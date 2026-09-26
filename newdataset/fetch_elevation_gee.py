"""
MOIL-GeoSync â€” Real SRTM Elevation Data via Google Earth Engine
================================================================
Pulls REAL NASA SRTM 30m Digital Elevation Model data for 3 regions.

Features extracted:
  - elevation_m: Elevation in meters
  - slope_deg: Terrain slope in degrees

Output: newdataset/elevation_real.csv
"""

import ee
import pandas as pd
import numpy as np
import os
import time

# â”€â”€â”€ Configuration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
GEE_PROJECT = 'moil-geosync'
GRID_STEP = 0.01
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(OUTPUT_DIR, 'elevation_real.csv')

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
    try:
        ee.Initialize(project=GEE_PROJECT)
        print(f"[INFO] âœ… GEE initialized with project: {GEE_PROJECT}")
        return True
    except Exception as e:
        print(f"[ERROR] GEE initialization failed: {e}")
        return False


def build_grid(bbox, step=GRID_STEP):
    west, south, east, north = bbox
    lons = np.arange(west, east, step)
    lats = np.arange(south, north, step)
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    return lat_grid.ravel(), lon_grid.ravel()


def get_srtm_data(bbox):
    """Get SRTM elevation and compute slope."""
    geometry = ee.Geometry.Rectangle(bbox)

    # NASA SRTM 30m DEM
    srtm = ee.Image('USGS/SRTMGL1_003').clip(geometry)
    elevation = srtm.select('elevation')

    # Compute slope from elevation
    slope = ee.Terrain.slope(srtm).rename('slope_deg')

    return elevation.addBands(slope)


def sample_elevation(image, lats, lons, region_name, batch_size=500):
    """Sample elevation values at grid points."""
    all_results = []
    total = len(lats)

    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch_lats = lats[start:end]
        batch_lons = lons[start:end]

        points = []
        for lat, lon in zip(batch_lats, batch_lons):
            point = ee.Feature(ee.Geometry.Point([float(lon), float(lat)]))
            points.append(point)

        fc = ee.FeatureCollection(points)

        sampled = image.sampleRegions(
            collection=fc,
            scale=30,  # 30m resolution for SRTM
            geometries=True
        )

        try:
            features = sampled.getInfo()['features']
            for feat in features:
                props = feat['properties']
                coords = feat['geometry']['coordinates']
                row = {
                    'latitude': coords[1],
                    'longitude': coords[0],
                    'region': region_name,
                    'elevation_m': props.get('elevation', np.nan),
                    'slope_deg': props.get('slope_deg', np.nan),
                }
                all_results.append(row)

            print(f"[INFO]   Batch {start//batch_size + 1}: {len(features)} points sampled")

        except Exception as e:
            print(f"[WARN]   Batch {start//batch_size + 1} failed: {e}")

        time.sleep(1)

    return all_results


def main():
    print("=" * 70)
    print("MOIL-GeoSync â€” Real SRTM Elevation Data via GEE")
    print("=" * 70)

    if not initialize_gee():
        return

    all_data = []

    for region_name, config in REGIONS.items():
        bbox = config['bbox']
        desc = config['description']
        print(f"\n{'â”€' * 50}")
        print(f"[REGION] {region_name}: {desc}")

        lats, lons = build_grid(bbox)
        print(f"[INFO]   Grid: {len(lats)} points")

        srtm_image = get_srtm_data(bbox)

        print(f"[INFO]   Sampling elevation at {len(lats)} grid points...")
        results = sample_elevation(srtm_image, lats, lons, region_name)
        all_data.extend(results)
        print(f"[INFO]   âœ… {region_name}: {len(results)} points done")

    if not all_data:
        print("\n[ERROR] No elevation data fetched!")
        return

    df = pd.DataFrame(all_data)
    df = df.dropna().reset_index(drop=True)

    # Save
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(f"# DATA SOURCE: REAL (NASA SRTM 30m DEM via Google Earth Engine)\n")
        f.write(f"# GENERATED: {pd.Timestamp.now().isoformat()}\n")
        f.write(f"# Elevation in meters, Slope in degrees\n")
        df.to_csv(f, index=False)

    print(f"\n{'=' * 70}")
    print(f"OUTPUT: {OUTPUT_PATH}")
    print(f"Total rows: {len(df)}")
    print(f"\nRegion breakdown:")
    print(df['region'].value_counts().to_string())
    print(f"\nElevation stats:")
    print(df[['elevation_m', 'slope_deg']].describe().round(2).to_string())
    print("\nâœ… DONE! Real elevation data saved.")


if __name__ == '__main__':
    main()

