import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import joblib
import os
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
MODEL_DIR = os.path.join(PROJECT_ROOT, 'models')

# ─── Plotly dark theme template ───
PLOTLY_BASE = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(color='#c9d1d9', size=14),
    margin=dict(l=40, r=20, t=40, b=40),
)

PLOTLY_AXIS_GRID = dict(
    gridcolor='rgba(255,255,255,0.06)',
    zerolinecolor='rgba(255,255,255,0.06)',
)

def apply_plotly_theme(fig, has_axes=True):
    """Apply consistent dark theme to a Plotly figure."""
    fig.update_layout(**PLOTLY_BASE)
    if has_axes:
        fig.update_xaxes(**PLOTLY_AXIS_GRID)
        fig.update_yaxes(**PLOTLY_AXIS_GRID)
    return fig

EARTH_COLORS = ['#d97706', '#0d9488', '#6366f1', '#e11d48', '#22c55e', '#8b5cf6', '#f59e0b', '#06b6d4']

# ─── Data loaders ───
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

# ─── CSS ───
st.markdown("""
<style>
    .geo-header {
        background: linear-gradient(135deg, rgba(217, 119, 6, 0.15) 0%, rgba(13, 148, 136, 0.15) 50%, rgba(99, 102, 241, 0.1) 100%);
        border: 1px solid rgba(217, 119, 6, 0.25);
        border-radius: 16px;
        padding: 28px 36px;
        margin-bottom: 24px;
    }
    .geo-header h1 {
        background: linear-gradient(135deg, #f59e0b, #0d9488, #6366f1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.6rem !important;
        font-weight: 800 !important;
        margin-bottom: 4px !important;
    }
    .geo-header p {
        color: #9ca3af !important;
        font-size: 1.05rem !important;
        margin-bottom: 0 !important;
    }
    .geo-badge {
        display: inline-block;
        background: rgba(13, 148, 136, 0.2);
        border: 1px solid rgba(13, 148, 136, 0.4);
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.8rem !important;
        color: #5eead4 !important;
        margin-top: 10px;
    }
    .kpi-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 22px 24px;
        transition: all 0.3s ease-in-out;
        min-height: 140px;
    }
    .kpi-card:hover {
        background: rgba(255, 255, 255, 0.07);
        transform: translateY(-3px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        border-color: rgba(217, 119, 6, 0.3);
    }
    .kpi-label {
        font-size: 0.85rem !important;
        color: #9ca3af !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px !important;
    }
    .kpi-value {
        font-size: 2.2rem !important;
        font-weight: 700 !important;
        color: #f9fafb !important;
        line-height: 1.1 !important;
    }
    .kpi-delta {
        font-size: 0.82rem !important;
        margin-top: 6px !important;
    }
    .kpi-delta.positive { color: #22c55e !important; }
    .kpi-delta.neutral  { color: #9ca3af !important; }
    .kpi-delta.warning  { color: #f59e0b !important; }
    .legend-bar {
        background: linear-gradient(to top, #1e40af, #06b6d4, #22c55e, #eab308, #ef4444);
        height: 140px; width: 22px; border-radius: 6px; float: left; margin-right: 14px;
    }
    .legend-labels {
        height: 140px; display: flex; flex-direction: column; justify-content: space-between;
        font-size: 0.85rem !important; color: #d1d5db !important;
    }
    .sidebar-section {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 14px;
    }
    .sidebar-section-title {
        font-size: 0.75rem !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #6b7280 !important;
        font-weight: 700 !important;
        margin-bottom: 10px !important;
    }
    div[data-testid="stTabs"] button[data-baseweb="tab"] {
        font-size: 0.95rem !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

# ─── HEADER ───
st.markdown("""
<div class="geo-header">
    <h1>⛏️ GeoProspect AI</h1>
    <p>AI-predicted manganese prospectivity mapping for the <strong>Nagpur–Bhandara–Balaghat</strong> belt using PU-Bagging Random Forest on satellite spectral indices, geological proxies, and terrain features.</p>
    <span class="geo-badge">🧠 PU-Learning · 30× Bagging · 10 Features · 2,500 Grid Points</span>
</div>
""", unsafe_allow_html=True)

# ─── Load data ───
df = load_data()
model = load_model()

if df.empty:
    st.warning("No data found. Run the data pipeline first (`python src/generate_data.py && python src/train_prospectivity.py`).")
    st.stop()

# ─── SIDEBAR FILTERS ───
with st.sidebar:
    st.markdown('<p class="sidebar-section-title">🎛️ Filters</p>', unsafe_allow_html=True)

    # Probability range
    prob_min = float(df['mn_probability'].min()) if 'mn_probability' in df.columns else 0.0
    prob_max = float(df['mn_probability'].max()) if 'mn_probability' in df.columns else 1.0
    prob_range = st.slider(
        "Mn Probability Range",
        min_value=0.0, max_value=1.0,
        value=(prob_min, prob_max),
        step=0.01,
        help="Filter grid points by predicted manganese probability"
    )

    # Rock type filter
    if 'rock_type' in df.columns:
        all_rocks = sorted(df['rock_type'].dropna().unique().tolist())
        selected_rocks = st.multiselect("Rock Type", all_rocks, default=all_rocks)
    else:
        selected_rocks = None

    # Confidence filter
    if 'confidence' in df.columns:
        conf_options = df['confidence'].dropna().unique().tolist()
        selected_conf = st.multiselect("Confidence", conf_options, default=conf_options)
    else:
        selected_conf = None

    st.markdown("---")
    st.markdown('<p class="sidebar-section-title">🗺️ Map Layers</p>', unsafe_allow_html=True)

    show_heatmap = st.checkbox("🔥 Prospectivity Heatmap", value=True)
    show_markers = st.checkbox("📍 Grid Point Markers", value=False,
                               help="Show individual points color-coded by probability")
    show_geo = st.checkbox("🌿 NDVI Vegetation Layer", value=False)
    show_mines = st.checkbox("⛏️ Known MOIL Mines", value=True)
    show_drill = st.checkbox("🎯 Drilling Priority Zones", value=True)

    st.markdown("---")
    st.markdown('<p class="sidebar-section-title">📐 Legend</p>', unsafe_allow_html=True)
    st.markdown("""
    <div style="display:flex; align-items:stretch;">
        <div class="legend-bar"></div>
        <div class="legend-labels">
            <span><b>High</b> (>0.8)</span>
            <span><b>Med</b> (0.4–0.8)</span>
            <span><b>Low</b> (<0.4)</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ─── Apply filters ───
filtered = df.copy()
if 'mn_probability' in filtered.columns:
    filtered = filtered[(filtered['mn_probability'] >= prob_range[0]) & (filtered['mn_probability'] <= prob_range[1])]
if selected_rocks is not None and 'rock_type' in filtered.columns:
    filtered = filtered[filtered['rock_type'].isin(selected_rocks)]
if selected_conf is not None and 'confidence' in filtered.columns:
    filtered = filtered[filtered['confidence'].isin(selected_conf)]

# ─── KPI CARDS ───
if 'mn_probability' in filtered.columns:
    n_total = len(filtered)
    n_high = int((filtered['mn_probability'] > 0.8).sum())
    n_medium = int(((filtered['mn_probability'] > 0.4) & (filtered['mn_probability'] <= 0.8)).sum())
    avg_prob = filtered['mn_probability'].mean()
    pct_high = (n_high / n_total * 100) if n_total > 0 else 0

    # Dominant rock in high-prob zones
    if 'rock_type' in filtered.columns:
        high_df = filtered[filtered['mn_probability'] > 0.8]
        if len(high_df) > 0:
            dominant_rock = high_df['rock_type'].mode().iloc[0] if len(high_df['rock_type'].mode()) > 0 else "N/A"
        else:
            dominant_rock = "N/A"
    else:
        dominant_rock = "N/A"
else:
    n_total, n_high, n_medium, avg_prob, pct_high, dominant_rock = 0, 0, 0, 0, 0, "N/A"

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Grid Points (Filtered)</div>
        <div class="kpi-value">{n_total:,}</div>
        <div class="kpi-delta neutral">of {len(df):,} total</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">High Priority Targets</div>
        <div class="kpi-value" style="color: #ef4444 !important;">{n_high}</div>
        <div class="kpi-delta warning">{pct_high:.1f}% of filtered</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Avg Mn Probability</div>
        <div class="kpi-value">{avg_prob:.4f}</div>
        <div class="kpi-delta {'positive' if avg_prob > 0.4 else 'neutral'}">{'Above threshold' if avg_prob > 0.4 else 'Below threshold'}</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Dominant Rock (High Prob)</div>
        <div class="kpi-value" style="font-size: 1.4rem !important;">{dominant_rock.replace('_', ' ')}</div>
        <div class="kpi-delta neutral">in zones > 0.8 probability</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── MAP ───
st.markdown("### 🗺️ Prospectivity Map")

# Center on filtered data or default
if len(filtered) > 0:
    center_lat = filtered['latitude'].mean()
    center_lon = filtered['longitude'].mean()
else:
    center_lat, center_lon = 21.25, 79.25

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=10,
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri Satellite'
)

