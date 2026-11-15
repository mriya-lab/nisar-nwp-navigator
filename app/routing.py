"""
app/routing.py
Deterministic Maritime Tactical Risk & Route Optimization Engine for the Northwest Passage.
Utilizes rasterio and shapely to sample ice hazard rasters along NORDREG corridor vectors,
evaluating Polar Code operational statuses (NAVIGABLE, CAUTION, BLOCKED), transit delays,
and fuel-burn penalties across three distinct vessel profiles:
1. Standard Cargo (Non-ice strengthened commercial freighter)
2. Polar Class 6 (Medium polar ice-strengthened vessel / 1A Super)
3. Heavy Icebreaker (Polar Class 1 / CCGS Louis S. St-Laurent)
"""

import numpy as np
import rasterio
from rasterio.transform import rowcol
from shapely.geometry import shape, LineString, Point
from typing import Dict, Any, Union, List, Optional
import pyproj

# Vessel performance matrices and Polar Code risk thresholds
VESSEL_PROFILES: Dict[str, Dict[str, Any]] = {
    "Standard Cargo": {
        "designation": "Standard Cargo (Non-Ice Strengthened / Commercial)",
        "description": "Standard container or bulk carrier with unreinforced steel hull. Strict zero-tolerance for multi-year ice floes.",
        "nominal_speed_knots": 14.0,
        "baseline_fuel_rate_tons_hour": 1.05,  # ~25.2 metric tons/day at service speed
        "speed_multipliers": {
            1: 1.0,    # Open Water: 14.0 kn
            2: 0.30,   # First-Year Ice: Crawl at 4.2 kn in young slush
            3: 0.05    # Multi-Year Ice: Impassable (1 kn drift / stopped)
        },
        "fuel_multipliers": {
            1: 1.0,    # Baseline fuel rate
            2: 1.65,   # Increased drag & maneuvering in FYI
            3: 3.20    # Extreme engine load / halting burn
        },
        "thresholds": {
            "myi_block": 0.5,    # > 0.5% Multi-Year Ice causes catastrophic hull penetration risk -> BLOCKED
            "myi_caution": 0.1,  # > 0.1% -> CAUTION
            "fyi_block": 12.0,   # > 12% First-Year Ice -> BLOCKED without icebreaker escort
            "fyi_caution": 2.5   # > 2.5% -> CAUTION
        }
    },
    "Polar Class 6": {
        "designation": "Polar Class 6 (Medium Ice-Strengthened / 1A Super)",
        "description": "Medium polar vessel designed for summer/autumn operations in medium first-year ice with old ice inclusions.",
        "nominal_speed_knots": 12.0,
        "baseline_fuel_rate_tons_hour": 1.45,  # ~34.8 metric tons/day
        "speed_multipliers": {
            1: 1.0,    # Open Water: 12.0 kn
            2: 0.70,   # First-Year Ice: 8.4 kn steady transit
            3: 0.28    # Multi-Year Ice: 3.4 kn tactical ice management
        },
        "fuel_multipliers": {
            1: 1.0,    # Baseline fuel rate
            2: 1.40,   # Resistance in first-year ice
            3: 2.30    # High torque / variable pitch propeller thrust
        },
        "thresholds": {
            "myi_block": 15.0,   # > 15% Multi-Year Ice exceeds unescorted PC6 capability -> BLOCKED
            "myi_caution": 2.0,  # > 2.0% -> CAUTION
            "fyi_block": 55.0,   # > 55% First-Year Ice -> BLOCKED unescorted
            "fyi_caution": 18.0  # > 18% -> CAUTION
        }
    },
    "Heavy Icebreaker": {
        "designation": "Heavy Icebreaker (Polar Class 1 / Escort Icebreaker)",
        "description": "Heavy polar icebreaker capable of year-round polar operations in multi-year ice ridges (24,000+ Shaft HP).",
        "nominal_speed_knots": 12.0,
        "baseline_fuel_rate_tons_hour": 2.50,  # ~60.0 metric tons/day
        "speed_multipliers": {
            1: 1.0,    # Open Water: 12.0 kn
            2: 0.85,   # First-Year Ice: 10.2 kn continuous breaking
            3: 0.45    # Multi-Year Ice: 5.4 kn continuous ramming mode
        },
        "fuel_multipliers": {
            1: 1.0,    # Baseline fuel rate
            2: 1.35,   # First-year ice resistance
            3: 2.60    # Maximum power back-and-ram cycles in ridged ice
        },
        "thresholds": {
            "myi_block": 75.0,   # > 75% heavy consolidated polar pack -> BLOCKED
            "myi_caution": 25.0,  # > 25% Multi-Year Ice requires continuous ramming -> CAUTION
            "fyi_block": 95.0,   # > 95% -> BLOCKED
            "fyi_caution": 55.0  # > 55% -> CAUTION
        }
    }
}


