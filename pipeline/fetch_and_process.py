"""
pipeline/fetch_and_process.py
NISAR L2 GCOV Ingestion, Processing & State Management Pipeline.
Interfaces with Alaska Satellite Facility (ASF) Vertex API, extracts calibrated backscatter
matrices from HDF5 granules, converts power ratios to decibels (dB), applies terrain-corrected
spatial bounds, and exports exclusively to Cloud-Optimized GeoTIFFs (COGs). Maintains systemic
state integrity by updating data/processed/manifest.json.
"""

import os
import sys
import json
import argparse
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform_bounds
from typing import Tuple, Dict, Any, List
import pyproj
from global_land_mask import globe

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    import asf_search as asf
except ImportError:
    asf = None

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"
MANIFEST_PATH = os.path.join(PROCESSED_DIR, "manifest.json")


def query_asf_vertex(wkt_geometry: str, start_date: str = "2026-08-01T00:00:00Z", end_date: str = "2026-11-14T23:59:59Z"):
    """
    Executes a programmatic search against the Alaska Satellite Facility (ASF) catalog 
    targeting NISAR L2 GCOV imagery over specified spatial vectors.
    """
    print(f"[INGEST] Querying ASF Vertex catalog over spatial domain footprint...")
    if asf is None:
        print("[WARN] asf_search library not available in environment.")
        return []
    
    try:
        search_results = asf.search(
            platform=[asf.PLATFORM.NISAR],
            processingLevel="GCOV",
            intersectsWith=wkt_geometry,
            start=start_date,
            end=end_date
        )
        print(f"[INGEST] Discovered {len(search_results)} relevant NISAR L2 GCOV granules in ASF catalog.")
        return search_results
    except Exception as e:
        print(f"[WARN] ASF catalog query encountered connection/credentials requirement: {e}")
        return []


