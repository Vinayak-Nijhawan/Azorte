import os
import sys
import json
import logging
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import ListedColormap

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold
from sklearn.metrics import average_precision_score
from sklearn.preprocessing import OrdinalEncoder
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import joblib

# Suppress minor warnings for clean output
warnings.filterwarnings("ignore", category=UserWarning)

# ==============================================================================
# CONFIGURATION
# ==============================================================================
class Config:
    # Features
    SPECTRAL_FEATURES = ['iron_oxide_index', 'clay_index', 'ndvi']
    TOPO_FEATURES = ['elevation_m', 'slope_deg']
    GEO_FEATURES = ['rock_type_encoded', 'fault_distance_km', 'shear_zone_proximity_km']
    ENV_FEATURES = ['rainfall_mm', 'soil_moisture']
    
    EXPECTED_FEATURES = SPECTRAL_FEATURES + TOPO_FEATURES + GEO_FEATURES + ENV_FEATURES
    TARGET_COL = 'known_occurrence'
    COORD_COLS = ['latitude', 'longitude']
    
    # PU Bagging Hyperparameters
    RANDOM_SEED = 42
    N_PU_BAGS = 50
    U_SAMPLE_RATIO = 1.0  # Sample U at 1:1 ratio with P for each bag
    
    # Random Forest Hyperparameters
    RF_PARAMS = {
        'n_estimators': 150,
        'max_depth': 12,
        'min_samples_leaf': 4,
        'max_features': 'sqrt',
        'class_weight': 'balanced',
        'n_jobs': -1
    }
    
    # Spatial Blocking
    SPATIAL_BLOCK_SIZE = 0.1  # degrees
    N_CV_FOLDS = 5
    
    # Domain Rules
    NDVI_THRESHOLD = 0.70
    NDVI_PENALTY = 0.70  # 30% reduction (multiplier = 0.70)
    
    # Prospectivity Classes
    THRESH_HIGH = 0.80
    THRESH_MED = 0.40
    
    # Paths (relative to script execution)
    BASE_DIR = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    OUTPUT_DIR = BASE_DIR / "pipeline_outputs"
    MODEL_DIR = OUTPUT_DIR / "model"
    METRICS_DIR = OUTPUT_DIR / "metrics"
    PRED_DIR = OUTPUT_DIR / "predictions"
    FIG_DIR = OUTPUT_DIR / "figures"

# Setup directories
for d in [Config.OUTPUT_DIR, Config.MODEL_DIR, Config.METRICS_DIR, Config.PRED_DIR, Config.FIG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(Config.OUTPUT_DIR / "pipeline.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. DATA VALIDATION
# ==============================================================================
class DataValidator:
    @staticmethod
    def validate(df):
        logger.info("--- Data Validation Started ---")
        
        # 1 & 2. Shape & Types
        logger.info(f"Dataset shape: {df.shape}")
        
        # 3. Check expected features
        missing_feats = [f for f in Config.EXPECTED_FEATURES if f not in df.columns]
        if missing_feats:
            logger.error(f"Missing required features: {missing_feats}")
            raise ValueError(f"Missing features: {missing_feats}")
        
        # 4. Check coords and target
        for col in Config.COORD_COLS + [Config.TARGET_COL]:
            if col not in df.columns:
                logger.error(f"Missing required column: {col}")
                raise ValueError(f"Missing column: {col}")
                
        # 5. Check missing values
        null_counts = df[Config.EXPECTED_FEATURES].isnull().sum()
        if null_counts.sum() > 0:
            logger.warning("Missing values detected in predictive features (will be imputed):")
            for k, v in null_counts[null_counts > 0].items():
                logger.warning(f"  - {k}: {v} missing")
                
        # 6. Check duplicates
        dupes = df.duplicated(subset=Config.COORD_COLS).sum()
        if dupes > 0:
            logger.warning(f"Found {dupes} duplicate spatial coordinates (Leakage risk!). Dropping duplicates...")
            df.drop_duplicates(subset=Config.COORD_COLS, inplace=True)
            
        # 7. Check infinite values
        inf_counts = np.isinf(df[Config.EXPECTED_FEATURES].select_dtypes(include=np.number)).sum()
        if inf_counts.sum() > 0:
            logger.error("Infinite values detected. Pipeline cannot proceed.")
            raise ValueError("Infinite values found.")
            
        # 9 & 10. Stats & Class counts
        pos_count = (df[Config.TARGET_COL] == 1).sum()
        u_count = (df[Config.TARGET_COL] == 0).sum()
        logger.info(f"Target distribution: {pos_count} Known Positives (1), {u_count} Unlabeled (0)")
        
        logger.info("--- Data Validation Passed ---")
        return df

# ==============================================================================
# 2. SPATIAL BLOCKING
# ==============================================================================
def create_spatial_blocks(df, block_size=Config.SPATIAL_BLOCK_SIZE):
    logger.info(f"Creating spatial blocks of {block_size} degrees...")
    lat_block = np.floor(df['latitude'] / block_size).astype(int).astype(str)
    lon_block = np.floor(df['longitude'] / block_size).astype(int).astype(str)
    df['block_id'] = lat_block + "_" + lon_block
    
    n_blocks = df['block_id'].nunique()
    logger.info(f"Generated {n_blocks} unique spatial blocks.")
    return df

# ==============================================================================
# 3. PREPROCESSING
# ==============================================================================
def build_preprocessor(df):
    """Builds preprocessing pipeline ensuring no data leakage."""
    # Identify types
    categorical = ['rock_type_encoded'] if 'rock_type_encoded' in Config.EXPECTED_FEATURES else []
    numerical = [f for f in Config.EXPECTED_FEATURES if f not in categorical]
    
    # Numerical: Impute only, NO scaling (Random Forest doesn't need it, preserves units)
    num_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='median'))
    ])
    
    # Categorical: Impute + OrdinalEncode
    cat_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('encoder', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1))
    ])
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', num_pipeline, numerical),
            ('cat', cat_pipeline, categorical)
        ],
        remainder='passthrough'
    )
    return preprocessor

