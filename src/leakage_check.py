"""
MOIL-GeoSync -- Step 3: Leakage Check
======================================
Part A: Distance-ring analysis around positive leases
Part B: Spectral ablation (re-run without iron_oxide_index, clay_index)
"""

import os
import json
import math
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely.geometry import shape, Point

# -- Paths --
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PREDICTIONS = os.path.join(BASE_DIR, "pipeline_outputs", "predictions", "final_predictions.csv")
DATASET = os.path.join(BASE_DIR, "data", "prospectivity_real_dataset.csv")
LEASE_GEOJSON = os.path.join(BASE_DIR, "newdataset", "ngdr_mn_leases.geojson")
LEASE_CSV = os.path.join(BASE_DIR, "newdataset", "ngdr_mn_positive_locations.csv")

# Approximate degrees-to-meters at this latitude (~21.5N)
DEG_TO_M = 111_320.0
COS_LAT = math.cos(math.radians(21.5))


def dist_m(lat1, lon1, lat2, lon2):
    """Approximate distance in meters (equirectangular)."""
    dlat = (lat2 - lat1) * DEG_TO_M
    dlon = (lon2 - lon1) * DEG_TO_M * COS_LAT
    return math.sqrt(dlat**2 + dlon**2)


def part_a_distance_rings():
    """
    For each positive lease, compute mean prospectivity score in rings:
    inside polygon, 0-500m outside, 500m-1km, 1-2km.
    """
    print("=" * 70)
    print("STEP 3A: Distance-Ring Leakage Analysis")
    print("=" * 70)

    # Load predictions
    preds = pd.read_csv(PREDICTIONS)
    print(f"Predictions loaded: {len(preds)} rows")
    print(f"Columns: {list(preds.columns)}")

    # Check which score column to use
    score_col = 'adjusted_score' if 'adjusted_score' in preds.columns else 'raw_score'
    print(f"Using score column: {score_col}")

    # Load lease polygons
    lease_meta = pd.read_csv(LEASE_CSV)
    lease_bbox = lease_meta[lease_meta["in_bbox"] == True]

    with open(LEASE_GEOJSON, "r", encoding="utf-8") as f:
        geojson_data = json.load(f)

    # Build lease polygon lookup
    lease_polys = {}
    for feat in geojson_data["features"]:
        props = feat["properties"]
        if not props.get("in_bbox", False):
            continue
        lid = props["lease_id"]
        try:
            poly = shape(feat["geometry"])
            if not poly.is_valid:
                poly = poly.buffer(0)
            lease_polys[lid] = poly
        except Exception:
            pass

    # Build grid tree for fast neighbor lookup
    grid_coords = preds[["latitude", "longitude"]].values
    grid_tree = cKDTree(grid_coords)

    # Distance rings in meters
    rings = [
        ("inside", 0, 0),        # inside the polygon
        ("0-500m", 0, 500),
        ("500m-1km", 500, 1000),
        ("1-2km", 1000, 2000),
    ]

    results = []

    for _, lease_row in lease_bbox.iterrows():
        lid = lease_row["lease_id"]
        mine_name = lease_row["mine_name"]
        clat = lease_row["centroid_lat"]
        clon = lease_row["centroid_lon"]

        poly = lease_polys.get(lid)
        if poly is None:
            continue

        # Get all grid points within 2.5km of centroid
        search_radius_deg = 2500 / DEG_TO_M  # ~0.022 degrees
        nearby_idx = grid_tree.query_ball_point([clat, clon], search_radius_deg)

        if not nearby_idx:
            continue

        ring_scores = {name: [] for name, _, _ in rings}

        for idx in nearby_idx:
            pt_lat = preds.at[idx, "latitude"]
            pt_lon = preds.at[idx, "longitude"]
            score = preds.at[idx, score_col]

            # Check if inside polygon
            pt = Point(pt_lon, pt_lat)
            is_inside = poly.contains(pt)

            if is_inside:
                ring_scores["inside"].append(score)
            else:
                # Compute distance to polygon boundary
                pt_dist_deg = poly.boundary.distance(pt)
                pt_dist_m = pt_dist_deg * DEG_TO_M  # approximate

                for name, r_min, r_max in rings:
                    if name == "inside":
                        continue
                    if r_min <= pt_dist_m < r_max:
                        ring_scores[name].append(score)
                        break

        row = {"lease_id": lid, "mine_name": mine_name}
        for name, _, _ in rings:
            scores = ring_scores[name]
            row[f"{name}_mean"] = round(np.mean(scores), 4) if scores else np.nan
            row[f"{name}_n"] = len(scores)
        results.append(row)

    df_rings = pd.DataFrame(results)

    # Print table
    print(f"\nDistance-Ring Prospectivity Scores ({len(df_rings)} leases with polygon data):")
    print("-" * 100)
    header = f"{'mine_name':30s} | {'inside':>10s} | {'0-500m':>10s} | {'500m-1km':>10s} | {'1-2km':>10s}"
    print(header)
    print("-" * 100)

    for _, r in df_rings.iterrows():
        def fmt(name):
            m = r.get(f"{name}_mean", np.nan)
            n = r.get(f"{name}_n", 0)
            if pd.isna(m):
                return f"{'--':>6s}({n:2d})"
            return f"{m:6.3f}({n:2d})"

        line = f"{str(r['mine_name'])[:30]:30s} | {fmt('inside'):>10s} | {fmt('0-500m'):>10s} | {fmt('500m-1km'):>10s} | {fmt('1-2km'):>10s}"
        print(line)

    # Aggregated summary
    print("-" * 100)
    for name, _, _ in rings:
        col = f"{name}_mean"
        vals = df_rings[col].dropna()
        if len(vals) > 0:
            print(f"  {name:10s} aggregate: mean={vals.mean():.4f}, median={vals.median():.4f}, n_leases={len(vals)}")
        else:
            print(f"  {name:10s} aggregate: no data")

    # Interpretation
    print("\n  INTERPRETATION:")
    inside_vals = df_rings["inside_mean"].dropna()
    ring1_vals = df_rings["0-500m_mean"].dropna()
    ring2_vals = df_rings["500m-1km_mean"].dropna()
    ring3_vals = df_rings["1-2km_mean"].dropna()

    if len(inside_vals) > 0 and len(ring1_vals) > 0:
        drop = inside_vals.mean() - ring1_vals.mean()
        print(f"  Inside -> 0-500m drop: {drop:.4f}")
        if drop > 0.2:
            print("  [WARNING] Sharp drop at boundary -- possible mine-scar leakage!")
        else:
            print("  [OK] Gradual transition -- model likely using geological features, not mine scars.")

    return df_rings


