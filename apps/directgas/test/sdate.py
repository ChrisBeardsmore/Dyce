# -----------------------------------------
# File: sdate.py
# Purpose: Streamlit frontend for Dyce's multi-site gas quote builder
# Dependencies: logic modules from /apps/directgas/logic/
# -----------------------------------------

import sys
import os
import io
import streamlit as st
import pandas as pd
from PIL import Image
from datetime import date  # NEW: Import for start date

# ✅ Fix: Add /apps to Python path robustly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))             # /apps/directgas/test
APPS_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))    # → /apps
if APPS_DIR not in sys.path:
    sys.path.insert(0, APPS_DIR)

# ✅ Core logic imports
from logic.ldz_lookup import load_ldz_data, match_postcode_to_ldz
from logic.base_rate_lookup import get_base_rates
from logic.tac_calculator import calculate_tac_and_margin
from logic.flat_file_loader import load_flat_file
from logic.input_setup import create_input_dataframe

# -----------------------------------------
# UI Setup
# -----------------------------------------
st.set_page_config(page_title="Direct Sales Gas Tool", layout="wide")
st.title("Direct Sales Gas Tool")

# Logo
col1, col2 = st.columns([8, 2])
with col2:
    try:
        logo = Image.open("shared/DYCE-DARK BG.png")
        st.image(logo, width=180)
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

if "input_df" not in st.session_state:
    st.session_state.input_df, st.session_state.all_cols = create_input_dataframe(num_rows=0)

