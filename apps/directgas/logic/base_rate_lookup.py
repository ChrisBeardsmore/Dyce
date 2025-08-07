# 🔴 -----------------------------------------
# 🔴 Function: get_base_rates (UPDATED WITH START DATE LOGIC)
# 🔴 Purpose: Retrieve the lowest-priced Standing Charge and Unit Rate 
# 🔴          from the supplier flat file based on site-specific inputs.
# 🔴 Inputs:
# 🔴   - ldz (str): Region code (e.g. "NE") matched from postcode
# 🔴   - kwh (float): Annual consumption in kilowatt-hours
# 🔴   - duration (int): Contract length in months (e.g. 12, 24, 36)
# 🔴   - carbon_offset_required (bool): Whether the product requires Carbon Off pricing
# 🔴   - flat_df (pd.DataFrame): Loaded and cleaned supplier pricing flat file
# 🔴   - start_date (str or datetime, optional): Contract start date for date-range filtering
# 🔴 Returns:
# 🔴   - tuple: (Standing Charge in p/day [float], Unit Rate in p/kWh [float])
# 🔴 Notes:
# 🔴   - Returns (0.0, 0.0) if no match is found
# 🔴   - Prioritises lowest Unit Rate when multiple matches exist
# 🔴   - NEW: Filters by start date if date columns exist in flat file
# 🔴 -----------------------------------------

import pandas as pd
from datetime import datetime

def get_base_rates(ldz: str, kwh: float, duration: int, carbon_offset_required: bool, flat_df: pd.DataFrame, start_date=None) -> tuple[float, float]:
    """Match a quote row and return best Standing Charge and Unit Rate."""
    
    # Base filtering (existing logic)
    match = flat_df[
        (flat_df["LDZ"] == ldz) &
        (flat_df["Contract_Duration"] == duration) &
        (flat_df["Minimum_Annual_Consumption"] <= kwh) &
        (flat_df["Maximum_Annual_Consumption"] >= kwh) &
        (flat_df["Carbon_Offset"] == carbon_offset_required)
    ]
    
    # NEW: Add start date filtering if date columns exist and start_date provided
    if start_date is not None and not match.empty:
        # Convert start_date to datetime if it's a string
        if isinstance(start_date, str):
            try:
                start_date = datetime.strptime(start_date, "%d/%m/%Y")
            except ValueError:
                try:
                    start_date = datetime.strptime(start_date, "%Y-%m-%d")
                except ValueError:
                    # If date parsing fails, continue without date filtering
                    pass
        
        # Check if flat file has date range columns (common names)
        date_columns_to_check = [
            ('Valid_From', 'Valid_To'),
            ('Start_Date', 'End_Date'),
            ('Effective_From', 'Effective_To'),
            ('Price_Valid_From', 'Price_Valid_To'),
            ('Rate_Start_Date', 'Rate_End_Date'),
            ('Minimum_Contract_Start_Date', 'Maximum_Contract_Start_Date')
        ]
        
        for from_col, to_col in date_columns_to_check:
            if from_col in flat_df.columns and to_col in flat_df.columns:
                try:
                    # Convert date columns to datetime
                    match[from_col] = pd.to_datetime(match[from_col], errors='coerce')
                    match[to_col] = pd.to_datetime(match[to_col], errors='coerce')
                    
                    # Filter by date range
                    match = match[
                        (match[from_col] <= start_date) &
                        (match[to_col] >= start_date)
                    ]
                    break  # Use first matching date column pair
                except Exception:
                    # If date filtering fails, continue without it
                    continue
    
    if not match.empty:
        # Sort to pick the lowest Unit Rate from all valid matches
        best = match.sort_values("Unit_Rate").iloc[0]
        return round(best["Standing_Charge"], 2), round(best["Unit_Rate"], 3)
    
    # Return zeroed prices if no match found
    return 0.0, 0.0


# Alternative version for backward compatibility
def get_base_rates_legacy(ldz: str, kwh: float, duration: int, carbon_offset_required: bool, flat_df: pd.DataFrame) -> tuple[float, float]:
    """Legacy version without start date - for backward compatibility."""
    return get_base_rates(ldz, kwh, duration, carbon_offset_required, flat_df, start_date=None)
