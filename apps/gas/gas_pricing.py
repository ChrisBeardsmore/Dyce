import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Gas Pricing Uplift Tool", layout="wide")
st.title("🔹 Gas Pricing Uplift Tool")

uploaded_file = st.file_uploader("Upload your pricing XLSX file:", type="xlsx")

if uploaded_file:
    # Read Excel
    df = pd.read_excel(uploaded_file)
    # Remove the Credit Score columns if they exist
    df = df.drop(columns=[col for col in ["Minimum_Credit_Score", "Maximum_Credit_Score"] if col in df.columns])
    # Show preview
    st.subheader("📄 Flat File Preview")
    st.dataframe(df.head())

    st.markdown("---")
    st.subheader("Step 1 – Enter Uplifts (pence per kWh and pence per day)")

    # Consumption Bands
    default_bands = [
        {"Min": 1000, "Max": 24999},
        {"Min": 25000, "Max": 49999},
        {"Min": 50000, "Max": 73199},
        {"Min": 73200, "Max": 124999},
        {"Min": 125000, "Max": 292999},
        {"Min": 293000, "Max": 449999},
        {"Min": 450000, "Max": 731999},
    ]

    band_inputs = []

    with st.expander("Click to configure uplifts", expanded=True):
        for i, band in enumerate(default_bands):
            st.markdown(f"**Band {i+1}: {band['Min']} – {band['Max']} kWh**")
            cols = st.columns([2, 1, 1, 1, 1])
            contract = cols[0].selectbox(
                f"Contract Duration (Years) for Band {i+1}",
                [1, 2, 3],
                key=f"contract_{i}"
            )
            # Standard Uplifts
            uplift_unit_std = cols[1].number_input(
                "Standard Unit Rate Uplift (p/kWh)", 
                min_value=0.0, 
                step=0.001, 
                format="%.3f",
                key=f"std_unit_{i}"
            )
            uplift_stand_std = cols[2].number_input(
                "Standard Standing Charge Uplift (p/day)", 
                min_value=0.0, 
                step=0.1,
                format="%.4f",
                key=f"std_stand_{i}"
            )
            # Carbon Neutral Uplifts
            uplift_unit_carbon = cols[3].number_input(
                "Carbon Neutral Unit Rate Uplift (p/kWh)", 
                min_value=0.0, 
                step=0.001, 
                format="%.3f",
                key=f"carbon_unit_{i}"
            )
            uplift_stand_carbon = cols[4].number_input(
                "Carbon Neutral Standing Charge Uplift (p/day)", 
                min_value=0.0, 
                step=0.1,
                format="%.4f",
                key=f"carbon_stand_{i}"
            )

            band_inputs.append({
                "Min": band["Min"],
                "Max": band["Max"],
                "Contract": contract,
                "Standard_Unit": uplift_unit_std,
                "Standard_Standing": uplift_stand_std,
                "Carbon_Unit": uplift_unit_carbon,
                "Carbon_Standing": uplift_stand_carbon,
            })

    st.markdown("---")

    # Annual Consumption (used for total cost)
    annual_consumption = st.number_input(
        "Annual Consumption to calculate estimated total cost (kWh):",
        min_value=1,
        value=20000
    )

    # Function to determine uplift per row
    def get_uplifts(row):
        consumption = row["Minimum_Annual_Consumption"]
        matched_band = next((b for b in band_inputs if b["Min"] <= consumption <= b["Max"]), band_inputs[-1])

        # Determine if carbon neutral
        carbon_raw = str(row.get("Carbon_Offset", "")).strip().lower()
        carbon = carbon_raw in ["yes", "y", "true", "1"]

        # Contract duration (force match to band selection)
        contract = matched_band["Contract"]

        if carbon:
            uplift_unit = matched_band["Carbon_Unit"]
            uplift_standing = matched_band["Carbon_Standing"]
        else:
            uplift_unit = matched_band["Standard_Unit"]
            uplift_standing = matched_band["Standard_Standing"]

        return pd.Series({
            "Uplift_Unit": uplift_unit,
            "Uplift_Standing": uplift_standing
        })

    # Apply
    uplift_df = df.apply(get_uplifts, axis=1)
    df_final = pd.concat([df.reset_index(drop=True), uplift_df], axis=1)

    # Compute uplifted columns
    df_final["Unit Rate"] = (df_final["Unit_Rate"] + df_final["Uplift_Unit"]).round(4)
    df_final["Standing Charge"] = (df_final["Standing_Charge"] + df_final["Uplift_Standing"]).round(4)
    df_final["Total Annual Cost (£)"] = (
        (df_final["Standing Charge"] * 365) + (df_final["Unit Rate"] * df_final["Minimum_Annual_Consumption"])
    ) / 100

    # Select only columns to display/export
    display_cols = [
        "Broker_ID",
        "Production_Date",
        "Utility",
        "LDZ",
        "Exit_Zone",
        "Sale_Type",
        "Contract_Duration",
        "Minimum_Annual_Consumption",
        "Maximum_Annual_Consumption",
        "Minimum_Contract_Start_Date",
        "Maximum_Contract_Start_Date",
        "Minimum_Valid_Quote_Date",
        "Maximum_Valid_Quote_Date",
        "Product_Name",
        "Carbon_Offset",
        "Unit Rate",
        "Standing Charge",
        "Total Annual Cost (£)"
    ]

    st.subheader("✅ Price List Preview")
    st.dataframe(df_final[display_cols].head())

    # Excel output
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_final[display_cols].to_excel(writer, index=False, sheet_name="PriceList")

    st.download_button(
        "⬇️ Download Broker Price List",
        data=output.getvalue(),
        file_name="broker_pricelist.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
