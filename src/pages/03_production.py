import streamlit as st

import sys
import os
# Add the project root to sys.path so we can import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils import load_css, inject_kpi_animations, inject_volcano_animations
load_css()

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os

st.markdown("""
<style>
.geo-kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 24px; }
.geo-kpi-card { background: rgba(17,24,39,0.7); backdrop-filter: blur(12px); border: 1px solid rgba(30,41,59,0.8); border-radius: 16px; padding: 22px 24px; display: flex; flex-direction: column; gap: 10px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3); transition: all 0.2s ease; }
.geo-kpi-card:hover { border-color: rgba(59,130,246,0.5); transform: translateY(-2px); }
.geo-kpi-header { display: flex; justify-content: space-between; align-items: center; }
.geo-kpi-title { color: #94A3B8; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
.geo-kpi-icon { width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; }
.geo-icon-blue   { background: rgba(59,130,246,0.1); color: #3B82F6; }
.geo-icon-green  { background: rgba(16,185,129,0.1); color: #10B981; }
.geo-icon-purple { background: rgba(139,92,246,0.1); color: #8B5CF6; }
.geo-icon-amber  { background: rgba(245,158,11,0.1); color: #F59E0B; }
.geo-icon-red    { background: rgba(239,68,68,0.1);  color: #EF4444; }
.geo-kpi-value { font-size: 2.2rem; font-weight: 700; color: #F8FAFC; line-height: 1.2; }
.geo-kpi-footer { display: flex; align-items: center; gap: 8px; margin-top: 2px; }
.geo-kpi-subtext { font-size: 0.8rem; color: #64748B; }
.geo-trend-up     { background: rgba(16,185,129,0.15); color: #34D399; padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }
.geo-trend-down   { background: rgba(244,63,94,0.15);  color: #FB7185; padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }
.geo-trend-neutral{ background: rgba(148,163,184,0.15);color: #94A3B8; padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }
.geo-trend-amber  { background: rgba(245,158,11,0.15); color: #FCD34D; padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }
</style>
<div class="fd-header">
    <div class="fd-header-left">
        <h1>📈 MineFlow Optimizer - Production Forecast</h1>
        <div class="fd-subtitle">Predictive Output &amp; Risk Mitigation · MOIL Manganese Operations</div>
    </div>
    <div class="fd-header-right">
        <div class="fd-tag">⛏️ Production</div>
        <div class="fd-live"><div class="fd-live-dot"></div> OPERATIONAL</div>
    </div>
</div>
""", unsafe_allow_html=True)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

@st.cache_data
def load_production_data():
    prod_path = os.path.join(DATA_DIR, 'production_dataset_real.csv')
    forecast_path = os.path.join(DATA_DIR, 'production_forecast_real.csv')
    
    df_prod = pd.read_csv(prod_path, comment='#') if os.path.exists(prod_path) else pd.DataFrame()
    df_forecast = pd.read_csv(forecast_path, comment='#') if os.path.exists(forecast_path) else pd.DataFrame()
    
    return df_prod, df_forecast

df_prod, df_forecast = load_production_data()

if df_prod.empty:
    st.warning("Production dataset not found. Run generate_data.py first.")
    st.stop()

# ================= SIDEBAR =================
mines = df_prod['mine_id'].unique().tolist()
selected_mine = st.sidebar.selectbox("Select Mine", mines)

mine_data = df_prod[df_prod['mine_id'] == selected_mine].copy()
mine_data['date'] = pd.to_datetime(mine_data['year'].astype(str) + '-' + mine_data['month'].astype(str) + '-01')
mine_data = mine_data.sort_values('date')

# Forecast data for selected mine
forecast_data = pd.DataFrame()
if not df_forecast.empty:
    forecast_data = df_forecast[df_forecast['mine_id'] == selected_mine].copy()
    if not forecast_data.empty:
        forecast_data['date'] = pd.to_datetime(forecast_data['year'].astype(str) + '-' + forecast_data['month'].astype(str) + '-01')
        forecast_data = forecast_data.sort_values('date')

# ================= KPI METRICS =================
avg_planned = mine_data['planned_production_tpd__DERIVED'].mean()
avg_actual = mine_data['actual_production_tpd__DERIVED'].mean()
efficiency = (avg_actual / avg_planned * 100) if avg_planned > 0 else 0
high_risk_months = (mine_data['shortfall_risk'] == 'High').sum()

