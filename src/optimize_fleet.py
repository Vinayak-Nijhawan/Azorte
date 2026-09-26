"""
MOIL-GeoSync — MILP Fleet Dispatch Optimizer
=============================================
Assigns dumpers to shovels for each mine/month using Mixed-Integer
Linear Programming (Google OR-Tools, SCIP solver).

Equipment parameters are PROJECT-DEFINED ASSUMPTIONS (no real fleet
specs available). All assumptions are documented in the config section.

Inputs:
  data/production_forecast_real.csv (scenario-based ML predictions)
  models/production_config.json     (assumption parameters)

Outputs:
  data/dispatch_plan_real.csv       (optimized assignments)
  data/fleet_alerts_real.csv        (operational alerts)
"""

import os
import json
import numpy as np
import pandas as pd
from ortools.linear_solver import pywraplp

np.random.seed(42)

# ==============================================================================
# PATHS
# ==============================================================================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODEL_DIR = os.path.join(BASE_DIR, 'models')

# ==============================================================================
# EQUIPMENT ASSUMPTIONS (PROJECT-DEFINED — NOT real MOIL fleet specs)
# ==============================================================================
EQUIPMENT_CONFIG = {
    # Dumper specs (ASSUMED)
    "dumper_capacity_tph_range": (30, 45),   # Tons per hour per dumper
    "dumper_cycle_time_min": 30,             # Round trip: load + haul + dump + return
    "shifts_per_day": 2,
    "hours_per_shift": 8,
    "max_dumpers_per_shovel": 4,             # Congestion limit
    
    # Shovel specs (ASSUMED)
    "shovel_capacity_tph_range": (150, 280), # Tons per hour per shovel
    
    # Weather availability factor
    "rain_dumper_unavail_pct": 0.15,         # 15% of dumpers may be down in heavy rain
    
    # Haul road efficiency
    "haul_road_efficiency_base": 1.0,
    "haul_road_penalty_per_point": 0.08,     # 8% loss per road condition point below 5
}


