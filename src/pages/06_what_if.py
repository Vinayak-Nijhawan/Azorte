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
    
    dumper_base_caps = np.random.uniform(30, 40, num_dumpers)
    shovel_base_caps = np.random.uniform(150, 250, num_shovels)
    
    # Weather penalty
    weather_penalty = 0
    if rainfall_mm > 100:
        weather_penalty = (rainfall_mm / 500) * 0.30
    weather_loss_tpd = planned_tpd * weather_penalty
        
    # Road penalty
    road_penalty = (5 - haul_road_condition) * 0.10
    road_loss_tpd = planned_tpd * road_penalty
    
    total_penalty = weather_penalty + road_penalty
    efficiency = max(0.1, 1.0 - total_penalty)
    
    # Equipment availability
    available_dumpers = []
    unavailable_count = 0
    for i in range(num_dumpers):
        if np.random.rand() <= equipment_availability_pct:
            available_dumpers.append((i, dumper_base_caps[i] * efficiency))
        else:
            unavailable_count += 1
            
    available_shovels = []
    for j in range(num_shovels):
        available_shovels.append((j, shovel_base_caps[j] * efficiency))
        
    # Solve MILP
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
                eff_tpd = d_cap * 16
                assignments.append({
                    'dumper_id': f'Dumper_{i}',
                    'shovel_id': f'Shovel_{j}',
                    'effective_capacity_tpd': round(eff_tpd, 1)
                })
                total_tpd += eff_tpd
                per_shovel_throughput[j] += eff_tpd

    # Equipment loss = what we'd lose from unavailable dumpers
    equip_loss_tpd = (unavailable_count / max(1, num_dumpers)) * planned_tpd * 0.5
                
    crusher_loss_tpd = 0
    if total_tpd > crusher_capacity_tpd:
        crusher_loss_tpd = total_tpd - crusher_capacity_tpd
        ratio = crusher_capacity_tpd / total_tpd
        total_tpd = crusher_capacity_tpd
        for a in assignments:
            a['effective_capacity_tpd'] = round(a['effective_capacity_tpd'] * ratio, 1)
        for j in per_shovel_throughput:
            per_shovel_throughput[j] *= ratio
            
    util_pct = (len(assignments) / max(1, num_dumpers)) * 100
    
    return {
        'total_tpd': total_tpd,
        'assignments': assignments,
        'per_shovel_throughput': per_shovel_throughput,
        'utilization_pct': util_pct,
        'weather_loss': weather_loss_tpd,
        'road_loss': road_loss_tpd,
        'equip_loss': equip_loss_tpd,
        'crusher_loss': crusher_loss_tpd,
        'unavailable_dumpers': unavailable_count
    }


st.title("What-If Scenario Simulator 🎛️")
st.markdown("Adjust operational parameters and see how production and fleet respond **in real-time**")

forecast_df, dispatch_df = load_data()

if forecast_df.empty:
    st.error("Missing `production_forecast.csv`. Run the pipeline first.")
    st.stop()

# ================= SIDEBAR =================
st.sidebar.header("⚙️ Scenario Settings")
mines = forecast_df['mine_id'].unique().tolist()

selected_mine = st.sidebar.selectbox("Select Mine", mines)
available_months = forecast_df[forecast_df['mine_id'] == selected_mine]['month'].unique().tolist()
selected_month = st.sidebar.selectbox("Select Month (2026)", available_months)

default_row = forecast_df[(forecast_df['mine_id'] == selected_mine) & (forecast_df['month'] == selected_month)]

if default_row.empty:
    st.warning("No forecast data for selected mine/month.")
    st.stop()

default_row = default_row.iloc[0]

# ================= ONE-CLICK PRESETS =================
st.sidebar.markdown("---")
st.sidebar.markdown("### 🚀 Quick Scenarios")

preset_cols = st.sidebar.columns(3)

def apply_preset(rain, equip, road, dumpers, shovels, crusher):
    st.session_state.sim_rainfall = rain
    st.session_state.sim_equip_avail = equip
    st.session_state.sim_road_cond = road
    st.session_state.sim_dumpers = dumpers
    st.session_state.sim_shovels = shovels
    st.session_state.sim_crusher = crusher

