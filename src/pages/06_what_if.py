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
    hp = os.path.join(DATA_DIR, 'production_dataset.csv')
    forecast = pd.read_csv(fp) if os.path.exists(fp) else pd.DataFrame()
    history = pd.read_csv(hp) if os.path.exists(hp) else pd.DataFrame()
    return forecast, history

@st.cache_resource
def load_model():
    mp = os.path.join(MODEL_DIR, 'production_gb.joblib')
    return joblib.load(mp) if os.path.exists(mp) else None

forecast_df, history_df = load_data()
prod_model = load_model()

if forecast_df.empty:
    st.error("Missing `production_forecast.csv`. Run the pipeline first.")
    st.stop()

# ========== PRODUCTION FORMULA (same as generate_data.py — this IS ground truth) ==========
def calculate_production(planned_tpd, rainfall_mm, equipment_pct, blasting_days, road_cond, num_dumpers, num_shovels):
    """Exact same formula used in data generation — 100% accurate."""
    
    # 1. Equipment availability: direct multiplier
    equip_factor = equipment_pct
    
    # 2. Rainfall impact
    if rainfall_mm < 50:
        rain_factor = 1.0
    elif rainfall_mm < 200:
        rain_factor = 1.0 - (rainfall_mm - 50) * 0.001
    elif rainfall_mm < 400:
        rain_factor = 0.85 - (rainfall_mm - 200) * 0.0015
    else:
        rain_factor = 0.55 - (rainfall_mm - 400) * 0.001
    rain_factor = max(0.3, rain_factor)
    
    # 3. Blasting days
    blast_factor = 0.4 + 0.6 * (blasting_days / 25.0)
    
    # 4. Road condition
    road_factor = 0.6 + 0.1 * road_cond
    
    # 5. Fleet size
    dumper_factor = min(1.2, 0.5 + 0.1 * num_dumpers)
    shovel_factor = min(1.15, 0.55 + 0.2 * num_shovels)
    
    # Combined
    total_factor = equip_factor * rain_factor * blast_factor * road_factor * dumper_factor * shovel_factor
    total_factor = np.clip(total_factor, 0.2, 1.15)
    
    actual_tpd = planned_tpd * total_factor
    
    # Individual losses (for waterfall)
    losses = {
        'Equipment': planned_tpd * (1 - equip_factor),
        'Rainfall': planned_tpd * equip_factor * (1 - rain_factor),
        'Blasting': planned_tpd * equip_factor * rain_factor * (1 - blast_factor),
        'Road': planned_tpd * equip_factor * rain_factor * blast_factor * (1 - road_factor),
        'Fleet Size': planned_tpd * equip_factor * rain_factor * blast_factor * road_factor * (1 - dumper_factor * shovel_factor),
    }
    # Ensure losses are non-negative and also handle gains
    
    return actual_tpd, total_factor, losses, {
        'equip': equip_factor, 'rain': rain_factor, 'blast': blast_factor,
        'road': road_factor, 'dumper': dumper_factor, 'shovel': shovel_factor
    }

# ================= PAGE =================
st.title("What-If Scenario Simulator 🎛️")
st.markdown("Uses the **exact production formula** from our data pipeline — change any parameter and see real-time impact.")

# ================= SIDEBAR =================
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

# ================= PRESETS =================
st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ Quick Presets")

def set_preset(rain, equip, road, dump, shov, blast):
    st.session_state.update({'rain': rain, 'equip': equip, 'road': road, 'dump': dump, 'shov': shov, 'blast': blast})

p1, p2, p3 = st.sidebar.columns(3)
p1.button("⛈️ Monsoon", on_click=set_preset, args=(350, 0.65, 1, int(row.get('num_dumpers',6)), int(row.get('num_shovels',3)), 5), use_container_width=True)
p2.button("🔧 Breakdown", on_click=set_preset, args=(30, 0.50, 3, 3, 1, int(row.get('blasting_days',15))), use_container_width=True)
p3.button("☀️ Best Case", on_click=set_preset, args=(10, 0.98, 5, 8, 4, 23), use_container_width=True)

