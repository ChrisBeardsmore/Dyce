# margin_pricing_tool.py

import streamlit as st
import pandas as pd
import json
import io

st.set_page_config(page_title="Dyce Electric Pricing Tool", layout="wide")
st.title("🔌 Dyce Electric Pricing Tool – Apply Margin Template")

# --- STEP 1: Upload Files ---
st.markdown("### 📁 Upload Inputs")
col1, col2 = st.columns(2)

with col1:
    flat_file = st.file_uploader("Upload Electricity Flat File (.xlsx)", type="xlsx")
with col2:
    margin_template_file = st.file_uploader("Upload Margin Template (.json)", type="json")

if flat_file and margin_template_file:
    df = pd.read_excel(flat_file)
    template = json.load(margin_template_file)

    # Validate necessary columns
    required_cols = [
        "Contract_Duration", "Minimum_Annual_Consumption", "Standing_Charge",
        "Standard_Rate", "Day_Rate", "Night_Rate", "Evening_And_Weekend_Rate",
        "Green_Energy"
    ]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        st.error(f"Missing columns in flat file: {missing}")
        st.stop()

    # --- STEP 2: Select Parameters ---
    st.markdown("### ⚙️ Select Configuration")
    contract_duration = st.selectbox("Contract Duration (Months)", sorted(df["Contract_Duration"].unique()))
    green_option = st.selectbox("Tariff Type", ["Standard", "Green"])
    report_title = st.text_input("Output Filename (no extension)", value="electric_price_book")

    year_key = str(int(contract_duration // 12))
    if year_key not in template["years"]:
        st.error(f"No pricing configuration found for year: {year_key}")
        st.stop()

    config = template["years"][year_key]
    bands = template["bands"]

    # --- STEP 3: Apply Uplifts ---
    def apply_uplift(row):
        cons = row["Minimum_Annual_Consumption"]
        band = next((b for b in config["bands"] if b["Min"] <= cons <= b["Max"]), None)
        if not band:
            return pd.Series([None]*10, index=[
                "Sell_Standing_Charge", "Sell_Standard_Rate", "Sell_Day_Rate", "Sell_Night_Rate", "Sell_EW_Rate",
                "TAC", "Uplift_SC", "Uplift_Unit", "Split_Type", "Band_Label"])

        # Recovery Cost Split
        fixed_cost = config["fixed_cost"] * 100
        sc_pct = config.get("standing_pct", 50)
        ur_pct = config.get("unit_pct", 50)

        uplift_sc = (fixed_cost * sc_pct / 100) / 365
        uplift_unit = (fixed_cost * ur_pct / 100) / cons

        if row["Standard_Rate"] > 0:
            sr = round(row["Standard_Rate"] + uplift_unit + band.get("Standard_Rate", 0), 4)
            tac = (sr * cons + (row["Standing_Charge"] + uplift_sc + band.get("Standing_Charge", 0)) * 365) / 100
            return pd.Series([
                round(row["Standing_Charge"] + uplift_sc + band.get("Standing_Charge", 0), 4),
                sr, None, None, None, round(tac, 2),
                round(uplift_sc, 4), round(uplift_unit, 4), "Standard", f"{band['Min']:,}–{band['Max']:,}"
            ], index=[
                "Sell_Standing_Charge", "Sell_Standard_Rate", "Sell_Day_Rate", "Sell_Night_Rate", "Sell_EW_Rate",
                "TAC", "Uplift_SC", "Uplift_Unit", "Split_Type", "Band_Label"])

        # TOU split: 50/30/20
        day_split, night_split, ew_split = 0.5, 0.3, 0.2
        ur = row["Day_Rate"] + band.get("Day_Rate", 0)
        nr = row["Night_Rate"] + band.get("Night_Rate", 0)
        ew = row["Evening_And_Weekend_Rate"] + band.get("Evening_And_Weekend_Rate", 0)

        day_cost = (ur + uplift_unit) * cons * day_split
        night_cost = (nr + uplift_unit) * cons * night_split
        ew_cost = (ew + uplift_unit) * cons * ew_split
        sc_cost = (row["Standing_Charge"] + uplift_sc + band.get("Standing_Charge", 0)) * 365
        tac = (day_cost + night_cost + ew_cost + sc_cost) / 100

        return pd.Series([
            round(row["Standing_Charge"] + uplift_sc + band.get("Standing_Charge", 0), 4),
            None, round(ur + uplift_unit, 4), round(nr + uplift_unit, 4), round(ew + uplift_unit, 4), round(tac, 2),
            round(uplift_sc, 4), round(uplift_unit, 4), "TOU", f"{band['Min']:,}–{band['Max']:,}"
        ], index=[
            "Sell_Standing_Charge", "Sell_Standard_Rate", "Sell_Day_Rate", "Sell_Night_Rate", "Sell_EW_Rate",
            "TAC", "Uplift_SC", "Uplift_Unit", "Split_Type", "Band_Label"])

    df_filtered = df[(df["Contract_Duration"] == contract_duration)]
    df_filtered = df_filtered[df_filtered["Green_Energy"].astype(str).str.upper().isin(["TRUE", "YES"] if green_option == "Green" else ["FALSE", "NO"])]
    df_out = df_filtered.copy()
    uplifted = df_filtered.apply(apply_uplift, axis=1)
    df_out = pd.concat([df_out, uplifted], axis=1)

    # --- STEP 4: Download Options ---
    st.success("✅ Pricing completed. Preview below:")
    st.dataframe(df_out.head())

    broker_cols = [
        "Contract_Duration", "Minimum_Annual_Consumption", "Green_Energy", "Band_Label", "Split_Type",
        "Sell_Standing_Charge", "Sell_Standard_Rate", "Sell_Day_Rate", "Sell_Night_Rate", "Sell_EW_Rate", "TAC"
    ]

    audit_output = io.BytesIO()
    with pd.ExcelWriter(audit_output, engine="xlsxwriter") as writer:
        df_out.to_excel(writer, index=False, sheet_name="Audit")

    broker_output = io.BytesIO()
    with pd.ExcelWriter(broker_output, engine="xlsxwriter") as writer:
        df_out[broker_cols].to_excel(writer, index=False, sheet_name="Broker View")

    st.download_button("⬇️ Download Broker Price Book", data=broker_output.getvalue(), file_name=f"{report_title}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.download_button("⬇️ Download Internal Audit File", data=audit_output.getvalue(), file_name=f"{report_title}_audit.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
