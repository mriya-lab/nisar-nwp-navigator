"""
app/components/architecture_tab.py
Renders Tab 4 ("System Architecture & Data Pipeline"):
1. End-to-End System Architecture & Data Flow Diagram (Custom Inline SVG, 230px)
2. Data Sources & Sensor Specifications Table + Pipeline Telemetry KPIs
3. Step-by-Step Signal Processing & Classification Pipeline Breakdown (Horizontal SVG Flowchart + Cards)
"""

import base64
import streamlit as st


def _svg_to_img_html(svg_markup: str, height_px: int, alt_text: str) -> str:
    b64 = base64.b64encode(svg_markup.strip().encode("utf-8")).decode("ascii")
    return (
        f'<div style="margin: 6px 0 12px 0;">'
        f'<img src="data:image/svg+xml;base64,{b64}" '
        f'alt="{alt_text}" '
        f'style="width: 100%; height: {height_px}px; display: block; border-radius: 8px;" />'
        f"</div>"
    )


def render_architecture_overview_svg() -> None:
    """
    Renders the 4-stage End-to-End System Architecture & Data Flow SVG diagram
    (width: 100%, height: 230px, #0f172a slate background with #38bdf8, #fbbf24, #f43f5e accents).
    """
    svg = """
    <svg viewBox="0 0 1120 230" style="width: 100%; height: 230px; display: block; border-radius: 8px;" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <marker id="arrow-cyan" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="#38bdf8"/>
        </marker>
        <marker id="arrow-amber" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="#fbbf24"/>
        </marker>
        <marker id="arrow-crimson" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="#f43f5e"/>
        </marker>
      </defs>

      <!-- Outer dark-slate background -->
      <rect width="1120" height="230" rx="10" fill="#0f172a" stroke="#1e293b" stroke-width="2"/>

      <!-- Top Banner Header -->
      <text x="20" y="24" fill="#38bdf8" font-family="monospace" font-size="11.5" font-weight="bold">
        END-TO-END SYSTEM ARCHITECTURE &amp; DATA FLOW — NISAR NWP TACTICAL NAVIGATOR
      </text>
      <text x="1100" y="24" text-anchor="end" fill="#94a3b8" font-family="monospace" font-size="10">
        RINGFENCED PIPELINE: 17 GB RAW HDF5 → &lt;10 MB CLOUD-OPTIMIZED GEOTIFFS
      </text>
      <line x1="16" y1="32" x2="1104" y2="32" stroke="#1e293b" stroke-width="1.5"/>

      <!-- ==================== STAGE 1: INGESTION ==================== -->
      <rect x="16" y="44" width="245" height="170" rx="8" fill="#111c33" stroke="#38bdf8" stroke-width="1.8"/>
      <rect x="16" y="44" width="245" height="28" rx="8" fill="#0284c7" opacity="0.28"/>
      <text x="28" y="62" fill="#38bdf8" font-family="monospace" font-size="11" font-weight="bold">STAGE 1 · INGESTION</text>
      <text x="28" y="84" fill="#e2e8f0" font-family="monospace" font-size="10" font-weight="bold">pipeline/load_real_scenes.py</text>
      <text x="28" y="103" fill="#cbd5e1" font-family="sans-serif" font-size="10">• NASA ASF Vertex API (asf_search)</text>
      <text x="28" y="120" fill="#cbd5e1" font-family="sans-serif" font-size="10">• 2026 NISAR L2 GCOV Granules</text>
      <text x="28" y="137" fill="#38bdf8" font-family="monospace" font-size="9.5">  - DHDH Dual-Pol (HHHH + HVHV)</text>
      <text x="28" y="153" fill="#fbbf24" font-family="monospace" font-size="9.5">  - NASV Single-Pol (VVVV 80m)</text>
      <text x="28" y="172" fill="#94a3b8" font-family="sans-serif" font-size="9.5">• AOIs: Barrow, M'Clure &amp; Victoria</text>
      <rect x="28" y="184" width="221" height="20" rx="4" fill="#0f172a" stroke="#334155" stroke-width="1"/>
      <text x="138" y="198" text-anchor="middle" fill="#94a3b8" font-family="monospace" font-size="9">data/raw/*.h5 (Git-Ignored)</text>

      <!-- Connector 1 -> 2 -->
      <line x1="261" y1="128" x2="289" y2="128" stroke="#38bdf8" stroke-width="2.5" marker-end="url(#arrow-cyan)"/>
      <text x="275" y="118" text-anchor="middle" fill="#38bdf8" font-family="monospace" font-size="8.5">.h5</text>

      <!-- ==================== STAGE 2: RADIOMETRIC & GEOMETRIC PROCESSING ==================== -->
      <rect x="293" y="44" width="272" height="170" rx="8" fill="#111c33" stroke="#fbbf24" stroke-width="1.8"/>
      <rect x="293" y="44" width="272" height="28" rx="8" fill="#f59e0b" opacity="0.22"/>
      <text x="305" y="62" fill="#fbbf24" font-family="monospace" font-size="11" font-weight="bold">STAGE 2 · SAR PROCESSING</text>
      <text x="305" y="84" fill="#e2e8f0" font-family="monospace" font-size="10" font-weight="bold">pipeline/fetch_and_process.py</text>
      <text x="305" y="103" fill="#cbd5e1" font-family="sans-serif" font-size="10">• Extract /science/LSAR/GCOV/grids</text>
      <text x="305" y="120" fill="#cbd5e1" font-family="sans-serif" font-size="10">• Power → dB: 10·log10(γ⁰) (STEP=6)</text>
      <text x="305" y="137" fill="#cbd5e1" font-family="sans-serif" font-size="10">• Land Masking (Arctic Island Zeroing)</text>
      <text x="305" y="154" fill="#cbd5e1" font-family="sans-serif" font-size="10">• Reproject EPSG:3413/UTM → EPSG:4326</text>
      <text x="305" y="171" fill="#fbbf24" font-family="monospace" font-size="9.5">• 3-Tier Hazard + rasterio.merge</text>
      <rect x="305" y="184" width="248" height="20" rx="4" fill="#0f172a" stroke="#334155" stroke-width="1"/>
      <text x="429" y="198" text-anchor="middle" fill="#fbbf24" font-family="monospace" font-size="9">Regional Chokepoint Composites</text>

      <!-- Connector 2 -> 3 -->
      <line x1="565" y1="128" x2="593" y2="128" stroke="#fbbf24" stroke-width="2.5" marker-end="url(#arrow-amber)"/>
      <text x="579" y="118" text-anchor="middle" fill="#fbbf24" font-family="monospace" font-size="8.5">COG</text>

      <!-- ==================== STAGE 3: LIGHTWEIGHT ARTIFACT STORE ==================== -->
      <rect x="597" y="44" width="235" height="170" rx="8" fill="#111c33" stroke="#38bdf8" stroke-width="1.8"/>
      <rect x="597" y="44" width="235" height="28" rx="8" fill="#0284c7" opacity="0.28"/>
      <text x="609" y="62" fill="#38bdf8" font-family="monospace" font-size="11" font-weight="bold">STAGE 3 · ARTIFACT STORE</text>
      <text x="609" y="84" fill="#e2e8f0" font-family="monospace" font-size="10" font-weight="bold">data/processed/ &amp; data/gis/</text>
      <text x="609" y="103" fill="#cbd5e1" font-family="sans-serif" font-size="10">• *_rgb.tif (3-Band Dual-Pol RGB)</text>
      <text x="609" y="120" fill="#cbd5e1" font-family="sans-serif" font-size="10">• *_hazard.tif (1-Band Tier 1/2/3)</text>
      <text x="609" y="137" fill="#38bdf8" font-family="monospace" font-size="9.5">• manifest.json State Registry</text>
      <text x="609" y="154" fill="#cbd5e1" font-family="sans-serif" font-size="10">• nordreg_barrow_strait.geojson</text>
      <text x="609" y="171" fill="#94a3b8" font-family="sans-serif" font-size="9.5">• Deflate COG (&lt;1.5 MB per scene)</text>
      <rect x="609" y="184" width="211" height="20" rx="4" fill="#0f172a" stroke="#334155" stroke-width="1"/>
      <text x="714" y="198" text-anchor="middle" fill="#38bdf8" font-family="monospace" font-size="9">Instant Cloud / Docker Ready</text>

      <!-- Connector 3 -> 4 -->
      <line x1="832" y1="128" x2="860" y2="128" stroke="#f43f5e" stroke-width="2.5" marker-end="url(#arrow-crimson)"/>
      <text x="846" y="118" text-anchor="middle" fill="#f43f5e" font-family="monospace" font-size="8.5">I/O</text>

      <!-- ==================== STAGE 4: TACTICAL DECISION ENGINE ==================== -->
      <rect x="864" y="44" width="240" height="170" rx="8" fill="#111c33" stroke="#f43f5e" stroke-width="1.8"/>
      <rect x="864" y="44" width="240" height="28" rx="8" fill="#f43f5e" opacity="0.22"/>
      <text x="876" y="62" fill="#f43f5e" font-family="monospace" font-size="11" font-weight="bold">STAGE 4 · DECISION ENGINE</text>
      <text x="876" y="84" fill="#e2e8f0" font-family="monospace" font-size="10" font-weight="bold">app/data_manager.py &amp; routing.py</text>
      <text x="876" y="103" fill="#cbd5e1" font-family="sans-serif" font-size="10">• 350-Point Geodesic Route Sampler</text>
      <text x="876" y="120" fill="#cbd5e1" font-family="sans-serif" font-size="10">• IMO Polar Code Risk &amp; Fuel Engine</text>
      <text x="876" y="137" fill="#cbd5e1" font-family="sans-serif" font-size="10">• Tactical Folium Map &amp; Swipe UI</text>
      <text x="876" y="154" fill="#cbd5e1" font-family="sans-serif" font-size="10">• Live dB Histograms &amp; Rerouting</text>
      <text x="876" y="171" fill="#fbbf24" font-family="monospace" font-size="9.5">• Synthetic Fallback Resilience</text>
      <rect x="876" y="184" width="216" height="20" rx="4" fill="#0f172a" stroke="#f43f5e" stroke-width="1"/>
      <text x="984" y="198" text-anchor="middle" fill="#fda4af" font-family="monospace" font-size="9">NAVIGABLE / CAUTION / BLOCKED</text>
    </svg>
    """
    st.markdown(
        _svg_to_img_html(
            svg,
            230,
            "Four-stage end-to-end architecture diagram of NISAR NWP Navigator from ASF ingestion to tactical routing",
        ),
        unsafe_allow_html=True,
    )


