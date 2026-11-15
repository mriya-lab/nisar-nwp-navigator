"""
app/components/telemetry_cards.py
Modular UI component for rendering real-time voyage telemetry cards,
Polar Code operational status badges, ice hazard concentration breakdowns,
and comparative corridor optimization matrices.
"""

import base64
import streamlit as st
from typing import Dict, Any, List


def render_route_status_banner(telemetry: Dict[str, Any], route_name: str):
    """Renders the primary operational status header card."""
    status = telemetry["status"]
    color = telemetry["status_color"]
    reason = telemetry["status_reason"]
    vessel = telemetry["vessel_class"]

    if status == "NAVIGABLE":
        badge_icon = "🟢"
        callout_type = st.success
    elif status == "CAUTION":
        badge_icon = "🟡"
        callout_type = st.warning
    else:
        badge_icon = "🔴"
        callout_type = st.error

    with st.container(border=True):
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <h3 style="margin: 0; color: {color};">
                        {badge_icon} OPERATIONAL STATUS: {status}
                    </h3>
                    <p style="margin: 4px 0 0 0; color: #BBB; font-size: 0.95rem;">
                        <strong>Corridor:</strong> {route_name} | <strong>Assigned Vessel:</strong> {vessel}
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown(f"**Polar Code Assessment:** {reason}")


