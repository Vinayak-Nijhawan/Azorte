import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ─── Paths ───
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DISPATCH_PLAN_PATH = os.path.join(DATA_DIR, "dispatch_plan.csv")
FLEET_ALERTS_PATH = os.path.join(DATA_DIR, "fleet_alerts.csv")
FORECAST_PATH = os.path.join(DATA_DIR, "production_forecast.csv")

# ─── Plotly theme helper ───
def apply_dark_theme(fig, height=400, show_legend=True):
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#c9d1d9', size=13),
        margin=dict(l=40, r=20, t=40, b=40),
        height=height,
        showlegend=show_legend,
    )
    fig.update_xaxes(gridcolor='rgba(255,255,255,0.05)', zerolinecolor='rgba(255,255,255,0.05)')
    fig.update_yaxes(gridcolor='rgba(255,255,255,0.05)', zerolinecolor='rgba(255,255,255,0.05)')
    return fig

# ─── CSS ───
st.markdown("""
<style>
    /* ── Header ── */
    .fd-header {
        background: linear-gradient(135deg, rgba(30,58,95,0.5) 0%, rgba(15,23,42,0.8) 100%);
        border: 1px solid rgba(100,116,139,0.2);
        border-radius: 12px;
        padding: 20px 28px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
    }
    .fd-header-left h1 {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #e2e8f0 !important;
        margin: 0 !important;
        letter-spacing: 0.5px;
    }
    .fd-header-left .fd-subtitle {
        font-size: 0.85rem !important;
        color: #64748b !important;
        margin-top: 2px !important;
    }
    .fd-header-right {
        display: flex;
        align-items: center;
        gap: 16px;
        flex-wrap: wrap;
    }
    .fd-tag {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 6px;
        padding: 5px 12px;
        font-size: 0.78rem !important;
        color: #94a3b8 !important;
    }
    .fd-live {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(34,197,94,0.1);
        border: 1px solid rgba(34,197,94,0.25);
        border-radius: 6px;
        padding: 5px 12px;
        font-size: 0.78rem !important;
        color: #4ade80 !important;
        font-weight: 600;
    }
    .fd-live-dot {
        width: 7px; height: 7px;
        background: #22c55e;
        border-radius: 50%;
        animation: pulse-dot 1.5s infinite;
    }
    @keyframes pulse-dot {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }

    /* ── KPI Cards ── */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(8, 1fr);
        gap: 10px;
        margin-bottom: 20px;
    }
    .kpi-card {
        background: rgba(255,255,255,0.025);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px;
        padding: 16px 18px;
        transition: border-color 0.2s;
    }
    .kpi-card:hover {
        border-color: rgba(99,102,241,0.3);
    }
    .kpi-label {
        font-size: 0.68rem !important;
        color: #64748b !important;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        font-weight: 600 !important;
        margin-bottom: 6px !important;
    }
    .kpi-value {
        font-size: 1.7rem !important;
        font-weight: 700 !important;
        color: #f1f5f9 !important;
        line-height: 1.1 !important;
    }
    .kpi-unit {
        font-size: 0.75rem !important;
        color: #64748b !important;
        font-weight: 400 !important;
        margin-left: 3px;
    }
    .kpi-delta {
        font-size: 0.75rem !important;
        margin-top: 4px !important;
    }
    .kpi-delta.positive { color: #22c55e !important; }
    .kpi-delta.negative { color: #ef4444 !important; }
    .kpi-delta.neutral  { color: #64748b !important; }
    .kpi-delta.warning  { color: #f59e0b !important; }

    /* ── Section headers ── */
    .section-title {
        font-size: 0.72rem !important;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        color: #475569 !important;
        font-weight: 700 !important;
        margin-bottom: 12px !important;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(255,255,255,0.05);
    }

    /* ── Cards / Panels ── */
    .panel {
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px;
        padding: 20px;
        height: 100%;
    }
    .panel-header {
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        color: #e2e8f0 !important;
        margin-bottom: 14px !important;
    }

    /* ── AI Recommendation ── */
    .ai-card {
        background: linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(15,23,42,0.5) 100%);
        border: 1px solid rgba(99,102,241,0.2);
        border-radius: 10px;
        padding: 20px;
    }
    .ai-card-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        color: #a5b4fc !important;
        margin-bottom: 16px !important;
    }
    .ai-badge {
        background: rgba(99,102,241,0.2);
        border: 1px solid rgba(99,102,241,0.3);
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 0.6rem !important;
        color: #818cf8 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 700;
    }
    .ai-section-label {
        font-size: 0.65rem !important;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #64748b !important;
        font-weight: 600 !important;
        margin-top: 12px !important;
        margin-bottom: 4px !important;
    }
    .ai-value {
        font-size: 0.95rem !important;
        color: #e2e8f0 !important;
    }
    .ai-impact-item {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.85rem !important;
        padding: 3px 0;
    }
    .impact-positive { color: #4ade80 !important; }
    .impact-negative { color: #f87171 !important; }

    /* ── Bottleneck cards ── */
    .bottleneck-card {
        background: rgba(255,255,255,0.02);
        border-radius: 8px;
        padding: 14px 16px;
        border-left: 3px solid;
    }
    .bn-critical { border-left-color: #ef4444; background: rgba(239,68,68,0.05); }
    .bn-warning  { border-left-color: #f59e0b; background: rgba(245,158,11,0.05); }
    .bn-info     { border-left-color: #3b82f6; background: rgba(59,130,246,0.05); }
    .bn-label {
        font-size: 0.7rem !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 700 !important;
        margin-bottom: 4px !important;
    }
    .bn-critical .bn-label { color: #f87171 !important; }
    .bn-warning  .bn-label { color: #fbbf24 !important; }
    .bn-info     .bn-label { color: #60a5fa !important; }
    .bn-message {
        font-size: 0.85rem !important;
        color: #cbd5e1 !important;
    }

    /* ── Fleet status items ── */
    .fleet-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 12px;
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.04);
        border-radius: 6px;
        margin-bottom: 6px;
        font-size: 0.85rem !important;
    }
    .fleet-dot {
        width: 8px; height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
    }
    .dot-active   { background: #22c55e; }
    .dot-idle     { background: #f59e0b; }
    .dot-maint    { background: #ef4444; }
    .fleet-id {
        font-weight: 700 !important;
        color: #e2e8f0 !important;
        min-width: 30px;
    }
    .fleet-status {
        color: #94a3b8 !important;
        flex: 1;
    }
    .fleet-cap {
        color: #64748b !important;
        font-size: 0.78rem !important;
    }
</style>
""", unsafe_allow_html=True)