def render_signal_processing_flowchart_svg() -> None:
    """
    Renders the secondary horizontal SVG flowchart illustrating the 4 mathematical and
    spatial signal-processing steps inside pipeline/fetch_and_process.py and pipeline/load_real_scenes.py.
    """
    svg = """
    <svg viewBox="0 0 1120 175" style="width: 100%; height: 175px; display: block; border-radius: 8px;" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <marker id="flow-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="#38bdf8"/>
        </marker>
      </defs>

      <rect width="1120" height="175" rx="10" fill="#0f172a" stroke="#1e293b" stroke-width="2"/>
      <text x="20" y="23" fill="#fbbf24" font-family="monospace" font-size="11" font-weight="bold">
        SIGNAL PROCESSING, POLARIMETRIC CLASSIFICATION &amp; WAYPOINT ROUTING PIPELINE
      </text>
      <line x1="16" y1="31" x2="1104" y2="31" stroke="#1e293b" stroke-width="1.2"/>

      <!-- Step 1: Radiometric Calibration -->
      <rect x="16" y="42" width="248" height="118" rx="7" fill="#132038" stroke="#38bdf8" stroke-width="1.5"/>
      <text x="28" y="61" fill="#38bdf8" font-family="monospace" font-size="10.5" font-weight="bold">1. RADIOMETRIC CALIBRATION</text>
      <text x="28" y="81" fill="#f8fafc" font-family="monospace" font-size="10">γ⁰_dB = 10 · log10(max(γ⁰, 1e-6))</text>
      <text x="28" y="100" fill="#cbd5e1" font-family="sans-serif" font-size="9.5">• Extract HHHH/HVHV or VVVV grids</text>
      <text x="28" y="116" fill="#cbd5e1" font-family="sans-serif" font-size="9.5">• Adaptive STEP=6 spatial decimation</text>
      <text x="28" y="132" fill="#94a3b8" font-family="monospace" font-size="9">• Summer VVVV Bragg offset (-4.5 dB)</text>
      <text x="28" y="148" fill="#38bdf8" font-family="monospace" font-size="9">Output: Calibrated Float32 dB Arrays</text>

      <line x1="264" y1="101" x2="292" y2="101" stroke="#38bdf8" stroke-width="2.2" marker-end="url(#flow-arrow)"/>

      <!-- Step 2: Land Masking & Reprojection -->
      <rect x="296" y="42" width="252" height="118" rx="7" fill="#132038" stroke="#38bdf8" stroke-width="1.5"/>
      <text x="308" y="61" fill="#38bdf8" font-family="monospace" font-size="10.5" font-weight="bold">2. LAND MASK &amp; REPROJECTION</text>
      <text x="308" y="81" fill="#f8fafc" font-family="monospace" font-size="10">EPSG:3413 / UTM → EPSG:4326</text>
      <text x="308" y="100" fill="#cbd5e1" font-family="sans-serif" font-size="9.5">• Zero out Arctic island bedrock (0)</text>
      <text x="308" y="116" fill="#cbd5e1" font-family="sans-serif" font-size="9.5">• Preserve Russell Is. deep channel</text>
      <text x="308" y="132" fill="#94a3b8" font-family="monospace" font-size="9">• calculate_default_transform + warp</text>
      <text x="308" y="148" fill="#38bdf8" font-family="monospace" font-size="9">Output: Ocean-Only WGS84 Rasters</text>

      <line x1="548" y1="101" x2="576" y2="101" stroke="#38bdf8" stroke-width="2.2" marker-end="url(#flow-arrow)"/>

      <!-- Step 3: 3-Tier Polarimetric Classification -->
      <rect x="580" y="42" width="256" height="118" rx="7" fill="#132038" stroke="#fbbf24" stroke-width="1.5"/>
      <text x="592" y="61" fill="#fbbf24" font-family="monospace" font-size="10.5" font-weight="bold">3. 3-TIER HAZARD &amp; RGB</text>
      <text x="592" y="81" fill="#38bdf8" font-family="monospace" font-size="9.5">• Tier 1 Water: HH&lt;-15.5 | HV&lt;-25 dB</text>
      <text x="592" y="98" fill="#fbbf24" font-family="monospace" font-size="9.5">• Tier 2 FYI:   -25 ≤ HV ≤ -18.5 dB</text>
      <text x="592" y="115" fill="#f43f5e" font-family="monospace" font-size="9.5">• Tier 3 MYI:   HV&gt;-18.5 | HH&gt;-9.5 dB</text>
      <text x="592" y="132" fill="#cbd5e1" font-family="sans-serif" font-size="9.5">• False-Color RGB: [HH, HV, HH-HV]</text>
      <text x="592" y="148" fill="#fbbf24" font-family="monospace" font-size="9">Output: *_hazard.tif &amp; *_rgb.tif</text>

      <line x1="836" y1="101" x2="864" y2="101" stroke="#38bdf8" stroke-width="2.2" marker-end="url(#flow-arrow)"/>

      <!-- Step 4: Mosaicking & Waypoint Routing -->
      <rect x="868" y="42" width="236" height="118" rx="7" fill="#132038" stroke="#f43f5e" stroke-width="1.5"/>
      <text x="880" y="61" fill="#f43f5e" font-family="monospace" font-size="10.5" font-weight="bold">4. MOSAIC &amp; ROUTE ENGINE</text>
      <text x="880" y="81" fill="#f8fafc" font-family="monospace" font-size="9.5">rasterio.merge + 350 Waypoints</text>
      <text x="880" y="100" fill="#cbd5e1" font-family="sans-serif" font-size="9.5">• Max-hazard swath stitching</text>
      <text x="880" y="116" fill="#cbd5e1" font-family="sans-serif" font-size="9.5">• 5×5 neighborhood corridor window</text>
      <text x="880" y="132" fill="#94a3b8" font-family="monospace" font-size="9">• IMO Polar Code speed &amp; fuel burn</text>
      <text x="880" y="148" fill="#fda4af" font-family="monospace" font-size="9">Output: Tactical Telemetry &amp; Map</text>
    </svg>
    """
    st.markdown(
        _svg_to_img_html(
            svg,
            175,
            "Four-step signal processing flowchart showing radiometric calibration, land masking, polarimetric classification, and corridor routing",
        ),
        unsafe_allow_html=True,
    )


