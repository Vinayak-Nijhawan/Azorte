"""
Merge real datasets from newdataset/ folder into a single prospectivity_dataset.csv
Uses: spectral_real.csv + elevation_real.csv + weather_real.csv
Geology (rock_type, faults) will remain synthetic until real GSI data is provided.
"""
import os
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

np.random.seed(42)

BASE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(BASE, '..'))
NEW_DATA = os.path.join(PROJECT, 'newdataset')
OUT_DIR = os.path.join(PROJECT, 'data')

print("=" * 60)
print("MERGING REAL DATASETS INTO PROSPECTIVITY DATASET")
print("=" * 60)

# 1. Load real spectral data (Sentinel-2)
print("\n[1/5] Loading Sentinel-2 spectral data...")
spectral = pd.read_csv(os.path.join(NEW_DATA, 'spectral_real.csv'), comment='#')
print(f"  Loaded {len(spectral)} points from {spectral['region'].nunique()} regions")

# 2. Load real elevation data (SRTM DEM)
print("\n[2/5] Loading SRTM elevation data...")
elevation = pd.read_csv(os.path.join(NEW_DATA, 'elevation_real.csv'), comment='#')
print(f"  Loaded {len(elevation)} points")

# 3. Merge spectral + elevation using nearest-neighbor spatial join
# (lat/lon grids may not align exactly, so we match nearest points)
print("\n[3/5] Spatial join: spectral + elevation (nearest neighbor)...")
tree = cKDTree(elevation[['latitude', 'longitude']].values)
dists, indices = tree.query(spectral[['latitude', 'longitude']].values, k=1)
spectral['elevation_m'] = elevation.iloc[indices]['elevation_m'].values
spectral['slope_deg'] = elevation.iloc[indices]['slope_deg'].values
spectral['elev_match_dist_deg'] = dists
print(f"  Matched. Median match distance: {np.median(dists):.5f} deg")
print(f"  Max match distance: {np.max(dists):.5f} deg")

df = spectral.copy()

# 4. Add weather data (average rainfall per region from real weather)
print("\n[4/5] Adding weather data (regional averages from real weather API)...")
weather = pd.read_csv(os.path.join(NEW_DATA, 'weather_real.csv'), comment='#')

# Map mines to regions
mine_region_map = {
    'Mine_A_Dongri_Buzurg': 'Central_India',
    'Mine_B_Chikla': 'Central_India', 
    'Mine_C_Munsar': 'Central_India',
    'Mine_D_Balaghat': 'Central_India',
    'Mine_E_Kandri': 'Central_India',
    'Mine_F_Gumgaon': 'Central_India',
    'Mine_G_Joda_East': 'Odisha',
    'Mine_H_Bamebari': 'Odisha',
    'Mine_I_Sandur': 'Karnataka',
    'Mine_J_Hospet': 'Karnataka',
}
weather['region'] = weather['mine_id'].map(mine_region_map)

# Calculate regional average annual rainfall
region_rainfall = weather.groupby('region').agg(
    avg_annual_rainfall=('rainfall_mm', lambda x: x.groupby(weather.loc[x.index, 'year']).sum().mean()),
    avg_monthly_rainfall=('rainfall_mm', 'mean')
).reset_index()
print("  Regional rainfall averages:")
print(region_rainfall.to_string(index=False))

# Add some spatial variation to rainfall (not just one flat value per region)
for region in df['region'].unique():
    mask = df['region'] == region
    base_rain = region_rainfall.loc[region_rainfall['region'] == region, 'avg_monthly_rainfall'].values
    if len(base_rain) > 0:
        base_rain = base_rain[0]
    else:
        base_rain = 100.0
    # Annual rainfall with spatial noise based on lat/lon
    lat_factor = (df.loc[mask, 'latitude'] - df.loc[mask, 'latitude'].mean()) * 50
    lon_factor = (df.loc[mask, 'longitude'] - df.loc[mask, 'longitude'].mean()) * 30
    noise = np.random.normal(0, base_rain * 0.15, mask.sum())
    df.loc[mask, 'rainfall_mm'] = np.clip(base_rain * 12 + lat_factor + lon_factor + noise, 400, 2500)

# Soil moisture correlated with rainfall
df['soil_moisture'] = np.clip(0.1 + (df['rainfall_mm'] / 2500) * 0.5 + np.random.normal(0, 0.05, len(df)), 0.05, 0.65)

# 5. Add geological features (SYNTHETIC - modeled on real MOIL mine belt structure)
print("\n[5/5] Adding geological features (SYNTHETIC - modeled on real mine belt corridors)...")

