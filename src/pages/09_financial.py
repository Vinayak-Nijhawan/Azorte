import streamlit as st
import streamlit.components.v1 as components
import sys
import os
# Add the project root to sys.path so we can import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils import load_css
load_css()

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
# --- DATA LOADING ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
MOIL_MINES_PREFIXED = [
    "Mine_A_Dongri_Buzurg", "Mine_B_Chikla", "Mine_C_Munsar",
    "Mine_D_Balaghat", "Mine_E_Kandri", "Mine_F_Gumgaon",
]
MOIL_MINES_SHORT = [
    "Dongri_Buzurg", "Chikla", "Munsar",
    "Balaghat", "Kandri", "Gumgaon",
    "Beldongri", "Sitapatore", "Tirodi", "Ukwa",
]
# Match whichever naming convention the data uses
MOIL_MINES = MOIL_MINES_PREFIXED + MOIL_MINES_SHORT

@st.cache_data
def load_project_data():
    files = {
        "forecast": "production_forecast_real.csv",
        "dispatch": "dispatch_plan_real.csv",
        "alerts": "fleet_alerts_real.csv",
    }
    dfs = {}
    for key, fname in files.items():
        path = os.path.join(DATA_DIR, fname)
        if os.path.exists(path):
            dfs[key] = pd.read_csv(path, comment="#")
    return dfs

dfs = load_project_data()

tons_at_risk_dynamic = 72000
fleet_dumpers_dynamic = 48
annual_actionable_alerts = 150

if "forecast" in dfs:
    fc = dfs["forecast"]
    target_col = 'baseline_tpd' if 'baseline_tpd' in fc.columns else 'planned_production_tpd'
    pred_col = 'predicted_production_tpd'
    if target_col in fc.columns and pred_col in fc.columns:
        fc["shortfall_tpd"] = (fc[target_col] - fc[pred_col]).clip(lower=0)
        fc["shortfall_tons_month"] = fc["shortfall_tpd"] * 30
        fc_moil = fc[fc["mine_id"].isin(MOIL_MINES)] if 'mine_id' in fc.columns else fc
        tons_at_risk_dynamic = float(fc_moil["shortfall_tons_month"].sum())

if "dispatch" in dfs:
    dp = dfs["dispatch"]
    dp_moil = dp[dp["mine_id"].isin(MOIL_MINES)] if 'mine_id' in dp.columns else dp
    if 'mine_id' in dp_moil.columns and 'dumper_id' in dp_moil.columns:
        fleet_dumpers_dynamic = int(dp_moil.groupby("mine_id")["dumper_id"].nunique().sum())

if "alerts" in dfs:
    al = dfs["alerts"]
    al_moil = al[al["mine_id"].isin(MOIL_MINES)] if 'mine_id' in al.columns else al
    if 'alert_type' in al_moil.columns:
        counts = al_moil["alert_type"].value_counts()
        annual_actionable_alerts = int(counts.get("WARNING", 0)) + int(counts.get("CRITICAL", 0))
# --------------------