def render_system_architecture_tab(manifest_status: dict) -> None:
    """Renders the complete Tab 4 ('System Architecture & Data Pipeline') content."""
    st.subheader("🏗️ System Architecture & End-to-End SAR Data Pipeline")
    st.caption(
        "Technical overview of how NISAR L2 GCOV HDF5 radar granules are ingested, calibrated, "
        "classified into Cloud-Optimized GeoTIFFs, and evaluated by the deterministic Polar Code routing engine."
    )

    # Top-level Pipeline KPIs
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric(
            "Data Compression Ratio",
            "17 GB → 9.2 MB",
            delta="-99.94% footprint (COG)",
            delta_color="normal",
        )
    with k2:
        scene_cnt = manifest_status.get("scene_count", 21)
        st.metric(
            "Validated Manifest Scenes",
            f"{scene_cnt} COGs",
            delta="4 Regional Mosaics + 17 Swaths",
            delta_color="off",
        )
    with k3:
        st.metric(
            "Corridor Sampling Density",
            "350 Waypoints",
            delta="5×5 pixel local hazard window",
            delta_color="off",
        )
    with k4:
        st.metric(
            "NWP Chokepoints Covered",
            "3 Straits",
            delta="Barrow · M'Clure · Victoria",
            delta_color="off",
        )

    st.markdown("---")

    # 1. End-to-End Architecture Diagram
    st.markdown("### 1. End-to-End System Architecture & Data Flow")
    st.caption(
        "Strict ringfencing separates multi-gigabyte raw NISAR `.h5` granules (`data/raw/`) from lightweight, "
        "cloud-ready GeoTIFF artifacts (`data/processed/`) consumed at runtime by the Streamlit tactical portal."
    )
    render_architecture_overview_svg()

    st.markdown("---")

    # 2. Data Sources & Sensor Specifications Table
    st.markdown("### 2. Primary Data Sources & Sensor Specifications")
    st.caption(
        "Observational radar modes and geospatial vector datasets integrated across the Northwest Passage domain."
    )
    data_sources = [
        {
            "Data Source / Layer": "NASA NISAR L2 GCOV (DHDH Dual-Pol Mode)",
            "Band & Polarization": "L-Band (24 cm / 1.257 GHz) — Dual-Pol (HHHH + HVHV)",
            "Spatial Resolution / Swath": "10–20 m native posting (STEP=6 decimated) · ~240 km swath",
            "Operational Role in Navigator": "Primary cross-pol volume scattering detector for deformed Multi-Year Ice (MYI) ridges in Barrow Strait",
        },
        {
            "Data Source / Layer": "NASA NISAR L2 GCOV (NASV Single-Pol Mode)",
            "Band & Polarization": "L-Band (24 cm / 1.257 GHz) — Single-Pol (VVVV, 5 MHz BW)",
            "Spatial Resolution / Swath": "80 m native posting · Wide-swath Arctic coverage",
            "Operational Role in Navigator": "Wide-area regional gap-filling and late-October freeze-up mosaicking across M'Clure & Victoria Straits",
        },
        {
            "Data Source / Layer": "Canadian Coast Guard NORDREG Corridors",
            "Band & Polarization": "GeoJSON Vector LineStrings (EPSG:4326)",
            "Spatial Resolution / Swath": "~1,450 NM Baffin Bay to Beaufort Sea trans-Arctic tracks",
            "Operational Role in Navigator": "Primary deep-water route, Southern Somerset Island coastal alternate, and M'Clure Strait northern route",
        },
        {
            "Data Source / Layer": "Global Land Mask & Bathymetric Channel Guard",
            "Band & Polarization": "1 km Binary Land/Ocean Grid (global-land-mask) + Polygon Mask",
            "Spatial Resolution / Swath": "1 km grid + Russell Island narrow-channel override (74.11°–74.14°N)",
            "Operational Role in Navigator": "Masks high-backscatter Arctic island bedrock (Devon, Somerset, Cornwallis, Banks, Victoria) to NoData (0)",
        },
    ]
    st.table(
        data_sources,
        alt="Specifications table of NASA NISAR L2 GCOV DHDH dual-pol mode, NASV single-pol mode, NORDREG shipping corridors, and Arctic land masking layers",
    )

    st.markdown("---")

    # 3. Step-by-Step Signal Processing & Classification Pipeline Breakdown
    st.markdown("### 3. Signal Processing, Classification & Routing Pipeline Breakdown")
    st.caption(
        "Mathematical transformations applied from raw HDF5 radar covariance matrices to vessel-specific Polar Code telemetry."
    )
    render_signal_processing_flowchart_svg()

    pcol1, pcol2 = st.columns(2)
    with pcol1:
        with st.container(border=True):
            st.markdown("#### Step 1 · Radiometric Calibration (`pipeline/fetch_and_process.py`)")
            st.markdown(
                """
                * **HDF5 Layer Extraction:** Reads `/science/LSAR/GCOV/grids/frequencyB` (or `frequencyA`) coordinate arrays (`xCoordinates`, `yCoordinates`, `projection`) and backscatter covariance matrices (`HHHH`, `HVHV`, `VVVV`).
                * **Logarithmic dB Conversion:** Converts linear terrain-flattened gamma-nought power ratios to calibrated decibels:
                  $$\\sigma^0_{\\text{dB}} = 10 \\cdot \\log_{10}\\!\\left(\\max(\\gamma^0_{\\text{linear}},\\; 10^{-6})\\right)$$
                * **Single-Pol Summer Bragg Calibration:** Applies a $-4.5\\text{ dB}$ radiometric offset for summer single-pol `VVVV` frames to prevent wind-roughened capillary waves ($\\approx -13\\text{ dB}$) from false-triggering ice hazards.
                """
            )

        with st.container(border=True):
            st.markdown("#### Step 3 · 3-Tier Polarimetric Classification & False-Color RGB")
            st.markdown(
                """
                * **Tier 1 — Open Water (`Class 1`):** $\\text{HHHH} < -15.5\\text{ dB}$ or $\\text{HVHV} < -25.0\\text{ dB}$ (specular mirror reflection or wind-roughened Bragg scatter without volumetric depolarization).
                * **Tier 2 — First-Year Ice (`Class 2`):** $-15.5 \\le \\text{HHHH} \\le -9.5\\text{ dB}$ and $-25.0 \\le \\text{HVHV} \\le -18.5\\text{ dB}$ (saline young ice where brine dielectric loss suppresses internal volume scattering).
                * **Tier 3 — Multi-Year / Ridged Ice (`Class 3`):** $\\text{HVHV} > -18.5\\text{ dB}$ or $\\text{HHHH} > -9.5\\text{ dB}$ (desalinated air-bubble volume scattering and pressure-ridge double-bounce returns).
                * **Dual-Pol False-Color RGB:** Maps `R = HHHH [-24, -6 dB]`, `G = HVHV [-26, -12 dB]`, and `B = (HH - HV) [2, 12 dB]` into 8-bit Deflate-compressed Cloud-Optimized GeoTIFFs.
                """
            )

    with pcol2:
        with st.container(border=True):
            st.markdown("#### Step 2 · Coastline Land Masking & WGS84 Reprojection")
            st.markdown(
                """
                * **Coordinate Transformation:** Native NISAR Arctic granules use Polar Stereographic North (`EPSG:3413`) or local UTM zones. `pyproj.Transformer` maps every decimated pixel $(x, y)$ to $(\\text{lon}, \\text{lat})$.
                * **Bedrock Zeroing (`NoData = 0`):** Rocky Arctic islands produce strong radar backscatter that mimics ridged ice. `globe.is_land(lat, lon)` masks all land pixels to `0` (transparent RGBA), with an explicit bathymetric corridor guard preserving the narrow western Barrow Strait channel off Russell Island.
                * **WGS84 Warping:** `rasterio.warp.calculate_default_transform` and `reproject` warp native grids to `EPSG:4326` for distortion-free Folium overlay rendering.
                """
            )

        with st.container(border=True):
            st.markdown("#### Step 4 · Regional Mosaicking & Deterministic Waypoint Routing")
            st.markdown(
                """
                * **Multi-Swath Stitching (`pipeline/load_real_scenes.py`):** Merges overlapping orbital tracks across Barrow Strait, M'Clure Strait, and Victoria Strait using `rasterio.merge.merge` (`method="max"` for freeze-up hazard preservation) and appends scene metadata to `data/processed/manifest.json`.
                * **Corridor Waypoint Sampling (`app/routing.py`):** Interpolates **350 equidistant waypoints** along each NORDREG GeoJSON LineString and evaluates a $5 \\times 5$ local pixel window around each waypoint.
                * **IMO Polar Code Telemetry:** Computes effective transit speed, ice delay hours, excess fuel burn penalty (tons), and composite risk index ($0\\text{–}100$) for **Standard Cargo**, **Polar Class 6**, and **Heavy Icebreaker** profiles.
                """
            )
