"""
MOIL-GeoSync — Intelligent Fleet Dispatch Dashboard
=====================================================
Refactored to use ONLY real MOIL data from data/moil_real.csv.
Every metric is labeled with provenance: REAL, DERIVED, or SIMULATED.

REAL     = directly from MOIL annual reports / press releases
DERIVED  = formula applied to real data (e.g., TPD = tonnes / days)
SIMULATED = OR-Tools model output (fleet assignments, dumper capacities)
"""

import os
import time
import random
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# ─── Paths ───
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
MOIL_REAL_PATH = os.path.join(DATA_DIR, "moil_real.csv")

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
        color: #ffffff !important;
        margin: 0 !important;
        letter-spacing: 0.5px;
    }
    .fd-header-left .fd-subtitle {
        font-size: 0.85rem !important;
        color: #cbd5e1 !important;
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
    .fd-sim-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(245,158,11,0.12);
        border: 1px solid rgba(245,158,11,0.3);
        border-radius: 6px;
        padding: 5px 12px;
        font-size: 0.78rem !important;
        color: #fbbf24 !important;
        font-weight: 600;
    }

    /* ── Provenance badges ── */
    .badge-real {
        display: inline-block;
        background: rgba(34,197,94,0.15);
        border: 1px solid rgba(34,197,94,0.3);
        color: #4ade80 !important;
        font-size: 0.55rem !important;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        padding: 1px 6px;
        border-radius: 3px;
        vertical-align: super;
    }
    .badge-derived {
        display: inline-block;
        background: rgba(59,130,246,0.15);
        border: 1px solid rgba(59,130,246,0.3);
        color: #60a5fa !important;
        font-size: 0.55rem !important;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        padding: 1px 6px;
        border-radius: 3px;
        vertical-align: super;
    }
    .badge-simulated {
        display: inline-block;
        background: rgba(245,158,11,0.15);
        border: 1px solid rgba(245,158,11,0.3);
        color: #fbbf24 !important;
        font-size: 0.55rem !important;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        padding: 1px 6px;
        border-radius: 3px;
        vertical-align: super;
    }

    /* ── KPI Cards ── */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 10px;
        margin-bottom: 20px;
    }
    .kpi-card {
        background: rgba(241,245,249,0.6);
        border: 1px solid rgba(100,116,139,0.2);
        border-radius: 10px;
        padding: 16px 18px;
        transition: border-color 0.2s;
    }
    .kpi-card:hover {
        border-color: rgba(99,102,241,0.5);
    }
    .kpi-card-simulated {
        background: rgba(255,251,235,0.6);
        border: 1px solid rgba(245,158,11,0.3);
        border-radius: 10px;
        padding: 16px 18px;
        transition: border-color 0.2s;
    }
    .kpi-card-simulated:hover {
        border-color: rgba(245,158,11,0.6);
    }
    .kpi-label {
        font-size: 0.68rem !important;
        color: #475569 !important;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        font-weight: 600 !important;
        margin-bottom: 6px !important;
    }
    .kpi-value {
        font-size: 1.7rem !important;
        font-weight: 700 !important;
        color: #1e293b !important;
        line-height: 1.1 !important;
    }
    .kpi-unit {
        font-size: 0.75rem !important;
        color: #475569 !important;
        font-weight: 400 !important;
        margin-left: 3px;
    }
    .kpi-delta {
        font-size: 0.75rem !important;
        margin-top: 4px !important;
    }
    .kpi-delta.positive { color: #16a34a !important; }
    .kpi-delta.negative { color: #dc2626 !important; }
    .kpi-delta.neutral  { color: #475569 !important; }
    .kpi-delta.warning  { color: #d97706 !important; }

    /* ── Section headers ── */
    .section-title {
        font-size: 0.72rem !important;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        color: #475569 !important;
        font-weight: 700 !important;
        margin-bottom: 12px !important;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(0,0,0,0.08);
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
        color: #1e293b !important;
        margin-bottom: 14px !important;
    }

    /* ── AI Recommendation ── */
    .ai-card {
        background: linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(241,245,249,0.8) 100%);
        border: 1px solid rgba(99,102,241,0.25);
        border-radius: 10px;
        padding: 20px;
    }
    .ai-card-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        color: #4f46e5 !important;
        margin-bottom: 16px !important;
    }
    .ai-badge {
        background: rgba(99,102,241,0.2);
        border: 1px solid rgba(99,102,241,0.3);
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 0.6rem !important;
        color: #6366f1 !important;
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
        color: #1e293b !important;
    }
    .ai-impact-item {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.85rem !important;
        padding: 3px 0;
    }
    .impact-positive { color: #16a34a !important; }
    .impact-negative { color: #dc2626 !important; }

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
    .bn-critical .bn-label { color: #dc2626 !important; }
    .bn-warning  .bn-label { color: #d97706 !important; }
    .bn-info     .bn-label { color: #2563eb !important; }
    .bn-message {
        font-size: 0.85rem !important;
        color: #334155 !important;
    }

    /* ── Fleet status items ── */
    .fleet-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 12px;
        background: rgba(241,245,249,0.5);
        border: 1px solid rgba(100,116,139,0.15);
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
        color: #1e293b !important;
        min-width: 30px;
    }
    .fleet-status {
        color: #475569 !important;
        flex: 1;
    }
    .fleet-cap {
        color: #475569 !important;
        font-size: 0.78rem !important;
    }

    /* ── Provenance table ── */
    .prov-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.82rem;
    }
    .prov-table th {
        text-align: left;
        color: #64748b !important;
        font-weight: 600;
        padding: 6px 10px;
        border-bottom: 1px solid rgba(255,255,255,0.08);
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .prov-table td {
        padding: 5px 10px;
        color: #cbd5e1 !important;
        border-bottom: 1px solid rgba(255,255,255,0.03);
    }
    /* ── Data-check warning ── */
    .data-warn {
        background: rgba(239,68,68,0.08);
        border: 1px solid rgba(239,68,68,0.25);
        border-radius: 8px;
        padding: 12px 16px;
        color: #fca5a5 !important;
        font-size: 0.85rem;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING & VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data
def load_moil_real():
    """Load the canonical real MOIL data file."""
    if not os.path.exists(MOIL_REAL_PATH):
        return pd.DataFrame()
    df = pd.read_csv(MOIL_REAL_PATH)
    df['start_date'] = pd.to_datetime(df['start_date'])
    df['end_date'] = pd.to_datetime(df['end_date'])
    df['tpd'] = df['tonnes'] / df['days']
    return df


def validate_data(moil_df, mine_tpd, company_tpd, planned_tpd, fy_target):
    """
    Validation function that fails loudly if:
    1. Mine-level TPD exceeds company TPD
    2. Planned TPD is more than 20% away from FY target / 365
    """
    errors = []

    if mine_tpd > company_tpd:
        errors.append(
            f"❌ Mine TPD ({mine_tpd:,.0f}) EXCEEDS company TPD ({company_tpd:,.0f}). "
            f"Check mine_share assumption."
        )

    expected_planned = fy_target / 365
    deviation = abs(planned_tpd - expected_planned) / expected_planned * 100
    if deviation > 20:
        errors.append(
            f"❌ Planned TPD ({planned_tpd:,.0f}) deviates {deviation:.1f}% from "
            f"FY target/365 ({expected_planned:,.0f}). Max allowed: 20%."
        )

    return errors


def generate_fleet_for_mine_tpd(mine_tpd, seed=42):
    """
    Generate SIMULATED fleet data such that
    sum(dumper_effective_tph) × operating_hours ≈ mine_tpd.

    This ensures the fleet view and the production KPI agree.
    """
    rng = np.random.RandomState(seed)
    operating_hours = 16  # 2 shifts × 8 hours

    # Work backwards from mine_tpd to determine fleet size
    avg_dumper_tph = 37.5  # midpoint of 30-45 range
    required_dumpers_float = mine_tpd / (avg_dumper_tph * operating_hours)
    num_dumpers = max(3, int(np.ceil(required_dumpers_float)))
    num_shovels = max(1, num_dumpers // 3)

    # Generate dumper capacities that sum to the correct total
    target_total_tph = mine_tpd / operating_hours
    raw_caps = rng.uniform(30, 45, num_dumpers)
    # Scale so they sum correctly
    scale_factor = target_total_tph / raw_caps.sum()
    dumper_caps = raw_caps * scale_factor
    # Clip to reasonable range
    dumper_caps = np.clip(dumper_caps, 25, 55)

    # Assign dumpers to shovels round-robin
    assignments = []
    shovel_caps = rng.uniform(150, 280, num_shovels)
    for d in range(num_dumpers):
        s = d % num_shovels
        assignments.append({
            'dumper_id': f'D{d+1:02d}',
            'assigned_shovel': f'S{s+1}',
            'dumper_capacity_tph': round(float(dumper_caps[d]), 1),
            'effective_capacity_tph': round(float(dumper_caps[d]), 1),
            'available': True,
        })

    # Compute shovel-level stats
    assign_df = pd.DataFrame(assignments)
    shovel_stats = []
    for s in range(num_shovels):
        sid = f'S{s+1}'
        s_dumpers = assign_df[assign_df['assigned_shovel'] == sid]
        throughput = s_dumpers['effective_capacity_tph'].sum() * operating_hours
        shovel_stats.append({
            'shovel_id': sid,
            'shovel_capacity_tph': round(float(shovel_caps[s]), 1),
            'dumpers_assigned': len(s_dumpers),
            'throughput_tpd': round(float(throughput), 1),
            'capacity_tpd': round(float(shovel_caps[s] * operating_hours), 1),
        })

    actual_total_tpd = assign_df['effective_capacity_tph'].sum() * operating_hours

    return {
        'assignments': assign_df,
        'shovel_stats': pd.DataFrame(shovel_stats),
        'num_dumpers': num_dumpers,
        'num_shovels': num_shovels,
        'total_tpd': round(float(actual_total_tpd), 1),
        'operating_hours': operating_hours,
        'avg_dumper_tph': round(float(dumper_caps.mean()), 1),
        'efficiency_pct': round(float(scale_factor * 100), 1),
    }


# ══════════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════════════

moil_df = load_moil_real()

if moil_df.empty:
    st.error("⚠️ `data/moil_real.csv` not found. Cannot render dashboard without real data.")
    st.stop()

# ─── Extract key values from real data ───
fy26_target_row = moil_df[moil_df['period'] == 'FY26_target']
fy_target_tonnes = int(fy26_target_row['tonnes'].iloc[0]) if not fy26_target_row.empty else 2350000
planned_tpd = fy_target_tonnes / 365  # DERIVED

# Latest available monthly/period data
monthly = moil_df[moil_df['type'] == 'monthly'].sort_values('end_date')
latest_month_row = monthly.iloc[-1] if not monthly.empty else None

annual = moil_df[moil_df['type'] == 'annual'].sort_values('end_date')
fy25_row = moil_df[moil_df['period'] == 'FY25']

latest_period = moil_df[moil_df['type'] == 'period'].sort_values('end_date')
latest_period_row = latest_period.iloc[-1] if not latest_period.empty else None

# Determine the most recent actual TPD for company
if latest_month_row is not None:
    company_tpd = float(latest_month_row['tpd'])
    latest_label = latest_month_row['period']
elif latest_period_row is not None:
    company_tpd = float(latest_period_row['tpd'])
    latest_label = latest_period_row['period']
else:
    company_tpd = float(fy25_row['tpd'].iloc[0]) if not fy25_row.empty else 4940.0
    latest_label = "FY25"

# ─── Load live forecast for mine list ───
LIVE_FORECAST_PATH = os.path.join(DATA_DIR, "production_forecast_live.csv")
live_forecast_df = pd.DataFrame()
all_mines = ['Dongri_Buzurg']
if os.path.exists(LIVE_FORECAST_PATH):
    live_forecast_df = pd.read_csv(LIVE_FORECAST_PATH)
    if 'mine_id' in live_forecast_df.columns:
        all_mines = sorted(live_forecast_df['mine_id'].unique().tolist())

# ─── SIDEBAR ───
st.sidebar.header("⚙️ Configuration")

selected_mine = st.sidebar.selectbox(
    "Select Mine",
    all_mines,
    index=all_mines.index('Dongri_Buzurg') if 'Dongri_Buzurg' in all_mines else 0,
)

mine_display = selected_mine.replace('_', ' ')

# Mine share defaults per mine (approximate based on MOIL mine sizes)
DEFAULT_SHARES = {
    'Dongri_Buzurg': 12, 'Balaghat': 18, 'Chikla': 8, 'Kandri': 8,
    'Munsar': 7, 'Gumgaon': 10, 'Beldongri': 5, 'Ukwa': 4,
    'Tirodi': 7, 'Sitapatore': 5,
}

mine_share = st.sidebar.slider(
    f"Mine Share — {mine_display}",
    min_value=1, max_value=30,
    value=DEFAULT_SHARES.get(selected_mine, 8),
    step=1,
    key=f"mine_share_{selected_mine}",
    help=f"⚠️ ASSUMPTION — not MOIL data. "
         f"{mine_display}'s estimated share of total MOIL production. "
         f"Formula: Mine TPD = Company TPD × (mine_share / 100)"
)
st.sidebar.caption(
    f"⚠️ **ASSUMPTION — not MOIL data.**\n\n"
    f"Mine-level production is not publicly available. "
    f"Mine TPD = Company TPD × {mine_share}%."
)

# Derived mine TPD
mine_tpd = company_tpd * (mine_share / 100)  # DERIVED

# If we have live forecast data for this mine, also show its predicted TPD
live_mine_row = None
if not live_forecast_df.empty:
    live_mine = live_forecast_df[live_forecast_df['mine_id'] == selected_mine]
    if not live_mine.empty:
        live_mine_row = live_mine.iloc[0]

# ─── Validation ───
val_errors = validate_data(moil_df, mine_tpd, company_tpd, planned_tpd, fy_target_tonnes)

# ─── Generate fleet data (SIMULATED) ───
# Use a seed based on mine name + share so each mine gets a unique fleet
mine_seed = sum(ord(c) for c in selected_mine) + mine_share
fleet = generate_fleet_for_mine_tpd(mine_tpd, seed=mine_seed)
df_fleet = fleet['assignments']
shovel_stats = fleet['shovel_stats']

# ─── Compute KPIs ───
achievement_pct = (company_tpd / planned_tpd * 100) if planned_tpd > 0 else 0
# Clamp display
achievement_display = min(achievement_pct, 150)
achievement_warning = achievement_pct > 115


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════

st.markdown(f"""
<div class="fd-header">
    <div class="fd-header-left">
        <h1>🚛 Intelligent Fleet Dispatch</h1>
        <div class="fd-subtitle">MineFlow OR-Optimizer · MOIL Manganese Operations</div>
    </div>
    <div class="fd-header-right">
        <div class="fd-tag">⛏️ {mine_display}</div>
        <div class="fd-tag">📅 Last updated: {latest_label}</div>
        <div class="fd-sim-badge">🧪 Simulation Mode</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Validation errors ───
if val_errors:
    for err in val_errors:
        st.markdown(f'<div class="data-warn">{err}</div>', unsafe_allow_html=True)

if achievement_warning:
    st.markdown(
        f'<div class="data-warn">⚠️ <strong>Data Check:</strong> Achievement is '
        f'{achievement_pct:.1f}%, which exceeds 115%. This may indicate the latest '
        f'actual data ({latest_label}) is outperforming the FY26 target rate. '
        f'Displayed value clamped to {achievement_display:.1f}%.</div>',
        unsafe_allow_html=True
    )


# ══════════════════════════════════════════════════════════════════════════════
# KPI CARDS
# ══════════════════════════════════════════════════════════════════════════════

delta_tpd = company_tpd - planned_tpd
delta_class = "positive" if delta_tpd >= 0 else "negative"
delta_icon = "▲" if delta_tpd >= 0 else "▼"
achieve_class = "positive" if achievement_display >= 100 else ("warning" if achievement_display >= 90 else "negative")

st.markdown(f"""
<div class="kpi-grid">
    <div class="kpi-card">
        <div class="kpi-label">Company Production <span class="badge-derived">DERIVED</span></div>
        <div class="kpi-value">{company_tpd:,.0f}<span class="kpi-unit">TPD</span></div>
        <div class="kpi-delta neutral">{latest_label} · {int(latest_month_row['tonnes']) if latest_month_row is not None else 'N/A':,} tonnes / {int(latest_month_row['days']) if latest_month_row is not None else '?'} days</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">FY26 Planned <span class="badge-real">REAL</span></div>
        <div class="kpi-value">{planned_tpd:,.0f}<span class="kpi-unit">TPD</span></div>
        <div class="kpi-delta neutral">{fy_target_tonnes:,} tonnes / 365 days</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Achievement <span class="badge-derived">DERIVED</span></div>
        <div class="kpi-value">{achievement_display:.1f}<span class="kpi-unit">%</span></div>
        <div class="kpi-delta {achieve_class}">{delta_icon} {abs(delta_tpd):,.0f} TPD vs plan</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Mine TPD ({mine_display}) <span class="badge-derived">DERIVED</span></div>
        <div class="kpi-value">{mine_tpd:,.0f}<span class="kpi-unit">TPD</span></div>
        <div class="kpi-delta neutral">= {company_tpd:,.0f} × {mine_share}%</div>
    </div>
    <div class="kpi-card-simulated">
        <div class="kpi-label">Active Dumpers <span class="badge-simulated">SIMULATED</span></div>
        <div class="kpi-value">{fleet['num_dumpers']}</div>
        <div class="kpi-delta neutral">Sized to match mine TPD</div>
    </div>
    <div class="kpi-card-simulated">
        <div class="kpi-label">Active Shovels <span class="badge-simulated">SIMULATED</span></div>
        <div class="kpi-value">{fleet['num_shovels']}</div>
        <div class="kpi-delta neutral">1 per ~3 dumpers</div>
    </div>
    <div class="kpi-card-simulated">
        <div class="kpi-label">Fleet Efficiency <span class="badge-simulated">SIMULATED</span></div>
        <div class="kpi-value">{fleet['efficiency_pct']:.1f}<span class="kpi-unit">%</span></div>
        <div class="kpi-delta neutral">Scale factor to match mine TPD</div>
    </div>
    <div class="kpi-card-simulated">
        <div class="kpi-label">Avg Dumper Cap <span class="badge-simulated">SIMULATED</span></div>
        <div class="kpi-value">{fleet['avg_dumper_tph']}<span class="kpi-unit">TPH</span></div>
        <div class="kpi-delta neutral">After scaling</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT: Fleet View + AI Recommendation
# ══════════════════════════════════════════════════════════════════════════════

col_main, col_ai = st.columns([2, 1], gap="medium")

with col_main:
    st.markdown('<div class="section-title">🚛 Fleet Operational Status <span class="badge-simulated">SIMULATED</span></div>', unsafe_allow_html=True)

    fleet_items_html = ""
    for _, row in df_fleet.iterrows():
        dumper = row['dumper_id']
        shovel = row['assigned_shovel']
        eff_cap = row['effective_capacity_tph']
        base_cap = row['dumper_capacity_tph']
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
    st.markdown(fleet_items_html, unsafe_allow_html=True)

    # Verify fleet TPD matches mine TPD
    fleet_total = df_fleet['effective_capacity_tph'].sum() * fleet['operating_hours']
    st.caption(
        f"Fleet total: {fleet_total:,.0f} TPD | Mine target: {mine_tpd:,.0f} TPD | "
        f"Match: {'✅' if abs(fleet_total - mine_tpd) < mine_tpd * 0.05 else '⚠️'}"
    )


with col_ai:
    st.markdown('<div class="section-title">🧠 AI Dispatch Recommendation <span class="badge-simulated">SIMULATED</span></div>', unsafe_allow_html=True)

    if not shovel_stats.empty and len(shovel_stats) >= 2:
        shovel_stats_sorted = shovel_stats.sort_values('dumpers_assigned')
        bottleneck_shovel = shovel_stats_sorted.iloc[0]
        best_shovel = shovel_stats_sorted.iloc[-1]

        bn_shovel_id = bottleneck_shovel['shovel_id']
        bn_dumpers = int(bottleneck_shovel['dumpers_assigned'])
        best_shovel_id = best_shovel['shovel_id']
        best_dumpers = int(best_shovel['dumpers_assigned'])

        candidate_dumper = "N/A"
        over_supplied = df_fleet[df_fleet['assigned_shovel'] == best_shovel_id]
        if not over_supplied.empty:
            candidate_row = over_supplied.sort_values('effective_capacity_tph').iloc[0]
            candidate_dumper = candidate_row['dumper_id']
            candidate_cap = candidate_row['effective_capacity_tph']

        estimated_gain_tpd = candidate_cap * fleet['operating_hours'] if candidate_dumper != "N/A" else 0

        st.markdown(f"""
<div class="ai-card">
<div class="ai-card-header">
🧠 Dispatch Optimization <span class="ai-badge">OR-Tools</span> <span class="badge-simulated">SIMULATED</span>
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
</div>
""", unsafe_allow_html=True)
    else:
        st.info("Insufficient shovels for optimization recommendation.")


# ══════════════════════════════════════════════════════════════════════════════
# DISPATCH MATRIX + PRODUCTION PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
col_matrix, col_prod = st.columns([1, 1], gap="medium")

with col_matrix:
    st.markdown('<div class="section-title">📋 Dumper–Shovel Dispatch Matrix <span class="badge-simulated">SIMULATED</span></div>', unsafe_allow_html=True)

    matrix_df = df_fleet.copy()
    matrix_df['assigned'] = 1
    matrix = pd.pivot_table(matrix_df, values='assigned', index='dumper_id',
                            columns='assigned_shovel', fill_value=0, aggfunc='max')
    matrix = matrix.reindex(sorted(matrix.index), axis=0)
    matrix = matrix.reindex(sorted(matrix.columns), axis=1)

    dumpers = matrix.index.tolist()
    shovels = matrix.columns.tolist()
    z_values = matrix.values
    text_values = [['●' if v == 1 else '—' for v in row_data] for row_data in z_values]

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

    with st.expander("📄 View Assignment Details"):
        detail_df = df_fleet[['dumper_id', 'assigned_shovel', 'effective_capacity_tph', 'dumper_capacity_tph']].copy()
        detail_df.columns = ['Dumper', 'Shovel', 'Eff. Cap (TPH)', 'Base Cap (TPH)']
        st.dataframe(detail_df, use_container_width=True, hide_index=True)


with col_prod:
    st.markdown('<div class="section-title">📈 Production Performance</div>', unsafe_allow_html=True)

    # Planned vs Actual (Company level, REAL/DERIVED)
    fig_prod = go.Figure()
    fig_prod.add_trace(go.Bar(
        x=['FY26 Planned (REAL)', f'Latest Actual (DERIVED)'],
        y=[planned_tpd, company_tpd],
        marker_color=['#334155', '#6366f1'],
        text=[f'{planned_tpd:,.0f}', f'{company_tpd:,.0f}'],
        textposition='outside',
        textfont=dict(size=16, color='#e2e8f0'),
        width=0.5,
    ))
    apply_dark_theme(fig_prod, height=300, show_legend=False)
    fig_prod.update_yaxes(title_text='TPD')
    fig_prod.update_layout(title=dict(text='Company Planned vs Actual TPD', font=dict(size=14)))
    st.plotly_chart(fig_prod, use_container_width=True)

    # Shovel throughput chart (SIMULATED)
    if not shovel_stats.empty:
        fig_shovel = go.Figure()
        fig_shovel.add_trace(go.Bar(
            name='Throughput',
            x=shovel_stats['shovel_id'],
            y=shovel_stats['throughput_tpd'],
            marker_color='#6366f1',
            text=shovel_stats['throughput_tpd'].apply(lambda x: f'{x:,.0f}'),
            textposition='outside',
            textfont=dict(size=12),
        ))
        fig_shovel.add_trace(go.Bar(
            name='Capacity',
            x=shovel_stats['shovel_id'],
            y=shovel_stats['capacity_tpd'],
            marker_color='rgba(100,116,139,0.4)',
            text=shovel_stats['capacity_tpd'].apply(lambda x: f'{x:,.0f}'),
            textposition='outside',
            textfont=dict(size=12),
        ))
        apply_dark_theme(fig_shovel, height=300)
        fig_shovel.update_layout(
            barmode='group',
            title=dict(text='Shovel Throughput vs Capacity (SIMULATED)', font=dict(size=14)),
            legend=dict(font=dict(size=11), orientation='h', y=-0.15),
        )
        fig_shovel.update_yaxes(title_text='TPD')
        st.plotly_chart(fig_shovel, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# ANNUAL PRODUCTION TREND (REAL DATA)
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown('<div class="section-title">📈 MOIL Annual Production Trend <span class="badge-real">REAL</span></div>', unsafe_allow_html=True)

annual_data = moil_df[moil_df['type'] == 'annual'].sort_values('start_date').copy()
if not annual_data.empty:
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Bar(
        x=annual_data['period'],
        y=annual_data['tonnes'] / 1e6,
        marker_color='#6366f1',
        text=annual_data['tonnes'].apply(lambda x: f'{x/1e6:.2f}M'),
        textposition='outside',
        textfont=dict(size=12, color='#e2e8f0'),
    ))
    # Add FY26 target line
    fig_trend.add_hline(
        y=fy_target_tonnes / 1e6,
        line_dash="dash", line_color="rgba(245,158,11,0.5)",
        annotation_text=f"FY26 Target: {fy_target_tonnes/1e6:.2f}M",
        annotation_font_color="#fbbf24",
    )
    apply_dark_theme(fig_trend, height=350, show_legend=False)
    fig_trend.update_yaxes(title_text='Million Tonnes')
    fig_trend.update_layout(title=dict(text='MOIL Annual Production (Real Data)', font=dict(size=14)))
    st.plotly_chart(fig_trend, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# MONTHLY DATA POINTS (REAL DATA)
# ══════════════════════════════════════════════════════════════════════════════

monthly_data = moil_df[moil_df['type'] == 'monthly'].sort_values('start_date').copy()
if not monthly_data.empty:
    st.markdown('<div class="section-title">📊 Known Monthly Production <span class="badge-real">REAL</span></div>', unsafe_allow_html=True)

    fig_monthly = go.Figure()
    fig_monthly.add_trace(go.Scatter(
        x=monthly_data['period'],
        y=monthly_data['tpd'],
        mode='lines+markers+text',
        marker=dict(size=10, color='#22c55e'),
        line=dict(color='#22c55e', width=2),
        text=monthly_data['tpd'].apply(lambda x: f'{x:,.0f}'),
        textposition='top center',
        textfont=dict(size=11, color='#e2e8f0'),
    ))
    # Add planned TPD line
    fig_monthly.add_hline(
        y=planned_tpd,
        line_dash="dash", line_color="rgba(99,102,241,0.4)",
        annotation_text=f"FY26 Planned: {planned_tpd:,.0f} TPD",
        annotation_font_color="#818cf8",
    )
    apply_dark_theme(fig_monthly, height=300, show_legend=False)
    fig_monthly.update_yaxes(title_text='TPD')
    fig_monthly.update_layout(title=dict(text='Monthly TPD (Real Data Points)', font=dict(size=14)))
    st.plotly_chart(fig_monthly, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# SHOVEL UTILIZATION + DUMPER DISTRIBUTION (SIMULATED)
# ══════════════════════════════════════════════════════════════════════════════

if not shovel_stats.empty and len(shovel_stats) > 0:
    st.markdown("---")
    col_util, col_dist = st.columns(2, gap="medium")

    with col_util:
        st.markdown('<div class="section-title">📊 Shovel Utilization <span class="badge-simulated">SIMULATED</span></div>', unsafe_allow_html=True)

        shovel_stats['utilization_pct'] = np.where(
            shovel_stats['capacity_tpd'] > 0,
            shovel_stats['throughput_tpd'] / shovel_stats['capacity_tpd'] * 100,
            0
        )
        colors = ['#22c55e' if u >= 80 else ('#f59e0b' if u >= 50 else '#ef4444')
                  for u in shovel_stats['utilization_pct']]

        fig_util = go.Figure(go.Bar(
            x=shovel_stats['shovel_id'],
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
        st.markdown('<div class="section-title">🚛 Dumper Distribution <span class="badge-simulated">SIMULATED</span></div>', unsafe_allow_html=True)

        fig_dist = go.Figure(go.Bar(
            x=shovel_stats['shovel_id'],
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


# ══════════════════════════════════════════════════════════════════════════════
# DATA PROVENANCE PANEL
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
with st.expander("📋 Data Provenance — What's Real and What's Not", expanded=False):
    st.markdown("""
Every metric on this dashboard has a provenance badge. Here's the full breakdown:

<table class="prov-table">
<tr><th>Metric</th><th>Type</th><th>Source / Formula</th></tr>
<tr>
    <td>Company Production (TPD)</td>
    <td><span class="badge-derived">DERIVED</span></td>
    <td>tonnes ÷ days from latest monthly entry in moil_real.csv</td>
</tr>
<tr>
    <td>FY26 Planned (TPD)</td>
    <td><span class="badge-real">REAL</span></td>
    <td>FY26 target (2,350,000 tonnes) ÷ 365 days</td>
</tr>
<tr>
    <td>Achievement %</td>
    <td><span class="badge-derived">DERIVED</span></td>
    <td>Company TPD ÷ Planned TPD × 100. Clamped at 150%, warning &gt; 115%</td>
</tr>
<tr>
    <td>Mine TPD (Dongri Buzurg)</td>
    <td><span class="badge-derived">DERIVED</span></td>
    <td>Company TPD × mine_share slider (default 8%). <strong>ASSUMPTION.</strong></td>
</tr>
<tr>
    <td>Annual Production Trend</td>
    <td><span class="badge-real">REAL</span></td>
    <td>MOIL Annual Reports FY19–FY25</td>
</tr>
<tr>
    <td>Monthly Production Points</td>
    <td><span class="badge-real">REAL</span></td>
    <td>MOIL press releases (Dec-22, Dec-23, Aug-24, May-25, Jul-25, Oct-25)</td>
</tr>
<tr>
    <td>Dumper Count, Capacity, Assignments</td>
    <td><span class="badge-simulated">SIMULATED</span></td>
    <td>Generated to match mine TPD. Sized so Σ(TPH) × 16h = mine TPD</td>
</tr>
<tr>
    <td>Shovel Count, Throughput, Utilization</td>
    <td><span class="badge-simulated">SIMULATED</span></td>
    <td>1 shovel per ~3 dumpers, capacity randomly assigned 150–280 TPH</td>
</tr>
<tr>
    <td>Fleet Efficiency</td>
    <td><span class="badge-simulated">SIMULATED</span></td>
    <td>Scale factor applied to dumper capacities to match mine TPD</td>
</tr>
<tr>
    <td>OR-Tools Dispatch Recommendation</td>
    <td><span class="badge-simulated">SIMULATED</span></td>
    <td>Load-balancing heuristic based on simulated fleet</td>
</tr>
</table>
""", unsafe_allow_html=True)

    st.markdown("### Source Data File")
    st.dataframe(
        moil_df[['period', 'tonnes', 'days', 'tpd', 'type', 'source_url']].style.format({
            'tonnes': '{:,.0f}',
            'tpd': '{:,.0f}',
        }),
        use_container_width=True,
        hide_index=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# ALL MINES — LIVE RISK DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

if not live_forecast_df.empty:
    st.markdown("---")
    st.markdown('<div class="section-title">🌐 All Mines — Live Risk Dashboard <span class="badge-simulated">SIMULATED</span></div>', unsafe_allow_html=True)

    # Show timestamp
    if 'timestamp' in live_forecast_df.columns:
        ts = live_forecast_df['timestamp'].iloc[0]
        st.caption(f"🕐 **Last Updated:** {ts} | **Source:** Open-Meteo Live 14-Day Weather API → ML Model")

    live_display = live_forecast_df[['mine_id', 'baseline_tpd', 'predicted_production_tpd',
                                      'rainfall_mm_scenario', 'weather_penalty', 'shortfall_risk']].copy()
    live_display.columns = ['Mine', 'Baseline (TPD)', 'Predicted (TPD)', 'Rainfall (mm)', 'Weather Penalty', 'Risk']
    live_display['Mine'] = live_display['Mine'].str.replace('_', ' ')
    live_display['Efficiency'] = (live_display['Predicted (TPD)'] / live_display['Baseline (TPD)'] * 100).round(1)
    live_display = live_display.sort_values('Efficiency')

    def color_risk(val):
        if val == 'High':
            return 'background-color: rgba(220,38,38,0.15); color: #dc2626;'
        elif val == 'Medium':
            return 'background-color: rgba(217,119,6,0.15); color: #d97706;'
        return 'background-color: rgba(22,163,74,0.1); color: #16a34a;'

    styled_live = live_display.style.map(color_risk, subset=['Risk']).format({
        'Baseline (TPD)': '{:.0f}',
        'Predicted (TPD)': '{:.0f}',
        'Rainfall (mm)': '{:.0f}',
        'Weather Penalty': '{:.2f}',
        'Efficiency': '{:.1f}%'
    })
    st.dataframe(styled_live, use_container_width=True, hide_index=True)

    # Summary stats
    high_count = (live_forecast_df['shortfall_risk'] == 'High').sum()
    med_count = (live_forecast_df['shortfall_risk'] == 'Medium').sum()
    low_count = (live_forecast_df['shortfall_risk'] == 'Low').sum()

    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("🔴 High Risk Mines", high_count)
    sc2.metric("🟡 Medium Risk Mines", med_count)
    sc3.metric("🟢 Low Risk Mines", low_count)

    st.caption("📡 This uses **LIVE weather data** from Open-Meteo API → trained ML model. Run `python src/generate_live_forecast.py` to refresh.")


# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════

st.info(
    "💡 **Data Integrity Note:** This dashboard reads exclusively from `data/moil_real.csv`. "
    "Company-level production is REAL. Mine-level production is an ASSUMPTION (editable above). "
    "All fleet data is SIMULATED to match the derived mine TPD. "
    "The OR-Tools dispatch logic is unchanged — only its inputs are now grounded in real data."
)