# ==============================================================================
# 4. PU-BAGGING ENSEMBLE
# ==============================================================================
class PUBaggingEnsemble:
    def __init__(self, config=Config):
        self.n_bags = config.N_PU_BAGS
        self.rf_params = config.RF_PARAMS
        self.u_ratio = config.U_SAMPLE_RATIO
        self.models = []
        self.seed = config.RANDOM_SEED
        
    def fit(self, X, y):
        self.models = []
        P_idx = np.where(y == 1)[0]
        U_idx = np.where(y == 0)[0]
        
        np.random.seed(self.seed)
        n_u_sample = int(len(P_idx) * self.u_ratio)
        
        for i in range(self.n_bags):
            # 1. Sample P (All positives or bootstrap, here we use all)
            # 2. Sample U as temporary negatives
            U_sampled = np.random.choice(U_idx, size=n_u_sample, replace=False)
            
            bag_idx = np.concatenate([P_idx, U_sampled])
            X_bag = X[bag_idx]
            y_bag = np.concatenate([np.ones(len(P_idx)), np.zeros(len(U_sampled))])
            
            # 3. Train RF
            rf = RandomForestClassifier(**self.rf_params, random_state=self.seed + i)
            rf.fit(X_bag, y_bag)
            self.models.append(rf)
            
    def predict_proba_all(self, X):
        """Returns predictions from all bags."""
        preds = np.zeros((X.shape[0], self.n_bags))
        for i, model in enumerate(self.models):
            preds[:, i] = model.predict_proba(X)[:, 1]
        return preds
        
    def predict_proba(self, X):
        """Returns mean prediction across all bags."""
        return np.mean(self.predict_proba_all(X), axis=1)

# ==============================================================================
# 5. POST-PROCESSING (DOMAIN RULES & CLASSIFICATION)
# ==============================================================================
def apply_domain_rules(df):
    """Applies NDVI penalty and creates classes/confidence levels."""
    
    # Rule 1: NDVI Penalty
    dense_veg_mask = df['ndvi'] > Config.NDVI_THRESHOLD
    
    df['adjusted_score'] = np.where(
        dense_veg_mask,
        df['raw_score'] * Config.NDVI_PENALTY,
        df['raw_score']
    )
    
    # Classification
    conditions = [
        df['adjusted_score'] >= Config.THRESH_HIGH,
        (df['adjusted_score'] >= Config.THRESH_MED) & (df['adjusted_score'] < Config.THRESH_HIGH),
        df['adjusted_score'] < Config.THRESH_MED
    ]
    choices = ['High', 'Medium', 'Low']
    df['prospectivity_class'] = np.select(conditions, choices, default='Low')
    
    # Confidence Estimation
    # High standard deviation implies low model agreement
    std_thresh = df['prediction_std'].quantile(0.75)
    
    conf_conditions = [
        dense_veg_mask,  # Domain override
        df['prediction_std'] > std_thresh,
        df['prediction_std'] <= std_thresh
    ]
    conf_choices = [
        'LOW (Dense Vegetation)',
        'MEDIUM (Model Uncertainty)',
        'HIGH (Model Agreement)'
    ]
    df['confidence'] = np.select(conf_conditions, conf_choices, default='MEDIUM')
    
    return df