def solve_fleet_milp(num_dumpers, num_shovels, target_tpd, crusher_capacity,
                     rainfall_mm, weather_penalty, haul_road_condition,
                     equipment_availability):
    """
    Solve the dumper-to-shovel assignment problem using MILP.
    
    Decision variables: x[d][s] = 1 if dumper d is assigned to shovel s
    Objective: Maximize total daily throughput
    
    Constraints:
    - Each dumper assigned to exactly one shovel (or idle if unavailable)
    - Max dumpers per shovel (congestion limit)
    - Total throughput <= crusher capacity
    - Weather-dependent dumper availability
    
    Returns: dict with solution details, or None if infeasible.
    """
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        return {"status": "SOLVER_NOT_AVAILABLE", "error": "SCIP solver not found"}
    
    # Generate equipment capacities (deterministic based on seed)
    rng = np.random.RandomState(42)
    dumper_caps = rng.uniform(
        EQUIPMENT_CONFIG["dumper_capacity_tph_range"][0],
        EQUIPMENT_CONFIG["dumper_capacity_tph_range"][1],
        num_dumpers
    )
    shovel_caps = rng.uniform(
        EQUIPMENT_CONFIG["shovel_capacity_tph_range"][0],
        EQUIPMENT_CONFIG["shovel_capacity_tph_range"][1],
        num_shovels
    )
    
    # Determine available dumpers based on equipment availability
    available = np.ones(num_dumpers, dtype=bool)
    n_unavail = int(num_dumpers * (1 - equipment_availability))
    if n_unavail > 0:
        unavail_idx = rng.choice(num_dumpers, n_unavail, replace=False)
        available[unavail_idx] = False
    
    # Haul road efficiency
    road_eff = max(
        EQUIPMENT_CONFIG["haul_road_efficiency_base"] - 
        (5 - haul_road_condition) * EQUIPMENT_CONFIG["haul_road_penalty_per_point"],
        0.50
    )
    
    # Effective dumper capacity (after weather + road adjustments)
    effective_caps = dumper_caps * weather_penalty * road_eff
    
    hours_per_day = EQUIPMENT_CONFIG["hours_per_shift"] * EQUIPMENT_CONFIG["shifts_per_day"]
    
    # Decision variables: x[d][s] = binary
    x = {}
    for d in range(num_dumpers):
        for s in range(num_shovels):
            x[d, s] = solver.BoolVar(f'x_{d}_{s}')
    
    # Constraint 1: Each available dumper assigned to exactly one shovel
    for d in range(num_dumpers):
        if available[d]:
            solver.Add(sum(x[d, s] for s in range(num_shovels)) == 1)
        else:
            # Unavailable dumpers cannot be assigned
            for s in range(num_shovels):
                solver.Add(x[d, s] == 0)
    
    # Constraint 2: Max dumpers per shovel (congestion)
    for s in range(num_shovels):
        solver.Add(
            sum(x[d, s] for d in range(num_dumpers)) <= 
            EQUIPMENT_CONFIG["max_dumpers_per_shovel"]
        )
    
    # Throughput per shovel = min(shovel_cap, sum of assigned dumper caps) * hours
    # We linearize this using auxiliary variables
    shovel_throughput = {}
    for s in range(num_shovels):
        shovel_throughput[s] = solver.NumVar(0, shovel_caps[s] * hours_per_day, f'st_{s}')
        
        # Throughput <= shovel capacity * hours
        solver.Add(shovel_throughput[s] <= shovel_caps[s] * hours_per_day)
        
        # Throughput <= sum of assigned dumper capacities * hours
        solver.Add(
            shovel_throughput[s] <= 
            sum(x[d, s] * effective_caps[d] * hours_per_day for d in range(num_dumpers))
        )
    
    # Constraint 3: Total throughput <= crusher capacity
    total_throughput = solver.NumVar(0, crusher_capacity, 'total')
    solver.Add(total_throughput == sum(shovel_throughput[s] for s in range(num_shovels)))
    solver.Add(total_throughput <= crusher_capacity)
    
    # Objective: Maximize total throughput
    solver.Maximize(total_throughput)
    
    # Solve
    status = solver.Solve()
    
    if status not in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
        # Report infeasibility
        return {
            "status": "INFEASIBLE",
            "error": f"Solver status: {status}. Constraints cannot be satisfied.",
            "limiting_constraints": [
                f"Crusher capacity: {crusher_capacity} TPD",
                f"Available dumpers: {available.sum()}/{num_dumpers}",
                f"Target TPD: {target_tpd}",
            ]
        }
    
    # Extract solution
    assignments = []
    for d in range(num_dumpers):
        assigned_shovel = None
        for s in range(num_shovels):
            if x[d, s].solution_value() > 0.5:
                assigned_shovel = s
                break
        
        assignments.append({
            "dumper_id": f"D{d+1:02d}",
            "dumper_capacity_tph": round(dumper_caps[d], 1),
            "effective_capacity_tph": round(effective_caps[d], 1) if available[d] else 0,
            "available": bool(available[d]),
            "assigned_shovel": f"S{assigned_shovel+1}" if assigned_shovel is not None else "IDLE",
        })
    
    per_shovel = []
    for s in range(num_shovels):
        st = shovel_throughput[s].solution_value()
        assigned_dumpers = [f"D{d+1:02d}" for d in range(num_dumpers) if x[d, s].solution_value() > 0.5]
        per_shovel.append({
            "shovel_id": f"S{s+1}",
            "shovel_capacity_tph": round(shovel_caps[s], 1),
            "assigned_dumpers": assigned_dumpers,
            "throughput_tpd": round(st, 1),
        })
    
    total_tpd = total_throughput.solution_value()
    
    return {
        "status": "OPTIMAL" if status == pywraplp.Solver.OPTIMAL else "FEASIBLE",
        "total_tpd": round(total_tpd, 1),
        "target_tpd": round(target_tpd, 1),
        "achievable_pct": round(total_tpd / target_tpd * 100, 1) if target_tpd > 0 else 0,
        "assignments": assignments,
        "per_shovel": per_shovel,
        "available_dumpers": int(available.sum()),
        "total_dumpers": num_dumpers,
        "weather_penalty": round(weather_penalty, 4),
        "road_efficiency": round(road_eff, 4),
    }


