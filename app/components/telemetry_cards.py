"""
app/components/telemetry_cards.py
Modular UI component for rendering real-time voyage telemetry cards,
Polar Code operational status badges, ice hazard concentration breakdowns,
and comparative corridor optimization matrices.
"""

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

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"🌊 **Open Water (Tier 1):** `{p1:.1f}%`")
            st.progress(min(1.0, max(0.0, p1 / 100.0)))
        with col2:
            st.markdown(f"❄️ **First-Year Ice (Tier 2):** `{p2:.1f}%`")
            st.progress(min(1.0, max(0.0, p2 / 100.0)))
        with col3:
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
