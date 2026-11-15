"""
app/synthetic.py
Calibrated Synthetic NISAR L-Band Radar & Ice Hazard Simulation Engine for Barrow Strait.
Generates physically realistic L-band (24 cm) HHHH and HVHV backscatter arrays and 3-tier
ice hazard classifications for the Northwest Passage maritime tactical navigation portal.
"""

import numpy as np
import rasterio
from rasterio.transform import from_origin
import io
import base64
from PIL import Image

# Barrow Strait Geographical Extent (EPSG:4326)
MIN_LON = -98.5
MAX_LON = -90.0
MIN_LAT = 73.8
MAX_LAT = 75.2
GRID_WIDTH = 510
GRID_HEIGHT = 280

BOUNDS_FOLIUM = [[MIN_LAT, MIN_LON], [MAX_LAT, MAX_LON]]

# Affine transformation for rasterio
RES_LON = (MAX_LON - MIN_LON) / GRID_WIDTH
RES_LAT = (MAX_LAT - MIN_LAT) / GRID_HEIGHT
# top-left origin: (MIN_LON, MAX_LAT), pixel spacing (RES_LON, -RES_LAT)
TRANSFORM = from_origin(MIN_LON, MAX_LAT, RES_LON, RES_LAT)

STAGE_METADATA = {
    "aug_open_water": {
        "id": "aug_open_water",
        "name": "August 2026 — Open-Water Window",
        "date_str": "2026-08-18",
        "phase": "Mid-Summer Peak Navigation",
        "summary": "Predominantly clear open water with negligible multi-year ice. High transit speeds and low fuel burn across both northern deep-water and southern coastal corridors.",
        "ice_condition": "Open Water (~95%) with sparse decaying summer floe fragments.",
        "typical_hh": "-24 to -18 dB",
        "typical_hv": "-33 to -28 dB",
    },
    "sep_myi_intrusion": {
        "id": "sep_myi_intrusion",
        "name": "September 2026 — Multi-Year Ice Choke Intrusion",
        "date_str": "2026-09-24",
        "phase": "Late Season Tactical Choke Event",
        "summary": "Severe southerly advection of thick, deformed multi-year ice floes funneled from Wellington Channel and McDougall Sound. Northern corridor past Resolute Bay is severely choked, while Somerset Island southern bypass offers a protected tactical route.",
        "ice_condition": "Heavy Multi-Year Ice (~42% in northern corridor) with severe pressure ridging.",
        "typical_hh": "-13 to -9 dB (MYI ridges)",
        "typical_hv": "-18 to -14 dB (intense volume scattering)",
    },
    "oct_freeze_up": {
        "id": "oct_freeze_up",
        "name": "October 2026 — Polar Night Freeze-Up",
        "date_str": "2026-10-28",
        "phase": "Winter Freeze-Up in Complete Darkness",
        "summary": "24-hour Arctic polar night. Rapid formation of consolidated First-Year Ice sheet with embedded multi-year floes. Unreinforced vessels blocked; heavy icebreakers operate in continuous ramming mode.",
        "ice_condition": "Consolidated First-Year Ice (~74%) cementing trapped Multi-Year floes (~22%).",
        "typical_hh": "-18 to -14 dB (FYI sheet)",
        "typical_hv": "-26 to -22 dB (FYI) / -17 to -14 dB (MYI)",
    }
}


def _get_coordinate_grids():
    """Generates 2D arrays of longitude and latitude across Barrow Strait."""
    lons = np.linspace(MIN_LON, MAX_LON, GRID_WIDTH)
    lats = np.linspace(MAX_LAT, MIN_LAT, GRID_HEIGHT)  # top to bottom
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    return lon_grid, lat_grid


def _generate_spatial_noise(shape, seed=42, scale=1.0):
    """Generates smooth, spatially correlated random Gaussian noise."""
    rng = np.random.default_rng(seed)
    # Low-pass filter approximation using multi-frequency components
    y, x = np.mgrid[0:shape[0], 0:shape[1]]
    noise = np.zeros(shape, dtype=np.float32)
    for freq in [0.02, 0.05, 0.1]:
        phase_x = rng.uniform(0, 2 * np.pi)
        phase_y = rng.uniform(0, 2 * np.pi)
        amp = (1.0 / (freq * 10)) * scale
        noise += amp * (np.sin(freq * x + phase_x) * np.cos(freq * y + phase_y)).astype(np.float32)
    # Add minor high-frequency speckle
    speckle = rng.normal(0, 0.4 * scale, shape).astype(np.float32)
    noise += speckle
    return noise


