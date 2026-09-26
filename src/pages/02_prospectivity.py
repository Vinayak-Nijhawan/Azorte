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
import joblib
import os
import numpy as np
from dotenv import load_dotenv
load_dotenv()

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
MODEL_DIR = os.path.join(PROJECT_ROOT, 'models')

@st.cache_data
def load_data():
    try:
        return pd.read_csv(os.path.join(DATA_DIR, 'prospectivity_grid.csv'))
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

@st.cache_resource
def load_model():
    try:
        return joblib.load(os.path.join(MODEL_DIR, 'prospectivity_pu_rf.joblib'))
    except Exception:
        return None

st.markdown("""
<style>
/* 
   Increase font size and brightness of the metric labels (e.g., HIGH PRIORITY)
   Using high-specificity selectors to guarantee we beat Streamlit's defaults.
*/
div[data-testid="stMain"] div[data-testid="stMetricLabel"] p,
div[data-testid="stMain"] div[data-testid="stMetricLabel"] > div > div > p,
div[data-testid="stMetricLabel"] label p {
    font-size: 1.15rem !important;
    color: #ffffff !important; 
    font-weight: 700 !important;
    letter-spacing: 0.5px !important;
    opacity: 1.0 !important;
}
</style>
<div class="fd-header">
    <div class="fd-header-left">
        <h1>🎯 GeoProspect AI - Prospectivity Analysis</h1>
        <div class="fd-subtitle">AI-Powered Mineral Exploration · MOIL Manganese Operations</div>
    </div>
    <div class="fd-header-right">
        <div class="fd-tag">🗺️ Exploration</div>
        <div class="fd-live"><div class="fd-live-dot"></div> OPERATIONAL</div>
    </div>
</div>
""", unsafe_allow_html=True)
st.markdown("Interactive AI-predicted map · Pan-India Manganese Belt Analysis")

df = load_data()
model = load_model()

if df.empty:
    st.warning("No data found. Run the pipeline first.")
    st.stop()

# ================= LAYOUT: MAP (left) + CONTROLS (right) =================
col_map, col_ctrl = st.columns([3, 1], gap="large")

with col_ctrl:
    region = st.selectbox("🌍 Region", ["Central India (Nagpur)", "Eastern India (Odisha)", "Southern India (Karnataka)"])
    if "Central" in region:
        map_center = dict(lat=21.45, lon=79.65)
    elif "Eastern" in region:
        map_center = dict(lat=22.05, lon=85.25)
    else:
        map_center = dict(lat=15.15, lon=76.55)

    st.write("### Layers")
    show_heatmap = st.toggle("🔥 Prospectivity", value=True)
    show_iron = st.toggle("🟠 Iron Index", value=False)
    show_mines = st.toggle("⛏️ Known Mines", value=False)
    show_drill = st.toggle("🎯 Drill Zones", value=False)

    map_style = st.radio("Map Type", ["Dark", "Satellite", "Terrain", "Street Map"], index=0, horizontal=True)

    mapbox_token = os.environ.get("MAPBOX_TOKEN", "")

    if map_style == "Dark":
        plotly_style = "carto-darkmatter"
    elif map_style == "Satellite":
        plotly_style = "satellite-streets"
    elif map_style == "Terrain":
        plotly_style = "outdoors"
    else:
        plotly_style = "streets"

    overlay_radius = st.slider("Spread", 8, 40, 18)
    overlay_opacity = st.slider("Opacity", 0.1, 1.0, 0.6, 0.1)