# Add OpenStreetMap as an optional base layer
folium.TileLayer('openstreetmap', name='Street Map').add_to(m)

# 1. Prospectivity Heatmap
if show_heatmap and 'mn_probability' in filtered.columns:
    heat_data = filtered[['latitude', 'longitude', 'mn_probability']].values.tolist()
    HeatMap(
        heat_data,
        name='Mn Prospectivity',
        min_opacity=0.35,
        max_val=float(filtered['mn_probability'].max()) if len(filtered) > 0 else 1.0,
        radius=20,
        blur=14,
        max_zoom=15,
        gradient={0.0: '#1e40af', 0.25: '#06b6d4', 0.5: '#22c55e', 0.75: '#eab308', 1.0: '#ef4444'}
    ).add_to(m)

# 2. Individual grid-point markers (color-coded)
if show_markers and 'mn_probability' in filtered.columns:
    # Sample if too many points
    marker_df = filtered if len(filtered) <= 500 else filtered.sample(500, random_state=42)
    for _, row in marker_df.iterrows():
        prob = row['mn_probability']
        if prob > 0.8:
            color = '#ef4444'
        elif prob > 0.4:
            color = '#eab308'
        else:
            color = '#3b82f6'

        rock = row.get('rock_type', 'N/A')
        elev = row.get('elevation_m', 'N/A')
        ndvi_val = row.get('ndvi', 'N/A')
        conf = row.get('confidence', 'N/A')

        popup_html = f"""
        <div style="font-family:sans-serif; font-size:13px; min-width:180px;">
            <b style="font-size:14px;">Grid Point</b><br>
            <hr style="margin:4px 0;">
            <b>Probability:</b> {prob:.4f}<br>
            <b>Rock Type:</b> {rock}<br>
            <b>Elevation:</b> {elev if isinstance(elev, str) else f'{elev:.0f}m'}<br>
            <b>NDVI:</b> {ndvi_val if isinstance(ndvi_val, str) else f'{ndvi_val:.3f}'}<br>
            <b>Confidence:</b> {conf}<br>
            <b>Coords:</b> {row['latitude']:.4f}°N, {row['longitude']:.4f}°E
        </div>
        """
        folium.CircleMarker(
            [row['latitude'], row['longitude']],
            radius=5,
            color=color,
            weight=1,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"P={prob:.3f}"
        ).add_to(m)