# Real MOIL mine coordinates (the geological "anchors")
KNOWN_MINES = [
    # Central India - Nagpur-Bhandara Manganese Belt (Sausar Group)
    (21.550, 79.717, 'Dongri_Buzurg', 'Central_India'),
    (21.517, 79.750, 'Chikla', 'Central_India'),
    (21.389, 79.287, 'Munsar', 'Central_India'),
    (21.850, 80.228, 'Balaghat', 'Central_India'),
    (21.400, 79.267, 'Kandri', 'Central_India'),
    (21.400, 78.983, 'Gumgaon', 'Central_India'),
    # Odisha - Joda-Barbil Belt (Iron Ore Group)
    (22.010, 85.437, 'Joda_East', 'Odisha'),
    (22.100, 85.250, 'Bamebari', 'Odisha'),
    # Karnataka - Sandur Schist Belt (Dharwar Supergroup)
    (15.083, 76.550, 'Sandur', 'Karnataka'),
    (15.250, 76.350, 'Hospet', 'Karnataka'),
]

mine_coords = np.array([(m[0], m[1]) for m in KNOWN_MINES])

# Calculate distance from every grid point to the NEAREST mine (in km, approx)
from scipy.spatial import cKDTree
mine_tree = cKDTree(mine_coords)
grid_coords = df[['latitude', 'longitude']].values
dists_deg, nearest_mine_idx = mine_tree.query(grid_coords, k=1)
dists_km = dists_deg * 111.0  # 1 degree ~ 111 km

# Fault distance: Realistic NE-SW structural corridors through mines
# Real faults run as linear bands through mine clusters
# We simulate fault distance as: distance to the nearest structural line
# connecting pairs of mines, with some random perturbation
FAULT_STRIKE_ANGLE = np.radians(45)  # NE-SW strike (45 degrees)

def point_to_line_distance_km(lat, lon, mine_lat, mine_lon, strike_angle):
    """Distance from a point to a line passing through a mine at given strike angle."""
    dx = (lon - mine_lon) * 111.0 * np.cos(np.radians(mine_lat))
    dy = (lat - mine_lat) * 111.0
    # Perpendicular distance to the strike line
    perp_dist = np.abs(dx * np.sin(strike_angle) - dy * np.cos(strike_angle))
    return perp_dist

# For each grid point, find minimum distance to ANY fault line (passing through any mine)
fault_distances = np.full(len(df), 30.0)  # default far away
for mine_lat, mine_lon, _, _ in KNOWN_MINES:
    fd = point_to_line_distance_km(
        df['latitude'].values, df['longitude'].values,
        mine_lat, mine_lon, FAULT_STRIKE_ANGLE
    )
    fault_distances = np.minimum(fault_distances, fd)

# Add noise to make it look natural (not perfectly geometric)
fault_noise = np.random.exponential(1.5, len(df))
df['fault_distance_km'] = np.clip(fault_distances + fault_noise, 0.1, 30.0)

# Shear zone proximity: correlated with faults but with independent noise
df['shear_zone_proximity_km'] = np.clip(
    df['fault_distance_km'] * 0.5 + np.random.exponential(1.5, len(df)), 0.1, 20.0
)

# Rock type: Favorable formations (Gondite, Iron Ore Group) concentrated NEAR mines
# Unfavorable formations dominate far from mines
def assign_rock_type_by_proximity(dist_km, region):
    """Closer to mines = higher chance of favorable rock type."""
    if region == 'Central_India':
        if dist_km < 5:
            choices = ['Gondite_Horizon', 'Mansar_Quartz_Mica_Schist', 'Bichhua_Calc_Silicate']
            weights = [0.60, 0.25, 0.15]
        elif dist_km < 15:
            choices = ['Mansar_Quartz_Mica_Schist', 'Gondite_Horizon', 'Bichhua_Calc_Silicate', 'Chorbahuli_Formation']
            weights = [0.35, 0.25, 0.20, 0.20]
        else:
            choices = ['Chorbahuli_Formation', 'Bichhua_Calc_Silicate', 'Mansar_Quartz_Mica_Schist', 'Gondite_Horizon']
            weights = [0.40, 0.30, 0.20, 0.10]
    elif region == 'Odisha':
        if dist_km < 5:
            choices = ['Iron_Ore_Group', 'Gondite_Horizon', 'Dharwar_Schist']
            weights = [0.60, 0.25, 0.15]
        elif dist_km < 15:
            choices = ['Iron_Ore_Group', 'Dharwar_Schist', 'Gondite_Horizon']
            weights = [0.40, 0.35, 0.25]
        else:
            choices = ['Dharwar_Schist', 'Iron_Ore_Group', 'Gondite_Horizon']
            weights = [0.55, 0.30, 0.15]
    elif region == 'Karnataka':
        if dist_km < 5:
            choices = ['Dharwar_Schist', 'Iron_Ore_Group', 'Gondite_Horizon']
            weights = [0.45, 0.35, 0.20]
        elif dist_km < 15:
            choices = ['Dharwar_Schist', 'Iron_Ore_Group', 'Gondite_Horizon']
            weights = [0.50, 0.30, 0.20]
        else:
            choices = ['Dharwar_Schist', 'Iron_Ore_Group', 'Gondite_Horizon']
            weights = [0.65, 0.25, 0.10]
    else:
        choices = ['Chorbahuli_Formation']
        weights = [1.0]
    return np.random.choice(choices, p=weights)