def calculate_line_length_nm(line_geom: LineString) -> float:
    """Computes exact WGS84 ellipsoidal distance in Nautical Miles along a LineString."""
    geod = pyproj.Geod(ellps="WGS84")
    length_meters = geod.geometry_length(line_geom)
    return float(length_meters / 1852.0)


def sample_route_hazard(
    route_geom: Union[LineString, Dict, Any],
    hazard_source: Union[str, np.ndarray],
    transform: Optional[rasterio.Affine] = None,
    num_samples: int = 350
) -> Dict[str, Any]:
    """
    Samples ice hazard values along a maritime route geometry using rasterio and shapely.
    
    Args:
        route_geom: Shapely LineString, GeoJSON dict, or geometry object.
        hazard_source: Filepath string to *_hazard.tif OR a 2D numpy array of hazard classes (1, 2, 3).
        transform: Affine transform (required if hazard_source is a numpy array).
        num_samples: Number of equidistant sampling locations along the line.
        
    Returns:
        Dictionary containing exact percentage breakdowns and sampled statistics.
    """
    # Normalize to shapely LineString
    if isinstance(route_geom, dict):
        line = shape(route_geom)
    elif hasattr(route_geom, "geom_type"):
        line = route_geom
    else:
        raise ValueError("route_geom must be a Shapely geometry or GeoJSON dictionary")

    # Interpolate equidistant points along corridor
    t_vals = np.linspace(0.0, 1.0, num_samples)
    pts = [line.interpolate(t, normalized=True) for t in t_vals]
    xs = np.array([p.x for p in pts], dtype=np.float64)
    ys = np.array([p.y for p in pts], dtype=np.float64)

    # Sample raster values
    if isinstance(hazard_source, str):
        # Read from GeoTIFF file on disk
        with rasterio.open(hazard_source) as src:
            sample_coords = [(x, y) for x, y in zip(xs, ys)]
            sampled_vals = [val[0] for val in src.sample(sample_coords)]
            sampled = np.array(sampled_vals, dtype=np.uint8)
    elif isinstance(hazard_source, np.ndarray):
        # Sample from in-memory numpy array using rasterio affine transform
        if transform is None:
            raise ValueError("Affine transform must be provided when hazard_source is a numpy array")
        rows, cols = rowcol(transform, xs, ys)
        rows = np.clip(rows, 0, hazard_source.shape[0] - 1)
        cols = np.clip(cols, 0, hazard_source.shape[1] - 1)
        sampled = hazard_source[rows, cols].astype(np.uint8)
    else:
        raise TypeError("hazard_source must be a file path string or 2D numpy array")

    total_valid = len(sampled)
    if total_valid == 0:
        return {
            "open_water_pct": 100.0,
            "fyi_pct": 0.0,
            "myi_pct": 0.0,
            "mean_hazard_tier": 1.0,
            "total_samples": 0
        }

    c1 = int(np.sum(sampled == 1))
    c2 = int(np.sum(sampled == 2))
    c3 = int(np.sum(sampled == 3))

    p1 = float((c1 / total_valid) * 100.0)
    p2 = float((c2 / total_valid) * 100.0)
    p3 = float((c3 / total_valid) * 100.0)

    return {
        "open_water_pct": round(p1, 2),
        "fyi_pct": round(p2, 2),
        "myi_pct": round(p3, 2),
        "open_water_count": c1,
        "fyi_count": c2,
        "myi_count": c3,
        "total_samples": total_valid,
        "mean_hazard_tier": round(float(np.mean(sampled)), 2),
        "sampled_hazard": sampled,
        "sample_points": list(zip(xs, ys))
    }