# 3. NDVI vegetation layer
if show_geo and 'ndvi' in filtered.columns:
    ndvi_data = filtered[['latitude', 'longitude', 'ndvi']].values.tolist()
    HeatMap(
        ndvi_data,
        name='NDVI Vegetation',
        min_opacity=0.1,
        radius=15,
        blur=10,
        gradient={0.0: 'rgba(0,0,0,0)', 0.5: 'rgba(74,222,128,0.4)', 1.0: 'rgba(22,101,52,0.7)'}
    ).add_to(m)

# 4. Known MOIL mines
if show_mines:
    mines = [
        {"name": "Dongri Buzurg Mine", "lat": 21.38, "lon": 79.35, "type": "Underground", "ore": "High-grade Mn"},
        {"name": "Chikla Mine", "lat": 21.22, "lon": 79.42, "type": "Opencast", "ore": "Medium-grade Mn"},
        {"name": "Munsar Mine", "lat": 21.15, "lon": 79.55, "type": "Opencast", "ore": "Ferro-grade Mn"},
    ]
    for mine in mines:
        popup_html = f"""
        <div style="font-family:sans-serif; font-size:13px; min-width:160px;">
            <b style="font-size:15px; color:#d97706;">⛏️ {mine['name']}</b><br>
            <hr style="margin:4px 0;">
            <b>Type:</b> {mine['type']}<br>
            <b>Ore:</b> {mine['ore']}<br>
            <b>Coords:</b> {mine['lat']}°N, {mine['lon']}°E
        </div>
        """
        folium.Marker(
            [mine['lat'], mine['lon']],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"⛏️ {mine['name']}",
            icon=folium.Icon(color='orange', icon='industry', prefix='fa'),
        ).add_to(m)

