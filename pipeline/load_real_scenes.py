"""
pipeline/load_real_scenes.py
Processes local NISAR L2 GCOV granules in data/raw/ (or downloads from ASF Vertex when
requested) using land-masked, calibrated open-water/FYI/MYI thresholds and updates
data/processed/manifest.json.
"""

import os
import sys

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pipeline.fetch_and_process import (
    RAW_DIR,
    PROCESSED_DIR,
    MANIFEST_PATH,
    hdf5_to_cog,
    append_to_manifest,
)

AOI_WKT = "POLYGON((-98.5 73.8, -91.5 73.8, -91.5 75.3, -98.5 75.3, -98.5 73.8))"


def total_bytes(obj) -> int:
    if isinstance(obj, (int, float)):
        return int(obj)
    if isinstance(obj, dict):
        return sum(total_bytes(v) for v in obj.values())
    return 0


def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    raw_files = sorted(f for f in os.listdir(RAW_DIR) if f.endswith(".h5") or f.endswith(".hdf5"))

    # If local .h5 files exist and no explicit ASF indices were passed, process all local granules
    if raw_files and len(sys.argv) < 2:
        print(f"Found {len(raw_files)} local NISAR HDF5 granule(s) in {RAW_DIR}:")
        for fname in raw_files:
            gid = os.path.splitext(fname)[0]
            h5_path = os.path.join(RAW_DIR, fname)
            rgb_path, hazard_path, meta = hdf5_to_cog(h5_path, gid)
            append_to_manifest(gid, rgb_path, hazard_path, meta)
        print(f"\nDone! Processed {len(raw_files)} local granule(s) into {MANIFEST_PATH}")
        return

    import asf_search as asf

    results = asf.search(
        dataset="NISAR",
        processingLevel="GCOV",
        intersectsWith=AOI_WKT,
        start="2026-06-15T00:00:00Z",
        end="2026-11-15T23:59:59Z",
    )

    indices = [int(i) for i in sys.argv[1:]] if len(sys.argv) >= 2 else [510, 0]
    selected = [results[i] for i in indices if i < len(results)]

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
        rgb_path, hazard_path, meta = hdf5_to_cog(h5_path, gid)
        append_to_manifest(gid, rgb_path, hazard_path, meta)

    print(f"\nDone! Updated {MANIFEST_PATH} with {len(selected)} scene(s).")


if __name__ == "__main__":
    main()
