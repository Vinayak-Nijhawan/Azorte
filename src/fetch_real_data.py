"""
Stage 1: Fetch Real Sentinel-2 Spectral Data
=============================================
Pulls real, freely available Sentinel-2 Level-2A surface reflectance data
for the Nagpur-Bhandara-Balaghat manganese belt (21.0-21.5°N, 79.0-79.5°E).

Data Source: Microsoft Planetary Computer (Copernicus Sentinel-2 L2A)
  - Zero authentication required
  - Cloud-Optimized GeoTIFFs streamed via HTTP range requests

Output: data/real_spectral.csv
  Columns (ALL REAL from satellite):
    latitude, longitude, ndvi, iron_oxide_index, clay_index, B02, B04, B08, B11, B12

Fallback: If Planetary Computer is unreachable, generates synthetic spectral
data with realistic distributions. This is CLEARLY FLAGGED in the CSV and on stdout.
"""

import os
import sys
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BBOX = [79.0, 21.0, 79.5, 21.5]  # [west, south, east, north]
GRID_STEP = 0.01  # ~1 km spacing → ~2,500 points
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "real_spectral.csv")
RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)


def build_grid():
    """Create a regular lat/lon grid over the study area."""
    lons = np.arange(BBOX[0], BBOX[2], GRID_STEP)
    lats = np.arange(BBOX[1], BBOX[3], GRID_STEP)
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    return lat_grid.ravel(), lon_grid.ravel()


