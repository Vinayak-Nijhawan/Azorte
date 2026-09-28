import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import json
import os
import sys

# Load global CSS (fd-header styling, Material Symbols font)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils import load_css
load_css()

st.markdown("""
<div class="fd-header">
    <div class="fd-header-left">
        <h1>📈 MineFlow Optimizer - Production Forecast</h1>
        <div class="fd-subtitle">Predictive Output & Risk Mitigation · MOIL Manganese Operations</div>
    </div>
    <div class="fd-header-right">
        <div class="fd-tag">⛏️ Production</div>
        <div class="fd-live"><div class="fd-live-dot"></div> OPERATIONAL</div>
    </div>
</div>
""", unsafe_allow_html=True)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
MODEL_DIR = os.path.join(PROJECT_ROOT, 'models')

@st.cache_data
def load_production_data():
    # Try real data first, fall back to old synthetic
    real_path = os.path.join(DATA_DIR, 'production_dataset_real.csv')
    old_path = os.path.join(DATA_DIR, 'production_dataset.csv')
    
    if os.path.exists(real_path):
        df = pd.read_csv(real_path, comment='#')
        data_source = "REAL + DERIVED"
    elif os.path.exists(old_path):
        df = pd.read_csv(old_path)
        data_source = "SYNTHETIC"
    else:
        return pd.DataFrame(), pd.DataFrame(), None, "NONE"
    
    # Load forecast
    forecast_path = os.path.join(DATA_DIR, 'production_forecast_real.csv')
    old_forecast = os.path.join(DATA_DIR, 'production_forecast.csv')
    
    if os.path.exists(forecast_path):
        df_fc = pd.read_csv(forecast_path, comment='#')
    elif os.path.exists(old_forecast):
        df_fc = pd.read_csv(old_forecast)
    else:
        df_fc = pd.DataFrame()
    
    # Load model metrics
    metrics = None
    metrics_path = os.path.join(DATA_DIR, 'model_metrics.json')
    if os.path.exists(metrics_path):
        with open(metrics_path, 'r') as f:
            metrics = json.load(f)
    
    return df, df_fc, metrics, data_source

df_prod, df_forecast, model_metrics, data_source = load_production_data()

if df_prod.empty:
    st.warning("Production dataset not found. Run generate_real_production.py first.")
    st.stop()

# ================= DATA SOURCE BADGE =================
if data_source == "REAL + DERIVED":
    st.caption("📊 **Data Source:** REAL annual production (MOIL) + REAL weather (Open-Meteo) + DERIVED monthly estimates. See column suffixes for provenance.")
else:
    st.caption(f"⚠️ **Data Source:** {data_source}")

# ================= DETECT COLUMN NAMES =================
# Support both new (suffixed) and old (unsuffixed) column formats
def col(name):
    """Find the right column name whether suffixed or not."""
    if name in df_prod.columns:
        return name
    # Try suffixed versions
    for suffix in ['__REAL', '__DERIVED', '__ASSUMED']:
        if f"{name}{suffix}" in df_prod.columns:
            return f"{name}{suffix}"
    return name  # Return as-is, will error naturally if missing

COL_PLANNED = col('planned_production_tpd')
COL_ACTUAL = col('derived_actual_production_tpd') if 'derived_actual_production_tpd__DERIVED' in df_prod.columns else col('actual_production_tpd')
COL_BASELINE = col('baseline_tpd')
COL_RAINFALL = col('rainfall_mm')
COL_EQUIP = col('equipment_availability_pct')
COL_RISK = col('shortfall_risk')

# ================= SIDEBAR =================
mines = sorted(df_prod['mine_id'].unique().tolist())
selected_mine = st.sidebar.selectbox("Select Mine", mines)

# Scenario selector (if forecast has scenarios)
scenario = "normal_weather"
if not df_forecast.empty and 'scenario' in df_forecast.columns:
    scenarios = df_forecast['scenario'].unique().tolist()
    scenario = st.sidebar.selectbox("Forecast Scenario", scenarios, index=0)

mine_data = df_prod[df_prod['mine_id'] == selected_mine].copy()
mine_data['date'] = pd.to_datetime(mine_data['year'].astype(str) + '-' + mine_data['month'].astype(str).str.zfill(2) + '-01')
mine_data = mine_data.sort_values('date')

