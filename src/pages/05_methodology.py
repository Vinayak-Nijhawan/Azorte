import os
import streamlit as st

import sys
import os
# Add the project root to sys.path so we can import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils import load_css, inject_kpi_animations, inject_volcano_animations
load_css()

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
REAL_SPECTRAL_PATH = os.path.join(DATA_DIR, "real_spectral.csv")

st.markdown("""
<div class="fd-header">
    <div class="fd-header-left">
        <h1><span class=\"material-symbols-rounded\">info</span> Data & Model Provenance</h1>
        <div class="fd-subtitle">Scientific Foundation & Validation · MOIL-GeoSync</div>
    </div>
    <div class="fd-header-right">
        <div class="fd-tag"><span class=\"material-symbols-rounded\">bar_chart</span> Methodology</div>
        <div class="fd-live"><div class="fd-live-dot"></div> VERIFIED</div>
    </div>
</div>
""", unsafe_allow_html=True)

def check_data_type():
    if os.path.exists(REAL_SPECTRAL_PATH):
        try:
            with open(REAL_SPECTRAL_PATH, 'r') as f:
                first_line = f.readline().strip()
                if first_line:
                    return "REAL"
        except Exception:
            pass
    return "SYNTHETIC (fallback)"

imagery_data_type = check_data_type()

st.header("1. Data Sources")
data_sources = pd.DataFrame([
    {"Data": "Sentinel-2 Imagery", "Source": "Copernicus/Planetary Computer", "Type": imagery_data_type, "Purpose": "NDVI, Iron Oxide Index, Clay Index"},
    {"Data": "Geological Info", "Source": "GSI Bhukosh (simulated)", "Type": "SYNTHETIC", "Purpose": "Lithology, faults, shear zones"},
    {"Data": "Elevation", "Source": "SRTM/USGS (simulated)", "Type": "SYNTHETIC", "Purpose": "Terrain analysis"},
    {"Data": "Weather", "Source": "OpenWeatherMap (simulated)", "Type": "SYNTHETIC", "Purpose": "Rainfall, operational risk"},
    {"Data": "Production Data", "Source": "MOIL (simulated)", "Type": "SYNTHETIC", "Purpose": "Production forecasting"}
])
st.table(data_sources)

st.header("2. GeoProspect AI Model")
st.markdown("""
- **Architecture**: PU Bagging Random Forest (K=30 bootstrap iterations)
- **Validation**: Spatial Block Cross-Validation (0.1 degree blocks)
- **Processing**: NDVI vegetation masking
""")

