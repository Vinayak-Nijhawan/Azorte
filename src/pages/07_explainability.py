import streamlit as st
import pandas as pd
import numpy as np
import joblib
import os
import matplotlib.pyplot as plt
import plotly.express as px

# Setup paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
MODEL_DIR = os.path.join(PROJECT_ROOT, 'models')

# Try importing shap
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

st.title("AI Model Explainability (XAI) 🧬")

if not SHAP_AVAILABLE:
    st.error("The `shap` library is not installed. Please install it using `pip install shap` to view this page.")
    st.stop()

# Feature definitions
PROSPECT_FEATURES = ['iron_oxide_index', 'clay_index', 'ndvi', 'rock_type_encoded', 
                     'fault_distance_km', 'shear_zone_proximity_km', 'elevation_m', 
                     'slope_deg', 'rainfall_mm', 'soil_moisture']
PROD_FEATURES = ['planned_production_tpd', 'rainfall_mm', 'equipment_availability_pct', 
                 'blasting_days', 'haul_road_condition', 'crusher_capacity_tpd', 
                 'num_dumpers', 'num_shovels', 'lag_1', 'lag_2', 'lag_3']

@st.cache_data
def load_data():
    try:
        prospect_df = pd.read_csv(os.path.join(DATA_DIR, 'prospectivity_grid.csv'))
        prod_df = pd.read_csv(os.path.join(DATA_DIR, 'production_dataset.csv'))
        return prospect_df, prod_df
    except FileNotFoundError as e:
        st.error(f"Data file not found: {e}")
        return None, None

@st.cache_resource
def load_models():
    try:
        prospect_models = joblib.load(os.path.join(MODEL_DIR, 'prospectivity_pu_rf.joblib'))
        prod_model = joblib.load(os.path.join(MODEL_DIR, 'production_gb.joblib'))
        return prospect_models, prod_model
    except FileNotFoundError as e:
        st.error(f"Model file not found: {e}")
        return None, None

prospect_df, prod_df = load_data()
prospect_models, prod_model = load_models()

if prospect_df is None or prospect_models is None:
    st.stop()

@st.cache_data
def compute_shap_values(_model, data, is_ensemble=False):
    model_to_explain = _model[0] if is_ensemble else _model
    explainer = shap.TreeExplainer(model_to_explain)
    shap_values = explainer(data)
    return explainer, shap_values

tab1, tab2 = st.tabs(["GeoProspect AI (Prospectivity)", "MineFlow (Production)"])

