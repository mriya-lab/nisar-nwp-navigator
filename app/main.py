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
    ["NORDREG Deep Water Route", "Amundsen Gulf / Dolphin & Union Strait", "Lancaster Sound Entrance"]
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
    
    # Initialize high-performance leafmap engine focused on the Canadian Arctic Archipelago
    m = leafmap.Map(center=[74.5, -95.0], zoom=4, height=600)
    
    # Placeholder for loading GIS overlays and Raster layers
    # m.add_geojson("data/gis/nordreg_corridors.geojson", layer_name="NORDREG Routes")
    
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
        # Placeholder for st.bar_chart or st.pyplot distribution tracking
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
