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
    /* Targeted font size bumps (avoiding wildcards that break Streamlit UI components like sliders) */
    
    /* Removed aggressive global font-size overrides that break complex widgets */
    
    /* Headings - big and bold */
    h1 { font-size: 2.8rem !important; }
    h2 { font-size: 2.2rem !important; }
    h3 { font-size: 1.8rem !important; }
    h4 { font-size: 1.5rem !important; }
    
    /* Paragraphs and list items */
    .stMarkdown p, .stMarkdown li {
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
    [data-testid="stDataFrame"], table, table td, table th {
        font-size: 20px !important;
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
    
    /* Global Dashboard Headers */
    .fd-header {
        background: linear-gradient(135deg, rgba(30,58,95,0.5) 0%, rgba(15,23,42,0.8) 100%);
        border: 1px solid rgba(100,116,139,0.2);
        border-radius: 12px;
        padding: 20px 28px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
    }
    .fd-header-left h1 {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #e2e8f0 !important;
        margin: 0 !important;
        letter-spacing: 0.5px;
    }
    .fd-header-left .fd-subtitle {
        font-size: 0.85rem !important;
        color: #64748b !important;
        margin-top: 2px !important;
    }
    .fd-header-right {
        display: flex;
        align-items: center;
        gap: 16px;
        flex-wrap: wrap;
    }
    .fd-tag {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 6px;
        padding: 5px 12px;
        font-size: 0.78rem !important;
        color: #94a3b8 !important;
    }
    .fd-live {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(34,197,94,0.1);
        border: 1px solid rgba(34,197,94,0.25);
        border-radius: 6px;
        padding: 5px 12px;
        font-size: 0.78rem !important;
        color: #4ade80 !important;
        font-weight: 600;
    }
    .fd-live-dot {
        width: 7px; height: 7px;
        background: #22c55e;
        border-radius: 50%;
        animation: pulse-dot 1.5s infinite;
    }
    @keyframes pulse-dot {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
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
