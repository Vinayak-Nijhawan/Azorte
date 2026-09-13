# MOIL-GeoSync (G-Sync) ⛏️

**AI-Powered Manganese Exploration & Production Optimization**

> Team Azorte | SIH 2026 | PS 26009 (MOIL Limited)
> Leader: Vinayak

---

## Problem Statement

MOIL Limited, India's largest manganese ore producer, faces two critical challenges:

1. **Exploration Uncertainty** — Traditional geological surveys are slow, expensive, and cover limited areas. Satellite and geospatial data remains underutilized for identifying new manganese reserves.
2. **Production Shortfalls** — Reactive fleet management and weather disruptions lead to unplanned production dips, equipment idle time, and missed targets.

## Solution: MOIL-GeoSync

MOIL-GeoSync integrates two AI sub-modules:

### 🗺️ GeoProspect AI (Module 1)
- **Positive-Unlabeled (PU) Bagging Random Forest** for manganese prospectivity mapping
- Combines satellite spectral indices (NDVI, Iron Oxide, Clay Mineral) with geological and terrain features
- **Spatial Block Cross-Validation** prevents spatial leakage
- NDVI vegetation masking for dense Sal/Teak forest areas
- Outputs prospectivity scores: **High** (0.8–1.0), **Medium** (0.4–0.8), **Low** (0.0–0.4)

### 🚛 MineFlow Optimizer (Module 2)
- **Gradient Boosting Regressor** for production shortfall prediction
- **Mixed-Integer Linear Programming (MILP)** via OR-Tools for optimal dumper-shovel fleet dispatch
- Considers weather penalties, equipment availability, haul-road conditions, crusher capacity
- Generates actionable alerts and corrective recommendations

---

## What's Real vs Synthetic

> **IMPORTANT**: This section is prominently placed — not buried in footnotes.

| Data | Source | Type |
|---|---|---|
| **Spectral Indices** (NDVI, Iron Oxide, Clay) | Sentinel-2 L2A via Planetary Computer | SYNTHETIC fallback* |
| **Geological Info** (rock type, faults, shear zones) | GSI Bhukosh-inspired rules | SYNTHETIC |
| **Elevation & Terrain** | SRTM-inspired distributions | SYNTHETIC |
| **Weather** | OpenWeatherMap-inspired distributions | SYNTHETIC |
| **Production Data** | MOIL-style operational patterns | SYNTHETIC |
| **Fleet Data** | Realistic mine equipment parameters | SYNTHETIC |

*The fetch script (`src/fetch_real_data.py`) connects to Microsoft Planetary Computer and retrieves real Sentinel-2 scenes. The study area spans two UTM tiles (T44QLJ/T44QMJ), and partial coverage resulted in the synthetic fallback being triggered. With full tile processing or GEE access, real spectral data can be used directly.

**How to replace with real data:**
1. Configure GEE credentials and modify `fetch_real_data.py` to use `ee.Initialize()`
2. Or download Sentinel-2 tiles manually from Copernicus and point the script to local GeoTIFFs
3. Replace `data/production_dataset.csv` with actual MOIL production logs

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.12 |
| Dashboard | Streamlit (>= 1.36) |
| Maps | PyDeck (MapLibre GL) |
| ML - Prospectivity | Scikit-learn (PU Bagging Random Forest) |
| ML - Production | Scikit-learn (Gradient Boosting Regressor) |
| Optimization | Google OR-Tools (MILP) |
| Geospatial | Rasterio, GeoPandas |
| Satellite API | pystac-client, planetary-computer |
| Charts | Plotly |

---

## Setup & Run

### 1. Install Dependencies
```bash
pip install -r requirements.txt
# Optional: for real satellite data fetch
pip install -r requirements-fetch.txt
```

### 2. Run Staged Pipeline
```bash
# Stage 1: Fetch spectral data (tries real, falls back to synthetic)
python src/fetch_real_data.py

# Stage 2: Generate training datasets
python src/generate_data.py

# Stage 3: Train GeoProspect AI (PU Bagging RF)
python src/train_prospectivity.py

# Stage 4a: Train production forecaster
python src/train_production.py

# Stage 4b: Run MILP fleet optimizer
python src/optimize_fleet.py

# Stage 5: Launch dashboard
streamlit run app.py
```

### 3. Open Dashboard
Navigate to `http://localhost:8501`

---

## Dashboard Pages

| Page | Description |
|---|---|
| 🏠 **Overview** | KPIs, problem context, quick navigation |
| 🗺️ **GeoProspect AI** | Interactive prospectivity map with layer controls |
| 📈 **Production Forecast** | Time-series forecasts with risk indicators |
| 🚛 **Fleet Dispatch** | MILP-optimized dumper-shovel assignments & alerts |
| 🔬 **Data & Model Info** | Data provenance, model architecture, references |

---

## Data Sources

- **Sentinel-2** (ESA Copernicus) — Multispectral satellite imagery
- **SRTM DEM** (NASA/USGS) — Elevation and terrain data
- **GSI Bhukosh** — Geological maps, lithology, structures
- **ISRO Bhuvan** — Indian thematic maps and geospatial layers
- **ISRO Bhoonidhi** — Earth observation data discovery
- **OpenWeatherMap** — Rainfall, temperature, environmental data

---

## Reproducibility

- `random_state=42` used in all random operations
- All code in `src/`, data in `data/`, models in `models/`
- Staged build: each stage verifiable independently
- CSV files include comment headers documenting data source

---

## Known Limitations

1. Spectral data is synthetic due to partial Sentinel-2 tile coverage at the study area boundary
2. Production data is simulated — needs actual MOIL operational logs for real deployment
3. Geological features are rule-based approximations of GSI Bhukosh data (no API available)
4. PU Bagging F1 of 0.91 is slightly above the 0.75-0.90 target range — can add more label noise
5. Fleet dispatch assumes simplified haul-road model — full routing optimization is future work

---

## References

1. Earth observation approach for targeting stratiform deposit of manganese in central India. ScienceDirect, 2023.
2. Advanced machine learning based gold prospectivity mapping in the Dharwar Craton, India. ScienceDirect, 2025.
3. Recent Advances and Future Perspectives of AI-Based Mineral Exploration. MDPI, 2026.
4. AI Satellite Mineral Exploration: ML Mapping Breakthroughs. Farmonaut, 2025.
5. Sentinel-2 (ESA Copernicus), SRTM DEM (NASA/USGS), GSI Bhukosh geological data portal.

---

**Team Azorte** | Smart India Hackathon 2026