def fetch_from_planetary_computer(lats, lons):
    """
    Attempt to fetch real Sentinel-2 L2A bands from Microsoft Planetary Computer.
    Returns a DataFrame with real band values, or None if fetch fails.
    """
    try:
        import pystac_client
        import planetary_computer as pc
        import rasterio
        from rasterio.transform import rowcol
    except ImportError as e:
        print(f"[WARN] Missing dependency for real data fetch: {e}")
        print("[WARN] Install with: pip install -r requirements-fetch.txt")
        return None

    try:
        print("[INFO] Connecting to Microsoft Planetary Computer STAC API...")
        catalog = pystac_client.Client.open(
            "https://planetarycomputer.microsoft.com/api/stac/v1",
            modifier=pc.sign_inplace,
        )

        # Search for a recent, low-cloud Sentinel-2 scene
        search = catalog.search(
            collections=["sentinel-2-l2a"],
            bbox=BBOX,
            query={"eo:cloud_cover": {"lt": 20}},
            sortby=["-properties.datetime"],
            max_items=5,
        )
        items = list(search.items())
        if not items:
            print("[WARN] No Sentinel-2 scenes found with cloud cover < 20%.")
            return None

        item = items[0]
        print(f"[INFO] Selected scene: {item.id}")
        print(f"[INFO] Date: {item.datetime}")
        print(f"[INFO] Cloud cover: {item.properties.get('eo:cloud_cover', 'N/A')}%")

        # Bands we need
        band_names = ["B02", "B04", "B08", "B11", "B12"]
        band_data = {}

        # Reproject grid lat/lon to the scene's native CRS (UTM)
        from rasterio.windows import from_bounds
        from rasterio.crs import CRS
        from pyproj import Transformer

        # Get scene CRS from first band
        first_href = item.assets[band_names[0]].href
        with rasterio.open(first_href) as src_check:
            scene_crs = src_check.crs
            print(f"[INFO] Scene CRS: {scene_crs}")

        # Transform BBOX and grid points from EPSG:4326 to scene CRS
        transformer = Transformer.from_crs("EPSG:4326", scene_crs, always_xy=True)
        grid_xs, grid_ys = transformer.transform(lons, lats)
        bbox_left, bbox_bottom = transformer.transform(BBOX[0], BBOX[1])
        bbox_right, bbox_top = transformer.transform(BBOX[2], BBOX[3])

        for band in band_names:
            asset = item.assets[band]
            href = asset.href
            print(f"[INFO] Reading {band} from COG...")

            with rasterio.open(href) as src:
                # Read the window covering our bbox in the scene's native CRS
                window = from_bounds(bbox_left, bbox_bottom, bbox_right, bbox_top, src.transform)
                data = src.read(1, window=window).astype(np.float32)

                # Get the transform for this window
                win_transform = src.window_transform(window)

                print(f"[INFO]   Window shape: {data.shape}")

                # Sample band values at each grid point (already in UTM)
                values = []
                for gx, gy in zip(grid_xs, grid_ys):
                    try:
                        row, col = rowcol(win_transform, gx, gy)
                        row, col = int(row), int(col)
                        if 0 <= row < data.shape[0] and 0 <= col < data.shape[1]:
                            val = data[row, col]
                            # Sentinel-2 L2A values are scaled by 10000
                            values.append(val / 10000.0 if val > 0 else np.nan)
                        else:
                            values.append(np.nan)
                    except Exception:
                        values.append(np.nan)

                band_data[band] = np.array(values)
                valid_count = np.sum(~np.isnan(band_data[band]))
                mean_val = np.nanmean(band_data[band]) if valid_count > 0 else 0
                print(f"[INFO]   {band}: {mean_val:.4f} mean, {valid_count} valid pixels")

        # Build DataFrame
        df = pd.DataFrame({
            "latitude": lats,
            "longitude": lons,
            "B02": band_data["B02"],
            "B04": band_data["B04"],
            "B08": band_data["B08"],
            "B11": band_data["B11"],
            "B12": band_data["B12"],
        })

        # Drop rows with NaN bands
        valid_before = len(df)
        df = df.dropna().reset_index(drop=True)
        print(f"[INFO] Valid pixels: {len(df)} / {valid_before}")

        if len(df) < 100:
            print("[WARN] Too few valid pixels retrieved. Falling back to synthetic.")
            return None

        # Compute spectral indices — these are REAL values from REAL satellite data
        df["ndvi"] = (df["B08"] - df["B04"]) / (df["B08"] + df["B04"] + 1e-10)
        df["iron_oxide_index"] = df["B04"] / (df["B02"] + 1e-10)
        df["clay_index"] = df["B11"] / (df["B12"] + 1e-10)

        # Clamp indices to reasonable ranges
        df["ndvi"] = df["ndvi"].clip(-1, 1)
        df["iron_oxide_index"] = df["iron_oxide_index"].clip(0, 5)
        df["clay_index"] = df["clay_index"].clip(0, 5)

        print("[INFO] ✅ Successfully fetched REAL Sentinel-2 data!")
        return df

    except Exception as e:
        print(f"[WARN] Planetary Computer fetch failed: {e}")
        return None


