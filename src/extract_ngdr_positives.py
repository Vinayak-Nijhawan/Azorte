"""
MOIL-GeoSync -- Extract Mn Positive Locations from NGDR GeoJSON
================================================================
Step 1: Extraction only. Reads INDIA_MAJOR_LEASE_2022 and MINERALIZATION
GeoJSON layers, filters for manganese, writes:
  - newdataset/ngdr_mn_positive_locations.csv   (flat table)
  - newdataset/ngdr_mn_leases.geojson           (polygon geometries)

Does NOT modify any model or pipeline code.
"""

import json
import os
import csv
import math
import numpy as np
import pandas as pd
from collections import defaultdict

# -- Paths ------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NGDR_V2 = os.path.join(BASE_DIR, "newdataset", "NGDR", "extracted_v2")
OUT_CSV = os.path.join(BASE_DIR, "newdataset", "ngdr_mn_positive_locations.csv")
OUT_GEOJSON = os.path.join(BASE_DIR, "newdataset", "ngdr_mn_leases.geojson")
EXISTING_DATASET = os.path.join(BASE_DIR, "data", "prospectivity_real_dataset.csv")

# Study area bounding box
BBOX_LAT_MIN, BBOX_LAT_MAX = 21.0, 22.1
BBOX_LON_MIN, BBOX_LON_MAX = 79.0, 80.5

BLOCK_SIZE = 0.1  # degrees -- for spatial block counting

# -- Geometry helpers (no shapely dependency) -------------------------------

def polygon_centroid_and_bounds(geometry):
    """
    Compute centroid and bounding box from a GeoJSON geometry dict.
    Handles Polygon and MultiPolygon. Returns (lat, lon, minx, miny, maxx, maxy, area_sq_m).
    Area is approximate (using equirectangular projection at centroid latitude).
    """
    geom_type = geometry["type"]
    
    if geom_type == "Polygon":
        rings = geometry["coordinates"]
    elif geom_type == "MultiPolygon":
        # Flatten to a list of rings (use all outer rings)
        rings = [poly[0] for poly in geometry["coordinates"]]
    else:
        return None

    all_coords = []
    for ring in rings:
        if geom_type == "Polygon":
            # ring IS the coordinates list for Polygon
            if isinstance(ring[0], (int, float)):
                # It's a flat list -- shouldn't happen but guard
                break
            if isinstance(ring[0], list) and isinstance(ring[0][0], (int, float)):
                all_coords.extend(ring)
            else:
                # Nested ring (outer ring is ring[0] for Polygon)
                all_coords.extend(ring)
        else:
            all_coords.extend(ring)

    if not all_coords:
        return None

    lons = [c[0] for c in all_coords]
    lats = [c[1] for c in all_coords]

    centroid_lon = sum(lons) / len(lons)
    centroid_lat = sum(lats) / len(lats)
    minx, maxx = min(lons), max(lons)
    miny, maxy = min(lats), max(lats)

    # Approximate area in m² using Shoelace formula + equirectangular
    # Convert coords to meters relative to centroid
    cos_lat = math.cos(math.radians(centroid_lat))
    DEG_TO_M_LAT = 111320.0
    DEG_TO_M_LON = 111320.0 * cos_lat

    # Use the outer ring only (first ring for Polygon)
    if geom_type == "Polygon":
        outer = geometry["coordinates"][0]
    else:
        # Use the largest polygon's outer ring
        outer = max([poly[0] for poly in geometry["coordinates"]], key=len)

    # Shoelace
    n = len(outer)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        x_i = (outer[i][0] - centroid_lon) * DEG_TO_M_LON
        y_i = (outer[i][1] - centroid_lat) * DEG_TO_M_LAT
        x_j = (outer[j][0] - centroid_lon) * DEG_TO_M_LON
        y_j = (outer[j][1] - centroid_lat) * DEG_TO_M_LAT
        area += x_i * y_j - x_j * y_i
    area = abs(area) / 2.0

    return centroid_lat, centroid_lon, minx, miny, maxx, maxy, area


