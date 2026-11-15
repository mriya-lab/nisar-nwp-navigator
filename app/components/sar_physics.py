"""
app/components/sar_physics.py
Visual diagrams, real Arctic sea-ice reference photography loader, and 2D polarimetric
classification space chart for Tab 3 ("SAR Physics & Briefing").
"""

import os
import base64
from functools import lru_cache
from typing import Dict, Any, Optional
import streamlit as st
import plotly.graph_objects as go

ASSETS_PHYSICS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "physics")
)

REGIME_VISUAL_SPECS: Dict[str, Dict[str, Any]] = {
    "Calm Open Water": {
        "filename": "calm_open_water.jpg",
        "photo_caption": "Arctic Open-Water Lead — Specular mirror surface reflects radar energy away from sensor",
        "photo_alt": "Calm open water lead beside Arctic sea ice",
        "hh_center": -24.0,
        "hv_center": -32.5,
        "hh_span": 2.0,
        "hv_span": 2.5,
    },
    "Wind-Roughened Open Sea": {
        "filename": "wind_open_sea.jpg",
        "photo_caption": "Wind-Roughened Capillary Waves — Bragg resonance raises HH co-pol while HV remains suppressed",
        "photo_alt": "Wind-roughened Arctic sea surface with capillary and gravity waves",
        "hh_center": -17.5,
        "hv_center": -30.0,
        "hh_span": 1.5,
        "hv_span": 2.0,
    },
    "Smooth First-Year Ice (FYI)": {
        "filename": "first_year_ice.jpg",
        "photo_caption": "Saline First-Year Sea Ice — Brine pockets attenuate wave penetration; moderate surface scatter",
        "photo_alt": "Flat snow-covered first-year sea ice floe in the Arctic",
        "hh_center": -13.5,
        "hv_center": -22.0,
        "hh_span": 1.8,
        "hv_span": 2.0,
    },
    "Deformed / Ridged Multi-Year Ice (MYI)": {
        "filename": "multi_year_ice.jpg",
        "photo_caption": "Ridged Multi-Year Pack Ice — Desalinated air pockets & ridge keels drive strong HV depolarization",
        "photo_alt": "Heavily ridged multi-year sea ice pressure ridge in the high Arctic",
        "hh_center": -10.0,
        "hv_center": -15.5,
        "hh_span": 2.0,
        "hv_span": 2.0,
    },
}


