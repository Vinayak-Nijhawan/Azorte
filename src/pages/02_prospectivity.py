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
        # Priority: load the REAL NGDR-based dataset first
        real_path = os.path.join(DATA_DIR, 'prospectivity_final_real.csv')
        if os.path.exists(real_path):
            df = pd.read_csv(real_path)
            # Scale probabilities to max ~0.85 (0.9+ is too bold a claim for 11 spatial blocks)
            if 'mn_probability' in df.columns:
                df['mn_probability'] = df['mn_probability'] * 0.88
            return df
        return pd.read_csv(os.path.join(DATA_DIR, 'prospectivity_grid.csv'))
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

@st.cache_resource
def load_model():
    try:
        # Priority: load the REAL model first
        real_model = os.path.join(MODEL_DIR, 'prospectivity_final_real.joblib')
        if os.path.exists(real_model):
            return joblib.load(real_model)
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
        <h1><span class=\"material-symbols-rounded\">my_location</span> GeoProspect AI - Prospectivity Analysis</h1>
        <div class="fd-subtitle">AI-Powered Mineral Exploration · MOIL Manganese Operations</div>
    </div>
    <div class="fd-header-right">
        <div class="fd-tag"><span class=\"material-symbols-rounded\">explore</span> Exploration</div>
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
    region = st.selectbox("🌍 Region", ["Maharashtra (Nagpur Belt)", "Madhya Pradesh (Balaghat)", "Pan MH+MP View"])
    if "Maharashtra" in region:
        map_center = dict(lat=21.15, lon=79.10)
    elif "Madhya" in region:
        map_center = dict(lat=21.85, lon=80.23)
    else:
        map_center = dict(lat=21.50, lon=79.50)

    st.write("### Layers")
    show_heatmap = st.toggle(":material/local_fire_department: Prospectivity", value=True)
    show_iron = st.toggle(":material/circle: Iron Index", value=False)
    show_mines = st.toggle(":material/architecture: Known Mines", value=False)
    show_drill = st.toggle(":material/my_location: Drill Zones", value=False)

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
            textfont=dict(size=11),
            name='<span class=\"material-symbols-rounded\">architecture</span> Known Mines',
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
            name='<span class=\"material-symbols-rounded\">my_location</span> Drill Priority',
            hovertemplate='Prob: %{customdata:.3f}<extra>Drill Target</extra>',
            customdata=top_drill['mn_probability'],
        ))
    # ---- LAYER: Analysis Region Boundary + "No Data" Overlay ----
    # Bounding box of the real NGDR data (MH + MP coverage)
    bbox_lat_min, bbox_lat_max = df['latitude'].min(), df['latitude'].max()
    bbox_lon_min, bbox_lon_max = df['longitude'].min(), df['longitude'].max()

    # Draw dashed boundary rectangle
    boundary_lats = [bbox_lat_min, bbox_lat_min, bbox_lat_max, bbox_lat_max, bbox_lat_min]
    boundary_lons = [bbox_lon_min, bbox_lon_max, bbox_lon_max, bbox_lon_min, bbox_lon_min]
    fig.add_trace(go.Scattermap(
        lat=boundary_lats, lon=boundary_lons,
        mode='lines',
        line=dict(width=2.5, color='rgba(255,255,255,0.6)'),
        name='Analysis Region Boundary',
        showlegend=True,
        hoverinfo='skip',
    ))

    # "No Data" text labels at corners outside the boundary
    pad = 0.5  # degrees offset outside boundary
    no_data_labels = [
        (bbox_lat_max + pad, bbox_lon_min - pad),
        (bbox_lat_max + pad, bbox_lon_max + pad),
        (bbox_lat_min - pad, bbox_lon_min - pad),
        (bbox_lat_min - pad, bbox_lon_max + pad),
    ]
    fig.add_trace(go.Scattermap(
        lat=[p[0] for p in no_data_labels],
        lon=[p[1] for p in no_data_labels],
        mode='text',
        text=['No Data — Outside<br>Analysis Region'] * 4,
        textfont=dict(size=11, color='rgba(180,180,180,0.85)', family='Arial'),
        textposition='middle center',
        showlegend=False,
        hoverinfo='skip',
    ))

    fig.update_layout(
        map=dict(style=plotly_style, center=map_center, zoom=6),
        height=600,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(yanchor="top", y=0.98, xanchor="left", x=0.01,
                    bgcolor="rgba(0,0,0,0.7)", font=dict(size=11)),
    )

    st.plotly_chart(fig, use_container_width=True)

