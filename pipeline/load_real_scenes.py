import json
import os
import sys
import asf_search as asf
import h5py
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform_bounds

AOI_WKT = "POLYGON((-98.5 73.8, -91.5 73.8, -91.5 75.3, -98.5 75.3, -98.5 73.8))"
RAW_DIR = "data/raw"
PROC_DIR = "data/processed"
STEP = 4  # ~4x downsample for crisp, fast web map rendering


def total_bytes(obj) -> int:
    if isinstance(obj, (int, float)):
        return int(obj)
    if isinstance(obj, dict):
        return sum(total_bytes(v) for v in obj.values())
    return 0


def to_db(arr: np.ndarray) -> np.ndarray:
    valid = np.where(arr > 1e-6, arr, np.nan)
    return 10.0 * np.log10(valid)


def scale_u8(arr: np.ndarray, vmin: float, vmax: float) -> np.ndarray:
    norm = np.clip((arr - vmin) / (vmax - vmin), 0.0, 1.0)
    return np.nan_to_num(norm * 255.0, nan=0).astype(np.uint8)


def process_granule(h5_path: str, granule_id: str, timestamp: str) -> dict:
    with h5py.File(h5_path, "r") as f:
        freq_root = f["/science/LSAR/GCOV/grids"]
        freq_key = "frequencyA" if "frequencyA" in freq_root else list(freq_root.keys())[0]
        grid = freq_root[freq_key]
        keys = list(grid.keys())
        print(f"  Datasets in {freq_key}: {keys}")

        # Auto-detect co-pol (HHHH or VVVV) and cross-pol (HVHV or VHVH)
        copol_key = next((k for k in ("HHHH", "VVVV") if k in grid), None)
        if copol_key is None:
            raise KeyError(f"No co-pol backscatter dataset found in {keys}")
        xpol_key = next((k for k in ("HVHV", "VHVH") if k in grid), None)

        x_coords = grid["xCoordinates"][::STEP]
        y_coords = grid["yCoordinates"][::STEP]
        epsg = int(grid["projection"][()])

        copol_lin = grid[copol_key][::STEP, ::STEP].astype(np.float32)
        has_xpol = xpol_key is not None
        xpol_lin = grid[xpol_key][::STEP, ::STEP].astype(np.float32) if has_xpol else copol_lin.copy()
        print(f"  Using Co-Pol={copol_key}, Cross-Pol={xpol_key or 'None (Single-Pol)'}")

    copol_db = to_db(copol_lin)
    xpol_db = to_db(xpol_lin)
    ratio_db = (copol_db - xpol_db) if has_xpol else np.zeros_like(copol_db)

    p_co = np.nanpercentile(copol_db, [5, 25, 50, 75, 95])
    print(f"  {copol_key} dB percentiles (5/25/50/75/95%): {[round(float(x), 1) for x in p_co]}")
    if has_xpol:
        p_xp = np.nanpercentile(xpol_db, [5, 25, 50, 75, 95])
        print(f"  {xpol_key} dB percentiles (5/25/50/75/95%): {[round(float(x), 1) for x in p_xp]}")

    dx = float(x_coords[1] - x_coords[0])
    dy = float(y_coords[1] - y_coords[0])
    transform = from_origin(x_coords[0] - dx / 2.0, y_coords[0] - dy / 2.0, dx, abs(dy))
    crs_str = f"EPSG:{epsg}"

    # False-color RGB (uses clean ice-blue/amber/crimson palette when single-pol)
    if has_xpol:
        rgb = np.stack([
            scale_u8(copol_db, -28.0, -4.0),
            scale_u8(xpol_db, -35.0, -12.0),
            scale_u8(ratio_db, 0.0, 15.0),
        ])
    else:
        rgb = np.stack([
            scale_u8(copol_db, -24.0, -6.0),
            scale_u8(copol_db, -28.0, -10.0),
            scale_u8(-copol_db, 8.0, 26.0),
        ])

    rgb_path = os.path.join(PROC_DIR, f"{granule_id}_rgb.tif")
    with rasterio.open(
        rgb_path, "w", driver="GTiff",
        height=rgb.shape[1], width=rgb.shape[2], count=3,
        dtype=np.uint8, crs=crs_str, transform=transform, compress="deflate"
    ) as dst:
        dst.write(rgb)
        bounds = dst.bounds

    # 3-Tier Sea-Ice Hazard GeoTIFF
    hazard = np.zeros(copol_db.shape, dtype=np.uint8)
    valid_mask = ~np.isnan(copol_db)
    if has_xpol:
        open_water = valid_mask & (copol_db < -22.0) & (xpol_db < -30.0)
        myi_ridge = valid_mask & ((xpol_db > -19.0) | (copol_db > -10.0))
    else:
        open_water = valid_mask & (copol_db < -20.0)
        myi_ridge = valid_mask & (copol_db > -11.0)
    fyi_ice = valid_mask & ~open_water & ~myi_ridge

    hazard[open_water] = 1
    hazard[fyi_ice] = 2
    hazard[myi_ridge] = 3

    haz_path = os.path.join(PROC_DIR, f"{granule_id}_hazard.tif")
    with rasterio.open(
        haz_path, "w", driver="GTiff",
        height=hazard.shape[0], width=hazard.shape[1], count=1,
        dtype=np.uint8, crs=crs_str, transform=transform, nodata=0, compress="deflate"
    ) as dst:
        dst.write(hazard, 1)

    bbox_wgs84 = list(transform_bounds(crs_str, "EPSG:4326", *bounds))
    return {
        "granule_id": granule_id,
        "timestamp": timestamp,
        "polarization": f"{copol_key}+{xpol_key}" if has_xpol else copol_key,
        "bbox_wgs84": bbox_wgs84,
        "rgb_path": rgb_path,
        "hazard_path": haz_path,
    }


def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(PROC_DIR, exist_ok=True)

    results = asf.search(
        dataset="NISAR",
        processingLevel="GCOV",
        intersectsWith=AOI_WKT,
        start="2026-06-15T00:00:00Z",
        end="2026-11-15T23:59:59Z",
    )

    indices = [int(i) for i in sys.argv[1:]] if len(sys.argv) >= 2 else [510, 0]
    selected = [results[i] for i in indices]

    manifest = []
    for r in selected:
        fname = r.properties["fileName"]
        gid = r.properties["fileID"]
        ts = r.properties["startTime"]
        size_gb = total_bytes(r.properties.get("bytes", 0)) / 1e9
        h5_path = os.path.join(RAW_DIR, fname)

        if not os.path.exists(h5_path):
            print(f"Downloading {fname} ({size_gb:.2f} GB)...")
            r.download(path=RAW_DIR)

        print(f"Processing {gid} ({ts})...")
        manifest.append(process_granule(h5_path, gid, ts))

    manifest_path = os.path.join(PROC_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2)
    print(f"\nDone! Wrote {len(manifest)} scene(s) to {manifest_path}")


if __name__ == "__main__":
    main()
