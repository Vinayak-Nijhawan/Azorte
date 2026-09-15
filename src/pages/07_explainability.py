import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import joblib
import os
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import (confusion_matrix, classification_report, roc_curve, auc,
                             precision_recall_curve, f1_score, accuracy_score,
                             r2_score, mean_absolute_error, mean_squared_error)
from sklearn.preprocessing import LabelEncoder

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
MODEL_DIR = os.path.join(PROJECT_ROOT, 'models')

st.title("🧬 AI Model Explainability & Validation")
st.markdown("Model accuracy proof + SHAP-based AI decision explanations")

PROSPECT_FEATURES = ['iron_oxide_index','clay_index','ndvi','rock_type_encoded','fault_distance_km',
                     'shear_zone_proximity_km','elevation_m','slope_deg','rainfall_mm','soil_moisture']
PROD_FEATURES = ['planned_production_tpd','rainfall_mm','equipment_availability_pct','blasting_days',
                 'haul_road_condition','crusher_capacity_tpd','num_dumpers','num_shovels','lag_1','lag_2','lag_3']

@st.cache_data
def load_all_data():
    prospect_df = pd.read_csv(os.path.join(DATA_DIR, 'prospectivity_dataset.csv'))
    prospect_grid = pd.read_csv(os.path.join(DATA_DIR, 'prospectivity_grid.csv'))
    prod_df = pd.read_csv(os.path.join(DATA_DIR, 'production_dataset.csv'))
    le = LabelEncoder()
    prospect_df['rock_type_encoded'] = le.fit_transform(prospect_df['rock_type'])
    return prospect_df, prospect_grid, prod_df

@st.cache_resource
def load_models():
    prospect_models = joblib.load(os.path.join(MODEL_DIR, 'prospectivity_pu_rf.joblib'))
    prod_model = joblib.load(os.path.join(MODEL_DIR, 'production_gb.joblib'))
    return prospect_models, prod_model

@st.cache_data
def compute_shap_values(_model, data, is_ensemble=False):
    model_to_explain = _model[0] if is_ensemble else _model
    explainer = shap.TreeExplainer(model_to_explain)
    shap_values = explainer(data)
    return explainer, shap_values

prospect_df, prospect_grid, prod_df = load_all_data()
prospect_models, prod_model = load_models()

tab1, tab2 = st.tabs(["🎯 Prospectivity Model", "⛏️ Production Model"])