def build_calibrated_stage_arrays(stage_id: str):
    """
    Builds calibrated HHHH (dB), HVHV (dB), and 3-Tier Hazard grids (1, 2, 3)
    for a given shipping stage.
    """
    lon_grid, lat_grid = _get_coordinate_grids()
    shape = lon_grid.shape

    # Geographic reference landmarks
    # McDougall Sound intrusion gateway: lon ~ -95.5, lat > 74.6
    # Wellington Channel intrusion gateway: lon ~ -93.2, lat > 74.6
    # Resolute Bay: lon ~ -94.9, lat ~ 74.70

    if stage_id == "aug_open_water":
        # August: Open water dominates
        noise_hh = _generate_spatial_noise(shape, seed=101, scale=0.8)
        noise_hv = _generate_spatial_noise(shape, seed=102, scale=0.6)

        # Baseline open water backscatter (wind-roughened specular surface)
        hh_db = -22.5 + noise_hh
        hv_db = -31.5 + noise_hv

        # Minor isolated decaying floes in the western entrance
        dist_west = np.hypot((lon_grid - (-97.5)) / 0.8, (lat_grid - 74.5) / 0.2)
        floe_mask = (dist_west < 1.0) & (noise_hh > 0.6)
        hh_db[floe_mask] = -16.0 + 0.5 * noise_hh[floe_mask]
        hv_db[floe_mask] = -24.5 + 0.4 * noise_hv[floe_mask]

        # Classification
        hazard = np.ones(shape, dtype=np.uint8)  # Default: 1 (Open Water)
        hazard[floe_mask] = 2  # FYI / decaying floes

    elif stage_id == "sep_myi_intrusion":
        # September: Polar pack tongue pushes south across Barrow Strait
        noise_hh = _generate_spatial_noise(shape, seed=201, scale=0.9)
        noise_hv = _generate_spatial_noise(shape, seed=202, scale=0.7)

        # Start with calm / cooling open water
        hh_db = -23.0 + noise_hh
        hv_db = -32.0 + noise_hv

        # Massive multi-year ice intrusion tongue funneled from McDougall Sound (-95.5°W)
        # and Wellington Channel (-93.5°W) choking lat 74.40 to 74.75°N
        dist_mcdougall = np.hypot((lon_grid - (-95.0)) / 1.8, (lat_grid - 74.58) / 0.17)
        dist_wellington = np.hypot((lon_grid - (-93.5)) / 1.3, (lat_grid - 74.60) / 0.15)
        
        myi_plume = np.exp(-(dist_mcdougall**1.6)) * 1.0 + np.exp(-(dist_wellington**1.6)) * 0.70
        myi_plume = np.clip(myi_plume, 0.0, 1.0)

        # Deformed floe structure with internal roughness
        myi_core_mask = (myi_plume > 0.35) & (noise_hh > -0.4)
        fyi_fringe_mask = (myi_plume > 0.15) & ~myi_core_mask

        # Apply high MYI backscatter (volume scattering in 24 cm L-band + ridge roughness)
        hh_db[myi_core_mask] = -11.0 + 1.2 * noise_hh[myi_core_mask]
        hv_db[myi_core_mask] = -16.2 + 1.0 * noise_hv[myi_core_mask]

        # Apply FYI fringe backscatter
        hh_db[fyi_fringe_mask] = -17.5 + 0.8 * noise_hh[fyi_fringe_mask]
        hv_db[fyi_fringe_mask] = -24.8 + 0.6 * noise_hv[fyi_fringe_mask]

        # Classification
        hazard = np.ones(shape, dtype=np.uint8)  # 1: Open Water
        hazard[fyi_fringe_mask] = 2             # 2: First-Year Ice
        hazard[myi_core_mask] = 3               # 3: Multi-Year / Ridged Ice

    elif stage_id == "oct_freeze_up":
        # October: Consolidated freeze-up in polar darkness
        noise_hh = _generate_spatial_noise(shape, seed=301, scale=0.8)
        noise_hv = _generate_spatial_noise(shape, seed=302, scale=0.7)

        # Entire strait is covered in First-Year Ice sheet
        hh_db = -17.2 + 0.9 * noise_hh
        hv_db = -24.5 + 0.8 * noise_hv

        # Embedded frozen multi-year floes (remnants of September intrusion cemented into pack)
        dist_floes = np.hypot((lon_grid - (-95.0)) / 2.2, (lat_grid - 74.55) / 0.22)
        embedded_myi_mask = (dist_floes < 1.1) & (noise_hh > 0.1)

        hh_db[embedded_myi_mask] = -10.5 + 1.0 * noise_hh[embedded_myi_mask]
        hv_db[embedded_myi_mask] = -15.8 + 0.9 * noise_hv[embedded_myi_mask]

        # Narrow dynamic leads / polynyas along southern shore (fast ice shear zone)
        lead_mask = (lat_grid > 74.14) & (lat_grid < 74.19) & (noise_hh < -0.8)
        hh_db[lead_mask] = -23.5 + 0.5 * noise_hh[lead_mask]
        hv_db[lead_mask] = -32.5 + 0.5 * noise_hv[lead_mask]

        # Classification
        hazard = np.full(shape, 2, dtype=np.uint8)  # Default: 2 (First-Year Ice)
        hazard[lead_mask] = 1                      # 1: Open Water lead
        hazard[embedded_myi_mask] = 3              # 3: Multi-Year / Ridged Ice

    else:
        raise ValueError(f"Unknown synthetic stage: {stage_id}")

    # Clip values to physically realistic radar limits (-36 dB to -5 dB)
    hh_db = np.clip(hh_db, -35.0, -5.0)
    hv_db = np.clip(hv_db, -38.0, -10.0)

    return hh_db, hv_db, hazard