with preset_cols[0]:
    if st.button("⛈️ Monsoon", use_container_width=True):
        apply_preset(350, 0.65, 1, int(default_row.get('num_dumpers', 6)), int(default_row.get('num_shovels', 3)), int(default_row.get('crusher_capacity_tpd', 1500)))

with preset_cols[1]:
    if st.button("🔧 Breakdown", use_container_width=True):
        apply_preset(50, 0.50, 3, 3, 1, int(default_row.get('crusher_capacity_tpd', 1500)))

with preset_cols[2]:
    if st.button("☀️ Ideal", use_container_width=True):
        apply_preset(0, 0.98, 5, 8, 4, 2000)

# Reset button
def reset_defaults():
    st.session_state.sim_rainfall = int(default_row.get('rainfall_mm', 0))
    st.session_state.sim_equip_avail = float(default_row.get('equipment_availability_pct', 0.85))
    st.session_state.sim_road_cond = int(default_row.get('haul_road_condition', 3))
    st.session_state.sim_dumpers = int(default_row.get('num_dumpers', 5))
    st.session_state.sim_shovels = int(default_row.get('num_shovels', 2))
    st.session_state.sim_crusher = int(default_row.get('crusher_capacity_tpd', 1500))

st.sidebar.button("🔄 Reset to Defaults", on_click=reset_defaults, use_container_width=True)

# Initialize if not set
if 'sim_rainfall' not in st.session_state:
    reset_defaults()

# ================= GROUPED SLIDERS =================
st.sidebar.markdown("---")

with st.sidebar.expander("🌧️ Weather Conditions", expanded=True):
    sim_rainfall = st.slider("Rainfall (mm)", 0, 500, int(st.session_state.sim_rainfall), key="sim_rainfall")
    sim_road_cond = st.slider("Haul Road Condition", 1, 5, int(st.session_state.sim_road_cond), key="sim_road_cond",
                              help="1 = Waterlogged/Muddy, 5 = Dry & Excellent")

with st.sidebar.expander("🚛 Fleet Assets", expanded=True):
    sim_dumpers = st.slider("Number of Dumpers", 3, 10, int(st.session_state.sim_dumpers), key="sim_dumpers")
    sim_shovels = st.slider("Number of Shovels", 1, 5, int(st.session_state.sim_shovels), key="sim_shovels")
    sim_crusher = st.slider("Crusher Capacity (TPD)", 500, 3000, int(st.session_state.sim_crusher), step=100, key="sim_crusher")

with st.sidebar.expander("⚙️ Operational Status", expanded=True):
    sim_equip_avail = st.slider("Equipment Availability", 0.50, 1.00, float(st.session_state.sim_equip_avail), 0.05, key="sim_equip_avail",
                                help="Percentage of fleet that is operational")

planned_tpd = default_row.get('planned_production_tpd', 1000)

# ================= RUN SIMULATION =================
sim_results = solve_fleet_scenario(
    num_dumpers=sim_dumpers, num_shovels=sim_shovels,
    rainfall_mm=sim_rainfall, equipment_availability_pct=sim_equip_avail,
    haul_road_condition=sim_road_cond, crusher_capacity_tpd=sim_crusher,
    planned_tpd=planned_tpd
)

if not sim_results:
    st.error("Solver failed. Try different parameters.")
    st.stop()

sim_tpd = sim_results['total_tpd']
sim_util = sim_results['utilization_pct']
sim_risk = max(0, min(1, 1.0 - (sim_tpd / planned_tpd)))

# Original values
orig_dispatch = dispatch_df[(dispatch_df['mine_id'] == selected_mine) & (dispatch_df['month'] == selected_month)] if not dispatch_df.empty else pd.DataFrame()
orig_tpd = orig_dispatch['effective_capacity_tph'].sum() * 16 if not orig_dispatch.empty else default_row.get('predicted_production_tpd', 0)
orig_util = 85.0

orig_risk_raw = default_row.get('shortfall_risk', 0.5)
if isinstance(orig_risk_raw, str):
    risk_map = {'High': 0.8, 'Medium': 0.5, 'Low': 0.2}
    orig_risk = risk_map.get(orig_risk_raw, 0.5)
