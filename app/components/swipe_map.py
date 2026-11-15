"""
app/components/swipe_map.py
Split-screen Before / After swipe comparison slider component.
Enables side-by-side interactive comparison between two acquisition stages
(e.g., August Open-Water Window vs. September Multi-Year Ice Intrusion)
utilizing folium.plugins.SideBySideLayers.
"""

import folium
from folium import plugins
import streamlit as st
from typing import Dict, Any, Optional


def create_swipe_comparison_map(
    left_dataset: Dict[str, Any],
    right_dataset: Dict[str, Any],
    layer_mode: str = "3-Tier Ice Hazard Classification",
    opacity: float = 0.85,
    active_feature: Optional[Dict[str, Any]] = None
) -> folium.Map:
    """
    Constructs an interactive split-screen swipe map comparing two dates/stages.
    """
    left_bounds = left_dataset["bounds"]
    right_bounds = right_dataset["bounds"]
    left_center = left_dataset.get("swath_center", [74.35, -93.40])
    right_center = right_dataset.get("swath_center", [74.35, -93.40])
    lon_span = max(
        abs(left_bounds[1][1] - left_bounds[0][1]),
        abs(right_bounds[1][1] - right_bounds[0][1]),
    )
    if lon_span > 10.0:
        # Frame Barrow Strait corridor and swath overlap consistently with Tactical Route Map
        avg_lat = (left_center[0] + right_center[0]) / 2.0
        avg_lon = (left_center[1] + right_center[1]) / 2.0
        center_lat = (avg_lat * 0.35) + (74.35 * 0.65)
        center_lon = (avg_lon * 0.35) + (-93.40 * 0.65)
        zoom_start = 6
    else:
        center_lat = 74.35
        center_lon = -93.40
        zoom_start = 7

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        name="Satellite Basemap"
    )

    if layer_mode == "Dual-Pol False-Color RGB (HH/HV)":
        left_url = left_dataset["rgb_data_url"]
        right_url = right_dataset["rgb_data_url"]
        left_title = f"{left_dataset['date_str']} (Left) RGB"
        right_title = f"{right_dataset['date_str']} (Right) RGB"
    else:
        left_url = left_dataset["hazard_data_url"]
        right_url = right_dataset["hazard_data_url"]
        left_title = f"{left_dataset['date_str']} (Left) Hazard"
        right_title = f"{right_dataset['date_str']} (Right) Hazard"

    # Add left layer with its own geographic bounds
    layer_left = folium.raster_layers.ImageOverlay(
        image=left_url,
        bounds=left_bounds,
        opacity=opacity,
        name=left_title
    ).add_to(m)

    # Add right layer with its own geographic bounds
    layer_right = folium.raster_layers.ImageOverlay(
        image=right_url,
        bounds=right_bounds,
        opacity=opacity,
        name=right_title
    ).add_to(m)

    # Overlay active shipping corridor for spatial reference if provided
    if active_feature and "geometry" in active_feature:
        coords_latlon = [[c[1], c[0]] for c in active_feature["geometry"]["coordinates"]]
        r_name = active_feature.get("properties", {}).get("name", "Active Corridor")
        folium.PolyLine(
            locations=coords_latlon,
            color="#00E5FF",
            weight=4,
            opacity=0.9,
            dash_array="6, 4",
            tooltip=f"<b>{r_name}</b>",
            name=r_name
        ).add_to(m)

    # Add SideBySide split controller
    sbs = plugins.SideBySideLayers(layer_left=layer_left, layer_right=layer_right)
    sbs.add_to(m)

    # Patch L.ImageOverlay.prototype.getContainer AND L.Control.SideBySide.prototype._updateClip
    # so CSS clip: rect(...) accounts for each ImageOverlay element's own translate3d(pos.x, pos.y) offset
    m.get_root().html.add_child(folium.Element("""
    <script>
    (function() {
        function patchSideBySide() {
            if (!window.L) return;
            if (L.ImageOverlay && !L.ImageOverlay.prototype.getContainer) {
                L.ImageOverlay.prototype.getContainer = function() {
                    return this.getElement();
                };
            }
            if (L.Control && L.Control.SideBySide && !L.Control.SideBySide.prototype._patchedForImageOverlay) {
                L.Control.SideBySide.prototype._patchedForImageOverlay = true;
                var origAddEvents = L.Control.SideBySide.prototype._addEvents;
                L.Control.SideBySide.prototype._addEvents = function() {
                    origAddEvents.apply(this, arguments);
                    if (this._map) {
                        this._map.on("zoom viewreset zoomend moveend", this._updateClip, this);
                    }
                };
                L.Control.SideBySide.prototype._updateClip = function() {
                    var map = this._map;
                    if (!map) return;
                    var nw = map.containerPointToLayerPoint([0, 0]);
                    var se = map.containerPointToLayerPoint(map.getSize());
                    var clipX = nw.x + this.getPosition();
                    var dividerX = this.getPosition();
                    this._divider.style.left = dividerX + "px";
                    this.fire("dividermove", {x: dividerX});

                    if (this._leftLayer && this._leftLayer.getContainer) {
                        var elL = this._leftLayer.getContainer();
                        if (elL) {
                            var posL = L.DomUtil.getPosition(elL) || {x: 0, y: 0};
                            elL.style.clip = "rect(" + [
                                nw.y - posL.y,
                                clipX - posL.x,
                                se.y - posL.y,
                                nw.x - posL.x
                            ].join("px,") + "px)";
                        }
                    }
                    if (this._rightLayer && this._rightLayer.getContainer) {
                        var elR = this._rightLayer.getContainer();
                        if (elR) {
                            var posR = L.DomUtil.getPosition(elR) || {x: 0, y: 0};
                            elR.style.clip = "rect(" + [
                                nw.y - posR.y,
                                se.x - posR.x,
                                se.y - posR.y,
                                clipX - posR.x
                            ].join("px,") + "px)";
                        }
                    }
                };
            }
            // Also refresh any already-instantiated Leaflet maps so initial clip is accurate
            for (var k in window) {
                try {
                    if (k.indexOf("map_") === 0 && window[k] && window[k].fire) {
                        window[k].fire("move");
                    }
                } catch (e) {}
            }
        }
        patchSideBySide();
        document.addEventListener("DOMContentLoaded", patchSideBySide);
        window.addEventListener("load", function() {
            patchSideBySide();
            setTimeout(patchSideBySide, 150);
        });
    })();
    </script>
    """))

    plugins.Fullscreen(position="topleft").add_to(m)

    return m


