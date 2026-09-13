# MOIL-GeoSync — Judge Pitch Summary

## What It Solves

MOIL-GeoSync addresses two core challenges for MOIL Limited, India's largest manganese producer:

**Exploration**: Traditional geological surveys are slow and expensive. GeoProspect AI uses a Positive-Unlabeled Bagging Random Forest to combine satellite imagery (Sentinel-2 spectral indices) with geological features, generating prospectivity maps that identify high-potential manganese zones — reducing blind exploration and focusing drilling efforts.

**Production**: Reactive fleet management causes production shortfalls during monsoons and equipment downtime. MineFlow Optimizer uses Gradient Boosting to forecast shortfalls and Mixed-Integer Linear Programming (OR-Tools) to generate optimal dumper-shovel dispatch plans — proactively preventing production dips.

## Real vs Simulated

- **Satellite data pipeline** is validated against actual Sentinel-2 L2A imagery from Microsoft Planetary Computer for the real Nagpur-Bhandara manganese belt (21.0-21.5°N, 79.0-79.5°E)
- **Geological and production data** are simulated with realistic distributions — clearly labeled throughout the codebase and dashboard
- Architecture is designed for drop-in replacement with MOIL's actual operational data and full satellite coverage

## Key Numbers (Illustrative)

- **2,500 grid points** analyzed across the manganese belt at ~1 km resolution
- **GeoProspect AI F1 score: 0.91** with Spatial Block Cross-Validation
- **Production model R² = 0.90** on test data
- **193 optimized fleet dispatch assignments** with 74 automated alerts
- **5% shortfall reduction** across 3 mines ≈ cost savings through proactive fleet optimization *(illustrative, based on simulated data)*

## Next Steps for Production Deployment

1. Replace synthetic production data with actual MOIL mine logs
2. Extend satellite pull to full lease area using GEE or direct Copernicus download
3. Integrate with MOIL's fleet-management/ERP systems via API
4. Add field validation feedback loop to continuously improve prospectivity model

---

*Team Azorte | SIH 2026 | PS 26009*
