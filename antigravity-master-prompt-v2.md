# Master Prompt for Antigravity (Opus) — SIH 2026 PS 26009 Prototype

You are my AI pair programmer and solution architect for an SIH 2026 prototype. You have code execution — use it. Build this in stages, run each stage, and fix errors before moving to the next stage. Do not generate all files in one pass with no verification.

## 0. Problem Context (unchanged)
PS 26009: Using AI/ML and space technology to identify manganese reserves and overcome production shortfalls (MOIL Limited). Two modules: manganese prospectivity mapping, and production shortfall prediction. Delivered as a Streamlit dashboard.

## 1. Critical change: one real dataset, not all-synthetic
Before generating any code, write a short script `src/fetch_real_data.py` that pulls real, freely available data for the study area **21.0–21.5°N, 79.0–79.5°E** (this box sits on the actual Nagpur–Bhandara–Balaghat manganese belt — keep these coordinates, they're correct on purpose).

Use whichever of these is actually reachable from this environment:
- Google Earth Engine (Sentinel-2 surface reflectance, NDVI, or ASTER-derived mineral indices) for the box above, exported as a CSV of grid points with real band values.
- Bhuvan/ISRO open data portal, if GEE isn't accessible.
- If neither is reachable in this environment, say so explicitly instead of silently faking it, and fall back to synthetic — but flag this clearly in the README as a known limitation, not something to bury.

This becomes the real backbone for `iron_oxide_index`, `clay_index`, and `ndvi` in the prospectivity dataset. Geological rock-type labels and manganese occurrence points can stay rule-based/synthetic since real labeled occurrence data isn't public, but say so plainly in code comments — don't blend real and fake columns without marking which is which.

Production data (Module 2) stays fully synthetic — there's no public per-mine dataset to pull, and that's fine, just say so in the README.

Only `fetch_real_data.py` should depend on geopandas/rasterio/earthengine-api. The rest of the pipeline (training, dashboard) should run on plain CSVs with pandas/numpy/scikit-learn — don't make the whole project depend on GDAL for no reason.

## 2. Staged build order — run and verify at each step
Do not skip ahead until the previous step's output is confirmed correct.

1. `src/fetch_real_data.py` → run it → print row count and column summary of the real data pulled.
2. `src/generate_data.py` → run it → print `.head()` and `.describe()` of each of the four output CSVs. Confirm columns match what step 3–4 expect before continuing.
3. `src/train_prospectivity.py` → run it → print accuracy/precision/recall/F1 and feature importances. If F1 is suspiciously close to 1.0, add label noise until it's more realistic (aim for 0.75–0.9) — a perfect score just means the model relearned the label rule and that will get noticed.
4. `src/train_production.py` → run it → print MAE/RMSE/R².
5. `app.py` → build last, only after 1–4 produce verified files on disk. Run it and confirm it starts without error and each page renders.

Set `random_state=42` (or any fixed seed) everywhere — data generation, train/test splits, model training. Reproducible numbers matter when you're re-running this live in front of judges.

## 3. Everything else from the original scope stays
- Same project structure (`data/`, `models/`, `notebooks/`, `src/`, `app.py`, `requirements.txt`, `README.md`).
- Same dashboard pages: Home/Overview, Prospectivity Map, Production Forecast & Risk, Data & Model Info.
- Same feature sets for both models as originally specified (geological, terrain, spectral, structural, rainfall for Module 1; planned/actual production, rainfall, equipment availability, blasting days, lag features for Module 2).
- Same shortfall-risk thresholds (<0.9 planned = High, 0.9–0.95 = Medium, else Low).

## 4. New deliverable: judge-facing summary
In addition to the code, produce `PITCH_SUMMARY.md` — one page, no jargon, written for someone who won't read the Python. It must cover, in plain language:
- What problem this solves for MOIL, in one paragraph.
- What's real vs simulated in this prototype, stated plainly (don't bury this in a limitations footnote — put it up front, it's a strength if framed as "validated against real satellite data for the actual ore belt," not a weakness).
- One estimated business number: e.g., "a 5% reduction in production shortfall across 3 mines saves roughly X tons/month" — use round, defensible synthetic numbers and label them as illustrative.
- The one clear next step if MOIL wanted to pilot this for real (e.g., "replace synthetic production data with actual mine logs; extend the real satellite pull to the full lease area").

## 5. Requirements.txt — trimmed
Only add geopandas/rasterio/earthengine-api if `fetch_real_data.py` actually needs them for the source you end up using. Don't include them project-wide by default.

## 6. How to respond
Work through sections 1–2 as actual tool calls with real output shown at each stage, not as a text description of what the code would do. Only after step 5 (app.py) is verified working should you produce the final project tree, full file contents, requirements.txt, README.md, and PITCH_SUMMARY.md together.

If Google Earth Engine or Bhuvan access isn't available in this environment, say so explicitly at step 1 before proceeding, and confirm with me whether to fall back to synthetic-with-disclosure or find another real source, rather than silently defaulting to fake data.