# ================================================================
# TAB 1: PROSPECTIVITY
# ================================================================
with tab1:
    st.header("Prospectivity Model — PU Bagging Random Forest")

    X = prospect_df[PROSPECT_FEATURES]
    y = prospect_df['mn_occurrence']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

    y_proba = np.mean([m.predict_proba(X_test)[:,1] for m in prospect_models], axis=0)
    y_pred = (y_proba > 0.5).astype(int)

    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(prospect_models[0], X, y, cv=skf, scoring='f1')

    # ---- KPI ----
    st.subheader("📊 Performance Metrics")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Test Accuracy", f"{acc*100:.1f}%")
    m2.metric("Test F1 Score", f"{f1:.4f}")
    m3.metric("5-Fold CV F1", f"{cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
    m4.metric("Ensemble Size", f"{len(prospect_models)} estimators")

    # ---- CONFUSION MATRIX + ROC ----
    st.subheader("🔍 Model Validation Proof")
    col1, col2 = st.columns(2)

    with col1:
        cm = confusion_matrix(y_test, y_pred)
        labels = ['Unlabeled (0)', 'Mn Positive (1)']
        fig_cm = px.imshow(cm, text_auto=True, x=labels, y=labels,
                           color_continuous_scale='Blues',
                           labels=dict(x="Predicted", y="Actual", color="Count"))
        fig_cm.update_layout(height=400, title="Confusion Matrix (30% holdout)")
        st.plotly_chart(fig_cm, use_container_width=True)

    with col2:
        fpr, tpr, _ = roc_curve(y_test, y_proba)
        roc_auc = auc(fpr, tpr)
        fig_roc = go.Figure()
        fig_roc.add_trace(go.Scatter(x=fpr, y=tpr, mode='lines',
                                      name=f'PU-RF (AUC = {roc_auc:.4f})',
                                      line=dict(color='#e74c3c', width=3)))
        fig_roc.add_trace(go.Scatter(x=[0,1], y=[0,1], mode='lines',
                                      name='Random (0.5)', line=dict(color='gray', dash='dash')))
        fig_roc.update_layout(height=400, title=f"ROC Curve (AUC = {roc_auc:.4f})",
                              xaxis_title="False Positive Rate", yaxis_title="True Positive Rate")
        st.plotly_chart(fig_roc, use_container_width=True)

    # ---- PR CURVE + CV BARS ----
    col3, col4 = st.columns(2)

    with col3:
        precision, recall, _ = precision_recall_curve(y_test, y_proba)
        pr_auc = auc(recall, precision)
        fig_pr = go.Figure()
        fig_pr.add_trace(go.Scatter(x=recall, y=precision, mode='lines',
                                     name=f'PR (AUC = {pr_auc:.4f})', line=dict(color='#2ecc71', width=3)))
        fig_pr.update_layout(height=400, title=f"Precision-Recall (AUC = {pr_auc:.4f})",
                             xaxis_title="Recall", yaxis_title="Precision")
        st.plotly_chart(fig_pr, use_container_width=True)

    with col4:
        cv_df = pd.DataFrame({'Fold': [f'Fold {i+1}' for i in range(5)], 'F1 Score': cv_scores})
        fig_cv = px.bar(cv_df, x='Fold', y='F1 Score', color='F1 Score',
                        color_continuous_scale='RdYlGn', range_color=[0.8, 1.0])
        fig_cv.add_hline(y=cv_scores.mean(), line_dash="dash", line_color="white",
                         annotation_text=f"Mean: {cv_scores.mean():.4f}")
        fig_cv.update_layout(height=400, title="5-Fold Cross Validation", showlegend=False)
        st.plotly_chart(fig_cv, use_container_width=True)

    # ---- CLASSIFICATION REPORT ----
    report = classification_report(y_test, y_pred, target_names=['Unlabeled (0)', 'Mn Positive (1)'], output_dict=True)
    st.dataframe(pd.DataFrame(report).T.round(4), use_container_width=True)

    # ================= SHAP EXPLAINABILITY =================
    if SHAP_AVAILABLE:
        st.markdown("---")
        st.subheader("🧠 SHAP — Why did AI make this decision?")
        st.markdown("SHAP (SHapley Additive exPlanations) shows how each feature pushed the model's prediction up or down.")

        X_shap = prospect_df[PROSPECT_FEATURES].sample(n=min(200, len(prospect_df)), random_state=42)

        with st.spinner("Computing SHAP values..."):
            explainer_p, shap_values_p = compute_shap_values(prospect_models, X_shap, is_ensemble=True)

        # ---- GLOBAL: BEESWARM + BAR ----
        st.markdown("#### Global Feature Importance")
        col_s1, col_s2 = st.columns(2)

        with col_s1:
            st.markdown("**SHAP Summary Plot**")
            fig, ax = plt.subplots(figsize=(6, 4))
            sv = shap_values_p[:, :, 1] if len(shap_values_p.shape) == 3 else shap_values_p
            shap.plots.beeswarm(sv, show=False)
            st.pyplot(plt.gcf())
            plt.clf()

        with col_s2:
            st.markdown("**Mean |SHAP| Importance**")
            if len(shap_values_p.shape) == 3:
                mean_shap = np.abs(shap_values_p.values[:, :, 1]).mean(axis=0)
            else:
                mean_shap = np.abs(shap_values_p.values).mean(axis=0)
            imp_df = pd.DataFrame({'Feature': PROSPECT_FEATURES, 'Importance': mean_shap}).sort_values('Importance', ascending=True)
            fig_bar = px.bar(imp_df, x='Importance', y='Feature', orientation='h', title='Feature Impact Magnitude')
            st.plotly_chart(fig_bar, use_container_width=True)

        # ---- LOCAL: WATERFALL ----
        st.markdown("#### Local Explanation — Single Point")
        top_points = prospect_df.nlargest(10, 'mn_probability') if 'mn_probability' in prospect_df.columns else prospect_df.head(10)
        
        if 'mn_probability' in prospect_df.columns:
            point_idx = st.selectbox("Select a grid point (Top 10 by Probability):", top_points.index,
                                     format_func=lambda x: f"Point {x} - Prob: {prospect_df.loc[x, 'mn_probability']:.2f}")
        else:
            point_idx = st.selectbox("Select a grid point:", top_points.index)

        if point_idx is not None:
            point_data = prospect_df.loc[[point_idx]][PROSPECT_FEATURES]
            _, point_shap = compute_shap_values(prospect_models, point_data, is_ensemble=True)

            st.markdown(f"**Explanation for Point {point_idx} (Lat: {prospect_df.loc[point_idx, 'latitude']:.4f}, Lon: {prospect_df.loc[point_idx, 'longitude']:.4f})**")

            fig, ax = plt.subplots(figsize=(6, 4))
            sv_point = point_shap[0, :, 1] if len(point_shap.shape) == 3 else point_shap[0]
            shap.plots.waterfall(sv_point, show=False)
            st.pyplot(plt.gcf())
            plt.clf()

            vals = sv_point.values
            top_idx = np.argsort(np.abs(vals))[-3:][::-1]
            contrib = ", ".join([f"{PROSPECT_FEATURES[i]}={point_data.iloc[0, i]:.2f} ({'+' if vals[i]>0 else ''}{vals[i]:.2f})" for i in top_idx])
            
            if 'mn_probability' in prospect_df.columns:
                prob = prospect_df.loc[point_idx, 'mn_probability']
                cls = prospect_df.loc[point_idx].get('prospectivity_class', 'N/A')
                st.info(f"**Score: {prob:.2f} ({cls})** because: {contrib}")
            
            st.dataframe(point_data.T.rename(columns={point_idx: 'Value'}))

# ================================================================
# TAB 2: PRODUCTION
# ================================================================
with tab2:
    st.header("Production Model — Gradient Boosting Regressor")

    X_prod = prod_df[PROD_FEATURES]
    y_prod = prod_df['actual_production_tpd']
    X_tr, X_te, y_tr, y_te = train_test_split(X_prod, y_prod, test_size=0.3, random_state=42)
    y_te_pred = prod_model.predict(X_te)

    r2 = r2_score(y_te, y_te_pred)
    mae = mean_absolute_error(y_te, y_te_pred)
    rmse = np.sqrt(mean_squared_error(y_te, y_te_pred))

    # ---- KPI ----
    st.subheader("📊 Performance Metrics")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("R² Score", f"{r2:.4f}")
    m2.metric("MAE", f"{mae:.1f} TPD")
    m3.metric("RMSE", f"{rmse:.1f} TPD")
    m4.metric("Error %", f"{mae/y_prod.mean()*100:.1f}%")

    # ---- ACTUAL vs PREDICTED + RESIDUALS ----
    st.subheader("🔍 Model Validation Proof")
    col1, col2 = st.columns(2)

    with col1:
        fig_avp = go.Figure()
        fig_avp.add_trace(go.Scatter(x=y_te.values, y=y_te_pred, mode='markers',
                                      marker=dict(size=8, color='#3498db', opacity=0.7), name='Predictions'))
        mn, mx = min(y_te.min(), y_te_pred.min()), max(y_te.max(), y_te_pred.max())
        fig_avp.add_trace(go.Scatter(x=[mn,mx], y=[mn,mx], mode='lines', name='Perfect',
                                      line=dict(color='red', dash='dash', width=2)))
        fig_avp.update_layout(height=450, title=f"Actual vs Predicted (R²={r2:.4f})",
                              xaxis_title="Actual (TPD)", yaxis_title="Predicted (TPD)")
        st.plotly_chart(fig_avp, use_container_width=True)

    with col2:
        residuals = y_te.values - y_te_pred
        fig_res = px.histogram(residuals, nbins=25, title="Prediction Error Distribution",
                               labels={'value': 'Error (TPD)', 'count': 'Frequency'},
                               color_discrete_sequence=['#e74c3c'])
        fig_res.add_vline(x=0, line_dash="dash", line_color="white")
        fig_res.update_layout(height=450, showlegend=False)
        st.plotly_chart(fig_res, use_container_width=True)

    # ---- FEATURE IMPORTANCE ----
    imp = prod_model.feature_importances_
    feat_df = pd.DataFrame({'Feature': PROD_FEATURES, 'Importance': imp}).sort_values('Importance', ascending=True)
    fig_imp = px.bar(feat_df, x='Importance', y='Feature', orientation='h',
                     color='Importance', color_continuous_scale='RdYlGn_r', title="Which factors most affect production?")
    fig_imp.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig_imp, use_container_width=True)

    # ---- SHAP for Production ----
    if SHAP_AVAILABLE:
        st.markdown("---")
        st.subheader("🧠 SHAP — Production Decision Explanation")

        X_shap_prod = prod_df[PROD_FEATURES].sample(n=min(50, len(prod_df)), random_state=42)
        with st.spinner("Computing SHAP values..."):
            _, shap_values_prod = compute_shap_values(prod_model, X_shap_prod, is_ensemble=False)

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.markdown("**SHAP Summary Plot**")
            fig, ax = plt.subplots(figsize=(6, 4))
            shap.plots.beeswarm(shap_values_prod, show=False)
            st.pyplot(plt.gcf())
            plt.clf()

        with col_s2:
            mean_shap_prod = np.abs(shap_values_prod.values).mean(axis=0)
            imp_prod_df = pd.DataFrame({'Feature': PROD_FEATURES, 'Importance': mean_shap_prod}).sort_values('Importance', ascending=True)
            fig_bar_prod = px.bar(imp_prod_df, x='Importance', y='Feature', orientation='h', title='Feature Impact Magnitude')
            st.plotly_chart(fig_bar_prod, use_container_width=True)

        st.markdown("#### Local Explanation")
        mine_month = prod_df['mine_id'].astype(str) + " - Month " + prod_df['month'].astype(str) + ", " + prod_df['year'].astype(str)
        selected_idx = st.selectbox("Select a Mine & Month:", prod_df.index, format_func=lambda x: mine_month[x])

        if selected_idx is not None:
            point_prod = prod_df.loc[[selected_idx]][PROD_FEATURES]
            _, point_shap_prod = compute_shap_values(prod_model, point_prod, is_ensemble=False)
            st.markdown(f"**Explanation for {mine_month[selected_idx]}**")
            fig, ax = plt.subplots(figsize=(6, 4))
            shap.plots.waterfall(point_shap_prod[0], show=False)
            st.pyplot(plt.gcf())
            plt.clf()
            st.dataframe(point_prod.T.rename(columns={selected_idx: 'Value'}))

# ================= METHODOLOGY ============================
st.markdown("---")
st.subheader("📝 Methodology Note (For Judges)")
st.info("""
**Evaluation:**  
- 70/30 stratified train-test split — model never sees test data during training  
- 5-Fold Cross Validation confirms model is consistent, not overfitting  

**PU Learning (Positive-Unlabeled):**  
- Only ~15% of locations are labeled as manganese-positive (known survey sites)  
- Remaining 85% are *unlabeled* (not negative) — mirrors real geological surveys  
- PU Bagging with 30 Random Forest estimators handles this uncertainty  

**SHAP Explainability:**  
- SHapley Additive exPlanations — game-theory based feature attribution  
- Shows exactly WHY the model made each prediction — no black box  
- Beeswarm plot = global view, Waterfall plot = single-point explanation  

**Data:** Synthetic for prototype. Same pipeline can retrain on real MOIL data.
""")
