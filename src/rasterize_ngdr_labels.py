"""
MOIL-GeoSync -- Rasterize NGDR Mn Lease Polygons onto Prospectivity Grid
=========================================================================
Step 2a: Takes the 66 in-BBOX lease polygons from ngdr_mn_leases.geojson
and marks grid points inside each polygon as known_occurrence=1.

For mineralization points (if any in BBOX): nearest grid point only.

Adds columns:
  - lease_id: which lease polygon the point falls inside (NaN if none)
  - lease_block_id: block_id derived from lease centroid (for fold grouping)
  - block_id: standard 0.1-deg spatial block

Outputs:
  - data/prospectivity_real_dataset.csv (updated in place, old backed up)
  - Prints summary: grid-point positives, independent leases, unique blocks

Does NOT run the PU pipeline. That is done separately.
"""

import os
import json
import math
import shutil
import numpy as np
import pandas as pd
from shapely.geometry import shape, Point

# -- Paths --
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_PATH = os.path.join(BASE_DIR, "data", "prospectivity_real_dataset.csv")
LEASE_GEOJSON = os.path.join(BASE_DIR, "newdataset", "ngdr_mn_leases.geojson")
LEASE_CSV = os.path.join(BASE_DIR, "newdataset", "ngdr_mn_positive_locations.csv")

BBOX_LAT_MIN, BBOX_LAT_MAX = 21.0, 22.1
BBOX_LON_MIN, BBOX_LON_MAX = 79.0, 80.5
BLOCK_SIZE = 0.1


def block_id_from_coords(lat, lon):
    return f"{int(math.floor(lat / BLOCK_SIZE))}_{int(math.floor(lon / BLOCK_SIZE))}"


