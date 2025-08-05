# -----------------------------------------
# File: app_test.py
# Purpose: Streamlit test frontend for Dyce's multi-site gas quote builder
# Dependencies: logic modules from /apps/directgas/logic/
# -----------------------------------------

import sys
import os
import io
import streamlit as st
import pandas as pd
from PIL import Image

# Fix: Add /apps to the Python path so we can import directgas as a top-level module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", "apps")))

# Import core logic modules
from directgas.logic.ldz_lookup import load_ldz_data, match_postcode_to_ldz
from directgas.logic.base_rate_lookup import get_base_rates
from directgas.logic.tac_calculator import calculate_tac_and_margin
from directgas.logic.flat_file_loader import load_flat_file
from directgas.logic.input_setup import create_input_dataframe

# -----------------------------------------
# UI Setup: Page settings and branding
# -----------------------------------------
st.set_page_config(page_title="Gas Multi-tool (Final)", layout="wide")
st.title("Gas Multi-site Quote Builder – Final Version")

# Load logo image (top-right)
col1, col2 = st.columns([9, 1])
with col2:
    try:
        logo = Image.open("shared/DYCE-DARK BG.png")
        st.image(logo, width=120)
    except FileNotFoundError:
        st.warning("⚠️ Logo not found")

# -----------------------------------------
# Step 1: Load LDZ reference data
# -----------------------------------------
ldz_df = load_ldz_data()

# -----------------------------------------
# Step 2: Upload Supplier Flat File
# -----------------------------------------
uploaded_file = st.file_uploader("Upload Supplier Flat File (XLSX)", type=["xlsx"])

