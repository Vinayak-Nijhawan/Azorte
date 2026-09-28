"""
MineFlow Underground Fleet Dispatch — Discrete-Event Simulation Engine
====================================================================
SimPy-based simulation for underground mining (LHD -> Ore Pass -> Hoist).
"""

import os
import math
import simpy
import numpy as np
import pandas as pd
import yaml
from typing import Dict, List, Optional

try:
    from ortools.sat.python import cp_model
    HAS_ORTOOLS = True
except ImportError:
    HAS_ORTOOLS = False


def load_config(config_path: Optional[str] = None) -> dict:
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(__file__), '..', 'config', 'underground_config.yaml'
        )
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_underground_mines(config: dict) -> List[str]:
    mines = config['underground_simulation']['mines']
    return sorted(name for name, cfg in mines.items() if cfg['type'] == 'underground')


def derive_lhd_tph(payload_t, loaded_speed_kmh, empty_speed_kmh, tram_m, load_min, dump_min):
    tram_km = tram_m / 1000.0
    haul_loaded_min = (tram_km / loaded_speed_kmh) * 60
    haul_empty_min = (tram_km / empty_speed_kmh) * 60
    cycle_min = load_min + haul_loaded_min + dump_min + haul_empty_min
    tph = payload_t * 60.0 / cycle_min if cycle_min > 0 else 0
    return cycle_min, tph


def derive_hoist_tph(skip_payload_t, winding_speed_ms, accel_s, load_s, dump_s, depth_m):
    travel_s = depth_m / winding_speed_ms
    cycle_s = (travel_s * 2) + accel_s + load_s + dump_s
    tph = skip_payload_t * 3600.0 / cycle_s
    return cycle_s, tph