with col_map:
    fig = go.Figure()

    # Force Plotly to render the Map canvas even if all toggles are turned off
    fig.add_trace(go.Scattermap(lat=[None], lon=[None], showlegend=False, hoverinfo='none'))

    # ---- LAYER 1: Prospectivity (Sharp Scatter Points) ----
    if show_heatmap and 'mn_probability' in df.columns:
        # Filter out very low probability points for cleaner viz
        viz_df = df[df['mn_probability'] > 0.15].copy()
        
        # Color mapping: Low=blue, Medium=yellow, High=red
        def prob_to_color(p):
            if p >= 0.8:
                return 'rgba(220,30,30,0.85)'    # Red - HIGH
            elif p >= 0.6:
                return 'rgba(255,140,0,0.75)'     # Orange
            elif p >= 0.4:
                return 'rgba(255,220,50,0.65)'     # Yellow - MEDIUM
            elif p >= 0.25:
                return 'rgba(50,200,100,0.50)'     # Green
            else:
                return 'rgba(30,100,220,0.35)'     # Blue - LOW
        
        viz_df['color'] = viz_df['mn_probability'].apply(prob_to_color)
        viz_df['size'] = np.clip(viz_df['mn_probability'] * 12, 3, 14)
        
        # Sort so high-probability dots render on top
        viz_df = viz_df.sort_values('mn_probability', ascending=True)
        
        fig.add_trace(go.Scattermap(
            lat=viz_df['latitude'], lon=viz_df['longitude'],
            mode='markers',
            marker=dict(
                size=viz_df['size'],
                color=viz_df['mn_probability'],
                colorscale=[[0,'#1a5fb4'],[0.3,'#26a269'],[0.5,'#f5c211'],[0.7,'#ff7800'],[1.0,'#e01b24']],
                cmin=0.15, cmax=1.0,
                opacity=overlay_opacity,
                colorbar=dict(title=dict(text="Mn Prob"), x=1.0, len=0.5, y=0.75, thickness=12),
            ),
            name='Prospectivity', showlegend=True,
            text=viz_df['mn_probability'],
            hovertemplate='Lat: %{lat:.4f}<br>Lon: %{lon:.4f}<br>Prob: %{text:.3f}<extra></extra>',
        ))


    # ---- LAYER 3: Iron Oxide ----
    if show_iron and 'iron_oxide_index' in df.columns:
        fe = df.copy()
        fe['fe_norm'] = (fe['iron_oxide_index'] - fe['iron_oxide_index'].min()) / (fe['iron_oxide_index'].max() - fe['iron_oxide_index'].min() + 1e-10)
        fe_high = fe[fe['fe_norm'] > 0.3]
        fig.add_trace(go.Densitymap(
            lat=fe_high['latitude'], lon=fe_high['longitude'],
            z=fe_high['fe_norm'],
            radius=overlay_radius, opacity=overlay_opacity * 0.6,
            colorscale=[[0,'rgba(255,255,200,0.2)'],[0.5,'rgba(255,140,0,0.6)'],[1.0,'rgba(180,0,0,0.9)']],
            colorbar=dict(title=dict(text="Fe Index"), x=1.08, len=0.3, y=0.7, thickness=10),
            name='Iron Oxide', showlegend=True,
        ))

    # ---- LAYER 4: Known Mines (Real MOIL Locations) ----
    if show_mines:
        # Real coordinates from forestsclearance.nic.in, ResearchGate, Mapcarta
        mines_data = [
            (21.550, 79.717, "Dongri Buzurg", "Central"),
            (21.517, 79.750, "Chikla Mine", "Central"),
            (21.389, 79.287, "Munsar Mine", "Central"),
            (21.850, 80.228, "Balaghat Mine", "Central"),
            (21.400, 79.267, "Kandri Mine", "Central"),
            (21.400, 78.983, "Gumgaon Mine", "Central"),
            # Odisha (Joda-Barbil belt)
            (22.010, 85.437, "Joda East Mine", "Odisha"),
            (22.100, 85.250, "Bamebari Mine", "Odisha"),
            # Karnataka (Sandur schist belt)
            (15.083, 76.550, "Sandur Mine", "Karnataka"),
            (15.250, 76.350, "Hospet Mine", "Karnataka"),
        ]
        
        m_lats = [m[0] for m in mines_data]
        m_lons = [m[1] for m in mines_data]
        m_names = [m[2] for m in mines_data]
        m_regions = [m[3] for m in mines_data]
        m_colors = ['red' if r == 'Central' else 'cyan' if r == 'Odisha' else 'lime' for r in m_regions]
        
        fig.add_trace(go.Scattermap(
            lat=m_lats, lon=m_lons,
            mode='markers+text',
            marker=dict(size=14, color=m_colors),
            text=m_names, textposition='top center',
            textfont=dict(size=11, color='white'),
            name='⛏️ Known Mines',
            hovertemplate='%{text}<br>Lat: %{lat:.4f}<br>Lon: %{lon:.4f}<extra></extra>',
        ))

    # ---- LAYER 5: Drilling Priority Zones ----
    if show_drill and 'mn_probability' in df.columns:
        top_drill = df[df['mn_probability'] > 0.8].nlargest(25, 'mn_probability')
        fig.add_trace(go.Scattermap(
            lat=top_drill['latitude'], lon=top_drill['longitude'],
            mode='markers',
            marker=dict(
                size=14, 
                color='#FF00FF',  # Neon Purple/Magenta
                opacity=1.0
            ),
            name='🎯 Drill Priority',
            hovertemplate='Prob: %{customdata:.3f}<extra>Drill Target</extra>',
            customdata=top_drill['mn_probability'],
        ))

    fig.update_layout(
        map=dict(style=plotly_style, center=map_center, zoom=10),
        height=600,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(yanchor="top", y=0.98, xanchor="left", x=0.01,
                    bgcolor="rgba(0,0,0,0.7)", font=dict(color="white", size=11)),
    )

    st.plotly_chart(fig, use_container_width=True)

