# 🛳️ NISAR NWP Navigator

An advanced maritime tactical routing engine utilizing high-resolution **NISAR L2 GCOV (Ground Covariance)** radar observations to optimize vessel transit corridors through the Canadian Arctic Archipelago and the Northwest Passage (NWP).

---

## 🏗️ Repository Layout
```text
nisar-nwp-navigator/
├── GEMINI.md              # Always-on architectural rules read automatically by Antigravity
├── README.md              # Challenge pitch, setup instructions, and team roles
├── requirements.txt      # Pinned Python dependencies
├── data/
│   ├── raw/               # .gitignored — Raw NISAR_L2_GCOV .h5 granules
│   ├── processed/         # Lightweight COGs/GeoTIFFs + manifest.json state tracker
│   └── gis/               # NORDREG corridor GeoJSON + Canadian Ice Service overlays
├── pipeline/
│   └── fetch_and_process.py  # ASF Vertex search + HDF5 -> COG/JSON translation pipeline
└── app/
    ├── main.py            # Streamlit + Leafmap interactive dashboard
    ├── routing.py         # Vessel ice-class corridor risk & fuel-penalty evaluation engine
    └── components/        # UI primitives (split-screen swipe map, telemetry cards)
```

---

## ⚡ Quick Start

### 1. Environment Configuration
Set up your Python virtual environment and unpack dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Ingest Imagery Data
Query the Alaska Satellite Facility (ASF) API and generate radar backscatter COGs:
```bash
python pipeline/fetch_and_process.py
```

### 3. Launch Dashboard
Spin up the interactive Streamlit tactical mapping portal locally:
```bash
streamlit run app/main.py
```

## Deploy the demo to Streamlit Community Cloud

1. Open [Streamlit Community Cloud](https://share.streamlit.io/) and connect GitHub.
2. Create an app from `mriya-lab/nisar-nwp-navigator` on branch `main`.
3. Set the main file path to `app/main.py` and select Python 3.12.
4. Deploy and open the URL in a signed-out browser. Check that the data monitor
   loads the bundled scenes and that both map views work.

The app uses the historical scenes in the repository. The hosted demo needs
no secrets. Route sample coverage measures how many sample points have an ice
classification in the processed raster. Mosaics can include filled pixels.
The app withholds full-route estimates if any sample point lacks a
classification. For local fallback testing, set `NISAR_ALLOW_DATA_EDITS=1` before
starting Streamlit to show the controls that change the local manifest.

---

## 👥 Team Roles & Responsibilities
* **Data Engineering Lead:** Manages ASF API automation, HDF5 layer flattening, and Cloud-Optimized GeoTIFF formatting within `pipeline/`.
* **Maritime Logistics Analyst:** Maintains `app/routing.py` deterministic fuel burn penalties and ice hazard safety parameters.
* **Frontend GIS Developer:** Drives interactive split-screen layouts, histogram distribution overlays, and telemetry presentation inside `app/main.py`.