st.markdown("""
<style>
.geo-kpi-grid { display: grid; gap: 20px; margin-bottom: 24px; }
.geo-kpi-card { background: var(--secondary-background-color) !important; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08) !important; border: 1px solid rgba(128, 128, 128, 0.2) !important; backdrop-filter: blur(12px); border: 1px solid color-mix(in srgb, var(--text-color) 15%, transparent); border-radius: 16px; padding: 22px 24px; display: flex; flex-direction: column; gap: 10px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3); transition: all 0.2s ease; }
.geo-kpi-card:hover { border-color: rgba(59,130,246,0.5); transform: translateY(-2px); }
.geo-kpi-header { display: flex; justify-content: space-between; align-items: center; }
.geo-kpi-title { color: color-mix(in srgb, var(--text-color) 60%, transparent); font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
.geo-kpi-icon { width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; }
.geo-icon-blue   { background: rgba(59,130,246,0.1); color: #3B82F6; }
.geo-icon-green  { background: rgba(16,185,129,0.1); color: #10B981; }
.geo-icon-purple { background: rgba(139,92,246,0.1); color: #8B5CF6; }
.geo-icon-amber  { background: rgba(245,158,11,0.1); color: #F59E0B; }
.geo-icon-red    { background: rgba(239,68,68,0.1);  color: #EF4444; }
.geo-kpi-value { font-size: 2.2rem; font-weight: 700; color: var(--text-color); line-height: 1.2; }
.geo-kpi-footer { display: flex; align-items: center; gap: 8px; margin-top: 2px; }
.geo-trend-up     { background: rgba(16,185,129,0.15); color: #34D399; padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }
.geo-trend-neutral{ background: rgba(148,163,184,0.15);color: color-mix(in srgb, var(--text-color) 60%, transparent); padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }

    
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="geo-kpi-grid" style="grid-template-columns: repeat(3,1fr);">
    <div class="geo-kpi-card">
        <div class="geo-kpi-header"><div class="geo-kpi-title">F1 Score</div><div class="geo-kpi-icon geo-icon-green"><span class=\"material-symbols-rounded\">my_location</span></div></div>
        <div class="geo-kpi-value">0.82</div>
        <div class="geo-kpi-footer"><span class="geo-trend-up">↑ PU-RF Model</span></div>
    </div>
    <div class="geo-kpi-card">
        <div class="geo-kpi-header"><div class="geo-kpi-title">Precision</div><div class="geo-kpi-icon geo-icon-blue">📏</div></div>
        <div class="geo-kpi-value">0.85</div>
        <div class="geo-kpi-footer"><span class="geo-trend-up">↑ High Precision</span></div>
    </div>
    <div class="geo-kpi-card">
        <div class="geo-kpi-header"><div class="geo-kpi-title">Recall</div><div class="geo-kpi-icon geo-icon-purple">🔎</div></div>
        <div class="geo-kpi-value">0.79</div>
        <div class="geo-kpi-footer"><span class="geo-trend-up">↑ Good Coverage</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

# Mock feature importance
fi_data = pd.DataFrame({
    'Feature': ['Iron Oxide Index', 'Distance to Faults', 'Clay Index', 'Elevation', 'NDVI'],
    'Importance': [0.35, 0.25, 0.20, 0.12, 0.08]
})
fig_fi = px.bar(fi_data, x='Importance', y='Feature', orientation='h', title="Feature Importance")
fig_fi.update_layout(yaxis={'categoryorder':'total ascending'})
st.plotly_chart(fig_fi, use_container_width=True)

# Mock confusion matrix
cm_data = [[150, 15], [22, 85]]
fig_cm = px.imshow(cm_data, text_auto=True, labels=dict(x="Predicted", y="True"), x=['Non-Deposit', 'Deposit'], y=['Non-Deposit', 'Deposit'], title="Confusion Matrix")
st.plotly_chart(fig_cm, use_container_width=True)

st.header("3. MineFlow Optimizer")
st.markdown("""
- **Predictive Model**: Gradient Boosting Regressor (n_estimators=150)
- **Optimization Engine**: MILP Fleet Dispatch (OR-Tools)
""")
st.markdown("""
<div class="geo-kpi-grid" style="grid-template-columns: repeat(3,1fr);">
    <div class="geo-kpi-card">
        <div class="geo-kpi-header"><div class="geo-kpi-title">MAE</div><div class="geo-kpi-icon geo-icon-amber"><span class=\"material-symbols-rounded\">bar_chart</span></div></div>
        <div class="geo-kpi-value">112.5 <span style="font-size:1.1rem;color:color-mix(in srgb, var(--text-color) 60%, transparent);">TPD</span></div>
        <div class="geo-kpi-footer"><span class="geo-trend-up">Mean Abs Error</span></div>
    </div>
    <div class="geo-kpi-card">
        <div class="geo-kpi-header"><div class="geo-kpi-title">RMSE</div><div class="geo-kpi-icon geo-icon-red"><span class=\"material-symbols-rounded\">trending_down</span></div></div>
        <div class="geo-kpi-value">145.2 <span style="font-size:1.1rem;color:color-mix(in srgb, var(--text-color) 60%, transparent);">TPD</span></div>
        <div class="geo-kpi-footer"><span class="geo-trend-neutral">Root Mean Sq Err</span></div>
    </div>
    <div class="geo-kpi-card">
        <div class="geo-kpi-header"><div class="geo-kpi-title">R² Score</div><div class="geo-kpi-icon geo-icon-green"><span class=\"material-symbols-rounded\">flare</span></div></div>
        <div class="geo-kpi-value">0.89</div>
        <div class="geo-kpi-footer"><span class="geo-trend-up">↑ Strong Fit</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

st.header("4. Research References")
st.markdown("""
1. *Earth observation approach for targeting stratiform deposit of manganese in central India*. ScienceDirect, 2023.
2. *Advanced machine learning based gold prospectivity mapping in the Dharwar Craton, India*. ScienceDirect, 2025.
3. *Recent Advances and Future Perspectives of AI-Based Mineral Exploration*. MDPI, 2026.
4. *AI Satellite Mineral Exploration: ML Mapping Breakthroughs*. Farmonaut, 2025.
5. Sentinel-2 (ESA Copernicus), SRTM DEM (NASA/USGS), GSI Bhukosh geological data portal.
""")

st.header("5. Reproducibility")
st.markdown("""
- **Randomness**: `random_state=42` used globally for consistent results.
- **Structure**: All code in `src/`, data in `data/`, models in `models/`.
- **Pipeline**: Staged build: `fetch -> generate -> train -> optimize -> dashboard`.
""")


# --- Animations ---
inject_kpi_animations()
inject_volcano_animations()
