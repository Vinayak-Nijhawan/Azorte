"""
MOIL-GeoSync (G-Sync) Dashboard
================================
AI-Powered Manganese Exploration & Production Optimization
Team Azorte | SIH 2026 | PS 26009

Run with: streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    layout="wide",
    page_title="MOIL-GeoSync",
    page_icon="⛏️",
    initial_sidebar_state="expanded",
)

pg = st.navigation([
    st.Page("src/pages/01_home.py",            title="Overview",              icon="🏠"),
    st.Page("src/pages/02_prospectivity.py",   title="GeoProspect AI",        icon="🗺️"),
    st.Page("src/pages/03_production.py",      title="Production Forecast",   icon="📈"),
    st.Page("src/pages/04_fleet_dispatch.py",  title="Fleet Dispatch",        icon="🚛"),
    st.Page("src/pages/06_what_if.py",         title="What-If Simulator",     icon="🎛️"),
    st.Page("src/pages/07_explainability.py",  title="AI Explainability",     icon="🧬"),
    st.Page("src/pages/08_ai_assistant.py",    title="G-Sync AI",             icon="🤖"),
    st.Page("src/pages/09_financial.py",       title="Financial ROI",         icon="💰"),
    st.Page("src/pages/05_methodology.py",     title="Data & Model Info",     icon="🔬"),
])

pg.run()