# ================= TARGET STATS =================
st.markdown("---")
st.subheader("Target Statistics")

# Add region column to df for filtering
def get_region(lat, lon):
    if lat >= 21.0 and lat <= 22.0 and lon >= 78.5 and lon <= 80.5:
        return "Central India"
    elif lat >= 21.5 and lon >= 84.5:
        return "Odisha"
    elif lat < 16.0:
        return "Karnataka"
    return "Other"

if 'mn_probability' in df.columns:
    df['region'] = [get_region(lat, lon) for lat, lon in zip(df['latitude'], df['longitude'])]

    high_count   = int((df['mn_probability'] > 0.8).sum())
    medium_count = int(((df['mn_probability'] > 0.4) & (df['mn_probability'] <= 0.8)).sum())
    low_count    = int((df['mn_probability'] <= 0.4).sum())

    ci_high  = int((df[df['region'] == 'Central India']['mn_probability'] > 0.8).sum()) if len(df[df['region'] == 'Central India']) > 0 else 0
    od_high  = int((df[df['region'] == 'Odisha']['mn_probability'] > 0.8).sum())        if len(df[df['region'] == 'Odisha']) > 0       else 0
    kar_high = int((df[df['region'] == 'Karnataka']['mn_probability'] > 0.8).sum())     if len(df[df['region'] == 'Karnataka']) > 0    else 0

    st.markdown(f"""
<style>
/* KPI cards for GeoProspect — mirrors the Overview dashboard style */
.geo-kpi-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
    margin-bottom: 24px;
}}
.geo-kpi-card {{
    background: rgba(17, 24, 39, 0.7);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(30, 41, 59, 0.8);
    border-radius: 16px;
    padding: 22px 24px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3);
    transition: all 0.2s ease;
}}
.geo-kpi-card:hover {{
    border-color: rgba(59, 130, 246, 0.5);
    transform: translateY(-2px);
}}
.geo-kpi-header {{ display: flex; justify-content: space-between; align-items: center; }}
.geo-kpi-title {{
    color: #94A3B8;
    font-size: 0.9rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}
.geo-kpi-icon {{
    width: 36px; height: 36px;
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.1rem;
}}
.geo-icon-red    {{ background: rgba(239, 68, 68, 0.1);   color: #EF4444; }}
.geo-icon-amber  {{ background: rgba(245, 158, 11, 0.1);  color: #F59E0B; }}
.geo-icon-green  {{ background: rgba(16, 185, 129, 0.1);  color: #10B981; }}
.geo-icon-pink   {{ background: rgba(236, 72, 153, 0.1);  color: #EC4899; }}
.geo-icon-blue   {{ background: rgba(59, 130, 246, 0.1);  color: #3B82F6; }}
.geo-icon-lime   {{ background: rgba(132, 204, 22, 0.1);  color: #84CC16; }}
.geo-kpi-value {{
    font-size: 2.2rem;
    font-weight: 700;
    color: #F8FAFC;
    line-height: 1.2;
}}
.geo-kpi-footer {{ display: flex; align-items: center; gap: 8px; margin-top: 2px; }}
.geo-kpi-subtext {{ font-size: 0.8rem; color: #64748B; }}
.geo-trend-red    {{ background: rgba(239, 68, 68, 0.15);   color: #F87171; padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }}
.geo-trend-amber  {{ background: rgba(245, 158, 11, 0.15);  color: #FCD34D; padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }}
.geo-trend-green  {{ background: rgba(16, 185, 129, 0.15);  color: #34D399; padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }}
</style>

<div class="geo-kpi-grid">
    <div class="geo-kpi-card">
        <div class="geo-kpi-header">
            <div class="geo-kpi-title">High Priority</div>
            <div class="geo-kpi-icon geo-icon-red">🔴</div>
        </div>
        <div class="geo-kpi-value">{high_count} targets</div>
        <div class="geo-kpi-footer">
            <span class="geo-trend-red">Mn Prob &gt; 0.8</span>
            <span class="geo-kpi-subtext">drill candidates</span>
        </div>
    </div>
    <div class="geo-kpi-card">
        <div class="geo-kpi-header">
            <div class="geo-kpi-title">Medium Priority</div>
            <div class="geo-kpi-icon geo-icon-amber">🟡</div>
        </div>
        <div class="geo-kpi-value">{medium_count} targets</div>
        <div class="geo-kpi-footer">
            <span class="geo-trend-amber">Mn Prob 0.4–0.8</span>
            <span class="geo-kpi-subtext">further study</span>
        </div>
    </div>
    <div class="geo-kpi-card">
        <div class="geo-kpi-header">
            <div class="geo-kpi-title">Low Priority</div>
            <div class="geo-kpi-icon geo-icon-green">🟢</div>
        </div>
        <div class="geo-kpi-value">{low_count} targets</div>
        <div class="geo-kpi-footer">
            <span class="geo-trend-green">Mn Prob ≤ 0.4</span>
            <span class="geo-kpi-subtext">low probability</span>
        </div>
    </div>
</div>

<p style="font-weight:600; color:#E2E8F0; margin:8px 0 12px 0;">Region-wise High Priority Targets:</p>
<div class="geo-kpi-grid">
    <div class="geo-kpi-card">
        <div class="geo-kpi-header">
            <div class="geo-kpi-title">Central India</div>
            <div class="geo-kpi-icon geo-icon-pink">🟥</div>
        </div>
        <div class="geo-kpi-value">{ci_high} targets</div>
        <div class="geo-kpi-footer">
            <span class="geo-trend-red">Nagpur Belt</span>
        </div>
    </div>
    <div class="geo-kpi-card">
        <div class="geo-kpi-header">
            <div class="geo-kpi-title">Odisha</div>
            <div class="geo-kpi-icon geo-icon-blue">🟦</div>
        </div>
        <div class="geo-kpi-value">{od_high} targets</div>
        <div class="geo-kpi-footer">
            <span class="geo-trend-amber">Joda-Barbil Belt</span>
        </div>
    </div>
    <div class="geo-kpi-card">
        <div class="geo-kpi-header">
            <div class="geo-kpi-title">Karnataka</div>
            <div class="geo-kpi-icon geo-icon-lime">🟩</div>
        </div>
        <div class="geo-kpi-value">{kar_high} targets</div>
        <div class="geo-kpi-footer">
            <span class="geo-trend-green">Sandur Schist Belt</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ================= TOP DRILL TARGETS =================
st.subheader("📍 Top 10 Drill Targets")
if 'mn_probability' in df.columns:
    top_10 = df.nlargest(10, 'mn_probability').copy()
    top_10.insert(0, 'Rank', range(1, len(top_10) + 1))
    display_cols = ['Rank', 'latitude', 'longitude', 'region', 'elevation_m', 'mn_probability', 'prospectivity_class', 'rock_type']
    available = [c for c in display_cols if c in top_10.columns]
    renames = {'Rank':'#','latitude':'Lat °N','longitude':'Lon °E','region':'Region','elevation_m':'Elev (m)',
               'mn_probability':'Probability','prospectivity_class':'Class','rock_type':'Rock Type'}
    st.dataframe(top_10[available].rename(columns=renames).reset_index(drop=True),
                 use_container_width=True, hide_index=True)

# ================= FEATURE IMPORTANCE =================
st.subheader("🔬 Feature Importance")
if model is not None:
    try:
        base = model[0] if isinstance(model, list) else model
        if hasattr(base, 'feature_importances_'):
            imp = base.feature_importances_
            names = ['iron_oxide_index','clay_index','ndvi','rock_type','fault_distance_km',
                     'shear_zone_proximity_km','elevation_m','slope_deg','rainfall_mm__REAL','soil_moisture'][:len(imp)]
            feat_df = pd.DataFrame({'Feature': names, 'Importance': imp}).sort_values('Importance', ascending=True)
            fig_imp = px.bar(feat_df, x='Importance', y='Feature', orientation='h',
                           color='Importance', color_continuous_scale='RdYlGn_r')
            fig_imp.update_layout(height=350, showlegend=False, title="Feature Importances")
            st.plotly_chart(fig_imp, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")


# --- Animations ---
inject_kpi_animations()
inject_volcano_animations()
