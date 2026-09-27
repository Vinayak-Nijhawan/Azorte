"""
MOIL-GeoSync — MineFlow Data Preparation
=========================================
Combines REAL MOIL annual production data with REAL historical weather data
to create a monthly time-series dataset for ML training.

DATA HONESTY:
- REAL columns are directly from source files (no modification).
- DERIVED columns are computed using documented assumptions.
- No column is presented as observed MOIL monthly production.

Sources:
  Production: newdataset/moil_production_real.csv (MOIL Annual Reports)
  Weather:    newdataset/weather_real.csv          (Open-Meteo Historical API)
"""

import os
import json
import numpy as np
import pandas as pd

np.random.seed(42)

# ==============================================================================
# CONFIGURATION — All modelling assumptions in one place
# ==============================================================================
CONFIG = {
    # Weather penalty parameters
    # Assumption: Heavy rainfall reduces effective mining days and equipment access.
    # This is a PROJECT-DEFINED relationship, NOT an empirically validated one.
    "rainfall_penalty_threshold_mm": 100,   # Monthly rainfall above which penalty applies
    "rainfall_penalty_max": 0.30,           # Maximum production reduction due to rainfall (30%)
    "rainfall_penalty_scale_mm": 500,       # Rainfall at which max penalty is reached
    
    # Temperature penalty (extreme heat reduces worker productivity)
    "temp_penalty_threshold_c": 42,         # Max temp above which penalty applies
    "temp_penalty_per_degree": 0.02,        # 2% reduction per degree above threshold
    
    # Equipment availability (PROJECT-DEFINED ASSUMPTION)
    # Real equipment data is unavailable; we model availability as weather-dependent.
    "base_equipment_availability": 0.92,    # 92% in dry conditions
    "monsoon_equipment_reduction": 0.15,    # 15% drop during heavy rain months
    
    # Haul road condition (PROJECT-DEFINED ASSUMPTION, 1-5 scale)
    # 5 = excellent (dry), 1 = poor (waterlogged)
    "base_haul_road_condition": 4.5,
    "rain_haul_road_degradation_per_100mm": 0.8,  # Condition drops by 0.8 per 100mm rain
    
    # Blasting days (PROJECT-DEFINED ASSUMPTION)
    "base_blasting_days_per_month": 22,
    "rain_blasting_reduction_per_100mm": 3,  # 3 fewer blasting days per 100mm rain
    
    # Crusher capacity (PROJECT-DEFINED ASSUMPTION)
    "crusher_capacity_tpd_by_mine_size": {
        "large": 1200,   # Dongri Buzurg, Balaghat
        "medium": 800,   # Chikla, Munsar, Joda East
        "small": 500,    # Others
    },
    
    # Fleet size (PROJECT-DEFINED ASSUMPTION)
    "fleet_by_mine_size": {
        "large":  {"num_dumpers": 8, "num_shovels": 3},
        "medium": {"num_dumpers": 6, "num_shovels": 2},
        "small":  {"num_dumpers": 5, "num_shovels": 2},
    },
    
    # Noise to prevent deterministic outputs
    "production_noise_std_pct": 0.03,  # 3% random noise on derived production
    
    # Chronological split boundaries
    "train_end_year": 2022,
    "val_end_year": 2023,
    # Test: 2024-2025
}

# Mine size classification (based on real avg_daily_tpd from data)
MINE_SIZES = {
    "Mine_A_Dongri_Buzurg": "large",
    "Mine_B_Chikla": "medium",
    "Mine_C_Munsar": "medium",
    "Mine_D_Balaghat": "large",
    "Mine_E_Kandri": "small",
    "Mine_F_Gumgaon": "small",
    "Mine_G_Joda_East": "medium",
    "Mine_H_Bamebari": "small",
    "Mine_I_Sandur": "small",
    "Mine_J_Hospet": "small",
}

# ==============================================================================
# PATHS
# ==============================================================================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
NEWDATA_DIR = os.path.join(BASE_DIR, 'newdataset')
OUT_DIR = os.path.join(BASE_DIR, 'data')
CONFIG_DIR = os.path.join(BASE_DIR, 'models')
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)