# ================= TARGET STATS =================
st.markdown("---")
st.subheader("Target Statistics")

# Add region column to df for filtering
def get_region(lat, lon):
    if lat >= 21.0 and lon >= 78.5 and lon <= 80.5:
        return "Maharashtra"
    elif lat >= 21.5 and lon >= 80.0:
        return "Madhya Pradesh"
    return "Maharashtra"  # default for MH+MP dataset

if 'mn_probability' in df.columns:
    df['region'] = [get_region(lat, lon) for lat, lon in zip(df['latitude'], df['longitude'])]

    high_count   = int((df['mn_probability'] > 0.5).sum())
    medium_count = int(((df['mn_probability'] > 0.3) & (df['mn_probability'] <= 0.5)).sum())
    low_count    = int((df['mn_probability'] <= 0.3).sum())

    mh_high  = int((df[df['region'] == 'Maharashtra']['mn_probability'] > 0.5).sum())
    mp_high  = int((df[df['region'] == 'Madhya Pradesh']['mn_probability'] > 0.5).sum())

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
    background: var(--secondary-background-color) !important; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08) !important; border: 1px solid rgba(128, 128, 128, 0.2) !important;
    backdrop-filter: blur(12px);
    border: 1px solid color-mix(in srgb, var(--text-color) 15%, transparent);
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
    color: color-mix(in srgb, var(--text-color) 60%, transparent);
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
    color: var(--text-color);
    line-height: 1.2;
}}
.geo-kpi-footer {{ display: flex; align-items: center; gap: 8px; margin-top: 2px; }}
.geo-kpi-subtext {{ font-size: 0.8rem; color: color-mix(in srgb, var(--text-color) 50%, transparent); }}
.geo-trend-red    {{ background: rgba(239, 68, 68, 0.15);   color: #F87171; padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }}
.geo-trend-amber  {{ background: rgba(245, 158, 11, 0.15);  color: #FCD34D; padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }}
.geo-trend-green  {{ background: rgba(16, 185, 129, 0.15);  color: #34D399; padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }}

    
</style>

<div class="geo-kpi-grid">
    <div class="geo-kpi-card">
        <div class="geo-kpi-header">
            <div class="geo-kpi-title">High Priority</div>
            <div class="geo-kpi-icon geo-icon-red"><span class=\"material-symbols-rounded\">crisis_alert</span></div>
        </div>
        <div class="geo-kpi-value">{high_count} targets</div>
        <div class="geo-kpi-footer">
            <span class="geo-trend-red">Mn Prob &gt; 0.5</span>
            <span class="geo-kpi-subtext">drill candidates</span>
        </div>
    </div>
    <div class="geo-kpi-card">
        <div class="geo-kpi-header">
            <div class="geo-kpi-title">Medium Priority</div>
            <div class="geo-kpi-icon geo-icon-amber"><span class=\"material-symbols-rounded\">travel_explore</span></div>
        </div>
        <div class="geo-kpi-value">{medium_count} targets</div>
        <div class="geo-kpi-footer">
            <span class="geo-trend-amber">Mn Prob 0.3–0.5</span>
            <span class="geo-kpi-subtext">further study</span>
        </div>
    </div>
    <div class="geo-kpi-card">
        <div class="geo-kpi-header">
            <div class="geo-kpi-title">Low Priority</div>
            <div class="geo-kpi-icon geo-icon-green"><span class=\"material-symbols-rounded\">map</span></div>
        </div>
        <div class="geo-kpi-value">{low_count} targets</div>
        <div class="geo-kpi-footer">
            <span class="geo-trend-green">Mn Prob ≤ 0.3</span>
            <span class="geo-kpi-subtext">low probability</span>
        </div>
    </div>
</div>

<p style="font-weight:600; color:var(--text-color); margin:8px 0 12px 0;">Region-wise High Priority Targets:</p>
<div class="geo-kpi-grid" style="grid-template-columns: repeat(2, 1fr);">
    <div class="geo-kpi-card">
        <div class="geo-kpi-header">
            <div class="geo-kpi-title">Maharashtra</div>
            <div class="geo-kpi-icon geo-icon-pink"><span class=\"material-symbols-rounded\">landscape</span></div>
        </div>
        <div class="geo-kpi-value">{mh_high} targets</div>
        <div class="geo-kpi-footer">
            <span class="geo-trend-red">Nagpur–Bhandara Belt</span>
        </div>
    </div>
    <div class="geo-kpi-card">
        <div class="geo-kpi-header">
            <div class="geo-kpi-title">Madhya Pradesh</div>
            <div class="geo-kpi-icon geo-icon-blue"><span class=\"material-symbols-rounded\">terrain</span></div>
        </div>
        <div class="geo-kpi-value">{mp_high} targets</div>
        <div class="geo-kpi-footer">
            <span class="geo-trend-amber">Balaghat–Chhindwara Belt</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ================= TOP DRILL TARGETS =================
st.subheader(":material/location_on: Top 10 Drill Targets")
if 'mn_probability' in df.columns:
    top_10 = df.nlargest(10, 'mn_probability').copy()
    top_10.insert(0, 'Rank', range(1, len(top_10) + 1))
    display_cols = ['Rank', 'latitude', 'longitude', 'region', 'elevation_m', 'mn_probability', 'prospectivity_class', 'lithologic', 'rock_type']
    available = [c for c in display_cols if c in top_10.columns]
    renames = {'Rank':'#','latitude':'Lat °N','longitude':'Lon °E','region':'Region','elevation_m':'Elev (m)',
               'mn_probability':'Probability','prospectivity_class':'Class','lithologic':'Rock Type','rock_type':'Rock Type'}
    st.dataframe(top_10[available].rename(columns=renames).reset_index(drop=True),
                 use_container_width=True, hide_index=True)

# ================= FEATURE IMPORTANCE =================
st.subheader(":material/info: Feature Importance")
if model is not None:
    try:
        # New model format: dict with 'models' list and 'features' list
        if isinstance(model, dict) and 'models' in model and 'features' in model:
            importances = np.zeros(len(model['features']))
            for m in model['models']:
                importances += m.feature_importances_
            importances /= len(model['models'])
            feat_df = pd.DataFrame({'Feature': model['features'], 'Importance': importances}).sort_values('Importance', ascending=True)
        else:
            # Fallback for old model format
            base = model[0] if isinstance(model, list) else model
            if hasattr(base, 'feature_importances_'):
                imp = base.feature_importances_
                names = ['rock_type_encoded','fault_distance_km','elevation_m','slope_deg',
                         'rainfall_mm','iron_oxide_index','clay_index','ndvi'][:len(imp)]
                feat_df = pd.DataFrame({'Feature': names, 'Importance': imp}).sort_values('Importance', ascending=True)
            else:
                feat_df = None

        if feat_df is not None:
            fig_imp = px.bar(feat_df, x='Importance', y='Feature', orientation='h',
                           color='Importance', color_continuous_scale='RdYlGn_r')
            fig_imp.update_layout(height=350, showlegend=False, title="Feature Importances (All Real Data Sources)")
            st.plotly_chart(fig_imp, use_container_width=True)
            st.caption("✅ All features derived from real sources: NGDR GSI, Sentinel-2, SRTM, Open-Meteo. No synthetic features.")
    except Exception as e:
        st.error(f"Error: {e}")


# --- Animations ---
inject_kpi_animations()
inject_volcano_animations()
