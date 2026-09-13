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

st.set_page_config(layout="wide") if not st.get_option("layout") == "wide" else None

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
st.markdown("Interactive AI-predicted satellite map for the Nagpur-Bhandara-Balaghat belt.")

df = load_data()
model = load_model()

if df.empty:
    st.warning("No data found. Run the pipeline first.")
    st.stop()

# ================= 2-COLUMN LAYOUT (LIKE MOCKUP) =================
col_map, col_controls = st.columns([3, 1], gap="large")

with col_controls:
    st.markdown("### Layer Control")
    st.markdown('<div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px;">', unsafe_allow_html=True)
    
    show_heatmap = st.checkbox("🔥 Prospectivity Heatmap", value=True)
    show_geo = st.checkbox("🌍 Geological Layers (NDVI)", value=True)
    show_mines = st.checkbox("⛏️ Known Mines", value=True)
    show_drill = st.checkbox("🎯 Drilling Priority Zones", value=False)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Legend")
    st.markdown("""
    <div style="background: linear-gradient(to top, blue, cyan, lime, yellow, red); 
                height: 150px; width: 30px; border-radius: 5px; float: left; margin-right: 15px;"></div>
    <div style="height: 150px; display: flex; flex-direction: column; justify-content: space-between;">
        <b>High</b>
        <b>Medium</b>
        <b>Low</b>
    </div>
    <div style="clear: both;"></div>
    """, unsafe_allow_html=True)

with col_map:
    # Build folium map with ESRI Satellite Tiles
    m = folium.Map(
        location=[21.25, 79.25], 
        zoom_start=10, 
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri Satellite'
    )

    # 1. Prospectivity Heatmap
    if show_heatmap and 'mn_probability' in df.columns:
        heat_data = df[['latitude', 'longitude', 'mn_probability']].values.tolist()
        HeatMap(
            heat_data,
            name='Mn Prospectivity',
            min_opacity=0.3,
            max_val=1.0,
            radius=18,
            blur=12,
            max_zoom=15,
            gradient={0.0: 'blue', 0.25: 'cyan', 0.5: 'lime', 0.75: 'yellow', 1.0: 'red'}
        ).add_to(m)

    # 2. Geological Layers (NDVI for now, since it shows surface features)
    if show_geo and 'ndvi' in df.columns:
        ndvi_data = df[['latitude', 'longitude', 'ndvi']].values.tolist()
        HeatMap(
            ndvi_data,
            name='NDVI Vegetation',
            min_opacity=0.1,
            radius=15,
            blur=10,
            gradient={0.0: 'rgba(0,0,0,0)', 0.5: 'rgba(173,255,47,0.4)', 1.0: 'rgba(0,100,0,0.7)'}
        ).add_to(m)

    # 3. Known Mines
    if show_mines:
        mines = [
            {"name": "Dongri Buzurg Mine", "lat": 21.38, "lon": 79.35},
            {"name": "Chikla Mine", "lat": 21.22, "lon": 79.42},
            {"name": "Munsar Mine", "lat": 21.15, "lon": 79.55},
        ]
        for mine in mines:
            folium.Marker(
                [mine['lat'], mine['lon']],
                popup=mine['name'],
                tooltip=mine['name'],
                icon=folium.Icon(color='lightgray', icon='industry', prefix='fa'),
            ).add_to(m)

    # 4. Drilling Priority Zones
    if show_drill and 'mn_probability' in df.columns:
        high_df = df[df['mn_probability'] > 0.8].nlargest(20, 'mn_probability')
        for _, row in high_df.iterrows():
            folium.CircleMarker(
                [row['latitude'], row['longitude']],
                radius=8,
                color='white',
                weight=2,
                fill=True,
                fill_color='red',
                fill_opacity=1.0,
                popup=f"Prob: {row['mn_probability']:.3f}",
                tooltip=f"🎯 Target ({row['mn_probability']:.3f})",
            ).add_to(m)

    # Render map
    st_folium(m, use_container_width=True, height=550, returned_objects=[])


# ================= DRILL TARGET SUMMARY =================
st.markdown("---")
st.subheader("Target Statistics")
c1, c2, c3 = st.columns(3)
if 'mn_probability' in df.columns:
    c1.metric("🔴 High Priority", f"{int((df['mn_probability'] > 0.8).sum())} targets")
    c2.metric("🟡 Medium Priority", f"{int(((df['mn_probability'] > 0.4) & (df['mn_probability'] <= 0.8)).sum())} targets")
    c3.metric("🟢 Low Priority", f"{int((df['mn_probability'] <= 0.4).sum())} targets")


# ================= LOCATION INSPECTOR =================
st.subheader("📍 Top 10 Drill Targets")
if 'mn_probability' in df.columns:
    top_10 = df.nlargest(10, 'mn_probability').copy()
    top_10.insert(0, 'Rank', range(1, len(top_10) + 1))
    
    display_cols = ['Rank', 'latitude', 'longitude', 'elevation_m', 'mn_probability', 'prospectivity_class', 'rock_type']
    renames = {
        'Rank': '#', 'latitude': 'Lat °N', 'longitude': 'Lon °E', 'elevation_m': 'Elev (m)',
        'mn_probability': 'Probability', 'prospectivity_class': 'Class', 'rock_type': 'Rock Type'
    }
    
    # Filter only available columns
    available_cols = [c for c in display_cols if c in top_10.columns]
    
    st.dataframe(
        top_10[available_cols].rename(columns=renames).reset_index(drop=True),
        use_container_width=True, 
        hide_index=True
    )

# ================= FEATURE IMPORTANCE =================
st.subheader("🔬 Feature Importance")
if model is not None:
    try:
        base = model[0] if isinstance(model, list) else model
        if hasattr(base, 'feature_importances_'):
            imp = base.feature_importances_
            names = ['iron_oxide_index','clay_index','ndvi','rock_type','fault_distance_km',
                     'shear_zone_proximity_km','elevation_m','slope_deg','rainfall_mm','soil_moisture']
            names = names[:len(imp)]
            feat_df = pd.DataFrame({'Feature': names, 'Importance': imp}).sort_values('Importance', ascending=True)
            fig_imp = px.bar(feat_df, x='Importance', y='Feature', orientation='h',
                           color='Importance', color_continuous_scale='RdYlGn_r')
            fig_imp.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig_imp, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")
