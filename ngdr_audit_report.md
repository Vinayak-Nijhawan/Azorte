# NGDR Data Audit Report

**Date:** 2026-09-27  
**Scope:** All GeoJSON files downloaded from NGDR (Bhu-Chayan portal) for the MOIL-GeoSync manganese prospectivity pipeline.  
**Files location:** `C:\Users\vinay\OneDrive\Desktop\SIH\newdataset\NGDR`

---

## 1. Master Verification Table

All files extracted and loaded successfully with `geopandas.read_file()`. **Zero load failures.**

| # | File | Rows | CRS | Invalid Geoms | Bounding Box |
|---|------|------|-----|---------------|--------------|
| 1 | `LITHOLOGY_STATE_MAHARASHTRA` | 32,982 | EPSG:4326 | 0 | (15.61°N, 72.64°E) → (22.03°N, 80.90°E) ✅ |
| 2 | `LITHOLOGY_STATE_MADHYA_PRADESH` | 30,483 | EPSG:4326 | 0 | (21.07°N, 74.03°E) → (26.87°N, 82.81°E) ✅ |
| 3 | `LITHOLOGY_DIST_NAGPUR` | 1,539 | EPSG:4326 | 0 | (20.58°N, 78.25°E) → (21.72°N, 79.66°E) ✅ |
| 4 | `FAULT_STATE_MAHARASHTRA` | 984 | EPSG:4326 | 0 | (15.75°N, 72.65°E) → (21.92°N, 80.86°E) ✅ |
| 5 | `FAULT_STATE_MADHYA_PRADESH` | 1,558 | EPSG:4326 | 0 | (21.07°N, 74.09°E) → (26.12°N, 82.75°E) ✅ |
| 6 | `FAULT_TECTONIC_STATE_MAHARASHTRA` | 133 | EPSG:4326 | 0 | (15.77°N, 72.82°E) → (22.01°N, 80.47°E) ✅ |
| 7 | `FAULT_TECTONIC_STATE_MADHYA_PRADESH` | 73 | EPSG:4326 | 0 | (21.34°N, 74.04°E) → (26.62°N, 82.79°E) ✅ |
| 8 | `INDIA_MAJOR_LEASE_2022_MP` | 389 | EPSG:4326 | 0 | (21.49°N, 74.41°E) → (26.10°N, 81.63°E) ✅ |
| 9 | `INDIA_MAJOR_LEASE_2022_MH` | 102 | EPSG:4326 | 0 | (15.73°N, 73.06°E) → (21.56°N, 80.49°E) ✅ |
| 10 | `SHEAR_ZONE_TECTONIC_MP` | **2** | EPSG:4326 | 0 | (21.54°N, 79.67°E) → (22.56°N, 81.64°E) ⚠️ |
| 11 | `SHEAR_ZONE_TECTONIC_MH` | **2** | EPSG:4326 | 0 | (20.68°N, 79.19°E) → (21.54°N, 80.13°E) ⚠️ |

> [!NOTE]
> - **CRS is uniform** across all files: `EPSG:4326` (WGS 84). No reprojection needed. Spatial joins will work out of the box.
> - **Zero invalid geometries** across all files.
> - **Bounding boxes** match expected geographic extents for Maharashtra (~15.6–22.1°N) and Madhya Pradesh (~21–26.9°N).

> [!WARNING]
> Both `SHEAR_ZONE_TECTONIC` files contain only **2 rows each**. These are not broken — NGDR's tectonic layer genuinely has very few mapped shear zones in this region. They are usable as supplementary features but too sparse to build a standalone `shear_zone_distance_km` column with meaningful spatial variation.

---

## 2. Lease Files — Mineral Column Check

The mineral name column is **`mineral_na`** (lowercase). Full unique values:

### Madhya Pradesh (389 leases)
| Mineral | Count |
|---------|-------|
| Bauxite | — |
| Copper Ore | — |
| Diamond | — |
| Iron Ore | — |
| Limestone | — |
| **Manganese Ore** | **61** |
| Rock Phosphate | — |

### Maharashtra (102 leases)
| Mineral | Count |
|---------|-------|
| Bauxite | — |
| Fluorite | — |
| Iron Ore | — |
| Kyanite | — |
| Limestone | — |
| **Manganese Ore** | **23** |

> [!IMPORTANT]
> **84 total manganese lease polygons** (61 MP + 23 MH) are available as ground-truth positive labels. Filter with:
> ```python
> mn_leases = gdf[gdf['mineral_na'].str.contains('MANGAN', case=False, na=False)]
> ```
> The naming is consistent (`"Manganese Ore"`) across both files — no variant spellings detected.

---

## 3. Specific Flag: Duplicate FAULT_TECTONIC_SHEAR_ZONE Files (20 KB × 2)

The two 20 KB zips (`...1790501906` and `...1790506728`) are **NOT duplicates**. They are different states:

| Zip File | Contents (after extraction) |
|----------|----------------------------|
| `..._MADHYA_PRADESH_...1790501906.zip` | `FAULT_TECTONIC_STATE_MADHYA_PRADESH.geojson` (73 rows) + `SHEAR_ZONE_TECTONIC_STATE_MADHYA_PRADESH.geojson` (2 rows) |
| `..._MAHARASHTRA_...1790506728.zip` | `FAULT_TECTONIC_STATE_MAHARASHTRA.geojson` (133 rows) + `SHEAR_ZONE_TECTONIC_STATE_MAHARASHTRA.geojson` (2 rows) |

**Verdict:** Both are usable. Each zip contained two layers bundled together (fault tectonic + shear zone) for one state.

---

## 4. Specific Flag: FAULT_LITHOLOGY_STATE_MAHARASHTRA vs LITHOLOGY_STATE_MAHARASHTRA

