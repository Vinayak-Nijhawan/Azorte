"""
MOIL-GeoSync — Intelligent Fleet Dispatch (SimPy DES)
======================================================
Physically realistic discrete-event simulation for OPENCAST mines only.
Underground mines (Balaghat, Gumgaon, etc.) use shaft haulage, not trucks.

Data provenance:
  REAL      = MOIL annual reports / press releases
  DERIVED   = formula from real data (e.g. TPD = tonnes / days)
  SIMULATED = SimPy DES output — see config/fleet_config.yaml for assumptions
"""

import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# Load global CSS + Material Symbols font
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils import load_css
load_css()

# ─── Paths ───
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
MOIL_REAL_PATH = os.path.join(DATA_DIR, "moil_real.csv")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "fleet_config.yaml")

sys.path.insert(0, PROJECT_ROOT)
from src.fleet_sim import load_config, get_opencast_mines, FleetSimulation, derive_cycle_time



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
    df['tpd'] = df['tonnes'] / df['days']
    return df

@st.cache_data
def load_fleet_config():
    return load_config(CONFIG_PATH)

moil_df = load_moil_real()
fleet_cfg = load_fleet_config()

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

opencast_mines = get_opencast_mines(fleet_cfg)
cfg = fleet_cfg['fleet_simulation']

st.sidebar.header("⚙️ Fleet Configuration")
st.sidebar.caption("Only **opencast** mines have truck-shovel dispatch. "
                    "Underground mines use shaft haulage.")

selected_mine = st.sidebar.selectbox("Select Opencast Mine", opencast_mines,
    index=opencast_mines.index('Dongri_Buzurg') if 'Dongri_Buzurg' in opencast_mines else 0)
mine_display = selected_mine.replace('_', ' ')
mine_cfg = cfg['mines'][selected_mine]

st.sidebar.markdown("---")
st.sidebar.subheader("Editable Assumptions")

mine_share = st.sidebar.slider(
    f"Mine Share — {mine_display}", 1, 30,
    value=mine_cfg['mine_share_pct'],
    key=f"share_{selected_mine}",
    help="Estimated % of MOIL total production (ASSUMPTION)")

stripping_ratio = st.sidebar.slider(
    "Stripping Ratio (waste:ore)", 1.0, 8.0,
    value=float(cfg['stripping_ratio']), step=0.5,
    help="Tonnes of waste removed per tonne of ore")

target_util = st.sidebar.slider(
    "Target Utilisation", 0.60, 0.95,
    value=float(cfg['availability']['target_utilization']), step=0.05,
    help="Equipment mechanical availability target")

current_month = datetime.now().month
monsoon_on = current_month in cfg['monsoon']['months']
monsoon_override = st.sidebar.checkbox(
    f"Monsoon Derate ({cfg['monsoon']['derate_factor']:.0%})",
    value=monsoon_on,
    help=f"Currently {'active' if monsoon_on else 'inactive'} (Jun-Sep)")

num_runs = st.sidebar.slider("Comparison Runs", 5, 50, value=cfg['num_runs'], step=5,
    help="Number of seeded replications per strategy")

# Derived mine TPD
mine_tpd = company_tpd * (mine_share / 100)


# ═══════════════════════════════════════════════════════════════════════════════
# SIMULATION
# ═══════════════════════════════════════════════════════════════════════════════

# Override config values with sidebar inputs
fleet_cfg_run = fleet_cfg.copy()
fleet_cfg_run['fleet_simulation'] = dict(cfg)
fleet_cfg_run['fleet_simulation']['stripping_ratio'] = stripping_ratio
fleet_cfg_run['fleet_simulation']['availability'] = dict(cfg['availability'])
fleet_cfg_run['fleet_simulation']['availability']['target_utilization'] = target_util
fleet_cfg_run['fleet_simulation']['num_runs'] = num_runs

sim = FleetSimulation(
    fleet_cfg_run, selected_mine, mine_tpd,
    month=current_month if monsoon_override else None
)

# Run single shift (OR-Tools)
result = sim.simulate_shift(strategy='or_tools', seed=cfg['random_seed'])

# Run comparison (cached)
@st.cache_data(show_spinner="Running 3-strategy comparison...")
def run_cached_comparison(_mine, _tpd, _sr, _util, _mon, _runs, _seed):
    s = FleetSimulation(fleet_cfg_run, _mine, _tpd,
                        month=current_month if _mon else None)
    return s.run_comparison(num_runs=_runs)

comparison = run_cached_comparison(
    selected_mine, mine_tpd, stripping_ratio, target_util,
    monsoon_override, num_runs, cfg['random_seed'])


# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════

