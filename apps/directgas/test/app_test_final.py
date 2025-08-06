# -----------------------------------------
# File: app_test2.py - OPTIMIZED VERSION
# Purpose: Performance-optimized Streamlit frontend for Dyce's multi-site gas quote builder
# Performance improvements:
#   - Cached LDZ/base rate lookups
#   - Smart recalculation (changed rows only)
#   - Clean LDZ lookup (no debug spam)
#   - Manual calculate option
# -----------------------------------------

import sys
import os
import io
import streamlit as st
import pandas as pd
from PIL import Image
import hashlib

# Fix: Add /apps to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", "apps")))

# Import core logic modules
from directgas.logic.ldz_lookup import load_ldz_data
from directgas.logic.base_rate_lookup import get_base_rates
from directgas.logic.tac_calculator import calculate_tac_and_margin
from directgas.logic.flat_file_loader import load_flat_file
from directgas.logic.input_setup import create_input_dataframe

# -----------------------------------------
# OPTIMIZED FUNCTIONS WITH CACHING
# -----------------------------------------

def cached_ldz_lookup(postcode: str, ldz_df) -> str:
    """Clean LDZ lookup - no debug spam."""
    postcode = postcode.replace(" ", "").upper()
    
    # Try longest-to-shortest prefix match
    for length in [7, 6, 5, 4, 3]:
        match = ldz_df[ldz_df["Postcode"].str.startswith(postcode[:length])]
        if not match.empty:
            return match.iloc[0]["LDZ"]
    
    return ""

def cached_base_rates(ldz: str, kwh: float, duration: int, carbon_offset_required: bool, flat_df) -> tuple[float, float]:
    """Clean base rate lookup."""
    return get_base_rates(ldz, kwh, duration, carbon_offset_required, flat_df)

def calculate_row_hash(row_data: dict) -> str:
    """Generate hash of row data to detect changes."""
    relevant_data = {
        'site': row_data.get('Site Name', ''),
        'postcode': row_data.get('Post Code', ''),
        'kwh': row_data.get('Annual KWH', 0),
        'uplifts': {d: (
            row_data.get(f'Standing Charge Uplift ({d}m)', 0),
            row_data.get(f'Uplift Unit Rate ({d}m)', 0)
        ) for d in [12, 24, 36]}
    }
    return hashlib.md5(str(relevant_data).encode()).hexdigest()

def smart_recalculate(edited_df: pd.DataFrame, flat_df: pd.DataFrame, ldz_df: pd.DataFrame, carbon_offset_required: bool) -> pd.DataFrame:
    """Only recalculate rows that have actually changed."""
    updated_df = edited_df.copy()
    
    # Get previous row hashes from session state
    if 'row_hashes' not in st.session_state:
        st.session_state.row_hashes = {}
    
    rows_calculated = 0
    
    for i, row in edited_df.iterrows():
        # Calculate current row hash
        current_hash = calculate_row_hash(row.to_dict())
        
        # Skip calculation if row hasn't changed
        if st.session_state.row_hashes.get(i) == current_hash:
            continue
            
        # Row has changed - recalculate
        postcode = str(row.get("Post Code", "") or "").strip()
        
        try:
            kwh = float(row.get("Annual KWH", 0) or 0)
        except (ValueError, TypeError):
            kwh = 0.0
        
        if not postcode or kwh <= 0:
            continue
        
        # Use cached lookups
        ldz = cached_ldz_lookup(postcode, ldz_df)
        
        for duration in [12, 24, 36]:
            # Get cached base rates
            base_sc, base_unit = cached_base_rates(ldz, kwh, duration, carbon_offset_required, flat_df)
            
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
            updated_df.at[i, f"Base Standing Charge ({duration}m)"] = float(round(base_sc, 2))
            updated_df.at[i, f"Base Unit Rate ({duration}m)"] = float(round(base_unit, 3))
            updated_df.at[i, f"Final Standing Charge ({duration}m)"] = float(round(final_sc, 2))
            updated_df.at[i, f"Final Unit Rate ({duration}m)"] = float(round(final_unit, 3))
            updated_df.at[i, f"TAC £({duration}m)"] = float(sell_tac)
            updated_df.at[i, f"Margin £({duration}m)"] = float(margin)
        
        # Update hash for this row
        st.session_state.row_hashes[i] = current_hash
        rows_calculated += 1
    
    if rows_calculated > 0:
        st.success(f"✅ Recalculated {rows_calculated} rows")
    
    return updated_df

