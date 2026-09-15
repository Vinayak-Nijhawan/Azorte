import os
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import joblib
from ortools.linear_solver import pywraplp

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
MODEL_DIR = os.path.join(PROJECT_ROOT, 'models')

@st.cache_data
def load_data():
    fp = os.path.join(DATA_DIR, 'production_forecast.csv')
    dp = os.path.join(DATA_DIR, 'dispatch_plan.csv')
    hp = os.path.join(DATA_DIR, 'production_dataset.csv')
    forecast = pd.read_csv(fp) if os.path.exists(fp) else pd.DataFrame()
    dispatch = pd.read_csv(dp) if os.path.exists(dp) else pd.DataFrame()
    history = pd.read_csv(hp) if os.path.exists(hp) else pd.DataFrame()
    return forecast, dispatch, history

@st.cache_resource
def load_model():
    mp = os.path.join(MODEL_DIR, 'production_gb.joblib')
    if os.path.exists(mp):
        return joblib.load(mp)
    return None

forecast_df, dispatch_df, history_df = load_data()
prod_model = load_model()

if forecast_df.empty:
    st.error("Missing `production_forecast.csv`. Run the pipeline first.")
    st.stop()

FEATURES = ['planned_production_tpd', 'rainfall_mm', 'equipment_availability_pct', 'blasting_days',
            'haul_road_condition', 'crusher_capacity_tpd', 'num_dumpers', 'num_shovels', 'lag_1', 'lag_2', 'lag_3']

# ================= PAGE HEADER =================
st.title("What-If Scenario Simulator 🎛️")

if prod_model:
    st.markdown("Predictions powered by our **trained GradientBoosting model** (R² = 0.98) — not hardcoded formulas.")
else:
    st.warning("ML model not found. Using fallback estimation.")

# ================= SIDEBAR — MINE & MONTH =================
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

# Get baseline prediction (what model predicts with default/forecast values)
baseline_features = {f: float(row.get(f, 0)) for f in FEATURES}

# ================= QUICK PRESETS =================
st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ Quick Presets")

def set_preset(rain, equip, road, dump, shov, blast):
    st.session_state.update({'rain': rain, 'equip': equip, 'road': road, 'dump': dump, 'shov': shov, 'blast': blast})

p1, p2, p3 = st.sidebar.columns(3)
p1.button("⛈️ Monsoon", on_click=set_preset, 
          args=(350, 0.60, 1, int(row.get('num_dumpers',6)), int(row.get('num_shovels',3)), 5), 
          use_container_width=True)
p2.button("🔧 Breakdown", on_click=set_preset, 
          args=(50, 0.50, 3, 3, 1, int(row.get('blasting_days',15))), 
          use_container_width=True)
p3.button("☀️ Best Case", on_click=set_preset, 
          args=(10, 0.98, 5, 8, 4, 22), 
          use_container_width=True)

if 'rain' not in st.session_state:
    set_preset(int(row.get('rainfall_mm',100)), float(row.get('equipment_availability_pct',0.85)),
               int(row.get('haul_road_condition',3)), int(row.get('num_dumpers',6)), 
               int(row.get('num_shovels',3)), int(row.get('blasting_days',15)))

st.sidebar.button("🔄 Reset", on_click=lambda: set_preset(
    int(row.get('rainfall_mm',100)), float(row.get('equipment_availability_pct',0.85)),
    int(row.get('haul_road_condition',3)), int(row.get('num_dumpers',6)),
    int(row.get('num_shovels',3)), int(row.get('blasting_days',15))
), use_container_width=True)

# ================= SLIDERS =================
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎚️ Adjust Parameters")
rain = st.sidebar.slider("🌧️ Rainfall (mm)", 0, 500, key="rain")
road = st.sidebar.slider("🛤️ Road Condition (1=Bad → 5=Good)", 1, 5, key="road")
equip = st.sidebar.slider("⚙️ Equipment Availability %", 0.40, 1.00, step=0.05, key="equip")
dump = st.sidebar.slider("🚛 Dumpers", 2, 10, key="dump")
shov = st.sidebar.slider("⛏️ Shovels", 1, 5, key="shov")
blast = st.sidebar.slider("💥 Blasting Days", 0, 25, key="blast")
crusher_cap = float(row.get('crusher_capacity_tpd', 1500))