# ==============================================================================
# 6. SPATIAL CV & EVALUATION
# ==============================================================================
def evaluate_spatial_cv(df):
    logger.info("--- Starting Spatial Block Cross-Validation ---")
    
    gkf = GroupKFold(n_splits=Config.N_CV_FOLDS)
    X_raw = df[Config.EXPECTED_FEATURES].copy()
    y = df[Config.TARGET_COL].values
    groups = df['block_id'].values
    
    cv_metrics = []
    out_of_fold_preds = np.zeros(len(df))
    out_of_fold_std = np.zeros(len(df))
    
    for fold, (train_idx, val_idx) in enumerate(gkf.split(X_raw, y, groups)):
        X_train, y_train = X_raw.iloc[train_idx], y[train_idx]
        X_val, y_val = X_raw.iloc[val_idx], y[val_idx]
        
        # Leakage Prevention: Fit preprocessor ONLY on train fold
        preprocessor = build_preprocessor(X_train)
        X_train_proc = preprocessor.fit_transform(X_train)
        X_val_proc = preprocessor.transform(X_val)
        
        # Train PU Ensemble
        pu_model = PUBaggingEnsemble()
        pu_model.fit(X_train_proc, y_train)
        
        # Predict
        val_preds_all = pu_model.predict_proba_all(X_val_proc)
        val_preds_mean = np.mean(val_preds_all, axis=1)
        val_preds_std = np.std(val_preds_all, axis=1)
        
        out_of_fold_preds[val_idx] = val_preds_mean
        out_of_fold_std[val_idx] = val_preds_std
        
        # Evaluation on Fold (PU-Aware)
        p_val_idx = np.where(y_val == 1)[0]
        
        if len(p_val_idx) > 0:
            recall_at_05 = np.mean(val_preds_mean[p_val_idx] >= 0.5)
            pr_auc = average_precision_score(y_val, val_preds_mean)
        else:
            recall_at_05 = np.nan
            pr_auc = np.nan
            
        cv_metrics.append({
            'fold': fold + 1,
            'recall_known_positives': recall_at_05,
            'pr_auc_relative': pr_auc,
            'n_train': len(train_idx),
            'n_val': len(val_idx),
            'n_val_positives': len(p_val_idx)
        })
        logger.info(f"Fold {fold+1} | Val Positives: {len(p_val_idx)} | Recall@0.5: {recall_at_05:.3f}")

    metrics_df = pd.DataFrame(cv_metrics)
    metrics_df.to_csv(Config.METRICS_DIR / "spatial_cv_metrics.csv", index=False)
    
    df['raw_score'] = out_of_fold_preds
    df['prediction_std'] = out_of_fold_std
    
    return df, metrics_df

# ==============================================================================
# 7. FEATURE IMPORTANCE & VISUALIZATION
# ==============================================================================
def calculate_feature_importance(preprocessor, pu_model):
    logger.info("Calculating Feature Importance...")
    
    # Get feature names
    cat_feats = ['rock_type_encoded'] if 'rock_type_encoded' in Config.EXPECTED_FEATURES else []
    num_feats = [f for f in Config.EXPECTED_FEATURES if f not in cat_feats]
    feature_names = num_feats + cat_feats
    
    # Average feature importance across all RF bags
    importances = np.mean([model.feature_importances_ for model in pu_model.models], axis=0)
    
    feat_imp_df = pd.DataFrame({
        'Feature': feature_names,
        'Importance': importances
    }).sort_values('Importance', ascending=False)
    
    # Plot
    plt.figure(figsize=(10, 6))
    sns.barplot(x='Importance', y='Feature', data=feat_imp_df, palette='viridis')
    plt.title("PU Bagging Feature Importance (Model Reliance, Not Geological Causation)")
    plt.tight_layout()
    plt.savefig(Config.FIG_DIR / "feature_importance.png")
    plt.close()
    
    return feat_imp_df

