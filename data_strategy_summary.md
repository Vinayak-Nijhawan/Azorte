# MOIL-GeoSync: Master Data Strategy & Documentation

This document tracks all the data used in the project, what is 100% real, what is synthetic, and the upcoming data tasks. This is crucial for presenting our data authenticity to the SIH Judges.

---

## 1. 🟩 100% REAL DATA (Successfully Collected)

These datasets are completely real and fetched via official APIs or reports. They are stored in the `newdataset/` folder.

### A. Satellite Spectral Data (`spectral_real.csv`)
* **Source:** Sentinel-2 L2A via Google Earth Engine (ESA Copernicus).
* **What it has:** Real NDVI, Iron Oxide Index, Clay Index, and raw spectral bands for 23,957 coordinates.
* **Fayda (Pros):** Highly accurate, real surface reflectance for Central India, Odisha, and Karnataka. Shows actual vegetation and mineral signatures.
* **Dikkat (Cons):** Heavy to process. API calls take 15-20 mins if generated from scratch.

### B. Terrain Data (`elevation_real.csv`)
* **Source:** NASA SRTM 30m Digital Elevation Model via GEE.
* **What it has:** Real elevation (meters) and slope (degrees) for all grid points.
* **Fayda (Pros):** 100% real topography. Manganese is often found on specific slope profiles.

### C. Historical Weather Data (`weather_real.csv`)
* **Source:** Open-Meteo Historical API (ERA5 Reanalysis).
* **What it has:** 10 years (2016-2025) of monthly rainfall and temperature data for 10 mine locations.
* **Fayda (Pros):** Essential for training the production model to understand monsoon-driven production dips.

### D. MOIL Production Baselines (`moil_production_real.csv`)
* **Source:** Official MOIL Annual Reports & IBM Minerals Yearbook.
* **What it has:** Real yearly tonnage and revenue data (2016-2025).
* **Fayda (Pros):** Anchors our synthetic daily production data to real-world financial and operational realities.

---

## 2. 🟨 SEMI-SYNTHETIC DATA (Domain-Informed)

We tried to fetch real spatial shapefiles, but Indian Govt (GSI/NGDR) servers block automated API scripts. So, we engineered a smart workaround.

### A. Geological Rock Types & Faults
* **Source:** GSI G4 Exploration Report (Mandri-Panchala) extracted from `MANDRI-PANCHALA.rar`.
* **What it has:** We replaced fake names with 100% REAL GSI terminology (e.g., `Mansar_Quartz_Mica_Schist`, `Gondite_Horizon`, `Tirodi_Biotite_Gneiss`).
* **Fayda (Pros):** The ML model learns authentic Indian geological rules. Judges will be impressed by the deep domain research.
* **Dikkat (Cons):** The *spatial distribution* (which rock is at which exact GPS coordinate) is mathematically simulated. 
* **Fix for Judges:** Explain that the GSI API is locked, so we built a simulator calibrated with real GSI report logic.

---

## 3. 🟥 TO-DO: DATA TO BE FETCHED / IMPLEMENTED

These are the datasets and features we discussed that are currently missing or pending integration.

- [ ] **Live Weather API Integration**
  - *Plan:* Add a live API call to the Streamlit Dashboard (`app.py`).
  - *Purpose:* When judges view the "Fleet Dispatch" page, it should fetch today's exact live weather for Nagpur and adjust fleet speeds dynamically (e.g., "Heavy rain detected, reducing dumper speed by 15%").
  
- [ ] **Kaggle Process/Fleet Data**
  - *Plan:* Implement the "Quality Prediction in a Mining Process" dataset.
  - *Purpose:* To show real-time ore processing telemetry (flow rates, silica %, density) in Module 2 (Production/Optimization).

- [ ] **USGS MRDS Known Deposits**
  - *Plan:* Fetch CSV of known Indian Manganese deposit coordinates from USGS global database.
  - *Purpose:* Use them as "Ground Truth" (Positive Labels = 1) to validate our Prospectivity predictions.

- [ ] **Main Pipeline Integration**
  - *Plan:* Modify `src/generate_data.py` and `src/train_prospectivity.py` to completely drop the old synthetic random numbers and ONLY use the 4 CSVs from `newdataset/`.
