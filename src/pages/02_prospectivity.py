import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
import joblib
import os
import numpy as np

# Define paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
MODEL_DIR = os.path.join(PROJECT_ROOT, 'models')

@st.cache_data
def load_data():
    try:
        df = pd.read_csv(os.path.join(DATA_DIR, 'prospectivity_grid.csv'))
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

@st.cache_resource
def load_model():
    try:
        model = joblib.load(os.path.join(MODEL_DIR, 'prospectivity_pu_rf.joblib'))
        return model
    except Exception as e:
        st.error(f"Error loading model: {e}")
        return None

# Main execution
st.title('🎯 GeoProspect AI - Prospectivity Analysis')
st.markdown("Analyze multi-spectral indicators and AI-predicted manganese prospectivity.")

df = load_data()
model = load_model()

if df.empty:
    st.stop()

# ================= SIDEBAR =================
st.sidebar.header('Visualization Controls')

layer_selection = st.sidebar.radio(
    'Spectral Layer',
    ['Composite Prospectivity (OPI)', 'NDVI Canopy Mask', 'Ferrous Iron Index', 'Clay Alteration Index', 'True Color (RGB)']
)

view_mode = st.sidebar.radio('Map View', ['2D Scatter', '3D Columns', 'Heatmap'])

st.sidebar.markdown('---')
st.sidebar.header('Filters')

prob_threshold = st.sidebar.slider('Probability Threshold', 0.0, 1.0, 0.0, 0.05)

if 'prospectivity_class' in df.columns:
    available_classes = sorted(df['prospectivity_class'].dropna().unique().tolist())
else:
    available_classes = []
selected_classes = st.sidebar.multiselect('Prospectivity Class', available_classes, default=available_classes)

show_veg = st.sidebar.checkbox('Show Vegetation Masked Areas', value=True)

opacity = st.sidebar.slider('Layer Opacity', 0.1, 1.0, 0.8, 0.1)

# ================= FILTER DATA =================
filtered_df = df.copy()

if 'mn_probability' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['mn_probability'] >= prob_threshold]

if selected_classes and 'prospectivity_class' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['prospectivity_class'].isin(selected_classes)]

if not show_veg and 'vegetation_masked' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['vegetation_masked'] == 0]

# ================= METRICS =================
st.subheader("Drill Target Summary")
col1, col2, col3 = st.columns(3)

if 'mn_probability' in df.columns:
    high_pri = df[df['mn_probability'] > 0.8].shape[0]
    med_pri = df[(df['mn_probability'] > 0.4) & (df['mn_probability'] <= 0.8)].shape[0]
    low_pri = df[df['mn_probability'] <= 0.4].shape[0]
else:
    high_pri, med_pri, low_pri = 0, 0, 0

col1.metric("🔴 High Priority Targets", high_pri)
col2.metric("🟡 Medium Priority Targets", med_pri)
col3.metric("🟢 Low Priority Targets", low_pri)

# ================= MAP CONFIGURATION =================
# We need base columns to handle coloring safely
if 'mn_probability' not in filtered_df.columns:
    filtered_df['mn_probability'] = 0.5
if 'ndvi' not in filtered_df.columns:
    filtered_df['ndvi'] = 0.5
if 'iron_oxide_index' not in filtered_df.columns:
    filtered_df['iron_oxide_index'] = 0.5
if 'clay_index' not in filtered_df.columns:
    filtered_df['clay_index'] = 0.5
if 'elevation_m' not in filtered_df.columns:
    filtered_df['elevation_m'] = 300

# Set up coloring based on selected layer
if layer_selection == 'Composite Prospectivity (OPI)':
    st.caption("**Layer:** AI-Predicted Manganese Probability")
    # Red for high, yellow for med, green for low
    filtered_df['color_r'] = (filtered_df['mn_probability'] * 255).astype(int)
    filtered_df['color_g'] = ((1 - filtered_df['mn_probability']) * 255).astype(int)
    filtered_df['color_b'] = 0
    metric_col = 'mn_probability'
    elevation_factor = 5000

elif layer_selection == 'NDVI Canopy Mask':
    st.caption("**Layer:** NDVI Canopy Mask `(B08 - B04) / (B08 + B04)`")
    # Green scale
    filtered_df['color_r'] = 0
    ndvi_min, ndvi_max = filtered_df['ndvi'].min(), filtered_df['ndvi'].max()
    ndvi_norm = (filtered_df['ndvi'] - ndvi_min) / (ndvi_max - ndvi_min + 1e-5)
    filtered_df['color_g'] = (ndvi_norm * 255).astype(int)
    filtered_df['color_b'] = 0
    metric_col = 'ndvi'
    elevation_factor = 5000

elif layer_selection == 'Ferrous Iron Index':
    st.caption("**Layer:** Ferrous Iron Index `B04 / B02 — Gossan halo indicator`")
    # Orange/Red scale
    fe_min, fe_max = filtered_df['iron_oxide_index'].min(), filtered_df['iron_oxide_index'].max()
    fe_norm = (filtered_df['iron_oxide_index'] - fe_min) / (fe_max - fe_min + 1e-5)
    filtered_df['color_r'] = 255
    filtered_df['color_g'] = ((1 - fe_norm) * 165).astype(int) # Orange is 255,165,0
    filtered_df['color_b'] = 0
    metric_col = 'iron_oxide_index'
    elevation_factor = 5000