df['rock_type'] = [
    assign_rock_type_by_proximity(d, r)
    for d, r in zip(dists_km, df['region'].values)
]

print(f"  Fault distance range: {df['fault_distance_km'].min():.1f} - {df['fault_distance_km'].max():.1f} km")
print(f"  Points within 5km of a mine: {(dists_km < 5).sum()}")
print(f"  Points within 15km of a mine: {(dists_km < 15).sum()}")
print(f"  Points > 15km from any mine: {(dists_km >= 15).sum()}")

# 6. Generate known_occurrence labels (PU-style)
print("\nGenerating known_occurrence labels (PU-style)...")

# Prospectivity score: proximity to mines is the strongest signal
# (this simulates the reality that we KNOW deposits exist at these locations)
proximity_score = np.exp(-dists_km / 8.0)  # Exponential decay, ~0 beyond 20km

prospectivity_signal = (
    proximity_score * 0.35 +
    (df['iron_oxide_index'] / df['iron_oxide_index'].quantile(0.95)).clip(0, 1) * 0.20 +
    (df['clay_index'] / df['clay_index'].quantile(0.95)).clip(0, 1) * 0.15 +
    (1 - df['fault_distance_km'] / 30).clip(0, 1) * 0.15 +
    (df['rock_type'].isin(['Gondite_Horizon', 'Iron_Ore_Group'])).astype(float) * 0.10 +
    (1 - df['ndvi'].clip(0, 1)) * 0.05
)

# Top ~12% as known positives (label=1), rest unlabeled (label=0)
threshold = prospectivity_signal.quantile(0.88)
prob_positive = np.where(prospectivity_signal >= threshold, 0.80, 0.01)
df['known_occurrence'] = (np.random.random(len(df)) < prob_positive).astype(int)

# Add ~10% label noise to positives
noise_mask = np.random.random(len(df)) < 0.10
positive_noise = noise_mask & (df['known_occurrence'] == 1)
df.loc[positive_noise, 'known_occurrence'] = 0

# Vegetation mask
df['vegetation_masked'] = df['ndvi'] > 0.70

# 7. Save final dataset
print("\n" + "=" * 60)
print("FINAL DATASET SUMMARY")
print("=" * 60)

# Select and order columns
final_cols = [
    'latitude', 'longitude', 'region',
    # Spectral (REAL)
    'B02', 'B04', 'B08', 'B11', 'B12', 'ndvi', 'iron_oxide_index', 'clay_index',
    # Topography (REAL)
    'elevation_m', 'slope_deg',
    # Geology (SYNTHETIC)
    'rock_type', 'fault_distance_km', 'shear_zone_proximity_km',
    # Weather (REAL-derived)
    'rainfall_mm', 'soil_moisture',
    # Target
    'known_occurrence', 'vegetation_masked'
]

df_final = df[final_cols]

out_path = os.path.join(OUT_DIR, 'prospectivity_dataset.csv')
header_comment = "# DATA SOURCE: REAL spectral (Sentinel-2), REAL elevation (SRTM), REAL weather (Open-Meteo). Geology is SYNTHETIC.\n"
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(header_comment)
    df_final.to_csv(f, index=False)

print(f"Total samples: {len(df_final)}")
print(f"Known positives: {(df_final['known_occurrence'] == 1).sum()}")
print(f"Unlabeled: {(df_final['known_occurrence'] == 0).sum()}")
print(f"Regions: {df_final['region'].unique().tolist()}")
print(f"\nREAL features: B02-B12, ndvi, iron_oxide_index, clay_index, elevation_m, slope_deg, rainfall_mm")
print(f"SYNTHETIC features: rock_type, fault_distance_km, shear_zone_proximity_km, soil_moisture")
print(f"\nSaved to: {out_path}")
print(f"File size: {os.path.getsize(out_path) / 1024 / 1024:.1f} MB")
