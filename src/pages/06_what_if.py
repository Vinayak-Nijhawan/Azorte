import os
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from ortools.linear_solver import pywraplp

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

@st.cache_data
def load_data():
    forecast_path = os.path.join(PROJECT_ROOT, 'data', 'production_forecast.csv')
    dispatch_path = os.path.join(PROJECT_ROOT, 'data', 'dispatch_plan.csv')
    
    try:
        forecast_df = pd.read_csv(forecast_path)
    except FileNotFoundError:
        forecast_df = pd.DataFrame()
        
    try:
        dispatch_df = pd.read_csv(dispatch_path)
    except FileNotFoundError:
        dispatch_df = pd.DataFrame()
        
    return forecast_df, dispatch_df

def solve_fleet_scenario(num_dumpers, num_shovels, rainfall_mm, equipment_availability_pct, haul_road_condition, crusher_capacity_tpd, planned_tpd):
    np.random.seed(42)
    
    # 1. Create dumper capacities (30-40 tph range, seeded)
    dumper_base_caps = np.random.uniform(30, 40, num_dumpers)
    # 2. Create shovel capacities (150-250 tph range, seeded)
    shovel_base_caps = np.random.uniform(150, 250, num_shovels)
    
    # 3. Apply weather penalty: if rainfall > 100, penalty = (rainfall/500) * 0.30
    weather_penalty = 0
    if rainfall_mm > 100:
        weather_penalty = (rainfall_mm / 500) * 0.30
        
    # 4. Apply road penalty: (5 - haul_road_condition) * 0.10
    road_penalty = (5 - haul_road_condition) * 0.10
    
    total_penalty = weather_penalty + road_penalty
    efficiency = max(0.1, 1.0 - total_penalty)
    
    # 5. Mark dumpers as unavailable based on equipment_availability_pct (seeded)
    available_dumpers = []
    for i in range(num_dumpers):
        if np.random.rand() <= equipment_availability_pct:
            available_dumpers.append((i, dumper_base_caps[i] * efficiency))
            
    available_shovels = []
    for j in range(num_shovels):
        available_shovels.append((j, shovel_base_caps[j] * efficiency))
        
    # 6. Solve MILP
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        return None
        
    x = {}
    for _, (i, d_cap) in enumerate(available_dumpers):
        for _, (j, s_cap) in enumerate(available_shovels):
            x[i, j] = solver.IntVar(0, 1, f'x_{i}_{j}')
            
    for _, (i, d_cap) in enumerate(available_dumpers):
        solver.Add(solver.Sum([x[i, j] for _, (j, s_cap) in enumerate(available_shovels)]) <= 1)
        
    for _, (j, s_cap) in enumerate(available_shovels):
        solver.Add(solver.Sum([x[i, j] * dumper_base_caps[i] * efficiency for _, (i, d_cap) in enumerate(available_dumpers)]) <= s_cap)
        
    objective = solver.Objective()
    for _, (i, d_cap) in enumerate(available_dumpers):
        for _, (j, s_cap) in enumerate(available_shovels):
            objective.SetCoefficient(x[i, j], float(d_cap))
    objective.SetMaximization()
    
    solver.Solve()
    
    assignments = []
    total_tpd = 0
    per_shovel_throughput = {j: 0 for _, (j, s_cap) in enumerate(available_shovels)}
    for _, (i, d_cap) in enumerate(available_dumpers):
        for _, (j, s_cap) in enumerate(available_shovels):
            if x[i, j].solution_value() > 0.5:
                eff_tpd = d_cap * 16 # Assuming 16 effective operating hours
                assignments.append({
                    'dumper_id': f'Dumper_{i}',
                    'shovel_id': f'Shovel_{j}',
                    'effective_capacity_tpd': eff_tpd
                })
                total_tpd += eff_tpd
                per_shovel_throughput[j] += eff_tpd
                
    if total_tpd > crusher_capacity_tpd:
        ratio = crusher_capacity_tpd / total_tpd
        total_tpd = crusher_capacity_tpd
        for a in assignments:
            a['effective_capacity_tpd'] *= ratio
        for j in per_shovel_throughput:
            per_shovel_throughput[j] *= ratio
            
    util_pct = (len(assignments) / max(1, num_dumpers)) * 100
    
    return {
        'total_tpd': total_tpd,
        'assignments': assignments,
        'per_shovel_throughput': per_shovel_throughput,
        'utilization_pct': util_pct
    }