def render_swipe_differential_metrics(
    left_dataset: Dict[str, Any],
    right_dataset: Dict[str, Any],
    left_eval: Dict[str, Any],
    right_eval: Dict[str, Any],
    route_name: str
):
    """
    Renders differential KPI cards highlighting shifts in ice risk and corridor viability.
    """
    st.markdown(f"#### 📊 Tactical Impact Differential: {left_dataset['name']} ⟷ {right_dataset['name']}")
    st.caption(f"Evaluated along **{route_name}**.")

    col1, col2, col3, col4 = st.columns(4)

    t_left = left_eval["telemetry"]
    t_right = right_eval["telemetry"]
    b_left = left_eval["breakdown"]
    b_right = right_eval["breakdown"]

    with col1:
        myi_delta = b_right["myi_pct"] - b_left["myi_pct"]
        st.metric(
            label="Multi-Year Ice Shift",
            value=f"{b_right['myi_pct']:.1f}%",
            delta=f"{myi_delta:+.1f}% vs {left_dataset['date_str']}",
            delta_color="inverse" if myi_delta > 0 else "normal"
        )

    with col2:
        delay_delta = t_right["transit_delay_hours"] - t_left["transit_delay_hours"]
        st.metric(
            label="Transit Delay Impact",
            value=f"{t_right['transit_delay_hours']} hrs",
            delta=f"{delay_delta:+.1f} hrs delay",
            delta_color="inverse" if delay_delta > 0 else "normal"
        )

    with col3:
        fuel_delta = t_right["excess_fuel_penalty_tons"] - t_left["excess_fuel_penalty_tons"]
        st.metric(
            label="Excess Fuel Penalty",
            value=f"{t_right['excess_fuel_penalty_tons']} Tons",
            delta=f"{fuel_delta:+.1f} Tons (+{t_right['fuel_penalty_pct']}%)",
            delta_color="inverse" if fuel_delta > 0 else "normal"
        )

    with col4:
        st.metric(
            label="Corridor Feasibility",
            value=t_right["status"],
            delta=f"Was: {t_left['status']}",
            delta_color="normal" if t_right["status"] == "NAVIGABLE" else "inverse"
        )
