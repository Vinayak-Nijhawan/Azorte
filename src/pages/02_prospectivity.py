import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
    "open-street-map", "carto-positron", "carto-darkmatter"
], index=0)

st.sidebar.markdown("---")
st.sidebar.header("📡 Overlay Layers")
st.sidebar.caption("Select which data to overlay on the map")

overlay_choice = st.sidebar.radio("Active Overlay", [
    "🔴 Manganese Prospectivity",
    "🌿 NDVI Vegetation",
    "🟠 Ferrous Iron Index",
    "🟣 Clay Alteration Index",
    "None (Map Only)",
])

show_drill_sites = st.sidebar.checkbox("💎 Show Drill Site Markers", value=True)

st.sidebar.markdown("---")
overlay_radius = st.sidebar.slider("Overlay Spread", 5, 30, 15)
overlay_opacity = st.sidebar.slider("Overlay Opacity", 0.1, 1.0, 0.6, 0.1)

st.sidebar.markdown("---")
st.sidebar.header("🎯 Filters")
prob_threshold = st.sidebar.slider("Min Probability", 0.0, 1.0, 0.0, 0.05)

# ================= DRILL TARGET SUMMARY =================
st.subheader("Drill Target Summary")
c1, c2, c3 = st.columns(3)
if 'mn_probability' in df.columns:
    high_pri = int((df['mn_probability'] > 0.8).sum())
    med_pri = int(((df['mn_probability'] > 0.4) & (df['mn_probability'] <= 0.8)).sum())
    low_pri = int((df['mn_probability'] <= 0.4).sum())
else:
    high_pri, med_pri, low_pri = 0, 0, 0
c1.metric("🔴 High Priority", f"{high_pri} targets")
c2.metric("🟡 Medium Priority", f"{med_pri} targets")
c3.metric("🟢 Low Priority", f"{low_pri} targets")

# ================= PREPARE DATA =================
plot_df = df.copy()
if 'mn_probability' in plot_df.columns:
    plot_df = plot_df[plot_df['mn_probability'] >= prob_threshold]

# Determine which column and colorscale based on overlay
if "Manganese" in overlay_choice:
    z_col = 'mn_probability'
    color_label = "Mn Probability"
    color_scale = ["rgba(0,0,180,0.2)", "rgba(0,180,255,0.4)", "rgba(0,255,100,0.5)",
                   "rgba(255,255,0,0.6)", "rgba(255,140,0,0.7)", "rgba(255,0,0,0.9)"]
elif "NDVI" in overlay_choice:
    z_col = 'ndvi'
    color_label = "NDVI"
    color_scale = ["rgba(139,90,43,0.2)", "rgba(180,180,50,0.3)", "rgba(100,200,50,0.5)",
                   "rgba(0,150,0,0.7)", "rgba(0,80,0,0.9)"]
elif "Iron" in overlay_choice:
    z_col = 'iron_oxide_index'
    color_label = "Fe Index"
    color_scale = ["rgba(255,255,200,0.2)", "rgba(255,200,50,0.3)", "rgba(255,120,0,0.6)",
                   "rgba(200,50,0,0.8)", "rgba(139,0,0,0.9)"]
elif "Clay" in overlay_choice:
    z_col = 'clay_index'
    color_label = "Clay Index"
    color_scale = ["rgba(200,220,255,0.2)", "rgba(100,100,255,0.4)", "rgba(150,50,200,0.6)",
                   "rgba(100,0,100,0.9)"]
else:
    z_col = None

# ================= BUILD MAP =================
if z_col and z_col in plot_df.columns:
    # Plotly 7.x uses px.density_map (not density_mapbox)
    fig = px.density_map(
        plot_df,
        lat='latitude',
        lon='longitude',
        z=z_col,
        radius=overlay_radius,
        opacity=overlay_opacity,
        color_continuous_scale=color_scale,
        center=dict(lat=21.25, lon=79.25),
        zoom=10,
        labels={z_col: color_label},
        hover_data={
            'latitude': ':.4f',
            'longitude': ':.4f',
            z_col: ':.4f',
        },
    )
    fig.update_layout(map_style=map_style)
else:
    # No overlay — just base map
    fig = go.Figure(go.Scattermap(
        lat=[21.25], lon=[79.25],
        mode='markers',
        marker=dict(size=1, opacity=0),
        showlegend=False,
    ))
    fig.update_layout(
        map=dict(style=map_style, center=dict(lat=21.25, lon=79.25), zoom=10),
    )

# Add drill site markers colored by probability
if show_drill_sites and 'mn_probability' in df.columns:
    drill_df = df[df['mn_probability'] > 0.4].copy()
    if len(drill_df) > 0:
        fig.add_trace(go.Scattermap(
            lat=drill_df['latitude'],
            lon=drill_df['longitude'],
            mode='markers',
            marker=dict(
                size=9,
                color=drill_df['mn_probability'],
                colorscale=[
                    [0.0, 'rgb(0,100,255)'],     # Blue (low)
                    [0.3, 'rgb(0,200,100)'],     # Green
                    [0.5, 'rgb(255,255,0)'],     # Yellow
                    [0.7, 'rgb(255,165,0)'],     # Orange
                    [1.0, 'rgb(255,0,0)'],       # Red (high)
                ],
                cmin=0.0,
                cmax=1.0,
                opacity=0.9,
            ),
            text=[f"Prob: {p:.3f} | {c}"
                  for p, c in zip(
                      drill_df['mn_probability'],
                      drill_df.get('prospectivity_class', ['?']*len(drill_df))
                  )],
            hovertemplate='Lat: %{lat:.4f}<br>Lon: %{lon:.4f}<br>%{text}<extra>Drill Target</extra>',
            name='Drill Targets',
        ))

fig.update_layout(
    height=650,
    margin=dict(l=0, r=0, t=30, b=0),
    legend=dict(
        yanchor="top", y=0.98, xanchor="left", x=0.01,
        bgcolor="rgba(0,0,0,0.7)", font=dict(color="white", size=12),
    ),
    title=dict(
        text="Nagpur-Bhandara-Balaghat Manganese Belt",
        font=dict(size=14),
    ),
)

st.plotly_chart(fig, use_container_width=True)

# ================= LOCATION INSPECTOR =================
st.subheader("📍 Location Inspector — Top 10 Drill Targets")
if 'mn_probability' in df.columns:
    top_10 = df.nlargest(10, 'mn_probability').copy()
    top_10.insert(0, 'Rank', range(1, len(top_10) + 1))
    display_cols = ['Rank']
    col_map = {'Rank': '#'}
    for c, n in [('latitude','Lat °N'),('longitude','Lon °E'),('elevation_m','Elev (m)'),
                  ('mn_probability','Probability'),('prospectivity_class','Class'),
                  ('rock_type','Rock Type'),('ndvi','NDVI'),('iron_oxide_index','Fe Index'),
                  ('clay_index','Clay Index')]:
        if c in top_10.columns:
            display_cols.append(c)
            col_map[c] = n
    st.dataframe(top_10[display_cols].rename(columns=col_map).reset_index(drop=True),
                 use_container_width=True, hide_index=True)

# ================= FEATURE IMPORTANCE =================
st.subheader("🔬 Feature Importance (PU Bagging Random Forest)")
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
            fig_imp.update_layout(height=350, showlegend=False, title="Feature Importances")
            st.plotly_chart(fig_imp, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")
