import streamlit as st
import pandas as pd
import os

st.markdown('<h1 style="font-size: 4rem; font-weight: 800; margin-bottom: -10px;">MOIL-GeoSync (G-Sync)</h1>', unsafe_allow_html=True)
st.subheader("AI-Powered Manganese Exploration & Production Optimization")

st.markdown("**Team Azorte | SIH 2026 | PS 26009**")

with st.expander("Problem Context"):
    st.markdown("""
    **Exploration:** Traditional manganese exploration is slow, expensive, and relies heavily on manual field surveys. 
    **Production:** Production monitoring is often reactive, leading to unexpected shortfalls and inefficient resource allocation.
    """)

# Define paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

# Load data for KPIs
@st.cache_data
def load_kpi_data():
    kpi_data = {
        'total_grid_points': 0,
        'high_prospectivity_zones': 0,
        'mines_tracked': 0,
        'avg_shortfall_risk': "N/A"
    }
    
    # Prospectivity
    prospectivity_path = os.path.join(DATA_DIR, 'prospectivity_grid.csv')
    try:
        if os.path.exists(prospectivity_path):
            df_prosp = pd.read_csv(prospectivity_path)
            kpi_data['total_grid_points'] = len(df_prosp)
            if 'mn_probability' in df_prosp.columns:
                kpi_data['high_prospectivity_zones'] = len(df_prosp[df_prosp['mn_probability'] > 0.8])
    except Exception as e:
        pass

    # Production
    prod_path = os.path.join(DATA_DIR, 'production_dataset.csv')
    try:
        if os.path.exists(prod_path):
            df_prod = pd.read_csv(prod_path)
            if 'mine_id' in df_prod.columns:
                kpi_data['mines_tracked'] = df_prod['mine_id'].nunique()
            if 'shortfall_risk' in df_prod.columns:
                kpi_data['avg_shortfall_risk'] = f"{df_prod['shortfall_risk'].mean():.2f}"
    except Exception as e:
        pass
        
    return kpi_data

kpi = load_kpi_data()

# Add custom CSS for hover cards
st.markdown("""
<style>
.hover-card {
    background-color: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 24px;
    transition: all 0.3s ease-in-out;
    height: 180px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.hover-card:hover {
    background-color: white !important;
    transform: translateY(-5px);
    box-shadow: 0 10px 20px rgba(0,0,0,0.2);
}
.hover-card:hover * {
    color: #0044ff !important;
}
.hover-card-title {
    font-size: 1.2rem !important;
    font-weight: 600 !important;
    margin-bottom: 12px !important;
    opacity: 0.8 !important;
}
.hover-card-value {
    font-size: 2.8rem !important;
    font-weight: 700 !important;
}
.hover-card-text {
    font-size: 1.15rem !important;
    line-height: 1.6 !important;
}
</style>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f'<div class="hover-card"><div class="hover-card-title">Total Grid Points</div><div class="hover-card-value">{kpi["total_grid_points"]:,}</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="hover-card"><div class="hover-card-title">High Prospectivity Zones</div><div class="hover-card-value">{kpi["high_prospectivity_zones"]:,}</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="hover-card"><div class="hover-card-title">Mines Tracked</div><div class="hover-card-value">{kpi["mines_tracked"]}</div></div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="hover-card"><div class="hover-card-title">Avg Shortfall Risk</div><div class="hover-card-value">{kpi["avg_shortfall_risk"]}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("### Key Outcomes")
kc1, kc2, kc3, kc4 = st.columns(4)
with kc1:
    st.markdown('<div class="hover-card"><div class="hover-card-title">Focused Exploration</div><div class="hover-card-text">Reduce survey area by targeting high-probability zones.</div></div>', unsafe_allow_html=True)
with kc2:
    st.markdown('<div class="hover-card"><div class="hover-card-title">Reduced Delays</div><div class="hover-card-text">Proactive production risk management.</div></div>', unsafe_allow_html=True)
with kc3:
    st.markdown('<div class="hover-card"><div class="hover-card-title">Better Resource Utilization</div><div class="hover-card-text">Optimized fleet and machinery deployment.</div></div>', unsafe_allow_html=True)
with kc4:
    st.markdown('<div class="hover-card"><div class="hover-card-title">Lower Environmental Disturbance</div><div class="hover-card-text">Fewer exploratory drillings needed.</div></div>', unsafe_allow_html=True)

st.markdown("### Quick Navigation")
col_a, col_b, col_c, col_d = st.columns(4)
with col_a:
    st.page_link("src/pages/02_prospectivity.py", label="GeoProspect AI", icon="🗺️")
with col_b:
    st.page_link("src/pages/03_production.py", label="Production Forecast", icon="📈")
with col_c:
    st.page_link("src/pages/04_fleet_dispatch.py", label="Fleet Dispatch", icon="🚛")
with col_d:
    st.page_link("src/pages/06_what_if.py", label="What-If Simulator", icon="🎛️")

col_e, col_f, col_g, col_h = st.columns(4)
with col_e:
    st.page_link("src/pages/07_explainability.py", label="AI Explainability", icon="🧬")
with col_f:
    st.page_link("src/pages/08_ai_assistant.py", label="G-Sync AI", icon="🤖")
with col_g:
    st.page_link("src/pages/09_financial.py", label="Financial ROI", icon="💰")
with col_h:
    st.page_link("src/pages/05_methodology.py", label="Data & Model Info", icon="🔬")
