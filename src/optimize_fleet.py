import os
import pandas as pd
import numpy as np
from ortools.linear_solver import pywraplp

# Set random seed for reproducibility
np.random.seed(42)

def main():
    # Setup paths relative to the script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..'))
    data_dir = os.path.join(project_root, 'data')
    
    forecast_path = os.path.join(data_dir, 'production_forecast.csv')
    dispatch_plan_path = os.path.join(data_dir, 'dispatch_plan.csv')
    alerts_path = os.path.join(data_dir, 'fleet_alerts.csv')

    print(f"Loading production forecast from: {forecast_path}")
    if not os.path.exists(forecast_path):
        print(f"Error: Could not find {forecast_path}")
        return

    df_forecast = pd.read_csv(forecast_path)
    print(f"Loaded {len(df_forecast)} forecast records.")
    
    dispatch_records = []
    alerts = []

    shift_hours = 8
    shifts_per_day = 2
    operating_hours = shift_hours * shifts_per_day

    for idx, row in df_forecast.iterrows():
        mine_id = row['mine_id']
        month = row['month']
        year = row['year']
        planned_tpd = row['planned_production_tpd']
        rainfall_mm = row['rainfall_mm']
        avail_pct = row['equipment_availability_pct']
        road_cond = row['haul_road_condition']
        
        # Real/synthetic parameters from data or generation
        num_dumpers = int(row.get('num_dumpers', np.random.randint(5, 9)))
        num_shovels = int(row.get('num_shovels', np.random.randint(2, 5)))
        crusher_capacity_tpd = row.get('crusher_capacity_tpd', planned_tpd * 1.2)
        
        # Weather penalty
        weather_penalty = 0.0
        if rainfall_mm > 100:
            weather_penalty = (rainfall_mm / 500.0) * 0.30
            alerts.append({
                'mine_id': mine_id, 'month': month, 'year': year,
                'alert_type': 'WARNING',
                'alert_message': f'High rainfall ({rainfall_mm:.1f}mm) expected — possible production dip.'
            })
            
        # Haul road penalty
        # scale condition 1-5 where 5 is best
        road_cond_val = float(road_cond) if pd.notnull(road_cond) else 5.0
        road_penalty = (5.0 - road_cond_val) * 0.10
        if road_penalty > 0.2:
            alerts.append({
                'mine_id': mine_id, 'month': month, 'year': year,
                'alert_type': 'WARNING',
                'alert_message': f'Haul road condition poor ({road_cond_val}) — consider alternate route/maintenance.'
            })

        # Equipment generation
        # Dumper capacities: ~30-40 tph
        dumper_caps_base = np.random.uniform(30, 40, num_dumpers)
        # Apply penalties to get effective capacities
        dumper_caps_eff = dumper_caps_base * (1.0 - weather_penalty) * (1.0 - road_penalty)
        
        # Availability
        dumper_avail = []
        for d in range(num_dumpers):
            is_avail = np.random.rand() <= avail_pct
            dumper_avail.append(is_avail)
            if not is_avail:
                alerts.append({
                    'mine_id': mine_id, 'month': month, 'year': year,
                    'alert_type': 'INFO',
                    'alert_message': f'Dumper D{d} unavailable — maintenance scheduled.'
                })
        
        # Shovel capacities: ~150-250 tph
        shovel_caps = np.random.uniform(150, 250, num_shovels)
        
        # Create solver
        solver = pywraplp.Solver.CreateSolver('SCIP')
        if not solver:
            print("Failed to create solver.")
            continue
            
        # Decision variables: x[d][s] = 1 if dumper d assigned to shovel s
        x = {}
        for d in range(num_dumpers):
            for s in range(num_shovels):
                x[d, s] = solver.IntVar(0, 1, f'x_{d}_{s}')
                
        # Constraint: Each available dumper assigned to exactly one shovel
        # Unavailable dumpers assigned to none
        for d in range(num_dumpers):
            if dumper_avail[d]:
                solver.Add(solver.Sum([x[d, s] for s in range(num_shovels)]) == 1)
            else:
                solver.Add(solver.Sum([x[d, s] for s in range(num_shovels)]) == 0)
                
        # Constraint: Max dumpers per shovel <= 4
        for s in range(num_shovels):
            solver.Add(solver.Sum([x[d, s] for d in range(num_dumpers)]) <= 4)
            
        # We want to maximize total throughput. Total throughput is sum of shovel throughputs.
        # Shovel throughput = min(shovel_capacity, sum of assigned dumper capacities).
        # We can formulate this by introducing a variable y[s] for each shovel throughput (in tph)
        # y[s] <= shovel_caps[s]
        # y[s] <= sum(dumper_caps_eff[d] * x[d, s])
        # Total daily throughput = sum(y[s]) * operating_hours
        
        y = {}
        for s in range(num_shovels):
            y[s] = solver.NumVar(0, shovel_caps[s], f'y_{s}')
            solver.Add(y[s] <= solver.Sum([dumper_caps_eff[d] * x[d, s] for d in range(num_dumpers)]))
            
        # Total daily throughput <= crusher capacity
        solver.Add(solver.Sum([y[s] for s in range(num_shovels)]) * operating_hours <= crusher_capacity_tpd)
        
        # Objective: Maximize total throughput
        solver.Maximize(solver.Sum([y[s] for s in range(num_shovels)]) * operating_hours)
        
        status = solver.Solve()
        
        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            total_mine_tpd = solver.Objective().Value()
            
            achievable_pct = (total_mine_tpd / planned_tpd * 100) if planned_tpd > 0 else 0
            
            if achievable_pct < 90:
                alerts.append({
                    'mine_id': mine_id, 'month': month, 'year': year,
                    'alert_type': 'CRITICAL',
                    'alert_message': f'Throughput at {achievable_pct:.1f}% of plan — risk of shortfall.'
                })
                
            for d in range(num_dumpers):
                assigned_shovel = -1
                for s in range(num_shovels):
                    if x[d, s].solution_value() > 0.5:
                        assigned_shovel = s
                        break
                        
                if assigned_shovel != -1:
                    shovel_throughput_tph = y[assigned_shovel].solution_value()
                    shovel_throughput_tpd = shovel_throughput_tph * operating_hours
                    
                    dispatch_records.append({
                        'mine_id': mine_id,
                        'month': month,
                        'year': year,
                        'dumper_id': f'D{d}',
                        'assigned_shovel': f'S{assigned_shovel}',
                        'dumper_capacity_tph': dumper_caps_base[d],
                        'effective_capacity_tph': dumper_caps_eff[d],
                        'shovel_id': f'S{assigned_shovel}',
                        'shovel_throughput_tpd': shovel_throughput_tpd,
                        'total_mine_tpd': total_mine_tpd,
                        'planned_tpd': planned_tpd,
                        'achievable_vs_planned_pct': achievable_pct
                    })
        else:
            print(f"Could not find optimal solution for {mine_id} {month}/{year}")

    # Output dispatch plan
    df_dispatch = pd.DataFrame(dispatch_records)
    df_dispatch.to_csv(dispatch_plan_path, index=False)
    print(f"\nGenerated dispatch plan with {len(df_dispatch)} assignments. Saved to {dispatch_plan_path}")
    
    # Output alerts
    df_alerts = pd.DataFrame(alerts)
    if len(df_alerts) > 0:
        df_alerts.to_csv(alerts_path, index=False)
    print(f"Generated {len(df_alerts)} fleet alerts. Saved to {alerts_path}")
    
    # Print summary
    print("\n--- Summary: Achievable vs Planned TPD ---")
    if not df_dispatch.empty:
        summary = df_dispatch.groupby(['mine_id', 'month', 'year']).agg({
            'total_mine_tpd': 'first',
            'planned_tpd': 'first',
            'achievable_vs_planned_pct': 'first'
        }).reset_index()
        
        for _, row in summary.iterrows():
            print(f"Mine: {row['mine_id']}, {row['month']}/{row['year']} -> "
                  f"Planned: {row['planned_tpd']:.1f}, "
                  f"Achievable: {row['total_mine_tpd']:.1f} ({row['achievable_vs_planned_pct']:.1f}%)")
    else:
        print("No dispatch records generated.")

if __name__ == '__main__':
    main()