def hdf5_to_cog(h5_filepath: str, output_prefix: str, step: int = 0) -> Tuple[str, str, Dict[str, Any]]:
    """
    Extracts backscatter matrix from NISAR HDF5 granule, converts power ratios 
    to decibels (dB), applies georeferenced coordinate bounds, and writes as Cloud-Optimized GeoTIFFs (COGs).
    Exports lightweight _rgb.tif and _hazard.tif rasters adhering to GEMINI ringfencing rules.
    """
    import h5py

    print(f"[TRANSFORM] Processing NISAR HDF5 granule: {h5_filepath}")
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    out_rgb_path = os.path.join(PROCESSED_DIR, f"{output_prefix}_rgb.tif")
    out_hazard_path = os.path.join(PROCESSED_DIR, f"{output_prefix}_hazard.tif")
    
    with h5py.File(h5_filepath, "r") as f:
        # Standard NISAR L2 GCOV HDF5 layer hierarchy
        grids = f["science/LSAR/GCOV/grids"]
        
        # Prefer frequencyB for lightweight processing (multi-looked, ~4000x4000)
        freq = "frequencyB" if "frequencyB" in grids else list(grids.keys())[0]
        grid = grids[freq]
        
        # Spatial reference and coordinate grid
        epsg = int(grid["projection"][()]) if "projection" in grid else 3413
        crs_str = f"EPSG:{epsg}"
        
        xs = grid["xCoordinates"][:]
        ys = grid["yCoordinates"][:]
        dx = float(grid["xCoordinateSpacing"][()])
        dy = float(grid["yCoordinateSpacing"][()])
        
        # Adaptive decimation step to ensure lightweight COG output (< 1.5 MB)
        max_dim = max(len(ys), len(xs))
        if step <= 0:
            step = max(6, round(max_dim / 1000))
        
        # Extract backscatter fields (datasets are direct children of grid)
        has_xpol = False
        if "HHHH" in grid and "HVHV" in grid:
            hh_raw = grid["HHHH"][::step, ::step]
            hv_raw = grid["HVHV"][::step, ::step]
            polarization = "DHDH"
            has_xpol = True
        elif "VVVV" in grid and "VHVH" in grid:
            hh_raw = grid["VVVV"][::step, ::step]
            hv_raw = grid["VHVH"][::step, ::step]
            polarization = "DVDV"
            has_xpol = True
        elif "VVVV" in grid:
            hh_raw = grid["VVVV"][::step, ::step]
            hv_raw = hh_raw * 0.15  # Synthetic cross-pol estimate for single-pol VVVV
            polarization = "VVVV"
            has_xpol = False
        elif "HHHH" in grid:
            hh_raw = grid["HHHH"][::step, ::step]
            hv_raw = hh_raw * 0.15
            polarization = "HHHH"
            has_xpol = False
        else:
            # Fallback to available numerical datasets
            avail_terms = [k for k in grid.keys() if isinstance(grid[k], h5py.Dataset) and k in ["HHHH", "HVHV", "VVVV", "VHVH"]]
            hh_raw = grid[avail_terms[0]][::step, ::step]
            hv_raw = grid[avail_terms[1]][::step, ::step] if len(avail_terms) > 1 else hh_raw * 0.15
            polarization = avail_terms[0] if avail_terms else "Unknown"
            has_xpol = len(avail_terms) > 1

        # Timestamp and metadata
        ident = f.get("science/LSAR/identification")
        if ident and "zeroDopplerStartTime" in ident:
            raw_time = ident["zeroDopplerStartTime"][()]
            if isinstance(raw_time, bytes):
                raw_time = raw_time.decode("utf-8")
            timestamp = raw_time[:19] + "Z"
        else:
            # Parse from filename if available (e.g. 20260824T035109)
            parts = output_prefix.split("_")
            time_part = [p for p in parts if len(p) == 15 and "T" in p]
            if time_part:
                t = time_part[0]
                timestamp = f"{t[:4]}-{t[4:6]}-{t[6:8]}T{t[9:11]}:{t[11:13]}:{t[13:15]}Z"
            else:
                timestamp = "2026-09-15T12:00:00Z"

    # Convert linear power backscatter to decibels (dB)
    valid_hh = (hh_raw > 1e-6) & np.isfinite(hh_raw)
    valid_hv = (hv_raw > 1e-6) & np.isfinite(hv_raw)
    valid_mask = valid_hh & valid_hv

    hh_db = np.where(valid_hh, 10.0 * np.log10(np.maximum(hh_raw, 1e-6)), -9999.0)
    hv_db = np.where(valid_hv, 10.0 * np.log10(np.maximum(hv_raw, 1e-6)), -9999.0)

    # Mask land pixels to 0 (transparent) so Arctic islands never render as Multi-Year Ice
    xs_sub = xs[::step]
    ys_sub = ys[::step]
    yy, xx = np.meshgrid(ys_sub, xs_sub, indexing="ij")
    to_wgs84 = pyproj.Transformer.from_crs(crs_str, "EPSG:4326", always_xy=True)
    lons_grid, lats_grid = to_wgs84.transform(xx, yy)
    land_mask = globe.is_land(lats_grid, lons_grid)
    # Ensure narrow western Barrow Strait entrance channel off Russell Island (74.11-74.14N, -97.85 to -97.65W) is not clipped by 1km land mask
    western_channel = (lats_grid >= 74.11) & (lats_grid <= 74.14) & (lons_grid >= -97.85) & (lons_grid <= -97.65)
    land_mask = land_mask & (~western_channel)
    valid_ocean = valid_mask & (~land_mask)

    # 3-Tier Ice Hazard classification calibrated to NISAR L2 GCOV L-band radiometry:
    # 0: nodata / land (transparent), 1: Open Water, 2: First-Year Ice, 3: Multi-Year / Ridged Ice
    hazard = np.zeros_like(hh_db, dtype=np.uint8)
    is_summer = timestamp[5:7] in ("06", "07", "08", "09")
    if not has_xpol and is_summer:
        # Calibrate single-pol VVVV threshold for wind-roughened summer Bragg backscatter (~ -13 dB)
        open_water = valid_ocean & (hh_db < -11.0)
        myi_ridge = valid_ocean & (hh_db > -7.5)
        fyi_ice = valid_ocean & (~open_water) & (~myi_ridge)
        hh_rgb_db = hh_db - 4.5
        hv_rgb_db = hv_db - 4.5
    else:
        open_water = valid_ocean & ((hh_db < -15.5) | (hv_db < -25.0))
        myi_ridge = valid_ocean & ((hv_db > -18.5) | (hh_db > -9.5))
        fyi_ice = valid_ocean & (~open_water) & (~myi_ridge)
        hh_rgb_db = hh_db
        hv_rgb_db = hv_db

    hazard[open_water] = 1
    hazard[fyi_ice] = 2
    hazard[myi_ridge] = 3

    # Normalized False-Color RGB composite (masked over land):
    # R: HHHH normalized [-24, -6] dB
    # G: HVHV normalized [-26, -12] dB
    # B: HH - HV difference normalized [2, 12] dB
    r = np.clip((hh_rgb_db - (-24.0)) / ((-6.0) - (-24.0)), 0.0, 1.0) * 255.0
    g = np.clip((hv_rgb_db - (-26.0)) / ((-12.0) - (-26.0)), 0.0, 1.0) * 255.0
    diff = hh_rgb_db - hv_rgb_db
    b = np.clip((diff - 2.0) / (12.0 - 2.0), 0.0, 1.0) * 255.0

    r[~valid_ocean] = 0
    g[~valid_ocean] = 0
    b[~valid_ocean] = 0

    rgb = np.stack([r.astype(np.uint8), g.astype(np.uint8), b.astype(np.uint8)])

    # Georeferencing affine transform
    x0 = float(xs[0]) - (dx / 2.0)
    y0 = float(ys[0]) - (dy / 2.0)
    effective_dx = dx * step
    effective_dy = abs(dy) * step
    transform = from_origin(x0, y0, effective_dx, effective_dy)

    # Compute bounding box in EPSG:4326 (WGS84)
    h_rows, w_cols = hh_db.shape
    left = x0
    top = y0
    right = left + (effective_dx * w_cols)
    bottom = top - (effective_dy * h_rows)
    bbox_wgs84 = list(transform_bounds(crs_str, "EPSG:4326", left, bottom, right, top))

    # Write RGB Cloud-Optimized GeoTIFF (3-band uint8, COG driver)
    with rasterio.open(
        out_rgb_path, "w",
        driver="COG",
        height=h_rows, width=w_cols,
        count=3, dtype=np.uint8,
        crs=crs_str, transform=transform,
        compress="deflate"
    ) as dst:
        dst.write(rgb)
        dst.set_band_description(1, "Red (HH Backscatter)")
        dst.set_band_description(2, "Green (HV Backscatter)")
        dst.set_band_description(3, "Blue (HH/HV Ratio)")

    # Write Hazard Classification Cloud-Optimized GeoTIFF (1-band uint8, COG driver)
    with rasterio.open(
        out_hazard_path, "w",
        driver="COG",
        height=h_rows, width=w_cols,
        count=1, dtype=np.uint8,
        crs=crs_str, transform=transform,
        nodata=0, compress="deflate"
    ) as dst:
        dst.write(hazard, 1)
        dst.set_band_description(1, "Ice Hazard Tier (1: Water, 2: FYI, 3: MYI)")

    print(f"[EXPORT] Successfully generated COG rasters at {out_rgb_path} and {out_hazard_path}")
    
    # Build human-readable stage label
    parts = output_prefix.split("_")
    track_info = f"Track {parts[5]}" if len(parts) > 5 else output_prefix[:24]
    stage_label = f"{timestamp[:10]} — NISAR {polarization} ({track_info})"

    metadata = {
        "granule_id": output_prefix,
        "timestamp": timestamp,
        "polarization": polarization,
        "stage_label": stage_label,
        "bbox_wgs84": bbox_wgs84,
        "crs": crs_str
    }
    
    return out_rgb_path, out_hazard_path, metadata