def compute_vessel_telemetry(
    distance_nm: float,
    open_water_pct: float,
    fyi_pct: float,
    myi_pct: float,
    vessel_class: str = "Polar Class 6"
) -> Dict[str, Any]:
    """
    Computes operational status, transit delay, and fuel penalty for a given vessel class.
    
    Args:
        distance_nm: Total corridor transit distance in nautical miles.
        open_water_pct: Percentage of Open Water (Class 1) along route.
        fyi_pct: Percentage of First-Year Ice (Class 2) along route.
        myi_pct: Percentage of Multi-Year / Ridged Ice (Class 3) along route.
        vessel_class: Name of vessel profile.
        
    Returns:
        Structured dictionary of operational telemetry metrics.
    """
    profile = VESSEL_PROFILES.get(vessel_class, VESSEL_PROFILES["Polar Class 6"])
    limits = profile["thresholds"]
    speed_mult = profile["speed_multipliers"]
    fuel_mult = profile["fuel_multipliers"]
    v0 = profile["nominal_speed_knots"]
    fuel_rate = profile["baseline_fuel_rate_tons_hour"]

    # 1. Determine Operational Status (NAVIGABLE, CAUTION, BLOCKED)
    if (myi_pct > limits["myi_block"]) or (fyi_pct > limits["fyi_block"]):
        status = "BLOCKED"
        status_color = "#D50000"  # Red
        if myi_pct > limits["myi_block"]:
            reason = f"Multi-Year Ice concentration ({myi_pct:.1f}%) exceeds hull structural limit ({limits['myi_block']}%) — Catastrophic puncture risk."
        else:
            reason = f"First-Year Ice concentration ({fyi_pct:.1f}%) exceeds unescorted rating ({limits['fyi_block']}%)."
    elif (myi_pct > limits["myi_caution"]) or (fyi_pct > limits["fyi_caution"]):
        status = "CAUTION"
        status_color = "#FFB300"  # Amber
        reason = f"Moderate ice concentration ({myi_pct:.1f}% MYI, {fyi_pct:.1f}% FYI). Transit permitted with tactical floe avoidance & reduced speed."
    else:
        status = "NAVIGABLE"
        status_color = "#00E676"  # Emerald Green
        reason = f"Corridor open ({open_water_pct:.1f}% open water). Negligible ice risk within nominal vessel operating parameters."

    # 2. Compute Baseline Transit Metrics (Calm Open Water)
    t0_hours = distance_nm / v0
    f0_tons = t0_hours * fuel_rate

    # 3. Compute Segmented Transit Time & Fuel Burn
    fractions = {
        1: open_water_pct / 100.0,
        2: fyi_pct / 100.0,
        3: myi_pct / 100.0
    }

    total_actual_hours = 0.0
    total_projected_fuel = 0.0

    for tier in [1, 2, 3]:
        frac = fractions[tier]
        if frac > 0.0:
            tier_dist = distance_nm * frac
            tier_speed = max(0.5, v0 * speed_mult[tier])
            tier_time = tier_dist / tier_speed
            tier_fuel = tier_time * (fuel_rate * fuel_mult[tier])

            total_actual_hours += tier_time
            total_projected_fuel += tier_fuel

    transit_delay_hours = max(0.0, total_actual_hours - t0_hours)
    excess_fuel_tons = max(0.0, total_projected_fuel - f0_tons)
    fuel_penalty_pct = (excess_fuel_tons / f0_tons * 100.0) if f0_tons > 0 else 0.0
    effective_speed = distance_nm / total_actual_hours if total_actual_hours > 0 else v0

    # Composite Risk Index (0-100)
    # Weighs MYI heavily (factor of 1.0) and FYI moderately (factor of 0.3)
    raw_risk = (myi_pct * 1.0) + (fyi_pct * 0.3)
    if vessel_class == "Standard Cargo":
        risk_score = min(100.0, raw_risk * 2.2)
    elif vessel_class == "Polar Class 6":
        risk_score = min(100.0, raw_risk * 1.1)
    else:
        risk_score = min(100.0, raw_risk * 0.5)

    return {
        "vessel_class": vessel_class,
        "designation": profile["designation"],
        "status": status,
        "status_color": status_color,
        "status_reason": reason,
        "distance_nm": round(distance_nm, 1),
        "nominal_speed_knots": v0,
        "effective_speed_knots": round(effective_speed, 1),
        "baseline_transit_hours": round(t0_hours, 1),
        "actual_transit_hours": round(total_actual_hours, 1),
        "transit_delay_hours": round(transit_delay_hours, 1),
        "baseline_fuel_tons": round(f0_tons, 2),
        "total_fuel_tons": round(total_projected_fuel, 2),
        "excess_fuel_penalty_tons": round(excess_fuel_tons, 2),
        "fuel_penalty_pct": round(fuel_penalty_pct, 1),
        "risk_index": round(risk_score, 1)
    }


