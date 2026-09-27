# Final Prospectivity Model — Results Report

---

## 1. One-line verdict

**"This model is weak but usable — it has learned real geological patterns from real government data, but with only 17 confirmed positive points across 11 independent zones, its predictions are directional guidance, not reliable targeting."**

---

## 2. The 3 key numbers, explained simply

| Metric | Score | Plain-language meaning |
|--------|-------|------------------------|
| **Balanced Accuracy** | **0.77 (77%)** | A coin flip would be right 50% of the time. This model is right about 77% of the time, which means it's clearly better than guessing. But it still gets it wrong roughly 1 in 4 times. |
| **ROC-AUC** | **0.81 (81%)** | If you showed the model one location with manganese and one without, it would correctly say "this one is more likely" about 81% of the time. Anything above 0.80 is generally considered "good ranking ability." The model genuinely learned which geological conditions are associated with manganese. |
| **PR-AUC** | **0.06 (6%)** | This measures how well the model finds rare things. Manganese locations are extremely rare in our data — only 17 out of 16,931 points (0.1%). A random guesser would score about 0.1%. Our model scores 6%, which is **60× better than random** at finding the needles. But in absolute terms, 6% means: if you follow all its "high probability" flags, most will still be wrong. This is the honest cost of having only 17 confirmed examples to learn from. |

> [!IMPORTANT]
> The gap between ROC-AUC (0.81, looks good) and PR-AUC (0.06, looks bad) is normal and expected when positives are this rare. ROC-AUC says "the model ranks well." PR-AUC says "but there are so few real positives that even good ranking still produces many false alarms." Both statements are true simultaneously.

---

## 3. Feature check

### Confirmed INCLUDED (8 features, all real):

| Feature | Importance | Source |
|---------|------------|--------|
| `rock_type_encoded` | **17.4%** (rank 1) | NGDR Geology 50K Lithology (63,465 polygons, MH+MP) |
| `clay_index` | **15.5%** (rank 2) | Sentinel-2 L2A via GEE (B11/B12 ratio) |
| `fault_distance_km` | **13.9%** (rank 3) | NGDR Geology 50K Faults (2,542 lines, MH+MP) |
| `elevation_m` | **12.6%** (rank 4) | NASA SRTM 30m DEM via GEE |
| `iron_oxide_index` | **11.7%** (rank 5) | Sentinel-2 L2A via GEE (B04/B02 ratio) |
| `ndvi` | **10.6%** (rank 6) | Sentinel-2 L2A via GEE |
| `slope_deg` | **10.5%** (rank 7) | NASA SRTM 30m DEM via GEE |
| `rainfall_mm` | **7.9%** (rank 8) | Open-Meteo Historical API (2016–2025) |

### Confirmed ABSENT:

| Excluded Feature | Reason |
|------------------|--------|
| ❌ `shear_zone_proximity_km` | Real NGDR data had only 2 rows per state. Unusable. Not substituted. |
| ❌ `soil_moisture` | No real GEE source was fetched. Formula version (`rainfall/2500 + noise`) is deprecated. Removed entirely. |
| ❌ `prospectivity_signal` | Synthetic label formula fully deprecated. Labels from lease polygons only. |

---

## 4. Fold coverage table

The script attempted 5-fold CV first but **flagged that Folds 3 and 4 each had only 1 positive block** — making their metrics unreliable. It automatically switched to 3-fold CV as planned.

| Fold | Test Positive Blocks | Train Positive Blocks | Test Positive Points | Train Positive Points |
|------|---------------------:|----------------------:|---------------------:|----------------------:|
| 1 | 6 | 5 | 10 | 7 |
| 2 | 4 | 7 | 6 | 11 |
| 3 | **1** ⚠️ | 10 | **1** | 16 |

> [!WARNING]
> **Fold 3 still has only 1 positive block in its test set**, even with 3-fold CV. This means the Fold 3 metric (BalAcc=0.88, Recall=1.00) is based on a single test point and is statistically meaningless on its own. The overall averages are therefore weighted toward the more reliable Folds 1 and 2.
>
> This is a direct consequence of having only 11 unique positive blocks in the grid data. There is no CV configuration that fully avoids this — it is an honest limitation of the available data, not a bug.

**Clarification on block counts:** The 84 lease polygons span 29 unique blocks. However, only 17 of the 16,931 spectral grid points land inside those polygons, and those 17 points span only **11** of the 29 blocks. The remaining 18 blocks contain lease polygons but no grid points happened to fall inside them (the leases are small relative to the grid spacing). This is a grid resolution limitation, not a data error.

---

## 5. The real-world test

If someone used this model today to scout for manganese in Maharashtra or Madhya Pradesh, it would consistently point them toward the geologically correct rock types (metamorphic terrains of the Sausar Group), near fault zones, and at appropriate elevations. That's genuinely useful directional guidance — a geologist looking at the model's heatmap would say "yes, these are the right neighborhoods to investigate." However, within those neighborhoods, the model cannot reliably distinguish the exact spots with manganese from the ones without, because it only learned from 17 confirmed positive locations. It narrows the search area, but it does not replace boots-on-the-ground prospecting.

---

## 6. Documentation paragraph (verbatim, for the SIH project report)

> "This model was validated on 11 independent spatial zones (0.1° blocks) derived from confirmed GSI manganese lease data across Maharashtra and Madhya Pradesh. Given the limited number of independent positive sites, results should be treated as directional prospectivity guidance for further geological investigation, not as confirmed deposit predictions."

---

## 7. Files produced

| File | Path |
|------|------|
| Trained model | `C:\Users\vinay\OneDrive\Desktop\SIH\models\prospectivity_final_real.joblib` |
| Scored dataset (16,931 rows) | `C:\Users\vinay\OneDrive\Desktop\SIH\data\prospectivity_final_real.csv` |

---

## 8. What to do next (recommendation B — needs more data, not a rethink)

The model architecture (PU-Bagging RF + Spatial Block CV) is sound. The features are real. The bottleneck is purely **positive label count**: 17 grid-level positives across 11 blocks. To cross the 50-block threshold for confident validation, the most realistic path is downloading NGDR Lease + Lithology + Fault data for **Odisha** (Joda-Barbil manganese belt), which would add an entirely independent geographic region with its own manganese leases — genuine new spatial evidence, not inflated numbers from densification.