def generate_maps(df):
    logger.info("Generating Maps...")
    
    # Map 1: Prospectivity Map (LOW=red, MEDIUM=orange, HIGH=green)
    color_map = {'Low': 'red', 'Medium': 'orange', 'High': 'green'}
    
    plt.figure(figsize=(12, 10))
    sns.scatterplot(
        data=df, x='longitude', y='latitude', 
        hue='prospectivity_class', 
        palette=color_map, 
        s=10, alpha=0.6, edgecolor=None
    )
    
    # Overlay Known Positives
    pos_df = df[df[Config.TARGET_COL] == 1]
    plt.scatter(pos_df['longitude'], pos_df['latitude'], 
                c='blue', marker='*', s=150, edgecolor='white', label='Known Occurrence')
    
    plt.title("Mineral Prospectivity Map (Domain Adjusted)")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.legend()
    plt.tight_layout()
    plt.savefig(Config.FIG_DIR / "prospectivity_map.png", dpi=300)
    plt.close()
    
    # Map 2: Uncertainty Map
    plt.figure(figsize=(12, 10))
    sc = plt.scatter(df['longitude'], df['latitude'], c=df['prediction_std'], cmap='plasma', s=10)
    plt.colorbar(sc, label='Prediction Std Dev (Uncertainty)')
    plt.title("Ensemble Prediction Uncertainty Map")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.tight_layout()
    plt.savefig(Config.FIG_DIR / "uncertainty_map.png", dpi=300)
    plt.close()