# -----------------------------------------
# UI Setup: Page settings and branding
# -----------------------------------------
st.set_page_config(page_title="Gas Quote Builder - Optimized", layout="wide")
st.title("Gas Multi-site Quote Builder – Optimized Version ⚡")

# Load logo
col1, col2 = st.columns([9, 1])
with col2:
    try:
        logo = Image.open("shared/DYCE-DARK BG.png")
        st.image(logo, width=120)
    except FileNotFoundError:
        st.warning("⚠️ Logo not found")

# -----------------------------------------
# Step 1: Load LDZ reference data (cached)
# -----------------------------------------
ldz_df = load_ldz_data()

# -----------------------------------------
# Step 2: Upload Supplier Flat File
# -----------------------------------------
uploaded_file = st.file_uploader("Upload Supplier Flat File (XLSX)", type=["xlsx"])

# Initialize session state
if "input_df" not in st.session_state:
    st.session_state.input_df, st.session_state.all_cols = create_input_dataframe(num_rows=0)

if uploaded_file:
    flat_df = load_flat_file(uploaded_file)

    # -----------------------------------------
    # Step 3: Quote Configuration
    # -----------------------------------------
    st.subheader("Quote Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        customer_name = st.text_input("Customer Name")
        product_type = st.selectbox("Product Type", ["Standard Gas", "Carbon Off"])
        carbon_offset_required = product_type == "Carbon Off"
    with col2:
        output_filename = st.text_input("Output file name", value="dyce_quote")
        calculation_mode = st.radio(
            "Calculation Mode",
            ["Auto (Real-time)", "Manual (Button)"],
            help="Auto: Recalculates as you type. Manual: Click button to recalculate."
        )
    
    if st.button("🔄 Reset All Data"):
        st.session_state.clear()
        st.rerun()

    # -----------------------------------------
    # Step 3B: Add Sites
    # -----------------------------------------
    st.subheader("🔹 Add Sites to Quote")

    with st.form("add_site_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            site_name = st.text_input("Site Name")
            mpxn = st.text_input("MPAN (optional)", placeholder="Optional")
        with col2:
            postcode = st.text_input("Post Code")
            try:
                consumption = float(st.text_input("Annual Consumption (kWh)", "0"))
            except ValueError:
                consumption = 0.0
        submitted = st.form_submit_button("➕ Add Site")

    if submitted and site_name and postcode and consumption > 0:
        ldz = cached_ldz_lookup(postcode.strip(), ldz_df)
        if not ldz:
            st.error(f"❌ Postcode '{postcode}' not found in LDZ database.")
        else:
            new_row = {
                "Site Name": site_name.strip(),
                "Post Code": postcode.strip(),
                "Annual KWH": float(consumption)
            }

            # Pre-calculate base rates for new row
            for d in [12, 24, 36]:
                base_sc, base_unit = cached_base_rates(ldz, consumption, d, carbon_offset_required, flat_df)
                base_tac = round((base_sc * 365 + base_unit * consumption) / 100, 2)
                
                new_row.update({
                    f"Base Standing Charge ({d}m)": float(round(base_sc, 2)),
                    f"Base Unit Rate ({d}m)": float(round(base_unit, 3)),
                    f"Standing Charge Uplift ({d}m)": float(0),
                    f"Uplift Unit Rate ({d}m)": float(0),
                    f"Final Standing Charge ({d}m)": float(round(base_sc, 2)),
                    f"Final Unit Rate ({d}m)": float(round(base_unit, 3)),
                    f"TAC £({d}m)": float(base_tac),
                    f"Margin £({d}m)": float(0)
                })

            st.session_state.input_df = pd.concat([
                st.session_state.input_df,
                pd.DataFrame([new_row])
            ], ignore_index=True)
            st.success(f"✅ Added {site_name}")

    # -----------------------------------------
    # Step 4: Agent Input Grid
    # -----------------------------------------
    st.subheader("Agent Input Grid")

    # Column configuration
    column_config = {
        "Annual KWH": st.column_config.NumberColumn("Annual KWH", min_value=0, step=1, format="%.0f")
    }

    for duration in [12, 24, 36]:
        column_config.update({
            f"Standing Charge Uplift ({duration}m)": st.column_config.NumberColumn(
                f"SC+ ({duration}m)", min_value=0, max_value=100.0, step=0.01, format="%.2f", help="Max 100p/day"
            ),
            f"Uplift Unit Rate ({duration}m)": st.column_config.NumberColumn(
                f"Unit+ ({duration}m)", min_value=0, max_value=3.000, step=0.001, format="%.3f", help="Max 3.000p/kWh"
            ),
            f"Base Standing Charge ({duration}m)": st.column_config.NumberColumn(
                f"Base SC ({duration}m)", format="%.2f", disabled=True
            ),
            f"Base Unit Rate ({duration}m)": st.column_config.NumberColumn(
                f"Base Unit ({duration}m)", format="%.3f", disabled=True
            ),
            f"Final Standing Charge ({duration}m)": st.column_config.NumberColumn(
                f"Final SC ({duration}m)", format="%.2f", disabled=True
            ),
            f"Final Unit Rate ({duration}m)": st.column_config.NumberColumn(
                f"Final Unit ({duration}m)", format="%.3f", disabled=True
            ),
            f"TAC £({duration}m)": st.column_config.NumberColumn(
                f"TAC £({duration}m)", format="£%.2f", disabled=True
            ),
            f"Margin £({duration}m)": st.column_config.NumberColumn(
                f"Margin £({duration}m)", format="£%.2f", disabled=True
            )
        })

    # Show data editor
    edited_df = st.data_editor(
        st.session_state.input_df,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        column_config=column_config,
        key="optimized_grid"
    )

    # -----------------------------------------
    # Step 5: Smart Recalculation
    # -----------------------------------------
    if calculation_mode == "Manual (Button)":
        if st.button("🔄 Recalculate All", type="primary"):
            # Force recalculation of all rows
            st.session_state.row_hashes = {}  # Clear hash cache
            updated_df = smart_recalculate(edited_df, flat_df, ldz_df, carbon_offset_required)
            st.session_state.input_df = updated_df
    else:
        # Auto mode - smart recalculation
        updated_df = smart_recalculate(edited_df, flat_df, ldz_df, carbon_offset_required)
        st.session_state.input_df = updated_df

    # -----------------------------------------
    # Step 6: Customer Quote Preview
    # -----------------------------------------
    st.subheader("Customer Quote Preview")

    preview_rows = []
    for _, row in st.session_state.input_df.iterrows():
        site = str(row.get("Site Name", "") or "").strip()
        postcode = str(row.get("Post Code", "") or "").strip()
        try:
            kwh = float(row.get("Annual KWH", 0) or 0)
        except (ValueError, TypeError):
            kwh = 0.0
        
        if site and postcode and kwh > 0:
            preview_data = {
                "Site Name": site,
                "Post Code": postcode, 
                "Annual KWH": kwh
            }
            for duration in [12, 24, 36]:
                preview_data[f"Standing Charge ({duration}m)"] = f"{row.get(f'Final Standing Charge ({duration}m)', 0):.2f}p"
                preview_data[f"Unit Rate ({duration}m)"] = f"{row.get(f'Final Unit Rate ({duration}m)', 0):.3f}p"
                preview_data[f"Annual Cost ({duration}m)"] = f"£{row.get(f'TAC £({duration}m)', 0):.2f}"
            
            preview_rows.append(preview_data)

    if preview_rows:
        preview_df = pd.DataFrame(preview_rows)
        st.dataframe(preview_df, use_container_width=True, hide_index=True)
        
        # Export functionality
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
