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

                # Initialize all columns for new row
                for d in [12, 24, 36]:
                    base_sc, base_unit = get_base_rates(ldz, consumption, d, carbon_offset_required, flat_df)
                    new_row.update({
                        f"Base Standing Charge ({d}m)": round(base_sc, 2),
                        f"Base Unit Rate ({d}m)": round(base_unit, 3),
                        f"Standing Charge Uplift ({d}m)": 0,
                        f"Uplift Unit Rate ({d}m)": 0,
                        f"Final Standing Charge ({d}m)": round(base_sc, 2),  # NEW
                        f"Final Unit Rate ({d}m)": round(base_unit, 3),      # NEW
                        f"TAC £({d}m)": round((base_sc * 365 + base_unit * consumption) / 100, 2),  # NEW
                        f"Margin £({d}m)": 0  # NEW
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

    # Configure column types and validation
    column_config = {
        "Annual KWH": st.column_config.NumberColumn(
            "Annual KWH",
            min_value=0,
            step=1,
            format="%.0f"
        )
    }

    # Add configurations for uplift columns (editable)
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

    # Add configurations for calculated fields (read-only)
    for duration in [12, 24, 36]:
        column_config[f"Base Standing Charge ({duration}m)"] = st.column_config.NumberColumn(
            f"Base SC ({duration}m)",
            format="%.2f",
            disabled=True,
            help="Base rate from supplier (p/day)"
        )
        column_config[f"Base Unit Rate ({duration}m)"] = st.column_config.NumberColumn(
            f"Base Unit ({duration}m)",
            format="%.3f",
            disabled=True,
            help="Base rate from supplier (p/kWh)"
        )
        column_config[f"Final Standing Charge ({duration}m)"] = st.column_config.NumberColumn(
            f"Final SC ({duration}m)",
            format="%.2f",
            disabled=True,
            help="Base + Uplift (p/day)"
        )
        column_config[f"Final Unit Rate ({duration}m)"] = st.column_config.NumberColumn(
            f"Final Unit ({duration}m)",
            format="%.3f", 
            disabled=True,
            help="Base + Uplift (p/kWh)"
        )
        column_config[f"TAC £({duration}m)"] = st.column_config.NumberColumn(
            f"TAC £({duration}m)",
            format="£%.2f",
            disabled=True,
            help="Total Annual Cost"
        )
        column_config[f"Margin £({duration}m)"] = st.column_config.NumberColumn(
            f"Margin £({duration}m)",
            format="£%.2f",
            disabled=True,
            help="Dyce profit margin"
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
    # Step 5: Calculate All Values (Base Rates + TAC + Margin)
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
            # Get base rates from supplier file
            base_sc, base_unit = get_base_rates(ldz, kwh, duration, carbon_offset_required, flat_df)
            
            # Get uplift values from user input
            uplift_sc = row.get(f"Standing Charge Uplift ({duration}m)", 0)
            uplift_unit = row.get(f"Uplift Unit Rate ({duration}m)", 0)
            
            # Calculate final customer rates (base + uplift)
            final_sc = base_sc + uplift_sc
            final_unit = base_unit + uplift_unit
            
            # Calculate TAC and margin
            sell_tac, margin = calculate_tac_and_margin(kwh, base_sc, base_unit, uplift_sc, uplift_unit)
            
            # Update all calculated fields in the grid
            preview_df.at[i, f"Base Standing Charge ({duration}m)"] = round(base_sc, 2)
            preview_df.at[i, f"Base Unit Rate ({duration}m)"] = round(base_unit, 3)
            preview_df.at[i, f"Final Standing Charge ({duration}m)"] = round(final_sc, 2)
            preview_df.at[i, f"Final Unit Rate ({duration}m)"] = round(final_unit, 3)
            preview_df.at[i, f"TAC £({duration}m)"] = sell_tac
            preview_df.at[i, f"Margin £({duration}m)"] = margin

    edited_df = preview_df

    # -----------------------------------------
    # Step 6: Prepare Customer-Facing Output Data
    # -----------------------------------------
    st.subheader("Customer Quote Preview")
    
    if not edited_df.empty:
        customer_rows = []
        for _, row in edited_df.iterrows():
            site = row.get("Site Name", "").strip()
            postcode = row.get("Post Code", "").strip()
            try:
                kwh = float(row.get("Annual KWH", 0))
            except (ValueError, TypeError):
                continue
            if not postcode or kwh <= 0:
                continue
            
            # Build customer-facing row
            customer_data = {
                "Site Name": site,
                "Post Code": postcode,
                "Annual KWH": kwh
            }
            
            # Add final rates and TAC for each duration (customer view)
            for duration in [12, 24, 36]:
                customer_data[f"Standing Charge ({duration}m)"] = row.get(f"Final Standing Charge ({duration}m)", 0)
                customer_data[f"Unit Rate ({duration}m)"] = row.get(f"Final Unit Rate ({duration}m)", 0)
                customer_data[f"TAC £({duration}m)"] = row.get(f"TAC £({duration}m)", 0)
            
            customer_rows.append(customer_data)

        # -----------------------------------------
        # Step 7: Display Customer Output and Download
        # -----------------------------------------
        if customer_rows:
            customer_df = pd.DataFrame(customer_rows)
            
            # Define customer-facing columns in the right order
            customer_cols = ["Site Name", "Post Code", "Annual KWH"]
            for d in [12, 24, 36]:
                customer_cols += [f"Standing Charge ({d}m)", f"Unit Rate ({d}m)", f"TAC £({d}m)"]
            
            st.dataframe(customer_df[customer_cols], use_container_width=True)

            # Create Excel download for customer
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                customer_df[customer_cols].to_excel(writer, index=False, sheet_name="Quote")
            output.seek(0)

            st.download_button(
                label="📥 Download Customer Quote",
                data=output,
                file_name=f"{output_filename}_customer.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

else:
    st.info("📁 Please upload a supplier flat file to begin creating quotes.")
