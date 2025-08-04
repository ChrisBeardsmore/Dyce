# 🔴 -----------------------------------------
# 🔴 File: app_test.py
# 🔴 Purpose: Streamlit test frontend for Dyce’s multi-site gas quote builder
# 🔴 Dependencies: logic modules from /logic/, Streamlit, pandas, PIL
# 🔴 -----------------------------------------

import sys
import os
# 🔴 Fix path so Python can find top-level 'apps' folder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

import streamlit as st
import pandas as pd
from PIL import Image

# 🔴 Import core logic modules
from apps.directgas.logic.ldz_lookup import load_ldz_data, match_postcode_to_ldz
from apps.directgas.logic.base_price_lookup import get_base_rates
from apps.directgas.logic.tac_calculator import calculate_tac_and_margin
from apps.directgas.logic.flat_file_loader import load_flat_file
from apps.directgas.logic.input_setup import create_input_dataframe

# 🔴 -----------------------------------------
# 🔴 UI Setup: Page settings and branding
# 🔴 -----------------------------------------

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

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

# 🔴 -----------------------------------------
# 🔴 Step 1: Load LDZ reference data
# 🔴 -----------------------------------------
ldz_df = load_ldz_data()

# 🔴 -----------------------------------------
# 🔴 Step 2: Upload Supplier Flat File
# 🔴 -----------------------------------------
uploaded_file = st.file_uploader("Upload Supplier Flat File (XLSX)", type=["xlsx"])

if uploaded_file:
    flat_df = load_flat_file(uploaded_file)

    # 🔴 -----------------------------------------
    # 🔴 Step 3: Quote Configuration Inputs
    # 🔴 -----------------------------------------
    st.subheader("Quote Configuration")
    customer_name = st.text_input("Customer Name")
    product_type = st.selectbox("Product Type", ["Standard Gas", "Carbon Off"])
    carbon_offset_required = product_type == "Carbon Off"
    output_filename = st.text_input("Output file name", value="dyce_quote")

    # 🔴 -----------------------------------------
    # 🔴 Step 4: Editable Input Grid Setup
    # 🔴 -----------------------------------------
    st.subheader("Input Grid (Editable)")
    base_cols = ["Site Name", "Post Code", "Annual KWH"]
    durations = [12, 24, 36]

    input_df, all_cols = create_input_dataframe(num_rows=10)

    # Display editable grid to user
    edited_df = st.data_editor(
        input_df,
        use_container_width=True,
        num_rows="fixed",
        hide_index=True,
        disabled=[]
    )

    # 🔴 -----------------------------------------
    # 🔴 Step 5: Preview Output Table – TAC & Margin
    # 🔴 -----------------------------------------
    st.subheader("Customer-Facing Output Preview")
    result_rows = []

    for _, row in edited_df.iterrows():
        site = row.get("Site Name", "")
        postcode = row.get("Post Code", "")

        try:
            kwh = float(row.get("Annual KWH", 0))
        except (ValueError, TypeError):
            continue

        if not postcode or kwh <= 0:
            continue

        # Match postcode → LDZ
        ldz = match_postcode_to_ldz(postcode, ldz_df)

        # Prepare row for output
        row_data = {
            "Site Name": site,
            "Post Code": postcode,
            "Annual KWH": kwh
        }

        for duration in durations:
            # Lookup base prices
            base_sc, base_unit = get_base_rates(ldz, kwh, duration, carbon_offset_required, flat_df)

            # Pull uplifts from user input
            uplift_unit = row.get(f"Uplift Unit Rate ({duration}m)", 0)
            uplift_sc = row.get(f"Standing Charge Uplift ({duration}m)", 0)

            # Calculate TAC and margin
            sell_tac, margin = calculate_tac_and_margin(kwh, base_sc, base_unit, uplift_sc, uplift_unit)

            # Append results
            row_data[f"Base Standing Charge ({duration}m)"] = round(base_sc, 2)
            row_data[f"Base Unit Rate ({duration}m)"] = round(base_unit, 3)
            row_data[f"TAC £({duration}m)"] = sell_tac
            row_data[f"Margin £({duration}m)"] = margin

        result_rows.append(row_data)

    # 🔴 -----------------------------------------
    # 🔴 Step 6: Display Output Table
    # 🔴 -----------------------------------------
    if result_rows:
        output_df = pd.DataFrame(result_rows)

        output_cols = ["Site Name", "Post Code", "Annual KWH"] + \
                      [f"TAC £({d}m)" for d in durations] + \
                      [f"Margin £({d}m)" for d in durations]

        st.dataframe(output_df[output_cols], use_container_width=True)

        # Optional download
        st.download_button(
            label="Download Quote Output",
            data=output_df.to_excel(index=False, engine="openpyxl"),
            file_name=f"{output_filename}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
