import streamlit as st
import pandas as pd
import plotly.express as px
import joblib
import os
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

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

st.title('Manganese Prospectivity Map')
st.markdown("Interactive AI-predicted map • Nagpur-Bhandara-Balaghat Manganese Belt")

df = load_data()
model = load_model()

if df.empty:
    st.warning("No data found. Run the pipeline first.")
    st.stop()

# ================= LAYOUT: MAP (left) + CONTROLS (right) =================
col_map, col_ctrl = st.columns([3, 1], gap="large")

with col_ctrl:
    st.markdown("### Layer Control")
    show_heatmap = st.checkbox("🔥 Prospectivity Heatmap", value=True)
    show_ndvi = st.checkbox("🌿 Geological Layers (NDVI)", value=False)
    show_mines = st.checkbox("⛏️ Known Mines", value=True)
    show_drill = st.checkbox("🎯 Drilling Priority Zones", value=False)

    st.markdown("---")
    st.markdown("### Map Style")
    map_choice = st.radio("Select", [
        "🌑 Dark", "⬜ Light", "🗺️ Street", "🛰️ Satellite"
    ], index=0, label_visibility="collapsed")

    st.markdown("---")
    st.markdown("### Legend")
    st.markdown("""
    <div style="display:flex; align-items:center; gap:8px;">
        <div style="background:linear-gradient(to right, blue, cyan, lime, yellow, red); 
                    height:14px; width:120px; border-radius:3px;"></div>
    </div>
    <div style="display:flex; justify-content:space-between; width:120px; font-size:12px;">
        <span>Low</span><span>Med</span><span>High</span>
    </div>
    """, unsafe_allow_html=True)

with col_map:
    # ---- BASE MAP ----
    m = folium.Map(
        location=[21.25, 79.25],
        zoom_start=10,
        tiles=None,
        max_bounds=True,
    )

    # Add all tile layers — user switches via Layer Control on map OR radio button
    if "Dark" in map_choice:
        folium.TileLayer(
            tiles='https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
            attr='Esri Dark Gray', name='Dark', no_wrap=True
        ).add_to(m)
    elif "Light" in map_choice:
        folium.TileLayer(
            tiles='https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
            attr='Esri Light Gray', name='Light', no_wrap=True
        ).add_to(m)
    elif "Street" in map_choice:
        folium.TileLayer('openstreetmap', name='Street', no_wrap=True).add_to(m)
    elif "Satellite" in map_choice:
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri Satellite', name='Satellite', no_wrap=True
        ).add_to(m)

    # ---- OVERLAY 1: Prospectivity Heatmap ----
    if show_heatmap and 'mn_probability' in df.columns:
        hotspots = df[df['mn_probability'] > 0.25]
        heat_data = hotspots[['latitude', 'longitude', 'mn_probability']].values.tolist()
        HeatMap(
            heat_data, name='Mn Prospectivity',
            min_opacity=0.25, max_val=1.0,
            radius=20, blur=15, max_zoom=15,
            gradient={0.0: 'blue', 0.2: 'cyan', 0.4: 'lime', 0.6: 'yellow', 0.8: 'orange', 1.0: 'red'}
        ).add_to(m)

    # ---- OVERLAY 2: NDVI / Geological ----
    if show_ndvi and 'ndvi' in df.columns:
        veg = df[df['ndvi'] > 0.3]
        ndvi_data = veg[['latitude', 'longitude', 'ndvi']].values.tolist()
        HeatMap(
            ndvi_data, name='NDVI Vegetation',
            min_opacity=0.15, radius=15, blur=10,
            gradient={0.0: 'rgba(0,0,0,0)', 0.4: 'rgba(173,255,47,0.4)', 1.0: 'rgba(0,100,0,0.7)'}
        ).add_to(m)

    # ---- OVERLAY 3: Known Mines ----
    if show_mines:
        mines = [
            {"name": "Dongri Buzurg Mine", "lat": 21.38, "lon": 79.35},
            {"name": "Chikla Mine", "lat": 21.22, "lon": 79.42},
            {"name": "Munsar Mine", "lat": 21.15, "lon": 79.55},
        ]
        for mine in mines:
            folium.Marker(
                [mine['lat'], mine['lon']],
                popup=mine['name'], tooltip=mine['name'],
                icon=folium.Icon(color='red', icon='industry', prefix='fa'),
            ).add_to(m)

    # ---- OVERLAY 4: Drilling Priority Zones ----
    if show_drill and 'mn_probability' in df.columns:
        top_drill = df[df['mn_probability'] > 0.8].nlargest(20, 'mn_probability')
        for _, row in top_drill.iterrows():
            folium.CircleMarker(
                [row['latitude'], row['longitude']],
                radius=7, color='white', weight=2,
                fill=True, fill_color='red', fill_opacity=0.9,
                popup=f"Prob: {row['mn_probability']:.3f}",
                tooltip=f"🎯 {row['mn_probability']:.3f}",
            ).add_to(m)

    st_folium(m, use_container_width=True, height=550, returned_objects=[])

# ================= TARGET STATS =================
st.markdown("---")
st.subheader("Target Statistics")
c1, c2, c3 = st.columns(3)
if 'mn_probability' in df.columns:
    c1.metric("🔴 High Priority", f"{int((df['mn_probability'] > 0.8).sum())} targets")
    c2.metric("🟡 Medium Priority", f"{int(((df['mn_probability'] > 0.4) & (df['mn_probability'] <= 0.8)).sum())} targets")
    c3.metric("🟢 Low Priority", f"{int((df['mn_probability'] <= 0.4).sum())} targets")

# ================= TOP DRILL TARGETS =================
st.subheader("📍 Top 10 Drill Targets")
if 'mn_probability' in df.columns:
    top_10 = df.nlargest(10, 'mn_probability').copy()
    top_10.insert(0, 'Rank', range(1, len(top_10) + 1))
    display_cols = ['Rank', 'latitude', 'longitude', 'elevation_m', 'mn_probability', 'prospectivity_class', 'rock_type']
    available = [c for c in display_cols if c in top_10.columns]
    renames = {'Rank':'#','latitude':'Lat °N','longitude':'Lon °E','elevation_m':'Elev (m)',
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
                     'shear_zone_proximity_km','elevation_m','slope_deg','rainfall_mm','soil_moisture'][:len(imp)]
            feat_df = pd.DataFrame({'Feature': names, 'Importance': imp}).sort_values('Importance', ascending=True)
            fig_imp = px.bar(feat_df, x='Importance', y='Feature', orientation='h',
                           color='Importance', color_continuous_scale='RdYlGn_r')
            fig_imp.update_layout(height=350, showlegend=False, title="Feature Importances")
            st.plotly_chart(fig_imp, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")