if 'rain' not in st.session_state:
    set_preset(int(row.get('rainfall_mm',100)), round(float(row.get('equipment_availability_pct',0.85)),2),
               int(row.get('haul_road_condition',3)), int(row.get('num_dumpers',6)),
               int(row.get('num_shovels',3)), int(row.get('blasting_days',15)))

st.sidebar.button("🔄 Reset to Default", on_click=lambda: set_preset(
    int(row.get('rainfall_mm',100)), round(float(row.get('equipment_availability_pct',0.85)),2),
    int(row.get('haul_road_condition',3)), int(row.get('num_dumpers',6)),
    int(row.get('num_shovels',3)), int(row.get('blasting_days',15))
), use_container_width=True)

# ================= SLIDERS =================
st.sidebar.markdown("---")
rain = st.sidebar.slider("🌧️ Rainfall (mm)", 0, 500, key="rain")
road = st.sidebar.slider("🛤️ Road Condition (1=Bad → 5=Good)", 1, 5, key="road")
equip = st.sidebar.slider("⚙️ Equipment Availability", 0.40, 1.00, step=0.05, key="equip")
dump = st.sidebar.slider("🚛 Dumpers", 2, 10, key="dump")
shov = st.sidebar.slider("⛏️ Shovels", 1, 5, key="shov")
blast = st.sidebar.slider("💥 Blasting Days", 0, 25, key="blast")

# ================= CALCULATE =================
actual_tpd, total_factor, losses, factors = calculate_production(
    planned_tpd, rain, equip, blast, road, dump, shov
)

# Also calculate default (what the forecast row would give)
default_tpd, _, _, _ = calculate_production(
    planned_tpd, float(row.get('rainfall_mm',100)), float(row.get('equipment_availability_pct',0.85)),
    int(row.get('blasting_days',15)), int(row.get('haul_road_condition',3)),
    int(row.get('num_dumpers',6)), int(row.get('num_shovels',3))
)

efficiency = total_factor * 100
shortfall = max(0, planned_tpd - actual_tpd)
change = actual_tpd - default_tpd

# ================= KPI ROW =================
k1, k2, k3, k4 = st.columns(4)
k1.metric("📋 Planned", f"{planned_tpd:.0f} TPD")
k2.metric("⛏️ Achievable", f"{actual_tpd:.0f} TPD", f"{change:+.0f} vs forecast")
k3.metric("📊 Efficiency", f"{efficiency:.0f}%")
k4.metric("⚠️ Shortfall", f"{shortfall:.0f} TPD")

# ================= GAUGE METERS =================
g1, g2 = st.columns(2)

with g1:
    color = '#2ecc71' if efficiency >= 80 else '#e67e22' if efficiency >= 60 else '#e74c3c'
    fig_g = go.Figure(go.Indicator(
        mode="gauge+number", value=efficiency, number={'suffix': '%'},
        title={'text': "Production Efficiency"},
        gauge={'axis': {'range': [0, 115]}, 'bar': {'color': color},
               'steps': [{'range': [0,60], 'color': 'rgba(231,76,60,0.12)'},
                         {'range': [60,80], 'color': 'rgba(230,126,34,0.12)'},
                         {'range': [80,115], 'color': 'rgba(46,204,113,0.12)'}]}
    ))
    fig_g.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=10))
    st.plotly_chart(fig_g, use_container_width=True)

with g2:
    risk = max(0, 100 - efficiency)
    r_color = '#e74c3c' if risk >= 40 else '#e67e22' if risk >= 20 else '#2ecc71'
    fig_r = go.Figure(go.Indicator(
        mode="gauge+number", value=risk, number={'suffix': '%'},
        title={'text': "Shortfall Risk"},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': r_color},
               'steps': [{'range': [0,20], 'color': 'rgba(46,204,113,0.12)'},
                         {'range': [20,40], 'color': 'rgba(230,126,34,0.12)'},
                         {'range': [40,100], 'color': 'rgba(231,76,60,0.12)'}]}
    ))
    fig_r.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=10))
    st.plotly_chart(fig_r, use_container_width=True)