if uploaded_file:
    flat_df = load_flat_file(uploaded_file)

    # -----------------------------------------
    # Step 3: Quote Configuration Inputs
    # -----------------------------------------
    st.subheader("Quote Configuration")
    customer_name = st.text_input("Customer Name")
    product_type = st.selectbox("Product Type", ["Standard Gas", "Carbon Off"])
    carbon_offset_required = product_type == "Carbon Off"
    output_filename = st.text_input("Output file name", value="dyce_quote")

    # -----------------------------------------
    # Step 3B: Add Sites via Input Form
    # -----------------------------------------
    st.subheader("🔹 Add Sites to Quote")

    if "input_df" not in st.session_state:
        st.session_state.input_df, st.session_state.all_cols = create_input_dataframe(num_rows=0)

    with st.form("add_site_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            site_name = st.text_input("Site Name")
            mpxn = st.text_input("MPAN (optional)", placeholder="Can leave blank")
        with col2:
            postcode = st.text_input("Post Code")
            try:
                consumption = float(st.text_input("Annual Consumption (kWh)", "0"))
            except ValueError:
                consumption = 0.0
        submitted = st.form_submit_button("➕ Add Site")

    if submitted:
        if site_name and postcode and consumption > 0:
            ldz = match_postcode_to_ldz(postcode.strip(), ldz_df)
            if not ldz:
                st.error(f"❌ Postcode '{postcode}' not found in LDZ database. Please check the postcode.")
            else:
                new_row = {
                    "Site Name": site_name.strip(),
                    "Post Code": postcode.strip(),
                    "Annual KWH": consumption
                }

                for d in [12, 24, 36]:
                    base_sc, base_unit = get_base_rates(ldz, consumption, d, carbon_offset_required, flat_df)
                    new_row.update({
                        f"Base Standing Charge ({d}m)": round(base_sc, 2),
                        f"Base Unit Rate ({d}m)": round(base_unit, 3),
                        f"Standing Charge Uplift ({d}m)": 0,
                        f"Uplift Unit Rate ({d}m)": 0,
                        f"TAC £({d}m)": 0,
                        f"Margin £({d}m)": 0
                    })

                st.session_state.input_df = pd.concat([
                    st.session_state.input_df,
                    pd.DataFrame([new_row])
                ], ignore_index=True)
        else:
            st.warning("Please enter valid Site Name, Post Code, and KWH.")

    # -----------------------------------------
    # Step 4: Editable Input Grid Setup
    # -----------------------------------------
    st.subheader("Input Grid (Editable)")

    column_config = {
        "Annual KWH": st.column_config.NumberColumn(
            "Annual KWH",
            min_value=0,
            step=1,
            format="%.0f"
        )
    }

    for duration in [12, 24, 36]:
        column_config[f"Standing Charge Uplift ({duration}m)"] = st.column_config.NumberColumn(
            f"SC Uplift ({duration}m)",
            min_value=0,
            max_value=100.0,
            step=0.01,
            format="%.2f",
            help="Max 100p/day"
        )
        column_config[f"Uplift Unit Rate ({duration}m)"] = st.column_config.NumberColumn(
            f"Unit Uplift ({duration}m)",
            min_value=0,
            max_value=3.000,
            step=0.001,
            format="%.3f",
            help="Max 3.000p/kWh"
        )

    edited_df = st.data_editor(
        st.session_state.input_df,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        column_config=column_config,
        disabled=[]
    )

    # -----------------------------------------
    # Step 5: Inject Base Rates Back into Editable Grid
    # -----------------------------------------
    preview_df = edited_df.copy()
    for i, row in edited_df.iterrows():
        postcode = row.get("Post Code", "")
        try:
            kwh = float(row.get("Annual KWH", 0))
        except (ValueError, TypeError):
            continue
        if not postcode or kwh <= 0:
            continue
        ldz = match_postcode_to_ldz(postcode, ldz_df)
        for duration in [12, 24, 36]:
            base_sc, base_unit = get_base_rates(ldz, kwh, duration, carbon_offset_required, flat_df)
            preview_df.at[i, f"Base Standing Charge ({duration}m)"] = round(base_sc, 2)
            preview_df.at[i, f"Base Unit Rate ({duration}m)"] = round(base_unit, 3)

    edited_df = preview_df

    # -----------------------------------------
    # Step 6: Calculate TAC & Margin Values
    # -----------------------------------------
    result_rows = []
    for _, row in edited_df.iterrows():
        site = row.get("Site Name", "").strip()
        postcode = row.get("Post Code", "").strip()
        try:
            kwh = float(row.get("Annual KWH", 0))
        except (ValueError, TypeError):
            continue
        if not postcode or kwh <= 0:
            continue
        ldz = match_postcode_to_ldz(postcode, ldz_df)
        row_data = {
            "Site Name": site,
            "Post Code": postcode,
            "Annual KWH": kwh
        }
        for duration in [12, 24, 36]:
            base_sc, base_unit = get_base_rates(ldz, kwh, duration, carbon_offset_required, flat_df)
            uplift_unit = row.get(f"Uplift Unit Rate ({duration}m)", 0)
            uplift_sc = row.get(f"Standing Charge Uplift ({duration}m)", 0)
            sell_tac, margin = calculate_tac_and_margin(kwh, base_sc, base_unit, uplift_sc, uplift_unit)
            row_data[f"Base Standing Charge ({duration}m)"] = round(base_sc, 2)
            row_data[f"Base Unit Rate ({duration}m)"] = round(base_unit, 3)
            row_data[f"TAC £({duration}m)"] = sell_tac
            row_data[f"Margin £({duration}m)"] = margin
        result_rows.append(row_data)

    # -----------------------------------------
    # Step 7: Display Output Table
    # -----------------------------------------
    if result_rows:
        output_df = pd.DataFrame(result_rows)
        output_cols = ["Site Name", "Post Code", "Annual KWH"] + \
                      [f"TAC £({d}m)" for d in [12, 24, 36]] + \
                      [f"Margin £({d}m)" for d in [12, 24, 36]]
        output_df = output_df[output_cols].copy()
        st.dataframe(output_df, use_container_width=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            output_df.to_excel(writer, index=False)
        output.seek(0)

        st.download_button(
            label="Download Quote Output",
            data=output,
            file_name=f"{output_filename}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("📁 Please upload a supplier flat file to begin creating quotes.")
