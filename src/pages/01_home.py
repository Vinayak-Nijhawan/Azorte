import streamlit as st
import pandas as pd
import os

st.title("MOIL-GeoSync (G-Sync)")
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

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Grid Points", f"{kpi['total_grid_points']:,}")
col2.metric("High Prospectivity Zones", f"{kpi['high_prospectivity_zones']:,}")
col3.metric("Mines Tracked", kpi['mines_tracked'])
col4.metric("Avg Shortfall Risk", kpi['avg_shortfall_risk'])

st.markdown("### Key Outcomes")
kc1, kc2, kc3, kc4 = st.columns(4)
with kc1:
    st.markdown("**Focused Exploration**\nReduce survey area by targeting high-probability zones.")
with kc2:
    st.markdown("**Reduced Delays**\nProactive production risk management.")
with kc3:
    st.markdown("**Better Resource Utilization**\nOptimized fleet and machinery deployment.")
with kc4:
    st.markdown("**Lower Environmental Disturbance**\nFewer exploratory drillings needed.")

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