# ==============================================================================
# 8. FINAL REPORT GENERATOR
# ==============================================================================
def generate_final_report(df, metrics_df, feat_imp_df):
    report = f"""
==================================================
MOIL-GEOSYNC FINAL PIPELINE REPORT
==================================================
Date generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

1. DATASET SUMMARY
-------------------
Total samples: {len(df)}
Known positives (Label=1): {(df[Config.TARGET_COL] == 1).sum()}
Unlabeled samples (Label=0): {(df[Config.TARGET_COL] == 0).sum()}
Spatial blocks created: {df['block_id'].nunique()}

2. FEATURE SUMMARY
-------------------
Spectral (Sentinel-2): {', '.join(Config.SPECTRAL_FEATURES)}
Topography (SRTM DEM): {', '.join(Config.TOPO_FEATURES)}
Geology (GSI-Simulated): {', '.join(Config.GEO_FEATURES)}
Environment (APIs): {', '.join(Config.ENV_FEATURES)}

3. METHODOLOGY
-------------------
Algorithm: Positive-Unlabeled (PU) Bagging Random Forest
Number of PU Bags: {Config.N_PU_BAGS}
Unlabeled Sampling Ratio: {Config.U_SAMPLE_RATIO}:1
Spatial CV: GroupKFold ({Config.N_CV_FOLDS} Folds) block size {Config.SPATIAL_BLOCK_SIZE} deg

4. EVALUATION (Spatial CV)
-------------------
Mean Recall on Known Positives: {metrics_df['recall_known_positives'].mean():.3f} +/- {metrics_df['recall_known_positives'].std():.3f}
Mean PR-AUC (Relative to U): {metrics_df['pr_auc_relative'].mean():.3f} +/- {metrics_df['pr_auc_relative'].std():.3f}

* Note: Ordinary binary accuracy and ROC-AUC are excluded as U samples are not confirmed negatives.

5. FEATURE IMPORTANCE (Top 5)
-------------------
{feat_imp_df.head(5).to_string(index=False)}
* Note: Feature importance indicates model reliance, NOT geological causation.

6. DOMAIN ADJUSTMENT (NDVI)
-------------------
Points penalized due to dense vegetation (NDVI > {Config.NDVI_THRESHOLD}): {(df['ndvi'] > Config.NDVI_THRESHOLD).sum()}
Penalty factor: {Config.NDVI_PENALTY}

7. PROSPECTIVITY DISTRIBUTION
-------------------
HIGH (>= {Config.THRESH_HIGH}): {(df['prospectivity_class'] == 'High').sum()} points
MEDIUM ({Config.THRESH_MED} - {Config.THRESH_HIGH}): {(df['prospectivity_class'] == 'Medium').sum()} points
LOW (< {Config.THRESH_MED}): {(df['prospectivity_class'] == 'Low').sum()} points

8. REPRODUCIBILITY
-------------------
Random Seed: {Config.RANDOM_SEED}
Outputs saved to: {Config.OUTPUT_DIR.resolve()}
==================================================
    """
    
    logger.info("\n" + report)
    with open(Config.OUTPUT_DIR / "FINAL_REPORT.txt", "w", encoding='utf-8') as f:
        f.write(report)
        
    # Architecture Diagram
    diagram = """
    Data Sources (Spectral, Topo, GSI-Simulated, Weather)
        |
    10 Feature Dataset
        |
    Spatial Blocking (~0.1 deg)
        |
    PU-Bagging Random Forest (P vs U sampling)
        |
    Raw Prospectivity Score
        |
    NDVI Domain Adjustment (Penalty if > 0.70)
        |
    Uncertainty Estimation (Ensemble Std Dev)
        |
    High / Medium / Low Classes
        |
    Prospectivity Map + Dashboard
    """
    with open(Config.OUTPUT_DIR / "ARCHITECTURE.txt", "w", encoding='utf-8') as f:
        f.write(diagram)

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
def main(data_path):
    logger.info("Initializing MOIL-GeoSync PU Learning Pipeline...")
    
    if not os.path.exists(data_path):
        logger.error(f"Data not found at {data_path}. Please provide correct path.")
        return
        
    df = pd.read_csv(data_path, comment='#')
    
    # Column mapping: adapt dataset column names to pipeline schema
    if 'mn_occurrence' in df.columns and 'known_occurrence' not in df.columns:
        df.rename(columns={'mn_occurrence': 'known_occurrence'}, inplace=True)
        logger.info("Renamed 'mn_occurrence' -> 'known_occurrence'")
    
    # Encode rock_type (text) → rock_type_encoded (numeric) if needed
    if 'rock_type' in df.columns and 'rock_type_encoded' not in df.columns:
        from sklearn.preprocessing import LabelEncoder
        le = LabelEncoder()
        df['rock_type_encoded'] = le.fit_transform(df['rock_type'].astype(str))
        logger.info(f"Encoded 'rock_type' -> 'rock_type_encoded': {dict(zip(le.classes_, le.transform(le.classes_)))}")
    
    # 1. Validate (Handles shape, missing, duplicates, inf)
    df = DataValidator.validate(df)
    
    # 2. Spatial Blocking
    df = create_spatial_blocks(df)
    
    # 3 & 4 & 6. Spatial CV and Model Evaluation
    df, metrics_df = evaluate_spatial_cv(df)
    
    # 5. Apply Domain Rules & Uncertainty
    df = apply_domain_rules(df)
    
    # Final Model Training (on ALL data for production saving)
    logger.info("Training Final Full Model on all data...")
    preprocessor = build_preprocessor(df)
    X_full = preprocessor.fit_transform(df[Config.EXPECTED_FEATURES])
    y_full = df[Config.TARGET_COL].values
    
    final_model = PUBaggingEnsemble()
    final_model.fit(X_full, y_full)
    
    # Calculate feature importance
    feat_imp = calculate_feature_importance(preprocessor, final_model)
    
    # 7. Outputs & Artifacts
    logger.info("Saving models and predictions...")
    
    # Save preprocessing pipeline and final model
    joblib.dump(preprocessor, Config.MODEL_DIR / "preprocessor.joblib")
    joblib.dump(final_model, Config.MODEL_DIR / "pu_bagging_model.joblib")
    
    # Save configuration
    config_dict = {k: v for k, v in Config.__dict__.items() if not k.startswith('__') and not callable(v)}
    config_dict = {k: str(v) for k, v in config_dict.items()} # Ensure JSON serializable
    with open(Config.OUTPUT_DIR / "config.json", "w") as f:
        json.dump(config_dict, f, indent=4)
        
    # Format final export columns
    export_cols = Config.COORD_COLS + Config.EXPECTED_FEATURES + [
        'raw_score', 'prediction_std', 'adjusted_score', 'prospectivity_class', 'confidence'
    ]
    df[export_cols].to_csv(Config.PRED_DIR / "final_predictions.csv", index=False)
    
    # Generate Maps
    generate_maps(df)
    
    # Final Report
    generate_final_report(df, metrics_df, feat_imp)
    
    logger.info("Pipeline Execution Completed Successfully!")
    logger.info(f"All outputs saved to: {Config.OUTPUT_DIR.resolve()}")

if __name__ == "__main__":
    # Example execution argument mapping
    if len(sys.argv) > 1:
        target_csv = sys.argv[1]
    else:
        target_csv = "data/prospectivity_dataset.csv"  # Fallback Default
        logger.info(f"No dataset provided in args. Defaulting to {target_csv}")
        
    main(target_csv)
