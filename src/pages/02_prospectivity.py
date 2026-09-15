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
    st.markdown("### Region")
    region = st.selectbox("Jump to", ["Central India (Nagpur)", "Eastern India (Odisha)", "Southern India (Karnataka)"], label_visibility="collapsed")
    if "Central" in region:
        map_center = dict(lat=21.25, lon=79.25)
    elif "Eastern" in region:
        map_center = dict(lat=22.05, lon=85.25)
    else:
        map_center = dict(lat=15.15, lon=76.55)

    st.markdown("### Layer Control")
    show_heatmap = st.checkbox("🔥 Prospectivity Heatmap", value=True)
    show_ndvi = st.checkbox("🌿 NDVI Vegetation", value=False)
    show_iron = st.checkbox("🟠 Ferrous Iron Index", value=False)
    show_mines = st.checkbox("⛏️ Known Mines", value=True)
    show_drill = st.checkbox("🎯 Drilling Priority Zones", value=False)

    st.markdown("---")
    st.markdown("### Map Style")
    map_style = st.radio("Select", [
        "🌑 Dark", "⬜ Light", "🗺️ Street"
    ], index=0, label_visibility="collapsed")

    if "Dark" in map_style:
        plotly_style = "carto-darkmatter"
    elif "Light" in map_style:
        plotly_style = "carto-positron"
    else:
        plotly_style = "open-street-map"

    st.markdown("---")
    st.markdown("### Heatmap Settings")
    overlay_radius = st.slider("Spread", 8, 40, 18)
    overlay_opacity = st.slider("Opacity", 0.1, 1.0, 0.6, 0.1)

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
    fig = go.Figure()

    # ---- LAYER 1: Prospectivity Heatmap ----
    if show_heatmap and 'mn_probability' in df.columns:
        # Only plot medium-to-high probability points
        # This removes the uniform blue grid background and shows actual hotspots
        hotspots = df[df['mn_probability'] > 0.35].copy()
        
        fig.add_trace(go.Densitymap(
            lat=hotspots['latitude'], lon=hotspots['longitude'],
            z=hotspots['mn_probability'],
            radius=overlay_radius,
            opacity=overlay_opacity,
            colorscale=[[0,'blue'],[0.2,'cyan'],[0.4,'lime'],[0.6,'yellow'],[0.8,'orange'],[1.0,'red']],
            zmin=0.3, zmax=1.0,
            colorbar=dict(title=dict(text="Mn Prob"), x=1.0, len=0.5, y=0.75, thickness=12),
            name='Prospectivity', showlegend=True,
            hovertemplate='Lat: %{lat:.4f}<br>Lon: %{lon:.4f}<br>Prob: %{z:.3f}<extra></extra>',
        ))

    # ---- LAYER 2: NDVI Vegetation ----
    if show_ndvi and 'ndvi' in df.columns:
        veg = df[df['ndvi'] > 0.3]
        fig.add_trace(go.Densitymap(
            lat=veg['latitude'], lon=veg['longitude'],
            z=veg['ndvi'],
            radius=overlay_radius, opacity=overlay_opacity * 0.6,
            colorscale=[[0,'rgba(139,90,43,0.2)'],[0.5,'rgba(100,200,50,0.5)'],[1.0,'rgba(0,80,0,0.8)']],
            colorbar=dict(title=dict(text="NDVI"), x=1.08, len=0.3, y=0.3, thickness=10),
            name='NDVI', showlegend=True,
            hovertemplate='NDVI: %{z:.3f}<extra></extra>',
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

    # ---- LAYER 4: Known Mines ----
    if show_mines:
        mines_lat = [21.38, 21.22, 21.15]
        mines_lon = [79.35, 79.42, 79.55]
        mines_name = ["Dongri Buzurg", "Chikla Mine", "Munsar Mine"]
        fig.add_trace(go.Scattermap(
            lat=mines_lat, lon=mines_lon,
            mode='markers+text',
            marker=dict(size=14, color='red'),
            text=mines_name, textposition='top center',
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
            marker=dict(size=12, color='yellow', opacity=0.9),
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