def generate_dualpol_rgb(hh_db: np.ndarray, hv_db: np.ndarray) -> np.ndarray:
    """
    Constructs a dual-polarization false-color RGB image:
    - Red: HHHH (co-pol roughness, normalized [-28, -6] dB)
    - Green: HVHV (cross-pol volume scattering, normalized [-34, -12] dB)
    - Blue: Polarimetric difference (HH - HV, normalized [6, 18] dB)
    Returns uint8 array of shape (H, W, 4) RGBA.
    """
    # Normalize channels
    r = np.clip((hh_db - (-28.0)) / ((-7.0) - (-28.0)), 0.0, 1.0)
    g = np.clip((hv_db - (-34.0)) / ((-13.0) - (-34.0)), 0.0, 1.0)
    
    diff = hh_db - hv_db
    b = np.clip((diff - 6.0) / (18.0 - 6.0), 0.0, 1.0)

    # Scale to 0-255 uint8
    r_u8 = (r * 255).astype(np.uint8)
    g_u8 = (g * 255).astype(np.uint8)
    b_u8 = (b * 255).astype(np.uint8)
    alpha = np.full_like(r_u8, 220, dtype=np.uint8)  # Semi-transparent for mapping

    return np.dstack([r_u8, g_u8, b_u8, alpha])


def generate_hazard_rgba(hazard: np.ndarray) -> np.ndarray:
    """
    Constructs an RGBA representation of the 3-Tier Ice Hazard classification:
    - 1 (Open Water): Deep Marine Blue (#1565C0)
    - 2 (First-Year Ice): Glacial Cyan (#00BCD4)
    - 3 (Multi-Year / Ridged Ice): High-Risk Crimson (#D50000)
    Returns uint8 array of shape (H, W, 4) RGBA.
    """
    h, w = hazard.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)

    # Class 1: Open Water (Subtle translucent navy tint)
    mask1 = (hazard == 1)
    rgba[mask1] = [15, 76, 129, 95]

    # Class 2: First-Year Ice (#00BCD4, 80% opacity)
    mask2 = (hazard == 2)
    rgba[mask2] = [0, 188, 212, 205]

    # Class 3: Multi-Year / Ridged Ice (#D50000, 90% opacity)
    mask3 = (hazard == 3)
    rgba[mask3] = [213, 0, 0, 230]

    return rgba


