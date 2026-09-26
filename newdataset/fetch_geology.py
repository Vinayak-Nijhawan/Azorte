"""
MOIL-GeoSync -- Real Geology Data via BGS/GSI WMS
===================================================
Pulls REAL geological data (rock type / lithology, fault distance) for
every grid point in the elevation dataset.

Source: British Geological Survey / Geological Survey of India
       WMS endpoint: http://ogc.bgs.ac.uk/cgi-bin/BGS_GSI_Geology/wms
       Layers: IND_GSI_2M_Geology (lithology), IND_GSI_2M_Faults (faults)

Strategy:
  - Lithology: Deduplicate grid to 0.05-deg cells (1:2M map = ~5km resolution),
    query GetFeatureInfo with 10 parallel workers, then broadcast back.
  - Faults: Download fault map raster, extract fault pixel positions,
    build a KD-tree for fast nearest-fault-distance queries.

Output: newdataset/geology_real.csv
"""

import requests
import pandas as pd
import numpy as np
import os
import sys
import time
import re
import io
from math import radians, cos, sin, asin, sqrt
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Paths ----------------------------------------------------------------
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(OUTPUT_DIR, 'geology_real.csv')
CHECKPOINT_PATH = os.path.join(OUTPUT_DIR, 'geology_checkpoint.csv')
ELEVATION_PATH = os.path.join(OUTPUT_DIR, 'elevation_real.csv')
FAULT_CACHE_PATH = os.path.join(OUTPUT_DIR, 'fault_positions_cache.npz')

WMS_URL = 'http://ogc.bgs.ac.uk/cgi-bin/BGS_GSI_Geology/wms'

# Parallel workers for WMS queries
MAX_WORKERS = 10
# Resolution for deduplication (degrees). 0.05 deg ~ 5km, matches 1:2M map scale
DEDUP_RESOLUTION = 0.05


# --- Haversine distance (km) ----------------------------------------------
def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points in km."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6371 * asin(sqrt(a))


# --- Step 1: Build fault spatial index from raster -------------------------
def build_fault_index():
    """
    Download the IND_GSI_2M_Faults layer as a transparent PNG raster,
    find non-transparent pixels (= fault lines), convert pixel coords
    back to lat/lon, and return as arrays.
    """
    if os.path.exists(FAULT_CACHE_PATH):
        print("[FAULTS] Loading fault positions from cache...")
        data = np.load(FAULT_CACHE_PATH)
        return data['lats'], data['lons']

    print("[FAULTS] Downloading fault raster from BGS WMS...")

    BBOX_LON_MIN, BBOX_LAT_MIN = 75.5, 14.0
    BBOX_LON_MAX, BBOX_LAT_MAX = 86.5, 23.5
    IMG_W, IMG_H = 2200, 1900

    params = {
        'service': 'WMS',
        'version': '1.1.1',
        'request': 'GetMap',
        'layers': 'IND_GSI_2M_Faults',
        'styles': '',
        'format': 'image/png',
        'srs': 'EPSG:4326',
        'bbox': f'{BBOX_LON_MIN},{BBOX_LAT_MIN},{BBOX_LON_MAX},{BBOX_LAT_MAX}',
        'width': IMG_W,
        'height': IMG_H,
        'transparent': 'true',
    }

    r = requests.get(WMS_URL, params=params, timeout=120)
    r.raise_for_status()

    from PIL import Image
    img = Image.open(io.BytesIO(r.content)).convert('RGBA')
    arr = np.array(img)

    fault_mask = arr[:, :, 3] > 0
    fault_ys, fault_xs = np.where(fault_mask)

    print(f"[FAULTS] Found {len(fault_xs)} fault pixels in raster")

    fault_lons = BBOX_LON_MIN + (fault_xs / IMG_W) * (BBOX_LON_MAX - BBOX_LON_MIN)
    fault_lats = BBOX_LAT_MAX - (fault_ys / IMG_H) * (BBOX_LAT_MAX - BBOX_LAT_MIN)

    np.savez_compressed(FAULT_CACHE_PATH, lats=fault_lats, lons=fault_lons)
    print(f"[FAULTS] Cached {len(fault_lats)} fault positions")

    return fault_lats, fault_lons


