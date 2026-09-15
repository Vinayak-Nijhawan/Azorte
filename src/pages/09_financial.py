import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os

st.markdown("""
<style>
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
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Traditional Capex (100 Sites)", format_inr(trad_cost))
        c2.metric("GeoProspect Capex (15 Sites)", format_inr(ai_cost), "-85% Capex Reduction", delta_color="inverse")
        c3.metric("Net Capex Saved", format_inr(capex_saved), f"{sites_avoided} Dry Holes Avoided")
        
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
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Revenue at Risk (Annual)", format_inr(revenue_at_risk), f"-{tons_at_risk:,.0f} Tons", delta_color="inverse")
        c2.metric("AI Recovery Rate", f"{ai_recovery_pct}%", "MILP Dispatch Opt.")
        c3.metric("Revenue Protected (Annual)", format_inr(revenue_protected), f"+{tons_recovered:,.0f} Tons Recovered")
        
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
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Monthly Fleet Savings", format_inr(monthly_fleet_savings))
        c2.metric("Annual Fleet OpEx Savings", format_inr(annual_fleet_savings), f"{annual_idle_hours_saved:,.0f} Hours Saved")

    # --- Section 4: ESG & Sustainability ---
    with st.container(border=True):
        st.markdown('<div class="badge-green">ESG & Sustainability</div>', unsafe_allow_html=True)
        st.markdown("<h3 style='color: #38ef7d; margin-top: -10px;'>4. Environmental Impact 🌍</h3>", unsafe_allow_html=True)
        
        # Dynamically calculated based on fleet size
        co2_avoided_tons = (annual_idle_hours_saved * 35 * 2.68) / 1000
        forest_preserved_exploration = 21.25 # fixed ha
        trees_preserved = 8500 # fixed trees
        
        c1, c2, c3 = st.columns(3)
        c1.metric("CO₂ Emissions Avoided", f"{co2_avoided_tons:,.1f} Tons", "Annual Diesel Reduction")
        c2.metric("Forest Land Preserved", f"{forest_preserved_exploration:,.2f} Hectares", "Avoided Road Cutting")
        c3.metric("Equivalent Trees Saved", f"{trees_preserved:,.0f} Trees", "Exploratory Pads Avoided")

    # --- Section 5: Executive ROI Summary ---
    with st.container(border=True):
        st.markdown('<div class="badge-blue">Bottom Line</div>', unsafe_allow_html=True)
        st.subheader("5. Executive Summary & Payback Period")
        
        total_annual_value = capex_saved + revenue_protected + annual_fleet_savings
        implementation_capex = 5000000 # ₹50.00 Lakh
        
        payback_months = max(0.1, round((implementation_capex / total_annual_value) * 12, 1))
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Annual Value Created", format_inr(total_annual_value), "Capex + Rev + OpEx")
        c2.metric("Implementation Capex", format_inr(implementation_capex), "Software & Cloud")
        c3.metric("Payback Period", f"{payback_months:.1f} Months", f"~ {payback_months*30:.0f} Days")
        
        st.success(f"**Lightning Fast ROI:** With an estimated implementation Capex of **{format_inr(implementation_capex)}**, the MOIL-GeoSync ecosystem pays for itself in just **{payback_months:.1f} months**.")
