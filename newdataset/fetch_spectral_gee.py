"""
MOIL-GeoSync â€” Real Sentinel-2 Spectral Data via Google Earth Engine
=====================================================================
Pulls REAL Sentinel-2 L2A surface reflectance data for 3 manganese regions:
  1. Central India (Nagpur-Bhandara-Balaghat belt)
  2. Eastern India (Joda-Barbil, Odisha)
  3. Southern India (Sandur-Bellary, Karnataka)

Bands: B02 (Blue), B04 (Red), B08 (NIR), B11 (SWIR1), B12 (SWIR2)
Indices: NDVI, Iron Oxide Index, Clay Mineral Index

Output: newdataset/spectral_real.csv
"""

import ee
import pandas as pd
import numpy as np
import os
import time

# â”€â”€â”€ Configuration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
GEE_PROJECT = 'moil-geosync'
GRID_STEP = 0.01  # ~1 km spacing
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(OUTPUT_DIR, 'spectral_real.csv')

# Date range for cloud-free composite
DATE_START = '2024-01-01'
DATE_END = '2024-05-31'  # Pre-monsoon (best for mineral mapping)
MAX_CLOUD = 20  # Max cloud cover %

# 3 Manganese Regions
REGIONS = {
    'Central_India': {
        'bbox': [78.8, 21.0, 80.5, 22.0],
        'description': 'Nagpur-Bhandara-Balaghat Manganese Belt'
    },
    'Odisha': {
        'bbox': [85.0, 21.8, 85.7, 22.3],
        'description': 'Joda-Barbil Iron-Manganese Belt'
    },
    'Karnataka': {
        'bbox': [76.2, 14.8, 76.8, 15.4],
        'description': 'Sandur-Bellary Manganese Belt'
    }
}


def initialize_gee():
    """Initialize Google Earth Engine."""
    try:
        ee.Initialize(project=GEE_PROJECT)
        print(f"[INFO] âœ… GEE initialized with project: {GEE_PROJECT}")
        return True
    except Exception as e:
        print(f"[ERROR] GEE initialization failed: {e}")
        print("[INFO] Run 'earthengine authenticate' first.")
        return False


def build_grid(bbox, step=GRID_STEP):
    """Create a regular lat/lon grid over a bounding box."""
    west, south, east, north = bbox
    lons = np.arange(west, east, step)
    lats = np.arange(south, north, step)
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    return lat_grid.ravel(), lon_grid.ravel()


def get_sentinel2_composite(bbox):
    """
    Get a cloud-free Sentinel-2 L2A median composite for a region.
    Uses pre-monsoon imagery for best mineral detection.
    """
    geometry = ee.Geometry.Rectangle(bbox)

    # Sentinel-2 Surface Reflectance (L2A) â€” harmonized collection
    collection = (
        ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(geometry)
        .filterDate(DATE_START, DATE_END)
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', MAX_CLOUD))
    )

    count = collection.size().getInfo()
    print(f"[INFO]   Found {count} Sentinel-2 scenes")

    if count == 0:
        print("[WARN]   No scenes found! Try expanding date range.")
        return None

    # Median composite (removes clouds and outliers)
    composite = collection.median().clip(geometry)

    # Select bands and scale (Sentinel-2 L2A values are scaled by 10000)
    bands = composite.select(['B2', 'B4', 'B8', 'B11', 'B12'])
    bands = bands.divide(10000.0)

    # Compute spectral indices
    ndvi = bands.normalizedDifference(['B8', 'B4']).rename('ndvi')
    iron_oxide = bands.select('B4').divide(bands.select('B2').add(1e-10)).rename('iron_oxide_index')
    clay_index = bands.select('B11').divide(bands.select('B12').add(1e-10)).rename('clay_index')

    # Combine all
    result = bands.addBands([ndvi, iron_oxide, clay_index])
    return result


