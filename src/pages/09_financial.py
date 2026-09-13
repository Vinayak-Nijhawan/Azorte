import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os

st.title("Financial Impact & ROI Analysis 💰")
st.caption("⚠️ All financial projections are illustrative, based on industry-standard cost assumptions. Replace with actual MOIL data for deployment.")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

@st.cache_data
def load_data():
    prospectivity_df = pd.read_csv(os.path.join(PROJECT_ROOT, "data", "prospectivity_grid.csv"))
    production_df = pd.read_csv(os.path.join(PROJECT_ROOT, "data", "production_dataset.csv"))
    dispatch_df = pd.read_csv(os.path.join(PROJECT_ROOT, "data", "dispatch_plan.csv"))
    return prospectivity_df, production_df, dispatch_df

def format_inr(amount):
    if amount >= 1e7:
        return f'₹{amount/1e7:.2f} Cr'
    elif amount >= 1e5:
        return f'₹{amount/1e5:.2f} L'
    else:
        return f'₹{amount:,.0f}'

try:
    prospectivity_df, production_df, dispatch_df = load_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

st.sidebar.header("Cost Assumptions")
ore_price = st.sidebar.slider("Manganese ore price (₹/ton)", 5000, 25000, 12000, 500)
diesel_cost = st.sidebar.slider("Diesel cost per litre (₹)", 80, 120, 95, 1)
dumper_fuel_consumption = st.sidebar.slider("Dumper fuel consumption (litres/hour)", 30, 60, 40, 1)
idle_cost = st.sidebar.slider("Idle cost per dumper per hour (₹)", 2000, 10000, 5000, 500)
drill_cost = st.sidebar.slider("Exploration drill cost per site (₹)", 500000, 3000000, 1500000, 100000)
working_days = st.sidebar.slider("Working days per month", 20, 30, 25, 1)
shortfall_reduction_pct = st.sidebar.slider("AI-driven shortfall reduction (%)", 10, 80, 40, 1) / 100.0

st.header("1. Exploration Cost Savings (GeoProspect AI)")
total_traditional_sites = 100
ai_targets = len(prospectivity_df[prospectivity_df['prospectivity_class'].isin(['High', 'Medium'])])
if ai_targets == 0:
    ai_targets = 20 # Fallback

sites_avoided = max(0, total_traditional_sites - ai_targets)
exploration_savings = sites_avoided * drill_cost

col1, col2 = st.columns(2)
with col1:
    st.metric("Total Drill Sites (Without AI)", total_traditional_sites)
    st.metric("Total Drill Sites (With AI)", ai_targets)
with col2:
    st.metric("Sites Avoided", sites_avoided)
    st.metric("Exploration Cost Savings", format_inr(exploration_savings))

fig1 = go.Figure(data=[
    go.Bar(name='Cost Without AI', x=['Exploration'], y=[total_traditional_sites * drill_cost]),
    go.Bar(name='Cost With AI', x=['Exploration'], y=[ai_targets * drill_cost])
])
fig1.update_layout(title="Exploration Cost Comparison", barmode='group', yaxis_title="Cost (₹)")
st.plotly_chart(fig1, use_container_width=True)


st.header("2. Production Revenue Protection (MineFlow)")
production_df['shortfall'] = np.maximum(0, production_df['planned_production_tpd'] - production_df['actual_production_tpd'])
production_df['shortfall_monthly_tpd'] = production_df['shortfall'] * working_days
production_df['revenue_loss'] = production_df['shortfall_monthly_tpd'] * ore_price

total_revenue_loss = production_df['revenue_loss'].sum()
ai_recovery = total_revenue_loss * shortfall_reduction_pct

# Calculate Annual Recovery
months_in_data = len(production_df['month'].unique()) * len(production_df['year'].unique())
if months_in_data == 0: months_in_data = 60
annual_recovery = (ai_recovery / months_in_data) * 12

col1, col2 = st.columns(2)
with col1:
    st.metric("Total Historic Revenue Loss", format_inr(total_revenue_loss))
with col2:
    st.metric(f"MineFlow AI Recovery ({shortfall_reduction_pct*100:.0f}%)", format_inr(ai_recovery), f"Annually: {format_inr(annual_recovery)}")

mine_loss = production_df.groupby(['month', 'year', 'mine_id'])['revenue_loss'].sum().reset_index()
mine_loss['date'] = pd.to_datetime(mine_loss[['year', 'month']].assign(DAY=1))
mine_loss = mine_loss.sort_values('date')
fig2 = px.line(mine_loss, x='date', y='revenue_loss', color='mine_id', title="Monthly Revenue Loss Due to Production Shortfalls")
fig2.update_layout(yaxis_title="Revenue Loss (₹)")
st.plotly_chart(fig2, use_container_width=True)


st.header("3. Fleet Optimization Savings")
avg_achievable = dispatch_df['achievable_vs_planned_pct'].mean()
total_dumpers = len(dispatch_df['dumper_id'].unique())
if total_dumpers == 0: total_dumpers = 50

optimized_routes_reduction = 0.15 # 15% improvement
active_dumpers = int(total_dumpers * (avg_achievable / 100))
idle_dumpers = total_dumpers - active_dumpers
idle_hours_per_month = idle_dumpers * 8 * 2 * working_days
idle_cost_monthly = idle_hours_per_month * idle_cost

operating_hours_per_month = total_dumpers * 8 * 2 * working_days
diesel_savings_litres_monthly = optimized_routes_reduction * total_dumpers * dumper_fuel_consumption * 16 * working_days
diesel_savings_monthly_inr = diesel_savings_litres_monthly * diesel_cost
total_fleet_savings_monthly = idle_cost_monthly + diesel_savings_monthly_inr
total_fleet_savings_annual = total_fleet_savings_monthly * 12

col1, col2 = st.columns(2)
with col1:
    st.metric("Monthly Fleet Savings", format_inr(total_fleet_savings_monthly))
with col2:
    st.metric("Annual Fleet Savings", format_inr(total_fleet_savings_annual))


st.header("4. ESG & Carbon Impact 🌍")
annual_diesel_saved_litres = diesel_savings_litres_monthly * 12
co2_avoided_kg = annual_diesel_saved_litres * 2.68
co2_avoided_tons = co2_avoided_kg / 1000

forest_saved_hectares = sites_avoided * 0.5
trees_preserved = forest_saved_hectares * 400

col1, col2, col3 = st.columns(3)
with col1:
    st.success(f"### {co2_avoided_tons:,.1f}\n**CO₂ Avoided (tons/year)**")
with col2:
    st.success(f"### {forest_saved_hectares:,.1f}\n**Forest Saved (hectares)**")
with col3:
    st.success(f"### {trees_preserved:,.0f}\n**Equivalent Trees Preserved**")


st.header("5. Total ROI Summary")
total_annual_impact = exploration_savings + annual_recovery + total_fleet_savings_annual

st.markdown("---")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Annual Exploration Savings", format_inr(exploration_savings))
col2.metric("Annual Prod. Revenue Protected", format_inr(annual_recovery))
col3.metric("Annual Fleet Cost Savings", format_inr(total_fleet_savings_annual))
col4.metric("Total Annual Impact", format_inr(total_annual_impact), "🔥")

ai_dev_cost = 5000000 # ₹50 lakh
monthly_savings = total_annual_impact / 12
if monthly_savings > 0:
    breakeven_months = ai_dev_cost / monthly_savings
    st.info(f"**System ROI:** With an estimated development cost of ₹50 Lakh, the system pays for itself in **{breakeven_months:.1f} months**.")
