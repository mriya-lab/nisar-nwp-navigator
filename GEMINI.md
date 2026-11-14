# GEMINI Architectural Rules Matrix: nisar-nwp-navigator

## 1. Directory System Rules
* **Strict Layout Adherence:** Do not alter the directory schema without manual review. 
* **Data Ringfencing:** 
  * `data/raw/` is strictly for raw NISAR HDF5 (`.h5`) L2 GCOV granules. Never track these.
  * `data/processed/` must contain lightweight COGs/GeoTIFFs and a single tracking `manifest.json`.
  * `data/gis/` must handle NORDREG shipping corridors and Canadian Ice Service (CIS) vector overlays.

## 2. Pipeline Integrity (pipeline/fetch_and_process.py)
* **Ingestion:** Must interface with the ASF Vertex API to pull NISAR L2 GCOV imagery over Arctic corridors.
* **Transformation:** Extract HDF5 datasets, convert backscatter to decibels (dB), apply terrain correction coordinates, and export exclusively to Cloud-Optimized GeoTIFF (COG).
* **State Management:** Every generation pass must append metadata records to `data/processed/manifest.json`.

## 3. Application Architecture (app/)
* **main.py:** Streamlit entry point utilizing `leafmap`/`folium` for high-performance map rendering.
* **routing.py:** Deterministic core calculation engine. Evaluates corridor risk based on ice-class limits and computes shipping fuel-penalties.
* **components/:** Keep user-interface primitives modular:
  * Split-screen raster/vector swipe maps.
  * Interactive dB backscatter histograms.
  * Real-time voyage telemetry informational cards.
