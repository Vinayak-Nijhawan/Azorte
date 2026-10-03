"""
MOIL-GeoSync — Underground Fleet Dispatch (SimPy DES)
======================================================
Physically realistic discrete-event simulation for UNDERGROUND mines only.
"""

import os
import sys
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
UG_CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "underground_config.yaml")

sys.path.insert(0, PROJECT_ROOT)
from src.underground_sim import load_config, get_underground_mines, UndergroundSimulation

# Load global CSS
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils import load_css
load_css()

# ═══════════════════════════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""<style>
    /* Badges */
    .badge-real { display: inline-block; background: rgba(34,197,94,0.12); border: 1px solid rgba(34,197,94,0.25);
        color: #16a34a !important; font-size: 0.55rem !important; font-weight: 700;
        text-transform: uppercase; padding: 1px 6px; border-radius: 3px; vertical-align: super; }
    .badge-derived { display: inline-block; background: rgba(59,130,246,0.12); border: 1px solid rgba(59,130,246,0.25);
        color: #2563eb !important; font-size: 0.55rem !important; font-weight: 700;
        text-transform: uppercase; padding: 1px 6px; border-radius: 3px; vertical-align: super; }
    .badge-simulated { display: inline-block; background: rgba(245,158,11,0.15); border: 1px solid rgba(245,158,11,0.3);
        color: #d97706 !important; font-size: 0.55rem !important; font-weight: 700;
        text-transform: uppercase; padding: 1px 6px; border-radius: 3px; vertical-align: super; }

    /* KPI */
    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(155px, 1fr));
        gap: 10px; margin-bottom: 20px; }
    .kpi-card { background: rgba(241,245,249,0.6); border: 1px solid rgba(100,116,139,0.2);
        border-radius: 10px; padding: 16px 18px; }
    .kpi-card-sim { background: rgba(255,251,235,0.6); border: 1px solid rgba(245,158,11,0.3);
        border-radius: 10px; padding: 16px 18px; }
    .kpi-label { font-size: 0.68rem !important; color: #475569 !important;
        text-transform: uppercase; letter-spacing: 0.8px; font-weight: 600 !important;
        margin-bottom: 6px !important; }
    .kpi-value { font-size: 1.7rem !important; font-weight: 700 !important;
        color: #1e293b !important; line-height: 1.1 !important; }
    .kpi-unit { font-size: 0.75rem !important; color: #475569 !important;
        font-weight: 400 !important; margin-left: 3px; }
    .kpi-delta { font-size: 0.75rem !important; margin-top: 4px !important; }
    .kpi-delta.positive { color: #16a34a !important; }
    .kpi-delta.negative { color: #dc2626 !important; }
    .kpi-delta.neutral  { color: #475569 !important; }

    .section-title { font-size: 0.72rem !important; text-transform: uppercase;
        letter-spacing: 1.2px; color: #475569 !important; font-weight: 700 !important;
        margin-bottom: 12px !important; padding-bottom: 8px;
        border-bottom: 1px solid rgba(0,0,0,0.08); }

    .data-warn { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2);
        border-radius: 8px; padding: 10px 16px; margin-bottom: 12px;
        font-size: 0.85rem; color: #dc2626; }
    .data-pass { background: rgba(34,197,94,0.08); border: 1px solid rgba(34,197,94,0.2);
        border-radius: 8px; padding: 10px 16px; margin-bottom: 8px;
        font-size: 0.85rem; color: #16a34a; }
</style>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data
def load_moil_real():
    if not os.path.exists(MOIL_REAL_PATH):
        return pd.DataFrame()
    df = pd.read_csv(MOIL_REAL_PATH)
    df['start_date'] = pd.to_datetime(df['start_date'])
    df['end_date'] = pd.to_datetime(df['end_date'])
    if 'days' in df.columns and 'tonnes' in df.columns:
        df['tpd'] = df['tonnes'] / df['days']
    return df

@st.cache_data
def load_ug_config():
    return load_config(UG_CONFIG_PATH)

moil_df = load_moil_real()
ug_cfg = load_ug_config()

if moil_df.empty:
    st.error("data/moil_real.csv not found.")
    st.stop()

# Extract company-level KPIs
fy26_target_row = moil_df[moil_df['period'] == 'FY26_target']
fy_target_tonnes = int(fy26_target_row['tonnes'].iloc[0]) if not fy26_target_row.empty else 2350000
planned_tpd = fy_target_tonnes / 365

monthly = moil_df[moil_df['type'] == 'monthly'].sort_values('end_date')
latest_month = monthly.iloc[-1] if not monthly.empty else None

if latest_month is not None:
    company_tpd = float(latest_month['tpd'])
    latest_label = latest_month['period']
else:
    company_tpd = 4940.0
    latest_label = "FY25"


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════

ug_mines = get_underground_mines(ug_cfg)
cfg = ug_cfg['underground_simulation']

st.sidebar.header("⚙️ Fleet Configuration")
st.sidebar.caption("Only **underground** mines have shaft haulage dispatch. "
                    "Opencast mines use truck/shovel dispatch.")

selected_mine = st.sidebar.selectbox("Select Underground Mine", ug_mines,
    index=ug_mines.index('Balaghat') if 'Balaghat' in ug_mines else 0)
mine_display = selected_mine.replace('_', ' ')
mine_cfg = cfg['mines'][selected_mine]

st.sidebar.markdown("---")
st.sidebar.subheader("Editable Assumptions")

mine_share = st.sidebar.slider(
    f"Mine Share — {mine_display}", 1, 50,
    value=mine_cfg['mine_share_pct'],
    key=f"ug_share_{selected_mine}",
    help="ASSUMPTION - not MOIL data")

target_util = st.sidebar.slider(
    "Target Utilisation", 0.60, 0.95,
    value=float(cfg['availability']['target_utilization']), step=0.05,
    help="Equipment mechanical availability target")

num_runs = st.sidebar.slider("Comparison Runs", 5, 50, value=cfg['num_runs'], step=5,
    help="Number of seeded replications per strategy")

# Derived mine TPD
mine_tpd = company_tpd * (mine_share / 100)
# Cap by capacity if real data exists
if 'capacity_tpy' in mine_cfg:
    max_tpd = mine_cfg['capacity_tpy'] / 365.0
    if mine_tpd > max_tpd:
        mine_tpd = max_tpd


# ═══════════════════════════════════════════════════════════════════════════════
# SIMULATION
# ═══════════════════════════════════════════════════════════════════════════════

ug_cfg_run = ug_cfg.copy()
ug_cfg_run['underground_simulation'] = dict(cfg)
ug_cfg_run['underground_simulation']['availability'] = dict(cfg['availability'])
ug_cfg_run['underground_simulation']['availability']['target_utilization'] = target_util
ug_cfg_run['underground_simulation']['num_runs'] = num_runs

sim = UndergroundSimulation(ug_cfg_run, selected_mine, mine_tpd)

# Run single shift (CP-SAT Blended)
result = sim.simulate_shift(strategy='cp_sat', seed=cfg['random_seed'])

# Run comparison (cached)
@st.cache_data(show_spinner="Running 3-strategy comparison...")
def run_cached_comparison(_mine, _tpd, _util, _runs, _seed):
    s = UndergroundSimulation(ug_cfg_run, _mine, _tpd)
    return s.run_comparison(num_runs=_runs)

comparison = run_cached_comparison(selected_mine, mine_tpd, target_util, num_runs, cfg['random_seed'])


# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════

st.html(f"""
<div class="fd-header">
    <div class="fd-header-left">
        <h1>⛏️ Underground Fleet Dispatch</h1>
        <div class="fd-subtitle">MineFlow OR-Optimizer · SimPy DES · MOIL Manganese Operations</div>
    </div>
    <div class="fd-header-right">
        <span class="fd-tag">⛏️ {mine_display}</span>
        <span class="fd-live"><span class="fd-live-dot"></span> OPERATIONAL</span>
    </div>
</div>
""")


# ═══════════════════════════════════════════════════════════════════════════════
# COMPANY KPIs (REAL / DERIVED)
# ═══════════════════════════════════════════════════════════════════════════════

delta_tpd = company_tpd - planned_tpd
achieve_pct = min(150, company_tpd / planned_tpd * 100) if planned_tpd > 0 else 0
delta_cls = "positive" if delta_tpd >= 0 else "negative"
delta_icon = "▲" if delta_tpd >= 0 else "▼"

st.markdown(f"""
<div class="kpi-grid">
    <div class="kpi-card">
        <div class="kpi-label">Company Prod <span class="badge-derived">DERIVED</span></div>
        <div class="kpi-value">{company_tpd:,.0f}<span class="kpi-unit">TPD</span></div>
        <div class="kpi-delta neutral">{latest_label}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">FY26 Plan <span class="badge-real">REAL</span></div>
        <div class="kpi-value">{planned_tpd:,.0f}<span class="kpi-unit">TPD</span></div>
        <div class="kpi-delta neutral">{fy_target_tonnes:,} t / 365 d</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Achievement <span class="badge-derived">DERIVED</span></div>
        <div class="kpi-value">{achieve_pct:.1f}<span class="kpi-unit">%</span></div>
        <div class="kpi-delta {delta_cls}">{delta_icon} {abs(delta_tpd):,.0f} TPD vs plan</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Mine TPD ({mine_display}) <span class="badge-derived">DERIVED</span></div>
        <div class="kpi-value">{mine_tpd:,.0f}<span class="kpi-unit">TPD</span></div>
        <div class="kpi-delta neutral">= min(capacity, {company_tpd:,.0f} x {mine_share}%)</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# FLEET SIZING (DERIVED from formulas)
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="section-title">📐 Fleet Sizing — Derived from Physics <span class="badge-simulated">SIMULATED</span></div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**LHD (Tramming)**")
    st.markdown(f"""
    | Parameter | Value |
    |---|---|
    | Payload | **{sim.lhd_payload} t** |
    | Avg Tram | **{sum(sim.tram_dists)/sim.num_dp:.0f} m** |
    | Cycle time | **{sim.avg_lhd_cycle_min:.1f} min** |
    | TPH (Avg) | **{sim.avg_lhd_tph:.1f} t/h** |
    | LHDs needed | **{sim.num_lhds}** |
    """)

with col2:
    st.markdown("**Skip Hoist**")
    st.markdown(f"""
    | Parameter | Value |
    |---|---|
    | Payload | **{sim.hoist_payload} t** |
    | Depth | **{sim.hoist_depth} m** |
    | Cycle time | **{sim.hoist_cycle_s:.1f} s** |
    | Max TPH | **{sim.hoist_tph:.1f} t/h** |
    | Ore Pass Cap | **{sim.ore_pass_cap} t** |
    """)

with col3:
    st.markdown("**System Summary**")
    fleet_max_tpd = sim.avg_lhd_tph * sim.num_lhds * sim.shift_hours * sim.shifts_per_day * target_util
    hoist_max_tpd = sim.hoist_tph * sim.shift_hours * sim.shifts_per_day * target_util
    bottleneck = "Hoist" if hoist_max_tpd < mine_tpd else "LHDs"
    st.markdown(f"""
    | Parameter | Value |
    |---|---|
    | **Mine Target** | **{mine_tpd:,.0f} TPD** |
    | Max LHD Cap | {fleet_max_tpd:,.0f} TPD |
    | Max Hoist Cap | {hoist_max_tpd:,.0f} TPD |
    | **Bottleneck** | **{bottleneck}** |
    """)

st.caption(f"📐 **Formula:** LHDs = ceil(TPD / (LHD_TPH × {sim.shift_hours}h × {sim.shifts_per_day} shifts × {target_util:.0%} util)).")


# ═══════════════════════════════════════════════════════════════════════════════
# SIMULATION RESULTS — CP-SAT (single run)
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown('<div class="section-title">🔬 Simulation Results — CP-SAT Blended Dispatch <span class="badge-simulated">SIMULATED</span></div>', unsafe_allow_html=True)

st.markdown(f"""
<div class="kpi-grid">
    <div class="kpi-card-sim">
        <div class="kpi-label">Tonnes Hoisted <span class="badge-simulated">SIM</span></div>
        <div class="kpi-value">{result['tonnes_hoisted']:,.0f}<span class="kpi-unit">t/shift</span></div>
        <div class="kpi-delta neutral">{result['tonnes_hoisted'] * sim.shifts_per_day:,.0f} TPD</div>
    </div>
    <div class="kpi-card-sim">
        <div class="kpi-label">Avg Grade <span class="badge-simulated">SIM</span></div>
        <div class="kpi-value">{result['avg_grade']:.1f}<span class="kpi-unit">% Mn</span></div>
        <div class="kpi-delta neutral">Blended at ore pass</div>
    </div>
    <div class="kpi-card-sim">
        <div class="kpi-label">LHD Utilisation <span class="badge-simulated">SIM</span></div>
        <div class="kpi-value">{result['lhd_utilisation']:.1f}<span class="kpi-unit">%</span></div>
        <div class="kpi-delta neutral">Target: {target_util:.0%}</div>
    </div>
    <div class="kpi-card-sim">
        <div class="kpi-label">Hoist Utilisation <span class="badge-simulated">SIM</span></div>
        <div class="kpi-value">{result['hoist_utilisation']:.1f}<span class="kpi-unit">%</span></div>
        <div class="kpi-delta neutral">Continuous operation</div>
    </div>
    <div class="kpi-card-sim">
        <div class="kpi-label">Ore Pass Starved <span class="badge-simulated">SIM</span></div>
        <div class="kpi-value">{result['starve_events']}</div>
        <div class="kpi-delta neutral">Hoist waited for ore</div>
    </div>
    <div class="kpi-card-sim">
        <div class="kpi-label">Ore Pass Overflow <span class="badge-simulated">SIM</span></div>
        <div class="kpi-value">{result['overflow_events']}</div>
        <div class="kpi-delta neutral">LHD waited to dump</div>
    </div>
</div>
""", unsafe_allow_html=True)

# LHD log table
st.markdown("**LHD-Level Results** (single shift)")
log_df = result['lhd_logs']
if not log_df.empty:
    st.dataframe(
        log_df.style.format({
            'tonnes': '{:.0f}', 'queue_time_min': '{:.1f}',
            'idle_time_min': '{:.1f}', 'utilisation_pct': '{:.1f}%',
        }).background_gradient(subset=['utilisation_pct'], cmap='RdYlGn', vmin=60, vmax=100),
        use_container_width=True, hide_index=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# STRATEGY COMPARISON (30 seeded runs)
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown(f'<div class="section-title">📊 Strategy Comparison — {num_runs} Seeded Runs <span class="badge-simulated">SIMULATED</span></div>', unsafe_allow_html=True)

# Build comparison table
comp_rows = []
for label, data in comparison.items():
    comp_rows.append({
        'Strategy': label,
        'Hoisted (t/shift)': f"{data['hoisted_mean']:,.0f} ± {data['hoisted_std']:.0f}",
        'Grade (% Mn)': f"{data['grade_mean']:.1f} ± {data['grade_std']:.1f}",
        'LHD Util (%)': f"{data['util_mean']:.1f} ± {data['util_std']:.1f}",
        'Starve Events': f"{data['starve_mean']:.1f}",
        'Overflow Events': f"{data['overflow_mean']:.1f}",
    })
comp_df = pd.DataFrame(comp_rows)
st.dataframe(comp_df, use_container_width=True, hide_index=True)

# Comparison chart
strategies = list(comparison.keys())
hoisted_means = [comparison[s]['hoisted_mean'] for s in strategies]
grade_means = [comparison[s]['grade_mean'] for s in strategies]

fig = go.Figure()
fig.add_trace(go.Bar(name='Hoisted (t/shift)', x=strategies, y=hoisted_means,
    marker_color=['#94a3b8', '#3b82f6', '#22c55e'],
    text=[f'{v:,.0f}' for v in hoisted_means], textposition='outside'))
fig.update_layout(
    title='Tonnes Hoisted per Shift by Strategy',
    yaxis_title='Tonnes/shift',
    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
    font=dict(color='#1e293b'), height=350, margin=dict(t=50, b=40),
)
st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown('<div class="section-title">✅ Validation Checks</div>', unsafe_allow_html=True)

checks = sim.validate(result)
for status, msg in checks:
    if status == 'PASS':
        st.markdown(f'<div class="data-pass">✅ PASS: {msg}</div>', unsafe_allow_html=True)
    elif status == 'FAIL':
        st.markdown(f'<div class="data-warn">❌ FAIL: {msg}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="data-warn">⚠️ WARN: {msg}</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# ASSUMPTIONS PANEL
# ═══════════════════════════════════════════════════════════════════════════════

with st.expander("📋 Data Provenance & Assumptions"):
    st.markdown("""
    ### 1. Corporate & Mine KPIs
    | Metric | Type | Value | Source / Formula |
    |---|---|---|---|
    | FY26 Plan | **REAL** | {plan:,.0f} TPD | [MOIL FY26 Target]({fy_url}) |
    | Latest Monthly | **REAL** | {comp:,.0f} TPD | [MOIL PR {lbl}]({mo_url}) |
    | Mine TPD Target | **DERIVED** | {mine:,.0f} TPD | `min(capacity, Latest Monthly × Mine Share %)` |
    
    ### 2. Fleet Specifications & Assumptions
    **Every value below is a SIMULATED ASSUMPTION.** No value comes from MOIL internal data.
    Sources: UNVERIFIED ASSUMPTION unless specified.

    | Parameter | Value | Source / Rationale |
    |---|---|---|
    | Shift duration | {sh}h × {spd} shifts/day | UNVERIFIED ASSUMPTION |
    | Target utilisation | {tu:.0%} | UNVERIFIED ASSUMPTION |
    | MTBF / MTTR | {mtbf}h / {mttr}h | UNVERIFIED ASSUMPTION |
    | LHD payload | {lp}t | UNVERIFIED ASSUMPTION |
    | LHD speeds | {ls} loaded / {es} empty km/h | UNVERIFIED ASSUMPTION |
    | LHD load/dump time | {llt}m / {ldt}m | UNVERIFIED ASSUMPTION |
    | Skip hoist payload | {sp}t | UNVERIFIED ASSUMPTION |
    | Hoist depth | {hd}m | UNVERIFIED ASSUMPTION |
    | Winding speed | {ws} m/s | UNVERIFIED ASSUMPTION |
    | Ore pass capacity | {opc}t | UNVERIFIED ASSUMPTION |
    | Blast window | {bw} min/shift | UNVERIFIED ASSUMPTION |
    """.format(
        sh=cfg['shift']['hours'], spd=cfg['shift']['shifts_per_day'],
        tu=target_util, mtbf=cfg['availability']['mtbf_hours'], mttr=cfg['availability']['mttr_hours'],
        lp=cfg['lhd_class']['payload_t'],
        ls=cfg['lhd_class']['loaded_speed_kmh'], es=cfg['lhd_class']['empty_speed_kmh'],
        llt=cfg['lhd_class']['load_time_min'], ldt=cfg['lhd_class']['dump_time_min'],
        sp=cfg['hoist']['skip_payload_t'], hd=cfg['hoist']['depth_m'], ws=cfg['hoist']['winding_speed_ms'],
        opc=cfg['ore_pass']['capacity_t'], bw=cfg['shift']['blast_window_min'],
        plan=planned_tpd, comp=company_tpd, mine=mine_tpd,
        fy_url=fy26_target_row['source_url'].iloc[0] if not fy26_target_row.empty else "#",
        mo_url=latest_month['source_url'] if latest_month is not None else "#",
        lbl=latest_label
    ))