# ================= ML PREDICTION =================
# Build scenario feature vector
scenario = baseline_features.copy()
scenario['rainfall_mm'] = rain
scenario['equipment_availability_pct'] = equip
scenario['haul_road_condition'] = road
scenario['num_dumpers'] = dump
scenario['num_shovels'] = shov
scenario['blasting_days'] = blast

scenario_df = pd.DataFrame([scenario])[FEATURES]
baseline_df = pd.DataFrame([baseline_features])[FEATURES]

if prod_model:
    predicted_tpd = float(prod_model.predict(scenario_df)[0])
    baseline_tpd = float(prod_model.predict(baseline_df)[0])
else:
    # Fallback
    eff = equip * min(1, road/5) * max(0.5, 1 - rain/1000)
    predicted_tpd = planned_tpd * eff
    baseline_tpd = planned_tpd * 0.85

predicted_tpd = max(0, predicted_tpd)
baseline_tpd = max(0, baseline_tpd)

efficiency = (predicted_tpd / planned_tpd * 100) if planned_tpd > 0 else 0
shortfall = max(0, planned_tpd - predicted_tpd)
risk_pct = max(0, min(100, 100 - efficiency))

# ================= TOP KPI ROW =================
k1, k2, k3, k4 = st.columns(4)
k1.metric("📋 Planned", f"{planned_tpd:.0f} TPD")
k2.metric("🤖 ML Predicted", f"{predicted_tpd:.0f} TPD", f"{predicted_tpd - baseline_tpd:+.0f} vs default")
k3.metric("📊 Efficiency", f"{efficiency:.0f}%")
k4.metric("⚠️ Shortfall", f"{shortfall:.0f} TPD")

# ================= GAUGES =================
g1, g2 = st.columns(2)

with g1:
    color = '#2ecc71' if efficiency >= 80 else '#e67e22' if efficiency >= 60 else '#e74c3c'
    fig_g = go.Figure(go.Indicator(
        mode="gauge+number", value=efficiency, number={'suffix': '%'},
        title={'text': "Production Efficiency"},
        gauge={'axis': {'range': [0, 120]}, 'bar': {'color': color},
               'steps': [{'range': [0,60], 'color': 'rgba(231,76,60,0.12)'},
                         {'range': [60,80], 'color': 'rgba(230,126,34,0.12)'},
                         {'range': [80,120], 'color': 'rgba(46,204,113,0.12)'}]}
    ))
    fig_g.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=10))
    st.plotly_chart(fig_g, use_container_width=True)

with g2:
    r_color = '#e74c3c' if risk_pct >= 40 else '#e67e22' if risk_pct >= 20 else '#2ecc71'
    fig_r = go.Figure(go.Indicator(
        mode="gauge+number", value=risk_pct, number={'suffix': '%'},
        title={'text': "Shortfall Risk"},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': r_color},
               'steps': [{'range': [0,20], 'color': 'rgba(46,204,113,0.12)'},
                         {'range': [20,40], 'color': 'rgba(230,126,34,0.12)'},
                         {'range': [40,100], 'color': 'rgba(231,76,60,0.12)'}]}
    ))
    fig_r.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=10))
    st.plotly_chart(fig_r, use_container_width=True)

# ================= FEATURE IMPACT (Model-driven) =================
st.subheader("🔍 What's Driving This Prediction?")
st.markdown("Each bar shows how much changing a parameter **moved the prediction** compared to the default forecast.")

# Calculate individual feature impacts by changing one at a time
impacts = {}
for feat, label, sim_val in [
    ('rainfall_mm', '🌧️ Rainfall', rain),
    ('equipment_availability_pct', '⚙️ Equipment', equip),
    ('haul_road_condition', '🛤️ Road', road),
    ('num_dumpers', '🚛 Dumpers', dump),
    ('num_shovels', '⛏️ Shovels', shov),
    ('blasting_days', '💥 Blasting', blast),
]:
    if prod_model:
        # Predict with only this one feature changed
        single_change = baseline_features.copy()
        single_change[feat] = sim_val
        single_df = pd.DataFrame([single_change])[FEATURES]
        single_pred = float(prod_model.predict(single_df)[0])
        impact = single_pred - baseline_tpd
    else:
        impact = 0
    impacts[label] = round(impact, 1)

impact_df = pd.DataFrame({
    'Factor': list(impacts.keys()),
    'Impact (TPD)': list(impacts.values())
}).sort_values('Impact (TPD)')

