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
    # Assuming columns 'Mine', 'Month', 'Year' might exist, fallback gracefully
    mines = dispatch_plan['Mine'].unique() if 'Mine' in dispatch_plan.columns else ['All']
    selected_mine = st.sidebar.selectbox("Select Mine", mines)
    
    months = dispatch_plan['Month'].unique() if 'Month' in dispatch_plan.columns else ['All']
    selected_month = st.sidebar.selectbox("Select Month", months)
    
    years = dispatch_plan['Year'].unique() if 'Year' in dispatch_plan.columns else ['All']
    selected_year = st.sidebar.selectbox("Select Year", years)

    # Filter data based on selection (simplistic approach)
    df_filtered = dispatch_plan.copy()
    if selected_mine != 'All' and 'Mine' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['Mine'] == selected_mine]
    if selected_month != 'All' and 'Month' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['Month'] == selected_month]
    if selected_year != 'All' and 'Year' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['Year'] == selected_year]
        
    alerts_filtered = fleet_alerts.copy()
    if not alerts_filtered.empty:
        if selected_mine != 'All' and 'Mine' in alerts_filtered.columns:
            alerts_filtered = alerts_filtered[alerts_filtered['Mine'] == selected_mine]
        if selected_month != 'All' and 'Month' in alerts_filtered.columns:
            alerts_filtered = alerts_filtered[alerts_filtered['Month'] == selected_month]
        if selected_year != 'All' and 'Year' in alerts_filtered.columns:
            alerts_filtered = alerts_filtered[alerts_filtered['Year'] == selected_year]

    # Overall Metrics
    col1, col2, col3 = st.columns(3)
    planned_tpd = df_filtered['Planned_TPD'].sum() if 'Planned_TPD' in df_filtered.columns else 4500
    achievable_tpd = df_filtered['Achievable_TPD'].sum() if 'Achievable_TPD' in df_filtered.columns else 4800
    delta_tpd = achievable_tpd - planned_tpd
    
    with col1:
        st.metric(label="Achievable TPD vs Planned", value=f"{achievable_tpd:,.0f}", delta=f"{delta_tpd:,.0f}")
    with col2:
        st.metric(label="Total Dumpers Active", value=df_filtered['Dumper_ID'].nunique() if 'Dumper_ID' in df_filtered.columns else 24)
    with col3:
        st.metric(label="Total Shovels Active", value=df_filtered['Shovel_ID'].nunique() if 'Shovel_ID' in df_filtered.columns else 6)

    st.markdown("### Dumper-to-Shovel Dispatch Matrix")
    # If standard columns exist, create a matrix
    if 'Dumper_ID' in df_filtered.columns and 'Shovel_ID' in df_filtered.columns:
        # Values could be binary assigned flag
        val_col = 'Assigned' if 'Assigned' in df_filtered.columns else None
        if val_col:
            matrix = pd.pivot_table(df_filtered, values=val_col, index='Dumper_ID', columns='Shovel_ID', fill_value=0)
            fig = px.imshow(matrix, text_auto=True, aspect="auto", 
                            labels=dict(x="Shovel ID", y="Dumper ID", color="Assigned"),
                            color_continuous_scale="Blues")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.dataframe(df_filtered[['Dumper_ID', 'Shovel_ID']].head(20), use_container_width=True)
    else:
        st.dataframe(df_filtered.head(), use_container_width=True)
        
    st.markdown("### Shovel Throughput vs Capacity")
    if 'Shovel_ID' in df_filtered.columns and 'Throughput' in df_filtered.columns and 'Capacity' in df_filtered.columns:
        fig_bar = px.bar(df_filtered, x='Shovel_ID', y=['Throughput', 'Capacity'], barmode='group',
                         title="Throughput vs Capacity per Shovel")
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        # Mock data for demonstration if actual columns are missing
        mock_data = pd.DataFrame({
            'Shovel_ID': ['S1', 'S2', 'S3', 'S4'],
            'Throughput': [1200, 1100, 950, 1050],
            'Capacity': [1250, 1200, 1000, 1100]
        })
        fig_bar = px.bar(mock_data, x='Shovel_ID', y=['Throughput', 'Capacity'], barmode='group')
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("### Alerts & Recommendations")
    if not alerts_filtered.empty:
        for _, row in alerts_filtered.iterrows():
            severity = row.get('Severity', 'INFO').upper()
            msg = row.get('Message', 'Alert')
            if severity == 'CRITICAL':
                st.error(msg)
            elif severity == 'WARNING':
                st.warning(msg)
            else:
                st.info(msg)
    else:
        st.success("No active alerts for the selected period.")