# Forecast data
forecast_data = pd.DataFrame()
if not df_forecast.empty:
    fc_filter = df_forecast['mine_id'] == selected_mine
    if 'scenario' in df_forecast.columns:
        fc_filter = fc_filter & (df_forecast['scenario'] == scenario)
    forecast_data = df_forecast[fc_filter].copy()
    if not forecast_data.empty:
        forecast_data['date'] = pd.to_datetime(forecast_data['year'].astype(str) + '-' + forecast_data['month'].astype(str).str.zfill(2) + '-01')
        forecast_data = forecast_data.sort_values('date')

# ================= KPI METRICS =================
st.subheader("Key Metrics")
c1, c2, c3, c4 = st.columns(4)

avg_baseline = mine_data[COL_BASELINE].mean() if COL_BASELINE in mine_data.columns else mine_data[COL_PLANNED].mean()
avg_actual = mine_data[COL_ACTUAL].mean()
efficiency = (avg_actual / avg_baseline * 100) if avg_baseline > 0 else 0
high_risk_months = (mine_data[COL_RISK] == 'High').sum() if COL_RISK in mine_data.columns else 0

c1.metric("Avg Baseline (TPD)", f"{avg_baseline:.0f}", help="REAL: From MOIL annual reports")
c2.metric("Avg Derived (TPD)", f"{avg_actual:.0f}", help="DERIVED: Baseline adjusted by weather penalty")
c3.metric("Efficiency", f"{efficiency:.1f}%")
c4.metric("High Risk Months", f"{high_risk_months} / {len(mine_data)}")

# ================= MODEL METRICS (if available) =================
if model_metrics:
    with st.expander("🔬 ML Model Performance (vs Baseline)", expanded=False):
        test_m = model_metrics.get("metrics", {}).get("test", {})
        val_m = model_metrics.get("metrics", {}).get("validation", {})
        
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Test MAE", f"{test_m.get('ml_mae', 'N/A')}", 
                   delta=f"{test_m.get('improvement_mae_pct', 0):+.1f}% vs baseline",
                   delta_color="normal")
        mc2.metric("Test R²", f"{test_m.get('ml_r2', 'N/A')}")
        mc3.metric("Splitting", "Chronological", help="Train<=2022, Val=2023, Test=2024+")
        
        st.caption("⚠️ Target variable is DERIVED (not observed MOIL monthly production). Model learns weather-production relationship from derived data.")

# ================= PRODUCTION TIMELINE =================
st.subheader(f"Production Timeline — {selected_mine}")

fig = go.Figure()

# Historical: Baseline / Planned (dashed blue) — REAL
fig.add_trace(go.Scatter(
    x=mine_data['date'], y=mine_data[COL_BASELINE] if COL_BASELINE in mine_data.columns else mine_data[COL_PLANNED],
    name='Baseline (REAL)', line=dict(color='#3498db', dash='dash', width=2),
    hovertemplate='%{x|%b %Y}<br>Baseline: %{y:.0f} TPD<extra></extra>'
))

# Historical: Derived Actual (solid green) — DERIVED
fig.add_trace(go.Scatter(
    x=mine_data['date'], y=mine_data[COL_ACTUAL],
    name='Derived Actual', line=dict(color='#2ecc71', width=2.5),
    fill='tonexty', fillcolor='rgba(46,204,113,0.1)',
    hovertemplate='%{x|%b %Y}<br>Derived: %{y:.0f} TPD<extra></extra>'
))

# Forecast: ML Predicted (dashed orange) — PREDICTION
if not forecast_data.empty and 'predicted_production_tpd' in forecast_data.columns:
    # Connect forecast to historical with a bridge point
    last_hist_date = mine_data['date'].iloc[-1]
    last_hist_val = mine_data[COL_ACTUAL].iloc[-1]
    
    bridge_dates = pd.concat([pd.Series([last_hist_date]), forecast_data['date']])
    bridge_vals = pd.concat([pd.Series([last_hist_val]), forecast_data['predicted_production_tpd']])
    
    # Forecast baseline
    if 'baseline_tpd' in forecast_data.columns:
        bridge_base = pd.concat([pd.Series([mine_data[COL_BASELINE].iloc[-1] if COL_BASELINE in mine_data.columns else mine_data[COL_PLANNED].iloc[-1]]), 
                                forecast_data['baseline_tpd']])
        fig.add_trace(go.Scatter(
            x=bridge_dates, y=bridge_base,
            name='Baseline (2026)', line=dict(color='#3498db', dash='dot', width=1.5),
            hovertemplate='%{x|%b %Y}<br>Baseline: %{y:.0f} TPD<extra></extra>'
        ))
    
    fig.add_trace(go.Scatter(
        x=bridge_dates, y=bridge_vals,
        name='ML Predicted (2026)', line=dict(color='#e67e22', width=2.5, dash='dash'),
        hovertemplate='%{x|%b %Y}<br>Predicted: %{y:.0f} TPD<extra></extra>'
    ))
    
    # Add vertical line at forecast boundary
    fig.add_vline(x=last_hist_date.timestamp() * 1000, line_dash="dot", line_color="rgba(255,255,255,0.3)",
                  annotation_text="← Historical | Forecast →", annotation_position="top")

