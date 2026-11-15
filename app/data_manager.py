"""
app/data_manager.py
Unified Data Ingestion & State Management Layer for NISAR NWP Navigator.
Inspects data/processed/ for manifest.json and Cloud-Optimized GeoTIFFs (COGs).
Seamlessly falls back to calibrated synthetic Barrow Strait stages if manifest.json
is absent or has fewer than 2 scenes, while prioritizing real GeoTIFFs when present.
"""

import os
import json
import numpy as np
import rasterio
from typing import Dict, Any, Tuple, List, Optional
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
    Returns metadata regarding whether fallback mode is active.
    """
    if not os.path.exists(MANIFEST_PATH):
        return {
            "exists": False,
            "scene_count": 0,
            "is_fallback": True,
            "mode": "SYNTHETIC_FALLBACK",
            "message": "manifest.json not found in data/processed/. Seamlessly operating on calibrated synthetic Barrow Strait radar arrays.",
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

    valid_scenes = {}
    for gid, record in manifest_data.items():
        cog_path = record.get("cog_filepath")
        # Validate that the raster file exists on disk
        if cog_path and os.path.exists(cog_path):
            valid_scenes[gid] = record

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
        # If scene_id is not in STAGE_METADATA, default to first available
        if scene_id not in STAGE_METADATA:
            scene_id = "sep_myi_intrusion"
        ds = get_stage_dataset(scene_id)
        ds["source_type"] = "Calibrated Synthetic L-Band Simulation"
        return ds

    # Real Manifest Scene Loading
    record = manifest_info["scenes"].get(scene_id)
    if not record:
        # Fallback if specific scene_id not found in manifest
        ds = get_stage_dataset("sep_myi_intrusion")
        ds["source_type"] = "Calibrated Synthetic L-Band Simulation"
        return ds

    cog_path = record["cog_filepath"]
    hazard_path = record.get("hazard_filepath")

    # Read dual-pol backscatter from GeoTIFF
    with rasterio.open(cog_path) as src:
        band_count = src.count
        hh_db = src.read(1)
        hv_db = src.read(2) if band_count >= 2 else (hh_db - 8.0)
        transform = src.transform
        bounds_box = src.bounds
        crs = str(src.crs)

    # Read or calculate hazard grid
    if hazard_path and os.path.exists(hazard_path):
        with rasterio.open(hazard_path) as h_src:
            hazard = h_src.read(1).astype(np.uint8)
    else:
        # Classify hazard deterministically from HH and HV
        hazard = np.ones_like(hh_db, dtype=np.uint8)
        hazard[(hv_db >= -27.0) | (hh_db >= -20.0)] = 2
        hazard[(hv_db >= -19.5) & (hh_db >= -14.0)] = 3

    # Generate RGBA composites
    rgb_rgba = generate_dualpol_rgb(hh_db, hv_db)
    hazard_rgba = generate_hazard_rgba(hazard)

    rgb_data_url = array_to_base64_png(rgb_rgba)
    hazard_data_url = array_to_base64_png(hazard_rgba)

    # Folium bounds format [[min_lat, min_lon], [max_lat, max_lon]]
    bounds_folium = [
        [bounds_box.bottom, bounds_box.left],
        [bounds_box.top, bounds_box.right]
    ]

    total_px = hazard.size
    p1 = float(np.sum(hazard == 1) / total_px * 100.0)
    p2 = float(np.sum(hazard == 2) / total_px * 100.0)
    p3 = float(np.sum(hazard == 3) / total_px * 100.0)

    stage_name = record.get("stage_label", scene_id)
    acq_date = record.get("acquisition_date", "2026-09-15")

    return {
        "stage_id": scene_id,
        "name": stage_name,
        "date_str": acq_date,
        "phase": record.get("metadata", {}).get("phase", "Operational Ingestion"),
        "summary": record.get("metadata", {}).get("summary", f"NISAR L2 GCOV Scene: {scene_id}"),
        "ice_condition": f"Classified Ice: {p1:.1f}% Water, {p2:.1f}% FYI, {p3:.1f}% MYI",
        "typical_hh": f"Mean {np.mean(hh_db):.1f} dB",
        "typical_hv": f"Mean {np.mean(hv_db):.1f} dB",
        "hh_db": hh_db,
        "hv_db": hv_db,
        "hazard": hazard,
        "rgb_rgba": rgb_rgba,
        "hazard_rgba": hazard_rgba,
        "rgb_data_url": rgb_data_url,
        "hazard_data_url": hazard_data_url,
        "bounds": bounds_folium,
        "transform": transform,
        "crs": crs,
        "open_water_pct": p1,
        "fyi_pct": p2,
        "myi_pct": p3,
        "mean_hh_db": float(np.mean(hh_db)),
        "mean_hv_db": float(np.mean(hv_db)),
        "source_type": "Real NISAR L2 GCOV GeoTIFF (from manifest.json)"
    }


def seed_demo_manifest_cogs() -> int:
    """
    Utility to generate sample GeoTIFFs into data/processed/ and populate manifest.json
    with all three shipping stages, allowing manual verification of real manifest ingestion.
    """
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    manifest = {}

    for stage_id in ["aug_open_water", "sep_myi_intrusion", "oct_freeze_up"]:
        cog_path, hazard_path = write_synthetic_stage_to_cogs(stage_id, PROCESSED_DIR)
        meta = STAGE_METADATA[stage_id]
        gid = f"NISAR_L2_GCOV_{meta['date_str'].replace('-', '')}_BARROW_STRAIT"
        
        manifest[gid] = {
            "granule_id": gid,
            "cog_filepath": cog_path,
            "hazard_filepath": hazard_path,
            "processed_timestamp": "2026-11-14T17:00:00Z",
            "acquisition_date": meta["date_str"],
            "stage_label": meta["name"],
            "metadata": {
                "platform": "NISAR",
                "frequency": "L-band (1.25 GHz / 24 cm)",
                "polarization": "Dual-Pol (HHHH, HVHV)",
                "processing_level": "L2 GCOV",
                "spatial_coverage": "Barrow Strait (Cornwallis to Somerset Island)",
                "phase": meta["phase"],
                "summary": meta["summary"]
            }
        }

    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=4)

    return len(manifest)


def clear_manifest_for_fallback_testing():
    """Removes manifest.json to test fallback behavior."""
    if os.path.exists(MANIFEST_PATH):
        os.remove(MANIFEST_PATH)