def compute_fault_distances(grid_lats, grid_lons, fault_lats, fault_lons):
    """
    For each grid point, compute distance (km) to nearest fault pixel
    using scipy KD-tree.
    """
    from scipy.spatial import cKDTree

    print(f"[FAULTS] Building KD-tree from {len(fault_lats)} fault positions...")

    mean_lat = np.mean(grid_lats)
    cos_lat = np.cos(np.radians(mean_lat))

    fault_x = fault_lons * cos_lat * 111.32
    fault_y = fault_lats * 111.32
    tree = cKDTree(np.column_stack([fault_x, fault_y]))

    grid_x = grid_lons * cos_lat * 111.32
    grid_y = grid_lats * 111.32
    grid_pts = np.column_stack([grid_x, grid_y])

    print("[FAULTS] Querying nearest fault for all grid points...")
    distances_km, indices = tree.query(grid_pts)

    return distances_km, indices


# --- Step 2: Query lithology via GetFeatureInfo (parallel) -----------------
def query_lithology_single(lat, lon, retries=3):
    """
    Query BGS WMS GetFeatureInfo for rock type at a single lat/lon.
    Returns (rock_type, age) or ('Unknown', 'Unknown') on failure.
    """
    delta = 0.005
    bbox = f'{lon - delta},{lat - delta},{lon + delta},{lat + delta}'

    params = {
        'service': 'WMS',
        'version': '1.1.1',
        'request': 'GetFeatureInfo',
        'layers': 'IND_GSI_2M_Geology',
        'query_layers': 'IND_GSI_2M_Geology',
        'styles': '',
        'info_format': 'application/vnd.ogc.gml',
        'srs': 'EPSG:4326',
        'bbox': bbox,
        'width': 11,
        'height': 11,
        'x': 5,
        'y': 5,
        'feature_count': 1,
    }

    for attempt in range(retries):
        try:
            r = requests.get(WMS_URL, params=params, timeout=30)
            r.raise_for_status()
            text = r.text

            rock_match = re.search(r'<INDEX_>(.*?)</INDEX_>', text)
            age_match = re.search(r'<Age>(.*?)</Age>', text)

            rock_type = rock_match.group(1).strip() if rock_match else 'Unknown'
            age = age_match.group(1).strip() if age_match else 'Unknown'

            return rock_type, age

        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(2 ** (attempt + 1))
            else:
                return 'Timeout', 'Timeout'
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** (attempt + 1))
            else:
                return 'Error', 'Error'

    return 'Unknown', 'Unknown'


def fetch_lithology_parallel(cells_df):
    """
    Fetch lithology for unique cells using thread pool.
    cells_df must have columns: lat_cell, lon_cell
    Returns dict mapping (lat_cell, lon_cell) -> (rock_type, age)
    """
    # Load checkpoint if exists
    results = {}
    if os.path.exists(CHECKPOINT_PATH):
        df_ckpt = pd.read_csv(CHECKPOINT_PATH)
        for _, row in df_ckpt.iterrows():
            key = (row['lat_cell'], row['lon_cell'])
            results[key] = (row['rock_type'], row['geological_age'])
        print(f"[CKPT] Resuming from checkpoint: {len(results)} cells done")

    # Filter out already-done cells
    remaining = []
    for _, row in cells_df.iterrows():
        key = (row['lat_cell'], row['lon_cell'])
        if key not in results:
            remaining.append((row['lat_cell'], row['lon_cell']))

    total_remaining = len(remaining)
    total_all = len(cells_df)
    print(f"[LITHO] {total_all} unique cells, {total_remaining} remaining to query")

    if total_remaining == 0:
        return results

    # Process in parallel with checkpoint saves
    done_count = 0
    checkpoint_interval = 200

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_cell = {}
        for lat, lon in remaining:
            future = executor.submit(query_lithology_single, lat, lon)
            future_to_cell[future] = (lat, lon)

        for future in as_completed(future_to_cell):
            lat, lon = future_to_cell[future]
            try:
                rock_type, age = future.result(timeout=60)
            except Exception:
                rock_type, age = 'Error', 'Error'

            results[(lat, lon)] = (rock_type, age)
            done_count += 1

            if done_count % 50 == 0 or done_count == total_remaining:
                pct = (len(results)) / total_all * 100
                print(f"[LITHO] {len(results)}/{total_all} ({pct:.1f}%) -- last: {rock_type}", flush=True)

            # Checkpoint
            if done_count % checkpoint_interval == 0:
                _save_checkpoint(results)

    # Final checkpoint
    _save_checkpoint(results)
    return results


def _save_checkpoint(results):
    """Save current results to checkpoint CSV."""
    rows = []
    for (lat, lon), (rt, age) in results.items():
        rows.append({'lat_cell': lat, 'lon_cell': lon, 'rock_type': rt, 'geological_age': age})
    pd.DataFrame(rows).to_csv(CHECKPOINT_PATH, index=False)
    print(f"[CKPT] Saved checkpoint: {len(rows)} cells", flush=True)


