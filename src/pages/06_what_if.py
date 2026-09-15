import os
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from ortools.linear_solver import pywraplp

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

@st.cache_data
def load_data():
    fp = os.path.join(PROJECT_ROOT, 'data', 'production_forecast.csv')
    dp = os.path.join(PROJECT_ROOT, 'data', 'dispatch_plan.csv')
    forecast = pd.read_csv(fp) if os.path.exists(fp) else pd.DataFrame()
    dispatch = pd.read_csv(dp) if os.path.exists(dp) else pd.DataFrame()
    return forecast, dispatch

forecast_df, dispatch_df = load_data()

if forecast_df.empty:
    st.error("Missing `production_forecast.csv`. Run the pipeline first.")
    st.stop()

# ================= PAGE HEADER =================
st.title("What-If Scenario Simulator 🎛️")
st.markdown("Change mine conditions below and instantly see the impact on production, fleet, and revenue.")

# ================= SIDEBAR — MINE SELECTION =================
st.sidebar.header("Mine & Month")
mines = forecast_df['mine_id'].unique().tolist()
selected_mine = st.sidebar.selectbox("Mine", mines)
months = forecast_df[forecast_df['mine_id'] == selected_mine]['month'].unique().tolist()
selected_month = st.sidebar.selectbox("Month (2026)", months)

row = forecast_df[(forecast_df['mine_id'] == selected_mine) & (forecast_df['month'] == selected_month)]
if row.empty:
    st.warning("No data for this selection.")
    st.stop()
row = row.iloc[0]

planned_tpd = float(row.get('planned_production_tpd', 1000))

# ================= QUICK PRESETS =================
st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ Quick Presets")

def set_preset(rain, equip, road, dump, shov):
    st.session_state.update({'rain': rain, 'equip': equip, 'road': road, 'dump': dump, 'shov': shov})

p1, p2, p3 = st.sidebar.columns(3)
p1.button("⛈️ Monsoon", on_click=set_preset, args=(350, 0.60, 1, int(row.get('num_dumpers',6)), int(row.get('num_shovels',3))), use_container_width=True)
p2.button("🔧 Breakdown", on_click=set_preset, args=(50, 0.50, 3, 3, 1), use_container_width=True)
p3.button("☀️ Best Case", on_click=set_preset, args=(0, 0.98, 5, 8, 4), use_container_width=True)

# Defaults
if 'rain' not in st.session_state:
    set_preset(int(row.get('rainfall_mm',100)), float(row.get('equipment_availability_pct',0.85)),
               int(row.get('haul_road_condition',3)), int(row.get('num_dumpers',6)), int(row.get('num_shovels',3)))

st.sidebar.button("🔄 Reset", on_click=lambda: set_preset(
    int(row.get('rainfall_mm',100)), float(row.get('equipment_availability_pct',0.85)),
    int(row.get('haul_road_condition',3)), int(row.get('num_dumpers',6)), int(row.get('num_shovels',3))
), use_container_width=True)

# ================= SLIDERS =================
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎚️ Adjust Parameters")

rain = st.sidebar.slider("🌧️ Rainfall (mm)", 0, 500, key="rain")
road = st.sidebar.slider("🛤️ Road Condition (1=Bad → 5=Good)", 1, 5, key="road")
equip = st.sidebar.slider("⚙️ Equipment Availability %", 0.40, 1.00, step=0.05, key="equip")
dump = st.sidebar.slider("🚛 Dumpers Available", 2, 10, key="dump")
shov = st.sidebar.slider("⛏️ Shovels Available", 1, 5, key="shov")
crusher_cap = int(row.get('crusher_capacity_tpd', 1500))

# ================= CALCULATE PRODUCTION (Transparent) =================
# Step 1: Start with planned
base = planned_tpd

# Step 2: Weather penalty (rain > 100mm starts hurting)
weather_factor = 1.0
if rain > 100:
    weather_factor = max(0.4, 1.0 - (rain / 500) * 0.30)
weather_loss = base * (1 - weather_factor)
after_weather = base - weather_loss

# Step 3: Road penalty (bad roads slow everything)
road_factor = 1.0 - (5 - road) * 0.08
road_loss = after_weather * (1 - road_factor)
after_road = after_weather - road_loss