fig.update_layout(
    xaxis_title="Date", yaxis_title="Production (TPD)",
    height=450, hovermode='x unified',
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=60, r=20, t=40, b=60),
)
st.plotly_chart(fig, use_container_width=True)

# ================= EQUIPMENT & WEATHER IMPACT =================
st.subheader("Equipment & Weather Impact")

col_eq, col_rain = st.columns(2)

with col_eq:
    if COL_EQUIP in mine_data.columns:
        fig_eq = px.line(mine_data, x='date', y=COL_EQUIP,
                         title='Equipment Availability Over Time')
        fig_eq.update_traces(line_color='#e74c3c')
        fig_eq.update_layout(height=300, yaxis_title='Availability', xaxis_title='',
                             yaxis=dict(range=[0.5, 1.05]))
        st.plotly_chart(fig_eq, use_container_width=True)

with col_rain:
    if COL_RAINFALL in mine_data.columns:
        fig_rain = px.bar(mine_data, x='date', y=COL_RAINFALL,
                          title='Monthly Rainfall (REAL — Open-Meteo)')
        fig_rain.update_traces(marker_color='#3498db')
        fig_rain.update_layout(height=300, yaxis_title='Rainfall (mm)', xaxis_title='')
        st.plotly_chart(fig_rain, use_container_width=True)

# ================= SHORTFALL SUMMARY TABLE =================
st.subheader("Shortfall Summary (Last 12 Months)")

display_cols = ['date']
rename_map = {'date': 'Month'}

for orig, label in [
    (COL_PLANNED if COL_PLANNED in mine_data.columns else COL_BASELINE, 'Baseline (TPD)'),
    (COL_ACTUAL, 'Derived Actual (TPD)'),
    (COL_EQUIP, 'Equip Avail'),
    (COL_RAINFALL, 'Rainfall (mm)'),
    (COL_RISK, 'Risk'),
]:
    if orig in mine_data.columns:
        display_cols.append(orig)
        rename_map[orig] = label

table_df = mine_data.tail(12)[display_cols].copy()
table_df['date'] = table_df['date'].dt.strftime('%b %Y')
table_df = table_df.rename(columns=rename_map)

def color_risk(val):
    if val == 'High':
        return 'background-color: rgba(231,76,60,0.3)'
    elif val == 'Medium':
        return 'background-color: rgba(241,196,15,0.3)'
    return 'background-color: rgba(46,204,113,0.2)'

if 'Risk' in table_df.columns:
    styled = table_df.style.map(color_risk, subset=['Risk'])
    st.dataframe(styled, use_container_width=True, hide_index=True)
else:
    st.dataframe(table_df, use_container_width=True, hide_index=True)

# ================= FORECAST RISK TABLE =================
if not forecast_data.empty:
    st.subheader(f"2026 Forecast Risk ({scenario.replace('_', ' ').title()})")
    
    fc_display = forecast_data[['month', 'baseline_tpd', 'predicted_production_tpd', 'shortfall_risk']].copy()
    fc_display.columns = ['Month', 'Baseline (TPD)', 'ML Predicted (TPD)', 'Risk']
    fc_display['Month'] = fc_display['Month'].apply(lambda m: pd.Timestamp(2026, m, 1).strftime('%b'))
    fc_display['Gap'] = fc_display['ML Predicted (TPD)'] - fc_display['Baseline (TPD)']
    
    styled_fc = fc_display.style.map(color_risk, subset=['Risk']).format({
        'Baseline (TPD)': '{:.0f}', 'ML Predicted (TPD)': '{:.0f}', 'Gap': '{:+.0f}'
    })
    st.dataframe(styled_fc, use_container_width=True, hide_index=True)
    st.caption("⚠️ These are scenario-based ML predictions, NOT actual MOIL production forecasts.")