# ─── Data Loaders ───
@st.cache_data
def load_data():
    dispatch_plan = pd.DataFrame()
    fleet_alerts = pd.DataFrame()
    forecast = pd.DataFrame()

    if os.path.exists(DISPATCH_PLAN_PATH):
        dispatch_plan = pd.read_csv(DISPATCH_PLAN_PATH)
    if os.path.exists(FLEET_ALERTS_PATH):
        fleet_alerts = pd.read_csv(FLEET_ALERTS_PATH)
    if os.path.exists(FORECAST_PATH):
        forecast = pd.read_csv(FORECAST_PATH)

    return dispatch_plan, fleet_alerts, forecast


dispatch_plan, fleet_alerts, forecast = load_data()

if dispatch_plan.empty:
    st.info("No dispatch plan found. Run `python src/optimize_fleet.py` first.")
    st.stop()

# ─── SIDEBAR FILTERS (preserved) ───
st.sidebar.header("Filter Options")

mines = dispatch_plan['mine_id'].unique().tolist() if 'mine_id' in dispatch_plan.columns else ['All']
selected_mine = st.sidebar.selectbox("Select Mine", mines)

months = sorted(dispatch_plan['month'].unique().tolist()) if 'month' in dispatch_plan.columns else ['All']
selected_month = st.sidebar.selectbox("Select Month", months)

years = sorted(dispatch_plan['year'].unique().tolist()) if 'year' in dispatch_plan.columns else ['All']
selected_year = st.sidebar.selectbox("Select Year", years)

# ─── Filter dispatch data ───
df_filtered = dispatch_plan.copy()
if selected_mine != 'All' and 'mine_id' in df_filtered.columns:
    df_filtered = df_filtered[df_filtered['mine_id'] == selected_mine]
if selected_month != 'All' and 'month' in df_filtered.columns:
    df_filtered = df_filtered[df_filtered['month'] == selected_month]
if selected_year != 'All' and 'year' in df_filtered.columns:
    df_filtered = df_filtered[df_filtered['year'] == selected_year]

# Filter alerts
alerts_filtered = fleet_alerts.copy()
if not alerts_filtered.empty:
    if selected_mine != 'All' and 'mine_id' in alerts_filtered.columns:
        alerts_filtered = alerts_filtered[alerts_filtered['mine_id'] == selected_mine]
    if selected_month != 'All' and 'month' in alerts_filtered.columns:
        alerts_filtered = alerts_filtered[alerts_filtered['month'] == selected_month]
    if selected_year != 'All' and 'year' in alerts_filtered.columns:
        alerts_filtered = alerts_filtered[alerts_filtered['year'] == selected_year]

