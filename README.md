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

---

## Resources

* **Slides from presentation:**
https://docs.google.com/presentation/d/1fuyA7FH7fCL-wMLWpxS2z7jm6FEtaRgXs_F1a1nQbd0

* **Deployed app available for public use:**
https://nisar-nwp-navigator.streamlit.app

---

## 👥 Team Roles & Responsibilities
* **Data Engineering Lead:** Manages ASF API automation, HDF5 layer flattening, and Cloud-Optimized GeoTIFF formatting within `pipeline/`.
* **Maritime Logistics Analyst:** Maintains `app/routing.py` deterministic fuel burn penalties and ice hazard safety parameters.
* **Frontend GIS Developer:** Drives interactive split-screen layouts, histogram distribution overlays, and telemetry presentation inside `app/main.py`.
