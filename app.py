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

# Global font size increase — aggressive override
st.markdown("""
<style>
    /* Nuclear option: force ALL text bigger */
    * {
        font-size: inherit;
    }
    
    /* Root size bump */
    :root {
        font-size: 20px !important;
    }
    
    html, body, div, span, p, li, td, th, label, input, select, textarea,
    section, header, footer, main, aside, nav, article {
        font-size: 20px !important;
        line-height: 1.6 !important;
    }
    
    /* Headings - big and bold */
    h1 { font-size: 2.8rem !important; }
    h2 { font-size: 2.2rem !important; }
    h3 { font-size: 1.8rem !important; }
    h4 { font-size: 1.5rem !important; }
    
    /* Paragraphs and list items */
    p, li, span {
        font-size: 1.15rem !important;
        line-height: 1.7 !important;
    }
    
    /* Metric cards */
    [data-testid="stMetricValue"] > div {
        font-size: 2.5rem !important;
    }
    [data-testid="stMetricLabel"] > div > div > p {
        font-size: 1.1rem !important;
    }
    [data-testid="stMetricDelta"] > div {
        font-size: 1.1rem !important;
    }
    
    /* Sidebar navigation + text */
    section[data-testid="stSidebar"] * {
        font-size: 1.05rem !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdown"] p {
        font-size: 1.1rem !important;
    }
    
    /* Buttons, selectboxes, sliders labels */
    button, [data-baseweb="select"] *, [data-baseweb="slider"] * {
        font-size: 1rem !important;
    }
    
    /* Data tables */
    table, table td, table th {
        font-size: 1rem !important;
    }
    
    /* Alert / info / warning / error boxes */
    [data-testid="stAlert"] p,
    [data-testid="stAlert"] span,
    [data-testid="stNotification"] p {
        font-size: 1.1rem !important;
    }
    
    /* Expander */
    [data-testid="stExpander"] summary span {
        font-size: 1.15rem !important;
    }
    
    /* Tabs */
    [data-baseweb="tab"] {
        font-size: 1.15rem !important;
    }
    
    /* Chat input */
    [data-testid="stChatInput"] textarea {
        font-size: 1.1rem !important;
    }
    
    /* Chat messages */
    [data-testid="stChatMessage"] p {
        font-size: 1.15rem !important;
    }
    
    /* Checkbox labels */
    [data-testid="stCheckbox"] label span {
        font-size: 1.1rem !important;
    }
    
    /* Caption text */
    [data-testid="stCaption"] {
        font-size: 0.95rem !important;
    }
</style>
""", unsafe_allow_html=True)

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
