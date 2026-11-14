import streamlit as st
import leafmap.foliumap as leafmap
import os
import json

# Setup configuration
st.set_page_config(
    page_title="NISAR NWP Navigator",
    page_icon="🛳️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🛳️ NISAR Northwest Passage Navigator")
st.caption("Antigravity Maritime Tactical Routing Engine — Powered by NISAR Radar Observations")

# Sidebar Configuration Matrix
st.sidebar.header("Control Panel")
corridor_selection = st.sidebar.selectbox(
    "Select Shipping Corridor",
    ["NORDREG Deep Water Route", "Lancaster Sound Entrance", "Amundsen Gulf / Dolphin & Union Strait"]
)

ice_class = st.sidebar.select_slider(
    "Vessel Ice Class Certification",
    options=["Open Water (None)", "Type B", "Type A", "CAC 4", "CAC 3", "Polar Class 6", "Polar Class 1"]
)

st.sidebar.divider()
st.sidebar.subheader("Telemetry Feeds")
st.sidebar.metric(label="Active NISAR COG Granules", value="12", delta="+2 within 24h")
st.sidebar.metric(label="Average Route Risk Index", value="34 / 100", delta="-5 optimized")

# Core App Grid Split
col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("Tactical Split-Screen Corridor Evaluation")
    
    # Initialize leafmap engine centered on Canadian Arctic Archipelago
    m = leafmap.Map(center=[74.5, -95.0], zoom=4, height=600)
    
    # Load and overlay the GeoJSON routes if the file exists
    geojson_path = "data/gis/nordreg_corridors.geojson"
    if os.path.exists(geojson_path):
        with open(geojson_path, "r") as f:
            geojson_data = json.load(f)
        
        # Filter the GeoJSON features based on sidebar selection for explicit highlighting
        filtered_features = [
            f for f in geojson_data["features"] 
            if f["properties"]["name"] == corridor_selection
        ]
        
        if filtered_features:
            highlighted_geojson = {
                "type": "FeatureCollection",
                "features": filtered_features
            }
            # Add selected route styled with a prominent bright color
            m.add_geojson(
                highlighted_geojson, 
                layer_name=f"Active: {corridor_selection}",
                style={"color": "#00FFCC", "weight": 5, "opacity": 0.9}
            )
        
        # Overlay the full base transit grid behind it
        m.add_geojson(
            geojson_data, 
            layer_name="All NORDREG Corridors",
            style={"color": "#666666", "weight": 2, "opacity": 0.5}
        )
    
    m.to_streamlit()

with col2:
    st.subheader("Voyage Telemetry & Diagnostics")
    
    with st.container(border=True):
        st.markdown("**Corridor Operational Status**")
        st.success("🟢 Route Go / Clear Minimal Risk")
        st.info(f"Assigned Tier: {ice_class}")
        
    with st.container(border=True):
        st.markdown("**Backscatter Intensity Histogram**")
        st.caption("Distribution across current corridor bounding box (dB)")
        st.info("Awaiting pipeline/processed raster data to plot distribution.")

# Footer Manifest Monitor
st.divider()
st.subheader("System Data State Matrix (`manifest.json`)")
manifest_path = "data/processed/manifest.json"
if os.path.exists(manifest_path):
    with open(manifest_path, "r") as f:
        st.json(json.load(f))
else:
    st.info(f"No active data manifest discovered at `{manifest_path}`. Run `pipeline/fetch_and_process.py` to seed data inputs.")
