import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import joblib
import os
import numpy as np

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
st.markdown("Interactive map with AI-predicted overlays for the Nagpur-Bhandara-Balaghat Manganese Belt")

df = load_data()
model = load_model()

if df.empty:
    st.warning("No data found. Run the pipeline first.")
    st.stop()

# ================= SIDEBAR =================
st.sidebar.header("🗺️ Map Settings")
map_style = st.sidebar.selectbox("Map Style", [
    "carto-darkmatter", "carto-positron", "open-street-map"
], index=0)

st.sidebar.markdown("---")
st.sidebar.header("📡 Overlay Layers")

overlay_choice = st.sidebar.radio("Active Overlay", [
    "🔴 Manganese Prospectivity",
    "🌿 NDVI Vegetation",
    "🟠 Ferrous Iron Index",
    "🟣 Clay Alteration Index",
    "None (Map Only)",
])

st.sidebar.markdown("---")
overlay_radius = st.sidebar.slider("Overlay Spread", 5, 40, 15, help="Bigger = smoother overlay")
overlay_opacity = st.sidebar.slider("Overlay Opacity", 0.1, 1.0, 0.7, 0.1)

# ================= DRILL TARGET SUMMARY =================
st.subheader("Drill Target Summary")
c1, c2, c3 = st.columns(3)
if 'mn_probability' in df.columns:
    c1.metric("🔴 High Priority", f"{int((df['mn_probability'] > 0.8).sum())} targets")
    c2.metric("🟡 Medium Priority", f"{int(((df['mn_probability'] > 0.4) & (df['mn_probability'] <= 0.8)).sum())} targets")
    c3.metric("🟢 Low Priority", f"{int((df['mn_probability'] <= 0.4).sum())} targets")

# ================= DETERMINE OVERLAY =================
if "Manganese" in overlay_choice:
    z_col = 'mn_probability'
    color_scale = [[0, 'blue'], [0.3, 'cyan'], [0.5, 'green'], [0.7, 'yellow'], [0.85, 'orange'], [1.0, 'red']]
    label = "Mn Probability"
elif "NDVI" in overlay_choice:
    z_col = 'ndvi'
    color_scale = [[0, 'brown'], [0.3, 'yellow'], [0.6, 'lightgreen'], [1.0, 'darkgreen']]
    label = "NDVI"
elif "Iron" in overlay_choice:
    z_col = 'iron_oxide_index'
    color_scale = [[0, 'lightyellow'], [0.4, 'orange'], [0.7, 'red'], [1.0, 'darkred']]
    label = "Fe Index"
elif "Clay" in overlay_choice:
    z_col = 'clay_index'
    color_scale = [[0, 'lightblue'], [0.4, 'blue'], [0.7, 'purple'], [1.0, 'darkviolet']]
    label = "Clay Index"
else:
    z_col = None

# ================= BUILD MAP =================
if z_col and z_col in df.columns:
    # Use histfunc="avg" so zoom-out doesn't sum up all values and turn everything red!
    fig = px.density_map(
        df, lat='latitude', lon='longitude', z=z_col,
        radius=overlay_radius,
        opacity=overlay_opacity,
        color_continuous_scale=color_scale,
        range_color=[0, 1] if z_col == 'mn_probability' else None,
        center=dict(lat=21.25, lon=79.25),
        zoom=10,
        labels={z_col: label},
        histfunc="avg"  # <--- THIS FIXES THE ZOOM OUT RED BLOB ISSUE
    )
    fig.update_layout(map_style=map_style)
else:
    fig = go.Figure(go.Scattermap(
        lat=[21.25], lon=[79.25], mode='markers',
        marker=dict(size=1, opacity=0), showlegend=False,
    ))
    fig.update_layout(map=dict(style=map_style, center=dict(lat=21.25, lon=79.25), zoom=10))

fig.update_layout(
    height=650,
    margin=dict(l=0, r=0, t=30, b=0),
    title=dict(text="Nagpur-Bhandara-Balaghat Manganese Belt", font=dict(size=14)),
)

st.plotly_chart(fig, use_container_width=True)

# ================= LOCATION INSPECTOR =================
st.subheader("📍 Top 10 Drill Targets")
if 'mn_probability' in df.columns:
    top_10 = df.nlargest(10, 'mn_probability').copy()
    top_10.insert(0, 'Rank', range(1, len(top_10) + 1))
    cols = ['Rank']
    renames = {'Rank': '#'}
    for c, n in [('latitude','Lat °N'),('longitude','Lon °E'),('elevation_m','Elev (m)'),
                  ('mn_probability','Probability'),('prospectivity_class','Class'),
                  ('rock_type','Rock Type'),('ndvi','NDVI'),('iron_oxide_index','Fe Index'),
                  ('clay_index','Clay Index')]:
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