else:
    orig_risk = float(orig_risk_raw)

# ================= METRICS ROW =================
st.markdown("### 📊 Metrics Comparison")
col1, col2, col3, col4 = st.columns(4)

tpd_delta = sim_tpd - orig_tpd
col1.metric("Achievable TPD", f"{sim_tpd:.0f}", f"{tpd_delta:+.0f}", delta_color="normal")

col2.metric("Planned TPD", f"{planned_tpd:.0f}")

risk_delta = sim_risk - orig_risk
col3.metric("Shortfall Risk", f"{sim_risk:.0%}", f"{risk_delta:+.0%}", delta_color="inverse")

shortfall = max(0, planned_tpd - sim_tpd)
col4.metric("Production Gap", f"{shortfall:.0f} TPD")

# ================= GAUGE CHART =================
st.markdown("### 🎛️ Fleet Utilization")
g1, g2 = st.columns(2)

with g1:
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=sim_util,
        delta={'reference': orig_util, 'suffix': '%'},
        title={'text': "Fleet Utilization %"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': '#2ecc71' if sim_util >= 75 else '#e67e22' if sim_util >= 50 else '#e74c3c'},
            'steps': [
                {'range': [0, 50], 'color': 'rgba(231,76,60,0.15)'},
                {'range': [50, 75], 'color': 'rgba(230,126,34,0.15)'},
                {'range': [75, 100], 'color': 'rgba(46,204,113,0.15)'}
            ],
            'threshold': {'line': {'color': 'white', 'width': 3}, 'thickness': 0.8, 'value': orig_util}
        }
    ))
    fig_gauge.update_layout(height=280, margin=dict(l=30, r=30, t=50, b=10))
    st.plotly_chart(fig_gauge, use_container_width=True)

with g2:
    fig_risk_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=sim_risk * 100,
        title={'text': "Shortfall Risk %"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': '#e74c3c' if sim_risk >= 0.5 else '#e67e22' if sim_risk >= 0.2 else '#2ecc71'},
            'steps': [
                {'range': [0, 20], 'color': 'rgba(46,204,113,0.15)'},
                {'range': [20, 50], 'color': 'rgba(230,126,34,0.15)'},
                {'range': [50, 100], 'color': 'rgba(231,76,60,0.15)'}
            ]
        }
    ))
    fig_risk_gauge.update_layout(height=280, margin=dict(l=30, r=30, t=50, b=10))
    st.plotly_chart(fig_risk_gauge, use_container_width=True)

# ================= WATERFALL CHART =================
st.markdown("### 🌊 Production Breakdown — Where is TPD Lost?")

waterfall_data = {
    'Step': ['Planned TPD', 'Weather Impact', 'Road Condition', 'Equipment Downtime', 'Crusher Cap Limit', 'Simulated TPD'],
    'Value': [planned_tpd, -sim_results['weather_loss'], -sim_results['road_loss'], 
              -sim_results['equip_loss'], -sim_results['crusher_loss'], sim_tpd],
    'Type': ['absolute', 'relative', 'relative', 'relative', 'relative', 'total']
}

fig_waterfall = go.Figure(go.Waterfall(
    x=waterfall_data['Step'],
    y=waterfall_data['Value'],
    measure=waterfall_data['Type'],
    textposition="outside",
    text=[f"{v:+.0f}" if t != 'absolute' and t != 'total' else f"{v:.0f}" for v, t in zip(waterfall_data['Value'], waterfall_data['Type'])],
    connector={"line": {"color": "rgba(255,255,255,0.3)"}},
    increasing={"marker": {"color": "#2ecc71"}},
    decreasing={"marker": {"color": "#e74c3c"}},
    totals={"marker": {"color": "#3498db"}}
))
fig_waterfall.update_layout(
    height=400, title="Production Loss Waterfall",
    yaxis_title="TPD", showlegend=False,
    margin=dict(l=60, r=20, t=60, b=60)
)
st.plotly_chart(fig_waterfall, use_container_width=True)

# ================= SHOVEL COMPARISON ============================
st.markdown("### 📊 Shovel Throughput — Original vs Simulated")

