import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os

st.title("MineFlow Optimizer - Production Forecast & Risk")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

@st.cache_data
def load_production_data():
    prod_path = os.path.join(DATA_DIR, 'production_dataset.csv')
    forecast_path = os.path.join(DATA_DIR, 'production_forecast.csv')
    
    df_prod = pd.read_csv(prod_path) if os.path.exists(prod_path) else pd.DataFrame()
    df_forecast = pd.read_csv(forecast_path) if os.path.exists(forecast_path) else pd.DataFrame()
    
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
st.subheader("Key Metrics")
c1, c2, c3, c4 = st.columns(4)

avg_planned = mine_data['planned_production_tpd'].mean()
avg_actual = mine_data['actual_production_tpd'].mean()
efficiency = (avg_actual / avg_planned * 100) if avg_planned > 0 else 0
high_risk_months = (mine_data['shortfall_risk'] == 'High').sum()

c1.metric("Avg Planned (TPD)", f"{avg_planned:.0f}")
c2.metric("Avg Actual (TPD)", f"{avg_actual:.0f}")
c3.metric("Efficiency", f"{efficiency:.1f}%")
c4.metric("High Risk Months", f"{high_risk_months} / {len(mine_data)}")

# ================= PRODUCTION TIMELINE =================
st.subheader(f"Production Timeline — {selected_mine}")

fig = go.Figure()

# Historical: Planned (dashed blue)
fig.add_trace(go.Scatter(
    x=mine_data['date'], y=mine_data['planned_production_tpd'],
    name='Planned', line=dict(color='#3498db', dash='dash', width=2),
    hovertemplate='%{x|%b %Y}<br>Planned: %{y:.0f} TPD<extra></extra>'
))

# Historical: Actual (solid blue)
fig.add_trace(go.Scatter(
    x=mine_data['date'], y=mine_data['actual_production_tpd'],
    name='Actual', line=dict(color='#2ecc71', width=2.5),
    fill='tonexty', fillcolor='rgba(46,204,113,0.1)',
    hovertemplate='%{x|%b %Y}<br>Actual: %{y:.0f} TPD<extra></extra>'
))

# Forecast: Predicted (dashed orange)
if not forecast_data.empty and 'predicted_production_tpd' in forecast_data.columns:
    fig.add_trace(go.Scatter(
        x=forecast_data['date'], y=forecast_data['planned_production_tpd'],
        name='Planned (2026)', line=dict(color='#3498db', dash='dot', width=1.5),
        hovertemplate='%{x|%b %Y}<br>Planned: %{y:.0f} TPD<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        x=forecast_data['date'], y=forecast_data['predicted_production_tpd'],
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

bar_df = mine_data[['date', 'planned_production_tpd', 'actual_production_tpd']].copy()
bar_df['shortfall'] = bar_df['planned_production_tpd'] - bar_df['actual_production_tpd']
bar_df['month_label'] = bar_df['date'].dt.strftime('%b %Y')

fig_bar = go.Figure()
fig_bar.add_trace(go.Bar(
    x=bar_df['date'], y=bar_df['planned_production_tpd'],
    name='Planned', marker_color='rgba(52,152,219,0.6)',
))
fig_bar.add_trace(go.Bar(
    x=bar_df['date'], y=bar_df['actual_production_tpd'],
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
planned = latest.get('planned_production_tpd', 0)
actual = latest.get('actual_production_tpd', 0)
shortfall = max(0, planned - actual) if pd.notnull(planned) and pd.notnull(actual) else 0

r1, r2, r3 = st.columns(3)
with r1:
    color = "🔴" if risk == "High" else ("🟡" if risk == "Medium" else "🟢")
    st.metric(f"{color} Risk Level", risk)
with r2:
    st.metric("Latest Shortfall", f"{shortfall:.0f} TPD")
with r3:
    eff = (actual / planned * 100) if planned > 0 else 0
    st.metric("Latest Efficiency", f"{eff:.1f}%")

# ================= EQUIPMENT & WEATHER IMPACT =================
st.subheader("Equipment & Weather Impact")

col_eq, col_rain = st.columns(2)

with col_eq:
    fig_eq = px.line(mine_data, x='date', y='equipment_availability_pct',
                     title='Equipment Availability Over Time')
    fig_eq.update_traces(line_color='#e74c3c')
    fig_eq.update_layout(height=300, yaxis_title='Availability (%)', xaxis_title='',
                         yaxis=dict(range=[0.5, 1.05]))
    st.plotly_chart(fig_eq, use_container_width=True)

with col_rain:
    fig_rain = px.bar(mine_data, x='date', y='rainfall_mm',
                      title='Monthly Rainfall')
    fig_rain.update_traces(marker_color='#3498db')
    fig_rain.update_layout(height=300, yaxis_title='Rainfall (mm)', xaxis_title='')
    st.plotly_chart(fig_rain, use_container_width=True)

# ================= SHORTFALL SUMMARY TABLE =================
st.subheader("Shortfall Summary (Last 12 Months)")

table_df = mine_data.tail(12)[['date', 'planned_production_tpd', 'actual_production_tpd', 
                                 'equipment_availability_pct', 'rainfall_mm', 'shortfall_risk']].copy()
table_df['date'] = table_df['date'].dt.strftime('%b %Y')
table_df.columns = ['Month', 'Planned (TPD)', 'Actual (TPD)', 'Equip Avail (%)', 'Rainfall (mm)', 'Risk']

# Color code risk
def color_risk(val):
    if val == 'High':
        return 'background-color: rgba(231,76,60,0.3)'
    elif val == 'Medium':
        return 'background-color: rgba(241,196,15,0.3)'
    return 'background-color: rgba(46,204,113,0.2)'

styled = table_df.style.applymap(color_risk, subset=['Risk']).format({
    'Planned (TPD)': '{:.0f}',
    'Actual (TPD)': '{:.0f}',
    'Equip Avail (%)': '{:.1%}',
    'Rainfall (mm)': '{:.0f}',
})

st.dataframe(styled, use_container_width=True, hide_index=True)

st.info("💡 **Business Impact:** 5% reduction in production shortfall across 3 mines ≈ 2,500 tons/month saved (illustrative)")