if uploaded_file:
    flat_df = load_flat_file(uploaded_file)

    # -----------------------------------------
    # Step 3: Quote Configuration
    # -----------------------------------------
    st.subheader("Quote Configuration")
    
    # NEW: Add columns for better layout
    config_col1, config_col2, config_col3 = st.columns(3)
    
    with config_col1:
        customer_name = st.text_input("Customer Name")
        product_type = st.selectbox("Product Type", ["Standard Gas", "Carbon Off"])
    
    with config_col2:
        # NEW: Contract start date picker
        contract_start_date = st.date_input(
            "Contract Start Date", 
            value=date.today(),
            help="When should the contract begin?"
        )
        output_filename = st.text_input("Output file name", value="dyce_quote")
    
    with config_col3:
        st.write("")  # Spacer
        if st.button("🔄 Reset All Data (Clear Session)"):
            st.session_state.clear()
            st.rerun()
    
    carbon_offset_required = product_type == "Carbon Off"

    # -----------------------------------------
    # Step 3B: Add Sites via Input Form
    # -----------------------------------------
    st.subheader("🔹 Add Sites to Quote")

    with st.form("add_site_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            site_name = st.text_input("Site Name")
            site_reference = st.text_input("Site Reference (optional)", placeholder="Can leave blank")
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
                    "Site Reference": site_reference.strip(),  # NEW: Add site reference
                    "Post Code": postcode.strip(),
                    "Annual Consumption KWh": float(consumption),
                    "Contract Start Date": contract_start_date.strftime("%d/%m/%Y")  # NEW: Add start date
                }

                for d in [12, 24, 36]:
                    base_sc, base_unit = get_base_rates(ldz, consumption, d, carbon_offset_required, flat_df, start_date=contract_start_date)
                    base_tac = round((base_sc * 365 + base_unit * consumption) / 100, 2)

                    new_row.update({
                        f"Standing Charge (Base {d}m)": float(round(base_sc, 2)),
                        f"Unit Rate (Base {d}m)": float(round(base_unit, 3)),
                        f"Standing Charge (uplift {d}m)": float(0.00),
                        f"Unit Rate (Uplift {d}m)": float(0.000),
                        f"Sell Standing Charge ({d}m)": float(round(base_sc, 2)),
                        f"Sell Unit Rate ({d}m)": float(round(base_unit, 3)),
                        f"TAC ({d}m)": float(base_tac),
                        f"Margin £({d}m)": float(0.00)
                    })

                st.session_state.input_df = pd.concat([
                    st.session_state.input_df,
                    pd.DataFrame([new_row])
                ], ignore_index=True)
                
                # NEW: Success message with start date
                st.success(f"✅ Added {site_name} - Contract starts {contract_start_date.strftime('%d/%m/%Y')}")
        else:
            st.warning("⚠️ Please enter a valid Site Name, Post Code, and kWh.")

    # -----------------------------------------
    # Step 4: Agent Input Grid
    # -----------------------------------------
    st.subheader("Agent Input Grid")

    # Use a dynamic key to avoid glitchy rendering issues
    grid_key = f"agent_grid_{len(st.session_state.input_df)}"

    column_config = {
        "Site Name": st.column_config.TextColumn("Site Name"),
        "Site Reference": st.column_config.TextColumn("Site Reference"),  # NEW: Add reference column
        "Post Code": st.column_config.TextColumn("Post Code"),
        "Annual Consumption KWh": st.column_config.NumberColumn("Annual Consumption KWh", min_value=0, step=1, format="%.0f"),
        "Contract Start Date": st.column_config.TextColumn("Start Date")  # NEW: Add start date column
    }

    for duration in [12, 24, 36]:
        column_config[f"Standing Charge (uplift {duration}m)"] = st.column_config.NumberColumn(
            f"Standing Charge (uplift {duration}m)", min_value=0, max_value=100.0, step=0.01, format="%.2f", help="Max 100p/day"
        )
        column_config[f"Unit Rate (Uplift {duration}m)"] = st.column_config.NumberColumn(
            f"Unit Rate (Uplift {duration}m)", min_value=0, max_value=3.000, step=0.001, format="%.3f", help="Max 3.000p/kWh"
        )
        column_config[f"Standing Charge (Base {duration}m)"] = st.column_config.NumberColumn(
            f"Standing Charge (Base {duration}m)", format="%.2f", disabled=True
        )
        column_config[f"Unit Rate (Base {duration}m)"] = st.column_config.NumberColumn(
            f"Unit Rate (Base {duration}m)", format="%.3f", disabled=True
        )
        column_config[f"Sell Standing Charge ({duration}m)"] = st.column_config.NumberColumn(
            f"Sell Standing Charge ({duration}m)", format="%.2f", disabled=True
        )
        column_config[f"Sell Unit Rate ({duration}m)"] = st.column_config.NumberColumn(
            f"Sell Unit Rate ({duration}m)", format="%.3f", disabled=True
        )
        column_config[f"TAC ({duration}m)"] = st.column_config.NumberColumn(
            f"TAC ({duration}m)", format="£%.2f", disabled=True
        )
        column_config[f"Margin £({duration}m)"] = st.column_config.NumberColumn(
            f"Margin £({duration}m)", format="£%.2f", disabled=True
        )

    # Render the editable data grid
    edited_df = st.data_editor(
        st.session_state.input_df,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        column_config=column_config,
        key=grid_key
    )
    
    # Store the edited data and only calculate when button is pressed
    st.session_state.input_df = edited_df.copy()
    
    # -----------------------------------------
    # Step 5: Calculate Button Logic
    # -----------------------------------------
    if st.button("🔄 Calculate Rates"):
        updated_df = st.session_state.input_df.copy()

    for i, row in updated_df.iterrows():
        postcode = str(row.get("Post Code", "") or "").strip()
        # NEW: Get the start date for this row
        row_start_date = str(row.get("Contract Start Date", "") or "").strip()
        
        try:
            kwh = float(row.get("Annual Consumption KWh", 0) or 0)
        except (ValueError, TypeError):
            kwh = 0.0

        if not postcode or kwh <= 0:
            continue
  # NEW: Get LDZ for this row to recalculate base rates with start date
        ldz = match_postcode_to_ldz(postcode, ldz_df)
        
        for duration in [12, 24, 36]:
            try:
                # NEW: Recalculate base rates with start date
                base_sc, base_unit = get_base_rates(ldz, kwh, duration, carbon_offset_required, flat_df, start_date=row_start_date)
                
                # Update the base rates in the dataframe
                updated_df.at[i, f"Standing Charge (Base {duration}m)"] = round(base_sc, 2)
                updated_df.at[i, f"Unit Rate (Base {duration}m)"] = round(base_unit, 3)
                
                # Get uplifts
                uplift_sc = float(row.get(f"Standing Charge (uplift {duration}m)", 0) or 0)
                uplift_unit = float(row.get(f"Unit Rate (Uplift {duration}m)", 0) or 0)
            except (ValueError, TypeError):
                base_sc = base_unit = uplift_sc = uplift_unit = 0.0

            final_sc = base_sc + uplift_sc
            final_unit = base_unit + uplift_unit
            sell_tac, margin = calculate_tac_and_margin(kwh, base_sc, base_unit, uplift_sc, uplift_unit)

            updated_df.at[i, f"Sell Standing Charge ({duration}m)"] = round(final_sc, 2)
            updated_df.at[i, f"Sell Unit Rate ({duration}m)"] = round(final_unit, 3)
            updated_df.at[i, f"TAC ({duration}m)"] = sell_tac
            updated_df.at[i, f"Margin £({duration}m)"] = margin

    st.session_state.input_df = updated_df
    st.success("✅ Rates calculated successfully!")
    st.rerun()

    # -----------------------------------------
    # Step 6: Customer Quote Preview
    # -----------------------------------------
    st.subheader("Customer Quote Preview")

    preview_rows = []
    for _, row in st.session_state.input_df.iterrows():
        site = str(row.get("Site Name", "") or "").strip()
        postcode = str(row.get("Post Code", "") or "").strip()
        site_ref = str(row.get("Site Reference", "") or "").strip()  # NEW: Get reference
        start_date = str(row.get("Contract Start Date", "") or "").strip()  # NEW: Get start date
        try:
            kwh = float(row.get("Annual Consumption KWh", 0) or 0)
        except (ValueError, TypeError):
            kwh = 0.0

        if site and postcode and kwh > 0:
            preview_data = {
                "Site Name": site,
                "Site Reference": site_ref,  # NEW: Include reference
                "Post Code": postcode,
                "Annual Consumption KWh": kwh,
                "Contract Start Date": start_date  # NEW: Include start date
            }
            for duration in [12, 24, 36]:
                preview_data[f"Standing Charge ({duration}m)"] = f"{row.get(f'Sell Standing Charge ({duration}m)', 0):.2f}p"
                preview_data[f"Unit Rate ({duration}m)"] = f"{row.get(f'Sell Unit Rate ({duration}m)', 0):.3f}p"
                preview_data[f"Annual Cost ({duration}m)"] = f"£{row.get(f'TAC ({duration}m)', 0):.2f}"

            preview_rows.append(preview_data)

    if preview_rows:
        preview_df = pd.DataFrame(preview_rows)
        st.dataframe(preview_df, use_container_width=True, hide_index=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            preview_df.to_excel(writer, index=False, sheet_name="Quote")
        output.seek(0)

        st.download_button(
            label="📥 Download Customer Quote",
            data=output,
            file_name=f"{output_filename}_quote.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("👆 Add sites above to see customer quote preview")

else:
    st.info("📁 Please upload a supplier flat file to begin creating quotes.")
