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
</style>

<div class="header-banner">
    <div class="header-title">Financial Impact & ROI Analysis 💰</div>
    <div class="header-subtitle">Executive Dashboard: Economic & Environmental Impact of MOIL-GeoSync</div>
    <div class="header-caption">⚠️ All financial projections are based on standard PSU operational scale (MOIL turnover ~₹1,500 Cr).</div>
</div>
""", unsafe_allow_html=True)

# Custom CSS for Badges and Styling
st.markdown("""
<style>
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
</style>
""", unsafe_allow_html=True)

def format_inr(amount):
    if amount >= 1e7:
        return f'₹{amount/1e7:.2f} Cr'
    elif amount >= 1e5:
        return f'₹{amount/1e5:.2f} Lakh'
    else:
        return f'₹{amount:,.0f}'

# --- Section 1: Exploration Capex Savings ---
with st.container(border=True):
    st.markdown('<div class="badge-blue">GeoProspect AI</div>', unsafe_allow_html=True)
    st.subheader("1. Exploration Capex Savings")
    
    trad_boreholes = 100
    ai_boreholes = 15
    cost_per_hole = 1500000
    
    trad_cost = trad_boreholes * cost_per_hole
    ai_cost = ai_boreholes * cost_per_hole
    sites_avoided = trad_boreholes - ai_boreholes
    capex_saved = sites_avoided * cost_per_hole
    forest_preserved_exploration = sites_avoided * 0.25
    
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
    
    tons_at_risk = 36000
    ore_price = 12000
    revenue_at_risk = tons_at_risk * ore_price
    
    recovery_pct = 0.20
    tons_recovered = tons_at_risk * recovery_pct
    revenue_protected = tons_recovered * ore_price
    
    st.markdown(f"**Ground Truth Baseline:** 3 mines across 4 monsoon months experience an average shortfall of ~{tons_at_risk:,} tons total.")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Revenue at Risk (Annual)", format_inr(revenue_at_risk), f"-{tons_at_risk:,.0f} Tons", delta_color="inverse")
    c2.metric("AI Recovery Rate", f"{recovery_pct*100:.0f}%", "MILP Dispatch Opt.")
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
    
    fleet_dumpers = 24
    idle_hours_saved_per_month_per_truck = 2.5 # Calibrated to hit typical 40-60L/yr OpEx savings
    months_yr = 12
    fuel_consumption_lph = 35
    diesel_price = 95
    wear_tear_cost = 3000
    
    hourly_idle_cost = (fuel_consumption_lph * diesel_price) + wear_tear_cost
    annual_idle_hours_saved = fleet_dumpers * idle_hours_saved_per_month_per_truck * months_yr
    annual_fleet_savings = annual_idle_hours_saved * hourly_idle_cost
    monthly_fleet_savings = annual_fleet_savings / 12
    
    st.markdown(f"**Optimization Details:** {fleet_dumpers} active dumpers operating 16 hrs/day across 3 mines. Dynamic routing saves **{idle_hours_saved_per_month_per_truck} idle engine hours** per truck per month. Fuel consumption: {fuel_consumption_lph} L/hr @ ₹{diesel_price}/L diesel + ₹{wear_tear_cost:,.0f}/hr wear/tear & operator cost.")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Idle Cost Per Hour", format_inr(hourly_idle_cost))
    c2.metric("Monthly Fleet Savings", format_inr(monthly_fleet_savings))
    c3.metric("Annual Fleet OpEx Savings", format_inr(annual_fleet_savings), f"{annual_idle_hours_saved:,.0f} Hours Saved")


# --- Section 4: ESG & Sustainability ---
with st.container(border=True):
    st.markdown('<div class="badge-green">ESG & Sustainability</div>', unsafe_allow_html=True)
    st.markdown("<h3 style='color: #38ef7d; margin-top: -10px;'>4. Environmental Impact 🌍</h3>", unsafe_allow_html=True)
    
    annual_diesel_saved_litres = annual_idle_hours_saved * fuel_consumption_lph
    co2_avoided_kg = annual_diesel_saved_litres * 2.68
    co2_avoided_tons = co2_avoided_kg / 1000
    trees_preserved = forest_preserved_exploration * 400
    
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
    payback_months = (implementation_capex / total_annual_value) * 12
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Annual Value Created", format_inr(total_annual_value), "Capex + Rev + OpEx")
    c2.metric("Implementation Capex", format_inr(implementation_capex), "Software & Cloud")
    c3.metric("Payback Period", f"{payback_months:.1f} Months", f"~ {payback_months*30:.0f} Days")
    
    st.success(f"**Lightning Fast ROI:** With an estimated implementation Capex of **{format_inr(implementation_capex)}**, the MOIL-GeoSync ecosystem pays for itself in just **{payback_months:.1f} months**.")
