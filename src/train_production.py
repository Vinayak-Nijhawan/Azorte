import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

# Set global random state for reproducibility
np.random.seed(42)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODELS_DIR = os.path.join(BASE_DIR, 'models')

# Create models dir if not exists
os.makedirs(MODELS_DIR, exist_ok=True)

# 1. Load data
production_dataset_path = os.path.join(DATA_DIR, 'production_dataset.csv')
production_forecast_path = os.path.join(DATA_DIR, 'production_forecast.csv')

print(f"Loading data from {production_dataset_path}...")
df = pd.read_csv(production_dataset_path)

print("Dataset Head:")
print(df.head())
print(f"Total rows: {len(df)}")

# 2 & 3. Targets and Features
target = 'actual_production_tpd'
features = ['planned_production_tpd', 'rainfall_mm', 'equipment_availability_pct', 
            'blasting_days', 'haul_road_condition', 'crusher_capacity_tpd', 
            'num_dumpers', 'num_shovels', 'lag_1', 'lag_2', 'lag_3']

# Handle categorical encoding for haul_road_condition if it's string-based
if 'haul_road_condition' in df.columns and df['haul_road_condition'].dtype == object:
    mapping = {'Poor': 0, 'Fair': 1, 'Good': 2}
    df['haul_road_condition'] = df['haul_road_condition'].map(mapping).fillna(1)

X = df[features]
y = df[target]

# 4. 80/20 train/test split (random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 5. Train GradientBoostingRegressor
print("\nTraining Gradient Boosting Regressor...")
model = GradientBoostingRegressor(n_estimators=150, max_depth=5, learning_rate=0.1, random_state=42)
model.fit(X_train, y_train)

# 6. Print MAE, RMSE, R² on test set
y_pred = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

print(f"\nTest Metrics:")
print(f"MAE:  {mae:.2f}")
print(f"RMSE: {rmse:.2f}")
print(f"R²:   {r2:.4f}")

# 9. Save updated forecast CSV and model
model_path = os.path.join(MODELS_DIR, 'production_gb.joblib')
joblib.dump(model, model_path)
print(f"\nModel saved to {model_path}")

# 7. Predict on production_forecast.csv
print("\nPredicting on production_forecast.csv...")
if os.path.exists(production_forecast_path):
    forecast_df = pd.read_csv(production_forecast_path)
    
    if 'haul_road_condition' in forecast_df.columns and forecast_df['haul_road_condition'].dtype == object:
        mapping = {'Poor': 0, 'Fair': 1, 'Good': 2}
        forecast_df['haul_road_condition'] = forecast_df['haul_road_condition'].map(mapping).fillna(1)
        
    X_forecast = forecast_df[features].fillna(0)
    forecast_preds = model.predict(X_forecast)
    
    forecast_df['predicted_production_tpd'] = forecast_preds
    
    # 8. Compute shortfall_risk
    ratio = forecast_df['predicted_production_tpd'] / forecast_df['planned_production_tpd']
    
    def get_risk(r):
        if r < 0.9: return 'High'
        elif r < 0.95: return 'Medium'
        else: return 'Low'
        
    forecast_df['shortfall_risk'] = ratio.apply(get_risk)
    
    forecast_df.to_csv(production_forecast_path, index=False)
    
    print("Forecast predictions saved back to production_forecast.csv")
    
    # 10. Print forecast summary
    print("\nForecast Summary:")
    display_cols = ['date', 'planned_production_tpd', 'predicted_production_tpd', 'shortfall_risk']
    if 'date' not in forecast_df.columns:
        display_cols.remove('date')
    print(forecast_df[display_cols].head())
    
    print("\nRisk Value Counts:")
    print(forecast_df['shortfall_risk'].value_counts())
else:
    print(f"Warning: Forecast file {production_forecast_path} not found.")