def append_to_manifest(granule_id: str, rgb_path: str, hazard_path: str, metadata: dict):
    """
    Maintains systemic state integrity by tracking outputs in data/processed/manifest.json.
    Supports both list and dictionary schemas.
    """
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    if os.path.exists(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH, "r") as f:
                manifest = json.load(f)
        except json.JSONDecodeError:
            manifest = []
    else:
        manifest = []

    timestamp = metadata.get("timestamp") or metadata.get("acquisition_date") or "2026-09-15T12:00:00Z"
    pol = metadata.get("polarization", "Dual-Pol")
    bbox = metadata.get("bbox_wgs84")
    stage_label = metadata.get("stage_label") or f"{timestamp[:10]} — NISAR {pol} ({granule_id[:28]})"

    record = {
        "granule_id": granule_id,
        "timestamp": timestamp,
        "polarization": pol,
        "stage_label": stage_label,
        "bbox_wgs84": bbox,
        "rgb_path": rgb_path,
        "hazard_path": hazard_path
    }

    if isinstance(manifest, list):
        # Update existing record or append new
        existing = False
        for i, item in enumerate(manifest):
            if isinstance(item, dict) and item.get("granule_id") == granule_id:
                manifest[i] = record
                existing = True
                break
        if not existing:
            manifest.append(record)
    elif isinstance(manifest, dict):
        manifest[granule_id] = record
    else:
        manifest = [record]

    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=4)
    print(f"[STATE] State matrix updated in {MANIFEST_PATH} with record: {granule_id}")