st.markdown(f"""
<div class="geo-kpi-grid" style="grid-template-columns: repeat(4,1fr);">
    <div class="geo-kpi-card">
        <div class="geo-kpi-header"><div class="geo-kpi-title">Avg Planned</div><div class="geo-kpi-icon geo-icon-blue">📋</div></div>
        <div class="geo-kpi-value">{avg_planned:.0f} <span style="font-size:1.1rem;color:#94A3B8;">TPD</span></div>
        <div class="geo-kpi-footer"><span class="geo-trend-neutral">Target Output</span></div>
    </div>
    <div class="geo-kpi-card">
        <div class="geo-kpi-header"><div class="geo-kpi-title">Avg Actual</div><div class="geo-kpi-icon geo-icon-green">⛏️</div></div>
        <div class="geo-kpi-value">{avg_actual:.0f} <span style="font-size:1.1rem;color:#94A3B8;">TPD</span></div>
        <div class="geo-kpi-footer"><span class="{'geo-trend-up' if avg_actual >= avg_planned else 'geo-trend-down'}">{'↑ On Target' if avg_actual >= avg_planned else '↓ Below Plan'}</span></div>
    </div>
    <div class="geo-kpi-card">
        <div class="geo-kpi-header"><div class="geo-kpi-title">Efficiency</div><div class="geo-kpi-icon geo-icon-purple">📊</div></div>
        <div class="geo-kpi-value">{efficiency:.1f}<span style="font-size:1.5rem;color:#94A3B8;">%</span></div>
        <div class="geo-kpi-footer"><span class="{'geo-trend-up' if efficiency >= 90 else 'geo-trend-amber' if efficiency >= 75 else 'geo-trend-down'}">{'Optimal' if efficiency >= 90 else 'Moderate' if efficiency >= 75 else 'Low'}</span></div>
    </div>
    <div class="geo-kpi-card">
        <div class="geo-kpi-header"><div class="geo-kpi-title">High Risk Months</div><div class="geo-kpi-icon geo-icon-amber">⚠️</div></div>
        <div class="geo-kpi-value">{high_risk_months} <span style="font-size:1.1rem;color:#94A3B8;">/ {len(mine_data)}</span></div>
        <div class="geo-kpi-footer"><span class="{'geo-trend-down' if high_risk_months > 3 else 'geo-trend-amber' if high_risk_months > 0 else 'geo-trend-up'}">{'Critical' if high_risk_months > 3 else 'Moderate Risk' if high_risk_months > 0 else 'All Clear'}</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

# ================= PRODUCTION TIMELINE =================
st.subheader(f"Production Timeline — {selected_mine}")

fig = go.Figure()

# Historical: Planned (dashed blue)
fig.add_trace(go.Scatter(
    x=mine_data['date'], y=mine_data['planned_production_tpd__DERIVED'],
    name='Planned', line=dict(color='#3498db', dash='dash', width=2),
    hovertemplate='%{x|%b %Y}<br>Planned: %{y:.0f} TPD<extra></extra>'
))

# Historical: Actual (solid blue)
fig.add_trace(go.Scatter(
    x=mine_data['date'], y=mine_data['actual_production_tpd__DERIVED'],
    name='Actual', line=dict(color='#2ecc71', width=2.5),
    fill='tonexty', fillcolor='rgba(46,204,113,0.1)',
    hovertemplate='%{x|%b %Y}<br>Actual: %{y:.0f} TPD<extra></extra>'
))

# Forecast: Predicted (dashed orange)
if not forecast_data.empty and 'predicted_production_tpd__DERIVED' in forecast_data.columns:
    fig.add_trace(go.Scatter(
        x=forecast_data['date'], y=forecast_data['planned_production_tpd__DERIVED'],
        name='Planned (2026)', line=dict(color='#3498db', dash='dot', width=1.5),
        hovertemplate='%{x|%b %Y}<br>Planned: %{y:.0f} TPD<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        x=forecast_data['date'], y=forecast_data['predicted_production_tpd__DERIVED'],
        name='ML Predicted', line=dict(color='#e67e22', width=2.5, dash='dash'),
        hovertemplate='%{x|%b %Y}<br>Predicted: %{y:.0f} TPD<extra></extra>'
    ))

fig.update_layout(
    xaxis_title="Date", yaxis_title="Production (TPD)",
    height=450, hovermode='x unified',
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=60, r=20, t=40, b=60),
)
st.plotly_chart(fig, use_container_width=True)

# ================= MONTHLY COMPARISON BAR CHART =================
st.subheader("Actual vs Planned — Monthly Breakdown")

bar_df = mine_data[['date', 'planned_production_tpd__DERIVED', 'actual_production_tpd__DERIVED']].copy()
bar_df['shortfall'] = bar_df['planned_production_tpd__DERIVED'] - bar_df['actual_production_tpd__DERIVED']
bar_df['month_label'] = bar_df['date'].dt.strftime('%b %Y')

fig_bar = go.Figure()
fig_bar.add_trace(go.Bar(
    x=bar_df['date'], y=bar_df['planned_production_tpd__DERIVED'],
    name='Planned', marker_color='rgba(52,152,219,0.6)',
))
fig_bar.add_trace(go.Bar(
    x=bar_df['date'], y=bar_df['actual_production_tpd__DERIVED'],
    name='Actual', marker_color='rgba(46,204,113,0.8)',
))
fig_bar.update_layout(
    barmode='group', height=350,
    xaxis_title="Date", yaxis_title="Production (TPD)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig_bar, use_container_width=True)

# ================= RISK INDICATORS =================
st.subheader("Risk Indicators (Latest Month)")

latest = mine_data.iloc[-1]
risk = str(latest.get('shortfall_risk', 'N/A'))
planned = latest.get('planned_production_tpd__DERIVED', 0)
actual = latest.get('actual_production_tpd__DERIVED', 0)
shortfall = max(0, planned - actual) if pd.notnull(planned) and pd.notnull(actual) else 0
eff = (actual / planned * 100) if planned > 0 else 0

r1, r2, r3 = st.columns(3)
color = "🔴" if risk == "High" else ("🟡" if risk == "Medium" else "🟢")
risk_icon_cls = "geo-icon-red" if risk == "High" else ("geo-icon-amber" if risk == "Medium" else "geo-icon-green")
risk_trend_cls = "geo-trend-down" if risk == "High" else ("geo-trend-amber" if risk == "Medium" else "geo-trend-up")
eff_trend_cls = "geo-trend-up" if eff >= 90 else ("geo-trend-amber" if eff >= 75 else "geo-trend-down")

st.markdown(f"""
<div class="geo-kpi-grid" style="grid-template-columns: repeat(3,1fr);">
    <div class="geo-kpi-card">
        <div class="geo-kpi-header"><div class="geo-kpi-title">Risk Level</div><div class="geo-kpi-icon {risk_icon_cls}">{color}</div></div>
        <div class="geo-kpi-value">{risk}</div>
        <div class="geo-kpi-footer"><span class="{risk_trend_cls}">Latest Month</span></div>
    </div>
    <div class="geo-kpi-card">
        <div class="geo-kpi-header"><div class="geo-kpi-title">Latest Shortfall</div><div class="geo-kpi-icon geo-icon-amber">📉</div></div>
        <div class="geo-kpi-value">{shortfall:.0f} <span style="font-size:1.1rem;color:#94A3B8;">TPD</span></div>
        <div class="geo-kpi-footer"><span class="{'geo-trend-up' if shortfall == 0 else 'geo-trend-down'}">{'No Shortfall' if shortfall == 0 else 'Below Plan'}</span></div>
    </div>
    <div class="geo-kpi-card">
        <div class="geo-kpi-header"><div class="geo-kpi-title">Latest Efficiency</div><div class="geo-kpi-icon geo-icon-green">⚡</div></div>
        <div class="geo-kpi-value">{eff:.1f}<span style="font-size:1.5rem;color:#94A3B8;">%</span></div>
        <div class="geo-kpi-footer"><span class="{eff_trend_cls}">{'Optimal' if eff >= 90 else 'Moderate' if eff >= 75 else 'Low'}</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

# ================= EQUIPMENT & WEATHER IMPACT =================
st.subheader("Equipment & Weather Impact")

col_eq, col_rain = st.columns(2)

with col_eq:
    fig_eq = px.line(mine_data, x='date', y='equipment_availability_pct__DERIVED',
                     title='Equipment Availability Over Time')
    fig_eq.update_traces(line_color='#e74c3c')
    fig_eq.update_layout(height=300, yaxis_title='Availability (%)', xaxis_title='',
                         yaxis=dict(range=[0.5, 1.05]))
    st.plotly_chart(fig_eq, use_container_width=True)

with col_rain:
    fig_rain = px.bar(mine_data, x='date', y='rainfall_mm__REAL',
                      title='Monthly Rainfall')
    fig_rain.update_traces(marker_color='#3498db')
    fig_rain.update_layout(height=300, yaxis_title='Rainfall (mm)', xaxis_title='')
    st.plotly_chart(fig_rain, use_container_width=True)

# ================= SHORTFALL SUMMARY TABLE =================
st.subheader("Shortfall Summary (Last 12 Months)")

table_df = mine_data.tail(12)[['date', 'planned_production_tpd__DERIVED', 'actual_production_tpd__DERIVED', 
                                 'equipment_availability_pct__DERIVED', 'rainfall_mm__REAL', 'shortfall_risk']].copy()
table_df['date'] = table_df['date'].dt.strftime('%b %Y')
table_df.columns = ['Month', 'Planned (TPD)', 'Actual (TPD)', 'Equip Avail (%)', 'Rainfall (mm)', 'Risk']

# Color code risk
def color_risk(val):
    if val == 'High':
        return 'background-color: rgba(231,76,60,0.3)'
    elif val == 'Medium':
        return 'background-color: rgba(241,196,15,0.3)'
    return 'background-color: rgba(46,204,113,0.2)'

styled = table_df.style.map(color_risk, subset=['Risk']).format({
    'Planned (TPD)': '{:.0f}',
    'Actual (TPD)': '{:.0f}',
    'Equip Avail (%)': '{:.1%}',
    'Rainfall (mm)': '{:.0f}',
})

st.dataframe(styled, use_container_width=True, hide_index=True)

st.info("💡 **Business Impact:** 5% reduction in production shortfall across 3 mines ≈ 2,500 tons/month saved (illustrative)")


# --- Animations ---
inject_kpi_animations()
inject_volcano_animations()