# 5. Drilling priority zones
if show_drill and 'mn_probability' in filtered.columns:
    high_targets = filtered[filtered['mn_probability'] > 0.8].nlargest(25, 'mn_probability')
    for _, row in high_targets.iterrows():
        # Outer ring (glow effect)
        folium.CircleMarker(
            [row['latitude'], row['longitude']],
            radius=14,
            color='#ef4444',
            weight=1,
            fill=True,
            fill_color='#ef4444',
            fill_opacity=0.15,
        ).add_to(m)
        # Inner marker
        rock = row.get('rock_type', 'N/A')
        folium.CircleMarker(
            [row['latitude'], row['longitude']],
            radius=7,
            color='white',
            weight=2,
            fill=True,
            fill_color='#ef4444',
            fill_opacity=0.9,
            popup=f"🎯 P={row['mn_probability']:.4f} | {rock}",
            tooltip=f"🎯 Target ({row['mn_probability']:.4f})",
        ).add_to(m)

# Layer control
folium.LayerControl(collapsed=False).add_to(m)

st_folium(m, use_container_width=True, height=650, returned_objects=[])

# ─── TABBED ANALYTICS ───
st.markdown("---")
st.markdown("### 📊 Analytics")

tab_dist, tab_geo, tab_drill, tab_feat, tab_spatial = st.tabs([
    "📊 Distribution", "🪨 Geology", "🎯 Drill Targets", "🔬 Feature Importance", "📈 Spatial Trends"
])

# ── TAB 1: Distribution ──
with tab_dist:
    if 'mn_probability' in filtered.columns:
        col_hist, col_pie = st.columns(2)

        with col_hist:
            fig_hist = px.histogram(
                filtered, x='mn_probability', nbins=50,
                color_discrete_sequence=['#0d9488'],
                title='Mn Probability Distribution'
            )
            apply_plotly_theme(fig_hist)
            fig_hist.update_layout(bargap=0.05)
            fig_hist.update_xaxes(title_text='Mn Probability')
            fig_hist.update_yaxes(title_text='Count')
            st.plotly_chart(fig_hist, use_container_width=True)

        with col_pie:
            if 'prospectivity_class' in filtered.columns:
                class_counts = filtered['prospectivity_class'].value_counts().reset_index()
                class_counts.columns = ['Class', 'Count']
                color_map = {'High': '#ef4444', 'Medium': '#eab308', 'Low': '#3b82f6'}
                fig_pie = px.pie(
                    class_counts, names='Class', values='Count',
                    color='Class', color_discrete_map=color_map,
                    title='Prospectivity Class Breakdown',
                    hole=0.45
                )
                apply_plotly_theme(fig_pie, has_axes=False)
                fig_pie.update_traces(textinfo='percent+label', textfont_size=14)
                st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No probability data available.")

# ── TAB 2: Geology ──
with tab_geo:
    if 'rock_type' in filtered.columns and 'mn_probability' in filtered.columns:
        rock_stats = filtered.groupby('rock_type').agg(
            avg_prob=('mn_probability', 'mean'),
            max_prob=('mn_probability', 'max'),
            count=('mn_probability', 'count'),
            high_count=('mn_probability', lambda x: (x > 0.8).sum())
        ).reset_index().sort_values('avg_prob', ascending=True)
        rock_stats['rock_label'] = rock_stats['rock_type'].str.replace('_', ' ')

        col_bar, col_box = st.columns(2)

        with col_bar:
            fig_rock = px.bar(
                rock_stats, x='avg_prob', y='rock_label', orientation='h',
                color='avg_prob', color_continuous_scale='YlOrRd',
                title='Average Mn Probability by Rock Type',
                text=rock_stats['avg_prob'].apply(lambda x: f'{x:.4f}')
            )
            apply_plotly_theme(fig_rock)
            fig_rock.update_layout(height=400, showlegend=False)
            fig_rock.update_xaxes(title_text='Avg Probability')
            fig_rock.update_yaxes(title_text='')
            fig_rock.update_traces(textposition='outside')
            st.plotly_chart(fig_rock, use_container_width=True)

        with col_box:
            fig_box = px.box(
                filtered, x='rock_type', y='mn_probability',
                color='rock_type', color_discrete_sequence=EARTH_COLORS,
                title='Probability Distribution by Rock Type'
            )
            apply_plotly_theme(fig_box)
            fig_box.update_layout(height=400, showlegend=False,
                                  xaxis_tickangle=-30)
            fig_box.update_xaxes(title_text='')
            fig_box.update_yaxes(title_text='Mn Probability')
            st.plotly_chart(fig_box, use_container_width=True)

        # Summary table
        st.markdown("**Rock Type Summary**")
        summary = rock_stats[['rock_label', 'count', 'avg_prob', 'max_prob', 'high_count']].copy()
        summary.columns = ['Rock Type', 'Grid Points', 'Avg Probability', 'Max Probability', 'High Priority Count']
        summary = summary.sort_values('Avg Probability', ascending=False)
        st.dataframe(summary, use_container_width=True, hide_index=True)
    else:
        st.info("Rock type or probability data not available.")