def sample_image_at_points(image, lats, lons, region_name, batch_size=500):
    """
    Sample image values at grid points using GEE.
    Processes in batches to avoid GEE payload limits.
    """
    all_results = []
    total = len(lats)

    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch_lats = lats[start:end]
        batch_lons = lons[start:end]

        # Create FeatureCollection of sample points
        points = []
        for lat, lon in zip(batch_lats, batch_lons):
            point = ee.Feature(ee.Geometry.Point([float(lon), float(lat)]))
            points.append(point)

        fc = ee.FeatureCollection(points)

        # Sample the image at these points
        sampled = image.sampleRegions(
            collection=fc,
            scale=10,  # 10m resolution for Sentinel-2
            geometries=True
        )

        # Fetch results
        try:
            features = sampled.getInfo()['features']
            for feat in features:
                props = feat['properties']
                coords = feat['geometry']['coordinates']
                row = {
                    'latitude': coords[1],
                    'longitude': coords[0],
                    'region': region_name,
                    'B02': props.get('B2', np.nan),
                    'B04': props.get('B4', np.nan),
                    'B08': props.get('B8', np.nan),
                    'B11': props.get('B11', np.nan),
                    'B12': props.get('B12', np.nan),
                    'ndvi': props.get('ndvi', np.nan),
                    'iron_oxide_index': props.get('iron_oxide_index', np.nan),
                    'clay_index': props.get('clay_index', np.nan),
                }
                all_results.append(row)

            print(f"[INFO]   Batch {start//batch_size + 1}: {len(features)} points sampled")

        except Exception as e:
            print(f"[WARN]   Batch {start//batch_size + 1} failed: {e}")

        # Small delay to respect GEE rate limits
        time.sleep(1)

    return all_results


def main():
    print("=" * 70)
    print("MOIL-GeoSync â€” Real Sentinel-2 Spectral Data via GEE")
    print("=" * 70)

    # Initialize GEE
    if not initialize_gee():
        return

    all_data = []

    for region_name, config in REGIONS.items():
        bbox = config['bbox']
        desc = config['description']
        print(f"\n{'â”€' * 50}")
        print(f"[REGION] {region_name}: {desc}")
        print(f"[BBOX]   {bbox}")

        # Build grid
        lats, lons = build_grid(bbox)
        print(f"[INFO]   Grid: {len(lats)} points at ~{GRID_STEP * 111:.1f} km spacing")

        # Get Sentinel-2 composite
        composite = get_sentinel2_composite(bbox)

        if composite is None:
            print(f"[WARN]   Skipping {region_name} â€” no data available")
            continue

        # Sample at grid points
        print(f"[INFO]   Sampling spectral values at {len(lats)} grid points...")
        results = sample_image_at_points(composite, lats, lons, region_name)
        all_data.extend(results)
        print(f"[INFO]   âœ… {region_name}: {len(results)} points sampled successfully")

    if not all_data:
        print("\n[ERROR] No data fetched from any region!")
        return

    # Create DataFrame
    df = pd.DataFrame(all_data)

    # Drop rows with NaN
    valid_before = len(df)
    df = df.dropna().reset_index(drop=True)
    print(f"\n[INFO] Valid points: {len(df)} / {valid_before}")

    # Clamp indices to reasonable ranges
    df['ndvi'] = df['ndvi'].clip(-1, 1)
    df['iron_oxide_index'] = df['iron_oxide_index'].clip(0, 5)
    df['clay_index'] = df['clay_index'].clip(0, 5)

    # Save
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(f"# DATA SOURCE: REAL (Sentinel-2 L2A via Google Earth Engine)\n")
        f.write(f"# PROJECT: {GEE_PROJECT}\n")
        f.write(f"# DATE RANGE: {DATE_START} to {DATE_END} (pre-monsoon composite)\n")
        f.write(f"# GENERATED: {pd.Timestamp.now().isoformat()}\n")
        f.write(f"# ALL spectral values are REAL â€” derived from actual satellite imagery.\n")
        df.to_csv(f, index=False)

    # Print summary
    print(f"\n{'=' * 70}")
    print(f"OUTPUT: {OUTPUT_PATH}")
    print(f"DATA SOURCE: REAL Sentinel-2 L2A via Google Earth Engine")
    print(f"{'=' * 70}")
    print(f"\nTotal rows: {len(df)}")
    print(f"\nRegion breakdown:")
    print(df['region'].value_counts().to_string())
    print(f"\nColumn summary:")
    print(df.describe().round(4).to_string())
    print(f"\nFirst 5 rows:")
    print(df.head().to_string())
    print("\nâœ… DONE! Real spectral data saved successfully.")


if __name__ == '__main__':
    main()

