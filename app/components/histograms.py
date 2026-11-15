"""
app/components/histograms.py
Interactive radar backscatter histogram component utilizing Plotly.
Visualizes calibrated distributions of L-band HHHH (co-pol) and HVHV (cross-pol)
backscatter in decibels (dB), annotating physical dielectric and roughness thresholds.
"""

import streamlit as st
import numpy as np
import plotly.graph_objects as go
from typing import Dict, Any, Optional


def render_backscatter_histograms(
    hh_db: np.ndarray,
    hv_db: np.ndarray,
    hazard: Optional[np.ndarray] = None,
    stage_name: str = ""
):
    """
    Renders interactive Plotly backscatter distribution histograms
    with physical threshold demarcations.
    """
    # Subsample if large to keep browser interaction instant
    sample_size = 8000
    flat_hh = hh_db.flatten()
    flat_hv = hv_db.flatten()
    
    if len(flat_hh) > sample_size:
        idx = np.random.choice(len(flat_hh), sample_size, replace=False)
        sample_hh = flat_hh[idx]
        sample_hv = flat_hv[idx]
    else:
        sample_hh = flat_hh
        sample_hv = flat_hv

    fig = go.Figure()

    # HHHH Backscatter Distribution
    fig.add_trace(go.Histogram(
        x=sample_hh,
        nbinsx=50,
        name="HHHH (Co-Pol Roughness)",
        marker_color="rgba(33, 150, 243, 0.65)",
        opacity=0.75,
        hovertemplate="HH Backscatter: %{x:.1f} dB<br>Count: %{y}<extra></extra>"
    ))

    # HVHV Backscatter Distribution
    fig.add_trace(go.Histogram(
        x=sample_hv,
        nbinsx=50,
        name="HVHV (Cross-Pol Volume Scattering)",
        marker_color="rgba(255, 152, 0, 0.70)",
        opacity=0.75,
        hovertemplate="HV Backscatter: %{x:.1f} dB<br>Count: %{y}<extra></extra>"
    ))

    # Physical Threshold Demarcation Lines
    # Open water threshold (HV < -28 dB)
    fig.add_vline(
        x=-28.0, line_dash="dash", line_color="#4FC3F7", line_width=2,
        annotation_text="Open Water / Specular", annotation_position="top left",
        annotation_font=dict(size=10, color="#4FC3F7")
    )

    # First-Year Ice boundary (-27 to -20 dB)
    fig.add_vline(
        x=-20.0, line_dash="dot", line_color="#81C784", line_width=2,
        annotation_text="FYI Boundary", annotation_position="top",
        annotation_font=dict(size=10, color="#81C784")
    )

    # Multi-Year Ice / Ridges threshold (HV >= -19.5 dB)
    fig.add_vline(
        x=-19.5, line_dash="solid", line_color="#FF5252", line_width=2.5,
        annotation_text="Multi-Year / Ridged Ice", annotation_position="top right",
        annotation_font=dict(size=10, color="#FF5252")
    )

    fig.update_layout(
        title=dict(
            text=f"Dual-Pol Backscatter Intensity Distribution — {stage_name}",
            font=dict(size=15)
        ),
        xaxis_title="Calibrated Radar Backscatter $\\sigma^0$ (dB)",
        yaxis_title="Pixel Count Frequency",
        barmode="overlay",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        height=320,
        template="plotly_dark",
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        paper_bgcolor="rgba(15, 23, 42, 0.0)"
    )

    st.plotly_chart(fig, use_container_width=True)


def render_ice_donut_chart(open_water_pct: float, fyi_pct: float, myi_pct: float):
    """Renders a donut chart illustrating ice classification percentages."""
    labels = ["Open Water (Tier 1)", "First-Year Ice (Tier 2)", "Multi-Year Ice (Tier 3)"]
    values = [open_water_pct, fyi_pct, myi_pct]
    colors = ["#1976D2", "#00BCD4", "#D50000"]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colors),
        textinfo="label+percent",
        hovertemplate="%{label}: <b>%{value:.1f}%</b><extra></extra>"
    )])

    fig.update_layout(
        showlegend=False,
        margin=dict(l=20, r=20, t=20, b=20),
        height=220,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)"
    )

    st.plotly_chart(fig, use_container_width=True)
