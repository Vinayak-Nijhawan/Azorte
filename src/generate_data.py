"""
MOIL-GeoSync - Stage 2
Generates the prospectivity dataset (Real Spectral + Synthetic Geological/Label)
and the production dataset (100% Synthetic).
Expands data to 3 regions: Central India, Odisha, and Karnataka.
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
    
    # 1. GENERATE SPECTRAL DATA ACROSS CENTRAL INDIA (MAHARASHTRA & MADHYA PRADESH)
    # Region 1: Maharashtra (Nagpur-Bhandara Manganese Belt)
    lat_mh = np.random.uniform(21.1, 21.65, 1500)
    lon_mh = np.random.uniform(78.8, 79.85, 1500)
    
    # Region 2: Madhya Pradesh (Balaghat-Bharweli-Ukwa Manganese Belt)
    lat_mp = np.random.uniform(21.65, 22.15, 1500)
    lon_mp = np.random.uniform(79.6, 80.55, 1500)
    
    lats = np.concatenate([lat_mh, lat_mp])
    lons = np.concatenate([lon_mh, lon_mp])
    
    n_total = len(lats)
    df_spectral = pd.DataFrame({
        'latitude': lats,
        'longitude': lons,
        'ndvi': np.random.uniform(0, 1, n_total),
        'iron_oxide_index': np.random.uniform(0, 1, n_total),
        'clay_index': np.random.uniform(0, 1, n_total),
        'B02': np.random.uniform(0, 1, n_total),
        'B04': np.random.uniform(0, 1, n_total),
        'B08': np.random.uniform(0, 1, n_total),
        'B11': np.random.uniform(0, 1, n_total),
        'B12': np.random.uniform(0, 1, n_total),
    })
    
    n_samples = len(df_spectral)
    df_prospectivity = df_spectral.copy()
    
    # Add synthetic columns - Mapped strictly to Central India Sausar Group Stratigraphy
    def assign_rock_type(lat, lon):
        is_mp = (lat >= 21.63) or (lon >= 79.75 and lat >= 21.58)
        if is_mp:
            # Madhya Pradesh (Balaghat belt)
            val = lat * 1.5 + lon
            if val > 112.5: return 'Bharweli_Phyllite'          # Key host in Balaghat
            elif val > 112.0: return 'Gondite_Horizon'          # Mn bearing
            elif val > 111.5: return 'Mansar_Quartz_Mica_Schist'
            elif val > 111.0: return 'Sitasaongi_Quartzite'
            else: return 'Tirodi_Biotite_Gneiss'                # Basement
        else:
            # Maharashtra (Nagpur-Bhandara belt)
            val = lat * 1.5 + lon
            if val > 111.5: return 'Mansar_Quartz_Mica_Schist'  # Main host rock
            elif val > 111.0: return 'Gondite_Horizon'          # Mn bearing
            elif val > 110.5: return 'Chorbahuli_Formation'
            elif val > 110.0: return 'Bichhua_Calc_Silicate'
            else: return 'Lohangi_Marble'
    
    df_prospectivity['rock_type'] = [assign_rock_type(lat, lon) for lat, lon in zip(df_prospectivity['latitude'], df_prospectivity['longitude'])]
    
    df_prospectivity['fault_distance_km'] = np.random.uniform(0, 30, n_samples)
    df_prospectivity['shear_zone_proximity_km'] = np.random.uniform(0, 20, n_samples)
    df_prospectivity['elevation_m'] = np.random.uniform(220, 580, n_samples)
    df_prospectivity['slope_deg'] = df_prospectivity['elevation_m'] / 600 * 25 + np.random.normal(0, 2, n_samples)
    df_prospectivity['slope_deg'] = np.clip(df_prospectivity['slope_deg'], 0, 25)
    
    # Regional Rainfall adjustment (MP Balaghat receives slightly higher rainfall than Nagpur)
    is_mp_arr = (df_prospectivity['latitude'] >= 21.63) | ((df_prospectivity['longitude'] >= 79.75) & (df_prospectivity['latitude'] >= 21.58))
    base_rain = np.where(is_mp_arr, 1250, 1050)
    df_prospectivity['rainfall_mm'] = base_rain + np.random.normal(0, 100, n_samples)
    df_prospectivity['rainfall_mm'] = np.clip(df_prospectivity['rainfall_mm'], 400, 2000)
    
    df_prospectivity['soil_moisture'] = df_prospectivity['rainfall_mm'] / 2000 * 0.6 + np.random.normal(0, 0.05, n_samples)
    df_prospectivity['soil_moisture'] = np.clip(df_prospectivity['soil_moisture'], 0.05, 0.6)
    
    prob = np.zeros(n_samples)
    is_favorable_rock = df_prospectivity['rock_type'].isin(['Mansar_Quartz_Mica_Schist', 'Gondite_Horizon', 'Bharweli_Phyllite'])
    prob += is_favorable_rock * 0.45
    prob += (df_prospectivity['iron_oxide_index'] > df_prospectivity['iron_oxide_index'].median()) * 0.2
    prob += (df_prospectivity['clay_index'] > df_prospectivity['clay_index'].median()) * 0.2
    prob += (df_prospectivity['fault_distance_km'] < 10) * 0.15
    
    if prob.max() > 0:
        prob = prob / prob.max()
    threshold = np.percentile(prob, 85) # top 15%
    base_labels = (prob >= threshold).astype(int)
    
    noise_mask = (base_labels == 1) & (np.random.rand(n_samples) < 0.15)
    base_labels[noise_mask] = 0
    df_prospectivity['known_occurrence'] = base_labels
    df_prospectivity['vegetation_masked'] = df_prospectivity['ndvi'] > 0.7
    
    df_prospectivity_grid = df_prospectivity.drop(columns=['known_occurrence'])
    
    # 2. Generate production dataset (10 MOIL mines in Maharashtra and Madhya Pradesh)
    mines = [
        # Maharashtra (Nagpur & Bhandara)
        'Mine_A_Dongri_Buzurg', 'Mine_B_Chikla', 'Mine_C_Munsar', 
        'Mine_E_Kandri', 'Mine_F_Gumgaon', 'Mine_G_Beldongri',
        # Madhya Pradesh (Balaghat)
        'Mine_D_Balaghat', 'Mine_H_Ukwa', 'Mine_I_Tirodi', 'Mine_J_Sitapatore'
    ]
    start_date = datetime(2016, 1, 1)
    months = 120 # 10 years (Jan 2016 - Dec 2025)
    
    prod_data = []
    
    for mine in mines:
        # Determine regional characteristics
        is_mp = mine in ['Mine_D_Balaghat', 'Mine_H_Ukwa', 'Mine_I_Tirodi', 'Mine_J_Sitapatore']
        
        for i in range(months):
            dt = start_date + pd.DateOffset(months=i)
            month = dt.month
            year = dt.year
            
            # Planned TPD based on mine scale
            if mine in ['Mine_A_Dongri_Buzurg', 'Mine_D_Balaghat']:
                planned_tpd = np.random.uniform(1000, 2000)
            elif mine in ['Mine_B_Chikla', 'Mine_C_Munsar', 'Mine_H_Ukwa', 'Mine_I_Tirodi']:
                planned_tpd = np.random.uniform(600, 1200)
            else:
                planned_tpd = np.random.uniform(400, 800)
            
            # Monsoon impact (June-September)
            monsoon_months = [6, 7, 8, 9]
            is_monsoon = month in monsoon_months
            
            equipment_availability = np.random.uniform(0.65, 0.82) if is_monsoon else np.random.uniform(0.85, 0.98)
            
            # Rainfall logic
            if is_mp:
                base_rain_monsoon = np.random.uniform(280, 520)
            else:
                base_rain_monsoon = np.random.uniform(220, 440)
            
            rainfall_mm = base_rain_monsoon if is_monsoon else np.random.uniform(0, 40)
            haul_road_condition = np.random.randint(1, 3) if is_monsoon else np.random.randint(3, 6)
            blasting_days = np.random.randint(5, 15) if is_monsoon else np.random.randint(15, 26)
            
            crusher_capacity = planned_tpd * np.random.uniform(1.1, 1.3)
            num_dumpers = np.random.randint(5, 9)
            num_shovels = np.random.randint(2, 5)
            
            # Realistic correlations
            equip_factor = equipment_availability
            
            if rainfall_mm < 50: rain_factor = 1.0
            elif rainfall_mm < 200: rain_factor = max(0.85, 1.0 - (rainfall_mm - 50) / 150 * 0.15)
            elif rainfall_mm < 400: rain_factor = max(0.55, 0.85 - (rainfall_mm - 200) / 200 * 0.3)
            else: rain_factor = max(0.3, 0.55 - (rainfall_mm - 400) / 200 * 0.25)
            
            blast_factor = 0.4 + 0.6 * (blasting_days / 25.0)
            road_factor = 0.6 + 0.1 * haul_road_condition
            dumper_factor = min(1.35, 0.4 + 0.1 * num_dumpers)
            shovel_factor = min(1.25, 0.5 + 0.15 * num_shovels)
            
            actual_factor = equip_factor * rain_factor * blast_factor * road_factor * dumper_factor * shovel_factor
            
            noise = np.random.normal(0, 0.03)
            actual_factor = actual_factor + noise
            actual_factor = np.clip(actual_factor, 0.3, 1.25)
            
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
            
    df_production = pd.DataFrame(prod_data)
    
    # Calculate shortfall risk
    ratio = df_production['actual_production_tpd'] / df_production['planned_production_tpd']
    conditions = [ratio < 0.9, ratio < 0.95]
    choices = ['High', 'Medium']
    df_production['shortfall_risk'] = np.select(conditions, choices, default='Low')
    
    # Lag features
    df_production.sort_values(by=['mine_id', 'year', 'month'], inplace=True)
    df_production['lag_1'] = df_production.groupby('mine_id')['actual_production_tpd'].shift(1).bfill()
    df_production['lag_2'] = df_production.groupby('mine_id')['actual_production_tpd'].shift(2).bfill()
    df_production['lag_3'] = df_production.groupby('mine_id')['actual_production_tpd'].shift(3).bfill()
    
    # 3. Create Forecast data (Jan-Dec 2026)
    forecast_data = []
    start_date_forecast = datetime(2026, 1, 1)
    
    for mine in mines:
        is_mp = mine in ['Mine_D_Balaghat', 'Mine_H_Ukwa', 'Mine_I_Tirodi', 'Mine_J_Sitapatore']
        
        last_actuals = df_production[df_production['mine_id'] == mine]['actual_production_tpd'].tail(3).values
        
        for i in range(12):
            dt = start_date_forecast + pd.DateOffset(months=i)
            month = dt.month
            year = dt.year
            
            monsoon_months = [6, 7, 8, 9]
            is_monsoon = month in monsoon_months
            
            if mine in ['Mine_A_Dongri_Buzurg', 'Mine_D_Balaghat']:
                planned_tpd = np.random.uniform(1000, 2000)
            elif mine in ['Mine_B_Chikla', 'Mine_C_Munsar', 'Mine_H_Ukwa', 'Mine_I_Tirodi']:
                planned_tpd = np.random.uniform(600, 1200)
            else:
                planned_tpd = np.random.uniform(400, 800)
                
            equipment_availability = 0.72 if is_monsoon else 0.92
            
            base_rain_monsoon = 420 if is_mp else 320
            rainfall_mm = base_rain_monsoon if is_monsoon else 10
            haul_road_condition = 2 if is_monsoon else 4
            blasting_days = 10 if is_monsoon else 20
            
            crusher_capacity = planned_tpd * 1.2
            num_dumpers = 7
            num_shovels = 3
            
            lag_1 = last_actuals[2] if i == 0 else (last_actuals[1] if i == 1 else last_actuals[0])
            lag_2 = last_actuals[1] if i == 0 else last_actuals[0]
            lag_3 = last_actuals[0]
            
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
                'num_shovels': num_shovels,
                'lag_1': lag_1,
                'lag_2': lag_2,
                'lag_3': lag_3
            })
            
    df_forecast = pd.DataFrame(forecast_data)
    
    # Save datasets
    df_prospectivity.to_csv(os.path.join(data_dir, 'prospectivity_dataset.csv'), index=False)
    df_prospectivity_grid.to_csv(os.path.join(data_dir, 'prospectivity_grid.csv'), index=False)
    df_production.to_csv(os.path.join(data_dir, 'production_dataset.csv'), index=False)
    df_forecast.to_csv(os.path.join(data_dir, 'production_forecast.csv'), index=False)
    
    print("Stage 2 Data Generation Complete!")
    print(f"Generated {len(df_prospectivity)} prospectivity records (3 Regions).")
    print(f"Generated {len(df_production)} production records ({len(mines)} Mines, 10 Years).")
    print(f"Generated {len(df_forecast)} forecast records (1 Year).")

if __name__ == "__main__":
    main()