# Step 4: Equipment availability (some machines are down)
equip_loss = after_road * (1 - equip)
after_equip = after_road - equip_loss

# Step 5: Fleet size impact (fewer dumpers = less throughput)
default_dumpers = int(row.get('num_dumpers', 6))
fleet_ratio = min(1.0, dump / max(1, default_dumpers))
fleet_loss = after_equip * (1 - fleet_ratio)
after_fleet = after_equip - fleet_loss

# Step 6: Crusher bottleneck
crusher_loss = max(0, after_fleet - crusher_cap)
final_tpd = min(after_fleet, crusher_cap)

efficiency = (final_tpd / planned_tpd) * 100 if planned_tpd > 0 else 0
shortfall = max(0, planned_tpd - final_tpd)
risk_pct = max(0, min(100, 100 - efficiency))

# ================= TOP KPI ROW =================
k1, k2, k3, k4 = st.columns(4)
k1.metric("📋 Planned", f"{planned_tpd:.0f} TPD")
k2.metric("⛏️ Achievable", f"{final_tpd:.0f} TPD", f"{final_tpd - planned_tpd:+.0f}")
k3.metric("📊 Efficiency", f"{efficiency:.0f}%")
k4.metric("⚠️ Shortfall", f"{shortfall:.0f} TPD")

# ================= GAUGE METERS =================
g1, g2 = st.columns(2)

with g1:
    color = '#2ecc71' if efficiency >= 80 else '#e67e22' if efficiency >= 60 else '#e74c3c'
    fig_g = go.Figure(go.Indicator(
        mode="gauge+number", value=efficiency,
        number={'suffix': '%'},
        title={'text': "Production Efficiency"},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': color},
               'steps': [{'range': [0,60], 'color': 'rgba(231,76,60,0.12)'},
                         {'range': [60,80], 'color': 'rgba(230,126,34,0.12)'},
                         {'range': [80,100], 'color': 'rgba(46,204,113,0.12)'}]}
    ))
    fig_g.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=10))
    st.plotly_chart(fig_g, use_container_width=True)

with g2:
    r_color = '#e74c3c' if risk_pct >= 40 else '#e67e22' if risk_pct >= 20 else '#2ecc71'
    fig_r = go.Figure(go.Indicator(
        mode="gauge+number", value=risk_pct,
        number={'suffix': '%'},
        title={'text': "Shortfall Risk"},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': r_color},
               'steps': [{'range': [0,20], 'color': 'rgba(46,204,113,0.12)'},
                         {'range': [20,40], 'color': 'rgba(230,126,34,0.12)'},
                         {'range': [40,100], 'color': 'rgba(231,76,60,0.12)'}]}
    ))
    fig_r.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=10))
    st.plotly_chart(fig_r, use_container_width=True)

# ================= WATERFALL CHART =================
st.subheader("🌊 Production Breakdown — Where TPD is Lost")
st.markdown("This waterfall shows how your **planned production gets reduced** step-by-step due to different factors.")

fig_wf = go.Figure(go.Waterfall(
    x=['Planned TPD', '🌧️ Weather', '🛤️ Road', '⚙️ Equipment', '🚛 Fleet Size', '🏭 Crusher Limit', 'Final TPD'],
    y=[planned_tpd, -round(weather_loss), -round(road_loss), -round(equip_loss), -round(fleet_loss), -round(crusher_loss), final_tpd],
    measure=['absolute', 'relative', 'relative', 'relative', 'relative', 'relative', 'total'],
    text=[f"{planned_tpd:.0f}", f"-{weather_loss:.0f}", f"-{road_loss:.0f}", f"-{equip_loss:.0f}", 
          f"-{fleet_loss:.0f}", f"-{crusher_loss:.0f}", f"{final_tpd:.0f}"],
    textposition="outside",
    connector={"line": {"color": "rgba(255,255,255,0.2)"}},
    decreasing={"marker": {"color": "#e74c3c"}},
    increasing={"marker": {"color": "#2ecc71"}},
    totals={"marker": {"color": "#3498db"}}
))
fig_wf.update_layout(height=420, yaxis_title="Production (TPD)", showlegend=False)
st.plotly_chart(fig_wf, use_container_width=True)

