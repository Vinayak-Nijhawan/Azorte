"""
MOIL-GeoSync — Live Production Forecaster
=========================================
Fetches LIVE 14-day weather forecasts from Open-Meteo API for 10 MOIL mines.
Feeds this live data into the trained GradientBoostingRegressor to predict
real-time production risks for the upcoming month.
"""

import os
import json
import numpy as np
import pandas as pd
import requests
import joblib
from datetime import datetime, timedelta

# ==============================================================================
# PATHS
# ==============================================================================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODEL_DIR = os.path.join(BASE_DIR, 'models')

# ==============================================================================
# MINES
# ==============================================================================
MOIL_MINES = {
    "Chikla":        {"lat": 21.52, "lon": 79.70},
    "Dongri_Buzurg": {"lat": 21.65, "lon": 80.20},
    "Beldongri":     {"lat": 21.20, "lon": 79.32},
    "Kandri":        {"lat": 21.10, "lon": 79.15},
    "Munsar":        {"lat": 21.35, "lon": 79.55},
    "Gumgaon":       {"lat": 21.12, "lon": 79.10},
    "Balaghat":      {"lat": 21.81, "lon": 80.19},
    "Ukwa":          {"lat": 21.78, "lon": 80.30},
    "Tirodi":        {"lat": 21.69, "lon": 79.72},
    "Sitapatore":    {"lat": 21.73, "lon": 79.80},
}

API_URL = "https://api.open-meteo.com/v1/forecast"

def fetch_live_weather(mine_name, lat, lon):
    """Fetch next 14 days of weather forecast."""
    params = {
        'latitude': lat,
        'longitude': lon,
        'daily': 'precipitation_sum,temperature_2m_max,temperature_2m_min',
        'timezone': 'Asia/Kolkata',
        'forecast_days': 14
    }
    
    try:
        response = requests.get(API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        daily = data['daily']
        
        # Aggregate 14 days into a rough 30-day projection
        rain_14d = sum(daily['precipitation_sum'])
        rainy_days_14d = sum(1 for p in daily['precipitation_sum'] if p > 2.5)
        temp_max_14d = max(daily['temperature_2m_max'])
        
        # Scale to 30 days
        rain_30d = rain_14d * (30/14)
        rainy_days_30d = int(rainy_days_14d * (30/14))
        
        return {
            "rainfall_mm": round(rain_30d, 1),
            "rainy_days": rainy_days_30d,
            "temp_max": temp_max_14d,
            "temp_mean": temp_max_14d - 8.0 # Approx
        }
    except Exception as e:
        print(f"Error fetching live weather for {mine_name}: {e}")
        return None

def main():
    print("=" * 60)
    print("Fetching LIVE 14-Day Weather Forecasts...")
    
    # 1. Load Model & Data
    model_path = os.path.join(MODEL_DIR, 'production_gb.joblib')
    prep_path = os.path.join(MODEL_DIR, 'production_preprocessor.joblib')
    hist_data = os.path.join(DATA_DIR, 'production_dataset_real.csv')
    
    if not os.path.exists(model_path):
        print("Model not found. Run train_production.py first.")
        return
        
    model = joblib.load(model_path)
    prep = joblib.load(prep_path)
    df = pd.read_csv(hist_data, comment='#')
    
    le_mine = prep['mine_encoder']
    le_state = prep['state_encoder']
    le_type = prep['type_encoder']
    features = prep['feature_cols']
    
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    forecast_rows = []
    
    for mine in MOIL_MINES.keys():
        print(f"  -> Fetching {mine}...")
        live_w = fetch_live_weather(mine, MOIL_MINES[mine]['lat'], MOIL_MINES[mine]['lon'])
        if not live_w:
            continue
            
        # Get historical context
        mine_latest = df[df.mine_id == mine].tail(3)
        baseline_tpd = mine_latest['baseline_tpd__REAL'].iloc[-1]
        mine_state = mine_latest['state__REAL'].iloc[-1]
        mine_type = mine_latest['mine_type__REAL'].iloc[-1]
        mine_share = mine_latest['mine_share_pct__DERIVED'].iloc[-1]
        
        lag_values = mine_latest['derived_actual_production_tpd__DERIVED'].tolist()
        while len(lag_values) < 3: lag_values.insert(0, baseline_tpd)
        
        rain = live_w['rainfall_mm']
        
        # Weather penalties
        wp = max(1.0 - max(0, rain - 100) / 500 * 0.30, 0.50)
        ea = max(0.92 - (rain / 500 * 0.15), 0.60)
        hr = max(4.5 - (rain / 100 * 0.8), 1.0)
        bl = max(int(22 - (rain / 100 * 3)), 5)
        hrf = 1 if rain > 200 else 0
        
        X_pred = pd.DataFrame([{
            'rainfall_mm__REAL': rain,
            'rainy_days__REAL': live_w['rainy_days'],
            'temp_max__REAL': live_w['temp_max'],
            'temp_mean__REAL': live_w['temp_mean'],
            'planned_production_tpd__DERIVED': baseline_tpd,
            'weather_penalty_factor__DERIVED': wp,
            'equipment_availability_pct__DERIVED': ea,
            'haul_road_condition__DERIVED': round(hr, 2),
            'blasting_days__DERIVED': bl,
            'high_rainfall_flag__DERIVED': hrf,
            'lag_1__DERIVED': lag_values[-1],
            'lag_2__DERIVED': lag_values[-2],
            'lag_3__DERIVED': lag_values[-3],
            'mine_share_pct__DERIVED': mine_share,
            'month': current_month,
            'mine_encoded': le_mine.transform([mine])[0],
            'state_encoded': le_state.transform([mine_state])[0],
            'mine_type_encoded': le_type.transform([mine_type])[0],
        }])[features]
        
        predicted_tpd = model.predict(X_pred)[0]
        
        # Calculate Risk
        ratio = predicted_tpd / baseline_tpd
        if ratio < 0.85: risk = "High"
        elif ratio < 0.92: risk = "Medium"
        else: risk = "Low"
        
        forecast_rows.append({
            "mine_id": mine,
            "year": current_year,
            "month": current_month,
            "scenario": "live_forecast",
            "baseline_tpd": round(baseline_tpd, 1),
            "predicted_production_tpd": round(predicted_tpd, 1),
            "shortfall_risk": risk,
            "rainfall_mm_scenario": rain,
            "weather_penalty": round(wp, 4),
            "data_type": "LIVE_API",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    out_df = pd.DataFrame(forecast_rows)
    out_path = os.path.join(DATA_DIR, 'production_forecast_live.csv')
    out_df.to_csv(out_path, index=False)
    print(f"\nSaved LIVE predictions to {out_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
