import streamlit as st
import pandas as pd
import plotly.express as px
import joblib
import os
import numpy as np
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

st.title('🎯 GeoProspect AI - Manganese Prospectivity Map')

df = load_data()
model = load_model()

if df.empty:
    st.warning("No data found. Run the pipeline first.")
    st.stop()

# ================= SIDEBAR — LAYER CONTROL =================
st.sidebar.header("Layer Control")

show_heatmap = st.sidebar.checkbox("🔥 Prospectivity Heatmap", value=True)
show_ndvi = st.sidebar.checkbox("🌿 Vegetation (NDVI)", value=False)
show_iron = st.sidebar.checkbox("🟠 Ferrous Iron Index", value=False)
show_clay = st.sidebar.checkbox("🟣 Clay Alteration", value=False)
show_mines = st.sidebar.checkbox("⛏️ Known Mines", value=True)
show_drill = st.sidebar.checkbox("🎯 Drilling Priority Zones", value=False)

st.sidebar.markdown("---")
st.sidebar.header("Heatmap Settings")
heatmap_radius = st.sidebar.slider("Radius", 8, 30, 15)
heatmap_blur = st.sidebar.slider("Blur", 5, 25, 12)
heatmap_opacity = st.sidebar.slider("Max Opacity", 0.3, 1.0, 0.7, 0.1)

st.sidebar.markdown("---")
st.sidebar.caption("🔴 High  🟡 Medium  🔵 Low")

# ================= DRILL TARGET SUMMARY =================
c1, c2, c3 = st.columns(3)
if 'mn_probability' in df.columns:
    c1.metric("🔴 High Priority", f"{int((df['mn_probability'] > 0.8).sum())} targets")
    c2.metric("🟡 Medium Priority", f"{int(((df['mn_probability'] > 0.4) & (df['mn_probability'] <= 0.8)).sum())} targets")
    c3.metric("🟢 Low Priority", f"{int((df['mn_probability'] <= 0.4).sum())} targets")

# ================= BUILD FOLIUM MAP =================
# Satellite tiles from ESRI
satellite_tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
satellite_attr = "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, AEX, GeoEye, Getmapping, Aerogrid"

m = folium.Map(
    location=[21.25, 79.25],
    zoom_start=11,
    tiles=satellite_tiles,
    attr=satellite_attr,
    control_scale=True,
)

# Also add OpenStreetMap as an alternative tile layer
folium.TileLayer('openstreetmap', name='Street Map').add_to(m)
folium.TileLayer('cartodbdark_matter', name='Dark Map').add_to(m)

# ---- PROSPECTIVITY HEATMAP OVERLAY ----
if show_heatmap and 'mn_probability' in df.columns:
    heat_data = df[['latitude', 'longitude', 'mn_probability']].values.tolist()
    
    heatmap_layer = HeatMap(
        heat_data,
        name='Mn Prospectivity',
        min_opacity=0.3,
        max_val=1.0,
        radius=heatmap_radius,
        blur=heatmap_blur,
        max_zoom=18,
        gradient={
            '0.0': 'blue',
            '0.2': 'cyan',
            '0.4': 'lime',
            '0.6': 'yellow',
            '0.8': 'orange',
            '1.0': 'red',
        },
    )
    heatmap_layer.add_to(m)

# ---- NDVI VEGETATION OVERLAY ----
if show_ndvi and 'ndvi' in df.columns:
    ndvi_data = df[['latitude', 'longitude', 'ndvi']].values.tolist()
    HeatMap(
        ndvi_data,
        name='NDVI Vegetation',
        min_opacity=0.2,
        radius=heatmap_radius,
        blur=heatmap_blur,
        gradient={'0.0': '#8B5A2B', '0.3': '#B8B432', '0.6': '#32CD32', '1.0': '#006400'},
    ).add_to(m)

# ---- IRON OXIDE OVERLAY ----
if show_iron and 'iron_oxide_index' in df.columns:
    fe = df['iron_oxide_index']
    fe_norm = ((fe - fe.min()) / (fe.max() - fe.min() + 1e-10)).values
    iron_data = [[r['latitude'], r['longitude'], fe_norm[i]] for i, (_, r) in enumerate(df.iterrows())]
    HeatMap(
        iron_data,
        name='Iron Oxide',
        min_opacity=0.2,
        radius=heatmap_radius,
        blur=heatmap_blur,
        gradient={'0.0': '#FFFFC0', '0.3': '#FFC832', '0.6': '#FF6400', '1.0': '#8B0000'},
    ).add_to(m)

# ---- CLAY ALTERATION OVERLAY ----
if show_clay and 'clay_index' in df.columns:
    cl = df['clay_index']
    cl_norm = ((cl - cl.min()) / (cl.max() - cl.min() + 1e-10)).values
    clay_data = [[r['latitude'], r['longitude'], cl_norm[i]] for i, (_, r) in enumerate(df.iterrows())]
    HeatMap(
        clay_data,
        name='Clay Alteration',
        min_opacity=0.2,
        radius=heatmap_radius,
        blur=heatmap_blur,
        gradient={'0.0': '#C8DCFF', '0.4': '#6464FF', '0.7': '#9632C8', '1.0': '#640064'},
    ).add_to(m)

# ---- KNOWN MINES MARKERS ----
if show_mines:
    mines = [
        {"name": "Dongri Buzurg", "lat": 21.38, "lon": 79.35, "type": "Active"},
        {"name": "Chikla Mine", "lat": 21.22, "lon": 79.42, "type": "Active"},
        {"name": "Munsar Mine", "lat": 21.15, "lon": 79.55, "type": "Active"},
    ]
    mine_group = folium.FeatureGroup(name='⛏️ Known Mines')
    for mine in mines:
        folium.Marker(
            [mine['lat'], mine['lon']],
            popup=f"<b>{mine['name']}</b><br>Type: {mine['type']}",
            tooltip=mine['name'],
            icon=folium.Icon(color='red', icon='industry', prefix='fa'),
        ).add_to(mine_group)
    mine_group.add_to(m)

# ---- DRILLING PRIORITY ZONES ----
if show_drill and 'mn_probability' in df.columns:
    drill_group = folium.FeatureGroup(name='🎯 Drill Priority')
    high_df = df[df['mn_probability'] > 0.8].nlargest(20, 'mn_probability')
    for _, row in high_df.iterrows():
        folium.CircleMarker(
            [row['latitude'], row['longitude']],
            radius=6,
            color='red',
            fill=True,
            fill_color='red',
            fill_opacity=0.8,
            popup=f"Prob: {row['mn_probability']:.3f}",
            tooltip=f"🎯 {row['mn_probability']:.3f}",
        ).add_to(drill_group)
    drill_group.add_to(m)

# Layer control toggle
folium.LayerControl(collapsed=False).add_to(m)

# Render map
st_folium(m, use_container_width=True, height=600)

# ================= LOCATION INSPECTOR =================
st.subheader("📍 Top 10 Drill Targets")
if 'mn_probability' in df.columns:
    top_10 = df.nlargest(10, 'mn_probability').copy()
    top_10.insert(0, 'Rank', range(1, len(top_10) + 1))
    cols, renames = ['Rank'], {'Rank': '#'}
    for c, n in [('latitude','Lat °N'),('longitude','Lon °E'),('elevation_m','Elev (m)'),
                  ('mn_probability','Probability'),('prospectivity_class','Class'),
                  ('rock_type','Rock Type')]:
        if c in top_10.columns:
            cols.append(c)
            renames[c] = n
    st.dataframe(top_10[cols].rename(columns=renames).reset_index(drop=True),
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