def part_b_spectral_ablation():
    """
    Re-run spatial CV without spectral bare-soil/iron-oxide features.
    Compare PR-AUC, recall, and top-k% recall.
    """
    print("\n" + "=" * 70)
    print("STEP 3B: Spectral Ablation (remove iron_oxide_index, clay_index)")
    print("=" * 70)

    # Import pipeline components
    import sys
    sys.path.insert(0, os.path.join(BASE_DIR, "src"))

    from pu_prospectivity_pipeline import (
        Config, DataValidator, create_spatial_blocks,
        build_preprocessor, PUBaggingEnsemble
    )
    from sklearn.model_selection import GroupKFold
    from sklearn.metrics import average_precision_score

    # Load dataset
    df = pd.read_csv(DATASET, comment="#")
    if "mn_occurrence" in df.columns and "known_occurrence" not in df.columns:
        df.rename(columns={"mn_occurrence": "known_occurrence"}, inplace=True)

    df = create_spatial_blocks(df)

    # Define feature sets
    full_features = Config.EXPECTED_FEATURES
    ablated_features = [f for f in full_features if f not in ["iron_oxide_index", "clay_index"]]

    print(f"  Full features ({len(full_features)}): {full_features}")
    print(f"  Ablated features ({len(ablated_features)}): {ablated_features}")

    # Run CV for both
    results = {}
    for label, features in [("Full Model", full_features), ("No Spectral-Mineral", ablated_features)]:
        print(f"\n  --- Running Spatial CV: {label} ---")

        groups = df["cv_group"].values
        n_pos_groups = df.loc[df["known_occurrence"] == 1, "cv_group"].nunique()
        n_folds = min(5, n_pos_groups)
        gkf = GroupKFold(n_splits=n_folds)
        X_raw = df[features].copy()
        y = df["known_occurrence"].values

        fold_metrics = []
        all_preds = np.zeros(len(df))

        for fold, (train_idx, val_idx) in enumerate(gkf.split(X_raw, y, groups)):
            X_train = X_raw.iloc[train_idx]
            y_train = y[train_idx]
            X_val = X_raw.iloc[val_idx]
            y_val = y[val_idx]

            # Build preprocessor for this feature set
            categorical = ["rock_type_encoded"] if "rock_type_encoded" in features else []
            numerical = [f for f in features if f not in categorical]

            from sklearn.pipeline import Pipeline as SkPipeline
            from sklearn.impute import SimpleImputer
            from sklearn.preprocessing import OrdinalEncoder
            from sklearn.compose import ColumnTransformer

            num_pipe = SkPipeline([("imputer", SimpleImputer(strategy="median"))])
            cat_pipe = SkPipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encoder", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)),
            ])
            preprocessor = ColumnTransformer([
                ("num", num_pipe, numerical),
                ("cat", cat_pipe, categorical),
            ], remainder="passthrough")

            X_train_proc = preprocessor.fit_transform(X_train)
            X_val_proc = preprocessor.transform(X_val)

            pu_model = PUBaggingEnsemble()
            pu_model.fit(X_train_proc, y_train)

            val_preds = pu_model.predict_proba(X_val_proc)
            all_preds[val_idx] = val_preds

            p_val_idx = np.where(y_val == 1)[0]
            if len(p_val_idx) > 0:
                recall_05 = np.mean(val_preds[p_val_idx] >= 0.5)
                pr_auc = average_precision_score(y_val, val_preds)
            else:
                recall_05 = np.nan
                pr_auc = np.nan

            fold_metrics.append({
                "fold": fold + 1,
                "recall_05": recall_05,
                "pr_auc": pr_auc,
                "n_val_pos": len(p_val_idx),
            })
            print(f"    Fold {fold+1}: Recall@0.5={recall_05:.3f}, PR-AUC={pr_auc:.4f}, Val P={len(p_val_idx)}")

        # Top-k% recall: what fraction of positives are captured in the top k% of predicted area
        sorted_idx = np.argsort(-all_preds)
        pos_mask = (y == 1)
        for k_pct in [1, 2, 5, 10]:
            top_k = int(len(df) * k_pct / 100)
            top_k_idx = sorted_idx[:top_k]
            top_k_pos = pos_mask[top_k_idx].sum()
            total_pos = pos_mask.sum()
            recall_k = top_k_pos / total_pos if total_pos > 0 else 0
            print(f"    Recall@top-{k_pct}% area: {recall_k:.3f} ({top_k_pos}/{total_pos} positives in top {top_k} grid pts)")

        mdf = pd.DataFrame(fold_metrics)
        results[label] = {
            "mean_recall_05": mdf["recall_05"].mean(),
            "std_recall_05": mdf["recall_05"].std(),
            "mean_pr_auc": mdf["pr_auc"].mean(),
            "std_pr_auc": mdf["pr_auc"].std(),
        }

    # Side-by-side comparison
    print("\n" + "=" * 70)
    print("SIDE-BY-SIDE COMPARISON")
    print("=" * 70)
    print(f"{'Metric':30s} | {'Full Model':>20s} | {'No Spectral-Mineral':>20s}")
    print("-" * 75)
    for metric_name, key in [
        ("Mean Recall@0.5", "mean_recall_05"),
        ("Std Recall@0.5", "std_recall_05"),
        ("Mean PR-AUC", "mean_pr_auc"),
        ("Std PR-AUC", "std_pr_auc"),
    ]:
        v1 = results["Full Model"][key]
        v2 = results["No Spectral-Mineral"][key]
        print(f"  {metric_name:28s} | {v1:20.4f} | {v2:20.4f}")

    print("\n  INTERPRETATION:")
    full_r = results["Full Model"]["mean_recall_05"]
    abl_r = results["No Spectral-Mineral"]["mean_recall_05"]
    if full_r - abl_r > 0.1:
        print(f"  Spectral features contribute significantly (+{full_r-abl_r:.3f} recall).")
        print("  This is expected: iron_oxide and clay indices detect mineral signatures.")
    elif abl_r >= full_r:
        print("  Removing spectral-mineral features does NOT hurt performance.")
        print("  Model may be relying on topo/geological features, not spectral mine-scar artifacts.")
    else:
        print(f"  Minor spectral contribution (+{full_r-abl_r:.3f} recall).")
        print("  Model mostly uses topo/geology; spectral features add modest geological signal.")


def main():
    part_a_distance_rings()
    part_b_spectral_ablation()

    print("\n" + "=" * 70)
    print("STEP 3 COMPLETE.")
    print("Files created: None (analysis only).")
    print("Files modified: None.")
    print("Cannot verify: Whether 'inside' polygon scores are inflated by")
    print("  training data leakage vs genuine geological signal (would need")
    print("  ground-truth from field surveys to confirm).")
    print("=" * 70)


if __name__ == "__main__":
    main()