# Explain the biggest loss
losses = {'Weather': weather_loss, 'Road Condition': road_loss, 'Equipment Downtime': equip_loss, 
          'Fleet Size': fleet_loss, 'Crusher Limit': crusher_loss}
biggest = max(losses, key=losses.get)
if losses[biggest] > 0:
    st.warning(f"⚠️ **Biggest loss factor: {biggest}** — causing {losses[biggest]:.0f} TPD reduction. Fix this first for maximum impact!")
else:
    st.success("✅ No significant losses! Production is running at optimal levels.")

# ================= FLEET DISPATCH (MILP) =================
st.subheader("📋 Optimized Fleet Dispatch")
st.markdown("OR-Tools MILP solver assigns each available dumper to the best shovel for maximum throughput.")

np.random.seed(42)
dumper_caps = np.random.uniform(30, 40, dump)
shovel_caps = np.random.uniform(150, 250, shov)
eff = max(0.3, weather_factor * road_factor)

# Build assignments
solver = pywraplp.Solver.CreateSolver('SCIP')
if solver:
    avail_d = [(i, dumper_caps[i] * eff) for i in range(dump) if np.random.RandomState(42+i).rand() <= equip]
    
    x = {}
    for i, _ in avail_d:
        for j in range(shov):
            x[i, j] = solver.IntVar(0, 1, f'x_{i}_{j}')
    
    for i, _ in avail_d:
        solver.Add(solver.Sum([x[i, j] for j in range(shov)]) <= 1)
    
    for j in range(shov):
        solver.Add(solver.Sum([x[i, j] * dumper_caps[i] * eff for i, _ in avail_d]) <= shovel_caps[j] * eff)
    
    obj = solver.Objective()
    for i, d_cap in avail_d:
        for j in range(shov):
            obj.SetCoefficient(x[i, j], float(d_cap))
    obj.SetMaximization()
    solver.Solve()
    
    assignments = []
    for i, d_cap in avail_d:
        for j in range(shov):
            if x[i, j].solution_value() > 0.5:
                assignments.append({
                    'Dumper': f'Dumper {i+1}',
                    'Assigned Shovel': f'Shovel {j+1}',
                    'Capacity (TPH)': f'{d_cap:.1f}',
                    'Daily Output (TPD)': f'{d_cap * 16:.0f}'
                })
    
    if assignments:
        d1, d2 = st.columns([2, 1])
        with d1:
            st.dataframe(pd.DataFrame(assignments), use_container_width=True, hide_index=True)
        with d2:
            st.metric("Dumpers Working", f"{len(assignments)} / {dump}")
            st.metric("Dumpers Down", f"{dump - len(avail_d)}")
            st.metric("Shovels Active", f"{shov}")
    else:
        st.warning("No dumpers could be assigned. Equipment availability too low!")

# ================= FINANCIAL IMPACT =================
st.subheader("💰 Financial Impact")
mn_price = 12000  # ₹/ton approx

daily_loss_rs = shortfall * mn_price
monthly_loss_rs = daily_loss_rs * 25
annual_loss_rs = monthly_loss_rs * 12

f1, f2, f3 = st.columns(3)
f1.metric("Daily Loss", f"₹{daily_loss_rs/100000:.1f} Lakh")
f2.metric("Monthly Loss", f"₹{monthly_loss_rs/10000000:.2f} Cr")
f3.metric("Annual Loss", f"₹{annual_loss_rs/10000000:.1f} Cr")

st.caption("*Estimated at ₹12,000/ton manganese ore. Actual prices vary by grade (30-48% Mn content).*")

# ================= RECOMMENDATIONS =================
st.subheader("💡 Recommendations")

if weather_loss > equip_loss and weather_loss > road_loss:
    st.info("🌧️ **Weather is the #1 bottleneck.** Defer non-critical operations during heavy rain. Invest in covered haul roads and drainage systems.")
elif equip_loss > road_loss:
    st.info("🔧 **Equipment downtime is the #1 bottleneck.** Schedule preventive maintenance during dry season. Keep standby dumpers ready for monsoon months.")
elif road_loss > 0:
    st.info("🛤️ **Road condition is the #1 bottleneck.** Grade haul roads regularly. Use laterite/gravel surfacing for wet-weather resilience.")
else:
    st.success("✅ Operations are running near optimal. Consider increasing fleet size to exceed planned targets.")
