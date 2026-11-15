"""
app/data_manager.py
Unified Data Ingestion & State Management Layer for NISAR NWP Navigator.
Inspects data/processed/ for manifest.json and Cloud-Optimized GeoTIFFs (COGs).
Seamlessly falls back to calibrated synthetic Barrow Strait stages if manifest.json
is absent or has fewer than 2 scenes, while prioritizing real GeoTIFFs when present.
Supports both list and dictionary schemas for manifest.json and both EPSG:4326 and EPSG:3413 rasters.
"""

import os
import json
import numpy as np
import rasterio
from rasterio.warp import transform_bounds
from typing import Dict, Any, Tuple, List, Optional
from PIL import Image
import io
import base64

from app.synthetic import (
    get_stage_dataset,
    STAGE_METADATA,
    BOUNDS_FOLIUM,
    TRANSFORM,
    array_to_base64_png,
    generate_dualpol_rgb,
    generate_hazard_rgba,
    write_synthetic_stage_to_cogs
)

PROCESSED_DIR = "data/processed"
MANIFEST_PATH = os.path.join(PROCESSED_DIR, "manifest.json")


def inspect_manifest() -> Dict[str, Any]:
    """
    Inspects data/processed/manifest.json and validates available scenes.
    Handles both list-of-dicts and dict-of-dicts manifest formats.
    """
    if not os.path.exists(MANIFEST_PATH):
        return {
            "exists": False,
            "scene_count": 0,
            "is_fallback": True,
            "mode": "SYNTHETIC_FALLBACK",
            "message": "manifest.json not found in data/processed/. Operating on calibrated synthetic Barrow Strait radar arrays.",
            "scenes": STAGE_METADATA
        }

    try:
        with open(MANIFEST_PATH, "r") as f:
            manifest_data = json.load(f)
    except Exception as e:
        return {
            "exists": True,
            "scene_count": 0,
            "is_fallback": True,
            "mode": "SYNTHETIC_FALLBACK",
            "message": f"Error parsing manifest.json ({e}). Defaulting to calibrated synthetic arrays.",
            "scenes": STAGE_METADATA
        }

    # Normalize manifest_data into a dictionary keyed by granule_id
    raw_records = {}
    if isinstance(manifest_data, list):
        for idx, item in enumerate(manifest_data):
            if isinstance(item, dict):
                gid = item.get("granule_id") or item.get("id") or f"scene_{idx:02d}"
                raw_records[gid] = item
    elif isinstance(manifest_data, dict):
        raw_records = manifest_data
    else:
        raw_records = {}

    valid_scenes = {}
    for gid, record in raw_records.items():
        # Check potential raster file paths
        rgb_path = record.get("rgb_path") or record.get("cog_filepath") or record.get("cog_path")
        hazard_path = record.get("hazard_path") or record.get("hazard_filepath")
        
        # Valid if at least one raster exists on disk
        has_rgb = bool(rgb_path and os.path.exists(rgb_path))
        has_hazard = bool(hazard_path and os.path.exists(hazard_path))

        if has_rgb or has_hazard:
            primary_path = rgb_path if has_rgb else hazard_path
            timestamp = record.get("timestamp") or record.get("acquisition_date") or "2026-09-15"
            stage_label = record.get("stage_label") or f"{gid[:32]}... ({timestamp[:10]})"
            
            valid_scenes[gid] = {
                "granule_id": gid,
                "rgb_path": rgb_path if has_rgb else None,
                "hazard_path": hazard_path if has_hazard else None,
                "primary_path": primary_path,
                "timestamp": timestamp,
                "acquisition_date": timestamp,
                "stage_label": stage_label,
                "polarization": record.get("polarization", "Dual-Pol"),
                "bbox_wgs84": record.get("bbox_wgs84"),
                "raw_record": record
            }

    count = len(valid_scenes)
    if count < 2:
        return {
            "exists": True,
            "scene_count": count,
            "is_fallback": True,
            "mode": "SYNTHETIC_FALLBACK",
            "message": f"manifest.json contains {count} valid scene(s) (< 2 required). Defaulting to calibrated synthetic Barrow Strait stages.",
            "scenes": STAGE_METADATA,
            "manifest_records": valid_scenes
        }

    return {
        "exists": True,
        "scene_count": count,
        "is_fallback": False,
        "mode": "REAL_MANIFEST",
        "message": f"Successfully loaded {count} validated NISAR L2 GCOV scenes from manifest.json.",
        "scenes": valid_scenes
    }