def compute_weather_penalty(rainfall_mm, temp_max):
    """
    Compute a multiplicative weather penalty factor (0.0 to 1.0).
    1.0 = no penalty (perfect conditions).
    Lower = worse conditions.
    
    ASSUMPTION: This is a PROJECT-DEFINED model, not an empirically
    validated rainfall-to-production relationship.
    """
    # Rainfall penalty
    rain_penalty = 0.0
    if rainfall_mm > CONFIG["rainfall_penalty_threshold_mm"]:
        excess = rainfall_mm - CONFIG["rainfall_penalty_threshold_mm"]
        rain_penalty = min(
            excess / CONFIG["rainfall_penalty_scale_mm"] * CONFIG["rainfall_penalty_max"],
            CONFIG["rainfall_penalty_max"]
        )
    
    # Temperature penalty
    temp_penalty = 0.0
    if temp_max > CONFIG["temp_penalty_threshold_c"]:
        temp_penalty = (temp_max - CONFIG["temp_penalty_threshold_c"]) * CONFIG["temp_penalty_per_degree"]
        temp_penalty = min(temp_penalty, 0.10)  # Cap at 10%
    
    return max(1.0 - rain_penalty - temp_penalty, 0.50)  # Floor at 50%


def compute_operational_features(rainfall_mm, temp_max):
    """
    Derive operational indicators from weather.
    All are PROJECT-DEFINED ASSUMPTIONS.
    """
    # Equipment availability
    equip_avail = CONFIG["base_equipment_availability"]
    if rainfall_mm > CONFIG["rainfall_penalty_threshold_mm"]:
        reduction = min(
            (rainfall_mm / CONFIG["rainfall_penalty_scale_mm"]) * CONFIG["monsoon_equipment_reduction"],
            CONFIG["monsoon_equipment_reduction"]
        )
        equip_avail -= reduction
    equip_avail = max(equip_avail, 0.60)
    
    # Haul road condition
    haul_road = CONFIG["base_haul_road_condition"]
    haul_road -= (rainfall_mm / 100) * CONFIG["rain_haul_road_degradation_per_100mm"]
    haul_road = max(haul_road, 1.0)
    haul_road = min(haul_road, 5.0)
    
    # Blasting days
    blasting = CONFIG["base_blasting_days_per_month"]
    blasting -= (rainfall_mm / 100) * CONFIG["rain_blasting_reduction_per_100mm"]
    blasting = max(int(round(blasting)), 5)
    blasting = min(blasting, 25)
    
    # Rainfall intensity category
    if rainfall_mm < 50:
        rain_intensity = "low"
    elif rainfall_mm < 200:
        rain_intensity = "moderate"
    else:
        rain_intensity = "heavy"
    
    high_rainfall_flag = 1 if rainfall_mm > 200 else 0
    
    return equip_avail, haul_road, blasting, rain_intensity, high_rainfall_flag