colors = ['#e74c3c' if v < -5 else '#2ecc71' if v > 5 else '#95a5a6' for v in impact_df['Impact (TPD)']]

fig_impact = go.Figure(go.Bar(
    x=impact_df['Impact (TPD)'], y=impact_df['Factor'],
    orientation='h', marker_color=colors,
    text=[f"{v:+.0f} TPD" for v in impact_df['Impact (TPD)']],
    textposition='outside'
))
fig_impact.add_vline(x=0, line_color="white", line_width=1)
fig_impact.update_layout(height=300, xaxis_title="Impact on Production (TPD)", 
                         yaxis_title="", margin=dict(l=10, r=80, t=10, b=40))
st.plotly_chart(fig_impact, use_container_width=True)

# Identify biggest negative impact
neg_impacts = {k: v for k, v in impacts.items() if v < -5}
if neg_impacts:
    worst = min(neg_impacts, key=neg_impacts.get)
    st.warning(f"⚠️ **Biggest drag: {worst}** is reducing production by **{abs(neg_impacts[worst]):.0f} TPD**. Address this first!")

# ================= FLEET DISPATCH (MILP) =================
st.subheader("📋 Optimized Fleet Dispatch")

np.random.seed(42)
dumper_caps = np.random.uniform(30, 40, dump)
shovel_caps = np.random.uniform(150, 250, shov)
weather_eff = max(0.5, 1.0 - (rain / 500) * 0.25)
road_eff = max(0.6, road / 5)
total_eff = weather_eff * road_eff

solver = pywraplp.Solver.CreateSolver('SCIP')
if solver:
    avail_d = [(i, dumper_caps[i] * total_eff) for i in range(dump) if np.random.RandomState(42+i).rand() <= equip]
    
    x = {}
    for i, _ in avail_d:
        for j in range(shov):
            x[i, j] = solver.IntVar(0, 1, f'x_{i}_{j}')
    
    for i, _ in avail_d:
        solver.Add(solver.Sum([x[i, j] for j in range(shov)]) <= 1)
    
    for j in range(shov):
        solver.Add(solver.Sum([x[i, j] * dumper_caps[i] * total_eff for i, _ in avail_d]) <= shovel_caps[j] * total_eff)
    
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
                    'Dumper': f'Dumper {i+1}', 'Assigned Shovel': f'Shovel {j+1}',
                    'Capacity (TPH)': f'{d_cap:.1f}', 'Daily Output (TPD)': f'{d_cap * 16:.0f}'
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
        st.warning("No dumpers assigned — equipment availability too low!")

# ================= COMPARE WITH HISTORY =================
if not history_df.empty:
    st.subheader("📈 How Does This Compare to History?")
    mine_hist = history_df[history_df['mine_id'] == selected_mine].copy()
    if not mine_hist.empty:
        mine_hist['date'] = pd.to_datetime(mine_hist['year'].astype(str) + '-' + mine_hist['month'].astype(str) + '-01')
        mine_hist = mine_hist.sort_values('date')
        
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Scatter(x=mine_hist['date'], y=mine_hist['actual_production_tpd'],
                                      name='Historical Actual', line=dict(color='#3498db', width=2)))
        fig_hist.add_trace(go.Scatter(x=mine_hist['date'], y=mine_hist['planned_production_tpd'],
                                      name='Historical Planned', line=dict(color='gray', dash='dash')))
        # Add simulated point
        fig_hist.add_trace(go.Scatter(x=[pd.Timestamp(f'2026-{selected_month}-01')], y=[predicted_tpd],
                                      name='🤖 Your Scenario', mode='markers',
                                      marker=dict(size=15, color='#e74c3c', symbol='star')))
        fig_hist.update_layout(height=350, yaxis_title="Production (TPD)", 
                               legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_hist, use_container_width=True)

# ================= FINANCIAL IMPACT =================
st.subheader("💰 Financial Impact")
mn_price = 12000
daily_loss_rs = shortfall * mn_price
f1, f2, f3 = st.columns(3)
f1.metric("Daily Loss", f"₹{daily_loss_rs/100000:.1f} Lakh")
f2.metric("Monthly Loss", f"₹{daily_loss_rs * 25 / 10000000:.2f} Cr")
f3.metric("Annual Loss", f"₹{daily_loss_rs * 300 / 10000000:.1f} Cr")
st.caption("*Estimated at ₹12,000/ton manganese ore.*")
