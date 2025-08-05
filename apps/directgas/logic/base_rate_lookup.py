# 🔴 -----------------------------------------
# 🔴 Function: get_base_rates
# 🔴 Purpose: Retrieve the lowest-priced Standing Charge and Unit Rate 
# 🔴          from the supplier flat file based on site-specific inputs.
# 🔴 Inputs:
# 🔴   - ldz (str): Region code (e.g. "NE") matched from postcode
# 🔴   - kwh (float): Annual consumption in kilowatt-hours
# 🔴   - duration (int): Contract length in months (e.g. 12, 24, 36)
# 🔴   - carbon_offset_required (bool): Whether the product requires Carbon Off pricing
# 🔴   - flat_df (pd.DataFrame): Loaded and cleaned supplier pricing flat file
# 🔴 Returns:
# 🔴   - tuple: (Standing Charge in p/day [float], Unit Rate in p/kWh [float])
# 🔴 Notes:
# 🔴   - Returns (0.0, 0.0) if no match is found
# 🔴   - Prioritises lowest Unit Rate when multiple matches exist
# 🔴 -----------------------------------------
import pandas as pd
def get_base_rates(ldz: str, kwh: float, duration: int, carbon_offset_required: bool, flat_df: pd.DataFrame) -> tuple[float, float]:
    """Match a quote row and return best Standing Charge and Unit Rate."""
    # Filter flat file for rows matching LDZ, duration, carbon setting, and usage band
    match = flat_df[
        (flat_df["LDZ"] == ldz) &
        (flat_df["Contract_Duration"] == duration) &
        (flat_df["Minimum_Annual_Consumption"] <= kwh) &
        (flat_df["Maximum_Annual_Consumption"] >= kwh) &
        (flat_df["Carbon_Offset"] == carbon_offset_required)
    ]
    if not match.empty:
        # Sort to pick the lowest Unit Rate from all valid matches
        best = match.sort_values("Unit_Rate").iloc[0]
        return round(best["Standing_Charge"], 2), round(best["Unit_Rate"], 3)
    
    # Return zeroed prices if no match found
    return 0.0, 0.0
