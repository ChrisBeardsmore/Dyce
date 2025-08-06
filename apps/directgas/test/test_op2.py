# -----------------------------------------
# File: app2.py
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

# Initialize session state BEFORE any conditionals
if "input_df" not in st.session_state:
    st.session_state.input_df, st.session_state.all_cols = create_input_dataframe(num_rows=0)

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
    
    if st.button("🔄 Reset All Data (Clear Session)"):
        st.session_state.clear()
        st.rerun()

    # -----------------------------------------
    # Step 3B: Add Sites via Input Form
    # -----------------------------------------
    st.subheader("🔹 Add Sites to Quote")

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
                    base_tac = round((base_sc * 365 + base_unit * consumption) / 100, 2)
                    
                    new_row.update({
                        f"Base Standing Charge ({d}m)": round(base_sc, 2),
                        f"Base Unit Rate ({d}m)": round(base_unit, 3),
                        f"Standing Charge Uplift ({d}m)": 0,
                        f"Uplift Unit Rate ({d}m)": 0,
                        f"Final Standing Charge ({d}m)": round(base_sc, 2),
                        f"Final Unit Rate ({d}m)": round(base_unit, 3),
                        f"TAC £({d}m)": base_tac,
                        f"Margin £({d}m)": 0
                    })

                st.session_state.input_df = pd.concat([
                    st.session_state.input_df,
                    pd.DataFrame([new_row])
                ], ignore_index=True)
        else:
            st.warning("Please enter valid Site Name, Post Code, and KWH.")

    # -----------------------------------------
    # Step 4: Agent Input Grid (All Calculations Happen Here)
    # -----------------------------------------
    st.subheader("Agent Input Grid")

    # Configure column types and validation
    column_config = {
        "Annual KWH": st.column_config.NumberColumn("Annual KWH", min_value=0, step=1, format="%.0f")
    }

    for duration in [12, 24, 36]:
        column_config[f"Standing Charge Uplift ({duration}m)"] = st.column_config.NumberColumn(
            f"SC Uplift ({duration}m)", min_value=0, max_value=100.0, step=0.01, format="%.2f", help="Max 100p/day"
        )
        column_config[f"Uplift Unit Rate ({duration}m)"] = st.column_config.NumberColumn(
            f"Unit Uplift ({duration}m)", min_value=0, max_value=3.000, step=0.001, format="%.3f", help="Max 3.000p/kWh"
        )
        # Read-only calculated fields for agent reference
        column_config[f"Base Standing Charge ({duration}m)"] = st.column_config.NumberColumn(
            f"Base SC ({duration}m)", format="%.2f", disabled=True, help="Base rate from supplier (p/day)"
        )
        column_config[f"Base Unit Rate ({duration}m)"] = st.column_config.NumberColumn(
            f"Base Unit ({duration}m)", format="%.3f", disabled=True, help="Base rate from supplier (p/kWh)"
        )
        column_config[f"Final Standing Charge ({duration}m)"] = st.column_config.NumberColumn(
            f"Final SC ({duration}m)", format="%.2f", disabled=True, help="Base + Uplift (p/day)"
        )
        column_config[f"Final Unit Rate ({duration}m)"] = st.column_config.NumberColumn(
            f"Final Unit ({duration}m)", format="%.3f", disabled=True, help="Base + Uplift (p/kWh)"
        )
        column_config[f"TAC £({duration}m)"] = st.column_config.NumberColumn(
            f"TAC £({duration}m)", format="£%.2f", disabled=True, help="Total Annual Cost"
        )
        column_config[f"Margin £({duration}m)"] = st.column_config.NumberColumn(
            f"Margin £({duration}m)", format="£%.2f", disabled=True, help="Dyce profit margin"
        )

    # Show data editor and capture changes
    edited_df = st.data_editor(
        st.session_state.input_df,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        column_config=column_config,
        key="agent_grid"
    )

    # -----------------------------------------
    # Step 5: Manual Calculation Update
    # -----------------------------------------
    # Add Calculate button to trigger recalculation
    if st.button("🔄 Calculate Rates"):
        # Calculate all values (same logic as before, just moved inside button)
        updated_df = edited_df.copy()

        for i, row in edited_df.iterrows():
            postcode = str(row.get("Post Code", "") or "").strip()
            
            try:
                kwh = float(row.get("Annual KWH", 0) or 0)
            except (ValueError, TypeError):
                kwh = 0.0
            
            if not postcode or kwh <= 0:
                continue
            
            ldz = match_postcode_to_ldz(postcode, ldz_df)
            
            for duration in [12, 24, 36]:
                # Get base rates from supplier file
                base_sc, base_unit = get_base_rates(ldz, kwh, duration, carbon_offset_required, flat_df)
                
                # Get user uplifts with proper type conversion
                try:
                    uplift_sc = float(row.get(f"Standing Charge Uplift ({duration}m)", 0) or 0)
                    uplift_unit = float(row.get(f"Uplift Unit Rate ({duration}m)", 0) or 0)
                except (ValueError, TypeError):
                    uplift_sc = 0.0
                    uplift_unit = 0.0
                
                # Calculate final values
                final_sc = base_sc + uplift_sc
                final_unit = base_unit + uplift_unit
                sell_tac, margin = calculate_tac_and_margin(kwh, base_sc, base_unit, uplift_sc, uplift_unit)
                
                # Update calculated dataframe
                updated_df.at[i, f"Base Standing Charge ({duration}m)"] = round(base_sc, 2)
                updated_df.at[i, f"Base Unit Rate ({duration}m)"] = round(base_unit, 3)
                updated_df.at[i, f"Final Standing Charge ({duration}m)"] = round(final_sc, 2)
                updated_df.at[i, f"Final Unit Rate ({duration}m)"] = round(final_unit, 3)
                updated_df.at[i, f"TAC £({duration}m)"] = sell_tac
                updated_df.at[i, f"Margin £({duration}m)"] = margin

        # Update session state with calculated values
        st.session_state.input_df = updated_df
        st.success("✅ Rates calculated successfully!")
        st.rerun()

    # Debug info (remove this after testing)
    if st.checkbox("Show Debug Info"):
        if not st.session_state.input_df.empty:
            test_row = st.session_state.input_df.iloc[0]
            st.write("Debug - First Row Values:")
            st.write(f"Unit Uplift (12m): {test_row.get('Uplift Unit Rate (12m)', 'NOT FOUND')}")
            st.write(f"Base Unit (12m): {test_row.get('Base Unit Rate (12m)', 'NOT FOUND')}")
            st.write(f"Final Unit (12m): {test_row.get('Final Unit Rate (12m)', 'NOT FOUND')}")

    # -----------------------------------------
    # Step 6: Customer Quote Preview (Display Only)
    # -----------------------------------------
    st.subheader("Customer Quote Preview")

    # Filter out empty rows for preview
    preview_rows = []
    for _, row in st.session_state.input_df.iterrows():
        site = str(row.get("Site Name", "") or "").strip()
        postcode = str(row.get("Post Code", "") or "").strip()
        try:
            kwh = float(row.get("Annual KWH", 0) or 0)
        except (ValueError, TypeError):
            kwh = 0.0
        
        if site and postcode and kwh > 0:  # Only include completed rows
            preview_data = {
                "Site Name": site,
                "Post Code": postcode,
                "Annual KWH": kwh
            }
            # Add customer-facing pricing (final rates and TAC only)
            for duration in [12, 24, 36]:
                preview_data[f"Standing Charge ({duration}m)"] = f"{row.get(f'Final Standing Charge ({duration}m)', 0):.2f}p"
                preview_data[f"Unit Rate ({duration}m)"] = f"{row.get(f'Final Unit Rate ({duration}m)', 0):.3f}p"
                preview_data[f"Annual Cost ({duration}m)"] = f"£{row.get(f'TAC £({duration}m)', 0):.2f}"
            
            preview_rows.append(preview_data)

    if preview_rows:
        preview_df = pd.DataFrame(preview_rows)
        st.dataframe(preview_df, use_container_width=True, hide_index=True)
        
        # -----------------------------------------
        # Step 7: Export Customer Quote
        # -----------------------------------------
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