def evaluate_corridor(
    route_geom: Union[LineString, Dict, Any],
    hazard_source: Union[str, np.ndarray],
    transform: Optional[rasterio.Affine] = None,
    vessel_class: Optional[str] = "Polar Class 6",
    nominal_length_nm: Optional[float] = None
) -> Dict[str, Any]:
    """
    High-level orchestrator evaluating corridor risk, breakdown, and vessel profiles.
    If vessel_class is None, evaluates all three standard profiles.
    """
    # Ensure route geometry is a LineString
    if isinstance(route_geom, dict):
        line = shape(route_geom)
    else:
        line = route_geom

    # Distance calculation
    if nominal_length_nm is not None and nominal_length_nm > 0:
        dist_nm = float(nominal_length_nm)
    else:
        dist_nm = calculate_line_length_nm(line)

    # Sample ice hazard breakdown
    breakdown = sample_route_hazard(line, hazard_source, transform=transform)

    p1 = breakdown["open_water_pct"]
    p2 = breakdown["fyi_pct"]
    p3 = breakdown["myi_pct"]

    # Evaluate vessel telemetry
    if vessel_class is not None and vessel_class in VESSEL_PROFILES:
        telemetry = compute_vessel_telemetry(dist_nm, p1, p2, p3, vessel_class)
        all_profiles = {
            vname: compute_vessel_telemetry(dist_nm, p1, p2, p3, vname)
            for vname in VESSEL_PROFILES
        }
    else:
        all_profiles = {
            vname: compute_vessel_telemetry(dist_nm, p1, p2, p3, vname)
            for vname in VESSEL_PROFILES
        }
        telemetry = all_profiles["Polar Class 6"]

    return {
        "distance_nm": dist_nm,
        "breakdown": breakdown,
        "telemetry": telemetry,
        "all_vessel_profiles": all_profiles
    }


# Retain legacy functions for backwards compatibility with any existing scripts
def calculate_corridor_risk(mean_db: float, ice_class_str: str) -> float:
    """Legacy helper maintained for compatibility."""
    multiplier = 2.5 if "Open Water" in ice_class_str else 1.0
    normalized = np.clip((mean_db + 30) / 25, 0.1, 1.0) * 100
    return float(np.clip(normalized * multiplier, 0.0, 100.0))


def compute_fuel_penalty(distance_nm: float, mean_db: float, ice_class_str: str) -> Dict[str, Any]:
    """Legacy helper maintained for compatibility."""
    risk_score = calculate_corridor_risk(mean_db, ice_class_str)
    baseline_burn_per_nm = 0.15
    penalty_factor = 1.0 + (risk_score / 100.0) ** 2
    total_burn = distance_nm * baseline_burn_per_nm * penalty_factor
    excess_fuel = total_burn - (distance_nm * baseline_burn_per_nm)
    return {
        "baseline_burn_tons": float(distance_nm * baseline_burn_per_nm),
        "total_projected_burn_tons": float(total_burn),
        "excess_fuel_penalty_tons": float(excess_fuel),
        "risk_index": risk_score
    }


if __name__ == "__main__":
    print("Testing routing module with synthetic test data...")
    from app.synthetic import get_stage_dataset
    import json

    with open("data/gis/nordreg_barrow_strait.geojson") as f:
        routes_geojson = json.load(f)

    for stage_id in ["aug_open_water", "sep_myi_intrusion"]:
        stage = get_stage_dataset(stage_id)
        print(f"\n--- Evaluation for {stage['name']} ---")
        for feature in routes_geojson["features"]:
            res = evaluate_corridor(
                feature["geometry"],
                stage["hazard"],
                transform=stage["transform"],
                vessel_class="Polar Class 6",
                nominal_length_nm=feature["properties"].get("nominal_length_nm")
            )
            t = res["telemetry"]
            b = res["breakdown"]
            print(f"Route: {feature['properties']['name'][:30]:30} | {t['status']:9} | Water: {b['open_water_pct']:5.1f}% | FYI: {b['fyi_pct']:5.1f}% | MYI: {b['myi_pct']:5.1f}% | Delay: +{t['transit_delay_hours']:4.1f}h | Excess Fuel: +{t['excess_fuel_penalty_tons']:4.1f}t (+{t['fuel_penalty_pct']}%)")