monsoon_tag = '<div class="fd-tag"><span class="material-symbols-rounded">water_drop</span> Monsoon Derate Active</div>' if monsoon_override else ''
sim_badge = '<div class="fd-live"><div class="fd-live-dot"></div> OPERATIONAL</div>'
st.markdown(f"""
<div class="fd-header">
    <div class="fd-header-left">
        <h1><span class="material-symbols-rounded">local_shipping</span> Intelligent Fleet Dispatch</h1>
        <div class="fd-subtitle">MineFlow OR-Optimizer · SimPy DES · MOIL Manganese Operations</div>
    </div>
    <div class="fd-header-right">
        <div class="fd-tag"><span class="material-symbols-rounded">architecture</span> {mine_display}</div>
        <div class="fd-tag"><span class="material-symbols-rounded">calendar_month</span> {latest_label}</div>
        {monsoon_tag}
        {sim_badge}
    </div>
</div>
""", unsafe_allow_html=True)


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
        <div class="kpi-delta neutral">= {company_tpd:,.0f} x {mine_share}%</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# FLEET SIZING (DERIVED from formulas)
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="section-title">📐 Fleet Sizing — Derived from Physics <span class="badge-simulated">SIMULATED</span></div>', unsafe_allow_html=True)

dumper_cfg = cfg['dumper_classes'][mine_cfg['dumper_class']]
shovel_cfg_data = cfg['shovel_classes'][mine_cfg['shovel_class']]

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Ore Haulage**")
    st.markdown(f"""
    | Parameter | Value |
    |---|---|
    | Payload | **{dumper_cfg['payload_t']} t** ({mine_cfg['dumper_class']}) |
    | Haul distance | **{mine_cfg['haul_distance_km']['ore']} km** |
    | Cycle time | **{sim.ore_cycle_min:.1f} min** |
    | TPH | **{sim.ore_tph:.1f} t/h** |
    | Dumpers needed | **{sim.num_ore_dumpers}** |
    """)

with col2:
    st.markdown("**Waste Haulage**")
    waste_tpd = mine_tpd * stripping_ratio
    st.markdown(f"""
    | Parameter | Value |
    |---|---|
    | Payload | **{dumper_cfg['payload_t']} t** ({mine_cfg['dumper_class']}) |
    | Haul distance | **{mine_cfg['haul_distance_km']['waste']} km** |
    | Cycle time | **{sim.waste_cycle_min:.1f} min** |
    | TPH | **{sim.waste_tph:.1f} t/h** |
    | Dumpers needed | **{sim.num_waste_dumpers}** |
    """)

with col3:
    st.markdown("**Fleet Summary**")
    st.markdown(f"""
    | Parameter | Value |
    |---|---|
    | **Total dumpers** | **{sim.num_dumpers}** ({sim.num_ore_dumpers} ore + {sim.num_waste_dumpers} waste) |
    | **Shovels** | **{sim.num_shovels}** (match-factor) |
    | Shovel class | {mine_cfg['shovel_class']} ({shovel_cfg_data['capacity_tph']} TPH) |
    | Stripping ratio | {stripping_ratio:.1f}:1 |
    | Ore target | {mine_tpd:,.0f} TPD |
    | Waste target | {waste_tpd:,.0f} TPD |
    """)

st.caption(f"📐 **Formula:** dumpers = ceil(TPD / (TPH × {sim.shift_hours}h × {sim.shifts_per_day} shifts × {target_util:.0%} util)). "
           f"Shovels via match-factor: ceil(fleet_TPH / shovel_TPH).")


# ═══════════════════════════════════════════════════════════════════════════════
# SIMULATION RESULTS — OR-Tools (single run)
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown('<div class="section-title">🔬 Simulation Results — OR-Tools Dynamic Dispatch <span class="badge-simulated">SIMULATED</span></div>', unsafe_allow_html=True)

ore_tpd_achieved = result['ore_tonnes'] * sim.shifts_per_day
waste_tpd_achieved = result['waste_tonnes'] * sim.shifts_per_day