@lru_cache(maxsize=8)
def _load_physics_photo_b64(filename: str) -> Optional[str]:
    """Reads and base64-encodes a cached Arctic reference photo from assets/physics/."""
    path = os.path.join(ASSETS_PHYSICS_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def render_pillar_svg(pillar_key: str) -> None:
    """
    Renders one of the three core dark-mode technical SVG diagrams (height: 150px)
    for the SAR Physics Briefing cards.
    """
    if pillar_key == "snow_penetration":
        svg = """
        <svg viewBox="0 0 360 150" style="width: 100%; height: 150px; display: block; border-radius: 8px;" xmlns="http://www.w3.org/2000/svg">
          <rect width="360" height="150" rx="8" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
          <!-- Atmosphere label -->
          <text x="12" y="18" fill="#94a3b8" font-family="monospace" font-size="9.5">ATMOSPHERE</text>
          <!-- Dry Snow Layer (30 cm) -->
          <rect x="8" y="55" width="344" height="38" fill="#1e293b" opacity="0.85"/>
          <line x1="8" y1="55" x2="352" y2="55" stroke="#94a3b8" stroke-width="1" stroke-dasharray="4,3"/>
          <text x="268" y="70" fill="#cbd5e1" font-family="monospace" font-size="9" font-weight="bold">30 cm Dry Snow</text>
          <text x="268" y="82" fill="#94a3b8" font-family="sans-serif" font-size="8.5">&amp; Frost Flowers</text>
          <!-- Snow grains -->
          <circle cx="72" cy="68" r="2.2" fill="#fbbf24" opacity="0.9"/>
          <circle cx="84" cy="76" r="2.0" fill="#fbbf24" opacity="0.8"/>
          <circle cx="64" cy="79" r="1.8" fill="#cbd5e1" opacity="0.6"/>
          <circle cx="95" cy="65" r="2.0" fill="#fbbf24" opacity="0.8"/>
          <!-- True Sea-Ice Substrate -->
          <rect x="8" y="93" width="344" height="49" rx="4" fill="#0c2d48"/>
          <path d="M 8 93 L 145 93 L 155 86 L 168 95 L 182 85 L 195 93 L 352 93" fill="none" stroke="#38bdf8" stroke-width="2"/>
          <text x="248" y="128" fill="#38bdf8" font-family="monospace" font-size="9.5" font-weight="bold">True Sea-Ice Matrix</text>

          <!-- Left: C-Band (5.6 cm) scatters in snowpack -->
          <path d="M 30 22 L 74 67" stroke="#fbbf24" stroke-width="2.2" stroke-dasharray="3,2"/>
          <path d="M 74 67 L 48 36" stroke="#fbbf24" stroke-width="1.6"/>
          <path d="M 74 67 L 96 34" stroke="#fbbf24" stroke-width="1.6"/>
          <path d="M 74 67 L 106 48" stroke="#fbbf24" stroke-width="1.4"/>
          <circle cx="74" cy="67" r="3.5" fill="#f43f5e"/>
          <text x="14" y="46" fill="#fbbf24" font-family="monospace" font-size="9.5" font-weight="bold">C-Band (5.6 cm)</text>
          <text x="14" y="114" fill="#fbbf24" font-family="sans-serif" font-size="8.5">Blocked by snow grains</text>

          <!-- Right: NISAR L-Band (24 cm) penetrates snow to ice surface -->
          <path d="M 135 20 L 176 90" stroke="#38bdf8" stroke-width="2.8"/>
          <path d="M 176 90 L 216 22" stroke="#38bdf8" stroke-width="2.4" stroke-dasharray="5,2"/>
          <circle cx="176" cy="90" r="4" fill="#38bdf8"/>
          <text x="142" y="34" fill="#38bdf8" font-family="monospace" font-size="9.5" font-weight="bold">NISAR L-Band (24 cm)</text>
          <text x="122" y="114" fill="#e2e8f0" font-family="sans-serif" font-size="8.5">Penetrates snow → true ice</text>
        </svg>
        """
    elif pillar_key == "hv_depolarization":
        svg = """
        <svg viewBox="0 0 360 150" style="width: 100%; height: 150px; display: block; border-radius: 8px;" xmlns="http://www.w3.org/2000/svg">
          <rect width="360" height="150" rx="8" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
          <!-- Center divider -->
          <line x1="176" y1="10" x2="176" y2="140" stroke="#334155" stroke-width="1" stroke-dasharray="3,3"/>

          <!-- LEFT: First-Year Ice (FYI) Single Bounce -->
          <text x="12" y="19" fill="#38bdf8" font-family="monospace" font-size="9.5" font-weight="bold">FYI: Saline Surface Scatter</text>
          <rect x="10" y="92" width="156" height="46" rx="3" fill="#164e63" opacity="0.65"/>
          <line x1="10" y1="92" x2="166" y2="92" stroke="#38bdf8" stroke-width="2"/>
          <!-- Incident H wave -->
          <line x1="26" y1="34" x2="86" y2="91" stroke="#38bdf8" stroke-width="2.4"/>
          <!-- Specular bounce away + weak HH return -->
          <line x1="86" y1="91" x2="146" y2="38" stroke="#38bdf8" stroke-width="2" stroke-dasharray="4,2"/>
          <line x1="86" y1="91" x2="42" y2="48" stroke="#38bdf8" stroke-width="1.3" opacity="0.7"/>
          <circle cx="86" cy="91" r="3" fill="#38bdf8"/>
          <text x="16" y="112" fill="#cbd5e1" font-family="sans-serif" font-size="8.5">High salinity blocks depth</text>
          <text x="16" y="126" fill="#38bdf8" font-family="monospace" font-size="9" font-weight="bold">HV ≈ -25 dB (Low X-Pol)</text>

          <!-- RIGHT: Multi-Year Ice (MYI) Volume Depolarization -->
          <text x="186" y="19" fill="#f43f5e" font-family="monospace" font-size="9.5" font-weight="bold">MYI: Volume Depolarization</text>
          <path d="M 186 88 L 222 72 L 248 86 L 284 68 L 315 86 L 350 82 L 350 138 L 186 138 Z" fill="#31102f" stroke="#f43f5e" stroke-width="1.8"/>
          <!-- Brine-drained air bubble pockets -->
          <circle cx="242" cy="102" r="5" fill="#0f172a" stroke="#fbbf24" stroke-width="1.3"/>
          <circle cx="268" cy="112" r="6" fill="#0f172a" stroke="#fbbf24" stroke-width="1.3"/>
          <circle cx="290" cy="96" r="4.5" fill="#0f172a" stroke="#fbbf24" stroke-width="1.3"/>
          <!-- Incident H wave penetrating MYI and bouncing between air pockets -->
          <line x1="198" y1="32" x2="242" y2="102" stroke="#38bdf8" stroke-width="2.5"/>
          <line x1="242" y1="102" x2="268" y2="112" stroke="#fbbf24" stroke-width="2.2"/>
          <line x1="268" y1="112" x2="290" y2="96" stroke="#fbbf24" stroke-width="2.2"/>
          <!-- Strong depolarized HV return back to radar -->
          <line x1="290" y1="96" x2="215" y2="30" stroke="#f43f5e" stroke-width="2.6"/>
          <line x1="242" y1="102" x2="195" y2="46" stroke="#f43f5e" stroke-width="2" stroke-dasharray="3,2"/>
          <text x="192" y="129" fill="#fbbf24" font-family="monospace" font-size="9" font-weight="bold">HV &gt; -18.5 dB (Strong HV!)</text>
        </svg>
        """
    else:
        svg = """
        <svg viewBox="0 0 360 150" style="width: 100%; height: 150px; display: block; border-radius: 8px;" xmlns="http://www.w3.org/2000/svg">
          <rect width="360" height="150" rx="8" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
          <!-- Stars in 24h Polar Night sky -->
          <circle cx="30" cy="18" r="1" fill="#e2e8f0"/>
          <circle cx="155" cy="14" r="1.2" fill="#e2e8f0"/>
          <circle cx="205" cy="24" r="1" fill="#e2e8f0"/>
          <circle cx="335" cy="16" r="1.2" fill="#e2e8f0"/>
          <text x="115" y="16" fill="#94a3b8" font-family="monospace" font-size="8.5">24-HR POLAR NIGHT</text>

          <!-- Thick Arctic Storm Cloud Deck -->
          <rect x="14" y="58" width="332" height="28" rx="14" fill="#334155" stroke="#475569" stroke-width="1.2"/>
          <text x="102" y="76" fill="#e2e8f0" font-family="sans-serif" font-size="9.5" font-weight="bold">Dense Arctic Blizzard &amp; Cloud Deck</text>

          <!-- Sea Ice / Barrow Strait Surface -->
          <rect x="8" y="118" width="344" height="24" rx="4" fill="#0c2d48"/>
          <line x1="8" y1="118" x2="352" y2="118" stroke="#38bdf8" stroke-width="1.8"/>
          <text x="112" y="134" fill="#38bdf8" font-family="monospace" font-size="9">Barrow Strait Shipping Corridor</text>

          <!-- LEFT: Optical Sensor (Blocked) -->
          <rect x="42" y="22" width="36" height="12" rx="2" fill="#475569" stroke="#94a3b8" stroke-width="1"/>
          <text x="16" y="46" fill="#cbd5e1" font-family="monospace" font-size="8.5">Optical (MODIS/S2)</text>
          <line x1="60" y1="34" x2="60" y2="58" stroke="#f43f5e" stroke-width="2.2" stroke-dasharray="3,2"/>
          <!-- Red X on cloud top -->
          <line x1="53" y1="53" x2="67" y2="65" stroke="#f43f5e" stroke-width="2.6"/>
          <line x1="67" y1="53" x2="53" y2="65" stroke="#f43f5e" stroke-width="2.6"/>
          <text x="20" y="104" fill="#f43f5e" font-family="monospace" font-size="9" font-weight="bold">✕ BLIND IN DARK/CLOUDS</text>

          <!-- RIGHT: NISAR Active L-Band SAR -->
          <rect x="256" y="20" width="44" height="13" rx="2" fill="#0284c7" stroke="#38bdf8" stroke-width="1.2"/>
          <text x="236" y="45" fill="#38bdf8" font-family="monospace" font-size="8.5" font-weight="bold">NISAR Active L-SAR</text>
          <!-- Active radar beam piercing cloud deck to surface and back -->
          <line x1="274" y1="33" x2="246" y2="117" stroke="#38bdf8" stroke-width="2.6"/>
          <line x1="246" y1="117" x2="286" y2="33" stroke="#fbbf24" stroke-width="2" stroke-dasharray="4,2"/>
          <circle cx="246" cy="117" r="3.5" fill="#fbbf24"/>
          <text x="198" y="104" fill="#38bdf8" font-family="monospace" font-size="9" font-weight="bold">✓ 100% ALL-WEATHER</text>
        </svg>
        """

    b64_svg = base64.b64encode(svg.strip().encode("utf-8")).decode("ascii")
    st.markdown(
        f'<div style="margin: 6px 0 10px 0;">'
        f'<img src="data:image/svg+xml;base64,{b64_svg}" '
        f'alt="{pillar_key} technical radar diagram" '
        f'style="width: 100%; height: 150px; display: block; border-radius: 8px;" />'
        f"</div>",
        unsafe_allow_html=True,
    )


def _get_regime_scattering_svg(regime_name: str) -> str:
    """Returns a dynamic 150px SVG radar bounce diagram tailored to the selected surface regime."""
    if regime_name == "Calm Open Water":
        return """
        <svg viewBox="0 0 380 155" style="width: 100%; height: 155px; display: block; border-radius: 8px;" xmlns="http://www.w3.org/2000/svg">
          <rect width="380" height="155" rx="8" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
          <text x="12" y="20" fill="#38bdf8" font-family="monospace" font-size="10" font-weight="bold">SPECULAR MIRROR REFLECTION (θ ≈ 38°)</text>
          <!-- Mirror flat ocean -->
          <rect x="10" y="102" width="360" height="42" rx="4" fill="#0c2d48"/>
          <line x1="10" y1="102" x2="370" y2="102" stroke="#38bdf8" stroke-width="2.5"/>
          <!-- Incident NISAR pulse -->
          <line x1="48" y1="34" x2="180" y2="101" stroke="#38bdf8" stroke-width="3"/>
          <text x="42" y="58" fill="#38bdf8" font-family="monospace" font-size="9">Incident L-Band</text>
          <!-- Forward specular reflection away from sensor -->
          <line x1="180" y1="101" x2="325" y2="34" stroke="#fbbf24" stroke-width="2.8"/>
          <text x="228" y="55" fill="#fbbf24" font-family="monospace" font-size="9" font-weight="bold">Energy Reflected Away ↗</text>
          <!-- Negligible return to radar -->
          <line x1="180" y1="101" x2="82" y2="48" stroke="#94a3b8" stroke-width="1.2" stroke-dasharray="2,4"/>
          <text x="86" y="86" fill="#94a3b8" font-family="sans-serif" font-size="8.5">Near noise floor return (HH ≈ -24 dB, HV ≈ -33 dB)</text>
          <text x="18" y="130" fill="#cbd5e1" font-family="monospace" font-size="9">Smooth Calm Lead → Minimal Backscatter → TIER 1: OPEN WATER</text>
        </svg>
        """
    elif regime_name == "Wind-Roughened Open Sea":
        return """
        <svg viewBox="0 0 380 155" style="width: 100%; height: 155px; display: block; border-radius: 8px;" xmlns="http://www.w3.org/2000/svg">
          <rect width="380" height="155" rx="8" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
          <text x="12" y="20" fill="#38bdf8" font-family="monospace" font-size="10" font-weight="bold">BRAGG CAPILLARY WAVE SCATTERING</text>
          <!-- Capillary wave surface -->
          <rect x="10" y="104" width="360" height="40" rx="4" fill="#0c2d48"/>
          <path d="M 10 104 Q 25 94, 40 104 T 70 104 T 100 104 T 130 104 T 160 104 T 190 104 T 220 104 T 250 104 T 280 104 T 310 104 T 340 104 T 370 104" fill="none" stroke="#38bdf8" stroke-width="2.5"/>
          <!-- Incident L-Band -->
          <line x1="48" y1="34" x2="175" y2="100" stroke="#38bdf8" stroke-width="3"/>
          <!-- Moderate HH Bragg return back toward sensor -->
          <line x1="175" y1="100" x2="72" y2="38" stroke="#38bdf8" stroke-width="2.4" stroke-dasharray="5,2"/>
          <line x1="205" y1="100" x2="96" y2="42" stroke="#38bdf8" stroke-width="1.8" stroke-dasharray="5,2"/>
          <text x="82" y="54" fill="#38bdf8" font-family="monospace" font-size="9" font-weight="bold">↖ Elevated Co-Pol (HH ≈ -17.5 dB)</text>
          <!-- Suppressed cross-pol -->
          <text x="195" y="78" fill="#fbbf24" font-family="sans-serif" font-size="9">No internal volume → HV stays low (-30 dB)</text>
          <text x="18" y="130" fill="#cbd5e1" font-family="monospace" font-size="9">High HH/HV Ratio (12–15 dB) → TIER 1: OPEN WATER</text>
        </svg>
        """
    elif regime_name == "Smooth First-Year Ice (FYI)":
        return """
        <svg viewBox="0 0 380 155" style="width: 100%; height: 155px; display: block; border-radius: 8px;" xmlns="http://www.w3.org/2000/svg">
          <rect width="380" height="155" rx="8" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
          <text x="12" y="20" fill="#fbbf24" font-family="monospace" font-size="10" font-weight="bold">SALINE FIRST-YEAR ICE SURFACE SCATTERING</text>
          <!-- Snow + Saline FYI layer -->
          <rect x="10" y="88" width="360" height="14" fill="#1e293b"/>
          <rect x="10" y="102" width="360" height="42" rx="4" fill="#164e63"/>
          <line x1="10" y1="102" x2="370" y2="102" stroke="#38bdf8" stroke-width="2.2"/>
          <!-- Brine inclusions absorbing deep waves -->
          <circle cx="170" cy="115" r="2.5" fill="#38bdf8"/>
          <circle cx="192" cy="118" r="2.5" fill="#38bdf8"/>
          <circle cx="215" cy="114" r="2.5" fill="#38bdf8"/>
          <!-- Incident L-Band penetrating snow & scattering at saline ice top -->
          <line x1="52" y1="34" x2="185" y2="102" stroke="#38bdf8" stroke-width="3"/>
          <line x1="185" y1="102" x2="78" y2="40" stroke="#fbbf24" stroke-width="2.3" stroke-dasharray="4,2"/>
          <line x1="185" y1="102" x2="290" y2="46" stroke="#38bdf8" stroke-width="1.8" opacity="0.7"/>
          <text x="86" y="56" fill="#fbbf24" font-family="monospace" font-size="9" font-weight="bold">↖ Moderate HH (-13.5 dB) &amp; HV (-22 dB)</text>
          <text x="18" y="132" fill="#e2e8f0" font-family="monospace" font-size="9">Dielectric brine loss limits volume bounce → TIER 2: FIRST-YEAR ICE</text>
        </svg>
        """
    else:
        return """
        <svg viewBox="0 0 380 155" style="width: 100%; height: 155px; display: block; border-radius: 8px;" xmlns="http://www.w3.org/2000/svg">
          <rect width="380" height="155" rx="8" fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
          <text x="12" y="20" fill="#f43f5e" font-family="monospace" font-size="10" font-weight="bold">MYI PRESSURE RIDGE &amp; BUBBLE DEPOLARIZATION</text>
          <!-- Deformed MYI ridge & deep keel -->
          <path d="M 10 100 L 115 98 L 155 70 L 195 95 L 240 66 L 285 96 L 370 96 L 370 144 L 10 144 Z" fill="#31102f" stroke="#f43f5e" stroke-width="2"/>
          <!-- Desalinated air pockets -->
          <circle cx="170" cy="106" r="5.5" fill="#0f172a" stroke="#fbbf24" stroke-width="1.5"/>
          <circle cx="205" cy="114" r="6" fill="#0f172a" stroke="#fbbf24" stroke-width="1.5"/>
          <circle cx="235" cy="100" r="5" fill="#0f172a" stroke="#fbbf24" stroke-width="1.5"/>
          <!-- Incident L-Band undergoing double-bounce on ridge + volume scatter -->
          <line x1="45" y1="30" x2="155" y2="70" stroke="#38bdf8" stroke-width="2.8"/>
          <line x1="155" y1="70" x2="170" y2="106" stroke="#fbbf24" stroke-width="2.4"/>
          <line x1="170" y1="106" x2="205" y2="114" stroke="#fbbf24" stroke-width="2.4"/>
          <line x1="205" y1="114" x2="235" y2="100" stroke="#fbbf24" stroke-width="2.4"/>
          <!-- Intense depolarized HV + HH backscatter to sensor -->
          <line x1="235" y1="100" x2="95" y2="28" stroke="#f43f5e" stroke-width="3"/>
          <line x1="155" y1="70" x2="68" y2="34" stroke="#f43f5e" stroke-width="2.4" stroke-dasharray="4,2"/>
          <text x="105" y="46" fill="#f43f5e" font-family="monospace" font-size="9.5" font-weight="bold">↖ Intense HV (&gt; -18.5 dB) &amp; HH (-10 dB)</text>
          <text x="18" y="135" fill="#fda4af" font-family="monospace" font-size="9" font-weight="bold">Severe Volume + Ridge Double-Bounce → TIER 3: MULTI-YEAR ICE</text>
        </svg>
        """


def render_regime_photo_and_svg(regime_name: str) -> None:
    """
    Renders the matching real-world Arctic reference photo (from assets/physics/)
    side-by-side with the dynamic SVG radar scattering diagram for the selected regime.
    """
    spec = REGIME_VISUAL_SPECS.get(
        regime_name, REGIME_VISUAL_SPECS["Deformed / Ridged Multi-Year Ice (MYI)"]
    )
    photo_b64 = _load_physics_photo_b64(spec["filename"])
    svg_str = _get_regime_scattering_svg(regime_name)
    svg_b64 = base64.b64encode(svg_str.strip().encode("utf-8")).decode("ascii")

    vcol1, vcol2 = st.columns(2)
    with vcol1:
        if photo_b64:
            st.markdown(
                f'<div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 6px;">'
                f'<img src="data:image/jpeg;base64,{photo_b64}" '
                f'alt="{spec["photo_alt"]}" '
                f'style="width: 100%; height: 155px; object-fit: cover; border-radius: 6px; display: block;" />'
                f'<div style="margin-top: 5px; color: #94a3b8; font-size: 0.76rem; font-style: italic; text-align: center;">'
                f'{spec["photo_caption"]}</div></div>',
                unsafe_allow_html=True,
            )
    with vcol2:
        st.markdown(
            f'<div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 6px;">'
            f'<img src="data:image/svg+xml;base64,{svg_b64}" '
            f'alt="Radar scattering diagram for {regime_name}" '
            f'style="width: 100%; height: 155px; display: block; border-radius: 6px;" />'
            f'<div style="margin-top: 5px; color: #94a3b8; font-size: 0.76rem; font-style: italic; text-align: center;">'
            f'Physical L-Band Scattering Geometry ({regime_name})</div></div>',
            unsafe_allow_html=True,
        )


def render_polarimetric_classification_chart(selected_regime: str) -> None:
    """
    Renders a dark-themed 2D Polarimetric Classification Space Chart (HHHH vs. HVHV dB)
    showing the exact shaded decision zones used by pipeline/fetch_and_process.py
    and highlighting the currently selected simulator regime.
    """
    fig = go.Figure()

    # Exact pipeline decision boundaries (pipeline/fetch_and_process.py lines 174-176):
    # X-axis: HHHH from -30 to 0 dB
    # Y-axis: HVHV from -38 to -8 dB
    # Tier 3 (MYI): HVHV > -18.5 dB OR HHHH > -9.5 dB
    # Tier 2 (FYI): -15.5 <= HHHH <= -9.5 dB AND -25.0 <= HVHV <= -18.5 dB
    # Tier 1 (Open Water): (HHHH < -15.5 dB AND HVHV <= -18.5 dB) OR (-15.5 <= HHHH <= -9.5 dB AND HVHV < -25.0 dB)

    # Shaded Zone 1: Tier 1 Open Water (left & bottom L-shaped region)
    fig.add_shape(
        type="path",
        path="M -30 -38 L -9.5 -38 L -9.5 -25.0 L -15.5 -25.0 L -15.5 -18.5 L -30 -18.5 Z",
        fillcolor="rgba(25, 118, 210, 0.22)",
        line=dict(color="rgba(56, 189, 248, 0.45)", width=1),
        layer="below",
    )

    # Shaded Zone 2: Tier 2 First-Year Ice (central box)
    fig.add_shape(
        type="rect",
        x0=-15.5,
        y0=-25.0,
        x1=-9.5,
        y1=-18.5,
        fillcolor="rgba(0, 188, 212, 0.25)",
        line=dict(color="#38bdf8", width=1.5, dash="dot"),
        layer="below",
    )

    # Shaded Zone 3: Tier 3 Multi-Year / Ridged Ice (top & right L-shaped region)
    fig.add_shape(
        type="path",
        path="M -30 -18.5 L -9.5 -18.5 L -9.5 -38 L 0 -38 L 0 -8 L -30 -8 Z",
        fillcolor="rgba(244, 63, 94, 0.22)",
        line=dict(color="rgba(244, 63, 94, 0.55)", width=1.5),
        layer="below",
    )

    # Decision boundary lines
    fig.add_hline(
        y=-18.5,
        line_dash="solid",
        line_color="#f43f5e",
        line_width=2,
        annotation_text="MYI Cross-Pol Threshold (HV = -18.5 dB)",
        annotation_position="top left",
        annotation_font=dict(size=10, color="#fda4af"),
    )
    fig.add_hline(
        y=-25.0,
        line_dash="dash",
        line_color="#38bdf8",
        line_width=1.5,
        annotation_text="Open Water / FYI Boundary (HV = -25.0 dB)",
        annotation_position="bottom left",
        annotation_font=dict(size=10, color="#38bdf8"),
    )
    fig.add_vline(
        x=-15.5,
        line_dash="dash",
        line_color="#38bdf8",
        line_width=1.5,
        annotation_text="HH = -15.5 dB",
        annotation_position="bottom left",
        annotation_font=dict(size=10, color="#38bdf8"),
    )
    fig.add_vline(
        x=-9.5,
        line_dash="solid",
        line_color="#f43f5e",
        line_width=2,
        annotation_text="Ridge HH = -9.5 dB",
        annotation_position="bottom right",
        annotation_font=dict(size=10, color="#fda4af"),
    )

    # Zone Labels
    fig.add_annotation(
        x=-23.0,
        y=-34.5,
        text="<b>TIER 1: OPEN WATER</b><br>Specular / Bragg Regime",
        showarrow=False,
        font=dict(size=11, color="#7dd3fc"),
        bgcolor="rgba(15, 23, 42, 0.75)",
        bordercolor="#0284c7",
        borderpad=4,
    )
    fig.add_annotation(
        x=-12.5,
        y=-21.75,
        text="<b>TIER 2: FIRST-YEAR ICE</b><br>Saline Surface Scatter",
        showarrow=False,
        font=dict(size=10.5, color="#67e8f9"),
        bgcolor="rgba(15, 23, 42, 0.80)",
        bordercolor="#00bcd4",
        borderpad=3,
    )
    fig.add_annotation(
        x=-21.0,
        y=-12.0,
        text="<b>TIER 3: MULTI-YEAR / RIDGED ICE</b><br>Volume Depolarization & Ridge Double-Bounce",
        showarrow=False,
        font=dict(size=11, color="#fda4af"),
        bgcolor="rgba(15, 23, 42, 0.80)",
        bordercolor="#f43f5e",
        borderpad=4,
    )

    # Plot unselected regimes as subtle reference points
    other_x, other_y, other_names = [], [], []
    for r_name, spec in REGIME_VISUAL_SPECS.items():
        if r_name != selected_regime:
            other_x.append(spec["hh_center"])
            other_y.append(spec["hv_center"])
            other_names.append(r_name)

    fig.add_trace(
        go.Scatter(
            x=other_x,
            y=other_y,
            mode="markers+text",
            name="Reference Sea-Ice Regimes",
            text=other_names,
            textposition="top center",
            textfont=dict(size=10, color="#94a3b8"),
            marker=dict(
                size=11,
                color="#64748b",
                symbol="circle",
                line=dict(color="#cbd5e1", width=1.5),
            ),
            hovertemplate="<b>%{text}</b><br>Mean HHHH: %{x:.1f} dB<br>Mean HVHV: %{y:.1f} dB<extra></extra>",
        )
    )

    # Plot currently selected regime with glowing highlight marker + range error bars
    active_spec = REGIME_VISUAL_SPECS.get(
        selected_regime, REGIME_VISUAL_SPECS["Deformed / Ridged Multi-Year Ice (MYI)"]
    )
    fig.add_trace(
        go.Scatter(
            x=[active_spec["hh_center"]],
            y=[active_spec["hv_center"]],
            mode="markers+text",
            name=f"Selected: {selected_regime}",
            text=[f"🎯 {selected_regime}"],
            textposition="top center",
            textfont=dict(size=12, color="#fbbf24"),
            error_x=dict(
                type="constant",
                value=active_spec["hh_span"],
                color="#fbbf24",
                thickness=2,
                width=6,
            ),
            error_y=dict(
                type="constant",
                value=active_spec["hv_span"],
                color="#fbbf24",
                thickness=2,
                width=6,
            ),
            marker=dict(
                size=18,
                color="#fbbf24",
                symbol="diamond",
                line=dict(color="#ffffff", width=2.5),
            ),
            hovertemplate=(
                f"<b>{selected_regime} (Active)</b><br>"
                "Center HHHH: %{x:.1f} dB (±" + f"{active_spec['hh_span']:.1f} dB)<br>"
                "Center HVHV: %{y:.1f} dB (±" + f"{active_spec['hv_span']:.1f} dB)<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title=dict(
            text="2D Polarimetric Classification Space (NISAR L-Band HHHH vs. HVHV Decision Boundaries)",
            font=dict(size=15, color="#f8fafc"),
        ),
        xaxis=dict(
            title="Co-Polarized Backscatter HHHH σ⁰ (dB) — Surface Roughness & Ridge Geometry",
            range=[-30, 0],
            dtick=5,
            gridcolor="rgba(148, 163, 184, 0.15)",
            zeroline=False,
        ),
        yaxis=dict(
            title="Cross-Polarized Backscatter HVHV σ⁰ (dB) — Volumetric Bubble Depolarization",
            range=[-38, -8],
            dtick=5,
            gridcolor="rgba(148, 163, 184, 0.15)",
            zeroline=False,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11),
        ),
        margin=dict(l=55, r=30, t=65, b=50),
        height=430,
        template="plotly_dark",
        plot_bgcolor="rgba(15, 23, 42, 0.85)",
        paper_bgcolor="rgba(15, 23, 42, 0.0)",
    )

    st.plotly_chart(
        fig,
        width="stretch",
        alt=f"2D polarimetric backscatter classification chart of HHHH versus HVHV in dB highlighting {selected_regime}",
    )