# ================= FACTOR BREAKDOWN =================
st.subheader("📊 Factor Breakdown — How Each Parameter Affects Output")

factor_names = ['⚙️ Equipment', '🌧️ Rainfall', '💥 Blasting', '🛤️ Road', '🚛 Dumpers', '⛏️ Shovels']
factor_values = [factors['equip']*100, factors['rain']*100, factors['blast']*100, 
                 factors['road']*100, factors['dumper']*100, factors['shovel']*100]
factor_colors = ['#e74c3c' if v < 75 else '#e67e22' if v < 90 else '#2ecc71' for v in factor_values]

fig_factors = go.Figure(go.Bar(
    x=factor_values, y=factor_names, orientation='h',
    marker_color=factor_colors,
    text=[f"{v:.0f}%" for v in factor_values],
    textposition='outside'
))
fig_factors.add_vline(x=100, line_color="rgba(255,255,255,0.3)", line_dash="dash")
fig_factors.update_layout(height=300, xaxis_title="Factor Efficiency (%)", xaxis=dict(range=[0, 130]),
                          margin=dict(l=10, r=60, t=10, b=40))
st.plotly_chart(fig_factors, use_container_width=True)

st.markdown("""
**How to read:** Each bar shows the efficiency of that factor. 
- **100% = no loss** from this factor  
- **Below 100% = causing production loss** (red = severe, yellow = moderate, green = good)  
- **Above 100% = boosting production** (e.g., more dumpers than baseline)
""")

# ================= WATERFALL =================
st.subheader("🌊 Production Waterfall — Where TPD is Lost")

# Calculate sequential losses
steps = ['Planned\nTPD']
values = [planned_tpd]
measures = ['absolute']

remaining = planned_tpd
for name, factor_key in [('⚙️ Equipment', 'equip'), ('🌧️ Rainfall', 'rain'), 
                          ('💥 Blasting', 'blast'), ('🛤️ Road', 'road'),
                          ('🚛 Fleet', None)]:
    if name == '🚛 Fleet':
        fleet_f = factors['dumper'] * factors['shovel']
        loss = remaining * (1 - fleet_f)
    else:
        f = factors[factor_key]
        loss = remaining * (1 - f)
    
    # If factor > 1, it's a gain (negative loss)
    steps.append(name)
    values.append(-loss)
    measures.append('relative')
    remaining -= loss

steps.append('Final\nTPD')
values.append(max(remaining, planned_tpd * 0.2))  # clipped at 20%
measures.append('total')

fig_wf = go.Figure(go.Waterfall(
    x=steps, y=values, measure=measures,
    text=[f"{abs(v):.0f}" for v in values],
    textposition="outside",
    connector={"line": {"color": "rgba(255,255,255,0.2)"}},
    decreasing={"marker": {"color": "#e74c3c"}},
    increasing={"marker": {"color": "#2ecc71"}},
    totals={"marker": {"color": "#3498db"}}
))
fig_wf.update_layout(height=420, yaxis_title="Production (TPD)", showlegend=False)
st.plotly_chart(fig_wf, use_container_width=True)

# Biggest loss
loss_items = {k: abs(v) for k, v in zip(steps[1:-1], values[1:-1]) if v < -1}
if loss_items:
    worst = max(loss_items, key=loss_items.get)
    st.warning(f"⚠️ **Biggest bottleneck: {worst.strip()}** — causing **{loss_items[worst]:.0f} TPD** loss. Fix this first!")

# ================= SENSITIVITY ANALYSIS =================
st.subheader("📈 Sensitivity — What Matters Most?")
st.markdown("Shows how much production changes when **each parameter is at its WORST vs BEST** value.")