st.markdown("""
<style>
/* Plotly Volcano Eruption Animation */
@keyframes volcanoErupt {
    0% { transform: scaleY(0); opacity: 0; }
    70% { transform: scaleY(1.05); }
    100% { transform: scaleY(1); opacity: 1; }
}

/* Target Plotly chart SVG bar paths */
[data-testid="stPlotlyChart"] svg .bars path,
[data-testid="stPlotlyChart"] svg .point path {
    transform-origin: bottom !important;
    animation: volcanoErupt 1.2s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards !important;
}


/* Increase font sizes across the rest of the page */
.stMarkdown p, .stMarkdown li {
    font-size: 18px !important;
    line-height: 1.6;
}

.badge-blue {
    background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
    color: white;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 14px;
    font-weight: bold;
    display: inline-block;
    margin-bottom: 10px;
}
.badge-green {
    background: linear-gradient(90deg, #11998e 0%, #38ef7d 100%);
    color: white;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 14px;
    font-weight: bold;
    display: inline-block;
    margin-bottom: 10px;
}
.money-tag {
    color: #00C851;
    font-weight: bold;
}

/* Make the right control panel sticky */
div[data-testid="stColumn"]:nth-of-type(2) {
    position: sticky;
    top: 6rem;
    align-self: flex-start;
    z-index: 100;
}

  .geo-kpi-grid { display: flex; gap: 20px; margin-bottom: 24px; flex-wrap: wrap; }
  .geo-kpi-card { background: var(--secondary-background-color) !important; flex: 1; min-width: 200px; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08) !important; border: 1px solid rgba(128, 128, 128, 0.2) !important; border-radius: 16px; padding: 22px 24px; display: flex; flex-direction: column; gap: 10px; transition: all 0.2s ease; }
  .geo-kpi-card:hover { border-color: rgba(59,130,246,0.5); transform: translateY(-2px); }
  .geo-kpi-title { color: color-mix(in srgb, var(--text-color) 60%, transparent); font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; line-height: 1.2; }
  .geo-kpi-value { font-size: 1.8rem; font-weight: 700; color: var(--text-color); line-height: 1.2; display: flex; align-items: center; gap: 4px; }
  .geo-trend-up, .geo-trend-down, .geo-trend-neutral { display: inline-block; padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; margin-top: 5px; }
  .geo-trend-up { background: rgba(16,185,129,0.15); color: #10B981; }
  .geo-trend-down { background: rgba(239,68,68,0.15); color: #EF4444; }
  .geo-trend-neutral { background: rgba(59,130,246,0.15); color: #3B82F6; }
</style>

<div class="fd-header">
    <div class="fd-header-left">
        <h1><span class="material-symbols-rounded">attach_money</span> Financial Impact & ROI Analysis</h1>
        <div class="fd-subtitle">Executive Dashboard: Economic & Environmental Impact of MOIL-GeoSync</div>
    </div>
    <div class="fd-header-right">
        <div class="fd-tag"><span class="material-symbols-rounded" style="font-size: 16px; margin-right: 4px; vertical-align: middle;">warning</span> Baseline: MOIL Turnover ~₹1,500 Cr</div>
    </div>
</div>
""", unsafe_allow_html=True)


def format_inr(amount):
    if amount >= 1e7:
        return f'₹{amount/1e7:.2f} Cr'
    elif amount >= 1e5:
        return f'₹{amount/1e5:.2f} Lakh'
    else:
        return f'₹{amount:,.0f}'

def render_animated_kpi_row(kpi_list):
    cards_html = """<div class="geo-kpi-grid">"""
    
    for kpi in kpi_list:
        val = kpi["value"]
        prefix = kpi.get("prefix", "")
        suffix = kpi.get("suffix", "")
        decimals = kpi.get("decimals", 2)
        
        if kpi.get("is_money", False):
            prefix = "₹"
            if val >= 1e7:
                val = val / 1e7
                suffix = " Cr"
            elif val >= 1e5:
                val = val / 1e5
                suffix = " Lakh"
            else:
                decimals = 0
        
        formatted_val = f"{val:,.{decimals}f}" if decimals > 0 else f"{val:,.0f}"
        
        badge_html = ""
        if kpi.get("badge"):
            b_color = kpi.get("badge_color", "badge-green")
            trend_class = "geo-trend-up" if "green" in b_color else ("geo-trend-down" if "red" in b_color else "geo-trend-neutral")
            badge_html = f"""<div class="geo-kpi-footer"><span class="{trend_class}">{kpi['badge']}</span></div>"""
            
        cards_html += f"""
        <div class="geo-kpi-card">
            <div class="geo-kpi-title">{kpi['title']}</div>
            <div class="geo-kpi-value">{prefix}{formatted_val}{suffix}</div>
            {badge_html}
        </div>
        """
        
    cards_html += "</div>"
    cards_html = '\n'.join([line.strip() for line in cards_html.split('\n')])
    import streamlit as st
    st.markdown(cards_html, unsafe_allow_html=True)



main_col, controls_col = st.columns([3, 1], gap="medium")