def run_pipeline(generate_sample_cogs: bool = False):
    """
    Orchestrates the ingestion, processing, and state tracking workflow.
    """
    print("=" * 65)
    print("🛳️  NISAR NWP INGESTION & PROCESSING PIPELINE")
    print("=" * 65)
    
    # Check for raw granules in data/raw
    os.makedirs(RAW_DIR, exist_ok=True)
    raw_files = [f for f in sorted(os.listdir(RAW_DIR)) if f.endswith(".h5") or f.endswith(".hdf5")]
    
    if raw_files:
        print(f"[PIPELINE] Found {len(raw_files)} raw HDF5 granules in {RAW_DIR}.")
        for h5_file in raw_files:
            h5_path = os.path.join(RAW_DIR, h5_file)
            prefix = os.path.splitext(h5_file)[0]
            rgb_path, hazard_path, meta = hdf5_to_cog(h5_path, prefix)
            append_to_manifest(prefix, rgb_path, hazard_path, meta)
        print(f"[PIPELINE] All {len(raw_files)} raw granules processed and tracked in {MANIFEST_PATH}.")
    else:
        # Search ASF Vertex for live granules over Barrow Strait
        sample_wkt = "POLYGON((-98.5 73.8, -90.0 73.8, -90.0 75.2, -98.5 75.2, -98.5 73.8))"
        results = query_asf_vertex(sample_wkt)
        
        if not results:
            print("[INFO] No raw .h5 files in data/raw/ and 0 online public granules found.")
            if generate_sample_cogs:
                print("[PIPELINE] Generating calibrated Barrow Strait COGs to populate manifest.json...")
                from app.data_manager import seed_demo_manifest_cogs
                count = seed_demo_manifest_cogs()
                print(f"[PIPELINE] Seeded {count} calibrated scenes into {PROCESSED_DIR} and {MANIFEST_PATH}.")
            else:
                print("[INFO] Fallback mode is active in the dashboard. Pass '--generate-cogs' to create processed COGs.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NISAR NWP Ingestion & Processing Pipeline")
    parser.add_argument("--generate-cogs", action="store_true", help="Generate calibrated sample COGs into data/processed/ and populate manifest.json")
    args = parser.parse_args()
    
    run_pipeline(generate_sample_cogs=args.generate_cogs)