def main():
    print("=" * 70)
    print("MOIL-GeoSync — MineFlow Data Preparation")
    print("=" * 70)
    
    # ── 1. Load Real Data ──────────────────────────────────────────────
    print("\n[1/6] Loading REAL data sources...")
    prod = pd.read_csv(os.path.join(NEWDATA_DIR, 'moil_production_real.csv'), comment='#')
    weather = pd.read_csv(os.path.join(NEWDATA_DIR, 'weather_real.csv'), comment='#')
    
    # ── 2. Data Quality Report ─────────────────────────────────────────
    print("\n[2/6] DATA QUALITY REPORT")
    print("-" * 40)
    print(f"  Production records:    {len(prod)}")
    print(f"  Production mines:      {prod.mine_id.nunique()}")
    print(f"  Production years:      {prod.year.min()}-{prod.year.max()}")
    print(f"  Production missing:    {prod.isnull().sum().sum()}")
    print(f"  Production duplicates: {prod.duplicated().sum()}")
    print()
    print(f"  Weather records:       {len(weather)}")
    print(f"  Weather mines:         {weather.mine_id.nunique()}")
    print(f"  Weather years:         {weather.year.min()}-{weather.year.max()}")
    print(f"  Weather months:        {sorted(weather.month.unique().tolist())}")
    print(f"  Weather missing:       {weather.isnull().sum().sum()}")
    print(f"  Weather duplicates:    {weather.duplicated().sum()}")
    
    matched = set(prod.mine_id) & set(weather.mine_id)
    unmatched_prod = set(prod.mine_id) - set(weather.mine_id)
    unmatched_weather = set(weather.mine_id) - set(prod.mine_id)
    print(f"\n  Matched mines:         {len(matched)}")
    print(f"  Unmatched (prod):      {unmatched_prod if unmatched_prod else 'None'}")
    print(f"  Unmatched (weather):   {unmatched_weather if unmatched_weather else 'None'}")
    
    if unmatched_prod:
        print(f"  WARNING: {len(unmatched_prod)} production mines have no weather data!")
    
    # ── 3. Merge and Generate Monthly Dataset ──────────────────────────
    print("\n[3/6] Generating monthly dataset...")
    
    rows = []
    for _, prod_row in prod.iterrows():
        mine = prod_row['mine_id']
        year = prod_row['year']
        baseline_tpd = prod_row['avg_daily_tpd']
        annual_tonnes = prod_row['annual_production_tonnes']
        mn_grade = prod_row['mn_grade_avg_pct']
        
        mine_size = MINE_SIZES.get(mine, "small")
        crusher_cap = CONFIG["crusher_capacity_tpd_by_mine_size"][mine_size]
        fleet = CONFIG["fleet_by_mine_size"][mine_size]
        
        # Get weather for this mine+year
        w_year = weather[(weather.mine_id == mine) & (weather.year == year)]
        
        if len(w_year) == 0:
            print(f"  WARNING: No weather data for {mine}/{year}, skipping.")
            continue
        
        for _, w_row in w_year.iterrows():
            month = w_row['month']
            rainfall = w_row['rainfall_mm']
            temp_max = w_row['temp_max']
            temp_min = w_row['temp_min']
            temp_mean = w_row['temp_mean']
            rainy_days = w_row['rainy_days']
            
            # Weather penalty
            weather_factor = compute_weather_penalty(rainfall, temp_max)
            
            # Derived production (NOT real observed monthly production)
            noise = np.random.normal(0, CONFIG["production_noise_std_pct"])
            derived_tpd = baseline_tpd * weather_factor * (1 + noise)
            derived_tpd = max(derived_tpd, baseline_tpd * 0.40)  # Floor at 40%
            
            # Operational features (all DERIVED/ASSUMED)
            equip_avail, haul_road, blasting, rain_intensity, high_rain = \
                compute_operational_features(rainfall, temp_max)
            
            # Planned production = baseline (no weather adjustment)
            planned_tpd = baseline_tpd
            
            rows.append({
                # ── REAL: directly from source files ──
                "mine_id": mine,
                "year": int(year),
                "month": int(month),
                "baseline_tpd__REAL": round(baseline_tpd, 1),
                "annual_production_tonnes__REAL": int(annual_tonnes),
                "mn_grade_avg_pct__REAL": mn_grade,
                "rainfall_mm__REAL": round(rainfall, 1),
                "rainy_days__REAL": int(rainy_days),
                "temp_max__REAL": round(temp_max, 1),
                "temp_min__REAL": round(temp_min, 1),
                "temp_mean__REAL": round(temp_mean, 2),
                
                # ── DERIVED: computed from real data + assumptions ──
                "planned_production_tpd__DERIVED": round(planned_tpd, 1),
                "derived_actual_production_tpd__DERIVED": round(derived_tpd, 1),
                "weather_penalty_factor__DERIVED": round(weather_factor, 4),
                "equipment_availability_pct__DERIVED": round(equip_avail, 3),
                "haul_road_condition__DERIVED": round(haul_road, 2),
                "blasting_days__DERIVED": blasting,
                "rainfall_intensity__DERIVED": rain_intensity,
                "high_rainfall_flag__DERIVED": high_rain,
                
                # ── ASSUMED: project-defined constants ──
                "crusher_capacity_tpd__ASSUMED": crusher_cap,
                "num_dumpers__ASSUMED": fleet["num_dumpers"],
                "num_shovels__ASSUMED": fleet["num_shovels"],
            })
    
    df = pd.DataFrame(rows)
    df.sort_values(['mine_id', 'year', 'month'], inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    # ── 4. Add lag features (DERIVED) ──────────────────────────────────
    print("[4/6] Adding lag features...")
    target_col = "derived_actual_production_tpd__DERIVED"
    for lag in [1, 2, 3]:
        df[f'lag_{lag}__DERIVED'] = df.groupby('mine_id')[target_col].shift(lag)
    # Backfill the first months where lags don't exist
    for lag in [1, 2, 3]:
        df[f'lag_{lag}__DERIVED'] = df.groupby('mine_id')[f'lag_{lag}__DERIVED'].bfill()
    
    # ── 5. Compute shortfall risk (DERIVED) ────────────────────────────
    ratio = df[target_col] / df["planned_production_tpd__DERIVED"]
    df['shortfall_risk__DERIVED'] = pd.cut(
        ratio, bins=[0, 0.85, 0.92, float('inf')],
        labels=['High', 'Medium', 'Low']
    )
    
    # ── 6. Save ────────────────────────────────────────────────────────
    print("[5/6] Saving dataset...")
    
    out_path = os.path.join(OUT_DIR, 'production_dataset_real.csv')
    header = (
        "# MOIL-GeoSync Production Dataset\n"
        "# Columns suffixed __REAL are direct observations from MOIL/Open-Meteo.\n"
        "# Columns suffixed __DERIVED are computed using documented assumptions.\n"
        "# Columns suffixed __ASSUMED are project-defined constants.\n"
        "# derived_actual_production_tpd is NOT observed monthly MOIL production.\n"
    )
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(header)
        df.to_csv(f, index=False)
    
    # Save config
    config_path = os.path.join(CONFIG_DIR, 'production_config.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(CONFIG, f, indent=2)
    
    # ── Report ─────────────────────────────────────────────────────────
    print("\n[6/6] FINAL DATASET REPORT")
    print("-" * 40)
    print(f"  Total records:       {len(df)}")
    print(f"  Mines:               {df.mine_id.nunique()}")
    print(f"  Date range:          {df.year.min()}/{df.month.min():02d} - {df.year.max()}/{df.month.max():02d}")
    print(f"  REAL columns:        {len([c for c in df.columns if '__REAL' in c])}")
    print(f"  DERIVED columns:     {len([c for c in df.columns if '__DERIVED' in c])}")
    print(f"  ASSUMED columns:     {len([c for c in df.columns if '__ASSUMED' in c])}")
    print()
    
    risk_counts = df['shortfall_risk__DERIVED'].value_counts()
    print(f"  Shortfall Risk Distribution:")
    for risk in ['High', 'Medium', 'Low']:
        ct = risk_counts.get(risk, 0)
        print(f"    {risk}: {ct} months ({ct/len(df)*100:.1f}%)")
    
    print(f"\n  Chronological Split:")
    train_mask = df['year'] <= CONFIG['train_end_year']
    val_mask = (df['year'] > CONFIG['train_end_year']) & (df['year'] <= CONFIG['val_end_year'])
    test_mask = df['year'] > CONFIG['val_end_year']
    print(f"    Train (<=2022): {train_mask.sum()} records")
    print(f"    Val   (2023):   {val_mask.sum()} records")
    print(f"    Test  (2024+):  {test_mask.sum()} records")
    
    print(f"\n  Saved to: {out_path}")
    print(f"  Config:   {config_path}")
    print(f"  File size: {os.path.getsize(out_path)/1024:.1f} KB")
    print("=" * 70)


if __name__ == '__main__':
    main()