with controls_col:
    with st.container(border=True):
        st.subheader("Adjust Assumptions")
        ore_price = st.slider("Manganese Ore Price (:material/currency_rupee:/ton)", 6000, 15000, 9164, 50)
        drill_cost = st.slider("Exploration Drill Cost (:material/currency_rupee:/Site)", 1000000, 3000000, 1500000, 100000)
        ai_recovery_pct = st.slider("AI Shortfall Recovery Rate (%)", 5, 25, 12, 1)
        diesel_cost = st.slider("Diesel Cost per Litre (:material/currency_rupee:)", 80.0, 110.0, 98.4, 0.1)
        idle_cost = st.slider("Idle Cost per Dumper/Hour (:material/currency_rupee:)", 3000, 8000, 5000, 500)


with main_col:
    # --- Section 1: Exploration Capex Savings ---
    with st.container(border=True):
        st.markdown('<div class="badge-blue">GeoProspect AI</div>', unsafe_allow_html=True)
        st.subheader("1. Exploration Capex Savings")
        
        trad_boreholes = 100
        ai_boreholes = 15
        
        trad_cost = trad_boreholes * drill_cost
        ai_cost = ai_boreholes * drill_cost
        sites_avoided = trad_boreholes - ai_boreholes
        capex_saved = sites_avoided * drill_cost
        
        render_animated_kpi_row([
            {
                "title": "Traditional Capex (100 Sites)",
                "value": trad_cost,
                "is_money": True
            },
            {
                "title": "Geoprospect Capex (15 Sites)",
                "value": ai_cost,
                "is_money": True,
                "badge": "↓ -85% Capex Reduction",
                "highlight": True
            },
            {
                "title": "Net Capex Saved",
                "value": capex_saved,
                "is_money": True,
                "badge": f"↑ {sites_avoided} Dry Holes Avoided"
            }
        ])
        
        fig1 = go.Figure(data=[
            go.Bar(name='Traditional Campaign', x=['Exploration Capex'], y=[trad_cost], marker_color='#E03C31', text=[format_inr(trad_cost)], textposition='auto'),
            go.Bar(name='AI-Optimized Campaign', x=['Exploration Capex'], y=[ai_cost], marker_color='#00C851', text=[format_inr(ai_cost)], textposition='auto')
        ])
        fig1.update_layout(
            template="plotly_white",
            barmode='group',
            yaxis_title="Capital Expenditure (₹)",
            margin=dict(l=0, r=0, t=30, b=0),
            height=350,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig1, use_container_width=True)

    # --- Section 2: Operational Revenue Protection ---
    with st.container(border=True):
        st.markdown('<div class="badge-blue">MineFlow Optimizer</div>', unsafe_allow_html=True)
        st.subheader("2. Operational Revenue Protection")
        
        tons_at_risk = tons_at_risk_dynamic
        revenue_at_risk = tons_at_risk * ore_price
        
        recovery_pct_dec = ai_recovery_pct / 100.0
        tons_recovered = tons_at_risk * recovery_pct_dec
        revenue_protected = revenue_at_risk * recovery_pct_dec
        
        st.markdown(f"**Ground Truth Baseline:** {len(MOIL_MINES)} mines across 4 monsoon months experience an average shortfall of ~{tons_at_risk:,.0f} tons total.")
        
        render_animated_kpi_row([
            {
                "title": "Revenue at Risk (Annual)",
                "value": revenue_at_risk,
                "is_money": True,
                "badge": f"-{tons_at_risk:,.0f} Tons",
                "badge_color": "badge-red"
            },
            {
                "title": "AI Recovery Rate",
                "value": ai_recovery_pct,
                "decimals": 0,
                "suffix": "%",
                "badge": "MILP Dispatch Opt.",
                "badge_color": "badge-green"
            },
            {
                "title": "Revenue Protected (Annual)",
                "value": revenue_protected,
                "is_money": True,
                "badge": f"+{tons_recovered:,.0f} Tons Recovered",
                "highlight": True
            }
        ])
        
        fig2 = go.Figure(data=[
            go.Pie(labels=['Revenue Protected (AI)', 'Unrecovered Shortfall'], 
                   values=[revenue_protected, revenue_at_risk - revenue_protected],
                   hole=0.6,
                   marker_colors=['#00C851', '#333333'],
                   textinfo='label+percent')
        ])
        fig2.update_layout(
            title="Monsoon Shortfall Recovery",
            template="plotly_white",
            margin=dict(l=0, r=0, t=40, b=0),
            height=350
        )
        st.plotly_chart(fig2, use_container_width=True)

    # --- Section 3: Fleet Optimization Savings ---
    with st.container(border=True):
        st.markdown('<div class="badge-blue">Dynamic Dispatch</div>', unsafe_allow_html=True)
        st.subheader("3. Fleet Optimization & Diesel Savings")
        
        fleet_dumpers = fleet_dumpers_dynamic
        annual_idle_hours_saved = annual_actionable_alerts * 2.5
        dumper_hours_per_month = annual_idle_hours_saved / 12
        idle_hours_saved_per_month_per_truck = dumper_hours_per_month / max(1, fleet_dumpers)
        
        # User defined formula
        monthly_fleet_savings = dumper_hours_per_month * ((35 * diesel_cost) + (idle_cost * 0.6))
        annual_fleet_savings = monthly_fleet_savings * 12
        
        st.markdown(f"**Optimization Details:** {fleet_dumpers} active dumpers operating across {len(MOIL_MINES)} mines. Dynamic routing saves **{idle_hours_saved_per_month_per_truck:.1f} idle engine hours** per truck per month based on {annual_actionable_alerts} historical critical alerts. Fuel consumption: 35 L/hr @ ₹{diesel_cost}/L diesel.")
        
        render_animated_kpi_row([
            {
                "title": "Monthly Fleet Savings",
                "value": monthly_fleet_savings,
                "is_money": True
            },
            {
                "title": "Annual Fleet OpEx Savings",
                "value": annual_fleet_savings,
                "is_money": True,
                "badge": f"{annual_idle_hours_saved:,.0f} Hours Saved",
                "highlight": True
            }
        ])

    # --- Section 4: ESG & Sustainability ---
    with st.container(border=True):
        st.markdown('<div class="badge-green">ESG & Sustainability</div>', unsafe_allow_html=True)
        st.markdown("<h3 style='color: #38ef7d; margin-top: -10px;'>4. Environmental Impact 🌍</h3>", unsafe_allow_html=True)
        
        # Dynamically calculated based on fleet size
        co2_avoided_tons = (annual_idle_hours_saved * 35 * 2.68) / 1000
        forest_preserved_exploration = 21.25 # fixed ha
        trees_preserved = 8500 # fixed trees
        
        render_animated_kpi_row([
            {
                "title": "CO₂ Emissions Avoided",
                "value": co2_avoided_tons,
                "decimals": 1,
                "suffix": "Tons",
                "badge": "Annual Diesel Reduction"
            },
            {
                "title": "Forest Land Preserved",
                "value": forest_preserved_exploration,
                "decimals": 2,
                "suffix": "Hectares",
                "badge": "Avoided Road Cutting"
            },
            {
                "title": "Equivalent Trees Saved",
                "value": trees_preserved,
                "decimals": 0,
                "suffix": "Trees",
                "badge": "Exploratory Pads Avoided",
                "highlight": True
            }
        ])

    # --- Section 5: Executive ROI Summary ---
    with st.container(border=True):
        st.markdown('<div class="badge-blue">Bottom Line</div>', unsafe_allow_html=True)
        st.subheader("5. Executive Summary & Payback Period")
        
        total_annual_value = capex_saved + revenue_protected + annual_fleet_savings
        implementation_capex = 5000000 # ₹50.00 Lakh
        
        payback_months = max(0.1, round((implementation_capex / total_annual_value) * 12, 1))
        
        render_animated_kpi_row([
            {
                "title": "Total Annual Value Created",
                "value": total_annual_value,
                "is_money": True,
                "badge": "Capex + Rev + OpEx",
                "highlight": True
            },
            {
                "title": "Implementation Capex",
                "value": implementation_capex,
                "is_money": True,
                "badge": "Software & Cloud"
            },
            {
                "title": "Payback Period",
                "value": payback_months,
                "decimals": 1,
                "suffix": "Months",
                "badge": f"~ {payback_months*30:.0f} Days"
            }
        ])
        
        st.success(f"**Lightning Fast ROI:** With an estimated implementation Capex of **{format_inr(implementation_capex)}**, the MOIL-GeoSync ecosystem pays for itself in just **{payback_months:.1f} months**.")