def point_coords(geometry):
    """Extract (lat, lon) from a GeoJSON Point geometry."""
    coords = geometry["coordinates"]
    return coords[1], coords[0]  # GeoJSON is [lon, lat]


def in_bbox(lat, lon):
    return BBOX_LAT_MIN <= lat <= BBOX_LAT_MAX and BBOX_LON_MIN <= lon <= BBOX_LON_MAX


def block_id(lat, lon):
    return f"{int(math.floor(lat / BLOCK_SIZE))}_{int(math.floor(lon / BLOCK_SIZE))}"


# -- Step 1: Print schemas -------------------------------------------------

def find_geojson(layer_prefix, state):
    """Find the .geojson file for a given layer prefix and state."""
    for d in os.listdir(NGDR_V2):
        if f"{layer_prefix}_STATE_{state}" in d:
            path_dir = os.path.join(NGDR_V2, d)
            for f in os.listdir(path_dir):
                if f.endswith(".geojson"):
                    return os.path.join(path_dir, f)
    return None


def load_geojson(filepath):
    with open(filepath, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main():
    print("=" * 70)
    print("MOIL-GeoSync -- NGDR Mn Positive Extraction (Step 1)")
    print(f"Study BBOX: lat [{BBOX_LAT_MIN}, {BBOX_LAT_MAX}], lon [{BBOX_LON_MIN}, {BBOX_LON_MAX}]")
    print("=" * 70)

    records = []          # All extracted Mn records
    geojson_features = [] # For lease polygon GeoJSON output

    # -- A) LEASE LAYERS ------------------------------------------------
    for state in ["MADHYA_PRADESH", "MAHARASHTRA"]:
        filepath = find_geojson("INDIA_MAJOR_LEASE_2022", state)
        if not filepath:
            print(f"\n[WARN] No lease GeoJSON found for {state}")
            continue

        data = load_geojson(filepath)
        features = data.get("features", [])
        state_label = "Madhya Pradesh" if "MADHYA" in state else "Maharashtra"

        print(f"\n-- LEASE {state_label} --")
        print(f"  File: {os.path.basename(filepath)}")
        print(f"  Total features: {len(features)}")
        if features:
            print(f"  Schema: {list(features[0]['properties'].keys())}")
            print(f"  Commodity field: 'mineral_na' (primary), 'name_of_as' (associated)")

        for feat in features:
            props = feat["properties"]
            geom = feat["geometry"]
            mineral_na = str(props.get("mineral_na", "") or "").strip()
            name_of_as = str(props.get("name_of_as", "") or "").strip()

            is_primary_mn = "manganese" in mineral_na.lower()
            is_assoc_mn = "manganese" in name_of_as.lower() or "manga" in name_of_as.lower()

            if not is_primary_mn and not is_assoc_mn:
                continue

            # Compute centroid and bounds
            result = polygon_centroid_and_bounds(geom)
            if result is None:
                print(f"  [SKIP] Could not parse geometry for gid={props.get('gid')}")
                continue

            centroid_lat, centroid_lon, minx, miny, maxx, maxy, area_sqm = result
            mixed = not is_primary_mn and is_assoc_mn  # associated Mn only

            rec = {
                "lease_id": props.get("gid"),
                "mine_code": props.get("mine_code", ""),
                "mine_name": props.get("mine_name", ""),
                "lessee": props.get("name_of_le", ""),
                "state": state_label,
                "district": props.get("district", ""),
                "taluka": props.get("taluka", ""),
                "mineral_na": mineral_na,
                "name_of_as": name_of_as,
                "mixed_commodity": mixed,
                "method": props.get("method_of_", ""),
                "dispatches": props.get("dispatches_tons_1920_2021_2122", ""),
                "psu_private": props.get("psu_privat", ""),
                "centroid_lat": round(centroid_lat, 6),
                "centroid_lon": round(centroid_lon, 6),
                "minx": round(minx, 6),
                "miny": round(miny, 6),
                "maxx": round(maxx, 6),
                "maxy": round(maxy, 6),
                "area_sqm": round(area_sqm, 1),
                "in_bbox": in_bbox(centroid_lat, centroid_lon),
                "source": "lease",
            }
            records.append(rec)

            # Save polygon geometry for GeoJSON output
            geojson_features.append({
                "type": "Feature",
                "properties": {
                    "lease_id": rec["lease_id"],
                    "mine_name": rec["mine_name"],
                    "state": rec["state"],
                    "mineral_na": rec["mineral_na"],
                    "mixed_commodity": rec["mixed_commodity"],
                    "in_bbox": rec["in_bbox"],
                },
                "geometry": geom,
            })

    # -- B) MINERALIZATION LAYERS ---------------------------------------
    for state in ["MADHYA_PRADESH", "MAHARASHTRA"]:
        filepath = find_geojson("MINERALIZATION", state)
        if not filepath:
            print(f"\n[WARN] No mineralization GeoJSON found for {state}")
            continue

        data = load_geojson(filepath)
        features = data.get("features", [])
        state_label = "Madhya Pradesh" if "MADHYA" in state else "Maharashtra"

        print(f"\n-- MINERALIZATION {state_label} --")
        print(f"  File: {os.path.basename(filepath)}")
        print(f"  Total features: {len(features)}")
        if features:
            print(f"  Schema: {list(features[0]['properties'].keys())}")
            print(f"  Commodity field: 'commodity'")

        for feat in features:
            props = feat["properties"]
            geom = feat["geometry"]
            commodity = str(props.get("commodity", "") or "").strip()

            if "manganese" not in commodity.lower() and "manga" not in commodity.lower():
                continue

            lat, lon = point_coords(geom)

            rec = {
                "lease_id": props.get("gid"),
                "mine_code": "",
                "mine_name": "",
                "lessee": "",
                "state": state_label,
                "district": "",
                "taluka": "",
                "mineral_na": commodity,
                "name_of_as": "",
                "mixed_commodity": False,
                "method": "",
                "dispatches": "",
                "psu_private": "",
                "centroid_lat": round(lat, 6),
                "centroid_lon": round(lon, 6),
                "minx": round(lon, 6),
                "miny": round(lat, 6),
                "maxx": round(lon, 6),
                "maxy": round(lat, 6),
                "area_sqm": 0.0,
                "in_bbox": in_bbox(lat, lon),
                "source": "mineralization",
            }
            records.append(rec)

    # -- C) Write outputs -----------------------------------------------
    df = pd.DataFrame(records)

    # Save CSV
    df.to_csv(OUT_CSV, index=False)
    print(f"\n[SAVED] {OUT_CSV} ({len(df)} records)")

    # Save GeoJSON (lease polygons only)
    geojson_out = {
        "type": "FeatureCollection",
        "features": geojson_features,
    }
    with open(OUT_GEOJSON, "w", encoding="utf-8") as fh:
        json.dump(geojson_out, fh, indent=2)
    print(f"[SAVED] {OUT_GEOJSON} ({len(geojson_features)} polygon features)")

    # -- D) Summary -----------------------------------------------------
    print("\n" + "=" * 70)
    print("EXTRACTION SUMMARY")
    print("=" * 70)

    # Per state + layer
    for source in ["lease", "mineralization"]:
        subset = df[df["source"] == source]
        print(f"\n  Source: {source.upper()}")
        for state in df["state"].unique():
            s = subset[subset["state"] == state]
            in_box = s[s["in_bbox"] == True]
            mixed = s[s["mixed_commodity"] == True]
            print(f"    {state:25s}: {len(s):3d} total, {len(in_box):3d} in BBOX, {len(mixed):3d} mixed-commodity")

    # BBOX summary
    in_bbox_df = df[df["in_bbox"] == True]
    in_bbox_primary = in_bbox_df[in_bbox_df["mixed_commodity"] == False]
    in_bbox_mixed = in_bbox_df[in_bbox_df["mixed_commodity"] == True]

    print(f"\n  INSIDE BBOX ({BBOX_LAT_MIN}-{BBOX_LAT_MAX}N, {BBOX_LON_MIN}-{BBOX_LON_MAX}E):")
    print(f"    Total Mn records:      {len(in_bbox_df)}")
    print(f"    Primary Mn leases:     {len(in_bbox_primary[in_bbox_primary['source']=='lease'])}")
    print(f"    Mixed-commodity leases: {len(in_bbox_mixed[in_bbox_mixed['source']=='lease'])}")
    print(f"    Mineralization points:  {len(in_bbox_df[in_bbox_df['source']=='mineralization'])}")

    # Unique 0.1-degree blocks
    if len(in_bbox_df) > 0:
        in_bbox_df = in_bbox_df.copy()
        in_bbox_df["block_id"] = in_bbox_df.apply(
            lambda r: block_id(r["centroid_lat"], r["centroid_lon"]), axis=1
        )
        n_blocks = in_bbox_df["block_id"].nunique()
        print(f"    Unique 0.1 deg blocks:    {n_blocks}")

        # Block distribution
        block_counts = in_bbox_df["block_id"].value_counts()
        print(f"\n    Block distribution (leases per block):")
        for bid, cnt in block_counts.items():
            print(f"      {bid}: {cnt} record(s)")

    # -- E) Compare with existing 17 positives --------------------------
    print(f"\n  COMPARISON WITH EXISTING POSITIVES:")
    try:
        existing = pd.read_csv(EXISTING_DATASET, comment="#")
        existing_pos = existing[existing["mn_occurrence"] == 1]
        print(f"    Existing positives in dataset: {len(existing_pos)}")

        if len(existing_pos) > 0 and len(in_bbox_df) > 0:
            # Match by proximity: existing positive within 0.02 deg (~2.2km) of new NGDR centroid
            match_count = 0
            matched_existing = set()
            for _, ngdr_row in in_bbox_df.iterrows():
                for idx, ex_row in existing_pos.iterrows():
                    dist = math.sqrt(
                        (ngdr_row["centroid_lat"] - ex_row["latitude"]) ** 2
                        + (ngdr_row["centroid_lon"] - ex_row["longitude"]) ** 2
                    )
                    if dist < 0.02:  # ~2.2 km
                        if idx not in matched_existing:
                            matched_existing.add(idx)
                if len(matched_existing) == len(existing_pos):
                    break

            print(f"    Existing positives matched to NGDR leases (within 2km): {len(matched_existing)} / {len(existing_pos)}")
            print(f"    Existing positives NOT matched: {len(existing_pos) - len(matched_existing)}")
    except Exception as e:
        print(f"    [ERROR] Could not load existing dataset: {e}")

    # OUTSIDE BBOX
    out_bbox_df = df[df["in_bbox"] == False]
    print(f"\n  OUTSIDE BBOX (not used):")
    print(f"    Total: {len(out_bbox_df)}")
    for state in df["state"].unique():
        s = out_bbox_df[out_bbox_df["state"] == state]
        print(f"    {state:25s}: {len(s)}")

    # -- F) Print first 20 rows -----------------------------------------
    print(f"\n{'=' * 70}")
    print("FIRST 20 ROWS (in-BBOX first, sorted by state then mine_name)")
    print("=" * 70)
    display_df = df.sort_values(
        ["in_bbox", "state", "mine_name"], ascending=[False, True, True]
    ).head(20)
    cols_to_show = [
        "lease_id", "mine_name", "state", "district", "mineral_na",
        "mixed_commodity", "centroid_lat", "centroid_lon", "area_sqm",
        "in_bbox", "source",
    ]
    print(display_df[cols_to_show].to_string(index=False))

    print(f"\n{'=' * 70}")
    print("STEP 1 COMPLETE. Waiting for approval before proceeding to Step 2.")
    print("=" * 70)


if __name__ == "__main__":
    main()
