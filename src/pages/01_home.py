import streamlit as st

import sys
import os
# Add the project root to sys.path so we can import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils import load_css, inject_kpi_animations, inject_volcano_animations
load_css()

import pandas as pd
import os

st.markdown("""
<style>
/* Dashboard Specific Global overrides */
.glass-panel {
    background: var(--secondary-background-color) !important; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08) !important; border: 1px solid rgba(128, 128, 128, 0.2) !important;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid color-mix(in srgb, var(--text-color) 15%, transparent);
    border-radius: 16px;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.2);
}

/* Header Area */
.modern-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 24px 32px;
    margin-bottom: 32px;
    background: #EBF2FA !important;
    border-left: 4px solid #FF9933 !important;
}
.header-titles h1 {
    font-size: 2.4rem !important;
    font-weight: 800 !important;
    color: #111827 !important;
    margin: 0 0 4px 0 !important;
    letter-spacing: -0.02em;
}
.header-titles p {
    font-size: 1.05rem !important;
    color: #4B5563 !important;
    margin: 0 !important;
    font-weight: 400;
}
.header-actions {
    display: flex;
    align-items: center;
    gap: 16px;
}
.search-bar {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid color-mix(in srgb, var(--text-color) 20%, transparent);
    border-radius: 9999px;
    padding: 8px 20px;
    display: flex;
    align-items: center;
    gap: 8px;
    color: color-mix(in srgb, var(--text-color) 60%, transparent);
    font-size: 0.9rem;
    width: 250px;
}
.search-bar i {
    opacity: 0.7;
}
.profile-action {
    display: flex;
    align-items: center;
    gap: 10px;
    background: rgba(30, 41, 59, 0.5);
    padding: 6px 12px 6px 6px;
    border-radius: 9999px;
    border: 1px solid color-mix(in srgb, var(--text-color) 20%, transparent);
    cursor: pointer;
}
.profile-avatar {
    width: 32px;
    height: 32px;
    background: linear-gradient(135deg, #3B82F6, #8B5CF6);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: bold;
    font-size: 0.8rem;
}
.profile-name {
    font-size: 0.85rem;
    color: var(--text-color);
    font-weight: 600;
}

/* KPI Cards */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 24px;
    margin-bottom: 32px;
}
.kpi-card {
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    transition: all 0.2s ease;
    cursor: default;
}
.kpi-card:hover {
    border-color: rgba(59, 130, 246, 0.5);
    box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.1);
    transform: translateY(-2px);
}
.kpi-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.kpi-title {
    color: color-mix(in srgb, var(--text-color) 60%, transparent);
    font-size: 0.9rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.kpi-icon {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.1rem;
}
.icon-blue { background: rgba(59, 130, 246, 0.1); color: #3B82F6; }
.icon-emerald { background: rgba(16, 185, 129, 0.1); color: #10B981; }
.icon-purple { background: rgba(139, 92, 246, 0.1); color: #8B5CF6; }
.icon-amber { background: rgba(245, 158, 11, 0.1); color: #F59E0B; }

.kpi-value {
    font-size: 2.2rem;
    font-weight: 700;
    color: var(--text-color);
    line-height: 1.2;
}
.kpi-footer {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 4px;
}
.trend-badge {
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 4px;
}
.trend-up { background: rgba(16, 185, 129, 0.15); color: #34D399; }
.trend-down { background: rgba(244, 63, 94, 0.15); color: #FB7185; }
.trend-neutral { background: rgba(148, 163, 184, 0.15); color: color-mix(in srgb, var(--text-color) 60%, transparent); }
.kpi-subtext {
    font-size: 0.8rem;
    color: color-mix(in srgb, var(--text-color) 50%, transparent);
}

/* Outcome Cards */
.outcome-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 24px;
    margin-bottom: 32px;
}
.outcome-card {
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 12px;
}
.outcome-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--text-color);
    display: flex;
    align-items: center;
    gap: 10px;
}
.outcome-title i {
    color: #3B82F6;
    font-size: 1.2rem;
}
.outcome-desc {
    font-size: 0.9rem;
    color: color-mix(in srgb, var(--text-color) 60%, transparent);
    line-height: 1.5;
}

/* Nav Cards */
.nav-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
}

/* Native Dot-Border Effect for Streamlit Quick Actions */
[data-testid="stPageLink"] {
    position: relative !important;
    --dot-size: 4px;
    --line-weight: 1px;
    --animation-speed: 0.35s;
    --dot-color: rgba(255, 255, 255, 0.6);
    --line-color: rgba(255, 255, 255, 0.3);
    --grid-color: rgba(255, 255, 255, 0.05);
}

[data-testid="stPageLink"] a {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    gap: 10px !important;
    background-color: var(--secondary-background-color) !important;
    border: 1px solid rgba(51, 65, 85, 0.5) !important;
    border-radius: 8px !important;
    padding: 12px 16px !important;
    color: var(--text-color) !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
    text-decoration: none !important;
    width: 100% !important;
    box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
    z-index: 10 !important;
    position: relative;
    /* Draw the lines using multiple background gradients */
    background-image: 
        linear-gradient(var(--line-color), var(--line-color)),
        linear-gradient(var(--line-color), var(--line-color)),
        linear-gradient(var(--line-color), var(--line-color)),
        linear-gradient(var(--line-color), var(--line-color)),
        repeating-linear-gradient(45deg, var(--grid-color) 0 1px, transparent 2px 5px) !important;
    background-position: top left, top right, bottom right, bottom left, center !important;
    background-repeat: no-repeat, no-repeat, no-repeat, no-repeat, repeat !important;
    background-size: 0% var(--line-weight), var(--line-weight) 0%, 0% var(--line-weight), var(--line-weight) 0%, 100% 100% !important;
    transition: background-size var(--animation-speed) ease-in-out, transform 0.2s, box-shadow 0.2s !important;
}

/* Hover effects for the background grid and lines */
[data-testid="stPageLink"]:hover a {
    background-color: var(--background-color) !important;
    color: var(--text-color) !important;
    box-shadow: 0 4px 12px rgba(6, 182, 212, 0.15) !important;
    background-size: 100% var(--line-weight), var(--line-weight) 100%, 100% var(--line-weight), var(--line-weight) 100%, 100% 100% !important;
}

/* 4 Dots using Pseudo-elements on wrapper and anchor */
[data-testid="stPageLink"]::before,
[data-testid="stPageLink"]::after,
[data-testid="stPageLink"] a::before,
[data-testid="stPageLink"] a::after {
    content: '' !important;
    position: absolute !important;
    width: var(--dot-size) !important;
    height: var(--dot-size) !important;
    background-color: var(--dot-color) !important;
    border-radius: 50% !important;
    opacity: 0 !important;
    z-index: 20 !important;
    transition: all var(--animation-speed) ease-in-out !important;
    pointer-events: none !important;
}

/* Top-Left */
[data-testid="stPageLink"]::before { top: -2px !important; left: -2px !important; transform: translate(10px, 10px) !important; transition-delay: 0s !important; }
/* Top-Right */
[data-testid="stPageLink"]::after { top: -2px !important; right: -2px !important; transform: translate(-10px, 10px) !important; transition-delay: 0.1s !important; }
/* Bottom-Right */
[data-testid="stPageLink"] a::before { bottom: -2px !important; right: -2px !important; transform: translate(-10px, -10px) !important; transition-delay: 0.2s !important; }
/* Bottom-Left */
[data-testid="stPageLink"] a::after { bottom: -2px !important; left: -2px !important; transform: translate(10px, -10px) !important; transition-delay: 0.3s !important; }

[data-testid="stPageLink"]:hover::before,
[data-testid="stPageLink"]:hover::after,
[data-testid="stPageLink"]:hover a::before,
[data-testid="stPageLink"]:hover a::after {
    transform: translate(0, 0) !important;
    opacity: 1 !important;
}


/* Quick Actions Header specific styling */
.qa-header {
    margin-top: 32px;
    margin-bottom: 24px;
}
.qa-header h3 {
    font-size: 1.15rem;
    color: var(--text-color);
    font-weight: 600;
    margin: 0;
    letter-spacing: 0.02em;
}
.qa-header p {
    font-size: 0.8rem;
    color: color-mix(in srgb, var(--text-color) 60%, transparent);
    margin: 4px 0 12px 0;
}
.qa-divider {
    border-bottom: 1px solid rgba(51, 65, 85, 0.8);
    width: 100%;
    margin-bottom: 24px;
}

</style>
""", unsafe_allow_html=True)