# ── TAB 3: Drill Targets ──
with tab_drill:
    if 'mn_probability' in filtered.columns:
        n_targets = st.slider("Number of targets to display", 5, 50, 15, key="drill_slider")
        top_n = filtered.nlargest(n_targets, 'mn_probability').copy()
        top_n.insert(0, 'Rank', range(1, len(top_n) + 1))

        display_cols = {
            'Rank': 'Rank',
            'latitude': 'Lat °N',
            'longitude': 'Lon °E',
            'mn_probability': 'Mn Probability',
            'prospectivity_class': 'Class',
            'rock_type': 'Rock Type',
            'elevation_m': 'Elevation (m)',
            'ndvi': 'NDVI',
            'iron_oxide_index': 'Iron Oxide',
            'clay_index': 'Clay Index',
            'fault_distance_km': 'Fault Dist (km)',
            'confidence': 'Confidence'
        }

        available = {k: v for k, v in display_cols.items() if k in top_n.columns}
        styled_df = top_n[list(available.keys())].rename(columns=available)

        # Format numeric columns
        for col in ['Mn Probability', 'NDVI', 'Iron Oxide', 'Clay Index']:
            if col in styled_df.columns:
                styled_df[col] = styled_df[col].apply(lambda x: f'{x:.4f}' if pd.notna(x) else 'N/A')
        for col in ['Elevation (m)', 'Fault Dist (km)']:
            if col in styled_df.columns:
                styled_df[col] = styled_df[col].apply(lambda x: f'{x:.1f}' if pd.notna(x) else 'N/A')
        for col in ['Lat °N', 'Lon °E']:
            if col in styled_df.columns:
                styled_df[col] = styled_df[col].apply(lambda x: f'{x:.4f}' if pd.notna(x) else 'N/A')

        if 'Rank' in styled_df.columns:
            styled_df = styled_df.set_index('Rank')

        st.dataframe(styled_df, use_container_width=True)

        # Download button
        csv_data = top_n.to_csv(index=False)
        st.download_button(
            "📥 Download Top Targets as CSV",
            csv_data,
            file_name="top_drill_targets.csv",
            mime="text/csv"
        )
    else:
        st.info("No probability data available.")

# ── TAB 4: Feature Importance ──
with tab_feat:
    if model is not None:
        try:
            base = model[0] if isinstance(model, list) else model
            if hasattr(base, 'feature_importances_'):
                # Average importance across all ensemble members if it's a list
                if isinstance(model, list):
                    importances = np.zeros(len(model[0].feature_importances_))
                    for m_item in model:
                        importances += m_item.feature_importances_
                    importances /= len(model)
                else:
                    importances = base.feature_importances_

                feature_names = [
                    'Iron Oxide Index', 'Clay Index', 'NDVI', 'Rock Type',
                    'Fault Distance (km)', 'Shear Zone Prox (km)',
                    'Elevation (m)', 'Slope (°)', 'Rainfall (mm)', 'Soil Moisture'
                ]
                feature_names = feature_names[:len(importances)]

                feat_df = pd.DataFrame({
                    'Feature': feature_names,
                    'Importance': importances
                }).sort_values('Importance', ascending=True)

                col_bar_fi, col_info = st.columns([2, 1])

                with col_bar_fi:
                    fig_imp = px.bar(
                        feat_df, x='Importance', y='Feature', orientation='h',
                        color='Importance',
                        color_continuous_scale='YlOrRd',
                        title='Feature Importance (PU-Bagging RF Ensemble)'
                    )
                    apply_plotly_theme(fig_imp)
                    fig_imp.update_layout(height=500, showlegend=False)
                    fig_imp.update_traces(texttemplate='%{x:.3f}', textposition='outside')
                    st.plotly_chart(fig_imp, use_container_width=True)

                with col_info:
                    st.markdown("#### 🧠 Interpretation Guide")
                    st.markdown("""
                    - **Higher importance** = feature has more influence on the model's manganese probability predictions
                    - The model uses **PU-Bagging** (Positive-Unlabeled) with 30 Random Forest iterations
                    - **Spectral indices** (Iron Oxide, Clay, NDVI) are derived from Sentinel-2 satellite bands
                    - **Geological proxies** (Fault Distance, Shear Zone) indicate structural controls
                    - **Terrain features** (Elevation, Slope) capture topographic influence
                    """)

                    top_feat = feat_df.iloc[-1]
                    st.success(f"**Top Feature:** {top_feat['Feature']} ({top_feat['Importance']:.3f})")
        except Exception as e:
            st.error(f"Error computing feature importance: {e}")
    else:
        st.warning("Model not loaded. Run `python src/train_prospectivity.py` to train the model.")