def generate_synthetic_fallback(lats, lons):
    """
    Generate synthetic spectral data with realistic distributions.
    THIS IS SYNTHETIC DATA — clearly flagged as such.

    Distributions are modeled after typical Sentinel-2 reflectance values
    for semi-arid tropical terrain in central India (Deccan Plateau).
    """
    print("=" * 70)
    print("[SYNTHETIC FALLBACK] Planetary Computer / GEE not reachable.")
    print("[SYNTHETIC FALLBACK] Generating synthetic spectral data with")
    print("[SYNTHETIC FALLBACK] realistic distributions for the study area.")
    print("[SYNTHETIC FALLBACK] THIS DATA IS NOT FROM REAL SATELLITES.")
    print("=" * 70)

    n = len(lats)

    # Realistic Sentinel-2 surface reflectance ranges for Deccan Plateau
    # B02 (Blue):  0.02 - 0.12
    # B04 (Red):   0.03 - 0.15
    # B08 (NIR):   0.10 - 0.45
    # B11 (SWIR1): 0.08 - 0.35
    # B12 (SWIR2): 0.05 - 0.25

    # Create spatial gradient to simulate real terrain variation
    lat_norm = (lats - lats.min()) / (lats.max() - lats.min() + 1e-10)
    lon_norm = (lons - lons.min()) / (lons.max() - lons.min() + 1e-10)

    # Vegetation increases towards the east (forest belt)
    veg_gradient = 0.3 * lon_norm + 0.2 * lat_norm

    B02 = np.clip(0.05 + 0.03 * np.random.randn(n) + 0.02 * (1 - veg_gradient), 0.01, 0.15)
    B04 = np.clip(0.07 + 0.04 * np.random.randn(n) + 0.03 * (1 - veg_gradient), 0.02, 0.20)
    B08 = np.clip(0.25 + 0.10 * np.random.randn(n) + 0.15 * veg_gradient, 0.05, 0.50)
    B11 = np.clip(0.18 + 0.07 * np.random.randn(n) + 0.05 * (1 - veg_gradient), 0.04, 0.40)
    B12 = np.clip(0.12 + 0.05 * np.random.randn(n) + 0.03 * (1 - veg_gradient), 0.03, 0.30)

    # Add some localized anomalies (simulating ore-bearing laterite patches)
    anomaly_mask = np.random.rand(n) < 0.15
    B04[anomaly_mask] *= 1.3  # Higher red reflectance (iron oxide)
    B11[anomaly_mask] *= 1.2  # Higher SWIR1 (clay minerals)

    ndvi = (B08 - B04) / (B08 + B04 + 1e-10)
    iron_oxide_index = B04 / (B02 + 1e-10)
    clay_index = B11 / (B12 + 1e-10)

    df = pd.DataFrame({
        "latitude": lats,
        "longitude": lons,
        "B02": B02,
        "B04": B04,
        "B08": B08,
        "B11": B11,
        "B12": B12,
        "ndvi": ndvi.clip(-1, 1),
        "iron_oxide_index": iron_oxide_index.clip(0, 5),
        "clay_index": clay_index.clip(0, 5),
    })

    return df


def main():
    print("=" * 70)
    print("STAGE 1: Fetch Real Sentinel-2 Spectral Data")
    print(f"Study Area: {BBOX[1]}–{BBOX[3]}°N, {BBOX[0]}–{BBOX[2]}°E")
    print("(Nagpur–Bhandara–Balaghat Manganese Belt)")
    print("=" * 70)

    # Build grid
    lats, lons = build_grid()
    print(f"\n[INFO] Grid: {len(lats)} points at ~{GRID_STEP * 111:.1f} km spacing")

    # Try real data first
    df = fetch_from_planetary_computer(lats, lons)

    if df is not None:
        data_source = "REAL (Sentinel-2 L2A via Microsoft Planetary Computer)"
        is_synthetic = False
    else:
        # Fallback to synthetic
        df = generate_synthetic_fallback(lats, lons)
        data_source = "SYNTHETIC (Planetary Computer/GEE unreachable - see README)"
        is_synthetic = True

    # Save
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    # Write CSV with a comment header documenting the source
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(f"# DATA SOURCE: {data_source}\n")
        f.write(f"# GENERATED: {pd.Timestamp.now().isoformat()}\n")
        f.write(f"# BBOX: {BBOX}\n")
        if is_synthetic:
            f.write("# WARNING: This is SYNTHETIC data, NOT real satellite observations.\n")
            f.write("# See README.md for details on why and how to replace with real data.\n")
        else:
            f.write("# All spectral values (B02, B04, B08, B11, B12, NDVI, iron_oxide_index,\n")
            f.write("# clay_index) are REAL values derived from actual Sentinel-2 imagery.\n")
        df.to_csv(f, index=False)

    # Print summary
    print(f"\n{'=' * 70}")
    print(f"OUTPUT: {OUTPUT_PATH}")
    print(f"DATA SOURCE: {data_source}")
    print(f"{'=' * 70}")
    print(f"\nRow count: {len(df)}")
    print(f"\nColumn summary:")
    print(df.describe().round(4).to_string())
    print(f"\nColumns: {list(df.columns)}")
    print(f"\nFirst 5 rows:")
    print(df.head().to_string())


if __name__ == "__main__":
    main()