# --- Main pipeline --------------------------------------------------------
def main():
    print("=" * 70)
    print("MOIL-GeoSync -- Real Geology Data (BGS/GSI WMS)")
    print("Source: " + WMS_URL)
    print("=" * 70)

    # Load grid
    print(f"\n[GRID] Loading grid from {ELEVATION_PATH}...")
    df_grid = pd.read_csv(ELEVATION_PATH, comment='#')
    df_unique = df_grid[['latitude', 'longitude', 'region']].drop_duplicates(
        subset=['latitude', 'longitude']
    ).reset_index(drop=True)
    print(f"[GRID] {len(df_unique)} unique grid points")

    # -- Step 1: Fault distances (bulk, fast) --
    print(f"\n{'=' * 50}")
    print("STEP 1: FAULT LINE DISTANCES")
    print(f"{'=' * 50}")

    fault_lats, fault_lons = build_fault_index()

    distances_km, nearest_idx = compute_fault_distances(
        df_unique['latitude'].values,
        df_unique['longitude'].values,
        fault_lats, fault_lons
    )

    df_unique = df_unique.copy()
    df_unique['fault_distance_km'] = np.round(distances_km, 4)
    df_unique['near_fault_name'] = [
        f"Fault_{flat:.2f}N_{flon:.2f}E"
        for flat, flon in zip(fault_lats[nearest_idx], fault_lons[nearest_idx])
    ]

    print(f"[FAULTS] Distance stats (km):")
    print(f"   min:  {distances_km.min():.2f}")
    print(f"   mean: {distances_km.mean():.2f}")
    print(f"   max:  {distances_km.max():.2f}")

    # -- Step 2: Lithology (deduplicated + parallel) --
    print(f"\n{'=' * 50}")
    print("STEP 2: LITHOLOGY (deduplicated + parallel)")
    print(f"{'=' * 50}")

    # Deduplicate to coarser grid (map is 1:2M, ~5km resolution)
    df_unique['lat_cell'] = np.round(df_unique['latitude'] / DEDUP_RESOLUTION) * DEDUP_RESOLUTION
    df_unique['lon_cell'] = np.round(df_unique['longitude'] / DEDUP_RESOLUTION) * DEDUP_RESOLUTION

    cells = df_unique[['lat_cell', 'lon_cell']].drop_duplicates().reset_index(drop=True)
    print(f"[LITHO] Deduplicated {len(df_unique)} points -> {len(cells)} unique {DEDUP_RESOLUTION}-deg cells")

    litho_results = fetch_lithology_parallel(cells)

    # Map results back to all points
    rock_types = []
    ages = []
    for _, row in df_unique.iterrows():
        key = (row['lat_cell'], row['lon_cell'])
        rt, age = litho_results.get(key, ('Unknown', 'Unknown'))
        rock_types.append(rt)
        ages.append(age)

    df_unique['rock_type'] = rock_types
    df_unique['geological_age'] = ages

    # -- Step 3: Save --
    print(f"\n{'=' * 50}")
    print("STEP 3: SAVING RESULTS")
    print(f"{'=' * 50}")

    df_out = df_unique.rename(columns={
        'latitude': 'lat',
        'longitude': 'lon',
    })

    cols = ['lat', 'lon', 'rock_type', 'geological_age',
            'fault_distance_km', 'near_fault_name']
    df_out = df_out[cols]

    # Clean rock type names
    df_out['rock_type'] = df_out['rock_type'].str.replace(' ', '_').str.replace('-', '_')

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(f"# DATA SOURCE: REAL (BGS/GSI WMS -- IND_GSI_2M_Geology + IND_GSI_2M_Faults)\n")
        f.write(f"# ENDPOINT: {WMS_URL}\n")
        f.write(f"# GENERATED: {pd.Timestamp.now().isoformat()}\n")
        f.write(f"# Rock types are from the GSI 1:2M geological map of India.\n")
        f.write(f"# Fault distances computed from raster fault map via KD-tree.\n")
        df_out.to_csv(f, index=False)

    print(f"\n[OUTPUT] {OUTPUT_PATH}")
    print(f"   Total rows: {len(df_out)}")
    print(f"\n   Rock type breakdown:")
    print(df_out['rock_type'].value_counts().head(20).to_string())
    print(f"\n   Fault distance stats (km):")
    print(df_out['fault_distance_km'].describe().round(2).to_string())

    # Clean up checkpoint
    if os.path.exists(CHECKPOINT_PATH):
        os.remove(CHECKPOINT_PATH)
        print("\n[CKPT] Checkpoint file cleaned up")

    print("\nDONE! Real geology data saved.")


if __name__ == '__main__':
    main()