with tab1:
    st.header("GeoProspect AI Explanation")
    
    # Sample data for SHAP to avoid slowness
    X_prospect = prospect_df[PROSPECT_FEATURES].sample(n=min(200, len(prospect_df)), random_state=42)
    
    with st.spinner("Computing SHAP values..."):
        explainer_prospect, shap_values_prospect = compute_shap_values(prospect_models, X_prospect, is_ensemble=True)
    
    st.subheader("Global Feature Importance")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**SHAP Summary Plot**")
        fig, ax = plt.subplots(figsize=(6, 4))
        sv_to_plot = shap_values_prospect
        if len(shap_values_prospect.shape) == 3:
            sv_to_plot = shap_values_prospect[:, :, 1]
        shap.plots.beeswarm(sv_to_plot, show=False)
        fig = plt.gcf()
        st.pyplot(fig)
        plt.clf()
        
    with col2:
        st.markdown("**Mean |SHAP| Importance**")
        if len(shap_values_prospect.shape) == 3:
            mean_shap = np.abs(shap_values_prospect.values[:, :, 1]).mean(axis=0)
        else:
            mean_shap = np.abs(shap_values_prospect.values).mean(axis=0)
        
        importance_df = pd.DataFrame({'Feature': PROSPECT_FEATURES, 'Importance': mean_shap})
        importance_df = importance_df.sort_values(by='Importance', ascending=True)
        fig_bar = px.bar(importance_df, x='Importance', y='Feature', orientation='h', title='Feature Impact Magnitude')
        fig_bar.update_layout(
            title=dict(font=dict(size=26)),
            xaxis=dict(title=dict(font=dict(size=20)), tickfont=dict(size=16)),
            yaxis=dict(title=dict(font=dict(size=20)), tickfont=dict(size=20)),
            height=500,
            margin=dict(l=250)
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("Local Explanation")
    top_points = prospect_df.nlargest(10, 'mn_probability')
    point_idx = st.selectbox("Select a grid point to explain (Top 10 by Probability):", top_points.index, 
                             format_func=lambda x: f"Point {x} - Prob: {prospect_df.loc[x, 'mn_probability']:.2f}")
    
    if point_idx is not None:
        point_data = prospect_df.loc[[point_idx]][PROSPECT_FEATURES]
        _, point_shap = compute_shap_values(prospect_models, point_data, is_ensemble=True)
        
        st.markdown(f"**Explanation for Point {point_idx} (Lat: {prospect_df.loc[point_idx, 'latitude']:.4f}, Lon: {prospect_df.loc[point_idx, 'longitude']:.4f})**")
        
        fig, ax = plt.subplots(figsize=(6, 4))
        sv_point_plot = point_shap[0]
        if len(point_shap.shape) == 3:
             sv_point_plot = point_shap[0, :, 1]
        shap.plots.waterfall(sv_point_plot, show=False)
        fig = plt.gcf()
        st.pyplot(fig)
        plt.clf()
        
        prob = prospect_df.loc[point_idx, 'mn_probability']
        cls = prospect_df.loc[point_idx, 'prospectivity_class']
        
        vals = sv_point_plot.values
        top_indices = np.argsort(np.abs(vals))[-3:][::-1]
        
        contrib_text = ", ".join([f"{PROSPECT_FEATURES[i]}={point_data.iloc[0, i]:.2f} (contributed {'+' if vals[i] > 0 else ''}{vals[i]:.2f})" for i in top_indices])
        st.info(f"This location at ({prospect_df.loc[point_idx, 'latitude']:.4f}, {prospect_df.loc[point_idx, 'longitude']:.4f}) scored {prob:.2f} ({cls}) because: {contrib_text}...")
        
        st.table(point_data.T.rename(columns={point_idx: 'Value'}))

with tab2:
    st.header("MineFlow Explanation")
    
    X_prod = prod_df[PROD_FEATURES].sample(n=min(50, len(prod_df)), random_state=42)
    
    with st.spinner("Computing SHAP values..."):
        explainer_prod, shap_values_prod = compute_shap_values(prod_model, X_prod, is_ensemble=False)
        
    st.subheader("Global Feature Importance")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**SHAP Summary Plot**")
        fig, ax = plt.subplots(figsize=(6, 4))
        shap.plots.beeswarm(shap_values_prod, show=False)
        fig = plt.gcf()
        st.pyplot(fig)
        plt.clf()
        
    with col2:
        st.markdown("**Mean |SHAP| Importance**")
        mean_shap_prod = np.abs(shap_values_prod.values).mean(axis=0)
        importance_prod_df = pd.DataFrame({'Feature': PROD_FEATURES, 'Importance': mean_shap_prod})
        importance_prod_df = importance_prod_df.sort_values(by='Importance', ascending=True)
        fig_bar_prod = px.bar(importance_prod_df, x='Importance', y='Feature', orientation='h', title='Feature Impact Magnitude')
        fig_bar_prod.update_layout(
            title=dict(font=dict(size=26)),
            xaxis=dict(title=dict(font=dict(size=20)), tickfont=dict(size=16)),
            yaxis=dict(title=dict(font=dict(size=20)), tickfont=dict(size=20)),
            height=500,
            margin=dict(l=250)
        )
        st.plotly_chart(fig_bar_prod, use_container_width=True)

    st.subheader("Local Explanation")
    mine_month = prod_df['mine_id'].astype(str) + " - Month " + prod_df['month'].astype(str) + ", " + prod_df['year'].astype(str)
    selected_idx = st.selectbox("Select a Mine & Month for Explanation:", prod_df.index, format_func=lambda x: mine_month[x])
    
    if selected_idx is not None:
        point_data_prod = prod_df.loc[[selected_idx]][PROD_FEATURES]
        _, point_shap_prod = compute_shap_values(prod_model, point_data_prod, is_ensemble=False)
        
        st.markdown(f"**Explanation for {mine_month[selected_idx]}**")
        fig, ax = plt.subplots(figsize=(6, 4))
        shap.plots.waterfall(point_shap_prod[0], show=False)
        fig = plt.gcf()
        st.pyplot(fig)
        plt.clf()
        
        st.table(point_data_prod.T.rename(columns={selected_idx: 'Value'}))