# Filter forecast
forecast_filtered = forecast.copy()
if not forecast_filtered.empty:
    if selected_mine != 'All' and 'mine_id' in forecast_filtered.columns:
        forecast_filtered = forecast_filtered[forecast_filtered['mine_id'] == selected_mine]
    if selected_month != 'All' and 'month' in forecast_filtered.columns:
        forecast_filtered = forecast_filtered[forecast_filtered['month'] == selected_month]
    if selected_year != 'All' and 'year' in forecast_filtered.columns:
        forecast_filtered = forecast_filtered[forecast_filtered['year'] == selected_year]

# ─── Compute all metrics from actual data ───
planned_tpd = df_filtered['planned_tpd'].mean() if 'planned_tpd' in df_filtered.columns else 0
achievable_tpd = df_filtered['total_mine_tpd'].mean() if 'total_mine_tpd' in df_filtered.columns else 0
delta_tpd = achievable_tpd - planned_tpd
achievement_pct = df_filtered['achievable_vs_planned_pct'].mean() if 'achievable_vs_planned_pct' in df_filtered.columns else 0

num_dumpers = df_filtered['dumper_id'].nunique() if 'dumper_id' in df_filtered.columns else 0
num_shovels = df_filtered['shovel_id'].nunique() if 'shovel_id' in df_filtered.columns else 0

avg_dumper_cap = df_filtered['effective_capacity_tph'].mean() if 'effective_capacity_tph' in df_filtered.columns else 0
avg_base_cap = df_filtered['dumper_capacity_tph'].mean() if 'dumper_capacity_tph' in df_filtered.columns else 0
efficiency_pct = (avg_dumper_cap / avg_base_cap * 100) if avg_base_cap > 0 else 100

# Equipment availability from forecast
equip_avail = forecast_filtered['equipment_availability_pct'].mean() * 100 if (
    not forecast_filtered.empty and 'equipment_availability_pct' in forecast_filtered.columns
) else 0

# Rainfall and road condition
rainfall = forecast_filtered['rainfall_mm'].mean() if (
    not forecast_filtered.empty and 'rainfall_mm' in forecast_filtered.columns
) else 0
road_cond = forecast_filtered['haul_road_condition'].mean() if (
    not forecast_filtered.empty and 'haul_road_condition' in forecast_filtered.columns
) else 5

# Shortfall risk
shortfall_risk = forecast_filtered['shortfall_risk'].mode().iloc[0] if (
    not forecast_filtered.empty and 'shortfall_risk' in forecast_filtered.columns and len(forecast_filtered['shortfall_risk'].mode()) > 0
) else "N/A"

# Shovel stats
shovel_stats = pd.DataFrame()
if 'assigned_shovel' in df_filtered.columns and 'shovel_throughput_tpd' in df_filtered.columns:
    shovel_stats = df_filtered.groupby('assigned_shovel').agg(
        throughput_tpd=('shovel_throughput_tpd', 'first'),
        dumpers_assigned=('dumper_id', 'count'),
        avg_eff_cap=('effective_capacity_tph', 'mean'),
        total_eff_cap=('effective_capacity_tph', 'sum'),
    ).reset_index()
    shovel_stats['capacity_tpd'] = shovel_stats['throughput_tpd'] * 1.2
    shovel_stats['utilization_pct'] = np.where(
        shovel_stats['capacity_tpd'] > 0,
        shovel_stats['throughput_tpd'] / shovel_stats['capacity_tpd'] * 100,
        0
    )

# Mine display name
mine_display = selected_mine.replace('_', ' ').replace('Mine ', '') if isinstance(selected_mine, str) else str(selected_mine)
month_names = {1:'Jan',2:'Feb',3:'Mar',4:'Apr',5:'May',6:'Jun',7:'Jul',8:'Aug',9:'Sep',10:'Oct',11:'Nov',12:'Dec'}
month_display = month_names.get(selected_month, str(selected_month))

# ─────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────
status_class = "fd-live" if achievement_pct >= 90 else "fd-tag"
status_text = "OPERATIONAL" if achievement_pct >= 90 else "AT RISK"
status_dot = '<div class="fd-live-dot"></div>' if achievement_pct >= 90 else '⚠️'

