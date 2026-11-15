"""
app/components/map_view.py
Interactive Leafmap & Folium map rendering component for the Tactical Route Map.
Overlays calibrated L-band radar rasters (Dual-Pol RGB / 3-Tier Hazard classification),
interactive NORDREG corridor vectors with status color-coding, and key Arctic navigation POIs.
"""

import folium
from folium import plugins
import json
import streamlit as st
from typing import Dict, Any, Optional


def create_tactical_folium_map(
    scene_dataset: Dict[str, Any],
    routes_geojson: Dict[str, Any],
    active_route_id: str,
    evaluations: Dict[str, Any],
    radar_mode: str = "3-Tier Hazard Classification",
    radar_opacity: float = 0.80,
    fit_full_passage: bool = False
) -> folium.Map:
    """
    Constructs an interactive Folium Map centered on the active NISAR SAR mosaic bounding box
    (or fitted to the full Baffin Bay–to–Beaufort Sea Northwest Passage when fit_full_passage=True).
    """
    bounds = scene_dataset["bounds"]
    s_south, s_west = bounds[0]
    s_north, s_east = bounds[1]
    swath_center = scene_dataset.get(
        "swath_center",
        [(s_south + s_north) / 2.0, (s_west + s_east) / 2.0],
    )
    swath_lon_span = abs(s_east - s_west)

    if fit_full_passage:
        center_lat = 71.80
        center_lon = -104.50
        zoom_start = 4
    else:
        # Center on the active NISAR SAR mosaic bounding box so the radar overlay stays crisp
        box_lat = (s_south + s_north) / 2.0
        box_lon = (s_west + s_east) / 2.0
        center_lat = (swath_center[0] * 0.35) + (box_lat * 0.65)
        center_lon = (swath_center[1] * 0.35) + (box_lon * 0.65)
        zoom_start = 7 if swath_lon_span < 6.5 else 6

    # Base map using satellite imagery
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        name="Satellite Basemap",
        control_scale=True
    )

    if fit_full_passage:
        m.fit_bounds([[68.0, -133.5], [75.5, -75.5]])

    if radar_mode == "Dual-Pol False-Color RGB (HH/HV)":
        folium.raster_layers.ImageOverlay(
            image=scene_dataset["rgb_data_url"],
            bounds=bounds,
            opacity=radar_opacity,
            name="NISAR Dual-Pol RGB (R:HH, G:HV, B:Ratio)",
            interactive=True
        ).add_to(m)

    elif radar_mode == "3-Tier Hazard Classification":
        folium.raster_layers.ImageOverlay(
            image=scene_dataset["hazard_data_url"],
            bounds=bounds,
            opacity=radar_opacity,
            name="3-Tier Ice Hazard Map (Blue:Water, Cyan:FYI, Red:MYI)",
            interactive=True
        ).add_to(m)

    # 2. Key Maritime POIs and Waypoints
    pois = [
        {
            "name": "Resolute Bay Port (74.7° N, 95.0° W)",
            "coords": [74.697, -94.829],
            "icon": "anchor",
            "color": "blue",
            "desc": "Primary Canadian Arctic logistical hub and ice monitoring station on Cornwallis Island."
        },
        {
            "name": "Lancaster Sound Gateway (East Entrance)",
            "coords": [74.32, -90.00],
            "icon": "compass",
            "color": "green",
            "desc": "Eastern convergence gate entering Barrow Strait from Baffin Bay."
        },
        {
            "name": "Viscount Melville Sound Gateway (West Exit)",
            "coords": [74.42, -98.50],
            "icon": "ship",
            "color": "purple",
            "desc": "Western gateway connecting to Beaufort Sea and western NWP corridors."
        },
        {
            "name": "Somerset Island Coastal Anchorage",
            "coords": [74.12, -93.80],
            "icon": "shield",
            "color": "orange",
            "desc": "Sheltered southern waterway along Somerset Island northern bluffs."
        },
        {
            "name": "M'Clure Strait Western Gate (Beaufort Exit)",
            "coords": [74.75, -121.00],
            "icon": "compass",
            "color": "green",
            "desc": "Western deep-water chokepoint exiting M'Clure Strait toward the Beaufort Sea."
        },
        {
            "name": "Mercy Bay / Banks Island Monitoring Point",
            "coords": [74.15, -119.00],
            "icon": "anchor",
            "color": "blue",
            "desc": "Historic HMS Investigator anchorage and northern Banks Island ice monitoring point."
        },
        {
            "name": "Victoria Strait Northern Gate (Larsen Sound)",
            "coords": [70.15, -100.70],
            "icon": "compass",
            "color": "purple",
            "desc": "Northern entrance to Victoria Strait between Victoria Island and King William Island."
        },
        {
            "name": "King William Island / Queen Maud Gulf Gate",
            "coords": [69.00, -99.75],
            "icon": "anchor",
            "color": "orange",
            "desc": "Southern Victoria Strait exit into Queen Maud Gulf along the Amundsen route."
        },
        {
            "name": "Baffin Bay Eastern Gateway (Lancaster Entrance)",
            "coords": [73.95, -76.00],
            "icon": "ship",
            "color": "darkblue",
            "desc": "Eastern Atlantic/Baffin Bay entry into the Northwest Passage."
        },
        {
            "name": "Beaufort Sea Western Gateway (Amundsen / M'Clure Exit)",
            "coords": [72.50, -133.00],
            "icon": "ship",
            "color": "darkgreen",
            "desc": "Western Beaufort Sea exit completing the Baffin Bay–to–Beaufort Sea transit."
        }
    ]

    for poi in pois:
        folium.Marker(
            location=poi["coords"],
            tooltip=poi["name"],
            popup=folium.Popup(f"<b>{poi['name']}</b><br>{poi['desc']}", max_width=250),
            icon=folium.Icon(icon=poi["icon"], prefix="fa", color=poi["color"])
        ).add_to(m)

    # 3. Add Shipping Routes with Status Styling
    for feature in routes_geojson.get("features", []):
        r_props = feature["properties"]
        rid = r_props["route_id"]
        is_active = (rid == active_route_id)
        
        # Get evaluation status
        eval_item = evaluations.get(rid, {})
        status = eval_item.get("telemetry", {}).get("status", "NAVIGABLE")
        
        # Status driven styling
        if status == "BLOCKED":
            color = "#FF1744"  # Red
            weight = 6 if is_active else 3
            dash_array = "8, 6" if not is_active else None
        elif status == "CAUTION":
            color = "#FFC107"  # Amber
            weight = 6 if is_active else 3
            dash_array = "6, 4" if not is_active else None
        else:
            color = "#00E676"  # Bright Green
            weight = 6 if is_active else 3
            dash_array = "4, 4" if not is_active else None

        # Convert LineString coordinates [lon, lat] -> [lat, lon] for folium
        coords_latlon = [[c[1], c[0]] for c in feature["geometry"]["coordinates"]]

        tooltip_text = f"<b>{r_props['name']}</b><br>Status: {status} ({eval_item.get('telemetry', {}).get('risk_index', 0)}/100 risk)"
        
        folium.PolyLine(
            locations=coords_latlon,
            color=color,
            weight=weight,
            opacity=0.95 if is_active else 0.65,
            dash_array=dash_array,
            tooltip=tooltip_text,
            name=f"Corridor: {r_props['name']}"
        ).add_to(m)

        # If this is the active route, place a vessel icon near the sampled chokepoint midpoint
        if is_active and len(coords_latlon) >= 2:
            sampled_pts = eval_item.get("breakdown", {}).get("sample_points", [])
            if sampled_pts and not fit_full_passage:
                sp_mid = sampled_pts[len(sampled_pts) // 2]
                mid_pt = [float(sp_mid[1]), float(sp_mid[0])]
            else:
                mid_idx = len(coords_latlon) // 2
                mid_pt = coords_latlon[mid_idx]
            folium.Marker(
                location=mid_pt,
                tooltip=f"Vessel Position: {eval_item.get('telemetry', {}).get('vessel_class', 'Vessel')}",
                icon=folium.Icon(icon="ship", prefix="fa", color="darkred" if status == "BLOCKED" else "cadetblue")
            ).add_to(m)

    # Controls
    folium.LayerControl(position="topright", collapsed=True).add_to(m)
    plugins.Fullscreen(position="topleft").add_to(m)
    plugins.MiniMap(toggle_display=True, position="bottomleft").add_to(m)

    return m
