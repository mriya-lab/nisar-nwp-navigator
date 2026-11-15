"""
app/main.py
Interactive Northwest Passage SAR Ice Navigator Web Application
2026 NASA Space Apps Challenge — "Dancing with the SARs"
Antigravity Maritime Tactical Routing & Decision Support Portal
"""

import os
import sys
import json
import streamlit as st

# Ensure root workspace directory is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.data_manager import (
    MANIFEST_PATH,
    inspect_manifest,
    load_scene_dataset,
    seed_demo_manifest_cogs,
    clear_manifest_for_fallback_testing,
    STAGE_METADATA
)
from app.routing import evaluate_corridor, VESSEL_PROFILES
from app.components.telemetry_cards import (
    render_route_status_banner,
    render_kpi_metrics,
    render_ice_breakdown_bars,
    render_corridor_comparison_table
)
from app.components.histograms import (
    render_backscatter_histograms,
    render_ice_donut_chart
)
from app.components.map_view import create_tactical_folium_map
from app.components.swipe_map import (
    create_swipe_comparison_map,
    render_swipe_differential_metrics
)

# Page configuration
st.set_page_config(
    page_title="NISAR NWP Navigator | NASA Space Apps 2026",
    page_icon="🛳️",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_data(max_entries=8, show_spinner=False)
def _load_routes_geojson(path: str, mtime: float) -> dict:
    with open(path, "r") as f:
        return json.load(f)


@st.cache_data(max_entries=16, show_spinner=False)
def _cached_load_scene_dataset(scene_id: str, is_fallback: bool, manifest_mtime: float) -> dict:
    return load_scene_dataset(scene_id, inspect_manifest())


# Load GIS Corridor Routes
ROUTES_GEOJSON_PATH = os.path.join(BASE_DIR, "data/gis/nordreg_barrow_strait.geojson")
if not os.path.exists(ROUTES_GEOJSON_PATH):
    # Fallback to nordreg_corridors.geojson if barrow strait geojson not yet created
    ROUTES_GEOJSON_PATH = os.path.join(BASE_DIR, "data/gis/nordreg_corridors.geojson")

routes_mtime = os.path.getmtime(ROUTES_GEOJSON_PATH) if os.path.exists(ROUTES_GEOJSON_PATH) else 0.0
routes_geojson = _load_routes_geojson(ROUTES_GEOJSON_PATH, routes_mtime)

# Inspect manifest and determine fallback status
manifest_status = inspect_manifest()
manifest_mtime = os.path.getmtime(MANIFEST_PATH) if os.path.exists(MANIFEST_PATH) else 0.0


# ==========================================
# SIDEBAR CONTROL PANEL
# ==========================================
st.sidebar.title("🛳️ Tactical Controls")
st.sidebar.caption("NISAR Northwest Passage SAR Ice Navigator")

# System State Monitor
with st.sidebar.expander("📡 Data Source & Manifest Monitor", expanded=True):
    if manifest_status["is_fallback"]:
        st.info(
            "*manifest.json has < 2 scenes; operating on calibrated Barrow Strait L-band stages.*",
            title="🟡 Engine Mode: Calibrated Synthetic Fallback",
        )
    else:
        st.success(
            f"*Loaded {manifest_status['scene_count']} validated scenes from manifest.json.*",
            title="🟢 Engine Mode: Real NISAR GeoTIFFs",
        )

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🌱 Seed COGs", help="Generates calibrated GeoTIFFs and populates manifest.json", width="stretch"):
            seed_demo_manifest_cogs()
            st.cache_data.clear()
            st.rerun()
    with col_btn2:
        if st.button("🧹 Clear Manifest", help="Removes manifest.json to test automatic fallback mode", width="stretch"):
            clear_manifest_for_fallback_testing()
            st.cache_data.clear()
            st.rerun()

st.sidebar.divider()

# Corridor Selection
route_options = {
    f["properties"]["name"]: f["properties"].get("route_id", f["properties"]["name"])
    for f in routes_geojson.get("features", [])
}
selected_route_name = st.sidebar.selectbox(
    "Active Shipping Corridor",
    list(route_options.keys()),
    index=0
)
active_route_id = route_options[selected_route_name]
active_feature = next(
    f for f in routes_geojson["features"]
    if f["properties"].get("route_id", f["properties"]["name"]) == active_route_id
)

# Vessel Profile Selection
vessel_options = list(VESSEL_PROFILES.keys())
selected_vessel = st.sidebar.selectbox(
    "Vessel Ice-Class Certification",
    vessel_options,
    index=1  # Default to Polar Class 6
)

# Observation Stage / Scene Selection
scene_choices = {}
if manifest_status["is_fallback"]:
    for sid, meta in STAGE_METADATA.items():
        scene_choices[meta["name"]] = sid
else:
    for gid, rec in manifest_status["scenes"].items():
        label = rec.get("stage_label", gid)
        scene_choices[label] = gid

selected_scene_label = st.sidebar.selectbox(
    "Radar Acquisition Stage",
    list(scene_choices.keys()),
    index=1 if len(scene_choices) > 1 else 0  # Default to September Intrusion
)
active_scene_id = scene_choices[selected_scene_label]

# Display Layer Options
st.sidebar.divider()
st.sidebar.subheader("Layer Presentation")
radar_display_mode = st.sidebar.radio(
    "Radar Overlay Mode",
    [
        "3-Tier Hazard Classification",
        "Dual-Pol False-Color RGB (HH/HV)",
        "Basemap Satellite Only"
    ],
    index=0
)
radar_opacity = st.sidebar.slider("Radar Layer Opacity", min_value=0.2, max_value=1.0, value=0.80, step=0.05)


# ==========================================
# LOAD ACTIVE DATA & RUN ROUTING EVALUATIONS
# ==========================================
active_scene = _cached_load_scene_dataset(
    active_scene_id,
    manifest_status["is_fallback"],
    manifest_mtime,
)

# Evaluate all corridors for comparison table and active route
all_corridor_evaluations = []
evaluations_dict = {}

for feat in routes_geojson.get("features", []):
    rid = feat["properties"].get("route_id", feat["properties"]["name"])
    nominal_dist = feat["properties"].get("nominal_length_nm")
    eval_res = evaluate_corridor(
        route_geom=feat["geometry"],
        hazard_source=active_scene.get("hazard_source", active_scene["hazard"]),
        transform=active_scene["transform"],
        crs=active_scene.get("crs"),
        vessel_class=selected_vessel,
        nominal_length_nm=nominal_dist
    )
    eval_res["route_info"] = feat["properties"]
    all_corridor_evaluations.append(eval_res)
    evaluations_dict[rid] = eval_res

active_eval = evaluations_dict[active_route_id]
active_telemetry = active_eval["telemetry"]
active_breakdown = active_eval["breakdown"]


# ==========================================
# MAIN APPLICATION INTERFACE
# ==========================================
st.title("🛳️ Northwest Passage SAR Ice Navigator")
st.caption("2026 NASA Space Apps Challenge ('Dancing with the SARs') — Real-time L-Band Radar Tactical Maritime Decision Support")

# Top Level Status Alert
render_route_status_banner(active_telemetry, selected_route_name)

# Three Primary Tabs (state-tracked so inactive tabs skip heavy map rendering)
tab_tactical, tab_swipe, tab_physics = st.tabs(
    [
        "📍 Tactical Route Map",
        "🔄 Before / After Swipe Comparison",
        "🛰️ SAR Physics & Briefing",
    ],
    on_change="rerun",
    key="main_navigation_tabs",
)


# ==========================================
# TAB 1: TACTICAL ROUTE MAP
# ==========================================
if tab_tactical.open:
    with tab_tactical:
        # 1. Top KPI Metric Cards
        render_kpi_metrics(active_telemetry)

        st.markdown("---")

        # 2. Main Map & Diagnostics Split
        col_map, col_diag = st.columns([2.5, 1.0])

        with col_map:
            st.subheader("Tactical Radar Overlay & Route Vectors")
            st.caption(f"Displaying **{selected_scene_label}** with active **{selected_vessel}** corridor risk.")

            tactical_map = create_tactical_folium_map(
                scene_dataset=active_scene,
                routes_geojson=routes_geojson,
                active_route_id=active_route_id,
                evaluations=evaluations_dict,
                radar_mode=radar_display_mode,
                radar_opacity=radar_opacity
            )

            map_html = tactical_map.get_root().render()
            st.iframe(
                map_html,
                height=580,
                alt=f"Interactive tactical route map showing {selected_scene_label} radar overlay and {selected_route_name}",
            )

        with col_diag:
            st.subheader("Diagnostics & Telemetry")

            # Ice Concentration Breakdown Progress Bars
            render_ice_breakdown_bars(active_breakdown)

            # Ice Class Proportion Donut Chart
            render_ice_donut_chart(
                active_breakdown["open_water_pct"],
                active_breakdown["fyi_pct"],
                active_breakdown["myi_pct"]
            )

            with st.container(border=True):
                st.markdown("**Vessel Capability Specifications**")
                st.markdown(f"**Selected:** `{active_telemetry['vessel_class']}`")
                st.caption(active_telemetry["designation"])
                st.markdown(f"• **Baseline Speed:** `{active_telemetry['nominal_speed_knots']} knots`")
                st.markdown(f"• **Effective Speed:** `{active_telemetry['effective_speed_knots']} knots`")
                st.markdown(f"• **Excess Fuel Penalty:** `+{active_telemetry['excess_fuel_penalty_tons']} Tons`")

        # 3. Decision Matrix & Histograms
        st.markdown("---")
        render_corridor_comparison_table(all_corridor_evaluations, active_route_id)

        st.markdown("---")
        st.subheader("Radar Backscatter Distribution along Corridor")
        render_backscatter_histograms(
            hh_db=active_scene["hh_db"],
            hv_db=active_scene["hv_db"],
            hazard=active_scene["hazard"],
            stage_name=active_scene["name"]
        )


# ==========================================
# TAB 2: BEFORE / AFTER SWIPE COMPARISON
# ==========================================
if tab_swipe.open:
    with tab_swipe:
        st.subheader("Tactical Split-Screen Stage Comparison")
        st.caption("Draggable interactive split slider comparing polar sea ice conditions across key seasonal transit epochs.")

        col_s1, col_s2, col_s3 = st.columns([1.5, 1.5, 1.0])

        # Available stages
        if manifest_status["is_fallback"]:
            stage_keys = list(STAGE_METADATA.keys())
            stage_format = lambda k: STAGE_METADATA[k]["name"]
        else:
            stage_keys = list(manifest_status["scenes"].keys())
            stage_format = lambda k: manifest_status["scenes"][k].get("stage_label", k)

        with col_s1:
            left_stage_id = st.selectbox(
                "Left Panel (Reference Baseline)",
                stage_keys,
                index=0,
                format_func=stage_format
            )
        with col_s2:
            right_stage_id = st.selectbox(
                "Right Panel (Target Evaluation)",
                stage_keys,
                index=1 if len(stage_keys) > 1 else 0,
                format_func=stage_format
            )
        with col_s3:
            swipe_mode = st.selectbox(
                "Swipe Visualization Mode",
                ["3-Tier Ice Hazard Classification", "Dual-Pol False-Color RGB (HH/HV)"]
            )

        # Load both datasets (cached)
        left_ds = _cached_load_scene_dataset(
            left_stage_id,
            manifest_status["is_fallback"],
            manifest_mtime,
        )
        right_ds = _cached_load_scene_dataset(
            right_stage_id,
            manifest_status["is_fallback"],
            manifest_mtime,
        )

        # Evaluate along active route
        left_eval = evaluate_corridor(
            active_feature["geometry"],
            left_ds.get("hazard_source", left_ds["hazard"]),
            transform=left_ds["transform"],
            crs=left_ds.get("crs"),
            vessel_class=selected_vessel,
            nominal_length_nm=active_feature["properties"].get("nominal_length_nm")
        )
        right_eval = evaluate_corridor(
            active_feature["geometry"],
            right_ds.get("hazard_source", right_ds["hazard"]),
            transform=right_ds["transform"],
            crs=right_ds.get("crs"),
            vessel_class=selected_vessel,
            nominal_length_nm=active_feature["properties"].get("nominal_length_nm")
        )

        # Render Differential KPI metrics
        render_swipe_differential_metrics(
            left_dataset=left_ds,
            right_dataset=right_ds,
            left_eval=left_eval,
            right_eval=right_eval,
            route_name=selected_route_name
        )

        st.markdown("---")

        # Interactive Swipe Map
        swipe_map = create_swipe_comparison_map(
            left_dataset=left_ds,
            right_dataset=right_ds,
            layer_mode=swipe_mode,
            opacity=0.88,
            active_feature=active_feature,
        )
        swipe_html = swipe_map.get_root().render()
        st.iframe(
            swipe_html,
            height=620,
            alt=f"Split-screen comparison map between {left_ds['name']} and {right_ds['name']}",
        )

        with st.container(border=True):
            st.markdown("### 🔍 The Barrow Strait Choke Phenomenon Explained")
            st.markdown("""
            In late summer, polar pack ice from the Queen Elizabeth Islands drifts southward through **McDougall Sound** and **Wellington Channel**, funneled directly across the northern deep-water route past Resolute Bay. 
            
            * **August:** Wide-open water window allows unreinforced vessels to navigate at full cruising speed (14 kn) with negligible fuel penalties.
            * **September Intrusion:** Severe influx of thick, desalinated multi-year ice floes (3–4 meters thick with intense pressure ridges) creates an impassable barrier for Standard Cargo and unescorted Polar Class 6 ships.
            * **Tactical Mitigation:** SAR tactical routing enables navigators to divert south along Somerset Island's northern coastline, circumventing the choke point entirely and eliminating over 50 hours of ice delay.
            """)


# ==========================================
# TAB 3: SAR PHYSICS & BRIEFING
# ==========================================
@st.fragment
def _render_polarimetric_simulator():
    st.markdown("### 🔬 Interactive Polarimetric Signature Simulator")
    st.caption("Select an Arctic sea surface regime to inspect its physical radar backscatter response and tactical navigation implications.")

    sig_col1, sig_col2 = st.columns([1, 2])

    regimes = {
        "Calm Open Water": {
            "hh_range": "-26.0 to -22.0 dB",
            "hv_range": "-35.0 to -30.0 dB",
            "ratio": "10 to 14 dB",
            "mechanism": "Specular reflection directs transmitted energy away from the antenna. Extremely low cross-pol return near sensor noise floor (NESZ).",
            "hazard_tier": "Tier 1: Open Water",
            "status": "NAVIGABLE for all vessels",
            "color": "#1565C0"
        },
        "Wind-Roughened Open Sea": {
            "hh_range": "-19.0 to -16.0 dB",
            "hv_range": "-32.0 to -28.0 dB",
            "ratio": "12 to 15 dB",
            "mechanism": "Bragg resonant scattering from surface capillary waves elevates co-pol HHHH, but cross-pol HVHV remains suppressed due to lack of volume depolarization.",
            "hazard_tier": "Tier 1: Open Water",
            "status": "NAVIGABLE for all vessels",
            "color": "#1976D2"
        },
        "Smooth First-Year Ice (FYI)": {
            "hh_range": "-19.0 to -16.0 dB",
            "hv_range": "-27.0 to -23.0 dB",
            "ratio": "7 to 10 dB",
            "mechanism": "High salinity (4-10 ppt) in young ice creates high dielectric loss, absorbing microwave energy and limiting penetration depth to a few centimeters.",
            "hazard_tier": "Tier 2: First-Year Ice",
            "status": "CAUTION for Standard Cargo, NAVIGABLE for PC6+",
            "color": "#00BCD4"
        },
        "Deformed / Ridged Multi-Year Ice (MYI)": {
            "hh_range": "-12.0 to -8.0 dB",
            "hv_range": "-17.5 to -13.5 dB",
            "ratio": "4 to 7 dB",
            "mechanism": "Multi-year desalination leaves porous, bubble-filled low-loss ice matrix. L-band microwaves penetrate deep (1-2 m), undergoing severe volume depolarization. Pressure ridges cause massive double-bounce returns.",
            "hazard_tier": "Tier 3: Multi-Year / Ridged Ice",
            "status": "BLOCKED for Standard Cargo & unescorted PC6. Extreme hull breach hazard.",
            "color": "#D50000"
        }
    }

    with sig_col1:
        selected_regime = st.radio(
            "Select Surface Regime:",
            list(regimes.keys()),
            index=3
        )

    r_info = regimes[selected_regime]
    with sig_col2:
        with st.container(border=True):
            st.markdown(f"#### Regime: `{selected_regime}`")

            subcol1, subcol2, subcol3 = st.columns(3)
            with subcol1:
                st.metric("Expected HHHH (Co-Pol)", r_info["hh_range"])
            with subcol2:
                st.metric("Expected HVHV (Cross-Pol)", r_info["hv_range"])
            with subcol3:
                st.metric("HH / HV Difference", r_info["ratio"])

            st.markdown(f"**Electromagnetic Scattering Mechanism:**\n{r_info['mechanism']}")
            st.markdown(f"**Hazard Classification:** `{r_info['hazard_tier']}`")
            st.markdown(f"**Polar Code Implication:** `{r_info['status']}`")


if tab_physics.open:
    with tab_physics:
        st.subheader("🛰️ SAR Physics & Radar Electromagnetics Briefing")
        st.caption("2026 NASA Space Apps Challenge ('Dancing with the SARs') — Scientific Foundation for Judges")

        # High-level summary cards
        c1, c2, c3 = st.columns(3)
        with c1:
            with st.container(border=True):
                st.markdown("#### 1. 24 cm L-Band Penetration")
                st.markdown("""
                **Wavelength Advantage:**
                NISAR operates at **L-band (λ = 24 cm / 1.25 GHz)**. Unlike C-band (λ = 5.6 cm) or X-band (λ = 3.1 cm), 24 cm microwave signals penetrate dry Arctic snow covers (10–40 cm) with minimal attenuation. C-band scatters within the snow pack, mistaking snow roughness for ice deformation. NISAR interrogates the true underlying sea ice matrix.
                """)
        with c2:
            with st.container(border=True):
                st.markdown("#### 2. HV Cross-Pol Discrimination")
                st.markdown("""
                **Depolarization & Volume Scattering:**
                Desalinated Multi-Year Ice (MYI) features drained brine channels and dense air bubble pockets that induce intense multiple volume scattering. This depolarizes the transmitted horizontal wave, producing a powerful cross-polarized return (**HV ≈ -16 dB**), whereas First-Year Ice (**HV ≈ -25 dB**) and Open Water (**HV < -30 dB**) exhibit negligible volume depolarization.
                """)
        with c3:
            with st.container(border=True):
                st.markdown("#### 3. Complete Polar Darkness")
                st.markdown("""
                **All-Weather 24/7 Illumination:**
                From late October through March, the Northwest Passage is plunged into **24-hour polar night** beneath pervasive cloud decks and blizzards. Optical sensors (MODIS, Landsat, Sentinel-2) are completely blind. Active SAR provides its own microwave illumination, ensuring uninterrupted navigational safety day and night.
                """)

        st.markdown("---")

        # Comparative Sensor Matrix
        st.markdown("### 📊 Arctic Remote Sensing Sensor Comparison")
        sensor_data = [
            {
                "Sensor / Satellite": "NISAR L-Band SAR (24 cm)",
                "Snow Penetration": "High (penetrates 10-40 cm dry snow to ice structure)",
                "Multi-Year Ice Discrimination": "Superior (intense HV volume scattering from porous ice)",
                "Polar Darkness (Winter)": "✅ 100% Operational (Active Microwave)",
                "Cloud / Fog Penetration": "✅ 100% Transparent (All-Weather)",
                "Tactical Routing Value": "⭐⭐⭐⭐⭐ Definitive safety standard"
            },
            {
                "Sensor / Satellite": "Sentinel-1 / RADARSAT C-Band (5.6 cm)",
                "Snow Penetration": "Poor (significant scattering in snow pack & frost flowers)",
                "Multi-Year Ice Discrimination": "Moderate (ambiguous backscatter between rough FYI and MYI)",
                "Polar Darkness (Winter)": "✅ 100% Operational",
                "Cloud / Fog Penetration": "✅ 100% Transparent",
                "Tactical Routing Value": "⭐⭐⭐ Susceptible to snow ambiguities"
            },
            {
                "Sensor / Satellite": "Optical (MODIS / Landsat / Sentinel-2)",
                "Snow Penetration": "Zero (reflects off snow surface)",
                "Multi-Year Ice Discrimination": "Low (ice types look uniformly white/grey)",
                "Polar Darkness (Winter)": "❌ Completely Inoperable (0 hrs daylight)",
                "Cloud / Fog Penetration": "❌ Blocked by Arctic fog and storm clouds",
                "Tactical Routing Value": "⭐ Useless during winter freeze-up"
            }
        ]
        st.table(
            sensor_data,
            alt="Comparison of NISAR L-band SAR, Sentinel-1/RADARSAT C-band SAR, and optical sensors across snow penetration, multi-year ice discrimination, polar darkness operation, and cloud penetration",
        )

        st.markdown("---")

        _render_polarimetric_simulator()


# ==========================================
# FOOTER SYSTEM STATE & VERIFICATION
# ==========================================
st.divider()
footer_col1, footer_col2 = st.columns([2, 1])

with footer_col1:
    st.caption("Northwest Passage SAR Ice Navigator | 2026 NASA Space Apps Challenge ('Dancing with the SARs')")
    st.caption("Antigravity Maritime Autonomous Decision Matrix — Powered by NISAR L2 GCOV Radar Observations")

with footer_col2:
    if manifest_status["is_fallback"]:
        st.caption("Active State: Calibrated Synthetic Barrow Strait Fallback Mode")
    else:
        st.caption(f"Active State: Real Manifest Mode ({manifest_status['scene_count']} scenes loaded)")