def main():
    print("=" * 70)
    print("MOIL-GeoSync — MILP Fleet Dispatch Optimizer")
    print("=" * 70)
    
    # Load forecast
    print("\n[1/4] Loading production forecast...")
    forecast_path = os.path.join(DATA_DIR, 'production_forecast_real.csv')
    forecast = pd.read_csv(forecast_path, comment='#')
    print(f"  Loaded {len(forecast)} forecast records")
    print(f"  Scenarios: {forecast.scenario.unique().tolist()}")
    
    # Load config
    with open(os.path.join(MODEL_DIR, 'production_config.json'), 'r') as f:
        config = json.load(f)
    
    # Only optimize for normal_weather scenario
    normal = forecast[forecast.scenario == 'normal_weather'].copy()
    print(f"  Optimizing for 'normal_weather': {len(normal)} records")
    
    # Solve for each mine/month
    print("\n[2/4] Running MILP solver for each mine/month...")
    
    dispatch_rows = []
    alert_rows = []
    solve_stats = {"optimal": 0, "feasible": 0, "infeasible": 0}
    
    for _, row in normal.iterrows():
        mine = row['mine_id']
        month = int(row['month'])
        year = int(row['year'])
        target = row['predicted_production_tpd']
        baseline = row['baseline_tpd']
        rainfall = row['rainfall_mm_scenario']
        wp = row['weather_penalty']
        
        # Get mine size
        if baseline > 600:
            mine_size = "large"
        elif baseline > 300:
            mine_size = "medium"
        else:
            mine_size = "small"
        
        nd = config["fleet_by_mine_size"][mine_size]["num_dumpers"]
        ns = config["fleet_by_mine_size"][mine_size]["num_shovels"]
        cc = config["crusher_capacity_tpd_by_mine_size"][mine_size]
        
        ea = max(0.92 - (rainfall / 500 * 0.15), 0.60)
        hr = max(4.5 - (rainfall / 100 * 0.8), 1.0)
        
        result = solve_fleet_milp(
            num_dumpers=nd, num_shovels=ns, target_tpd=target,
            crusher_capacity=cc, rainfall_mm=rainfall,
            weather_penalty=wp, haul_road_condition=hr,
            equipment_availability=ea,
        )
        
        if result["status"] in ["OPTIMAL", "FEASIBLE"]:
            solve_stats["optimal" if result["status"] == "OPTIMAL" else "feasible"] += 1
            
            for a in result["assignments"]:
                dispatch_rows.append({
                    "mine_id": mine,
                    "year": year,
                    "month": month,
                    "dumper_id": a["dumper_id"],
                    "assigned_shovel": a["assigned_shovel"],
                    "dumper_capacity_tph__ASSUMED": a["dumper_capacity_tph"],
                    "effective_capacity_tph": a["effective_capacity_tph"],
                    "available": a["available"],
                    "total_mine_tpd": result["total_tpd"],
                    "target_tpd": result["target_tpd"],
                    "achievable_pct": result["achievable_pct"],
                    "weather_condition": "heavy_rain" if rainfall > 200 else ("moderate" if rainfall > 100 else "dry"),
                    "solver_status": result["status"],
                    "data_type": "MILP_OPTIMIZED",
                })
            
            # Generate alerts
            if result["achievable_pct"] < 85:
                alert_rows.append({
                    "mine_id": mine, "year": year, "month": month,
                    "alert_type": "CRITICAL",
                    "alert_message": f"Achievable TPD ({result['total_tpd']:.0f}) is only {result['achievable_pct']:.0f}% of target. Consider deploying additional fleet.",
                })
            elif result["achievable_pct"] < 92:
                alert_rows.append({
                    "mine_id": mine, "year": year, "month": month,
                    "alert_type": "WARNING",
                    "alert_message": f"Production shortfall risk: {result['achievable_pct']:.0f}% achievable. Monitor weather and equipment status.",
                })
            
            if rainfall > 200:
                alert_rows.append({
                    "mine_id": mine, "year": year, "month": month,
                    "alert_type": "WARNING",
                    "alert_message": f"Heavy rainfall scenario ({rainfall:.0f}mm). Haul road degradation expected. Weather penalty: {(1-wp)*100:.0f}%",
                })
            
            if result["available_dumpers"] < result["total_dumpers"]:
                idle = result["total_dumpers"] - result["available_dumpers"]
                alert_rows.append({
                    "mine_id": mine, "year": year, "month": month,
                    "alert_type": "INFO",
                    "alert_message": f"{idle} dumper(s) unavailable due to maintenance/weather. {result['available_dumpers']}/{result['total_dumpers']} operational.",
                })
        else:
            solve_stats["infeasible"] += 1
            alert_rows.append({
                "mine_id": mine, "year": year, "month": month,
                "alert_type": "CRITICAL",
                "alert_message": f"MILP INFEASIBLE: {result.get('error', 'Unknown')}. Constraints: {result.get('limiting_constraints', [])}",
            })
    
    # Save
    print("\n[3/4] Saving results...")
    
    dispatch_df = pd.DataFrame(dispatch_rows)
    dispatch_path = os.path.join(DATA_DIR, 'dispatch_plan_real.csv')
    header = (
        "# MOIL-GeoSync Fleet Dispatch Plan (MILP Optimized)\n"
        "# Equipment capacities are PROJECT-DEFINED ASSUMPTIONS.\n"
        "# Assignments are mathematically optimal under stated constraints.\n"
    )
    with open(dispatch_path, 'w', encoding='utf-8') as f:
        f.write(header)
        dispatch_df.to_csv(f, index=False)
    
    alerts_df = pd.DataFrame(alert_rows)
    alerts_path = os.path.join(DATA_DIR, 'fleet_alerts_real.csv')
    with open(alerts_path, 'w', encoding='utf-8') as f:
        f.write("# MOIL-GeoSync Fleet Alerts\n")
        alerts_df.to_csv(f, index=False)
    
    # Report
    print("\n[4/4] OPTIMIZATION REPORT")
    print("-" * 40)
    print(f"  Solver Stats:")
    print(f"    Optimal:    {solve_stats['optimal']}")
    print(f"    Feasible:   {solve_stats['feasible']}")
    print(f"    Infeasible: {solve_stats['infeasible']}")
    print(f"\n  Dispatch records: {len(dispatch_df)}")
    print(f"  Alert records:    {len(alerts_df)}")
    
    if len(dispatch_df) > 0:
        by_mine = dispatch_df.groupby('mine_id').agg(
            avg_achievable=('achievable_pct', 'mean'),
            avg_tpd=('total_mine_tpd', 'mean'),
        ).round(1)
        print(f"\n  Per-Mine Summary:")
        print(f"  {'Mine':<30} {'Avg TPD':>10} {'Achievable%':>12}")
        for mine, r in by_mine.iterrows():
            print(f"  {mine:<30} {r.avg_tpd:>10.1f} {r.avg_achievable:>11.1f}%")
    
    if len(alerts_df) > 0:
        alert_counts = alerts_df.alert_type.value_counts()
        print(f"\n  Alert Summary:")
        for atype, count in alert_counts.items():
            print(f"    {atype}: {count}")
    
    print(f"\n  Saved: {dispatch_path}")
    print(f"  Saved: {alerts_path}")
    print("=" * 70)


if __name__ == '__main__':
    main()
