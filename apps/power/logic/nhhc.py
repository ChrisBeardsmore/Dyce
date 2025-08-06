import pandas as pd

def apply_cost_allocation(total_cost, standing_pct, mid_consumption):
    cost_pence = total_cost * 100  # £ → p
    sc = (cost_pence * standing_pct) / 365  # p/day
    ur = (cost_pence * (1 - standing_pct)) / mid_consumption  # p/kWh
    return sc, ur

def calculate_uplifted_rates(row, allocated_sc, allocated_ur, uplifts):
    return {
        "Standing Charge (p/day)": row["Standing_Charge"] + allocated_sc + uplifts["uplift_standing"],
        "Day Rate (p/kWh)": row["Day_Rate"] + allocated_ur + uplifts["uplift_day"],
        "Night Rate (p/kWh)": row["Night_Rate"] + allocated_ur + uplifts["uplift_night"],
        "Evening & Weekend Rate (p/kWh)": row["Evening_And_Weekend_Rate"] + allocated_ur + uplifts["uplift_evw"]
    }

def calculate_tac(rates, consumption, profile_split):
    weighted_unit_cost = (
        rates["Day Rate (p/kWh)"] * (profile_split["day"] / 100) +
        rates["Night Rate (p/kWh)"] * (profile_split["night"] / 100) +
        rates["Evening & Weekend Rate (p/kWh)"] * (profile_split["evw"] / 100)
    )
    energy_cost = consumption * weighted_unit_cost / 100  # p → £
    standing_cost = 365 * rates["Standing Charge (p/day)"] / 100
    return round(energy_cost + standing_cost, 2)

def generate_price_book(df, bands, uplifts, total_cost, standing_pct, contract_duration, green_option, profile_split):
    output = []
    for idx, band in enumerate(uplifts):
        filtered = df[
            (df["Minimum_Annual_Consumption"] <= band["max"]) &
            (df["Maximum_Annual_Consumption"] >= band["min"]) &
            (df["Contract_Duration"] == contract_duration) &
            ((df["Green_Energy"].str.upper() == "YES") if green_option == "Green" else (df["Green_Energy"].str.upper() == "NO"))
        ]

        if filtered.empty:
            output.append({
                "Band": f"{band['min']:,} – {band['max']:,}",
                "Standing Charge (p/day)": "N/A",
                "Day Rate (p/kWh)": "N/A",
                "Night Rate (p/kWh)": "N/A",
                "Evening & Weekend Rate (p/kWh)": "N/A",
                "Total Annual Cost (£)": "N/A"
            })
            continue

        row = filtered.iloc[0]
        mid_consumption = (band["min"] + band["max"]) / 2
        allocated_sc, allocated_ur = apply_cost_allocation(total_cost, standing_pct, mid_consumption)

        rates = calculate_uplifted_rates(row, allocated_sc, allocated_ur, band)
        tac = calculate_tac(rates, mid_consumption, profile_split)

        output.append({
            "Band": f"{band['min']:,} – {band['max']:,}",
            **{k: round(v, 4) for k, v in rates.items()},
            "Total Annual Cost (£)": tac
        })
    return pd.DataFrame(output)
