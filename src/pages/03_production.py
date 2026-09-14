import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

st.title("MineFlow Optimizer - Production Forecast & Risk")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

@st.cache_data
def load_production_data():
    prod_path = os.path.join(DATA_DIR, 'production_dataset.csv')
    forecast_path = os.path.join(DATA_DIR, 'production_forecast.csv')
    
    df_prod = pd.DataFrame()
    df_forecast = pd.DataFrame()
    
    if os.path.exists(prod_path):
        df_prod = pd.read_csv(prod_path)
    
    if os.path.exists(forecast_path):
        df_forecast = pd.read_csv(forecast_path)
        
    return df_prod, df_forecast

df_prod, df_forecast = load_production_data()

if df_prod.empty:
    st.warning("Production dataset not found.")
else:
    if 'mine_id' in df_prod.columns:
        mines = df_prod['mine_id'].unique().tolist()
        selected_mine = st.sidebar.selectbox("Select Mine", mines)
        
        mine_data = df_prod[df_prod['mine_id'] == selected_mine].copy()
        
        # Determine year and month columns
        year_col = 'year' if 'year' in mine_data.columns else 'Year'
        month_col = 'month' if 'month' in mine_data.columns else 'Month'
        
        if year_col in mine_data.columns and month_col in mine_data.columns:
            mine_data['date'] = pd.to_datetime(mine_data[year_col].astype(str) + '-' + mine_data[month_col].astype(str) + '-01')
            mine_data = mine_data.sort_values('date')
            
            fig = go.Figure()
            
            if 'planned_production_tpd' in mine_data.columns:
                fig.add_trace(go.Scatter(x=mine_data['date'], y=mine_data['planned_production_tpd'], name='Planned', line=dict(color='blue', dash='dash')))
            if 'actual_production_tpd' in mine_data.columns:
                fig.add_trace(go.Scatter(x=mine_data['date'], y=mine_data['actual_production_tpd'], name='Actual', line=dict(color='blue')))
                
            if not df_forecast.empty and 'mine_id' in df_forecast.columns:
                forecast_data = df_forecast[df_forecast['mine_id'] == selected_mine].copy()
                if not forecast_data.empty and 'predicted_production_tpd' in forecast_data.columns:
                    forecast_data['date'] = pd.to_datetime(forecast_data[year_col].astype(str) + '-' + forecast_data[month_col].astype(str) + '-01')
                    forecast_data = forecast_data.sort_values('date')
                    fig.add_trace(go.Scatter(x=forecast_data['date'], y=forecast_data['predicted_production_tpd'], name='Predicted', line=dict(color='green', dash='dash')))
                    
            fig.update_layout(
                title=dict(text=f"Production Forecast for {selected_mine}", font=dict(size=28)),
                xaxis=dict(title=dict(text="Date", font=dict(size=20)), tickfont=dict(size=16)),
                yaxis=dict(title=dict(text="Production (TPD)", font=dict(size=20)), tickfont=dict(size=16)),
                legend=dict(font=dict(size=18)),
                margin=dict(t=80)
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("Risk Indicators (Latest Month)")
            latest = mine_data.iloc[-1]
            risk = latest.get('shortfall_risk', 'N/A')
            
            r_col1, r_col2 = st.columns(2)
            with r_col1:
                icon = "🔴" if risk == 'High' else "🟡" if risk == 'Medium' else "🟢"
                st.metric("Risk Level", f"{icon} {risk}" if pd.notnull(risk) else "N/A")
            with r_col2:
                planned = latest.get('planned_production_tpd', 0)
                actual = latest.get('actual_production_tpd', latest.get('predicted_production_tpd', 0))
                shortfall = planned - actual if pd.notnull(planned) and pd.notnull(actual) else 0
                st.metric("Latest Shortfall (TPD)", f"{max(0, shortfall):.0f}")
                    
            st.subheader("Shortfall Summary")
            cols_to_show = ['date']
            if 'planned_production_tpd' in mine_data.columns: cols_to_show.append('planned_production_tpd')
            if 'actual_production_tpd' in mine_data.columns: cols_to_show.append('actual_production_tpd')
            if 'shortfall_risk' in mine_data.columns: cols_to_show.append('shortfall_risk')
            st.table(mine_data[cols_to_show].tail(10))
            
            st.info("💡 **Business Impact:** 5% reduction in production shortfall across 3 mines = approximately 2,500 tons/month saved (illustrative)")
        else:
            st.warning("Time columns (year/month) not found in data.")
    else:
        st.warning("mine_id column not found in data.")
