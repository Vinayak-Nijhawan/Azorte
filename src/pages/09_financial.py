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

.header-banner {
    background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
    padding: 30px;
    border-radius: 15px;
    margin-bottom: 25px;
    box-shadow: 0 10px 20px rgba(0,0,0,0.3);
    border: 1px solid rgba(255,255,255,0.1);
}
.header-title {
    font-size: 42px !important;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 10px;
}
.header-subtitle {
    font-size: 22px !important;
    font-weight: 400;
    color: #40c9ff;
    margin-bottom: 15px;
}
.header-caption {
    font-size: 16px !important;
    color: #a0a0a0;
    font-style: italic;
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
</style>

<div class="header-banner">
    <div class="header-title">Financial Impact & ROI Analysis 💰</div>
    <div class="header-subtitle">Executive Dashboard: Economic & Environmental Impact of MOIL-GeoSync</div>
    <div class="header-caption">⚠️ All financial projections are based on standard PSU operational scale (MOIL turnover ~₹1,500 Cr).</div>
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
    cards_html = ""
    for i, kpi in enumerate(kpi_list):
        highlight_cls = "highlight" if kpi.get("highlight") else ""
        delay = i * 0.15
        
        val = kpi["value"]
        prefix = kpi.get("prefix", "")
        suffix = kpi.get("suffix", "")
        decimals = kpi.get("decimals", 2)
        
        if kpi.get("is_money", False):
            prefix = "₹"
            if val >= 1e7:
                target_val = val / 1e7
                suffix = "Cr"
            elif val >= 1e5:
                target_val = val / 1e5
                suffix = "Lakh"
            else:
                target_val = val
                decimals = 0
        else:
            target_val = val
            
        badge_html = ""
        if kpi.get("badge"):
            b_color = kpi.get("badge_color", "badge-green")
            badge_html = f'<div class="kpi-badge {b_color}">{kpi["badge"]}</div>'
            
        cards_html += f"""
        <div class="kpi-card {highlight_cls}" style="animation-delay: {delay}s;">
            <div class="kpi-title">{kpi['title']}</div>
            <div class="kpi-value">{prefix}<span class="count-up" data-target="{target_val}" data-decimals="{decimals}">0</span> {suffix}</div>
            {badge_html}
        </div>
        """
        
    html_code = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; font-family: 'Inter', sans-serif; background-color: transparent; overflow: hidden; }}
        .kpi-container {{ display: flex; gap: 1rem; justify-content: space-between; width: 100%; padding-bottom: 10px; }}
        .kpi-card {{ 
            background: #111520; border: 1px solid #1e293b; border-radius: 12px; 
            padding: 1.2rem; flex: 1; box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            transform: translateY(20px); opacity: 0; animation: fadeUp 0.6s ease-out forwards;
            min-width: 0; /* allows flex items to shrink below content size if needed */
        }}
        .kpi-card.highlight {{ border-color: #2563eb; background: linear-gradient(180deg, #111520 0%, #0f172a 100%); }}
        .kpi-title {{ color: #94a3b8; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-bottom: 0.5rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .kpi-value {{ color: #f8fafc; font-size: 1.9rem; font-weight: 700; margin: 0; display: flex; align-items: baseline; gap: 0.2rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .kpi-badge {{ display: inline-block; padding: 0.25rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; margin-top: 0.75rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }}
        .badge-red {{ background: rgba(220, 38, 38, 0.15); color: #ef4444; }}
        .badge-green {{ background: rgba(22, 163, 74, 0.15); color: #4ade80; }}
        
        @keyframes fadeUp {{
            to {{ transform: translateY(0); opacity: 1; }}
        }}
    </style>

    <div class="kpi-container">
        {cards_html}
    </div>

    <script>
        const counters = document.querySelectorAll('.count-up');
        const duration = 1500;

        counters.forEach(counter => {{
            const target = parseFloat(counter.getAttribute('data-target'));
            const dec = parseInt(counter.getAttribute('data-decimals'));
            const startTime = performance.now();

            const updateCounter = (currentTime) => {{
                const elapsedTime = currentTime - startTime;
                const progress = Math.min(elapsedTime / duration, 1);
                const easeOut = progress * (2 - progress);
                const currentVal = target * easeOut;
                
                counter.innerText = (currentVal).toLocaleString('en-IN', {{ minimumFractionDigits: dec, maximumFractionDigits: dec }});

                if (progress < 1) {{
                    requestAnimationFrame(updateCounter);
                }} else {{
                    counter.innerText = (target).toLocaleString('en-IN', {{ minimumFractionDigits: dec, maximumFractionDigits: dec }});
                }}
            }};
            requestAnimationFrame(updateCounter);
        }});
    </script>
    """
    components.html(html_code, height=180)


main_col, controls_col = st.columns([3, 1], gap="medium")

with controls_col:
    with st.container(border=True):
        st.subheader("Adjust Assumptions")
        ore_price = st.slider("Manganese Ore Price (₹/ton)", 8000, 20000, 12000, 500)
        drill_cost = st.slider("Exploration Drill Cost (₹/Site)", 1000000, 3000000, 1500000, 100000)
        ai_recovery_pct = st.slider("AI Shortfall Recovery Rate (%)", 10, 40, 20, 5)
        diesel_cost = st.slider("Diesel Cost per Litre (₹)", 80, 110, 95, 1)
        idle_cost = st.slider("Idle Cost per Dumper/Hour (₹)", 3000, 8000, 5000, 500)


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
            template="plotly_dark",
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
        
        tons_at_risk = 72000
        revenue_at_risk = tons_at_risk * ore_price
        
        recovery_pct_dec = ai_recovery_pct / 100.0
        tons_recovered = tons_at_risk * recovery_pct_dec
        revenue_protected = revenue_at_risk * recovery_pct_dec
        
        st.markdown(f"**Ground Truth Baseline:** 6 mines across 4 monsoon months experience an average shortfall of ~{tons_at_risk:,} tons total.")
        
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
            template="plotly_dark",
            margin=dict(l=0, r=0, t=40, b=0),
            height=350
        )
        st.plotly_chart(fig2, use_container_width=True)

    # --- Section 3: Fleet Optimization Savings ---
    with st.container(border=True):
        st.markdown('<div class="badge-blue">Dynamic Dispatch</div>', unsafe_allow_html=True)
        st.subheader("3. Fleet Optimization & Diesel Savings")
        
        fleet_dumpers = 48
        idle_hours_saved_per_month_per_truck = 2.5
        dumper_hours_per_month = fleet_dumpers * idle_hours_saved_per_month_per_truck # 60
        annual_idle_hours_saved = dumper_hours_per_month * 12 # 720
        
        # User defined formula
        monthly_fleet_savings = dumper_hours_per_month * ((35 * diesel_cost) + (idle_cost * 0.6))
        annual_fleet_savings = monthly_fleet_savings * 12
        
        st.markdown(f"**Optimization Details:** {fleet_dumpers} active dumpers operating across 6 mines. Dynamic routing saves **{idle_hours_saved_per_month_per_truck} idle engine hours** per truck per month. Fuel consumption: 35 L/hr @ ₹{diesel_cost}/L diesel.")
        
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
