import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import GroupKFold
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
import joblib

# Set global random state for reproducibility
np.random.seed(42)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODELS_DIR = os.path.join(BASE_DIR, 'models')

# Create models dir if not exists
os.makedirs(MODELS_DIR, exist_ok=True)

# Load data
prospectivity_dataset_path = os.path.join(DATA_DIR, 'prospectivity_dataset.csv')
prospectivity_grid_path = os.path.join(DATA_DIR, 'prospectivity_grid.csv')

print(f"Loading data from {prospectivity_dataset_path}...")
df = pd.read_csv(prospectivity_dataset_path)

# Print initial verification
print("Dataset Head:")
print(df.head())
print(f"Total rows: {len(df)}")

# SYNTHETIC DATA VERIFICATION - Label encoding for rock_type
le = LabelEncoder()
df['rock_type_encoded'] = le.fit_transform(df['rock_type'])

features = ['iron_oxide_index', 'clay_index', 'ndvi', 'rock_type_encoded', 
            'fault_distance_km', 'shear_zone_proximity_km', 'elevation_m', 
            'slope_deg', 'rainfall_mm', 'soil_moisture']
target = 'mn_occurrence'

# Spatial Block Cross-Validation
# Block IDs based on 0.1 degree lat/lon quantization
df['lat_block'] = np.floor(df['latitude'] / 0.1)
df['lon_block'] = np.floor(df['longitude'] / 0.1)
df['block_id'] = df['lat_block'].astype(str) + '_' + df['lon_block'].astype(str)

gkf = GroupKFold(n_splits=5)

class PUBaggingRF:
    def __init__(self, k_iterations=30, n_estimators=100, random_state=42):
        self.k_iterations = k_iterations
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.models = []
    
    def fit(self, X, y):
        self.models = []
        pos_mask = (y == 1)
        unl_mask = (y == 0)
        
        X_pos = X[pos_mask]
        y_pos = y[pos_mask]
        
        X_unl = X[unl_mask]
        y_unl = y[unl_mask]
        
        n_pos = len(X_pos)
        
        for k in range(self.k_iterations):
            rng = np.random.RandomState(self.random_state + k)
            
            if len(X_unl) > 0:
                indices = rng.choice(len(X_unl), size=n_pos, replace=True)
                X_unl_sample = X_unl.iloc[indices]
                y_unl_sample = y_unl.iloc[indices]
            else:
                X_unl_sample = pd.DataFrame()
                y_unl_sample = pd.Series()
            
            if len(X_unl_sample) > 0:
                X_train_k = pd.concat([X_pos, X_unl_sample])
                y_train_k = pd.concat([y_pos, y_unl_sample])
            else:
                X_train_k = X_pos
                y_train_k = y_pos
            
            rf = RandomForestClassifier(n_estimators=self.n_estimators, random_state=self.random_state + k)
            rf.fit(X_train_k, y_train_k)
            self.models.append(rf)
            
    def predict_proba(self, X):
        probas = np.zeros(len(X))
        for model in self.models:
            probas += model.predict_proba(X)[:, 1]
        return probas / self.k_iterations
    
    def predict(self, X, threshold=0.5):
        return (self.predict_proba(X) >= threshold).astype(int)

# 5. Spatial Block Cross-Validation
print("\nRunning Spatial Block CV...")
metrics = {'precision': [], 'recall': [], 'f1': [], 'accuracy': []}

for train_idx, test_idx in gkf.split(df, groups=df['block_id']):
    train_df = df.iloc[train_idx]
    test_df = df.iloc[test_idx]
    
    X_train, y_train = train_df[features], train_df[target]
    X_test, y_test = test_df[features], test_df[target]
    
    model = PUBaggingRF(k_iterations=30, n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test, threshold=0.5)
    
    metrics['precision'].append(precision_score(y_test, y_pred, zero_division=0))
    metrics['recall'].append(recall_score(y_test, y_pred, zero_division=0))
    metrics['f1'].append(f1_score(y_test, y_pred, zero_division=0))
    metrics['accuracy'].append(accuracy_score(y_test, y_pred))

print(f"CV Precision: {np.mean(metrics['precision']):.4f}")
print(f"CV Recall: {np.mean(metrics['recall']):.4f}")
print(f"CV F1: {np.mean(metrics['f1']):.4f}")
print(f"CV Accuracy: {np.mean(metrics['accuracy']):.4f}")

# 8. Train final model on ALL data
print("\nTraining final model on all data...")
X_all = df[features]
y_all = df[target]

final_model = PUBaggingRF(k_iterations=30, n_estimators=100, random_state=42)
final_model.fit(X_all, y_all)

# 9. Save final model ensemble
model_path = os.path.join(MODELS_DIR, 'prospectivity_pu_rf.joblib')
joblib.dump(final_model.models, model_path)
print(f"Saved model to {model_path}")

# 10. Print feature importances sorted
importances = np.zeros(len(features))
for m in final_model.models:
    importances += m.feature_importances_
importances /= len(final_model.models)

feat_imp = pd.DataFrame({'feature': features, 'importance': importances}).sort_values('importance', ascending=False)
print("\nFeature Importances:")
print(feat_imp)

# Predict on Grid (Step 8 continued)
print("\nPredicting on prospectivity_grid.csv...")
if os.path.exists(prospectivity_grid_path):
    grid_df = pd.read_csv(prospectivity_grid_path)
    
    if 'rock_type' in grid_df.columns:
        grid_df['rock_type_encoded'] = grid_df['rock_type'].map(lambda s: le.transform([s])[0] if s in le.classes_ else -1)
    
    X_grid = grid_df[features].fillna(0)
    
    base_scores = final_model.predict_proba(X_grid)
    
    # 6. NDVI confidence adjustment
    adj_scores = base_scores.copy()
    ndvi_mask = grid_df['ndvi'] > 0.7
    adj_scores[ndvi_mask] = adj_scores[ndvi_mask] * (1 - 0.3)
    
    grid_df['mn_probability'] = adj_scores
    grid_df['confidence'] = np.where(ndvi_mask, 'Low (Veg)', 'High')
    
    # 7. Classify prospectivity
    def classify_score(s):
        if s >= 0.8: return 'High'
        elif s >= 0.4: return 'Medium'
        else: return 'Low'
        
    grid_df['prospectivity_class'] = grid_df['mn_probability'].apply(classify_score)
    
    grid_df.to_csv(prospectivity_grid_path, index=False)
    print("Grid predictions saved back to prospectivity_grid.csv")
    print(grid_df[['mn_probability', 'confidence', 'prospectivity_class']].head())
else:
    print(f"Warning: Grid file {prospectivity_grid_path} not found.")
