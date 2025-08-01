# Bespoke Tool – V8.py
# Builds on V7 with Contract Length derivation, full TAC calculation, and correct pivoted table structure

import streamlit as st
import pandas as pd
from io import BytesIO

# --- Streamlit Setup ---
st.set_page_config(layout="wide")
st.title("🔌 Bespoke Power Pricing Tool – V8 (TAC + Duration Logic)")

# --- Upload Supplier Quote File ---
file = st.file_uploader("Upload Supplier Tender File (Excel)", type=["xlsx"])

if file:
    sheet = st.selectbox("Select Sheet", options=["Standard", "Green"])
    df_raw = pd.read_excel(file, sheet_name=sheet)

    # --- Derive Contract Length ---
    df_raw["CSD"] = pd.to_datetime(df_raw["CSD"], dayfirst=True, errors="coerce")
    df_raw["CED"] = pd.to_datetime(df_raw["CED"], dayfirst=True, errors="coerce")
    df_raw["Contract Length"] = ((df_raw["CED"] - df_raw["CSD"]) / pd.Timedelta(days=365)).round().astype(int)

    # --- Detect HH ---
    def is_hh(row):
        return pd.notna(row.get("All Year - Day Rate (p/kWh)")) and \
               pd.notna(row.get("All Year - Night Rate (p/kWh)")) and \
               pd.notna(row.get("DUoS (p/KVA/Day)")) and \
               pd.notna(row.get("Standing Charge (p/day)"))

    df_raw["Is_HH"] = df_raw.apply(is_hh, axis=1)

    # --- Split HH and NHH ---
    df_nhh = df_raw[df_raw["Is_HH"] == False].copy()
    df_hh = df_raw[df_raw["Is_HH"] == True].copy()

    st.success(f"Loaded {len(df_nhh)} NHH rows and {len(df_hh)} HH rows.")

    # --- Function to Build Uplift Table with TAC ---
    def build_uplift_editor(df, meter_type):
        terms = [12, 24, 36]
        df['EAC'] = df['EAC'].fillna(0)
        df['Contract Length'] = df['Contract Length'].astype(str)

        # Get one row per MPXN with EAC only once
        base_df = df.drop_duplicates(subset=["MPXN"])[["MPXN", "EAC"]].copy()

        for term in terms:
            term_str = f"{term}"
            sub_df = df[df['Contract Length'] == term_str].drop_duplicates(subset=["MPXN"])

            if meter_type == "NHH":
                for col in [
                    "Standing Charge (p/day)",
                    "Day Rate (p/kWh)",
                    "Night Rate (p/kWh)",
                    "E/W Rate (p/kWh)"
                ]:
                    mapping = sub_df.set_index("MPXN")[col]
                    base_df[f"{col} {term}m"] = base_df["MPXN"].map(mapping)
                for col in ["SC", "Day", "Night", "E/W"]:
                    base_df[f"{col} Uplift {term}m"] = 0.000

                tac = (
                    base_df[f"Standing Charge (p/day) {term}m"] * 365 +
                    base_df["EAC"] * (base_df[f"Day Rate (p/kWh) {term}m"] + base_df[f"Day Uplift {term}m"]) * 0.50 +
                    base_df["EAC"] * (base_df[f"Night Rate (p/kWh) {term}m"] + base_df[f"Night Uplift {term}m"]) * 0.30 +
                    base_df["EAC"] * (base_df[f"E/W Rate (p/kWh) {term}m"] + base_df[f"E/W Uplift {term}m"]) * 0.20
                ) / 100
                base_df[f"TAC_{term}m"] = tac.round(2)

            else:
                for col in [
                    "Standing Charge (p/day)",
                    "All Year - Day Rate (p/kWh)",
                    "All Year - Night Rate (p/kWh)",
                    "DUoS (p/KVA/Day)"
                ]:
                    mapping = sub_df.set_index("MPXN")[col]
                    base_df[f"{col} {term}m"] = base_df["MPXN"].map(mapping)
                for col in ["SC", "Day", "Night", "DUoS"]:
                    base_df[f"{col} Uplift {term}m"] = 0.000

                tac = (
                    base_df[f"Standing Charge (p/day) {term}m"] * 365 +
                    base_df[f"DUoS (p/KVA/Day) {term}m"] * 365 +
                    base_df["EAC"] * (base_df[f"All Year - Day Rate (p/kWh) {term}m"] + base_df[f"Day Uplift {term}m"]) * 0.70 +
                    base_df["EAC"] * (base_df[f"All Year - Night Rate (p/kWh) {term}m"] + base_df[f"Night Uplift {term}m"]) * 0.30
                ) / 100
                base_df[f"TAC_{term}m"] = tac.round(2)

        return base_df

    # --- Display NHH Table ---
    if not df_nhh.empty:
        st.subheader("📘 NHH Quotes – Uplift Entry")
        nhh_editor = build_uplift_editor(df_nhh, "NHH")
        nhh_editor.columns = [str(col).replace(" (£)", "").replace("(", "").replace(")", "").replace(" ", "_") for col in nhh_editor.columns]
        nhh_editor = nhh_editor.fillna(0)
        try:
            edited_nhh = st.data_editor(nhh_editor, use_container_width=True, num_rows="dynamic")
        except Exception as e:
            st.error(f"⚠️ Error displaying NHH table: {e}")

    # --- Display HH Table ---
    if not df_hh.empty:
        st.subheader("📗 HH Quotes – Uplift Entry")
        hh_editor = build_uplift_editor(df_hh, "HH")
        hh_editor.columns = [str(col).replace(" (£)", "").replace("(", "").replace(")", "").replace(" ", "_") for col in hh_editor.columns]
        hh_editor = hh_editor.fillna(0)
        try:
            edited_hh = st.data_editor(hh_editor, use_container_width=True, num_rows="dynamic")
        except Exception as e:
            st.error(f"⚠️ Error displaying HH table: {e}")
