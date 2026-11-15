"""
pipeline/load_real_scenes.py
Multi-granule regional mosaicking & single-scene ingestion pipeline for NISAR L2 GCOV data.
Queries ASF Vertex over the three classic Northwest Passage chokepoints:
  1. Barrow Strait (Central Chokepoint — Summer Baseline & Autumn Freeze-Up)
  2. M'Clure Strait (Western Chokepoint — Late-October Freeze-Up)
  3. Victoria Strait (Southern Chokepoint — Late-October Freeze-Up)
Processes each granule with STEP=6 decimation, land masking, and calibrated dB thresholds,
reprojects RGB and Hazard rasters to EPSG:4326, stitches regional composite GeoTIFFs (< 1.5 MB each)
using rasterio.merge.merge, and updates data/processed/manifest.json.
"""

import os
import sys
import json
from typing import List, Dict, Any, Tuple
import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.merge import merge
from rasterio.io import MemoryFile
from global_land_mask import globe

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pipeline.fetch_and_process import (
    RAW_DIR,
    PROCESSED_DIR,
    MANIFEST_PATH,
    hdf5_to_cog,
    append_to_manifest,
)

# Decimation step to guarantee lightweight COGs (< 1.5 MB per GeoTIFF)
STEP = 6

# Default wider Parry Channel / Barrow Strait operational AOI
BARROW_AOI_WKT = "POLYGON((-100.5 73.5, -88.5 73.5, -88.5 75.6, -100.5 75.6, -100.5 73.5))"
MCLURE_AOI_WKT = "POLYGON((-121.5 74.1, -114.5 74.1, -114.5 75.3, -121.5 75.3, -121.5 74.1))"
VICTORIA_AOI_WKT = "POLYGON((-102.5 68.8, -97.5 68.8, -97.5 70.3, -102.5 70.3, -102.5 68.8))"