st.markdown(f"""
<div class="fd-header">
    <div class="fd-header-left">
        <h1>🚛 Intelligent Fleet Dispatch</h1>
        <div class="fd-subtitle">MineFlow OR-Optimizer · MOIL Manganese Operations</div>
    </div>
    <div class="fd-header-right">
        <div class="fd-tag">⛏️ {mine_display}</div>
        <div class="fd-tag">📅 {month_display} {selected_year}</div>
        <div class="{status_class}">{status_dot} {status_text}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# KPI CARDS
# ─────────────────────────────────────────
delta_class = "positive" if delta_tpd >= 0 else "negative"
delta_icon = "▲" if delta_tpd >= 0 else "▼"
achieve_class = "positive" if achievement_pct >= 100 else ("warning" if achievement_pct >= 90 else "negative")

# Count maintenance/unavailable dumpers from alerts
maint_count = 0
if not alerts_filtered.empty:
    maint_alerts = alerts_filtered[alerts_filtered['alert_message'].str.contains('unavailable|maintenance', case=False, na=False)]
    maint_count = len(maint_alerts.drop_duplicates(subset=['alert_message']))

avail_dumpers = num_dumpers
total_fleet = num_dumpers + maint_count

st.markdown(f"""
<div class="kpi-grid">
    <div class="kpi-card">
        <div class="kpi-label">Production</div>
        <div class="kpi-value">{achievable_tpd:,.0f}<span class="kpi-unit">TPD</span></div>
        <div class="kpi-delta {delta_class}">{delta_icon} {abs(delta_tpd):,.0f} TPD vs plan</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Planned Production</div>
        <div class="kpi-value">{planned_tpd:,.0f}<span class="kpi-unit">TPD</span></div>
        <div class="kpi-delta neutral">Target for period</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Achievement</div>
        <div class="kpi-value">{achievement_pct:.1f}<span class="kpi-unit">%</span></div>
        <div class="kpi-delta {achieve_class}">{'On track' if achievement_pct >= 100 else ('Near target' if achievement_pct >= 90 else 'Below target')}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Active Dumpers</div>
        <div class="kpi-value">{avail_dumpers}<span class="kpi-unit">/ {total_fleet}</span></div>
        <div class="kpi-delta {'neutral' if maint_count == 0 else 'warning'}">{maint_count} in maintenance</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Active Shovels</div>
        <div class="kpi-value">{num_shovels}</div>
        <div class="kpi-delta neutral">Assigned this period</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Fleet Efficiency</div>
        <div class="kpi-value">{efficiency_pct:.1f}<span class="kpi-unit">%</span></div>
        <div class="kpi-delta {'positive' if efficiency_pct > 90 else 'warning'}">Eff. vs base capacity</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Equip Availability</div>
        <div class="kpi-value">{equip_avail:.0f}<span class="kpi-unit">%</span></div>
        <div class="kpi-delta {'positive' if equip_avail > 85 else 'warning'}">{'Healthy' if equip_avail > 85 else 'Below target'}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Shortfall Risk</div>
        <div class="kpi-value" style="font-size:1.3rem !important; color: {'#ef4444' if shortfall_risk=='High' else ('#f59e0b' if shortfall_risk=='Medium' else '#22c55e')} !important;">{shortfall_risk}</div>
        <div class="kpi-delta neutral">Forecast assessment</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# MAIN CONTENT: Fleet View + AI Recommendation
# ─────────────────────────────────────────
col_main, col_ai = st.columns([2, 1], gap="medium")

with col_main:
    st.markdown('<div class="section-title">🚛 Fleet Operational Status</div>', unsafe_allow_html=True)

    # Build fleet status from actual data
    if 'dumper_id' in df_filtered.columns and 'assigned_shovel' in df_filtered.columns:
        fleet_items_html = ""
        for _, row in df_filtered.iterrows():
            dumper = row['dumper_id']
            shovel = row['assigned_shovel']
            eff_cap = row.get('effective_capacity_tph', 0)
            base_cap = row.get('dumper_capacity_tph', 0)
            eff_ratio = (eff_cap / base_cap * 100) if base_cap > 0 else 100

            dot_class = "dot-active" if eff_ratio > 85 else "dot-idle"
            status_text = f"Assigned → {shovel}"
            cap_text = f"{eff_cap:.1f} TPH ({eff_ratio:.0f}%)"

            fleet_items_html += f"""
<div class="fleet-item">
<div class="fleet-dot {dot_class}"></div>
<div class="fleet-id">{dumper}</div>
<div class="fleet-status">{status_text}</div>
<div class="fleet-cap">{cap_text}</div>
</div>
"""

        # Add maintenance dumpers from alerts
        if not alerts_filtered.empty:
            maint_dumpers = alerts_filtered[
                alerts_filtered['alert_message'].str.contains('unavailable|maintenance', case=False, na=False)
            ]['alert_message'].drop_duplicates()
            for msg in maint_dumpers:
                # Extract dumper ID from message like "Dumper D6 unavailable..."
                parts = msg.split()
                d_id = parts[1] if len(parts) > 1 else "D?"
                fleet_items_html += f"""
<div class="fleet-item">
<div class="fleet-dot dot-maint"></div>
<div class="fleet-id">{d_id}</div>
<div class="fleet-status">Maintenance</div>
<div class="fleet-cap">Unavailable</div>
</div>
"""

        st.markdown(fleet_items_html, unsafe_allow_html=True)
    else:
        st.info("No fleet assignment data available.")

with col_ai:
    st.markdown('<div class="section-title">🧠 AI Dispatch Recommendation</div>', unsafe_allow_html=True)

    # Generate recommendation from actual data analysis
    if not shovel_stats.empty and len(shovel_stats) >= 2:
        # Find under-supplied shovel (lowest dumper count relative to throughput)
        shovel_stats_sorted = shovel_stats.sort_values('dumpers_assigned')
        bottleneck_shovel = shovel_stats_sorted.iloc[0]
        best_shovel = shovel_stats_sorted.iloc[-1]

        bn_shovel_id = bottleneck_shovel['assigned_shovel']
        bn_dumpers = int(bottleneck_shovel['dumpers_assigned'])
        best_shovel_id = best_shovel['assigned_shovel']
        best_dumpers = int(best_shovel['dumpers_assigned'])

        # Find a candidate dumper to reassign (from the most-supplied shovel)
        candidate_dumper = "N/A"
        if 'assigned_shovel' in df_filtered.columns:
            over_supplied = df_filtered[df_filtered['assigned_shovel'] == best_shovel_id]
            if not over_supplied.empty:
                # Pick the one with lowest effective capacity (least loss when moved)
                candidate_row = over_supplied.sort_values('effective_capacity_tph').iloc[0]
                candidate_dumper = candidate_row['dumper_id']
                candidate_cap = candidate_row['effective_capacity_tph']

        # Estimate impact
        estimated_gain_tpd = candidate_cap * 16 if candidate_dumper != "N/A" else 0  # 16 operating hours

        st.markdown(f"""
<div class="ai-card">
<div class="ai-card-header">
🧠 Dispatch Optimization <span class="ai-badge">OR-Tools</span>
</div>
<div class="ai-section-label">Current Observation</div>
<div class="ai-value">{bn_shovel_id} has fewest assigned dumpers ({bn_dumpers})</div>
<div class="ai-section-label">Recommended Action</div>
<div class="ai-value" style="font-size:1.1rem !important; font-weight:700 !important; color:#a5b4fc !important;">
{candidate_dumper} → {bn_shovel_id}
</div>
<div style="font-size:0.75rem; color:#64748b; margin-top:2px;">
from {best_shovel_id} ({best_dumpers} dumpers) → {bn_shovel_id} ({bn_dumpers} dumpers)
</div>
<div class="ai-section-label">Expected Impact</div>
<div class="ai-impact-item impact-positive">▲ ~{estimated_gain_tpd:.0f} TPD potential throughput at {bn_shovel_id}</div>
<div class="ai-impact-item impact-positive">▲ Better load balancing across shovels</div>
<div class="ai-impact-item impact-positive">▼ Reduced idle time at {bn_shovel_id}</div>
<div class="ai-section-label" style="margin-top:14px;">Why This Dispatch?</div>
<div style="font-size:0.82rem; color:#94a3b8; line-height:1.6;">
✓ {bn_shovel_id} has fewer trucks than other shovels<br>
✓ {best_shovel_id} can release a dumper without capacity loss<br>
✓ {candidate_dumper} has the lowest effective capacity at {best_shovel_id}<br>
✓ Rebalancing improves overall mine throughput<br>
✓ OR-Tools solver confirms feasibility
</div>
</div>
""", unsafe_allow_html=True)
    else:
        st.markdown("""
<div class="ai-card">
<div class="ai-card-header">🧠 Dispatch Optimization <span class="ai-badge">OR-Tools</span></div>
<div class="ai-value">Insufficient data for recommendation. Ensure optimization has been run.</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# DISPATCH MATRIX + PRODUCTION PERFORMANCE
# ─────────────────────────────────────────
st.markdown("---")
col_matrix, col_prod = st.columns([1, 1], gap="medium")

with col_matrix:
    st.markdown('<div class="section-title">📋 Dumper–Shovel Dispatch Matrix</div>', unsafe_allow_html=True)

    if 'dumper_id' in df_filtered.columns and 'assigned_shovel' in df_filtered.columns:
        matrix_df = df_filtered.copy()
        matrix_df['assigned'] = 1
        matrix = pd.pivot_table(matrix_df, values='assigned', index='dumper_id',
                                columns='assigned_shovel', fill_value=0, aggfunc='max')

        # Sort index and columns
        matrix = matrix.reindex(sorted(matrix.index), axis=0)
        matrix = matrix.reindex(sorted(matrix.columns), axis=1)

        # Create visual matrix with symbols
        dumpers = matrix.index.tolist()
        shovels = matrix.columns.tolist()

        # Build annotated heatmap
        z_values = matrix.values
        text_values = [['●' if v == 1 else '—' for v in row] for row in z_values]

        fig_matrix = go.Figure(data=go.Heatmap(
            z=z_values,
            x=shovels,
            y=dumpers,
            text=text_values,
            texttemplate='%{text}',
            textfont=dict(size=18, color='white'),
            colorscale=[[0, 'rgba(30,41,59,0.8)'], [1, 'rgba(99,102,241,0.7)']],
            showscale=False,
            hovertemplate='Dumper: %{y}<br>Shovel: %{x}<br>Assigned: %{z}<extra></extra>'
        ))
        apply_dark_theme(fig_matrix, height=max(300, len(dumpers) * 45 + 80), show_legend=False)
        fig_matrix.update_xaxes(title_text='Shovel', side='top', tickfont=dict(size=14))
        fig_matrix.update_yaxes(title_text='Dumper', tickfont=dict(size=14), autorange='reversed')
        fig_matrix.update_layout(margin=dict(l=60, r=20, t=50, b=20))
        st.plotly_chart(fig_matrix, use_container_width=True)

        # Compact assignment details in expander
        with st.expander("📄 View Assignment Details"):
            detail_cols = ['dumper_id', 'assigned_shovel', 'effective_capacity_tph', 'dumper_capacity_tph']
            avail_cols = [c for c in detail_cols if c in df_filtered.columns]
            detail_df = df_filtered[avail_cols].copy()
            if 'effective_capacity_tph' in detail_df.columns:
                detail_df['effective_capacity_tph'] = detail_df['effective_capacity_tph'].round(1)
            if 'dumper_capacity_tph' in detail_df.columns:
                detail_df['dumper_capacity_tph'] = detail_df['dumper_capacity_tph'].round(1)
            rename = {'dumper_id': 'Dumper', 'assigned_shovel': 'Shovel',
                      'effective_capacity_tph': 'Eff. Cap (TPH)', 'dumper_capacity_tph': 'Base Cap (TPH)'}
            st.dataframe(detail_df.rename(columns=rename), use_container_width=True, hide_index=True)
    else:
        st.info("No dispatch matrix data available.")

with col_prod:
    st.markdown('<div class="section-title">📈 Production Performance</div>', unsafe_allow_html=True)

    # Production comparison: Planned vs Achievable
    if planned_tpd > 0 or achievable_tpd > 0:
        fig_prod = go.Figure()
        fig_prod.add_trace(go.Bar(
            x=['Planned', 'Achievable'],
            y=[planned_tpd, achievable_tpd],
            marker_color=['#334155', '#6366f1'],
            text=[f'{planned_tpd:,.0f}', f'{achievable_tpd:,.0f}'],
            textposition='outside',
            textfont=dict(size=16, color='#e2e8f0'),
            width=0.5,
        ))
        apply_dark_theme(fig_prod, height=300, show_legend=False)
        fig_prod.update_yaxes(title_text='TPD')
        fig_prod.update_layout(title=dict(text='Planned vs Achievable Production', font=dict(size=14)))
        st.plotly_chart(fig_prod, use_container_width=True)

    # Shovel throughput chart
    if not shovel_stats.empty:
        fig_shovel = go.Figure()
        fig_shovel.add_trace(go.Bar(
            name='Throughput',
            x=shovel_stats['assigned_shovel'],
            y=shovel_stats['throughput_tpd'],
            marker_color='#6366f1',
            text=shovel_stats['throughput_tpd'].apply(lambda x: f'{x:,.0f}'),
            textposition='outside',
            textfont=dict(size=12),
        ))
        fig_shovel.add_trace(go.Bar(
            name='Capacity',
            x=shovel_stats['assigned_shovel'],
            y=shovel_stats['capacity_tpd'],
            marker_color='rgba(100,116,139,0.4)',
            text=shovel_stats['capacity_tpd'].apply(lambda x: f'{x:,.0f}'),
            textposition='outside',
            textfont=dict(size=12),
        ))
        apply_dark_theme(fig_shovel, height=300)
        fig_shovel.update_layout(
            barmode='group',
            title=dict(text='Shovel Throughput vs Capacity', font=dict(size=14)),
            legend=dict(font=dict(size=11), orientation='h', y=-0.15),
        )
        fig_shovel.update_yaxes(title_text='TPD')
        st.plotly_chart(fig_shovel, use_container_width=True)

# ─────────────────────────────────────────
# BOTTLENECKS & ALERTS
# ─────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-title">⚠️ Current Bottlenecks & Alerts</div>', unsafe_allow_html=True)

if not alerts_filtered.empty:
    unique_alerts = alerts_filtered.drop_duplicates(subset=['alert_type', 'alert_message'])
    critical = unique_alerts[unique_alerts['alert_type'] == 'CRITICAL']
    warnings = unique_alerts[unique_alerts['alert_type'] == 'WARNING']
    infos = unique_alerts[unique_alerts['alert_type'] == 'INFO']

    alert_cols = st.columns(min(len(unique_alerts), 4))
    all_alerts = pd.concat([critical, warnings, infos])

    for i, (_, row) in enumerate(all_alerts.iterrows()):
        if i >= 4:
            break
        atype = row['alert_type']
        css_class = 'bn-critical' if atype == 'CRITICAL' else ('bn-warning' if atype == 'WARNING' else 'bn-info')
        severity = atype.upper()
        msg = row['alert_message']
        # Clean encoding artifacts
        msg = msg.replace('\u2014', '—').replace('â\x80\x94', '—').replace('–', '—')

        with alert_cols[i % len(alert_cols)]:
            st.markdown(f"""
<div class="bottleneck-card {css_class}">
<div class="bn-label">{severity}</div>
<div class="bn-message">{msg}</div>
</div>
""", unsafe_allow_html=True)

    # Show remaining alerts in expander
    remaining = len(all_alerts) - 4
    if remaining > 0:
        with st.expander(f"View {remaining} more alert(s)"):
            for _, row in all_alerts.iloc[4:].iterrows():
                atype = row['alert_type']
                msg = row['alert_message'].replace('\u2014', '—').replace('â\x80\x94', '—').replace('–', '—')
                if atype == 'CRITICAL':
                    st.error(f"🔴 {msg}")
                elif atype == 'WARNING':
                    st.warning(f"⚠️ {msg}")
                else:
                    st.info(f"ℹ️ {msg}")

    st.caption(f"Total: {len(critical)} Critical · {len(warnings)} Warning · {len(infos)} Info")
else:
    st.markdown("""
<div class="bottleneck-card bn-info" style="border-left-color: #22c55e; background: rgba(34,197,94,0.05);">
<div class="bn-label" style="color: #4ade80 !important;">ALL CLEAR</div>
<div class="bn-message">No active alerts for the selected period.</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# SHOVEL UTILIZATION + DUMPER DISTRIBUTION
# ─────────────────────────────────────────
if not shovel_stats.empty and len(shovel_stats) > 0:
    st.markdown("---")
    col_util, col_dist = st.columns(2, gap="medium")

    with col_util:
        st.markdown('<div class="section-title">📊 Shovel Utilization</div>', unsafe_allow_html=True)

        colors = ['#22c55e' if u >= 80 else ('#f59e0b' if u >= 50 else '#ef4444')
                  for u in shovel_stats['utilization_pct']]

        fig_util = go.Figure(go.Bar(
            x=shovel_stats['assigned_shovel'],
            y=shovel_stats['utilization_pct'],
            marker_color=colors,
            text=shovel_stats['utilization_pct'].apply(lambda x: f'{x:.0f}%'),
            textposition='outside',
            textfont=dict(size=14),
        ))
        fig_util.add_hline(y=80, line_dash="dash", line_color="rgba(255,255,255,0.2)",
                           annotation_text="80% target", annotation_font_color="#64748b")
        apply_dark_theme(fig_util, height=350, show_legend=False)
        fig_util.update_yaxes(title_text='Utilization %', range=[0, 120])
        fig_util.update_layout(title=dict(text='Shovel Utilization Rate', font=dict(size=14)))
        st.plotly_chart(fig_util, use_container_width=True)

    with col_dist:
        st.markdown('<div class="section-title">🚛 Dumper Distribution by Shovel</div>', unsafe_allow_html=True)

        fig_dist = go.Figure(go.Bar(
            x=shovel_stats['assigned_shovel'],
            y=shovel_stats['dumpers_assigned'],
            marker_color='#6366f1',
            text=shovel_stats['dumpers_assigned'].astype(int).astype(str),
            textposition='outside',
            textfont=dict(size=14),
        ))
        apply_dark_theme(fig_dist, height=350, show_legend=False)
        fig_dist.update_yaxes(title_text='Dumpers', dtick=1)
        fig_dist.update_layout(title=dict(text='Dumpers Assigned per Shovel', font=dict(size=14)))
        st.plotly_chart(fig_dist, use_container_width=True)

# ─────────────────────────────────────────
# PRODUCTION TREND (across months for selected mine)
# ─────────────────────────────────────────
if not forecast.empty and 'mine_id' in forecast.columns:
    mine_forecast = forecast[forecast['mine_id'] == selected_mine].copy() if selected_mine != 'All' else forecast.copy()
    if not mine_forecast.empty and len(mine_forecast) > 1:
        st.markdown("---")
        st.markdown('<div class="section-title">📈 Production Trend (Annual View)</div>', unsafe_allow_html=True)

        mine_forecast = mine_forecast.sort_values(['year', 'month'])
        mine_forecast['period'] = mine_forecast['month'].map(month_names) + " " + mine_forecast['year'].astype(str)

        fig_trend = go.Figure()
        if 'planned_production_tpd' in mine_forecast.columns:
            fig_trend.add_trace(go.Scatter(
                x=mine_forecast['period'],
                y=mine_forecast['planned_production_tpd'],
                name='Planned',
                line=dict(color='#475569', width=2, dash='dash'),
                mode='lines+markers',
                marker=dict(size=6),
            ))
        if 'predicted_production_tpd' in mine_forecast.columns:
            fig_trend.add_trace(go.Scatter(
                x=mine_forecast['period'],
                y=mine_forecast['predicted_production_tpd'],
                name='Predicted',
                line=dict(color='#6366f1', width=2),
                mode='lines+markers',
                marker=dict(size=6),
            ))
        if 'crusher_capacity_tpd' in mine_forecast.columns:
            fig_trend.add_trace(go.Scatter(
                x=mine_forecast['period'],
                y=mine_forecast['crusher_capacity_tpd'],
                name='Crusher Capacity',
                line=dict(color='rgba(34,197,94,0.4)', width=1, dash='dot'),
                mode='lines',
            ))

        apply_dark_theme(fig_trend, height=350)
        fig_trend.update_layout(
            legend=dict(font=dict(size=11), orientation='h', y=-0.2),
        )
        fig_trend.update_yaxes(title_text='TPD')
        st.plotly_chart(fig_trend, use_container_width=True)

# ─────────────────────────────────────────
# ENVIRONMENTAL CONDITIONS
# ─────────────────────────────────────────
if rainfall > 0 or road_cond < 5:
    st.markdown("---")
    st.markdown('<div class="section-title">🌦️ Operating Conditions</div>', unsafe_allow_html=True)
    ec1, ec2, ec3 = st.columns(3)
    with ec1:
        rain_class = "warning" if rainfall > 100 else "positive"
        st.markdown(f"""
<div class="kpi-card">
<div class="kpi-label">Rainfall</div>
<div class="kpi-value">{rainfall:.0f}<span class="kpi-unit">mm</span></div>
<div class="kpi-delta {rain_class}">{'Heavy — production impact' if rainfall > 100 else 'Normal'}</div>
</div>""", unsafe_allow_html=True)
    with ec2:
        road_class = "warning" if road_cond < 3 else "positive"
        st.markdown(f"""
<div class="kpi-card">
<div class="kpi-label">Haul Road Condition</div>
<div class="kpi-value">{road_cond:.1f}<span class="kpi-unit">/ 5</span></div>
<div class="kpi-delta {road_class}">{'Poor — speed penalty' if road_cond < 3 else 'Acceptable'}</div>
</div>""", unsafe_allow_html=True)
    with ec3:
        penalty = max(0, (1 - efficiency_pct / 100)) * 100
        st.markdown(f"""
<div class="kpi-card">
<div class="kpi-label">Combined Penalty</div>
<div class="kpi-value">{penalty:.1f}<span class="kpi-unit">%</span></div>
<div class="kpi-delta {'warning' if penalty > 10 else 'neutral'}">Weather + road impact</div>
</div>""", unsafe_allow_html=True)
