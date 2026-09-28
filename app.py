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
    page_icon=":material/architecture:",
    initial_sidebar_state="expanded",
)


# ── Multi-Page Setup (Hidden native sidebar, we build our own) ───────────
pages = {
    "Overview": st.Page("src/pages/01_home.py", title="Overview", icon=":material/home:", default=True),
    "GeoProspect AI": st.Page("src/pages/02_prospectivity.py", title="GeoProspect AI", icon=":material/explore:"),
    "Production Forecast": st.Page("src/pages/03_production.py", title="Production Forecast", icon=":material/monitoring:"),
    "Fleet Dispatch": st.Page("src/pages/04_fleet_dispatch.py", title="Fleet Dispatch", icon=":material/local_shipping:"),
    "Underground Dispatch": st.Page("src/pages/05_underground_dispatch.py", title="Underground Dispatch", icon=":material/elevator:"),
    "What-If Simulator": st.Page("src/pages/06_what_if.py", title="What-If Simulator", icon=":material/tune:"),
    "AI Explainability": st.Page("src/pages/07_explainability.py", title="AI Explainability", icon=":material/science:"),
    "G-Sync AI": st.Page("src/pages/08_ai_assistant.py", title="G-Sync AI", icon=":material/smart_toy:"),
    "Financial ROI": st.Page("src/pages/09_financial.py", title="Financial ROI", icon=":material/attach_money:"),
    "Data & Model Info": st.Page("src/pages/05_methodology.py", title="Data & Model Info", icon=":material/info:"),
}

pg = st.navigation(list(pages.values()), position="hidden")

# ── Custom Sidebar Construction ───────────────────────────────────────────
with st.sidebar:

    
    
    
    
    
    # 1. BRANDING & WORKSPACE
    st.markdown("### :material/architecture: G-SYNC")
    st.caption("Intelligence Platform")
    
    with st.container(border=True):
        st.markdown("**Workspace:** Team Vinayak")
    
    # 2. NAVIGATION
    st.caption("COMMAND CENTER")
    st.page_link(pages["Overview"], label="Overview", icon=":material/home:")
    st.page_link(pages["GeoProspect AI"], label="GeoProspect AI", icon=":material/explore:")
    st.page_link(pages["Production Forecast"], label="Production Forecast", icon=":material/monitoring:")
    st.page_link(pages["Fleet Dispatch"], label="Fleet Dispatch", icon=":material/local_shipping:")
    st.page_link(pages["Underground Dispatch"], label="Underground Dispatch", icon=":material/elevator:")
    st.page_link(pages["What-If Simulator"], label="What-If Simulator", icon=":material/tune:")
    
    st.write("") # Spacer
    st.caption("INTELLIGENCE")
    st.page_link(pages["AI Explainability"], label="AI Explainability", icon=":material/science:")
    st.page_link(pages["G-Sync AI"], label="G-Sync AI", icon=":material/smart_toy:")
    st.page_link(pages["Financial ROI"], label="Financial ROI", icon=":material/attach_money:")
    st.page_link(pages["Data & Model Info"], label="Data & Model Info", icon=":material/info:")
    
    # 3. FOOTER (STATUS & PROFILE AT THE VERY BOTTOM)
    st.divider()
    st.markdown("🟢 **All systems operational**")
    st.caption("Last sync 2 min ago")
    st.markdown("**Vinayak Nijhawan** · *Project Lead*")

pg.run()