# Define paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

# Load data for KPIs
@st.cache_data
def load_kpi_data():
    kpi_data = {
        'total_grid_points': 45200,
        'high_prospectivity_zones': 124,
        'mines_tracked': 10,
        'avg_shortfall_risk': "14.2"
    }
    
    prospectivity_path = os.path.join(DATA_DIR, 'prospectivity_grid.csv')
    try:
        if os.path.exists(prospectivity_path):
            df_prosp = pd.read_csv(prospectivity_path)
            kpi_data['total_grid_points'] = len(df_prosp)
            if 'mn_probability' in df_prosp.columns:
                kpi_data['high_prospectivity_zones'] = len(df_prosp[df_prosp['mn_probability'] > 0.45])
    except Exception as e:
        pass

    prod_path = os.path.join(DATA_DIR, 'production_dataset_real.csv')
    try:
        if os.path.exists(prod_path):
            df_prod = pd.read_csv(prod_path, comment='#')
            if 'mine_id' in df_prod.columns:
                kpi_data['mines_tracked'] = df_prod['mine_id'].nunique()
            if 'shortfall_risk__DERIVED' in df_prod.columns:
                high_count = (df_prod['shortfall_risk__DERIVED'] == 'High').sum()
                kpi_data['avg_shortfall_risk'] = f"{high_count} High Risk"
    except Exception as e:
        pass
        
    return kpi_data