def render_kpi_metrics(telemetry: Dict[str, Any]):
    """Renders the top KPI metrics in a 4-column row."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Corridor Distance",
            value=f"{telemetry['distance_nm']} NM",
            delta=f"Speed: {telemetry['effective_speed_knots']} kn (Nominal: {telemetry['nominal_speed_knots']} kn)",
            delta_color="off"
        )

    with col2:
        delay = telemetry["transit_delay_hours"]
        delta_str = f"+{delay}h ice delay" if delay > 0 else "On schedule"
        delta_color = "inverse" if delay > 0 else "normal"
        st.metric(
            label="Estimated Transit Time",
            value=f"{telemetry['actual_transit_hours']} hrs",
            delta=delta_str,
            delta_color=delta_color
        )

    with col3:
        excess = telemetry["excess_fuel_penalty_tons"]
        pct = telemetry["fuel_penalty_pct"]
        delta_str = f"+{excess}t (+{pct}%)" if excess > 0 else "0% penalty"
        delta_color = "inverse" if excess > 0 else "normal"
        st.metric(
            label="Projected Fuel Burn",
            value=f"{telemetry['total_fuel_tons']} Tons",
            delta=delta_str,
            delta_color=delta_color
        )

    with col4:
        risk = telemetry["risk_index"]
        status = telemetry["status"]
        st.metric(
            label="Composite Risk Index",
            value=f"{risk} / 100",
            delta=f"Polar Code: {status}",
            delta_color="inverse" if risk > 25 else "normal"
        )


def render_ice_breakdown_bars(breakdown: Dict[str, Any]):
    """Renders progress breakdown of Open Water, FYI, and MYI."""
    with st.container(border=True):
        st.markdown("**Corridor Ice Composition Breakdown**")
        st.caption("Sampled at 350 georeferenced coordinates along the active transit route.")

        p1 = breakdown["open_water_pct"]
        p2 = breakdown["fyi_pct"]
        p3 = breakdown["myi_pct"]

        st.markdown(f"🌊 **Open Water (Tier 1):** `{p1:.1f}%`")
        st.progress(min(1.0, max(0.0, p1 / 100.0)))
        st.markdown(f"❄️ **First-Year Ice (Tier 2):** `{p2:.1f}%`")
        st.progress(min(1.0, max(0.0, p2 / 100.0)))
        st.markdown(f"⚠️ **Multi-Year / Ridged (Tier 3):** `{p3:.1f}%`")
        st.progress(min(1.0, max(0.0, p3 / 100.0)))


def render_corridor_comparison_table(evaluations: List[Dict[str, Any]], active_route_id: str):
    """
    Renders a tactical comparison table between available corridors,
    highlighting the optimal route choice.
    """
    with st.container(border=True):
        st.markdown("### 🧭 Tactical Routing Decision Matrix")
        st.caption("Direct comparison of primary and alternate passage corridors under current SAR ice conditions.")

        rows = []
        for item in evaluations:
            t = item["telemetry"]
            b = item["breakdown"]
            r_info = item["route_info"]
            is_active = (r_info["route_id"] == active_route_id)
            active_marker = " 🎯 [Selected]" if is_active else ""

            status_icon = "🟢" if t["status"] == "NAVIGABLE" else ("🟡" if t["status"] == "CAUTION" else "🔴")

            rows.append({
                "Corridor Route": f"{r_info['name']}{active_marker}",
                "Status": f"{status_icon} {t['status']}",
                "Distance": f"{t['distance_nm']} NM",
                "Est. Transit Time": f"{t['actual_transit_hours']} h (+{t['transit_delay_hours']}h)",
                "Fuel Burn": f"{t['total_fuel_tons']} t (+{t['excess_fuel_penalty_tons']}t, +{t['fuel_penalty_pct']}%)",
                "MYI %": f"{b['myi_pct']:.1f}%",
                "Risk Index": f"{t['risk_index']} / 100"
            })

        st.table(
            rows,
            alt="Tactical routing comparison matrix of shipping corridors by status, distance, transit time, fuel burn, multi-year ice percentage, and risk index",
        )

        # Tactical recommendation callout
        if len(evaluations) >= 2:
            r1 = evaluations[0]
            r2 = evaluations[1]
            t1 = r1["telemetry"]
            t2 = r2["telemetry"]

            if t1["status"] == "BLOCKED" and t2["status"] != "BLOCKED":
                st.warning(
                    f"⚠️ **Tactical Reroute Advisory:** {r1['route_info']['name']} is impassable ({t1['status']}). "
                    f"**Recommended Action:** Divert vessel to {r2['route_info']['name']} ({t2['status']}) "
                    f"saving estimated **{t1['transit_delay_hours'] - t2['transit_delay_hours']:.1f} hours** of delay and "
                    f"**{t1['excess_fuel_penalty_tons'] - t2['excess_fuel_penalty_tons']:.1f} tons** of fuel penalty while avoiding catastrophic hull damage."
                )
            elif t1["status"] == t2["status"] and t1["status"] == "NAVIGABLE":
                shorter = r1 if t1["distance_nm"] <= t2["distance_nm"] else r2
                st.success(
                    f"🟢 **Tactical Clearance:** Both corridors are navigable. "
                    f"**Recommended Action:** Proceed via {shorter['route_info']['name']} for fastest passage ({shorter['telemetry']['actual_transit_hours']} hrs)."
                )


def render_vessel_svg_card(vessel_class: str):
    """
    Renders a compact, dark-themed technical SVG hull profile card tailored
    to the currently selected vessel class.
    """
    if vessel_class == "Standard Cargo":
        badge_bg = "rgba(255, 23, 68, 0.16)"
        badge_border = "#FF1744"
        badge_color = "#FF8A80"
        badge_text = "Zero MYI tolerance — open water leads only"
        svg_markup = """
        <svg viewBox="0 0 320 85" style="width: 100%; height: 85px; display: block;" xmlns="http://www.w3.org/2000/svg">
          <rect width="320" height="85" rx="6" fill="#0B121E" stroke="#1E2D42" stroke-width="1"/>
          <!-- Waterline -->
          <line x1="8" y1="54" x2="312" y2="54" stroke="#1565C0" stroke-width="1" stroke-dasharray="4,3"/>
          <!-- Aft bridge & superstructure -->
          <rect x="28" y="22" width="22" height="20" rx="1" fill="#293B52" stroke="#5C7696" stroke-width="1"/>
          <rect x="33" y="16" width="14" height="6" fill="#3E5674"/>
          <!-- Container stacks -->
          <rect x="60" y="28" width="34" height="14" fill="#1E3A5F" stroke="#3B6998" stroke-width="0.8"/>
          <rect x="98" y="26" width="34" height="16" fill="#23456E" stroke="#3B6998" stroke-width="0.8"/>
          <rect x="136" y="28" width="34" height="14" fill="#1E3A5F" stroke="#3B6998" stroke-width="0.8"/>
          <rect x="174" y="30" width="32" height="12" fill="#23456E" stroke="#3B6998" stroke-width="0.8"/>
          <!-- Hull with prominent bulbous bow (right) -->
          <path d="M 20 42 L 245 42 L 252 52 C 264 52, 267 60, 256 64 L 236 64 L 26 64 L 20 52 Z"
                fill="#1B2838" stroke="#90A4AE" stroke-width="1.3"/>
          <!-- Highlighted thin mild steel bow section -->
          <path d="M 244 42 L 252 52 C 264 52, 267 60, 256 64 L 238 64"
                fill="none" stroke="#FF5252" stroke-width="2.2"/>
          <!-- Callout line & label -->
          <line x1="255" y1="48" x2="268" y2="26" stroke="#FF8A80" stroke-width="1"/>
          <circle cx="255" cy="48" r="2.2" fill="#FF5252"/>
          <text x="182" y="16" fill="#FF8A80" font-family="monospace" font-size="9.5" font-weight="bold">12–15 mm mild steel hull</text>
          <text x="14" y="77" fill="#7F94B0" font-family="sans-serif" font-size="9">PROFILE: Bulbous-Bow Container / Bulk Carrier</text>
        </svg>
        """
    elif vessel_class == "Polar Class 6":
        badge_bg = "rgba(255, 193, 7, 0.16)"
        badge_border = "#FFC107"
        badge_color = "#FFE082"
        badge_text = "Summer/autumn medium first-year ice up to 1.0 m"
        svg_markup = """
        <svg viewBox="0 0 320 85" style="width: 100%; height: 85px; display: block;" xmlns="http://www.w3.org/2000/svg">
          <rect width="320" height="85" rx="6" fill="#0B121E" stroke="#1E2D42" stroke-width="1"/>
          <!-- Waterline & thin FYI floes -->
          <line x1="8" y1="54" x2="312" y2="54" stroke="#00BCD4" stroke-width="1" stroke-dasharray="5,3"/>
          <rect x="255" y="51" width="22" height="4" rx="1" fill="#00E5FF" opacity="0.65"/>
          <rect x="282" y="51" width="18" height="4" rx="1" fill="#00E5FF" opacity="0.5"/>
          <!-- Superstructure & crane -->
          <rect x="44" y="20" width="38" height="22" rx="1.5" fill="#293B52" stroke="#6482A6" stroke-width="1"/>
          <rect x="52" y="13" width="18" height="7" fill="#3E5674"/>
          <path d="M 135 42 L 135 24 L 165 30" fill="none" stroke="#6482A6" stroke-width="1.5"/>
          <!-- Raked ice-strengthened hull -->
          <path d="M 22 42 L 260 40 L 244 55 L 228 64 L 28 64 L 22 53 Z"
                fill="#1D2E42" stroke="#90A4AE" stroke-width="1.2"/>
          <!-- Highlighted cyan ice-belt plating along waterline & raked stem -->
          <path d="M 30 50 L 249 50 L 260 40 L 244 55 L 228 64 L 185 60 L 30 58 Z"
                fill="rgba(0, 229, 255, 0.25)" stroke="#00E5FF" stroke-width="2.2"/>
          <!-- Callout line & label -->
          <line x1="251" y1="47" x2="264" y2="25" stroke="#00E5FF" stroke-width="1"/>
          <circle cx="251" cy="47" r="2.2" fill="#00E5FF"/>
          <text x="170" y="17" fill="#00E5FF" font-family="monospace" font-size="9.5" font-weight="bold">25–32 mm ice-belt hull</text>
          <text x="14" y="77" fill="#7F94B0" font-family="sans-serif" font-size="9">PROFILE: PC6 / 1A Super Raked Ice-Strengthened Bow</text>
        </svg>
        """
    else:
        badge_bg = "rgba(0, 230, 118, 0.16)"
        badge_border = "#00E676"
        badge_color = "#69F0AE"
        badge_text = "Continuous multi-year ice & pressure ridge penetration"
        svg_markup = """
        <svg viewBox="0 0 320 85" style="width: 100%; height: 85px; display: block;" xmlns="http://www.w3.org/2000/svg">
          <rect width="320" height="85" rx="6" fill="#0B121E" stroke="#1E2D42" stroke-width="1"/>
          <!-- Waterline & ridged MYI pack -->
          <line x1="8" y1="54" x2="312" y2="54" stroke="#00E5FF" stroke-width="1" stroke-dasharray="3,2"/>
          <polygon points="248,54 262,46 276,54 268,61 252,59" fill="#FF1744" opacity="0.45"/>
          <polygon points="278,54 292,48 306,54 298,60 282,58" fill="#00E5FF" opacity="0.55"/>
          <!-- Heavy Icebreaker mid-forward superstructure & aft helideck -->
          <rect x="26" y="34" width="35" height="6" fill="#37474F" stroke="#78909C" stroke-width="0.9"/>
          <rect x="75" y="18" width="68" height="22" rx="2" fill="#32465E" stroke="#7FA1C3" stroke-width="1"/>
          <rect x="92" y="11" width="28" height="7" fill="#496584"/>
          <!-- Spoon-shaped icebreaking bow & deep hull -->
          <path d="M 22 40 L 264 36 C 258 48, 244 58, 222 65 L 32 65 L 22 52 Z"
                fill="#221E2A" stroke="#B0BEC5" stroke-width="1.2"/>
          <!-- Highlighted crimson reinforced keel & spoon bow plating -->
          <path d="M 32 65 L 222 65 C 244 58, 258 48, 264 36 L 250 37 C 244 48, 232 56, 214 61 L 32 61 Z"
                fill="rgba(255, 23, 68, 0.38)" stroke="#FF1744" stroke-width="2.4"/>
          <!-- Callout line & label -->
          <line x1="252" y1="48" x2="264" y2="25" stroke="#FF5252" stroke-width="1"/>
          <circle cx="252" cy="48" r="2.4" fill="#FF1744"/>
          <text x="155" y="17" fill="#FF8A80" font-family="monospace" font-size="9.5" font-weight="bold">45–55 mm keel &amp; bow</text>
          <text x="14" y="77" fill="#7F94B0" font-family="sans-serif" font-size="9">PROFILE: Polar Class 2/3 Spoon-Bow Heavy Icebreaker</text>
        </svg>
        """

    b64_svg = base64.b64encode(svg_markup.strip().encode("utf-8")).decode("ascii")
    html = (
        f'<div style="margin: 4px 0 10px 0;">'
        f'<img src="data:image/svg+xml;base64,{b64_svg}" '
        f'alt="{vessel_class} technical hull profile" '
        f'style="width: 100%; height: 85px; display: block; border-radius: 6px;" />'
        f'<div style="margin-top: 5px; padding: 4px 8px; border-radius: 4px; '
        f'background: {badge_bg}; border: 1px solid {badge_border}; color: {badge_color}; '
        f'font-size: 0.76rem; font-weight: 600; text-align: center; letter-spacing: 0.01em;">'
        f'{badge_text}</div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)

