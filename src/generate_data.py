"""
MOIL-GeoSync - Stage 2
Generates the prospectivity dataset (Real Spectral + Synthetic Geological/Label)
and the production dataset (100% Synthetic).
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime

# Set random state globally
np.random.seed(42)

def main():
    # Paths relative to __file__
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    
    os.makedirs(data_dir, exist_ok=True)
    
    # 1. Load real_spectral.csv (REAL data from Stage 1)
    real_spectral_path = os.path.join(data_dir, 'real_spectral.csv')
    
    if not os.path.exists(real_spectral_path):
        # Create a dummy real_spectral.csv if it doesn't exist for testing
        print("real_spectral.csv not found, generating dummy spectral data to proceed...")
        df_spectral = pd.DataFrame({
            'latitude': np.random.uniform(21.0, 21.5, 1000),
            'longitude': np.random.uniform(79.0, 79.5, 1000),
            'ndvi': np.random.uniform(0, 1, 1000),
            'iron_oxide_index': np.random.uniform(0, 1, 1000),
            'clay_index': np.random.uniform(0, 1, 1000),
            'B02': np.random.uniform(0, 1, 1000),
            'B04': np.random.uniform(0, 1, 1000),
            'B08': np.random.uniform(0, 1, 1000),
            'B11': np.random.uniform(0, 1, 1000),
            'B12': np.random.uniform(0, 1, 1000),
        })
    else:
        # Use comment='#' to skip comment lines
        df_spectral = pd.read_csv(real_spectral_path, comment='#', encoding='utf-8')
    
    n_samples = len(df_spectral)
    
    # 2. Generate prospectivity dataset
    df_prospectivity = df_spectral.copy()
    
    # Add synthetic columns
    # rock_type: Rule-based from lat/lon (SYNTHETIC)
    def assign_rock_type(lat, lon):
        val = lat * 1.5 + lon
        if val > 111.5: return 'Mn_bearing_schist'
        elif val > 111.0: return 'Laterite'
        elif val > 110.5: return 'Gondwana_sediment'
        elif val > 110.0: return 'Deccan_basalt'
        else: return 'Granite_gneiss'
    
    df_prospectivity['rock_type'] = [assign_rock_type(lat, lon) for lat, lon in zip(df_prospectivity['latitude'], df_prospectivity['longitude'])]
    
    # Other SYNTHETIC geological features
    df_prospectivity['fault_distance_km'] = np.random.uniform(0, 30, n_samples)
    df_prospectivity['shear_zone_proximity_km'] = np.random.uniform(0, 20, n_samples)
    df_prospectivity['elevation_m'] = np.random.uniform(200, 600, n_samples)
    df_prospectivity['slope_deg'] = df_prospectivity['elevation_m'] / 600 * 25 + np.random.normal(0, 2, n_samples)
    df_prospectivity['slope_deg'] = np.clip(df_prospectivity['slope_deg'], 0, 25)
    
    df_prospectivity['rainfall_mm'] = 800 + (df_prospectivity['latitude'] - 21.0) / 0.5 * 800 + np.random.normal(0, 50, n_samples)
    df_prospectivity['rainfall_mm'] = np.clip(df_prospectivity['rainfall_mm'], 800, 1600)
    
    df_prospectivity['soil_moisture'] = df_prospectivity['rainfall_mm'] / 1600 * 0.6 + np.random.normal(0, 0.05, n_samples)
    df_prospectivity['soil_moisture'] = np.clip(df_prospectivity['soil_moisture'], 0.1, 0.6)
    
    # PU-style labels: mn_occurrence (SYNTHETIC)
    # ~15% labeled as 1. More likely if rock_type is Mn_bearing_schist/Laterite, high iron_oxide, high clay, low fault_distance
    prob = np.zeros(n_samples)
    
    is_favorable_rock = df_prospectivity['rock_type'].isin(['Mn_bearing_schist', 'Laterite'])
    prob += is_favorable_rock * 0.4
    prob += (df_prospectivity['iron_oxide_index'] > df_prospectivity['iron_oxide_index'].median()) * 0.2
    prob += (df_prospectivity['clay_index'] > df_prospectivity['clay_index'].median()) * 0.2
    prob += (df_prospectivity['fault_distance_km'] < 10) * 0.2
    
    # Normalize and threshold to get ~15%
    if prob.max() > 0:
        prob = prob / prob.max()
    threshold = np.percentile(prob, 85) # top 15%
    
    base_labels = (prob >= threshold).astype(int)
    
    # Inject 10-15% noise (flip some positives to 0) to prevent perfect F1
    noise_mask = (base_labels == 1) & (np.random.rand(n_samples) < 0.15)
    base_labels[noise_mask] = 0
    df_prospectivity['mn_occurrence'] = base_labels
    
    # vegetation_masked (SYNTHETIC)
    df_prospectivity['vegetation_masked'] = df_prospectivity['ndvi'] > 0.7
    
    # 4. Create prospectivity_grid.csv (without mn_occurrence)
    df_prospectivity_grid = df_prospectivity.drop(columns=['mn_occurrence'])
    
    # 3. Generate production dataset (100% SYNTHETIC)
    mines = ['Mine_A_Dongri_Buzurg', 'Mine_B_Chikla', 'Mine_C_Munsar']
    start_date = datetime(2021, 1, 1)
    months = 60 # Jan 2021 - Dec 2025
    
    prod_data = []
    
    for mine in mines:
        for i in range(months):
            dt = start_date + pd.DateOffset(months=i)
            month = dt.month
            year = dt.year
            
            planned_tpd = np.random.uniform(500, 1500)
            
            is_monsoon = month in [6, 7, 8, 9]
            
            equipment_availability = np.random.uniform(0.6, 0.8) if is_monsoon else np.random.uniform(0.8, 1.0)
            rainfall_mm = np.random.uniform(200, 500) if is_monsoon else np.random.uniform(0, 50)
            haul_road_condition = np.random.randint(1, 3) if is_monsoon else np.random.randint(3, 6)
            blasting_days = np.random.randint(0, 15) if is_monsoon else np.random.randint(15, 26)
            
            crusher_capacity = planned_tpd * np.random.uniform(1.1, 1.3)
            num_dumpers = np.random.randint(5, 9)
            num_shovels = np.random.randint(2, 5)
            
            # REALISTIC production factors — each parameter directly affects output
            # 1. Equipment availability: direct multiplier (50% avail → ~50% output)
            equip_factor = equipment_availability
            
            # 2. Rainfall impact: heavy rain reduces production significantly
            #    0-50mm: no impact, 50-200mm: mild, 200-400mm: severe, 400+: critical
            if rainfall_mm < 50:
                rain_factor = 1.0
            elif rainfall_mm < 200:
                rain_factor = 1.0 - (rainfall_mm - 50) * 0.001  # up to 15% loss
            elif rainfall_mm < 400:
                rain_factor = 0.85 - (rainfall_mm - 200) * 0.0015  # up to 30% more loss
            else:
                rain_factor = 0.55 - (rainfall_mm - 400) * 0.001  # severe
            rain_factor = max(0.3, rain_factor)
            
            # 3. Blasting days: proportional (0 days → ~40% capacity from existing stock, 25 → full)
            blast_factor = 0.4 + 0.6 * (blasting_days / 25.0)
            
            # 4. Road condition: bad roads slow hauling (1=40% penalty, 5=no penalty)
            road_factor = 0.6 + 0.1 * haul_road_condition  # range: 0.7 to 1.1
            
            # 5. Fleet size: more dumpers/shovels = more throughput (diminishing returns)
            #    Baseline: 6 dumpers, 3 shovels
            dumper_factor = min(1.2, 0.5 + 0.1 * num_dumpers)  # 5dum=1.0, 8dum=1.2 (capped)
            shovel_factor = min(1.15, 0.55 + 0.2 * num_shovels)  # 2shov=0.95, 4shov=1.15
            
            # Combine all factors with small random noise
            noise = np.random.normal(0, 0.03)
            actual_factor = equip_factor * rain_factor * blast_factor * road_factor * dumper_factor * shovel_factor + noise
            actual_factor = np.clip(actual_factor, 0.2, 1.15)
            
            actual_tpd = planned_tpd * actual_factor
            
            prod_data.append({
                'mine_id': mine,
                'month': month,
                'year': year,
                'planned_production_tpd': planned_tpd,
                'actual_production_tpd': actual_tpd,
                'rainfall_mm': rainfall_mm,
                'equipment_availability_pct': equipment_availability,
                'blasting_days': blasting_days,
                'haul_road_condition': haul_road_condition,
                'crusher_capacity_tpd': crusher_capacity,
                'num_dumpers': num_dumpers,
                'num_shovels': num_shovels
            })
            
    df_prod = pd.DataFrame(prod_data)
    
    # Lag features
    df_prod = df_prod.sort_values(by=['mine_id', 'year', 'month']).reset_index(drop=True)
    
    # Forward fill or backfill for lags
    df_prod['lag_1'] = df_prod.groupby('mine_id')['actual_production_tpd'].shift(1)
    df_prod['lag_2'] = df_prod.groupby('mine_id')['actual_production_tpd'].shift(2)
    df_prod['lag_3'] = df_prod.groupby('mine_id')['actual_production_tpd'].shift(3)
    
    df_prod[['lag_1', 'lag_2', 'lag_3']] = df_prod.groupby('mine_id')[['lag_1', 'lag_2', 'lag_3']].bfill()
    
    # Shortfall risk
    ratio = df_prod['actual_production_tpd'] / df_prod['planned_production_tpd']
    df_prod['shortfall_risk'] = np.where(ratio < 0.9, 'High', np.where(ratio < 0.95, 'Medium', 'Low'))
    
    # 5. Create production forecast (100% SYNTHETIC)
    forecast_data = []
    start_forecast = datetime(2026, 1, 1)
    
    for mine in mines:
        for i in range(12):
            dt = start_forecast + pd.DateOffset(months=i)
            month = dt.month
            year = dt.year
            
            planned_tpd = np.random.uniform(500, 1500)
            
            is_monsoon = month in [6, 7, 8, 9]
            
            equipment_availability = np.random.uniform(0.6, 0.8) if is_monsoon else np.random.uniform(0.8, 1.0)
            rainfall_mm = np.random.uniform(200, 500) if is_monsoon else np.random.uniform(0, 50)
            haul_road_condition = np.random.randint(1, 3) if is_monsoon else np.random.randint(3, 6)
            blasting_days = np.random.randint(0, 15) if is_monsoon else np.random.randint(15, 26)
            
            crusher_capacity = planned_tpd * np.random.uniform(1.1, 1.3)
            num_dumpers = np.random.randint(5, 9)
            num_shovels = np.random.randint(2, 5)
            
            forecast_data.append({
                'mine_id': mine,
                'month': month,
                'year': year,
                'planned_production_tpd': planned_tpd,
                'rainfall_mm': rainfall_mm,
                'equipment_availability_pct': equipment_availability,
                'blasting_days': blasting_days,
                'haul_road_condition': haul_road_condition,
                'crusher_capacity_tpd': crusher_capacity,
                'num_dumpers': num_dumpers,
                'num_shovels': num_shovels
            })
            
    df_forecast = pd.DataFrame(forecast_data)
    
    # Lags for forecast
    for lag in ['lag_1', 'lag_2', 'lag_3']:
        df_forecast[lag] = np.random.uniform(500, 1500, len(df_forecast))
    
    # 7. Output CSVs
    prospectivity_dataset_path = os.path.join(data_dir, 'prospectivity_dataset.csv')
    prospectivity_grid_path = os.path.join(data_dir, 'prospectivity_grid.csv')
    production_dataset_path = os.path.join(data_dir, 'production_dataset.csv')
    production_forecast_path = os.path.join(data_dir, 'production_forecast.csv')
    
    df_prospectivity.to_csv(prospectivity_dataset_path, index=False)
    df_prospectivity_grid.to_csv(prospectivity_grid_path, index=False)
    df_prod.to_csv(production_dataset_path, index=False)
    df_forecast.to_csv(production_forecast_path, index=False)
    
    # 8. Prints for verification
    print("=== Prospectivity Dataset ===")
    print(df_prospectivity.head())
    print(df_prospectivity.describe())
    print(f"Total rows: {len(df_prospectivity)}\n")
    
    print("=== Prospectivity Grid ===")
    print(df_prospectivity_grid.head())
    print(f"Total rows: {len(df_prospectivity_grid)}\n")
    
    print("=== Production Dataset ===")
    print(df_prod.head())
    print(df_prod.describe())
    print(f"Total rows: {len(df_prod)}\n")
    
    print("=== Production Forecast ===")
    print(df_forecast.head())
    print(f"Total rows: {len(df_forecast)}\n")

if __name__ == '__main__':
    main()