The `FAULT_LITHOLOGY_STATE_MAHARASHTRA` zip (266 MB) is **NOT a mislabeled duplicate**. It's a **bundle** — the portal combined two layers into one download:

| File inside the zip | Rows | Content |
|---------------------|------|---------|
| `FAULT_STATE_MAHARASHTRA.geojson` | 984 | Fault lines (identical to the standalone `FAULT_STATE_MAHARASHTRA` download) |
| `LITHOLOGY_STATE_MAHARASHTRA.geojson` | 32,982 | Lithology polygons (identical to the standalone `LITHOLOGY_STATE_MAHARASHTRA` download) |

**Verdict:** It contains no unique data. It is just the cart bundling both layers into one zip. **Discard this file** — you already have both layers as separate, cleaner downloads.

---

## 5. FAULT_TECTONIC vs FAULT Comparison

These are **genuinely different datasets**, not duplicates:

### Maharashtra
| Layer | Rows | Key Columns | What it is |
|-------|------|-------------|------------|
| `FAULT_STATE` | 984 | `fault_type`, `fault_name`, `toposheet_` | **Detailed 1:50K fault lines** from individual toposheets. Use this for `fault_distance_km`. |
| `FAULT_TECTONIC_STATE` | 133 | `code_desc`, `fault_name` | **Regional-scale tectonic lineaments** (major structures only). Supplementary. |

### Madhya Pradesh
| Layer | Rows | Key Columns | What it is |
|-------|------|-------------|------------|
| `FAULT_STATE` | 1,558 | `fault_type`, `fault_name`, `toposheet_` | **Detailed 1:50K fault lines**. Primary source. |
| `FAULT_TECTONIC_STATE` | 73 | `code_desc`, `fault_name` | **Regional-scale tectonic lineaments**. Supplementary. |

**Recommendation:** Standardize on `FAULT_STATE_*` (984 + 1,558 rows) as your primary fault distance feature — it has 12× more spatial resolution. Keep `FAULT_TECTONIC_STATE_*` as a secondary feature (`tectonic_fault_distance_km`) if you want an extra column.

---

## 6. Lithology Column Structure

All three lithology files share the same schema. The critical columns for the ML pipeline are:

| Column | Description | Sample Values |
|--------|-------------|---------------|
| `age` | Geological age | `ARCHAEAN`, `PALAEOPROTEROZOIC`, `QUATERNARY` |
| `supergroup` | Supergroup name | `DHARWAR`, (often null) |
| `group_name` | Group name | `SAUSAR`, `AMGAON GNEISSIC COMPLEX`, `GOA` |
| `formation` | Formation name | `LOHANGI`, `BICHUA`, `VAGERI` |
| `lithologic` | **Rock type name** | `AMPHIBOLITE`, `CALC GNEISS`, `MARBLE`, `ALLUVIUM` |
| `notation` | GSI map notation code | `σAagc7`, `Pt₁sb` |
| `geometry` | Polygon boundaries | MultiPolygon / Polygon |

> [!TIP]
> The `lithologic` column is what replaces the synthetic `rock_type` in `generate_data.py`. For any grid coordinate, a spatial join (`gpd.sjoin`) against the lithology GeoDataFrame will return the **real GSI rock type** at that exact location.
>
> The Nagpur file already shows `group_name = 'SAUSAR'` with formations `LOHANGI` and `BICHUA` — this is exactly the Sausar Group stratigraphy from the Mandri-Panchala G4 report we extracted earlier. **The data is consistent with our domain knowledge.**

---

## 7. Final Go / No-Go Decision

### What we have (verified & ready):

| Feature | Source | Rows | Real? |
|---------|--------|------|-------|
| **Rock type** (`lithologic`) | NGDR Lithology 50K | 63,465 polygons (MH+MP) | ✅ 100% Real |
| **Fault distance** | NGDR Fault 50K | 2,542 fault lines (MH+MP) | ✅ 100% Real |
| **Tectonic fault distance** (bonus) | NGDR Fault Tectonic | 206 lineaments (MH+MP) | ✅ 100% Real |
| **Ground truth labels** (`mn_occurrence=1`) | NGDR Major Lease 2022 | 84 Manganese Ore leases | ✅ 100% Real |
| **Spectral indices** (NDVI, Iron Oxide, Clay) | Google Earth Engine Sentinel-2 | 23,957 points | ✅ 100% Real |
| **Elevation & Slope** | NASA SRTM via GEE | 23,593 points | ✅ 100% Real |
| **Rainfall & Temperature** | Open-Meteo Historical API | 1,200 records | ✅ 100% Real |

### What's missing but NOT a blocker:

| Feature | Status | Impact |
|---------|--------|--------|
| Shear zone distance | Only 4 features total (2 per state) | Too sparse. Drop this column or merge into fault distance. Not critical. |
| Odisha & Karnataka data | Not downloaded from NGDR yet | Pipeline works for MH+MP. Can add later for pan-India generalization. |

### 🟢 VERDICT: GO

**You have enough verified, real data to completely drop the synthetic label formula and retrain the prospectivity model.** Specifically:

1. **Replace synthetic `rock_type`** → Use `gpd.sjoin()` with the Lithology GeoDataFrame to assign real `lithologic` values to every grid point.
2. **Replace synthetic `fault_distance_km`** → Use `gdf.geometry.distance()` against the merged Fault GeoDataFrame to compute real nearest-fault distances.
3. **Replace synthetic `mn_occurrence` labels** → Use the 84 Manganese Ore lease polygons as positive labels (`mn_occurrence = 1`). Points outside any manganese lease polygon get `mn_occurrence = 0` (unlabeled, handled by PU-Learning).

No synthetic formulas remain. The entire feature engineering pipeline can now run on 100% real Indian government geospatial data.
