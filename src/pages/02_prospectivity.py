import streamlit as st
import pandas as pd
import numpy as np
import os
import pydeck as pdk
import joblib

st.title("GeoProspect AI - Manganese Prospectivity Map")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
MODEL_DIR = os.path.join(PROJECT_ROOT, 'models')

@st.cache_data
def load_prospectivity_data():
    prospectivity_path = os.path.join(DATA_DIR, 'prospectivity_grid.csv')
    if os.path.exists(prospectivity_path):
        return pd.read_csv(prospectivity_path)
    return pd.DataFrame()

@st.cache_resource
def load_model():
    model_path = os.path.join(MODEL_DIR, 'prospectivity_pu_rf.joblib')
    if os.path.exists(model_path):
        return joblib.load(model_path)
    return None

df = load_prospectivity_data()

if df.empty or 'mn_probability' not in df.columns:
    st.warning("Data missing or mn_probability column not found. Please run train_prospectivity.py first to generate the necessary data.")
else:
    st.sidebar.header("Controls")
    prob_threshold = st.sidebar.slider("Probability Threshold", 0.0, 1.0, 0.4)
    
    classes = df['prospectivity_class'].unique().tolist() if 'prospectivity_class' in df.columns else ['High', 'Medium', 'Low']
    selected_classes = st.sidebar.multiselect("Prospectivity Class", classes, default=classes)
    
    show_veg = st.sidebar.checkbox("Show Vegetation Mask", value=False)
    
    filtered_df = df[df['mn_probability'] >= prob_threshold]
    if 'prospectivity_class' in df.columns:
        filtered_df = filtered_df[filtered_df['prospectivity_class'].isin(selected_classes)]
    
    def get_color(val):
        if val > 0.8: return [220, 50, 50]
        elif val > 0.4: return [255, 200, 50]
        else: return [50, 180, 80]
    
    filtered_df['color'] = filtered_df['mn_probability'].apply(get_color)
    filtered_df['radius'] = filtered_df['mn_probability'] * 500
    
    layers = [
        pdk.Layer(
            "ScatterplotLayer",
            data=filtered_df,
            get_position='[longitude, latitude]',
            get_fill_color='color',
            get_radius='radius',
            pickable=True
        )
    ]
    
    if show_veg and 'vegetation_masked' in df.columns:
        veg_df = df[df['vegetation_masked'] == True].copy()
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=veg_df,
                get_position='[longitude, latitude]',
                get_fill_color='[50, 180, 80, 100]',
                get_radius=800,
                pickable=False
            )
        )
        
    view_state = pdk.ViewState(
        latitude=21.25,
        longitude=79.25,
        zoom=10,
        pitch=45
    )
    
    st.pydeck_chart(pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        tooltip={"text": "Lat: {latitude}, Lon: {longitude}\\nProb: {mn_probability}"}
    ))
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Feature Importance")
        model = load_model()
        
        # Placeholder data for feature importance
        features = ['iron_oxide_index', 'clay_index', 'fault_distance_km', 'rock_type', 'ndvi', 'elevation_m', 'slope_deg', 'rainfall_mm', 'shear_zone_proximity_km', 'soil_moisture']
        np.random.seed(42)
        importances = np.random.rand(len(features))
        importances = importances / np.sum(importances)
        
        feat_df = pd.DataFrame({'Feature': features, 'Importance': importances}).sort_values('Importance', ascending=True)
        st.bar_chart(feat_df.set_index('Feature'))
        
    with col2:
        st.subheader("Top 10 High-Probability Zones")
        top_10 = df.nlargest(10, 'mn_probability')[['latitude', 'longitude', 'mn_probability']]
        if 'prospectivity_class' in df.columns:
            top_10['prospectivity_class'] = df.loc[top_10.index, 'prospectivity_class']
        st.dataframe(top_10)
        
    st.subheader("Statistics")
    c1, c2, c3 = st.columns(3)
    c1.metric("High Zones", len(df[df['mn_probability'] > 0.8]))
    c2.metric("Medium Zones", len(df[(df['mn_probability'] <= 0.8) & (df['mn_probability'] > 0.4)]))
    c3.metric("Low Zones", len(df[df['mn_probability'] <= 0.4]))
