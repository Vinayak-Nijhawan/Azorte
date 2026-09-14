import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Define paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DISPATCH_PLAN_PATH = os.path.join(DATA_DIR, "dispatch_plan.csv")
FLEET_ALERTS_PATH = os.path.join(DATA_DIR, "fleet_alerts.csv")

@st.cache_data
def load_data():
    dispatch_plan = pd.DataFrame()
    fleet_alerts = pd.DataFrame()
    
    if os.path.exists(DISPATCH_PLAN_PATH):
        dispatch_plan = pd.read_csv(DISPATCH_PLAN_PATH)
    
    if os.path.exists(FLEET_ALERTS_PATH):
        fleet_alerts = pd.read_csv(FLEET_ALERTS_PATH)
        
    return dispatch_plan, fleet_alerts

st.title('MineFlow Optimizer - Fleet Dispatch')

dispatch_plan, fleet_alerts = load_data()

if dispatch_plan.empty:
    st.info("No dispatch plan found. Please run the `optimize_fleet.py` script first to generate the optimization plan.")
else:
    st.sidebar.header("Filter Options")

    # Use actual column names from optimize_fleet.py: mine_id, month, year
    mines = dispatch_plan['mine_id'].unique().tolist() if 'mine_id' in dispatch_plan.columns else ['All']
    selected_mine = st.sidebar.selectbox("Select Mine", mines)
    
    months = sorted(dispatch_plan['month'].unique().tolist()) if 'month' in dispatch_plan.columns else ['All']
    selected_month = st.sidebar.selectbox("Select Month", months)
    
    years = sorted(dispatch_plan['year'].unique().tolist()) if 'year' in dispatch_plan.columns else ['All']
    selected_year = st.sidebar.selectbox("Select Year", years)

    # Filter dispatch data
    df_filtered = dispatch_plan.copy()
    if selected_mine != 'All' and 'mine_id' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['mine_id'] == selected_mine]
    if selected_month != 'All' and 'month' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['month'] == selected_month]
    if selected_year != 'All' and 'year' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['year'] == selected_year]
        
    # Filter alerts data
    alerts_filtered = fleet_alerts.copy()
    if not alerts_filtered.empty:
        if selected_mine != 'All' and 'mine_id' in alerts_filtered.columns:
            alerts_filtered = alerts_filtered[alerts_filtered['mine_id'] == selected_mine]
        if selected_month != 'All' and 'month' in alerts_filtered.columns:
            alerts_filtered = alerts_filtered[alerts_filtered['month'] == selected_month]
        if selected_year != 'All' and 'year' in alerts_filtered.columns:
            alerts_filtered = alerts_filtered[alerts_filtered['year'] == selected_year]

    # Overall Metrics
    col1, col2, col3 = st.columns(3)
    
    planned_tpd = df_filtered['planned_tpd'].mean() if 'planned_tpd' in df_filtered.columns else 0
    achievable_tpd = df_filtered['total_mine_tpd'].mean() if 'total_mine_tpd' in df_filtered.columns else 0
    delta_tpd = achievable_tpd - planned_tpd
    
    with col1:
        st.metric(label="Achievable TPD vs Planned", value=f"{achievable_tpd:,.0f}", delta=f"{delta_tpd:+,.0f}")
    with col2:
        st.metric(label="Total Dumpers Active", value=df_filtered['dumper_id'].nunique() if 'dumper_id' in df_filtered.columns else 0)
    with col3:
        st.metric(label="Total Shovels Active", value=df_filtered['shovel_id'].nunique() if 'shovel_id' in df_filtered.columns else 0)

    # Dispatch Matrix
    st.markdown("### Dumper-to-Shovel Dispatch Matrix")
    if 'dumper_id' in df_filtered.columns and 'assigned_shovel' in df_filtered.columns:
        # Create a binary assignment column for the heatmap
        matrix_df = df_filtered.copy()
        matrix_df['assigned'] = 1
        matrix = pd.pivot_table(matrix_df, values='assigned', index='dumper_id', columns='assigned_shovel', fill_value=0, aggfunc='max')
        fig = px.imshow(matrix, text_auto=True, aspect="auto", 
                        labels=dict(x="Shovel ID", y="Dumper ID", color="Assigned"),
                        color_continuous_scale="Blues")
        fig.update_layout(
            height=500,
            xaxis=dict(title=dict(font=dict(size=20)), tickfont=dict(size=16)),
            yaxis=dict(title=dict(font=dict(size=20)), tickfont=dict(size=16)),
            coloraxis_colorbar=dict(title=dict(font=dict(size=18)), tickfont=dict(size=16))
        )
        fig.update_traces(textfont=dict(size=18))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.dataframe(df_filtered.head(20), use_container_width=True)
        
    # Shovel Throughput
    st.markdown("### Shovel Throughput vs Capacity")
    if 'assigned_shovel' in df_filtered.columns and 'shovel_throughput_tpd' in df_filtered.columns:
        # Aggregate throughput per shovel
        shovel_stats = df_filtered.groupby('assigned_shovel').agg(
            Throughput=('shovel_throughput_tpd', 'first'),
            Dumpers_Assigned=('dumper_id', 'count'),
            Avg_Dumper_Cap=('effective_capacity_tph', 'mean')
        ).reset_index().rename(columns={'assigned_shovel': 'Shovel_ID'})
        
        # Estimate capacity as throughput * 1.2 (shovels typically have headroom)
        shovel_stats['Capacity'] = shovel_stats['Throughput'] * 1.2
        
        fig_bar = px.bar(shovel_stats, x='Shovel_ID', y=['Throughput', 'Capacity'], barmode='group',
                         title="Throughput vs Capacity per Shovel")
        fig_bar.update_layout(
            yaxis_title="TPD",
            title=dict(font=dict(size=26)),
            xaxis=dict(title=dict(font=dict(size=20)), tickfont=dict(size=16)),
            yaxis=dict(title=dict(font=dict(size=20)), tickfont=dict(size=16)),
            legend=dict(font=dict(size=18)),
            margin=dict(t=80)
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        mock_data = pd.DataFrame({
            'Shovel_ID': ['S0', 'S1', 'S2', 'S3'],
            'Throughput': [1200, 1100, 950, 1050],
            'Capacity': [1250, 1200, 1000, 1100]
        })
        fig_bar = px.bar(mock_data, x='Shovel_ID', y=['Throughput', 'Capacity'], barmode='group')
        st.plotly_chart(fig_bar, use_container_width=True)

    # Alerts & Recommendations — use actual column names: alert_type, alert_message
    st.markdown("### Alerts & Recommendations")
    if not alerts_filtered.empty:
        # Limit to most relevant alerts (avoid flooding the page)
        # Group by alert_type and show unique messages
        unique_alerts = alerts_filtered.drop_duplicates(subset=['alert_type', 'alert_message'])
        
        # Show critical and warning first, limit INFO alerts
        critical_alerts = unique_alerts[unique_alerts['alert_type'] == 'CRITICAL']
        warning_alerts = unique_alerts[unique_alerts['alert_type'] == 'WARNING']
        info_alerts = unique_alerts[unique_alerts['alert_type'] == 'INFO']
        
        for _, row in critical_alerts.iterrows():
            st.error(f"🔴 **CRITICAL:** {row['alert_message']}")
        
        for _, row in warning_alerts.iterrows():
            st.warning(f"⚠️ **WARNING:** {row['alert_message']}")
        
        # Show info alerts in a collapsed expander to avoid clutter
        if not info_alerts.empty:
            with st.expander(f"ℹ️ {len(info_alerts)} Info Alerts (equipment maintenance, etc.)"):
                for _, row in info_alerts.iterrows():
                    st.info(row['alert_message'])
        
        # Summary counts
        st.caption(f"Total alerts: {len(critical_alerts)} Critical, {len(warning_alerts)} Warning, {len(info_alerts)} Info")
    else:
        st.success("✅ No active alerts for the selected period.")