def array_to_base64_png(rgba_array: np.ndarray) -> str:
    """Encodes a uint8 RGBA array as a base64 PNG data URL for direct web rendering."""
    img = Image.fromarray(rgba_array, mode="RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def get_stage_dataset(stage_id: str):
    """
    Comprehensive loader for a single synthetic shipping stage.
    Returns complete dictionary including arrays, base64 images, transform, and stats.
    """
    meta = STAGE_METADATA.get(stage_id, STAGE_METADATA["aug_open_water"])
    hh_db, hv_db, hazard = build_calibrated_stage_arrays(stage_id)

    rgb_rgba = generate_dualpol_rgb(hh_db, hv_db)
    hazard_rgba = generate_hazard_rgba(hazard)

    rgb_data_url = array_to_base64_png(rgb_rgba)
    hazard_data_url = array_to_base64_png(hazard_rgba)

    # Calculate overall stage statistics
    total_px = hazard.size
    p1 = float(np.sum(hazard == 1) / total_px * 100.0)
    p2 = float(np.sum(hazard == 2) / total_px * 100.0)
    p3 = float(np.sum(hazard == 3) / total_px * 100.0)

    return {
        "stage_id": stage_id,
        "name": meta["name"],
        "date_str": meta["date_str"],
        "phase": meta["phase"],
        "summary": meta["summary"],
        "ice_condition": meta["ice_condition"],
        "typical_hh": meta["typical_hh"],
        "typical_hv": meta["typical_hv"],
        "hh_db": hh_db,
        "hv_db": hv_db,
        "hazard": hazard,
        "rgb_rgba": rgb_rgba,
        "hazard_rgba": hazard_rgba,
        "rgb_data_url": rgb_data_url,
        "hazard_data_url": hazard_data_url,
        "bounds": BOUNDS_FOLIUM,
        "transform": TRANSFORM,
        "crs": "EPSG:4326",
        "open_water_pct": p1,
        "fyi_pct": p2,
        "myi_pct": p3,
        "mean_hh_db": float(np.mean(hh_db)),
        "mean_hv_db": float(np.mean(hv_db)),
    }


def write_synthetic_stage_to_cogs(stage_id: str, output_dir: str = "data/processed"):
    """
    Exports synthetic stage arrays as real Cloud-Optimized GeoTIFFs (COGs)
    into output_dir, generating both a dual-pol backscatter COG and a *_hazard.tif raster.
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    stage = get_stage_dataset(stage_id)
    base_name = f"NISAR_L2_GCOV_BarrowStrait_{stage['date_str'].replace('-', '')}"
    cog_path = os.path.join(output_dir, f"{base_name}.tif")
    hazard_path = os.path.join(output_dir, f"{base_name}_hazard.tif")

    height, width = stage["hh_db"].shape

    # 1. Dual-Pol Backscatter Cloud-Optimized GeoTIFF (Band 1: HHHH dB, Band 2: HVHV dB)
    with rasterio.open(
        cog_path,
        "w",
        driver="COG",
        height=height,
        width=width,
        count=2,
        dtype=np.float32,
        crs="EPSG:4326",
        transform=TRANSFORM,
        nodata=-9999.0,
        compress="deflate"
    ) as dst:
        dst.write(stage["hh_db"].astype(np.float32), 1)
        dst.write(stage["hv_db"].astype(np.float32), 2)
        dst.set_band_description(1, "HHHH Backscatter (dB)")
        dst.set_band_description(2, "HVHV Backscatter (dB)")

    # 2. Hazard Classification Cloud-Optimized GeoTIFF (Band 1: uint8 1=Water, 2=FYI, 3=MYI)
    with rasterio.open(
        hazard_path,
        "w",
        driver="COG",
        height=height,
        width=width,
        count=1,
        dtype=np.uint8,
        crs="EPSG:4326",
        transform=TRANSFORM,
        nodata=0,
        compress="deflate"
    ) as dst:
        dst.write(stage["hazard"].astype(np.uint8), 1)
        dst.set_band_description(1, "Ice Hazard Tier (1: Water, 2: FYI, 3: MYI)")

    return cog_path, hazard_path