# Multi-granule regional mosaics across the three Northwest Passage chokepoints
MOSAIC_WINDOWS: List[Dict[str, Any]] = [
    {
        "mosaic_id": "NISAR_L2_GCOV_20260824_BARROW_MOSAIC",
        "stage_label": "2026-08-24 — Barrow Strait Regional Mosaic",
        "timestamp": "2026-08-24T08:45:50Z",
        "polarization": "Multi-Swath Dual/Single-Pol (DHDH + VVVV)",
        "aoi_wkt": BARROW_AOI_WKT,
        "bounds_wgs84": (-100.5, 73.5, -88.5, 75.6),
        "start": "2026-08-10T00:00:00Z",
        "end": "2026-08-28T23:59:59Z",
        "hazard_merge_method": "first",
        "granule_filenames": [
            # East Barrow Strait & Lancaster Sound (Dual-Pol DHDH)
            "NISAR_L2_PR_GCOV_028_158_D_049_4005_DHDH_A_20260824T035109_20260824T035140_P05023_N_F_J_001.h5",
            # Central-West Barrow Strait (Dual-Pol DHDH)
            "NISAR_L2_PR_GCOV_028_043_D_049_4005_DHDH_A_20260816T042432_20260816T042441_P05023_N_P_J_001.h5",
            # Central Barrow Strait (Dual-Pol DHDH)
            "NISAR_L2_PR_GCOV_028_060_A_040_4005_DHDH_A_20260817T083748_20260817T083806_P05023_N_P_J_001.h5",
            # Central-North Overlapping Frame on Track 072 (Single-Pol NASV)
            "NISAR_L2_PR_GCOV_028_072_D_048_0005_NASV_A_20260818T044034_20260818T044107_P05023_N_F_J_001.h5",
            # West Barrow Strait / Viscount Melville Sound (Single-Pol NASV)
            "NISAR_L2_PR_GCOV_028_072_D_049_0005_NASV_A_20260818T044106_20260818T044136_P05023_N_F_J_001.h5",
        ],
    },
    {
        "mosaic_id": "NISAR_L2_GCOV_20261029_BARROW_MOSAIC",
        "stage_label": "2026-10-29 — Barrow Strait Regional Mosaic",
        "timestamp": "2026-10-29T04:41:06Z",
        "polarization": "Multi-Swath Dual/Single-Pol (DHDH + VVVV)",
        "aoi_wkt": BARROW_AOI_WKT,
        "bounds_wgs84": (-100.5, 73.5, -88.5, 75.6),
        "start": "2026-10-19T00:00:00Z",
        "end": "2026-10-30T23:59:59Z",
        "hazard_merge_method": "max",
        "granule_filenames": [
            # West Barrow Strait (Single-Pol NASV)
            "NISAR_L2_PR_GCOV_034_072_D_049_0005_NASV_A_20261029T044106_20261029T044137_P05036_N_F_J_001.h5",
            # Central-North Barrow Strait (Single-Pol NASV)
            "NISAR_L2_PR_GCOV_033_173_D_048_0005_NASV_A_20261024T044854_20261024T044926_P05036_N_F_J_001.h5",
            # East Barrow Strait & Lancaster Sound (Dual-Pol DHDH)
            "NISAR_L2_PR_GCOV_034_002_A_041_4005_DHDH_A_20261024T080448_20261024T080518_P05036_N_F_J_001.h5",
            # Central-West Barrow Strait (Single-Pol NASV)
            "NISAR_L2_PR_GCOV_033_132_A_041_0005_NASV_A_20261021T082946_20261021T083016_P05023_N_F_J_001.h5",
        ],
    },
    {
        "mosaic_id": "NISAR_L2_GCOV_20261029_MCLURE_MOSAIC",
        "stage_label": "2026-10-29 — M'Clure Strait Chokepoint Mosaic",
        "timestamp": "2026-10-29T10:09:39Z",
        "polarization": "Multi-Swath Single-Pol (VVVV)",
        "aoi_wkt": MCLURE_AOI_WKT,
        "bounds_wgs84": (-121.5, 74.1, -114.5, 75.3),
        "start": "2026-10-15T00:00:00Z",
        "end": "2026-11-05T23:59:59Z",
        "hazard_merge_method": "max",
        "granule_filenames": [
            # West & Central M'Clure Strait (Single-Pol NASV)
            "NISAR_L2_PR_GCOV_034_133_A_041_0005_NASV_A_20261102T100939_20261102T101009_P05036_N_F_J_001.h5",
            # East M'Clure Strait (Single-Pol NASV)
            "NISAR_L2_PR_GCOV_034_118_A_042_0005_NASV_A_20261101T091152_20261101T091225_P05036_N_F_J_001.h5",
            # South-East M'Clure Strait / Banks Island Coast (Single-Pol NASV)
            "NISAR_L2_PR_GCOV_034_133_A_040_0005_NASV_A_20261102T100905_20261102T100940_P05036_N_F_J_001.h5",
        ],
    },
    {
        "mosaic_id": "NISAR_L2_GCOV_20261029_VICTORIA_MOSAIC",
        "stage_label": "2026-10-29 — Victoria Strait Chokepoint Mosaic",
        "timestamp": "2026-10-29T09:51:14Z",
        "polarization": "Multi-Swath Single-Pol (VVVV)",
        "aoi_wkt": VICTORIA_AOI_WKT,
        "bounds_wgs84": (-102.5, 68.8, -97.5, 70.3),
        "start": "2026-10-15T00:00:00Z",
        "end": "2026-11-05T23:59:59Z",
        "hazard_merge_method": "max",
        "granule_filenames": [
            # Central & Southern Victoria Strait (Single-Pol NASV)
            "NISAR_L2_PR_GCOV_034_133_A_037_0005_NASV_A_20261102T100718_20261102T100755_P05036_N_F_J_001.h5",
            # Northern Victoria Strait & Larsen Sound Entrance (Single-Pol NASV)
            "NISAR_L2_PR_GCOV_033_104_A_038_0005_NASV_A_20261019T095114_20261019T095151_P05023_N_F_J_001.h5",
            # Eastern Victoria Strait & King William Island Channel (Single-Pol NASV)
            "NISAR_L2_PR_GCOV_033_172_D_053_0005_NASV_A_20261024T031147_20261024T031224_P05036_N_F_J_001.h5",
        ],
    },
]


