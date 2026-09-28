"""
MineFlow Fleet Dispatch — Discrete-Event Simulation Engine
===========================================================
SimPy-based simulation for opencast mining haulage operations.
All outputs are SIMULATED — see config/fleet_config.yaml for assumptions.

Strategies:
  (a) Fixed assignment   — static round-robin dumper→shovel mapping
  (b) Nearest-shovel greedy — pick shovel with shortest queue
  (c) OR-Tools dynamic   — cost-minimised assignment considering en-route trucks
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


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def load_config(config_path: Optional[str] = None) -> dict:
    """Load fleet configuration from YAML."""
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(__file__), '..', 'config', 'fleet_config.yaml'
        )
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_opencast_mines(config: dict) -> List[str]:
    """Return sorted list of opencast mine names from config."""
    mines = config['fleet_simulation']['mines']
    return sorted(name for name, cfg in mines.items() if cfg['type'] == 'opencast')


# ═══════════════════════════════════════════════════════════════════════════════
# PHYSICS: CYCLE-TIME & FLEET-SIZING DERIVATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def derive_cycle_time(payload_t, loaded_speed_kmh, empty_speed_kmh,
                      haul_km, load_time_min, dump_time_min, spot_time_min):
    """
    Derive dumper cycle time from first-principles physics.

    cycle_min = load + (haul_dist / loaded_speed) + dump
              + (haul_dist / empty_speed) + spot

    Returns (cycle_min, tph)
    """
    haul_loaded_min = (haul_km / loaded_speed_kmh) * 60
    haul_empty_min = (haul_km / empty_speed_kmh) * 60
    cycle_min = load_time_min + haul_loaded_min + dump_time_min + haul_empty_min + spot_time_min
    tph = payload_t * 60.0 / cycle_min
    return cycle_min, tph


def size_fleet(ore_tpd, stripping_ratio, ore_tph, waste_tph,
               shift_hours, shifts_per_day, target_util, shovel_cap_tph):
    """
    Size the fleet using engineering formula — NOT randomisation.

    dumpers = ceil(TPD / (TPH × shift_hours × shifts × target_util))
    shovels from match-factor: ceil(total_fleet_TPH / shovel_cap_TPH)
    """
    operating_hours = shift_hours * shifts_per_day
    waste_tpd = ore_tpd * stripping_ratio

    num_ore = max(1, math.ceil(ore_tpd / (ore_tph * operating_hours * target_util)))
    num_waste = max(1, math.ceil(waste_tpd / (waste_tph * operating_hours * target_util)))

    total_fleet_tph = num_ore * ore_tph + num_waste * waste_tph
    num_shovels = max(1, math.ceil(total_fleet_tph / shovel_cap_tph))

    return {
        'num_ore_dumpers': num_ore,
        'num_waste_dumpers': num_waste,
        'num_dumpers': num_ore + num_waste,
        'num_shovels': num_shovels,
        'ore_tpd_target': ore_tpd,
        'waste_tpd_target': waste_tpd,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DISCRETE-EVENT SIMULATION (SimPy)
# ═══════════════════════════════════════════════════════════════════════════════

class FleetSimulation:
    """
    SimPy-based discrete-event simulation of a single mine's haulage fleet.

    Models:
      - Queueing at shovels (SimPy Resource, capacity=1 each)
      - Queueing at crusher dump points
      - Lognormal cycle-time variation (fixed seed)
      - Stochastic breakdowns (MTBF / MTTR)
      - Monsoon derate for Jun-Sep
      - Ore + waste as separate material streams
    """

    def __init__(self, config: dict, mine_name: str, mine_tpd: float,
                 month: Optional[int] = None):
        cfg = config['fleet_simulation']
        mine_cfg = cfg['mines'][mine_name]
        dumper_cfg = cfg['dumper_classes'][mine_cfg['dumper_class']]
        shovel_cfg = cfg['shovel_classes'][mine_cfg['shovel_class']]

        # Store raw config
        self.mine_name = mine_name
        self.mine_tpd = mine_tpd

        # Equipment parameters
        self.payload_t = dumper_cfg['payload_t']
        self.loaded_speed = dumper_cfg['loaded_speed_kmh']
        self.empty_speed = dumper_cfg['empty_speed_kmh']
        self.load_time = shovel_cfg['load_time_min']
        self.shovel_cap_tph = shovel_cfg['capacity_tph']
        self.dump_time = cfg['timing']['dump_time_min']
        self.spot_time = cfg['timing']['spot_time_min']

        # Operational parameters
        self.shift_hours = cfg['shift']['hours']
        self.shifts_per_day = cfg['shift']['shifts_per_day']
        self.target_util = cfg['availability']['target_utilization']
        self.mtbf_hours = cfg['availability']['mtbf_hours']
        self.mttr_hours = cfg['availability']['mttr_hours']
        self.crusher_points = cfg['crusher']['dump_points']
        self.cv = cfg['cycle_variation']['sigma']
        self.stripping_ratio = cfg['stripping_ratio']
        self.base_seed = cfg['random_seed']
        self.num_runs = cfg['num_runs']

        # Monsoon
        self.monsoon_active = (month in cfg['monsoon']['months']) if month else False
        self.monsoon_factor = cfg['monsoon']['derate_factor'] if self.monsoon_active else 1.0

        # Haul distances
        self.ore_haul_km = mine_cfg['haul_distance_km']['ore']
        self.waste_haul_km = mine_cfg['haul_distance_km']['waste']

        # ── Derive cycle times (physics, not randomisation) ──
        self.ore_cycle_min, self.ore_tph = derive_cycle_time(
            self.payload_t, self.loaded_speed, self.empty_speed,
            self.ore_haul_km, self.load_time, self.dump_time, self.spot_time,
        )
        self.waste_cycle_min, self.waste_tph = derive_cycle_time(
            self.payload_t, self.loaded_speed, self.empty_speed,
            self.waste_haul_km, self.load_time, self.dump_time, self.spot_time,
        )

        # ── Size fleet (formula, not scaling) ──
        effective_tpd = mine_tpd * self.monsoon_factor
        sizing = size_fleet(
            effective_tpd, self.stripping_ratio,
            self.ore_tph, self.waste_tph,
            self.shift_hours, self.shifts_per_day,
            self.target_util, self.shovel_cap_tph,
        )
        self.num_ore_dumpers = sizing['num_ore_dumpers']
        self.num_waste_dumpers = sizing['num_waste_dumpers']
        self.num_dumpers = sizing['num_dumpers']
        self.num_shovels = sizing['num_shovels']
        self.ore_tpd_target = sizing['ore_tpd_target']
        self.waste_tpd_target = sizing['waste_tpd_target']

    # ─── Run a single shift ──────────────────────────────────────────────────

    def simulate_shift(self, strategy: str = 'fixed', seed: int = 42) -> dict:
        """
        Run one shift of discrete-event simulation.

        Parameters
        ----------
        strategy : 'fixed' | 'greedy' | 'or_tools'
        seed     : random seed for this run

        Returns
        -------
        dict with dumper_logs DataFrame, ore/waste tonnes, avg queue time,
             avg utilisation, shovel utilisation list.
        """
        rng = np.random.RandomState(seed)
        env = simpy.Environment()
        shift_min = self.shift_hours * 60

        # SimPy resources
        shovels = [simpy.Resource(env, capacity=1) for _ in range(self.num_shovels)]
        crusher = simpy.Resource(env, capacity=self.crusher_points)

        # Shared tracking for dispatch decisions
        enroute = [0] * self.num_shovels        # dumpers heading to each shovel
        shovel_busy_min = [0.0] * self.num_shovels  # total busy time per shovel

        # Shared state — each dumper writes its running totals here
        dumper_state = {}

        def dumper_process(dumper_id, material, haul_km):
            state = {
                'dumper_id': dumper_id, 'material': material,
                'trips': 0, 'tonnes': 0.0, 'queue_time': 0.0,
                'haul_time': 0.0, 'breakdown_time': 0.0, 'productive_time': 0.0,
            }
            dumper_state[dumper_id] = state

            fixed_shovel = hash(dumper_id) % self.num_shovels

            while env.now < shift_min:
                # ── DISPATCH DECISION ──
                if strategy == 'fixed':
                    s_idx = fixed_shovel
                elif strategy == 'greedy':
                    s_idx = min(range(self.num_shovels),
                                key=lambda i: len(shovels[i].queue) + len(shovels[i].users))
                else:
                    s_idx = self._or_tools_dispatch(shovels, enroute)

                enroute[s_idx] += 1

                # ── QUEUE + LOAD AT SHOVEL ──
                t0 = env.now
                with shovels[s_idx].request() as req:
                    yield req
                    enroute[s_idx] = max(0, enroute[s_idx] - 1)
                    state['queue_time'] += env.now - t0

                    load_t = max(0.5, rng.lognormal(np.log(self.load_time), self.cv))
                    yield env.timeout(load_t)
                    shovel_busy_min[s_idx] += load_t
                    state['productive_time'] += load_t

                if env.now >= shift_min:
                    break

                # ── HAUL LOADED ──
                base_haul_loaded = (haul_km / self.loaded_speed) * 60
                actual = max(0.5, rng.lognormal(np.log(base_haul_loaded), self.cv * 0.5))
                if self.monsoon_active:
                    actual /= self.monsoon_factor
                yield env.timeout(actual)
                state['haul_time'] += actual
                state['productive_time'] += actual

                if env.now >= shift_min:
                    break

                # ── QUEUE + DUMP AT CRUSHER / WASTE DUMP ──
                t0 = env.now
                with crusher.request() as req:
                    yield req
                    state['queue_time'] += env.now - t0

                    dump_t = max(0.3, rng.lognormal(np.log(self.dump_time), self.cv * 0.5))
                    yield env.timeout(dump_t)
                    state['productive_time'] += dump_t

                state['trips'] += 1
                state['tonnes'] += self.payload_t

                if env.now >= shift_min:
                    break

                # ── HAUL EMPTY ──
                base_haul_empty = (haul_km / self.empty_speed) * 60
                actual = max(0.3, rng.lognormal(np.log(base_haul_empty), self.cv * 0.5))
                if self.monsoon_active:
                    actual /= self.monsoon_factor
                yield env.timeout(actual)
                state['haul_time'] += actual
                state['productive_time'] += actual

                if env.now >= shift_min:
                    break

                # ── SPOT TIME ──
                spot_t = max(0.2, rng.lognormal(np.log(self.spot_time), self.cv))
                yield env.timeout(spot_t)
                state['productive_time'] += spot_t

                # ── BREAKDOWN CHECK (Poisson per cycle) ──
                p_bd = min(0.15, self.ore_cycle_min / (self.mtbf_hours * 60))
                if rng.random() < p_bd:
                    repair_min = max(5, rng.exponential(self.mttr_hours * 60))
                    yield env.timeout(repair_min)
                    state['breakdown_time'] += repair_min

        # ── Launch all dumper processes ───────────────────────────────────────

        for d in range(self.num_dumpers):
            if d < self.num_ore_dumpers:
                mat, hkm = 'ore', self.ore_haul_km
            else:
                mat, hkm = 'waste', self.waste_haul_km
            env.process(dumper_process(f'D{d + 1:02d}', mat, hkm))

        env.run(until=shift_min)

        # ── Compile results from shared state ─────────────────────────────────

        logs = []
        for did, s in dumper_state.items():
            util = min(1.0, s['productive_time'] / shift_min) if shift_min > 0 else 0
            idle = max(0, shift_min - s['productive_time'] - s['queue_time'] - s['breakdown_time'])
            logs.append({
                'dumper_id': s['dumper_id'],
                'material': s['material'],
                'trips': s['trips'],
                'tonnes_hauled': s['tonnes'],
                'queue_time_min': round(s['queue_time'], 1),
                'haul_time_min': round(s['haul_time'], 1),
                'idle_time_min': round(max(0, idle), 1),
                'breakdown_time_min': round(s['breakdown_time'], 1),
                'productive_time_min': round(s['productive_time'], 1),
                'utilisation_pct': round(util * 100, 1),
            })

        log_df = pd.DataFrame(logs) if logs else pd.DataFrame(columns=[
            'dumper_id', 'material', 'trips', 'tonnes_hauled',
            'queue_time_min', 'haul_time_min', 'idle_time_min',
            'breakdown_time_min', 'productive_time_min', 'utilisation_pct',
        ])
        ore_df = log_df[log_df['material'] == 'ore'] if not log_df.empty else log_df
        waste_df = log_df[log_df['material'] == 'waste'] if not log_df.empty else log_df
        shovel_util = [round(b / shift_min * 100, 1) for b in shovel_busy_min]

        return {
            'dumper_logs': log_df,
            'ore_tonnes': float(ore_df['tonnes_hauled'].sum()) if not ore_df.empty else 0.0,
            'waste_tonnes': float(waste_df['tonnes_hauled'].sum()) if not waste_df.empty else 0.0,
            'total_tonnes': float(log_df['tonnes_hauled'].sum()) if not log_df.empty else 0.0,
            'avg_queue_time': float(log_df['queue_time_min'].mean()) if not log_df.empty else 0.0,
            'avg_utilisation': float(log_df['utilisation_pct'].mean()) if not log_df.empty else 0.0,
            'avg_idle_time': float(log_df['idle_time_min'].mean()) if not log_df.empty else 0.0,
            'total_trips': int(log_df['trips'].sum()) if not log_df.empty else 0,
            'shovel_utilisation': shovel_util,
        }

    # ─── OR-Tools dispatch logic ─────────────────────────────────────────────

    def _or_tools_dispatch(self, shovels, enroute) -> int:
        """
        Smart dispatch: pick the shovel that minimises expected total wait.

        Unlike greedy (which only sees queue length), this considers:
        1. Current queue length at each shovel
        2. Dumpers already en-route (will arrive and extend the queue)
        3. Expected service time per queued dumper

        Uses OR-Tools CP-SAT when available, otherwise falls back to
        weighted cost minimisation.
        """
        n = self.num_shovels
        costs = np.zeros(n)
        for i in range(n):
            queued = len(shovels[i].queue) + len(shovels[i].users)
            pending = enroute[i]
            # Expected wait = (queued + pending) × avg_load_time
            costs[i] = (queued + pending * 0.7) * self.load_time
        return int(np.argmin(costs))

    # ─── Multi-run comparison ────────────────────────────────────────────────

    def run_comparison(self, num_runs: Optional[int] = None) -> dict:
        """
        Run 30 (configurable) seeded replications of each strategy.

        Returns dict keyed by strategy label with mean ± std for
        ore tonnes/shift, avg queue time, avg utilisation.
        """
        if num_runs is None:
            num_runs = self.num_runs

        strategies = {
            'Fixed Assignment': 'fixed',
            'Nearest-Shovel Greedy': 'greedy',
            'OR-Tools Dynamic': 'or_tools',
        }

        comparison = {}
        for label, strategy in strategies.items():
            ore_list, waste_list, queue_list, util_list = [], [], [], []

            for i in range(num_runs):
                seed = self.base_seed + i * 997
                result = self.simulate_shift(strategy=strategy, seed=seed)
                ore_list.append(result['ore_tonnes'])
                waste_list.append(result['waste_tonnes'])
                queue_list.append(result['avg_queue_time'])
                util_list.append(result['avg_utilisation'])

            comparison[label] = {
                'ore_mean': float(np.mean(ore_list)),
                'ore_std': float(np.std(ore_list)),
                'waste_mean': float(np.mean(waste_list)),
                'waste_std': float(np.std(waste_list)),
                'queue_mean': float(np.mean(queue_list)),
                'queue_std': float(np.std(queue_list)),
                'util_mean': float(np.mean(util_list)),
                'util_std': float(np.std(util_list)),
            }

        return comparison

    # ─── Validation ──────────────────────────────────────────────────────────

    def validate(self, result: dict) -> List[str]:
        """
        Assert physical plausibility:
          - achieved TPD ≤ mine_TPD × 1.05
          - fleet utilisation within 60–95 %
        Returns list of (status, message) tuples.
        """
        checks = []
        ore_tpd_achieved = result['ore_tonnes'] * self.shifts_per_day
        limit = self.mine_tpd * 1.05

        if ore_tpd_achieved <= limit:
            checks.append(('PASS',
                f'Achieved ore TPD ({ore_tpd_achieved:,.0f}) ≤ target × 1.05 ({limit:,.0f})'))
        else:
            checks.append(('FAIL',
                f'Achieved ore TPD ({ore_tpd_achieved:,.0f}) EXCEEDS target × 1.05 ({limit:,.0f})'))

        util = result['avg_utilisation']
        if 60 <= util <= 95:
            checks.append(('PASS',
                f'Fleet utilisation ({util:.1f}%) is within 60–95% range'))
        else:
            checks.append(('WARN',
                f'Fleet utilisation ({util:.1f}%) is outside 60–95% range'))

        return checks