kpi = load_kpi_data()

# 1. Header Area
st.markdown("""
<div class="glass-panel modern-header">
    <div class="header-titles">
        <h1>MOIL-GeoSync (G-Sync)</h1>
        <p>AI-Powered Manganese Exploration & Production Optimization</p>
    </div>
    <div class="header-actions">
        <div class="search-bar">
            <span class=\"material-symbols-rounded\" style="vertical-align: middle; font-size: 1.2rem;">search</span> Search modules or reports...
        </div>
        <div class="profile-action">
            <div class="profile-avatar">VN</div>
            <div class="profile-name">Vinayak Nijhawan</div>
            <span style="color: color-mix(in srgb, var(--text-color) 50%, transparent); font-size: 0.8rem; margin-left: 4px;">▼</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# 2. KPI Section
st.markdown("""
<div class="kpi-grid">
    <div class="glass-panel kpi-card">
        <div class="kpi-header">
            <div class="kpi-title">Total Grid Points</div>
            <div class="kpi-icon icon-blue"><span class=\"material-symbols-rounded\">my_location</span></div>
        </div>
        <div class="kpi-value">{:,}</div>
        <div class="kpi-footer">
            <span class="trend-badge trend-up">↑ 12%</span>
            <span class="kpi-subtext">vs last scan</span>
        </div>
    </div>
    <div class="glass-panel kpi-card">
        <div class="kpi-header">
            <div class="kpi-title">High Prospectivity</div>
            <div class="kpi-icon icon-emerald"><span class=\"material-symbols-rounded\">flare</span></div>
        </div>
        <div class="kpi-value">{}</div>
        <div class="kpi-footer">
            <span class="trend-badge trend-up">↑ 4 new</span>
            <span class="kpi-subtext">this month</span>
        </div>
    </div>
    <div class="glass-panel kpi-card">
        <div class="kpi-header">
            <div class="kpi-title">Active Mines</div>
            <div class="kpi-icon icon-purple"><span class=\"material-symbols-rounded\">architecture</span></div>
        </div>
        <div class="kpi-value">{}</div>
        <div class="kpi-footer">
            <span class="trend-badge trend-neutral">→ 0</span>
            <span class="kpi-subtext">no change</span>
        </div>
    </div>
    <div class="glass-panel kpi-card">
        <div class="kpi-header">
            <div class="kpi-title">Avg Shortfall Risk</div>
            <div class="kpi-icon icon-amber"><span class=\"material-symbols-rounded\">warning</span></div>
        </div>
        <div class="kpi-value">{}%</div>
        <div class="kpi-footer">
            <span class="trend-badge trend-down">↓ 2.1%</span>
            <span class="kpi-subtext">improved</span>
        </div>
    </div>
</div>
""".format(
    kpi["total_grid_points"], 
    kpi["high_prospectivity_zones"], 
    kpi["mines_tracked"], 
    kpi["avg_shortfall_risk"]
), unsafe_allow_html=True)

# 3. Outcomes Section
st.markdown("""<h3 style="font-size: 1.1rem; color: var(--text-color); margin-bottom: 16px; font-weight: 600;">System Capabilities</h3>""", unsafe_allow_html=True)
st.markdown("""
<div class="outcome-grid">
    <div class="glass-panel outcome-card">
        <div class="outcome-title"><span class=\"material-symbols-rounded\">explore</span> Focused Exploration</div>
        <div class="outcome-desc">Drastically reduce survey area by targeting AI-identified high-probability zones across all belts.</div>
    </div>
    <div class="glass-panel outcome-card">
        <div class="outcome-title"><span class=\"material-symbols-rounded\">timer</span> Reduced Delays</div>
        <div class="outcome-desc">Proactive production risk management anticipates shortfalls before they occur.</div>
    </div>
    <div class="glass-panel outcome-card">
        <div class="outcome-title"><span class=\"material-symbols-rounded\">settings</span> Resource Utilization</div>
        <div class="outcome-desc">Optimized fleet and machinery deployment using advanced mathematical solvers.</div>
    </div>
    <div class="glass-panel outcome-card">
        <div class="outcome-title"><span class=\"material-symbols-rounded\">eco</span> Lower Impact</div>
        <div class="outcome-desc">Fewer exploratory drillings needed, reducing overall environmental disturbance.</div>
    </div>
</div>
""", unsafe_allow_html=True)

# 4. Navigation
st.markdown("""
<div class="qa-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <h3>Quick Actions</h3>
        <span style="font-size: 0.75rem; color: color-mix(in srgb, var(--text-color) 60%, transparent);">Shortcuts to platform modules</span>
    </div>
    <div class="qa-divider"></div>
</div>
""", unsafe_allow_html=True)

col_a, col_b, col_c, col_d = st.columns(4)
with col_a: st.page_link("src/pages/02_prospectivity.py", label="GeoProspect AI", icon=":material/explore:")
with col_b: st.page_link("src/pages/03_production.py", label="Production Forecast", icon=":material/monitoring:")
with col_c: st.page_link("src/pages/04_fleet_dispatch.py", label="Fleet Dispatch", icon=":material/local_shipping:")
with col_d: st.page_link("src/pages/06_what_if.py", label="What-If Simulator", icon=":material/tune:")

st.write("")
col_e, col_f, col_g, col_h = st.columns(4)
with col_e: st.page_link("src/pages/07_explainability.py", label="AI Explainability", icon=":material/science:")
with col_f: st.page_link("src/pages/08_ai_assistant.py", label="G-Sync AI", icon=":material/smart_toy:")
with col_g: st.page_link("src/pages/09_financial.py", label="Financial ROI", icon=":material/attach_money:")
with col_h: st.page_link("src/pages/05_methodology.py", label="Data & Model Info", icon=":material/info:")



# --- Animations ---
inject_kpi_animations()
inject_volcano_animations()