def total_bytes(obj) -> int:
    if isinstance(obj, (int, float)):
        return int(obj)
    if isinstance(obj, dict):
        return sum(total_bytes(v) for v in obj.values())
    return 0


def ensure_window_granules(window_cfg: Dict[str, Any]) -> List[str]:
    """
    Queries ASF Vertex for the given operational window over window_cfg['aoi_wkt'] if any
    target granule is not yet cached locally in data/raw/.
    """
    os.makedirs(RAW_DIR, exist_ok=True)
    filenames = window_cfg["granule_filenames"]
    aoi_wkt = window_cfg.get("aoi_wkt", BARROW_AOI_WKT)
    missing = [fn for fn in filenames if not os.path.exists(os.path.join(RAW_DIR, fn))]

    if missing:
        import asf_search as asf

        print(
            f"[ASF VERTEX] Querying dataset='NISAR', processingLevel='GCOV' "
            f"for {window_cfg['stage_label']} ({window_cfg['start']} .. {window_cfg['end']})..."
        )
        results = asf.search(
            dataset="NISAR",
            processingLevel="GCOV",
            intersectsWith=aoi_wkt,
            start=window_cfg["start"],
            end=window_cfg["end"],
        )
        by_name = {r.properties["fileName"]: r for r in results}
        for fn in missing:
            if fn in by_name:
                r = by_name[fn]
                sz_gb = total_bytes(r.properties.get("bytes", 0)) / 1e9
                print(f"[DOWNLOAD] Downloading {fn} ({sz_gb:.2f} GB)...")
                r.download(path=RAW_DIR)
            else:
                print(f"[WARN] Granule {fn} not found in ASF query results.")

    return [
        os.path.join(RAW_DIR, fn)
        for fn in filenames
        if os.path.exists(os.path.join(RAW_DIR, fn))
    ]


def _reproject_raster_to_wgs84_mem(
    raster_path: str, resampling: Resampling, nodata: int = 0
) -> Tuple[MemoryFile, rasterio.DatasetReader]:
    """
    Warps a single-band or multi-band GeoTIFF into EPSG:4326 inside an in-memory GeoTIFF
    so rasterio.merge.merge can stitch multiple orbital tracks into a unified mosaic.
    """
    with rasterio.open(raster_path) as src:
        dst_crs = "EPSG:4326"
        dst_transform, dst_w, dst_h = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds
        )
        profile = src.profile.copy()
        profile.update(
            driver="GTiff",
            crs=dst_crs,
            transform=dst_transform,
            width=dst_w,
            height=dst_h,
            nodata=nodata,
        )
        memfile = MemoryFile()
        dst = memfile.open(**profile)
        for band_idx in range(1, src.count + 1):
            reproject(
                source=rasterio.band(src, band_idx),
                destination=rasterio.band(dst, band_idx),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=dst_transform,
                dst_crs=dst_crs,
                resampling=resampling,
                src_nodata=nodata,
                dst_nodata=nodata,
            )
        return memfile, dst


