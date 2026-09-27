"""
MOIL-GeoSync — MineFlow Production Forecaster (CORRECTED)
==========================================================
Trains a GradientBoostingRegressor on CORRECTED 10-mine dataset.

Target: derived_actual_production_tpd (DERIVED — NOT observed MOIL production)

Splitting: Chronological (Train: <=2022, Val: 2023, Test: 2024-2025)
           NO random train_test_split to prevent future data leakage.

Baseline: Naive model that always predicts baseline_tpd (no weather adjustment).
          The ML model must demonstrate improvement over this baseline.

Corrected Mines: Balaghat, Ukwa, Tirodi, Sitapatore (MP)
                 Chikla, Dongri Buzurg, Beldongri, Kandri, Munsar, Gumgaon (MH)
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

warnings.filterwarnings('ignore')
np.random.seed(42)

# ==============================================================================
# PATHS
# ==============================================================================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODEL_DIR = os.path.join(BASE_DIR, 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

# ==============================================================================
# CONFIGURATION
# ==============================================================================
config_path = os.path.join(MODEL_DIR, 'production_config.json')
with open(config_path, 'r') as f:
    CONFIG = json.load(f)

TARGET = 'derived_actual_production_tpd__DERIVED'
BASELINE = 'baseline_tpd__REAL'

# Features for the ML model (updated for corrected dataset)
FEATURE_COLS = [
    # REAL weather observations
    'rainfall_mm__REAL',
    'rainy_days__REAL',
    'temp_max__REAL',
    'temp_mean__REAL',
    
    # DERIVED operational indicators
    'planned_production_tpd__DERIVED',
    'weather_penalty_factor__DERIVED',
    'equipment_availability_pct__DERIVED',
    'haul_road_condition__DERIVED',
    'blasting_days__DERIVED',
    'high_rainfall_flag__DERIVED',
    'lag_1__DERIVED',
    'lag_2__DERIVED',
    'lag_3__DERIVED',
    
    # REAL mine context
    'mine_share_pct__DERIVED',
    
    # Temporal & categorical features (created during training)
    'month',
    'mine_encoded',
    'state_encoded',
    'mine_type_encoded',
]


def main():
    print("=" * 70)
    print("MOIL-GeoSync — MineFlow Production Forecaster (CORRECTED)")
    print("10 Real MOIL Mines | Verified Production Totals")
    print("=" * 70)
    
    # ── 1. Load Data ───────────────────────────────────────────────────
    print("\n[1/7] Loading corrected production dataset...")
    df = pd.read_csv(os.path.join(DATA_DIR, 'production_dataset_real.csv'), comment='#')
    print(f"  Loaded {len(df)} records, {df.mine_id.nunique()} mines")
    print(f"  Mines: {sorted(df.mine_id.unique())}")
    
    # ── 2. Feature Engineering ─────────────────────────────────────────
    print("\n[2/7] Feature engineering...")
    
    # Encode mine_id
    le_mine = LabelEncoder()
    df['mine_encoded'] = le_mine.fit_transform(df['mine_id'])
    print(f"  Mine encoding: {dict(zip(le_mine.classes_, le_mine.transform(le_mine.classes_)))}")
    
    # Encode state
    le_state = LabelEncoder()
    df['state_encoded'] = le_state.fit_transform(df['state__REAL'])
    print(f"  State encoding: {dict(zip(le_state.classes_, le_state.transform(le_state.classes_)))}")
    
    # Encode mine type
    le_type = LabelEncoder()
    df['mine_type_encoded'] = le_type.fit_transform(df['mine_type__REAL'])
    print(f"  Mine type encoding: {dict(zip(le_type.classes_, le_type.transform(le_type.classes_)))}")
    
    # Verify all feature columns exist
    missing_cols = [c for c in FEATURE_COLS if c not in df.columns]
    if missing_cols:
        print(f"  ERROR: Missing columns: {missing_cols}")
        return
    print(f"  All {len(FEATURE_COLS)} features available.")
    
    # ── 3. Chronological Split ─────────────────────────────────────────
    print("\n[3/7] Chronological splitting (NO random split)...")
    
    train_mask = df['year'] <= CONFIG['train_end_year']
    val_mask = (df['year'] > CONFIG['train_end_year']) & (df['year'] <= CONFIG['val_end_year'])
    test_mask = df['year'] > CONFIG['val_end_year']
    
    X_train = df.loc[train_mask, FEATURE_COLS]
    y_train = df.loc[train_mask, TARGET]
    
    X_val = df.loc[val_mask, FEATURE_COLS]
    y_val = df.loc[val_mask, TARGET]
    
    X_test = df.loc[test_mask, FEATURE_COLS]
    y_test = df.loc[test_mask, TARGET]
    
    baseline_val = df.loc[val_mask, BASELINE]
    baseline_test = df.loc[test_mask, BASELINE]
    
    print(f"  Train: {len(X_train)} records (years <= {CONFIG['train_end_year']})")
    print(f"  Val:   {len(X_val)} records (year = {CONFIG['val_end_year']})")
    print(f"  Test:  {len(X_test)} records (years > {CONFIG['val_end_year']})")
    
    # ── 4. Train Model ─────────────────────────────────────────────────
    print("\n[4/7] Training GradientBoostingRegressor...")
    
    model = GradientBoostingRegressor(
        n_estimators=100,
        max_depth=2,
        learning_rate=0.05,
        subsample=1.0,
        min_samples_split=5,
        min_samples_leaf=20,
        random_state=42,
    )
    
    model.fit(X_train, y_train)
    print("  Training complete.")
    
    # ── 5. Evaluate ────────────────────────────────────────────────────
    print("\n[5/7] Evaluation...")
    
    metrics = {}
    
    for split_name, X, y, baseline in [
        ("Validation", X_val, y_val, baseline_val),
        ("Test", X_test, y_test, baseline_test),
    ]:
        y_pred = model.predict(X)
        
        mae_ml = mean_absolute_error(y, y_pred)
        rmse_ml = np.sqrt(mean_squared_error(y, y_pred))
        r2_ml = r2_score(y, y_pred)
        
        mae_base = mean_absolute_error(y, baseline)
        rmse_base = np.sqrt(mean_squared_error(y, baseline))
        r2_base = r2_score(y, baseline)
        
        improvement_mae = (1 - mae_ml / mae_base) * 100 if mae_base > 0 else 0
        
        print(f"\n  --- {split_name} Set ---")
        print(f"  {'Metric':<12} {'ML Model':>12} {'Baseline':>12} {'Improvement':>14}")
        print(f"  {'-'*52}")
        print(f"  {'MAE':<12} {mae_ml:>12.2f} {mae_base:>12.2f} {improvement_mae:>+13.1f}%")
        print(f"  {'RMSE':<12} {rmse_ml:>12.2f} {rmse_base:>12.2f}")
        print(f"  {'R2':<12} {r2_ml:>12.4f} {r2_base:>12.4f}")
        
        metrics[split_name.lower()] = {
            "ml_mae": round(mae_ml, 2),
            "ml_rmse": round(rmse_ml, 2),
            "ml_r2": round(r2_ml, 4),
            "baseline_mae": round(mae_base, 2),
            "baseline_rmse": round(rmse_base, 2),
            "baseline_r2": round(r2_base, 4),
            "improvement_mae_pct": round(improvement_mae, 1),
        }
    
    # Feature importance
    print("\n  Feature Importance (Top 10):")
    feat_imp = sorted(
        zip(FEATURE_COLS, model.feature_importances_),
        key=lambda x: x[1], reverse=True
    )
    for name, imp in feat_imp[:10]:
        bar = '#' * int(imp * 50)
        print(f"    {name:<45} {imp:.4f} {bar}")
    
    # ── 6. Save Model & Metrics ────────────────────────────────────────
    print("\n[6/7] Saving model and metrics...")
    
    model_path = os.path.join(MODEL_DIR, 'production_gb.joblib')
    joblib.dump(model, model_path)
    
    # Save encoders
    encoder_path = os.path.join(MODEL_DIR, 'production_preprocessor.joblib')
    joblib.dump({
        'mine_encoder': le_mine,
        'state_encoder': le_state,
        'type_encoder': le_type,
        'feature_cols': FEATURE_COLS,
        'target': TARGET,
        'baseline': BASELINE,
    }, encoder_path)
    
    # Save metrics
    metrics_report = {
        "model": "GradientBoostingRegressor",
        "target": TARGET,
        "target_note": "DERIVED proxy target from real MOIL annual totals + weather penalty.",
        "dataset_note": "CORRECTED: 10 real MOIL mines, verified production totals.",
        "splitting": f"Chronological (Train<={CONFIG['train_end_year']}, Val={CONFIG['val_end_year']}, Test={CONFIG['val_end_year']+1}+)",
        "n_estimators": 200,
        "features": FEATURE_COLS,
        "feature_importance": {name: round(imp, 4) for name, imp in feat_imp},
        "metrics": metrics,
        "baseline_model": "Naive: always predict baseline_tpd (annual avg, no weather)",
        "mines": sorted(le_mine.classes_.tolist()),
    }
    
    metrics_path = os.path.join(DATA_DIR, 'model_metrics.json')
    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump(metrics_report, f, indent=2)
    
    print(f"  Model:        {model_path}")
    print(f"  Preprocessor: {encoder_path}")
    print(f"  Metrics:      {metrics_path}")
    
    # ── 7. Generate Scenario-Based Forecasts ───────────────────────────
    print("\n[7/7] Generating scenario-based forecasts for 2026...")
    
    scenarios = {
        "normal_weather": {"rainfall_mm": 80, "temp_max": 35, "rainy_days": 5},
        "high_rainfall": {"rainfall_mm": 400, "temp_max": 33, "rainy_days": 22},
        "low_rainfall":  {"rainfall_mm": 15, "temp_max": 38, "rainy_days": 1},
    }
    
    forecast_rows = []
    for mine in df.mine_id.unique():
        mine_latest = df[df.mine_id == mine].tail(3)
        baseline_tpd = mine_latest['baseline_tpd__REAL'].iloc[-1]
        mine_enc = le_mine.transform([mine])[0]
        mine_state = mine_latest['state__REAL'].iloc[-1]
        mine_type = mine_latest['mine_type__REAL'].iloc[-1]
        state_enc = le_state.transform([mine_state])[0]
        type_enc = le_type.transform([mine_type])[0]
        mine_share = mine_latest['mine_share_pct__DERIVED'].iloc[-1]
        
        for scenario_name, scenario_weather in scenarios.items():
            lag_values = mine_latest[TARGET].tolist()
            while len(lag_values) < 3:
                lag_values.insert(0, baseline_tpd)

            for month in range(1, 13):
                rain = scenario_weather["rainfall_mm"]
                temp = scenario_weather["temp_max"]
                rainy_d = scenario_weather["rainy_days"]
                
                if scenario_name == "normal_weather":
                    if month == 6:
                        rain, rainy_d, temp = 180, 12, 34
                    elif month == 7:
                        rain, rainy_d, temp = 480, 22, 30
                    elif month == 8:
                        rain, rainy_d, temp = 380, 18, 30
                    elif month == 9:
                        rain, rainy_d, temp = 220, 14, 32
                    elif month in [3, 4, 5]:
                        temp = 42
                        rain = 20
                        rainy_d = 1
                
                wp = max(1.0 - max(0, rain - 100) / 500 * 0.30, 0.50)
                ea = max(0.92 - (rain / 500 * 0.15), 0.60)
                hr = max(4.5 - (rain / 100 * 0.8), 1.0)
                bl = max(int(22 - (rain / 100 * 3)), 5)
                hrf = 1 if rain > 200 else 0
                
                features = {
                    'rainfall_mm__REAL': rain,
                    'rainy_days__REAL': rainy_d,
                    'temp_max__REAL': temp,
                    'temp_mean__REAL': temp - 8,
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
                    'month': month,
                    'mine_encoded': mine_enc,
                    'state_encoded': state_enc,
                    'mine_type_encoded': type_enc,
                }
                
                X_pred = pd.DataFrame([features])[FEATURE_COLS]
                predicted_tpd = model.predict(X_pred)[0]
                
                lag_values.append(predicted_tpd)
                lag_values = lag_values[-3:]
                
                ratio = predicted_tpd / baseline_tpd
                if ratio < 0.85:
                    risk = "High"
                elif ratio < 0.92:
                    risk = "Medium"
                else:
                    risk = "Low"
                
                forecast_rows.append({
                    "mine_id": mine,
                    "year": 2026,
                    "month": month,
                    "scenario": scenario_name,
                    "baseline_tpd": round(baseline_tpd, 1),
                    "predicted_production_tpd": round(predicted_tpd, 1),
                    "shortfall_risk": risk,
                    "rainfall_mm_scenario": rain,
                    "weather_penalty": round(wp, 4),
                    "data_type": "SCENARIO_FORECAST",
                })
    
    forecast_df = pd.DataFrame(forecast_rows)
    forecast_path = os.path.join(DATA_DIR, 'production_forecast_real.csv')
    header = (
        "# MOIL-GeoSync Production Forecast (CORRECTED — Scenario-Based)\n"
        "# 10 Real MOIL Mines | Verified Production Baselines\n"
        "# These are ML MODEL PREDICTIONS under assumed weather scenarios.\n"
        "# Scenarios: normal_weather, high_rainfall, low_rainfall\n"
    )
    with open(forecast_path, 'w', encoding='utf-8') as f:
        f.write(header)
        forecast_df.to_csv(f, index=False)
    
    print(f"  Generated {len(forecast_df)} forecast records")
    print(f"  Mines: {forecast_df.mine_id.nunique()}")
    print(f"  Scenarios: {forecast_df.scenario.unique().tolist()}")
    print(f"  Saved to: {forecast_path}")
    
    print("\n" + "=" * 70)
    print("TRAINING COMPLETE (CORRECTED MODEL)")
    print("=" * 70)
    print(f"\nMines used: {sorted(le_mine.classes_.tolist())}")
    print(f"Data source: MOIL Annual Report 2025-26 + BSE filings")
    print(f"\nIMPORTANT DISCLAIMER:")
    print(f"  The target variable ({TARGET}) is a DERIVED proxy.")
    print(f"  Mine-wise splits are estimated from EC capacity + real anchors.")
    print(f"  Company-level totals (FY2018-FY2026) are VERIFIED from MOIL filings.")
    print("=" * 70)


if __name__ == '__main__':
    main()