def load_scene_dataset(scene_id: str, manifest_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Unified loader returning complete raster data, visualizations, and stats
    for either a synthetic stage or a real manifest GeoTIFF record.
    """
    if manifest_info is None:
        manifest_info = inspect_manifest()

    # Fallback to calibrated synthetic stages
    if manifest_info["is_fallback"] or scene_id in STAGE_METADATA:
        if scene_id not in STAGE_METADATA:
            scene_id = "sep_myi_intrusion"
        ds = get_stage_dataset(scene_id)
        ds["source_type"] = "Calibrated Synthetic L-Band Simulation"
        return ds

    # Real Manifest Scene Loading
    record = manifest_info["scenes"].get(scene_id)
    if not record:
        ds = get_stage_dataset("sep_myi_intrusion")
        ds["source_type"] = "Calibrated Synthetic L-Band Simulation"
        return ds

    rgb_path = record.get("rgb_path")
    hazard_path = record.get("hazard_path")
    primary_path = record.get("primary_path") or rgb_path or hazard_path

    # Read geometry and coordinate projection info from primary GeoTIFF
    with rasterio.open(primary_path) as src:
        crs = src.crs
        src_bounds = src.bounds
        src_transform = src.transform
        src_shape = src.shape

        # Reproject bounds to EPSG:4326 for Folium
        if crs and str(crs).upper() not in ["EPSG:4326", "WGS84"]:
            w, s, e, n = transform_bounds(crs, "EPSG:4326", *src_bounds)
        else:
            w, s, e, n = src_bounds.left, src_bounds.bottom, src_bounds.right, src_bounds.top

    # Check if bbox_wgs84 override is present in manifest
    if record.get("bbox_wgs84") and len(record["bbox_wgs84"]) == 4:
        bw, bs, be, bn = record["bbox_wgs84"]
        bounds_folium = [[bs, bw], [bn, be]]
    else:
        bounds_folium = [[s, w], [n, e]]

    # Process Hazard Layer
    if hazard_path and os.path.exists(hazard_path):
        with rasterio.open(hazard_path) as h_src:
            hazard = h_src.read(1).astype(np.uint8)
    else:
        # Fallback empty hazard grid
        hazard = np.ones(src_shape, dtype=np.uint8)

    # Process or Generate Hazard RGBA
    h_h, h_w = hazard.shape
    hazard_rgba = np.zeros((h_h, h_w, 4), dtype=np.uint8)
    # Class 0: Nodata / Transparent
    hazard_rgba[hazard == 1] = [21, 101, 192, 190]   # Open Water Blue
    hazard_rgba[hazard == 2] = [0, 188, 212, 205]    # First-Year Ice Cyan
    hazard_rgba[hazard == 3] = [213, 0, 0, 230]      # Multi-Year Ice Red
    hazard_data_url = array_to_base64_png(hazard_rgba)

    # Process RGB Layer
    if rgb_path and os.path.exists(rgb_path):
        with rasterio.open(rgb_path) as r_src:
            if r_src.count >= 3:
                rgb_raw = r_src.read([1, 2, 3])  # (3, H, W)
                rgb_t = np.transpose(rgb_raw, (1, 2, 0))  # (H, W, 3)
                # Alpha channel with transparency for nodata (0, 0, 0)
                is_data = (rgb_t[:, :, 0] > 0) | (rgb_t[:, :, 1] > 0) | (rgb_t[:, :, 2] > 0)
                alpha = np.where(is_data, 220, 0).astype(np.uint8)
                rgb_rgba = np.dstack([rgb_t, alpha])
                
                # Approximate calibrated dB values for distribution histograms
                r_norm = rgb_t[:, :, 0].astype(np.float32) / 255.0
                g_norm = rgb_t[:, :, 1].astype(np.float32) / 255.0
                hh_db = -28.0 + (r_norm * 22.0)
                hv_db = -34.0 + (g_norm * 22.0)
            elif r_src.count == 2:
                # 2-band float backscatter (HH, HV)
                hh_db = r_src.read(1)
                hv_db = r_src.read(2)
                rgb_rgba = generate_dualpol_rgb(hh_db, hv_db)
            else:
                hh_db = r_src.read(1)
                hv_db = hh_db - 8.0
                rgb_rgba = generate_dualpol_rgb(hh_db, hv_db)
    else:
        # Reconstruct pseudo-RGB from hazard
        hh_db = np.where(hazard == 3, -11.0, np.where(hazard == 2, -17.0, -23.0))
        hv_db = np.where(hazard == 3, -16.0, np.where(hazard == 2, -25.0, -32.0))
        rgb_rgba = generate_dualpol_rgb(hh_db, hv_db)

    rgb_data_url = array_to_base64_png(rgb_rgba)

    # Calculate ice concentration statistics excluding nodata (0)
    valid_mask = (hazard >= 1) & (hazard <= 3)
    total_valid = int(np.sum(valid_mask))
    if total_valid > 0:
        p1 = float(np.sum(hazard == 1) / total_valid * 100.0)
        p2 = float(np.sum(hazard == 2) / total_valid * 100.0)
        p3 = float(np.sum(hazard == 3) / total_valid * 100.0)
    else:
        p1, p2, p3 = 100.0, 0.0, 0.0

    stage_name = record.get("stage_label", scene_id)
    acq_date = record.get("timestamp", "2026-09-15")

    return {
        "stage_id": scene_id,
        "name": stage_name,
        "date_str": acq_date,
        "phase": f"NISAR Ingested Swath ({record.get('polarization', 'L-band')})",
        "summary": f"NISAR L2 GCOV Observation: {scene_id}",
        "ice_condition": f"Classified Ice: {p1:.1f}% Water, {p2:.1f}% FYI, {p3:.1f}% MYI",
        "typical_hh": f"Estimated Mean {np.mean(hh_db[valid_mask] if total_valid > 0 else hh_db):.1f} dB",
        "typical_hv": f"Estimated Mean {np.mean(hv_db[valid_mask] if total_valid > 0 else hv_db):.1f} dB",
        "hh_db": hh_db,
        "hv_db": hv_db,
        "hazard": hazard,
        "hazard_source": hazard_path or hazard,
        "rgb_rgba": rgb_rgba,
        "hazard_rgba": hazard_rgba,
        "rgb_data_url": rgb_data_url,
        "hazard_data_url": hazard_data_url,
        "bounds": bounds_folium,
        "transform": src_transform,
        "crs": str(crs),
        "open_water_pct": p1,
        "fyi_pct": p2,
        "myi_pct": p3,
        "mean_hh_db": float(np.mean(hh_db[valid_mask] if total_valid > 0 else hh_db)),
        "mean_hv_db": float(np.mean(hv_db[valid_mask] if total_valid > 0 else hv_db)),
        "source_type": "Real NISAR L2 GCOV GeoTIFF (from manifest.json)"
    }


def seed_demo_manifest_cogs() -> int:
    """
    Utility to generate sample GeoTIFFs into data/processed/ and populate manifest.json
    with all three shipping stages, allowing manual verification of real manifest ingestion.
    """
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    manifest = []

    for stage_id in ["aug_open_water", "sep_myi_intrusion", "oct_freeze_up"]:
        cog_path, hazard_path = write_synthetic_stage_to_cogs(stage_id, PROCESSED_DIR)
        meta = STAGE_METADATA[stage_id]
        gid = f"NISAR_L2_GCOV_{meta['date_str'].replace('-', '')}_BARROW_STRAIT"
        
        manifest.append({
            "granule_id": gid,
            "timestamp": meta["date_str"] + "T12:00:00Z",
            "polarization": "Dual-Pol (HHHH, HVHV)",
            "stage_label": meta["name"],
            "rgb_path": cog_path,
            "hazard_path": hazard_path,
            "bbox_wgs84": [-98.5, 73.8, -90.0, 75.2]
        })

    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=4)

    return len(manifest)


def clear_manifest_for_fallback_testing():
    """Removes manifest.json to test fallback behavior."""
    if os.path.exists(MANIFEST_PATH):
        os.remove(MANIFEST_PATH)
