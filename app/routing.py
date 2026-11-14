import numpy as np

# Map out structural numeric multipliers for vessel ice certifications
ICE_CLASS_MULTIPLIERS = {
    "Open Water (None)": 2.5,
    "Type B": 1.8,
    "Type A": 1.4,
    "CAC 4": 1.1,
    "CAC 3": 0.9,
    "Polar Class 6": 0.7,
    "Polar Class 1": 0.2
}

def calculate_corridor_risk(mean_db, ice_class_str):
    """
    Evaluates shipping risk based on radar roughness (mean dB backscatter)
    and the vessel's ice-class limit.
    Rougher, high-backscatter surfaces typically indicate deformed multi-year ice.
    """
    multiplier = ICE_CLASS_MULTIPLIERS.get(ice_class_str, 2.5)
    
    # Scale raw dB backscatter into a positive risk index proxy
    # e.g., mapping rough ice values (-10dB to -25dB range) into 1-100 base score
    normalized_ice_roughness = np.clip((mean_db + 30) / 25, 0.1, 1.0) * 100
    
    final_risk_score = normalized_ice_roughness * multiplier
    return float(np.clip(final_risk_score, 0.0, 100.0))

def compute_fuel_penalty(distance_nm, mean_db, ice_class_str):
    """
    Computes expected vessel fuel burn penalty (metric tons of fuel oil)
    due to ice drag and circuitous tactical routing.
    """
    risk_score = calculate_corridor_risk(mean_db, ice_class_str)
    
    # Baseline fuel consumption assumption per nautical mile (NM) under normal conditions
    baseline_burn_per_nm = 0.15 
    
    # Fuel penalty multiplier grows exponentially with ice roughness risk thresholds
    penalty_factor = 1.0 + (risk_score / 100.0) ** 2
    
    total_projected_burn = distance_nm * baseline_burn_per_nm * penalty_factor
    excess_fuel_penalty = total_projected_burn - (distance_nm * baseline_burn_per_nm)
    
    return {
        "baseline_burn_tons": float(distance_nm * baseline_burn_per_nm),
        "total_projected_burn_tons": float(total_projected_burn),
        "excess_fuel_penalty_tons": float(excess_fuel_penalty),
        "risk_index": risk_score
    }

if __name__ == "__main__":
    print("Testing routing calculation matrix with sample -15.5 dB backscatter array...")
    sample_metrics = compute_fuel_penalty(distance_nm=250, mean_db=-15.5, ice_class_str="Polar Class 6")
    print(f"Calculated Metrics: {sample_metrics}")