def main():
    print("=" * 70)
    print("MOIL-GeoSync -- Rasterize NGDR Mn Leases onto Grid (Step 2a)")
    print("=" * 70)

    # -- 1. Load grid dataset --
    print("\n[1/5] Loading prospectivity grid dataset...")
    df = pd.read_csv(DATASET_PATH, comment="#")
    print(f"  Grid points: {len(df)}")
    old_pos = (df["mn_occurrence"] == 1).sum() if "mn_occurrence" in df.columns else 0
    print(f"  Existing positives (mn_occurrence=1): {old_pos}")

    # -- 2. Load lease polygons --
    print("\n[2/5] Loading NGDR lease polygons...")
    with open(LEASE_GEOJSON, "r", encoding="utf-8") as f:
        geojson_data = json.load(f)

    lease_meta = pd.read_csv(LEASE_CSV)
    lease_meta_bbox = lease_meta[lease_meta["in_bbox"] == True].copy()

    # Build shapely polygons for in-BBOX leases
    leases = []
    for feat in geojson_data["features"]:
        props = feat["properties"]
        if not props.get("in_bbox", False):
            continue
        lid = props["lease_id"]
        meta_row = lease_meta_bbox[lease_meta_bbox["lease_id"] == lid]
        if meta_row.empty:
            continue
        meta_row = meta_row.iloc[0]
        try:
            poly = shape(feat["geometry"])
            if not poly.is_valid:
                poly = poly.buffer(0)  # fix self-intersections
            centroid_lat = meta_row["centroid_lat"]
            centroid_lon = meta_row["centroid_lon"]
            lease_block = block_id_from_coords(centroid_lat, centroid_lon)
            leases.append({
                "lease_id": lid,
                "mine_name": meta_row["mine_name"],
                "polygon": poly,
                "centroid_lat": centroid_lat,
                "centroid_lon": centroid_lon,
                "lease_block_id": lease_block,
            })
        except Exception as e:
            print(f"  [WARN] Could not parse polygon for lease_id={lid}: {e}")

    print(f"  Loaded {len(leases)} in-BBOX lease polygons")

    # -- 3. Rasterize: point-in-polygon --
    print("\n[3/5] Rasterizing lease polygons onto grid...")
    # Initialize new columns
    df["lease_id"] = np.nan
    df["lease_block_id"] = ""
    # Reset mn_occurrence to 0 (we will re-label from scratch using polygons)
    df["mn_occurrence"] = 0

    # Assign block_id for all grid points
    df["block_id"] = df.apply(
        lambda r: block_id_from_coords(r["latitude"], r["longitude"]), axis=1
    )

    # For each grid point, check if it falls inside any lease polygon
    grid_points = df[["latitude", "longitude"]].values
    total_assigned = 0
    lease_hit_counts = {}

    for lease in leases:
        lid = lease["lease_id"]
        poly = lease["polygon"]
        lease_blk = lease["lease_block_id"]

        # Pre-filter: only check grid points whose block overlaps the polygon bbox
        minx, miny, maxx, maxy = poly.bounds
        # Expand slightly for edge cases
        mask = (
            (df["longitude"] >= minx - 0.001)
            & (df["longitude"] <= maxx + 0.001)
            & (df["latitude"] >= miny - 0.001)
            & (df["latitude"] <= maxy + 0.001)
        )
        candidate_idx = df.index[mask]

        hits = 0
        for idx in candidate_idx:
            pt = Point(df.at[idx, "longitude"], df.at[idx, "latitude"])
            if poly.contains(pt):
                df.at[idx, "mn_occurrence"] = 1
                df.at[idx, "lease_id"] = lid
                # For fold grouping: use the lease centroid's block
                df.at[idx, "lease_block_id"] = lease_blk
                hits += 1

        if hits > 0:
            lease_hit_counts[lid] = {
                "mine_name": lease["mine_name"],
                "hits": hits,
                "block": lease_blk,
                "method": "polygon",
            }
            total_assigned += hits

    polygon_assigned = total_assigned
    polygon_leases = len(lease_hit_counts)
    missed_leases = [l for l in leases if l["lease_id"] not in lease_hit_counts]
    print(f"  Phase A (polygon containment): {polygon_assigned} grid pts from {polygon_leases} leases")
    print(f"  Leases with ZERO grid hits (smaller than grid): {len(missed_leases)}")

    # -- Phase B: Nearest-grid-point fallback for missed leases --
    print("  Phase B: Assigning nearest grid point for small leases...")
    from scipy.spatial import cKDTree
    grid_tree = cKDTree(df[["latitude", "longitude"]].values)

    nearest_assigned = 0
    for lease in missed_leases:
        lid = lease["lease_id"]
        clat = lease["centroid_lat"]
        clon = lease["centroid_lon"]
        lease_blk = lease["lease_block_id"]

        dist, idx = grid_tree.query([clat, clon], k=1)
        # Only assign if not already labeled by a polygon hit at same point
        if df.at[idx, "mn_occurrence"] == 0:
            df.at[idx, "mn_occurrence"] = 1
            df.at[idx, "lease_id"] = lid
            df.at[idx, "lease_block_id"] = lease_blk
            total_assigned += 1
            nearest_assigned += 1
            lease_hit_counts[lid] = {
                "mine_name": lease["mine_name"],
                "hits": 1,
                "block": lease_blk,
                "method": "nearest",
            }
        else:
            # Grid point already positive (another lease nearby) — still register the lease
            lease_hit_counts[lid] = {
                "mine_name": lease["mine_name"],
                "hits": 0,
                "block": lease_blk,
                "method": "nearest_shared",
            }

    print(f"  Phase B: {nearest_assigned} additional grid pts from {len(missed_leases)} small leases")

    # For points NOT in any lease, lease_block_id = their own block_id
    no_lease_mask = df["lease_block_id"] == ""
    df.loc[no_lease_mask, "lease_block_id"] = df.loc[no_lease_mask, "block_id"]

    print(f"\n  TOTAL grid points labeled as positive: {total_assigned}")
    print(f"  Independent leases with >= 1 grid hit: {sum(1 for v in lease_hit_counts.values() if v['hits'] > 0)}")
    print(f"  Leases sharing a grid point: {sum(1 for v in lease_hit_counts.values() if v['method'] == 'nearest_shared')}")

    # -- 4. Summary stats --
    print("\n[4/5] Computing summary statistics...")
    new_pos = (df["mn_occurrence"] == 1).sum()
    unique_leases = df.loc[df["mn_occurrence"] == 1, "lease_id"].nunique()
    pos_blocks = df.loc[df["mn_occurrence"] == 1, "block_id"].nunique()
    total_blocks = df["block_id"].nunique()
    # Unique lease_block_id values that contain positives (for fold grouping)
    pos_lease_blocks = df.loc[df["mn_occurrence"] == 1, "lease_block_id"].nunique()

    print(f"\n  BEFORE: {old_pos} positive grid points")
    print(f"  AFTER:  {new_pos} positive grid points")
    print(f"  Independent leases (with grid hits): {unique_leases}")
    print(f"  Unique 0.1-deg blocks with positives: {pos_blocks}")
    print(f"  Unique lease-blocks (for fold grouping): {pos_lease_blocks}")
    print(f"  Total grid blocks: {total_blocks}")

    # Per-lease breakdown
    print("\n  Per-lease grid hits:")
    for lid, info in sorted(lease_hit_counts.items(), key=lambda x: -x[1]["hits"]):
        method = info.get("method", "?")
        print(f"    lease_id={lid:5d} | {info['mine_name']:30s} | {info['hits']:3d} grid pts | block={info['block']} | {method}")

    # Simulate fold distribution (GroupKFold by lease_block_id)
    from sklearn.model_selection import GroupKFold
    pos_df = df[df["mn_occurrence"] == 1].copy()
    if len(pos_df) > 0 and pos_lease_blocks >= 5:
        gkf = GroupKFold(n_splits=5)
        groups = pos_df["lease_block_id"].values
        y_dummy = pos_df["mn_occurrence"].values
        print("\n  Simulated 5-Fold distribution (positives only, grouped by lease_block_id):")
        for fold, (train_idx, val_idx) in enumerate(gkf.split(pos_df, y_dummy, groups)):
            val_pos = len(val_idx)
            val_leases = pos_df.iloc[val_idx]["lease_id"].nunique()
            val_blocks = pos_df.iloc[val_idx]["lease_block_id"].nunique()
            print(f"    Fold {fold+1}: {val_pos:3d} val positives, {val_leases:2d} val leases, {val_blocks:2d} val blocks")
    elif pos_lease_blocks < 5:
        print(f"\n  [WARN] Only {pos_lease_blocks} positive-containing blocks. Need >= 5 for 5-fold CV.")
        print(f"  Consider reducing N_CV_FOLDS or expanding BBOX.")

    # -- 5. Save --
    print("\n[5/5] Saving updated dataset...")
    # Backup original
    backup_path = DATASET_PATH + ".bak_before_rasterize"
    if not os.path.exists(backup_path):
        shutil.copy2(DATASET_PATH, backup_path)
        print(f"  Backed up original to: {os.path.basename(backup_path)}")

    header = (
        "# MOIL-GeoSync Prospectivity Dataset (NGDR-Rasterized Labels)\n"
        "# mn_occurrence=1: grid point falls inside an NGDR Mn mining lease polygon\n"
        "# lease_id: NGDR GeoJSON feature gid of the lease\n"
        "# lease_block_id: 0.1-deg block of the lease centroid (for spatial CV fold grouping)\n"
        f"# Rasterized: {pd.Timestamp.now().isoformat()}\n"
    )
    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        f.write(header)
        df.to_csv(f, index=False)
    print(f"  Saved to: {DATASET_PATH}")
    print(f"  Rows: {len(df)}, Columns: {list(df.columns)}")

    print("\n" + "=" * 70)
    print("STEP 2a COMPLETE. Dataset updated with polygon-rasterized labels.")
    print("Run the PU pipeline next: python src/pu_prospectivity_pipeline.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