if not orig_dispatch.empty:
    orig_shovel_tpd = orig_dispatch.groupby('assigned_shovel')['effective_capacity_tph'].sum() * 16
    max_shovels = max(len(orig_shovel_tpd), len(sim_results['per_shovel_throughput']))
    
    chart_data = []
    for idx in range(max_shovels):
        shovel_name = f"Shovel_{idx}"
        o_val = orig_shovel_tpd.iloc[idx] if idx < len(orig_shovel_tpd) else 0
        s_val = sim_results['per_shovel_throughput'].get(idx, 0)
        chart_data.append({"Shovel": shovel_name, "TPD": round(o_val, 1), "Type": "Original"})
        chart_data.append({"Shovel": shovel_name, "TPD": round(s_val, 1), "Type": "Simulated"})
        
    fig_bar = px.bar(pd.DataFrame(chart_data), x="Shovel", y="TPD", color="Type", barmode="group",
                     color_discrete_map={"Original": "#3498db", "Simulated": "#e67e22"})
    fig_bar.update_layout(height=350)
    st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.info("No original dispatch plan available for comparison.")

# ================= DISPATCH TABLE =================
st.markdown("### 📋 Simulated Dispatch Assignments")
if sim_results['assignments']:
    sim_df = pd.DataFrame(sim_results['assignments'])
    sim_df.columns = ['Dumper', 'Assigned Shovel', 'Effective TPD']
    st.dataframe(sim_df, use_container_width=True, hide_index=True)
    
    st.caption(f"**{len(sim_results['assignments'])}** / {sim_dumpers} dumpers assigned | "
               f"**{sim_results['unavailable_dumpers']}** dumpers unavailable due to maintenance")
else:
    st.warning("No dumpers could be assigned in this scenario.")

# ================= RECOMMENDATIONS =================
st.markdown("### 💡 Auto-Generated Recommendations")

recs = []
if sim_rainfall > 200:
    recs.append(("🌧️", f"Heavy rainfall ({sim_rainfall}mm) detected. Consider delaying non-critical haul operations and deploying water pumps.", "warning"))
if sim_results['unavailable_dumpers'] > 1:
    recs.append(("🔧", f"{sim_results['unavailable_dumpers']} dumpers are down. Schedule preventive maintenance in dry season to avoid simultaneous failures.", "warning"))
if sim_road_cond <= 2:
    recs.append(("🛤️", f"Road condition is poor ({sim_road_cond}/5). Invest in road grading and drainage to recover ~{sim_results['road_loss']:.0f} TPD.", "warning"))
if sim_tpd > planned_tpd * 0.95:
    recs.append(("✅", f"Simulated production meets {(sim_tpd/planned_tpd*100):.0f}% of planned target. This configuration is optimal!", "success"))
if sim_tpd < planned_tpd * 0.7:
    recs.append(("🚨", f"Production is at {(sim_tpd/planned_tpd*100):.0f}% of target — critical shortfall! Deploy backup fleet immediately.", "error"))
if sim_results['crusher_loss'] > 0:
    recs.append(("🏭", f"Crusher is bottlenecking {sim_results['crusher_loss']:.0f} TPD. Consider upgrading crusher capacity or adding a secondary crusher.", "info"))

if not recs:
    recs.append(("📊", "Parameters are within normal operating range. No immediate action required.", "info"))

for icon, text, level in recs:
    getattr(st, level)(f"{icon} {text}")

# ================= FINANCIAL IMPACT =================
st.markdown("### 💰 Estimated Financial Impact")
mn_price_per_ton = 12000  # ₹ per ton (approximate manganese ore price)
daily_loss = max(0, planned_tpd - sim_tpd)
monthly_loss = daily_loss * 25  # ~25 working days
annual_loss = monthly_loss * 12

f1, f2, f3 = st.columns(3)
f1.metric("Daily Revenue Loss", f"₹{daily_loss * mn_price_per_ton / 100000:.1f}L")
f2.metric("Monthly Loss (est.)", f"₹{monthly_loss * mn_price_per_ton / 10000000:.2f}Cr")
f3.metric("Annual Loss (est.)", f"₹{annual_loss * mn_price_per_ton / 10000000:.1f}Cr")

st.caption("*Based on approximate manganese ore price of ₹12,000/ton. Actual prices vary by grade and market conditions.*")