st.markdown(f"""
<div class="kpi-grid">
    <div class="kpi-card-sim">
        <div class="kpi-label">Ore Achieved <span class="badge-simulated">SIM</span></div>
        <div class="kpi-value">{result['ore_tonnes']:,.0f}<span class="kpi-unit">t/shift</span></div>
        <div class="kpi-delta neutral">{ore_tpd_achieved:,.0f} TPD ({sim.shifts_per_day} shifts)</div>
    </div>
    <div class="kpi-card-sim">
        <div class="kpi-label">Waste Moved <span class="badge-simulated">SIM</span></div>
        <div class="kpi-value">{result['waste_tonnes']:,.0f}<span class="kpi-unit">t/shift</span></div>
        <div class="kpi-delta neutral">{waste_tpd_achieved:,.0f} TPD</div>
    </div>
    <div class="kpi-card-sim">
        <div class="kpi-label">Avg Queue Time <span class="badge-simulated">SIM</span></div>
        <div class="kpi-value">{result['avg_queue_time']:.1f}<span class="kpi-unit">min</span></div>
        <div class="kpi-delta neutral">Per dumper per shift</div>
    </div>
    <div class="kpi-card-sim">
        <div class="kpi-label">Fleet Utilisation <span class="badge-simulated">SIM</span></div>
        <div class="kpi-value">{result['avg_utilisation']:.1f}<span class="kpi-unit">%</span></div>
        <div class="kpi-delta neutral">Target: {target_util:.0%}</div>
    </div>
    <div class="kpi-card-sim">
        <div class="kpi-label">Total Trips <span class="badge-simulated">SIM</span></div>
        <div class="kpi-value">{result['total_trips']}</div>
        <div class="kpi-delta neutral">All dumpers, one shift</div>
    </div>
    <div class="kpi-card-sim">
        <div class="kpi-label">Avg Idle Time <span class="badge-simulated">SIM</span></div>
        <div class="kpi-value">{result['avg_idle_time']:.1f}<span class="kpi-unit">min</span></div>
        <div class="kpi-delta neutral">Per dumper per shift</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Dumper log table
st.markdown("**Dumper-Level Results** (single shift)")
log_df = result['dumper_logs']
if not log_df.empty:
    display_cols = ['dumper_id', 'material', 'trips', 'tonnes_hauled',
                    'queue_time_min', 'idle_time_min', 'breakdown_time_min', 'utilisation_pct']
    st.dataframe(
        log_df[display_cols].style.format({
            'tonnes_hauled': '{:.0f}', 'queue_time_min': '{:.1f}',
            'idle_time_min': '{:.1f}', 'breakdown_time_min': '{:.1f}',
            'utilisation_pct': '{:.1f}%',
        }).background_gradient(subset=['utilisation_pct'], cmap='RdYlGn', vmin=60, vmax=100),
        use_container_width=True, hide_index=True,
    )

# Shovel utilisation
shovel_util = result['shovel_utilisation']
st.markdown(f"**Shovel Utilisation:** " + " | ".join(
    f"S{i+1}: **{u:.1f}%**" for i, u in enumerate(shovel_util)))


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
        'Ore (t/shift)': f"{data['ore_mean']:,.0f} ± {data['ore_std']:.0f}",
        'Waste (t/shift)': f"{data['waste_mean']:,.0f} ± {data['waste_std']:.0f}",
        'Queue Time (min)': f"{data['queue_mean']:.1f} ± {data['queue_std']:.1f}",
        'Utilisation (%)': f"{data['util_mean']:.1f} ± {data['util_std']:.1f}",
        'Shovel Imbalance (%)': f"{data['imbalance_mean']:.1f}",
    })
comp_df = pd.DataFrame(comp_rows)
st.dataframe(comp_df, use_container_width=True, hide_index=True)

# Improvement vs Fixed
fixed = comparison.get('Fixed Assignment', {})
if fixed:
    for label in ['Nearest-Shovel Greedy', 'OR-Tools Dynamic']:
        d = comparison.get(label, {})
        if d and fixed['ore_mean'] > 0:
            ore_imp = (d['ore_mean'] - fixed['ore_mean']) / fixed['ore_mean'] * 100
            queue_imp = (d['queue_mean'] - fixed['queue_mean']) / fixed['queue_mean'] * 100 if fixed['queue_mean'] > 0 else 0
            st.markdown(f"**{label} vs Fixed:** Ore {ore_imp:+.1f}%, Queue time {queue_imp:+.1f}%")

# Comparison chart
strategies = list(comparison.keys())
ore_means = [comparison[s]['ore_mean'] for s in strategies]
queue_means = [comparison[s]['queue_mean'] for s in strategies]

fig = go.Figure()
fig.add_trace(go.Bar(name='Ore (t/shift)', x=strategies, y=ore_means,
    marker_color=['#94a3b8', '#3b82f6', '#22c55e'],
    text=[f'{v:,.0f}' for v in ore_means], textposition='outside'))
fig.update_layout(
    title='Ore Tonnes per Shift by Strategy',
    yaxis_title='Tonnes/shift',
    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
    font=dict(color='#1e293b'), height=350, margin=dict(t=50, b=40),
)
st.plotly_chart(fig, use_container_width=True)

fig2 = go.Figure()
fig2.add_trace(go.Bar(name='Avg Queue Time', x=strategies, y=queue_means,
    marker_color=['#ef4444', '#f59e0b', '#22c55e'],
    text=[f'{v:.1f} min' for v in queue_means], textposition='outside'))
fig2.update_layout(
    title='Average Queue Time by Strategy',
    yaxis_title='Minutes',
    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
    font=dict(color='#1e293b'), height=350, margin=dict(t=50, b=40),
)
st.plotly_chart(fig2, use_container_width=True)


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
    | Mine TPD Target | **DERIVED** | {mine:,.0f} TPD | `Latest Monthly × Mine Share %` |
    
    ### 2. Fleet Specifications & Assumptions
    **Every value below is a SIMULATED ASSUMPTION.** No value comes from MOIL internal data.
    Sources: UNVERIFIED ASSUMPTION unless specified.

    | Parameter | Value | Source / Rationale |
    |---|---|---|
    | Shift duration | {sh}h × {spd} shifts/day | UNVERIFIED ASSUMPTION |
    | Target utilisation | {tu:.0%} | UNVERIFIED ASSUMPTION |
    | MTBF | {mtbf}h | UNVERIFIED ASSUMPTION |
    | MTTR | {mttr}h | UNVERIFIED ASSUMPTION |
    | Monsoon derate | {md:.0%} | UNVERIFIED ASSUMPTION |
    | Stripping ratio | {sr:.1f}:1 | UNVERIFIED ASSUMPTION |
    | Cycle variation | Lognormal σ={cv} | UNVERIFIED ASSUMPTION |
    | Crusher dump points | {cdp} | UNVERIFIED ASSUMPTION |
    | Heavy dumper payload | {hp}t | UNVERIFIED ASSUMPTION |
    | Heavy loaded speed | {hls} km/h | UNVERIFIED ASSUMPTION |
    | Heavy empty speed | {hes} km/h | UNVERIFIED ASSUMPTION |
    | Medium dumper payload | {mp}t | UNVERIFIED ASSUMPTION |
    | Medium loaded speed | {mls} km/h | UNVERIFIED ASSUMPTION |
    | Medium empty speed | {mes} km/h | UNVERIFIED ASSUMPTION |
    | Large shovel capacity | {lsc} TPH | UNVERIFIED ASSUMPTION |
    | Large shovel load time | {lslt} min | UNVERIFIED ASSUMPTION |
    | Medium shovel capacity | {msc} TPH | UNVERIFIED ASSUMPTION |
    | Medium shovel load time | {mslt} min | UNVERIFIED ASSUMPTION |
    | Dump time | {dt} min | UNVERIFIED ASSUMPTION |
    | Spot time | {st_} min | UNVERIFIED ASSUMPTION |
    """.format(
        sh=cfg['shift']['hours'], spd=cfg['shift']['shifts_per_day'],
        tu=target_util, mtbf=cfg['availability']['mtbf_hours'],
        mttr=cfg['availability']['mttr_hours'],
        md=cfg['monsoon']['derate_factor'], sr=stripping_ratio,
        cv=cfg['cycle_variation']['sigma'], cdp=cfg['crusher']['dump_points'],
        hp=cfg['dumper_classes']['heavy']['payload_t'],
        hls=cfg['dumper_classes']['heavy']['loaded_speed_kmh'],
        hes=cfg['dumper_classes']['heavy']['empty_speed_kmh'],
        mp=cfg['dumper_classes']['medium']['payload_t'],
        mls=cfg['dumper_classes']['medium']['loaded_speed_kmh'],
        mes=cfg['dumper_classes']['medium']['empty_speed_kmh'],
        lsc=cfg['shovel_classes']['large']['capacity_tph'],
        lslt=cfg['shovel_classes']['large']['load_time_min'],
        msc=cfg['shovel_classes']['medium']['capacity_tph'],
        mslt=cfg['shovel_classes']['medium']['load_time_min'],
        dt=cfg['timing']['dump_time_min'], st_=cfg['timing']['spot_time_min'],
        plan=planned_tpd, comp=company_tpd, mine=mine_tpd,
        fy_url=fy26_target_row['source_url'].iloc[0] if not fy26_target_row.empty else "#",
        mo_url=latest_month['source_url'] if latest_month is not None else "#",
        lbl=latest_label
    ))

    st.markdown("### Mine-Specific Assumptions")
    mine_data = []
    for m, mc in cfg['mines'].items():
        mine_data.append({
            'Mine': m.replace('_', ' '),
            'Type': mc['type'],
            'Dumper Class': mc['dumper_class'],
            'Shovel Class': mc['shovel_class'],
            'Ore Haul (km)': mc['haul_distance_km']['ore'],
            'Waste Haul (km)': mc['haul_distance_km']['waste'],
            'Share (%)': mc['mine_share_pct'],
        })
    st.dataframe(pd.DataFrame(mine_data), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════

st.info(
    "💡 **Data Integrity:** Company-level production is REAL (MOIL reports). "
    f"Mine TPD ({mine_display}) is DERIVED (company × {mine_share}% ASSUMPTION). "
    "All fleet data is SIMULATED via SimPy DES with config/fleet_config.yaml assumptions. "
    "Edit assumptions in the sidebar or YAML file."
)