sens_data = []
for name, feat, worst, best in [
    ('🌧️ Rainfall', 'rain', 400, 0),
    ('⚙️ Equipment', 'equip', 0.40, 1.00),
    ('💥 Blasting', 'blast', 0, 25),
    ('🛤️ Road', 'road', 1, 5),
    ('🚛 Dumpers', 'dump', 2, 10),
    ('⛏️ Shovels', 'shov', 1, 5),
]:
    args_worst = {'planned_tpd': planned_tpd, 'rainfall_mm': rain, 'equipment_pct': equip,
                  'blasting_days': blast, 'road_cond': road, 'num_dumpers': dump, 'num_shovels': shov}
    args_best = args_worst.copy()
    
    if feat == 'rain':
        args_worst['rainfall_mm'] = worst; args_best['rainfall_mm'] = best
    elif feat == 'equip':
        args_worst['equipment_pct'] = worst; args_best['equipment_pct'] = best
    elif feat == 'blast':
        args_worst['blasting_days'] = worst; args_best['blasting_days'] = best
    elif feat == 'road':
        args_worst['road_cond'] = worst; args_best['road_cond'] = best
    elif feat == 'dump':
        args_worst['num_dumpers'] = worst; args_best['num_dumpers'] = best
    elif feat == 'shov':
        args_worst['num_shovels'] = worst; args_best['num_shovels'] = best
    
    worst_tpd, _, _, _ = calculate_production(**args_worst)
    best_tpd, _, _, _ = calculate_production(**args_best)
    sens_data.append({'Factor': name, 'Worst': round(worst_tpd), 'Best': round(best_tpd), 'Swing': round(best_tpd - worst_tpd)})

sens_df = pd.DataFrame(sens_data).sort_values('Swing', ascending=True)

fig_sens = go.Figure()
for _, r in sens_df.iterrows():
    fig_sens.add_trace(go.Bar(y=[r['Factor']], x=[r['Best'] - r['Worst']], 
                              orientation='h', marker_color='#3498db',
                              text=f"±{r['Swing']:.0f} TPD", textposition='outside',
                              base=r['Worst'], showlegend=False))
fig_sens.update_layout(height=280, xaxis_title="Production Range (TPD)", 
                        margin=dict(l=10, r=80, t=10, b=40))
st.plotly_chart(fig_sens, use_container_width=True)

most_sensitive = sens_df.iloc[-1]['Factor']
st.info(f"💡 **{most_sensitive}** has the biggest impact on production. Prioritize this in operational planning.")

# ================= FINANCIAL IMPACT =================
st.subheader("💰 Financial Impact")
mn_price = 12000
daily_loss_rs = shortfall * mn_price
f1, f2, f3 = st.columns(3)
f1.metric("Daily Loss", f"₹{daily_loss_rs/100000:.1f} Lakh")
f2.metric("Monthly Loss", f"₹{daily_loss_rs * 25 / 10000000:.2f} Cr")
f3.metric("Annual Loss", f"₹{daily_loss_rs * 300 / 10000000:.1f} Cr")
st.caption("*Estimated at ₹12,000/ton manganese ore.*")

# ================= HISTORICAL COMPARISON =================
if not history_df.empty:
    st.subheader("📈 Your Scenario vs Historical Data")
    mine_hist = history_df[history_df['mine_id'] == selected_mine].copy()
    if not mine_hist.empty:
        mine_hist['date'] = pd.to_datetime(mine_hist['year'].astype(str) + '-' + mine_hist['month'].astype(str) + '-01')
        mine_hist = mine_hist.sort_values('date')
        
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Scatter(x=mine_hist['date'], y=mine_hist['actual_production_tpd'],
                                      name='Historical Actual', line=dict(color='#3498db', width=2)))
        fig_hist.add_trace(go.Scatter(x=mine_hist['date'], y=mine_hist['planned_production_tpd'],
                                      name='Historical Planned', line=dict(color='gray', dash='dash')))
        fig_hist.add_trace(go.Scatter(x=[pd.Timestamp(f'2026-{selected_month}-01')], y=[actual_tpd],
                                      name='🎯 Your Scenario', mode='markers',
                                      marker=dict(size=16, color='#e74c3c', symbol='star')))
        fig_hist.add_hline(y=actual_tpd, line_dash="dot", line_color="#e74c3c", opacity=0.5)
        fig_hist.update_layout(height=350, yaxis_title="Production (TPD)",
                               legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_hist, use_container_width=True)