st.title("What-If Scenario Simulator 🎛️")
st.subheader("Adjust operational parameters and see how the fleet optimizer responds in real-time")

forecast_df, dispatch_df = load_data()

if forecast_df.empty or dispatch_df.empty:
    st.error("Missing required data files (`production_forecast.csv` and/or `dispatch_plan.csv`).")
else:
    # Sidebar Controls
    st.sidebar.header("Scenario Settings")
    mines = forecast_df['mine_id'].unique().tolist()
    
    # Store selectors in session state if not present
    if 'selected_mine' not in st.session_state:
        st.session_state.selected_mine = mines[0]
    if 'selected_month' not in st.session_state:
        months = forecast_df[forecast_df['mine_id'] == st.session_state.selected_mine]['month'].unique().tolist()
        st.session_state.selected_month = months[0] if months else 1

    selected_mine = st.sidebar.selectbox("Select Mine", mines, key="mine_selector")
    
    available_months = forecast_df[forecast_df['mine_id'] == selected_mine]['month'].unique().tolist()
    selected_month = st.sidebar.selectbox("Select Month", available_months, key="month_selector")

    # Get default row
    default_row = forecast_df[(forecast_df['mine_id'] == selected_mine) & (forecast_df['month'] == selected_month)]
    if not default_row.empty:
        default_row = default_row.iloc[0]
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Adjust Scenario")

        def reset_defaults():
            st.session_state.sim_rainfall = int(default_row.get('rainfall_mm', 0))
            st.session_state.sim_equip_avail = float(default_row.get('equipment_availability_pct', 0.85))
            st.session_state.sim_road_cond = int(default_row.get('haul_road_condition', 3))
            st.session_state.sim_dumpers = int(default_row.get('num_dumpers', 5))
            st.session_state.sim_shovels = int(default_row.get('num_shovels', 2))
            st.session_state.sim_crusher = int(default_row.get('crusher_capacity_tpd', 1500))

        st.sidebar.button("Reset to Defaults", on_click=reset_defaults)

        # Initialize session state for sliders if not set
        if 'sim_rainfall' not in st.session_state:
            reset_defaults()

        sim_rainfall = st.sidebar.slider("Rainfall (mm)", 0, 500, int(st.session_state.sim_rainfall), key="sim_rainfall")
        sim_equip_avail = st.sidebar.slider("Equipment Availability", 0.50, 1.00, float(st.session_state.sim_equip_avail), 0.05, key="sim_equip_avail")
        sim_road_cond = st.sidebar.slider("Haul Road Condition", 1, 5, int(st.session_state.sim_road_cond), key="sim_road_cond")
        sim_dumpers = st.sidebar.slider("Number of Dumpers", 3, 10, int(st.session_state.sim_dumpers), key="sim_dumpers")
        sim_shovels = st.sidebar.slider("Number of Shovels", 1, 5, int(st.session_state.sim_shovels), key="sim_shovels")
        sim_crusher = st.sidebar.slider("Crusher Capacity (TPD)", 500, 3000, int(st.session_state.sim_crusher), step=100, key="sim_crusher")

        planned_tpd = default_row.get('planned_production_tpd', 1000)
        
        # Get original dispatch info for this mine/month
        orig_dispatch = dispatch_df[(dispatch_df['mine_id'] == selected_mine) & (dispatch_df['month'] == selected_month)]
        
        orig_tpd = orig_dispatch['effective_capacity_tph'].sum() * 16 if not orig_dispatch.empty else default_row.get('predicted_production_tpd', 0)
        orig_util = 85.0 # Placeholder if not in df
        orig_risk = default_row.get('shortfall_risk', 0.5)

        # Run Simulator
        sim_results = solve_fleet_scenario(
            num_dumpers=sim_dumpers,
            num_shovels=sim_shovels,
            rainfall_mm=sim_rainfall,
            equipment_availability_pct=sim_equip_avail,
            haul_road_condition=sim_road_cond,
            crusher_capacity_tpd=sim_crusher,
            planned_tpd=planned_tpd
        )

        if sim_results:
            sim_tpd = sim_results['total_tpd']
            sim_util = sim_results['utilization_pct']
            
            # Recalculate shortfall risk roughly based on planned vs simulated
            sim_risk = max(0, min(1, 1.0 - (sim_tpd / planned_tpd)))

            st.markdown("### Metrics Comparison")
            col1, col2, col3 = st.columns(3)
            
            tpd_delta = sim_tpd - orig_tpd
            col1.metric("Achievable TPD", f"{sim_tpd:.1f}", f"{tpd_delta:+.1f}", delta_color="normal")
            
            util_delta = sim_util - orig_util
            col2.metric("Fleet Utilization %", f"{sim_util:.1f}%", f"{util_delta:+.1f}%")
            
            risk_delta = sim_risk - orig_risk
            col3.metric("Shortfall Risk", f"{sim_risk:.2f}", f"{risk_delta:+.2f}", delta_color="inverse")

            # Impact Comparison Chart
            st.markdown("### Impact Comparison Chart")
            if orig_dispatch.empty:
                st.info("No original dispatch plan available for this mine/month to compare shovels.")
            else:
                orig_shovel_tpd = orig_dispatch.groupby('assigned_shovel')['effective_capacity_tph'].sum() * 16
                orig_shovels_list = [f"Shovel_{i}" for i in range(len(orig_shovel_tpd))]
                
                # Align data lengths
                max_shovels = max(len(orig_shovels_list), len(sim_results['per_shovel_throughput']))
                
                chart_data = []
                for idx in range(max_shovels):
                    shovel_name = f"Shovel_{idx}"
                    o_val = orig_shovel_tpd.iloc[idx] if idx < len(orig_shovel_tpd) else 0
                    s_val = sim_results['per_shovel_throughput'].get(idx, 0)
                    chart_data.append({"Shovel": shovel_name, "TPD": o_val, "Type": "Original"})
                    chart_data.append({"Shovel": shovel_name, "TPD": s_val, "Type": "Simulated"})
                    
                df_chart = pd.DataFrame(chart_data)
                fig = px.bar(df_chart, x="Shovel", y="TPD", color="Type", barmode="group",
                             title="Original vs Simulated TPD per Shovel")
                st.plotly_chart(fig, use_container_width=True)

            # Simulated Dispatch Table
            st.markdown("### Simulated Dispatch Table")
            if sim_results['assignments']:
                sim_df = pd.DataFrame(sim_results['assignments'])
                st.dataframe(sim_df, use_container_width=True)
            else:
                st.warning("No dumpers could be assigned in this scenario.")

            # Auto-Generated Recommendation
            st.markdown("### Recommendations")
            
            if sim_rainfall > 200:
                st.info(f"🌧️ Heavy rainfall scenario detected. Increased penalties applied.")
                
            if sim_tpd < orig_tpd:
                pct_drop = ((orig_tpd - sim_tpd) / orig_tpd) * 100 if orig_tpd else 0
                st.warning(f"⚠️ Simulated production is lower by {pct_drop:.1f}%. Consider deploying backup fleet or improving road conditions.")
            elif sim_tpd > orig_tpd:
                pct_inc = ((sim_tpd - orig_tpd) / orig_tpd) * 100 if orig_tpd else 0
                st.success(f"✅ Simulated production increased by {pct_inc:.1f}%. This configuration is recommended to boost throughput.")
            else:
                st.info("The selected parameters yield roughly the same throughput as the original plan.")
                
    else:
        st.warning("No forecast data available for the selected mine and month.")