# ================= LIVE REAL-TIME FORECAST =================
live_path = os.path.join(DATA_DIR, 'production_forecast_live.csv')
if os.path.exists(live_path):
    df_live = pd.read_csv(live_path)
    
    if not df_live.empty:
        st.markdown("---")
        st.subheader("🔴 Live Real-Time Forecast (Next 30 Days)")
        
        # Show timestamp
        if 'timestamp' in df_live.columns:
            ts = df_live['timestamp'].iloc[0]
            st.caption(f"🕐 **Last Updated:** {ts} | **Source:** Open-Meteo Live 14-Day Weather API → ML Model")
        
        # Live forecast for selected mine
        live_mine = df_live[df_live['mine_id'] == selected_mine]
        
        if not live_mine.empty:
            row = live_mine.iloc[0]
            
            # Big KPI cards
            lc1, lc2, lc3, lc4 = st.columns(4)
            
            risk_color = "🔴" if row['shortfall_risk'] == 'High' else ("🟡" if row['shortfall_risk'] == 'Medium' else "🟢")
            
            lc1.metric(
                "Live Predicted TPD", 
                f"{row['predicted_production_tpd']:.0f}",
                delta=f"{row['predicted_production_tpd'] - row['baseline_tpd']:+.0f} vs baseline",
                delta_color="normal"
            )
            lc2.metric("Baseline TPD", f"{row['baseline_tpd']:.0f}")
            lc3.metric("Live Rainfall (30d est.)", f"{row['rainfall_mm_scenario']:.0f} mm")
            lc4.metric(f"{risk_color} Risk Level", row['shortfall_risk'])
            
            efficiency_live = row['predicted_production_tpd'] / row['baseline_tpd'] * 100
            if efficiency_live >= 92:
                st.success(f"✅ **{selected_mine}** is expected to operate at **{efficiency_live:.1f}%** of baseline capacity this month. No intervention needed.")
            elif efficiency_live >= 85:
                st.warning(f"⚠️ **{selected_mine}** may see a **{100 - efficiency_live:.1f}%** shortfall. Consider pre-positioning water pumps and adjusting blasting schedules.")
            else:
                rainfall = row.get('rainfall_mm_scenario', 0)
                if rainfall > 150:
                    st.error(f"🚨 **{selected_mine}** is at risk of a **{100 - efficiency_live:.1f}%** production shortfall due to heavy rainfall ({rainfall:.0f}mm projected). Activate monsoon contingency plan.")
                else:
                    st.error(f"🚨 **{selected_mine}** is at risk of a **{100 - efficiency_live:.1f}%** production shortfall based on current operational and environmental conditions. Activate contingency protocols.")
        
        # All mines summary
        st.subheader("All Mines — Live Risk Dashboard")
        
        live_display = df_live[['mine_id', 'baseline_tpd', 'predicted_production_tpd', 'rainfall_mm_scenario', 'weather_penalty', 'shortfall_risk']].copy()
        live_display.columns = ['Mine', 'Baseline (TPD)', 'Predicted (TPD)', 'Rainfall (mm)', 'Weather Penalty', 'Risk']
        live_display['Efficiency'] = (live_display['Predicted (TPD)'] / live_display['Baseline (TPD)'] * 100).round(1)
        live_display = live_display.sort_values('Efficiency')
        
        styled_live = live_display.style.map(color_risk, subset=['Risk']).format({
            'Baseline (TPD)': '{:.0f}', 
            'Predicted (TPD)': '{:.0f}', 
            'Rainfall (mm)': '{:.0f}',
            'Weather Penalty': '{:.2f}',
            'Efficiency': '{:.1f}%'
        })
        st.dataframe(styled_live, use_container_width=True, hide_index=True)
        
        # Summary stats
        high_count = (df_live['shortfall_risk'] == 'High').sum()
        med_count = (df_live['shortfall_risk'] == 'Medium').sum()
        low_count = (df_live['shortfall_risk'] == 'Low').sum()
        
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("🔴 High Risk Mines", high_count)
        sc2.metric("🟡 Medium Risk Mines", med_count)
        sc3.metric("🟢 Low Risk Mines", low_count)
        
        st.caption("📡 This forecast uses **LIVE weather data** from the Open-Meteo API, fed into the trained ML model. Run `python src/generate_live_forecast.py` to refresh.")

st.info("💡 **Business Impact:** Proactive identification of high-risk months enables MOIL to pre-position equipment and adjust blasting schedules, potentially recovering 5-10% of shortfall tonnage.")
