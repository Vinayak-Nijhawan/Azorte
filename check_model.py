import joblib, numpy as np, pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import roc_auc_score, auc, precision_recall_curve
import os

PROJECT_ROOT = r'c:\Users\Ayush\Desktop\sih\Azorte'
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
MODEL_DIR = os.path.join(PROJECT_ROOT, 'models')

PROSPECT_FEATURES = ['iron_oxide_index','clay_index','ndvi','rock_type_encoded','fault_distance_km',
                     'shear_zone_proximity_km','elevation_m','slope_deg','rainfall_mm','soil_moisture']

df = pd.read_csv(os.path.join(DATA_DIR, 'prospectivity_dataset.csv'), comment='#')
le = LabelEncoder()
df['rock_type_encoded'] = le.fit_transform(df['rock_type'])

X = df[PROSPECT_FEATURES]
y = df['known_occurrence']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

models = joblib.load(os.path.join(MODEL_DIR, 'prospectivity_pu_rf.joblib'))
y_proba = np.mean([m.predict_proba(X_test)[:,1] for m in models], axis=0)

roc = roc_auc_score(y_test, y_proba)
precision, recall, _ = precision_recall_curve(y_test, y_proba)
pr_auc = auc(recall, precision)

print(f'ROC-AUC: {roc:.4f}')
print(f'PR-AUC: {pr_auc:.4f}')
print(f'y_test distribution: {y_test.value_counts().to_dict()}')
print(f'Features used: {PROSPECT_FEATURES}')
print(f'Missing features: {[f for f in PROSPECT_FEATURES if f not in df.columns and f != \"rock_type_encoded\"]}')