class UndergroundSimulation:
    def __init__(self, config: dict, mine_name: str, mine_tpd: float):
        cfg = config['underground_simulation']
        mine_cfg = cfg['mines'][mine_name]

        self.mine_name = mine_name
        self.mine_tpd = min(mine_tpd, mine_cfg.get('capacity_tpy', float('inf')) / 365.0)

        # LHD config
        lhd = cfg['lhd_class']
        self.lhd_payload = lhd['payload_t']
        self.lhd_loaded_speed = lhd['loaded_speed_kmh']
        self.lhd_empty_speed = lhd['empty_speed_kmh']
        self.lhd_load_time = lhd['load_time_min']
        self.lhd_dump_time = lhd['dump_time_min']

        # Hoist config
        hoist = cfg['hoist']
        self.hoist_payload = hoist['skip_payload_t']
        self.hoist_speed = hoist['winding_speed_ms']
        self.hoist_accel = hoist['accel_s']
        self.hoist_load = hoist['load_time_s']
        self.hoist_dump = hoist['dump_time_s']
        self.hoist_depth = hoist['depth_m']

        self.ore_pass_cap = cfg['ore_pass']['capacity_t']

        # Operations
        self.shift_hours = cfg['shift']['hours']
        self.shifts_per_day = cfg['shift']['shifts_per_day']
        self.blast_window = cfg['shift']['blast_window_min']
        
        self.target_util = cfg['availability']['target_utilization']
        self.mtbf_hours = cfg['availability']['mtbf_hours']
        self.mttr_hours = cfg['availability']['mttr_hours']
        self.cv = cfg['cycle_variation']['sigma']
        
        self.base_seed = cfg['random_seed']
        self.num_runs = cfg['num_runs']

        # Draw points
        dp = cfg['draw_points']
        self.num_dp = dp['num_points']
        self.tram_dists = dp['tram_distance_m']
        self.grades = dp['grade_mn']

        # Derivations
        self.hoist_cycle_s, self.hoist_tph = derive_hoist_tph(
            self.hoist_payload, self.hoist_speed, self.hoist_accel,
            self.hoist_load, self.hoist_dump, self.hoist_depth
        )

        # LHD TPH (average across draw points)
        avg_tram = sum(self.tram_dists) / self.num_dp
        self.avg_lhd_cycle_min, self.avg_lhd_tph = derive_lhd_tph(
            self.lhd_payload, self.lhd_loaded_speed, self.lhd_empty_speed,
            avg_tram, self.lhd_load_time, self.lhd_dump_time
        )

        operating_hours = self.shift_hours * self.shifts_per_day
        self.num_lhds = max(1, math.ceil(self.mine_tpd / (self.avg_lhd_tph * operating_hours * self.target_util)))

    def _cp_sat_dispatch(self, pass_level, dp_queues, enroute, active_lhds) -> int:
        n = self.num_dp
        costs = np.zeros(n)
        
        # Penalize long queues and en-route
        for i in range(n):
            queued = dp_queues[i] + enroute[i]
            # distance penalty
            tram = self.tram_dists[i]
            # Grade penalty (try to blend towards 38% Mn)
            grade_diff = abs(self.grades[i] - 0.38)
            costs[i] = queued * 5.0 + (tram / 100.0) + (grade_diff * 100.0)
            
        if HAS_ORTOOLS:
            model = cp_model.CpModel()
            x = [model.NewBoolVar(f'dp_{i}') for i in range(n)]
            model.AddExactlyOne(x)
            
            # Scale costs to integers
            int_costs = [int(c * 100) for c in costs]
            model.Minimize(sum(x[i] * int_costs[i] for i in range(n)))
            
            solver = cp_model.CpSolver()
            status = solver.Solve(model)
            if status == cp_model.OPTIMAL:
                for i in range(n):
                    if solver.Value(x[i]):
                        return i
        
        return int(np.argmin(costs))

    def simulate_shift(self, strategy: str = 'fixed', seed: int = 42) -> dict:
        rng = np.random.RandomState(seed)
        env = simpy.Environment()
        shift_min = self.shift_hours * 60
        working_min = shift_min - self.blast_window

        shift_target = self.mine_tpd / self.shifts_per_day
        state = {'tonnes': 0.0, 'hoisted': 0.0, 'pass_level': 0.0, 'starve_events': 0, 'overflow_events': 0, 'hoist_util': 0.0}
        
        dispatched_tonnes = 0.0
        dispatched_hoisted = 0.0
        
        dp_queues = [0] * self.num_dp
        enroute = [0] * self.num_dp
        lhd_states = {}

        # SimPy container for ore pass
        ore_pass = simpy.Container(env, capacity=self.ore_pass_cap, init=self.ore_pass_cap * 0.2)
        hoist_lock = simpy.Resource(env, capacity=1)

        def lhd_process(lhd_id):
            nonlocal dispatched_tonnes
            ls = {
                'id': lhd_id, 'trips': 0, 'tonnes': 0.0,
                'queue_time': 0.0, 'tram_time': 0.0, 'idle_time': 0.0,
                'breakdown_time': 0.0, 'productive_time': 0.0,
                'mn_tonnes': 0.0
            }
            lhd_states[lhd_id] = ls

            fixed_dp = hash(lhd_id) % self.num_dp

            # Blast window at start of shift
            yield env.timeout(self.blast_window)

            while env.now < shift_min:
                if dispatched_tonnes >= shift_target:
                    yield env.timeout(shift_min - env.now)
                    break
                    
                dispatched_tonnes += self.lhd_payload

                if strategy == 'fixed':
                    dp_idx = fixed_dp
                elif strategy == 'greedy':
                    # Shortest tram + queue
                    dp_idx = min(range(self.num_dp), key=lambda i: self.tram_dists[i] + (dp_queues[i]*100))
                else:
                    dp_idx = self._cp_sat_dispatch(ore_pass.level, dp_queues, enroute, self.num_lhds)

                enroute[dp_idx] += 1
                
                # Tram empty
                tram_empty = (self.tram_dists[dp_idx] / 1000.0 / self.lhd_empty_speed) * 60
                actual_tram = max(0.5, rng.lognormal(np.log(tram_empty), self.cv))
                yield env.timeout(actual_tram)
                ls['tram_time'] += actual_tram
                ls['productive_time'] += actual_tram
                enroute[dp_idx] -= 1
                
                # Queue at DP (simulate single lane / mucking delay)
                dp_queues[dp_idx] += 1
                wait_t = max(0, (dp_queues[dp_idx]-1) * self.lhd_load_time)
                if wait_t > 0:
                    yield env.timeout(wait_t)
                    ls['queue_time'] += wait_t
                
                # Load
                load_t = max(0.5, rng.lognormal(np.log(self.lhd_load_time), self.cv))
                yield env.timeout(load_t)
                ls['productive_time'] += load_t
                dp_queues[dp_idx] -= 1

                # Tram loaded
                tram_loaded = (self.tram_dists[dp_idx] / 1000.0 / self.lhd_loaded_speed) * 60
                actual_tram = max(0.5, rng.lognormal(np.log(tram_loaded), self.cv))
                yield env.timeout(actual_tram)
                ls['tram_time'] += actual_tram
                ls['productive_time'] += actual_tram

                # Dump into ore pass
                if ore_pass.level + self.lhd_payload > ore_pass.capacity:
                    state['overflow_events'] += 1
                    # wait until space
                    t0 = env.now
                    yield ore_pass.put(self.lhd_payload)
                    ls['queue_time'] += env.now - t0
                else:
                    yield ore_pass.put(self.lhd_payload)

                dump_t = max(0.2, rng.lognormal(np.log(self.lhd_dump_time), self.cv))
                yield env.timeout(dump_t)
                ls['productive_time'] += dump_t

                ls['trips'] += 1
                ls['tonnes'] += self.lhd_payload
                ls['mn_tonnes'] += self.lhd_payload * self.grades[dp_idx]
                state['tonnes'] += self.lhd_payload

                # Breakdown
                p_bd = min(0.15, self.avg_lhd_cycle_min / (self.mtbf_hours * 60))
                if rng.random() < p_bd:
                    repair = max(5, rng.exponential(self.mttr_hours * 60))
                    yield env.timeout(repair)
                    ls['breakdown_time'] += repair

        def hoist_process():
            nonlocal dispatched_hoisted
            hoist_productive = 0.0
            hoist_trips = 0
            
            while env.now < shift_min:
                if dispatched_hoisted >= shift_target and ore_pass.level < self.hoist_payload:
                    yield env.timeout(shift_min - env.now)
                    break
                
                dispatched_hoisted += self.hoist_payload
                
                if ore_pass.level < self.hoist_payload:
                    state['starve_events'] += 1
                    # wait for ore
                    t0 = env.now
                    yield ore_pass.get(self.hoist_payload)
                    idle_t = env.now - t0
                else:
                    yield ore_pass.get(self.hoist_payload)

                cycle_m = max(0.5, rng.lognormal(np.log(self.hoist_cycle_s / 60.0), self.cv * 0.5))
                yield env.timeout(cycle_m)
                hoist_productive += cycle_m
                hoist_trips += 1
                state['hoisted'] += self.hoist_payload
            
            state['hoist_util'] = min(1.0, hoist_productive / shift_min) if shift_min > 0 else 0
            state['hoist_trips'] = hoist_trips

        for d in range(self.num_lhds):
            env.process(lhd_process(f'LHD{d+1:02d}'))
        
        env.process(hoist_process())
        env.run(until=shift_min)

        logs = []
        tot_mn = 0.0
        tot_t = 0.0
        for did, s in lhd_states.items():
            util = min(1.0, s['productive_time'] / shift_min) if shift_min > 0 else 0
            idle = max(0, shift_min - s['productive_time'] - s['queue_time'] - s['breakdown_time'] - self.blast_window)
            logs.append({
                'lhd_id': s['id'],
                'trips': s['trips'],
                'tonnes': s['tonnes'],
                'queue_time_min': round(s['queue_time'], 1),
                'idle_time_min': round(max(0, idle), 1),
                'utilisation_pct': round(util * 100, 1)
            })
            tot_mn += s['mn_tonnes']
            tot_t += s['tonnes']
        
        log_df = pd.DataFrame(logs) if logs else pd.DataFrame(columns=[
            'lhd_id', 'trips', 'tonnes', 'queue_time_min', 'idle_time_min', 'utilisation_pct'
        ])
        
        return {
            'lhd_logs': log_df,
            'tonnes_mined': float(tot_t),
            'tonnes_hoisted': float(state['hoisted']),
            'hoist_utilisation': state['hoist_util'] * 100,
            'lhd_utilisation': float(log_df['utilisation_pct'].mean()) if not log_df.empty else 0.0,
            'starve_events': state['starve_events'],
            'overflow_events': state['overflow_events'],
            'avg_grade': float(tot_mn / tot_t * 100) if tot_t > 0 else 0.0
        }

    def run_comparison(self, num_runs: Optional[int] = None) -> dict:
        if num_runs is None:
            num_runs = self.num_runs

        strategies = {
            'Fixed Assignment': 'fixed',
            'Nearest Draw Point': 'greedy',
            'CP-SAT Blended': 'cp_sat',
        }

        comparison = {}
        for label, strategy in strategies.items():
            hoist_list, util_list, grade_list = [], [], []
            starve_list, overflow_list = [], []

            for i in range(num_runs):
                seed = self.base_seed + i * 997
                res = self.simulate_shift(strategy=strategy, seed=seed)
                hoist_list.append(res['tonnes_hoisted'])
                util_list.append(res['lhd_utilisation'])
                grade_list.append(res['avg_grade'])
                starve_list.append(res['starve_events'])
                overflow_list.append(res['overflow_events'])

            comparison[label] = {
                'hoisted_mean': float(np.mean(hoist_list)),
                'hoisted_std': float(np.std(hoist_list)),
                'util_mean': float(np.mean(util_list)),
                'util_std': float(np.std(util_list)),
                'grade_mean': float(np.mean(grade_list)),
                'grade_std': float(np.std(grade_list)),
                'starve_mean': float(np.mean(starve_list)),
                'overflow_mean': float(np.mean(overflow_list)),
            }
        return comparison

    def validate(self, result: dict) -> List[str]:
        checks = []
        hoisted_tpd = result['tonnes_hoisted'] * self.shifts_per_day
        limit = self.mine_tpd * 1.05

        if hoisted_tpd <= limit:
            checks.append(('PASS', f'Achieved TPD ({hoisted_tpd:,.0f}) <= target × 1.05 ({limit:,.0f})'))
        else:
            checks.append(('FAIL', f'Achieved TPD ({hoisted_tpd:,.0f}) EXCEEDS target × 1.05 ({limit:,.0f})'))

        util = result['lhd_utilisation']
        if 60 <= util <= 95:
            checks.append(('PASS', f'LHD utilisation ({util:.1f}%) is within 60–95% range'))
        else:
            checks.append(('WARN', f'LHD utilisation ({util:.1f}%) is outside 60–95% range'))

        h_util = result['hoist_utilisation']
        if 60 <= h_util <= 95:
            checks.append(('PASS', f'Hoist utilisation ({h_util:.1f}%) is within 60–95% range'))
        else:
            checks.append(('WARN', f'Hoist utilisation ({h_util:.1f}%) is outside 60–95% range'))
            
        return checks
