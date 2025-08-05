import pandas as pd

# 🔴 -----------------------------------------
# 🔴 Function: create_input_dataframe
# 🔴 Purpose: Generate a blank input DataFrame for multi-site gas quoting.
# 🔴 Inputs:
# 🔴   - num_rows (int): Number of empty rows to initialize (default = 10)
# 🔴 Returns:
# 🔴   - df (pd.DataFrame): Editable DataFrame prefilled with column headers and placeholders
# 🔴   - all_cols (list): Ordered list of all column names (used for consistency)
# 🔴 Notes:
# 🔴   - Includes base pricing, uplift inputs, and TAC/margin for sales person view
# 🔴   - Covers contract durations: 12, 24, and 36 months
# 🔴 -----------------------------------------
def create_input_dataframe(num_rows: int = 10) -> tuple[pd.DataFrame, list]:
    """Create a blank input sheet with site details and pricing placeholders."""

    # Core user-input columns
    base_cols = ["Site Name", "Post Code", "Annual KWH"]
    durations = [12, 24, 36]

    # Build column list for all durations - SALES PERSON VIEW
    all_cols = base_cols.copy()
    for d in durations:
        all_cols += [
            f"Base Standing Charge ({d}m)",
            f"Base Unit Rate ({d}m)",
            f"Standing Charge Uplift ({d}m)",
            f"Uplift Unit Rate ({d}m)",
            f"Final Standing Charge ({d}m)",  # NEW: base + uplift
            f"Final Unit Rate ({d}m)",        # NEW: base + uplift
            f"TAC £({d}m)",                   # NEW: visible to sales person
            f"Margin £({d}m)"                 # NEW: visible to sales person
        ]

    # Initialize DataFrame with default values:
    # - Blank for text fields
    # - 0 for numeric fields
    df = pd.DataFrame([
        {col: "" if col in ["Site Name", "Post Code"] else 0 for col in all_cols}
        for _ in range(num_rows)
    ])

    return df, all_cols