elif layer_selection == 'Clay Alteration Index':
    st.caption("**Layer:** Clay Alteration Index `B11 / B12 — Argillic zone indicator`")
    # Purple/Blue scale
    clay_min, clay_max = filtered_df['clay_index'].min(), filtered_df['clay_index'].max()
    clay_norm = (filtered_df['clay_index'] - clay_min) / (clay_max - clay_min + 1e-5)
    filtered_df['color_r'] = ((clay_norm) * 128).astype(int) # Purple/Blue
    filtered_df['color_g'] = 0
    filtered_df['color_b'] = 255
    metric_col = 'clay_index'
    elevation_factor = 5000

else: # True Color
    st.caption("**Layer:** True Color equivalent (B04/B08/B02 proxy)")
    # Fallbacks in case bands aren't there
    for b in ['B04', 'B08', 'B02']:
        if b not in filtered_df.columns:
            filtered_df[b] = 0.5
    
    b4_norm = (filtered_df['B04'] - filtered_df['B04'].min()) / (filtered_df['B04'].max() - filtered_df['B04'].min() + 1e-5)
    b8_norm = (filtered_df['B08'] - filtered_df['B08'].min()) / (filtered_df['B08'].max() - filtered_df['B08'].min() + 1e-5)
    b2_norm = (filtered_df['B02'] - filtered_df['B02'].min()) / (filtered_df['B02'].max() - filtered_df['B02'].min() + 1e-5)
    filtered_df['color_r'] = (b4_norm * 255).astype(int)
    filtered_df['color_g'] = (b8_norm * 255).astype(int)
    filtered_df['color_b'] = (b2_norm * 255).astype(int)
    metric_col = 'elevation_m'
    elevation_factor = 10

# Clip colors to 0-255 just in case
for c in ['color_r', 'color_g', 'color_b']:
    filtered_df[c] = filtered_df[c].clip(0, 255)

# Handle color lists for PyDeck
filtered_df['fill_color'] = filtered_df[['color_r', 'color_g', 'color_b']].values.tolist()
# Add opacity
filtered_df['fill_color'] = filtered_df['fill_color'].apply(lambda x: x + [int(opacity * 255)])

filtered_df['elevation_viz'] = filtered_df[metric_col] * elevation_factor

# Build PyDeck layer
layers = []
if view_mode == '2D Scatter':
    layers.append(pdk.Layer(
        "ScatterplotLayer",
        data=filtered_df,
        get_position=["longitude", "latitude"],
        get_fill_color="fill_color",
        get_radius=250,
        pickable=True,
        opacity=1.0, # opacity handled in color
        auto_highlight=True,
    ))
    pitch = 0
elif view_mode == '3D Columns':
    layers.append(pdk.Layer(
        "ColumnLayer",
        data=filtered_df,
        get_position=["longitude", "latitude"],
        get_elevation="elevation_viz",
        elevation_scale=1,
        radius=250,
        get_fill_color="fill_color",
        pickable=True,
        auto_highlight=True,
        extruded=True,
    ))
    pitch = 60
else: # Heatmap
    layers.append(pdk.Layer(
        "HeatmapLayer",
        data=filtered_df,
        get_position=["longitude", "latitude"],
        get_weight=metric_col,
        opacity=opacity,
        pickable=False,
    ))
    pitch = 0

view_state = pdk.ViewState(
    latitude=21.25,
    longitude=79.25,
    zoom=10,
    pitch=pitch,
)

r = pdk.Deck(
    layers=layers,
    initial_view_state=view_state,
    tooltip={"text": f"Lat: {{latitude}}\nLon: {{longitude}}\n{metric_col}: {{{metric_col}}}"}
)

st.pydeck_chart(r, use_container_width=True)

# ================= TOP TARGETS =================
st.subheader("Top 10 Highest Probability Locations")
if 'mn_probability' in df.columns:
    top_10 = df.nlargest(10, 'mn_probability')
    display_cols = ['latitude', 'longitude', 'elevation_m', 'mn_probability', 'prospectivity_class', 'rock_type', 'ndvi', 'iron_oxide_index', 'clay_index']
    # Filter only existing columns
    display_cols = [c for c in display_cols if c in top_10.columns]
    st.dataframe(top_10[display_cols].reset_index(drop=True), use_container_width=True)
else:
    st.info("Probability data not available.")

# ================= FEATURE IMPORTANCE =================
st.subheader("Feature Importance")
if model is not None:
    try:
        # Check if list of models (e.g. bagged/ensemble from PU learning)
        if isinstance(model, list) and len(model) > 0:
            base_model = model[0]
        else:
            base_model = model
            
        if hasattr(base_model, 'feature_importances_'):
            importances = base_model.feature_importances_
            feature_names = ['iron_oxide_index', 'clay_index', 'ndvi', 'rock_type_encoded', 'fault_distance_km', 'shear_zone_proximity_km', 'elevation_m', 'slope_deg', 'rainfall_mm', 'soil_moisture']
            
            # Pad or truncate feature names if mismatch
            if len(importances) != len(feature_names):
                if len(importances) > len(feature_names):
                    feature_names += [f"feature_{i}" for i in range(len(feature_names), len(importances))]
                else:
                    feature_names = feature_names[:len(importances)]
                    
            feat_df = pd.DataFrame({
                'Feature': feature_names,
                'Importance': importances
            }).sort_values('Importance', ascending=True)
            
            fig = px.bar(feat_df, x='Importance', y='Feature', orientation='h', title='Random Forest Feature Importances')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Loaded model does not have feature_importances_ attribute.")
    except Exception as e:
        st.error(f"Could not extract feature importances: {e}")
else:
    st.info("Model not available for feature importance.")