# ── TAB 5: Spatial Trends ──
with tab_spatial:
    if 'mn_probability' in filtered.columns:
        col_s1, col_s2 = st.columns(2)

        with col_s1:
            if 'elevation_m' in filtered.columns:
                fig_elev = px.scatter(
                    filtered, x='elevation_m', y='mn_probability',
                    color='mn_probability',
                    color_continuous_scale='YlOrRd',
                    title='Elevation vs Mn Probability',
                    opacity=0.5
                )
                apply_plotly_theme(fig_elev)
                fig_elev.update_layout(height=400, showlegend=False)
                fig_elev.update_xaxes(title_text='Elevation (m)')
                fig_elev.update_yaxes(title_text='Mn Probability')
                st.plotly_chart(fig_elev, use_container_width=True)

        with col_s2:
            if 'fault_distance_km' in filtered.columns:
                fig_fault = px.scatter(
                    filtered, x='fault_distance_km', y='mn_probability',
                    color='mn_probability',
                    color_continuous_scale='YlOrRd',
                    title='Fault Distance vs Mn Probability',
                    opacity=0.5
                )
                apply_plotly_theme(fig_fault)
                fig_fault.update_layout(height=400, showlegend=False)
                fig_fault.update_xaxes(title_text='Fault Distance (km)')
                fig_fault.update_yaxes(title_text='Mn Probability')
                st.plotly_chart(fig_fault, use_container_width=True)

        # Correlation heatmap
        st.markdown("#### 🔗 Feature Correlation Matrix")
        numeric_cols = ['mn_probability', 'ndvi', 'iron_oxide_index', 'clay_index',
                        'fault_distance_km', 'shear_zone_proximity_km',
                        'elevation_m', 'slope_deg', 'rainfall_mm', 'soil_moisture']
        available_numeric = [c for c in numeric_cols if c in filtered.columns]

        if len(available_numeric) >= 3:
            corr_df = filtered[available_numeric].corr()
            # Rename for readability
            rename_map = {
                'mn_probability': 'Mn Prob', 'ndvi': 'NDVI',
                'iron_oxide_index': 'Fe Oxide', 'clay_index': 'Clay',
                'fault_distance_km': 'Fault Dist', 'shear_zone_proximity_km': 'Shear Zone',
                'elevation_m': 'Elevation', 'slope_deg': 'Slope',
                'rainfall_mm': 'Rainfall', 'soil_moisture': 'Soil Moist'
            }
            corr_df = corr_df.rename(index=rename_map, columns=rename_map)

            fig_corr = go.Figure(data=go.Heatmap(
                z=corr_df.values,
                x=corr_df.columns.tolist(),
                y=corr_df.index.tolist(),
                colorscale='RdBu_r',
                zmid=0,
                text=np.round(corr_df.values, 2),
                texttemplate='%{text}',
                textfont=dict(size=11),
            ))
            apply_plotly_theme(fig_corr)
            fig_corr.update_layout(
                title='Feature Correlation Heatmap',
                height=500,
                xaxis_tickangle=-45,
            )
            st.plotly_chart(fig_corr, use_container_width=True)
        else:
            st.info("Not enough numeric features for correlation analysis.")
    else:
        st.info("No probability data available.")