def build_regional_mosaic(
    window_cfg: Dict[str, Any],
    granule_cogs: Dict[str, Tuple[str, str, Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Reprojects each granule's RGB and Hazard COGs to EPSG:4326 and stitches them into
    a single regional composite GeoTIFF covering window_cfg['bounds_wgs84'].
    """
    mosaic_id = window_cfg["mosaic_id"]
    bounds_wgs84 = tuple(window_cfg["bounds_wgs84"])
    out_rgb_path = os.path.join(PROCESSED_DIR, f"{mosaic_id}_rgb.tif")
    out_hazard_path = os.path.join(PROCESSED_DIR, f"{mosaic_id}_hazard.tif")
    hazard_method = window_cfg.get("hazard_merge_method", "first")

    rgb_paths = []
    hazard_paths = []
    print(f"[MOSAIC] Granule breakdown for {mosaic_id}:")
    for fn in window_cfg["granule_filenames"]:
        gid = os.path.splitext(fn)[0]
        if gid in granule_cogs:
            r_path, h_path, meta = granule_cogs[gid]
            rgb_paths.append(r_path)
            hazard_paths.append(h_path)
            with rasterio.open(h_path) as h_src:
                h_arr = h_src.read(1)
                tot = int(np.sum(h_arr > 0))
                p1 = float(np.sum(h_arr == 1) / tot * 100.0) if tot > 0 else 0.0
                p2 = float(np.sum(h_arr == 2) / tot * 100.0) if tot > 0 else 0.0
                bbox_r = [round(float(x), 2) for x in meta.get("bbox_wgs84", [])]
                print(
                    f"  • {gid} | pol={meta.get('polarization')} | bbox={bbox_r} "
                    f"| Tier 1 (Open Water)={p1:.1f}% vs Tier 2 (FYI)={p2:.1f}%"
                )

    print(f"[MOSAIC] Stitching {len(hazard_paths)} passes into {mosaic_id} (method={hazard_method})...")

    # 1. Reproject and merge Hazard rasters (Resampling.nearest)
    h_mems, h_srcs = [], []
    for hp in hazard_paths:
        mf, ds = _reproject_raster_to_wgs84_mem(hp, Resampling.nearest, nodata=0)
        h_mems.append(mf)
        h_srcs.append(ds)

    merged_hazard, hazard_transform = merge(
        h_srcs,
        bounds=bounds_wgs84,
        res=(0.012, 0.005),
        nodata=0,
        method=hazard_method,
    )
    for ds in h_srcs:
        ds.close()
    for mf in h_mems:
        mf.close()

    # 2. Reproject and merge RGB rasters (Resampling.bilinear, masked to valid ocean pixels)
    r_mems, r_srcs = [], []
    for rp in rgb_paths:
        mf, ds = _reproject_raster_to_wgs84_mem(rp, Resampling.bilinear, nodata=0)
        r_mems.append(mf)
        r_srcs.append(ds)

    merged_rgb, rgb_transform = merge(
        r_srcs,
        bounds=bounds_wgs84,
        res=(0.012, 0.005),
        nodata=0,
        method="first",
    )
    for ds in r_srcs:
        ds.close()
    for mf in r_mems:
        mf.close()

    # Fill any narrow inter-swath ocean seams within bounds_wgs84 using iterative neighbor propagation
    # while keeping all land masses strictly masked to 0 (transparent)
    _, h_rows, w_cols = merged_hazard.shape
    cols_idx = np.arange(w_cols)
    rows_idx = np.arange(h_rows)
    lons_1d = hazard_transform.c + (cols_idx + 0.5) * hazard_transform.a
    lats_1d = hazard_transform.f + (rows_idx + 0.5) * hazard_transform.e
    lats_grid, lons_grid = np.meshgrid(lats_1d, lons_1d, indexing="ij")
    land_mask = globe.is_land(lats_grid, lons_grid)
    western_channel = (
        (lats_grid >= 74.11)
        & (lats_grid <= 74.14)
        & (lons_grid >= -97.85)
        & (lons_grid <= -97.65)
    )
    ocean_mask = ~(land_mask & (~western_channel))

    haz_2d = merged_hazard[0]
    for _ in range(40):
        missing_ocean = ocean_mask & (haz_2d == 0)
        if not np.any(missing_ocean):
            break
        for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            shifted_h = np.roll(haz_2d, shift=(dr, dc), axis=(0, 1))
            fill = missing_ocean & (shifted_h > 0)
            if np.any(fill):
                haz_2d[fill] = shifted_h[fill]
                if merged_rgb.shape[1:] == haz_2d.shape:
                    for b in range(merged_rgb.shape[0]):
                        shifted_b = np.roll(merged_rgb[b], shift=(dr, dc), axis=(0, 1))
                        merged_rgb[b][fill] = shifted_b[fill]
                missing_ocean = ocean_mask & (haz_2d == 0)
    haz_2d[~ocean_mask] = 0
    merged_hazard[0] = haz_2d

    # Ensure RGB is strictly 0 wherever merged_hazard == 0 (land / off-swath)
    valid_ocean_2d = merged_hazard[0] > 0
    if merged_rgb.shape[1:] == valid_ocean_2d.shape:
        for b in range(merged_rgb.shape[0]):
            merged_rgb[b][~valid_ocean_2d] = 0
            zero_ocean = valid_ocean_2d & (
                (merged_rgb[0] == 0) & (merged_rgb[1] == 0) & (merged_rgb[2] == 0)
            )
            if np.any(zero_ocean):
                merged_rgb[2][zero_ocean] = 18

    _, h_rows, w_cols = merged_hazard.shape

    # Write stitched RGB COG in EPSG:4326
    with rasterio.open(
        out_rgb_path,
        "w",
        driver="COG",
        height=h_rows,
        width=w_cols,
        count=3,
        dtype=np.uint8,
        crs="EPSG:4326",
        transform=rgb_transform,
        compress="deflate",
    ) as dst:
        dst.write(merged_rgb.astype(np.uint8))
        dst.set_band_description(1, "Red (HH Backscatter)")
        dst.set_band_description(2, "Green (HV Backscatter)")
        dst.set_band_description(3, "Blue (HH/HV Ratio)")

    # Write stitched Hazard COG in EPSG:4326
    with rasterio.open(
        out_hazard_path,
        "w",
        driver="COG",
        height=h_rows,
        width=w_cols,
        count=1,
        dtype=np.uint8,
        crs="EPSG:4326",
        transform=hazard_transform,
        nodata=0,
        compress="deflate",
    ) as dst:
        dst.write(merged_hazard[0].astype(np.uint8), 1)
        dst.set_band_description(1, "Ice Hazard Tier (1: Water, 2: FYI, 3: MYI)")

    rgb_kb = os.path.getsize(out_rgb_path) / 1024.0
    haz_kb = os.path.getsize(out_hazard_path) / 1024.0
    print(
        f"[MOSAIC] Exported composite COGs: {out_rgb_path} ({rgb_kb:.1f} KB) "
        f"and {out_hazard_path} ({haz_kb:.1f} KB)"
    )

    return {
        "granule_id": mosaic_id,
        "timestamp": window_cfg["timestamp"],
        "polarization": window_cfg["polarization"],
        "stage_label": window_cfg["stage_label"],
        "bbox_wgs84": list(bounds_wgs84),
        "rgb_path": out_rgb_path,
        "hazard_path": out_hazard_path,
    }


def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    # 1. Ensure all granules needed for the four regional chokepoint mosaics are present
    for win in MOSAIC_WINDOWS:
        ensure_window_granules(win)

    # 2. Process all local HDF5 granules in data/raw/ to individual calibrated COGs (STEP=6)
    raw_files = sorted(
        f for f in os.listdir(RAW_DIR) if f.endswith(".h5") or f.endswith(".hdf5")
    )
    print(f"Processing {len(raw_files)} local NISAR HDF5 granule(s) in {RAW_DIR} with STEP={STEP}...")

    granule_cogs: Dict[str, Tuple[str, str, Dict[str, Any]]] = {}
    single_records: List[Dict[str, Any]] = []

    for fname in raw_files:
        gid = os.path.splitext(fname)[0]
        h5_path = os.path.join(RAW_DIR, fname)
        rgb_path, hazard_path, meta = hdf5_to_cog(h5_path, gid, step=STEP)
        granule_cogs[gid] = (rgb_path, hazard_path, meta)
        single_records.append(
            {
                "granule_id": gid,
                "timestamp": meta["timestamp"],
                "polarization": meta["polarization"],
                "stage_label": meta["stage_label"],
                "bbox_wgs84": meta["bbox_wgs84"],
                "rgb_path": rgb_path,
                "hazard_path": hazard_path,
            }
        )

    # 3. Build the four stitched EPSG:4326 regional chokepoint mosaics
    mosaic_records: List[Dict[str, Any]] = []
    for win in MOSAIC_WINDOWS:
        mosaic_rec = build_regional_mosaic(win, granule_cogs)
        mosaic_records.append(mosaic_rec)

    # 4. Write manifest.json with the four regional mosaics first followed by single-track scenes
    manifest_records = mosaic_records + single_records
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest_records, f, indent=4)

    print(
        f"\nDone! Wrote {len(mosaic_records)} regional mosaic(s) and "
        f"{len(single_records)} single-track scene(s) to {MANIFEST_PATH}."
    )


if __name__ == "__main__":
    main()
