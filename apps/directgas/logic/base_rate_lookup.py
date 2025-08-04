def get_base_rates(ldz, kwh, duration, carbon_offset_required, flat_df):
    match = flat_df[
        (flat_df["LDZ"] == ldz) &
        (flat_df["Contract_Duration"] == duration) &
        (flat_df["Minimum_Annual_Consumption"] <= kwh) &
        (flat_df["Maximum_Annual_Consumption"] >= kwh) &
        (flat_df["Carbon_Offset"] == carbon_offset_required)
    ]

    if not match.empty:
        best = match.sort_values("Unit_Rate").iloc[0]
        return round(best["Standing_Charge"], 2), round(best["Unit_Rate"], 3)
    else:
        return 0.0, 0.0
