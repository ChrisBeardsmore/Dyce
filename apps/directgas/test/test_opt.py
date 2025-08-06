# -----------------------------------------
# File: app_fixed.py - MEMORY OPTIMIZED VERSION
# Purpose: Fixed version of the gas quote builder with proper optimization
# Fixes:
#   - Proper LDZ data caching
#   - Cleaned up session state management
#   - Simplified recalculation logic
#   - Memory leak prevention
# -----------------------------------------

import sys
import os
import io
import streamlit as st
import pandas as pd
from PIL import Image

# Fix: Add /apps to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", "apps")))

# Import core logic modules
from directgas.logic.base_rate_lookup import get_base_rates
from directgas.logic.tac_calculator import calculate_tac_and_margin
from directgas.logic.flat_file_loader import load_flat_file
from directgas.logic.input_setup import create_input_dataframe

# -----------------------------------------
# FIXED CACHING FUNCTIONS
# -----------------------------------------

@st.cache_data
def load_ldz_data_cached():
    """Load LDZ data once and cache it properly."""
    url = "https://raw.githubusercontent.com/ChrisBeardsmore/Gas-Pricing/main/postcode_ldz_full.csv"
    df = pd.read_csv(url)
    df["Postcode"] = df["Postcode"].astype(str).str.upper().str.replace(r"\s+", "", regex=True)
    return df

@st.cache_data
def lookup_postcode_to_ldz(postcode: str, _ldz_df: pd.DataFrame) -> str:
    """Clean cached postcode to LDZ lookup."""
    postcode = postcode.replace(" ", "").upper()
    
    # Try longest-to-shortest prefix match
    for length in [7, 6, 5, 4, 3]:
        if len(postcode) >= length:
            prefix = postcode[:length]
            match = _ldz_df[_ldz_df["Postcode"].str.startswith(prefix)]
            if not match.empty:
                return match.iloc[0]["LDZ"]
    
    return ""

def calculate_site_data(site_name: str, postcode: str, kwh: float, ldz_df: pd.DataFrame, flat_df: pd.DataFrame, carbon_offset_required: bool, uplifts: dict = None) -> dict:
    """Calculate all data for a single site."""
    if uplifts is None:
        uplifts = {}
    
    # Get LDZ
    ldz = lookup_postcode_to_ldz(postcode.strip(), ldz_df)
    
    site_data = {
        "Site Name": site_name,
        "Post Code": postcode,
        "Annual KWH": kwh
    }
    
    # Calculate for each duration
    for duration in [12, 24, 36]:
        # Get base rates
        base_sc, base_unit = get_base_rates(ldz, kwh, duration, carbon_offset_required, flat_df)
        
        # Get uplifts (default to 0)
        uplift_sc = uplifts.get(f"Standing Charge Uplift ({duration}m)", 0.0)
        uplift_unit = uplifts.get(f"Uplift Unit Rate ({duration}m)", 0.0)
        
        # Calculate final values
        final_sc = base_sc + uplift_sc
        final_unit = base_unit + uplift_unit
        sell_tac, margin = calculate_tac_and_margin(kwh, base_sc, base_unit, uplift_sc, uplift_unit)
        
        # Add to site data
        site_data.update({
            f"Base Standing Charge ({duration}m)": round(base_sc, 2),
            f"Base Unit Rate ({duration}m)": round(base_unit, 3),
            f"Standing Charge Uplift ({duration}m)": uplift_sc,
            f"Uplift Unit Rate ({duration}m)": uplift_unit,
            f"Final Standing Charge ({duration}m)": round(final_sc, 2),
            f"Final Unit Rate ({duration}m)": round(final_unit, 3),
            f"TAC £({duration}m)": sell_tac,
            f"Margin £({duration}m)": margin
        })
    
    return site_data

def recalculate_dataframe(df: pd.DataFrame, ldz_df: pd.DataFrame, flat_df: pd.DataFrame, carbon_offset_required: bool) -> pd.DataFrame:
    """Recalculate the entire dataframe - simplified approach."""
    updated_rows = []
    
    for _, row in df.iterrows():
        site_name = str(row.get("Site Name", "") or "").strip()
        postcode = str(row.get("Post Code", "") or "").strip()
        
        try:
            kwh = float(row.get("Annual KWH", 0) or 0)
        except (ValueError, TypeError):
            kwh = 0.0
        
        if not site_name or not postcode or kwh <= 0:
            # Keep empty/invalid rows as-is
            updated_rows.append(row.to_dict())
            continue
        
        # Get current uplifts from the row
        uplifts = {}
        for duration in [12, 24, 36]:
            try:
                uplifts[f"Standing Charge Uplift ({duration}m)"] = float(row.get(f"Standing Charge Uplift ({duration}m)", 0) or 0)
                uplifts[f"Uplift Unit Rate ({duration}m)"] = float(row.get(f"Uplift Unit Rate ({duration}m)", 0) or 0)
            except (ValueError, TypeError):
                uplifts[f"Standing Charge Uplift ({duration}m)"] = 0.0
                uplifts[f"Uplift Unit Rate ({duration}m)"] = 0.0
        
        # Calculate site data
        site_data = calculate_site_data(site_name, postcode, kwh, ldz_df, flat_df, carbon_offset_required, uplifts)
        updated_rows.append(site_data)
    
    return pd.DataFrame(updated_rows)

# -----------------------------------------
# UI Setup: Page settings and branding
# -----------------------------------------
st.set_page_config(page_title="Gas Quote Builder - Fixed", layout="wide")
st.title("Gas Multi-site Quote Builder – Fixed Version 🔧")

# Load logo
col1, col2 = st.columns([9, 1])
with col2:
    try:
        logo = Image.open("shared/DYCE-DARK BG.png")
        st.image(logo, width=120)
    except FileNotFoundError:
        st.warning("⚠️ Logo not found")

# -----------------------------------------
# Step 1: Load LDZ reference data (properly cached)
# -----------------------------------------
ldz_df = load_ldz_data_cached()

# -----------------------------------------
# Step 2: Upload Supplier Flat File
# -----------------------------------------
uploaded_file = st.file_uploader("Upload Supplier Flat File (XLSX)", type=["xlsx"])

# Initialize session state - CLEAN VERSION
if "quote_df" not in st.session_state:
    st.session_state.quote_df = pd.DataFrame()
if "needs_recalc" not in st.session_state:
    st.session_state.needs_recalc = False

if uploaded_file:
    flat_df = load_flat_file(uploaded_file)

    # -----------------------------------------
    # Step 3: Quote Configuration
    # -----------------------------------------
    st.subheader("Quote Configuration")
    
    customer_name = st.text_input("Customer Name")
    product_type = st.selectbox("Product Type", ["Standard Gas", "Carbon Off"])
    carbon_offset_required = product_type == "Carbon Off"
    output_filename = st.text_input("Output file name", value="dyce_quote")
    
    if st.button("🔄 Reset All Data"):
        st.session_state.quote_df = pd.DataFrame()
        st.session_state.needs_recalc = False
        st.rerun()

    # -----------------------------------------
    # Step 4: Add Sites (Simplified)
    # -----------------------------------------
    st.subheader("🔹 Add Sites to Quote")

    with st.form("add_site_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            site_name = st.text_input("Site Name")
        with col2:
            postcode = st.text_input("Post Code")
            try:
                consumption = float(st.text_input("Annual Consumption (kWh)", "0") or 0)
            except ValueError:
                consumption = 0.0
        
        submitted = st.form_submit_button("➕ Add Site")

    if submitted and site_name and postcode and consumption > 0:
        # Check if postcode is valid
        ldz = lookup_postcode_to_ldz(postcode.strip(), ldz_df)
        if not ldz:
            st.error(f"❌ Postcode '{postcode}' not found in LDZ database.")
        else:
            # Calculate new site data
            site_data = calculate_site_data(site_name.strip(), postcode.strip(), consumption, ldz_df, flat_df, carbon_offset_required)
            
            # Add to dataframe
            if st.session_state.quote_df.empty:
                st.session_state.quote_df = pd.DataFrame([site_data])
            else:
                st.session_state.quote_df = pd.concat([
                    st.session_state.quote_df,
                    pd.DataFrame([site_data])
                ], ignore_index=True)
            
            st.success(f"✅ Added {site_name}")

    # -----------------------------------------
    # Step 5: Manual Recalculation Button
    # -----------------------------------------
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Recalculate", disabled=st.session_state.quote_df.empty):
            st.session_state.needs_recalc = True

    # -----------------------------------------
    # Step 6: Data Editor (No Auto-Recalc)
    # -----------------------------------------
    if not st.session_state.quote_df.empty:
        st.subheader("Quote Data Editor")
        
        # Column configuration
        column_config = {
            "Site Name": st.column_config.TextColumn("Site Name"),
            "Post Code": st.column_config.TextColumn("Post Code"),
            "Annual KWH": st.column_config.NumberColumn("Annual KWh", min_value=0, step=1, format="%.0f")
        }

        for duration in [12, 24, 36]:
            column_config.update({
                f"Base Standing Charge ({duration}m)": st.column_config.NumberColumn(
                    f"Base SC ({duration}m)", format="%.2f", disabled=True
                ),
                f"Base Unit Rate ({duration}m)": st.column_config.NumberColumn(
                    f"Base Unit ({duration}m)", format="%.3f", disabled=True
                ),
                f"Standing Charge Uplift ({duration}m)": st.column_config.NumberColumn(
                    f"SC Uplift ({duration}m)", min_value=0, max_value=100.0, step=0.01, format="%.2f"
                ),
                f"Uplift Unit Rate ({duration}m)": st.column_config.NumberColumn(
                    f"Unit Uplift ({duration}m)", min_value=0, max_value=3.000, step=0.001, format="%.3f"
                ),
                f"Final Standing Charge ({duration}m)": st.column_config.NumberColumn(
                    f"Final SC ({duration}m)", format="%.2f", disabled=True
                ),
                f"Final Unit Rate ({duration}m)": st.column_config.NumberColumn(
                    f"Final Unit ({duration}m)", format="%.3f", disabled=True
                ),
                f"TAC £({duration}m)": st.column_config.NumberColumn(
                    f"TAC ({duration}m)", format="£%.2f", disabled=True
                ),
                f"Margin £({duration}m)": st.column_config.NumberColumn(
                    f"Margin ({duration}m)", format="£%.2f", disabled=True
                )
            })

        # Show data editor
        edited_df = st.data_editor(
            st.session_state.quote_df,
            use_container_width=True,
            num_rows="dynamic",
            hide_index=True,
            column_config=column_config,
            key="quote_editor"
        )

        # Update session state with edited data (but don't auto-recalculate)
        st.session_state.quote_df = edited_df

        # Perform recalculation if requested
        if st.session_state.needs_recalc:
            with st.spinner("Recalculating..."):
                st.session_state.quote_df = recalculate_dataframe(
                    edited_df, ldz_df, flat_df, carbon_offset_required
                )
                st.session_state.needs_recalc = False
                st.success("✅ Recalculation complete!")
                st.rerun()

        # -----------------------------------------
        # Step 7: Customer Quote Preview & Export
        # -----------------------------------------
        st.subheader("Customer Quote Preview")

        # Create customer-facing version
        preview_rows = []
        for _, row in st.session_state.quote_df.iterrows():
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
                    "Annual KWH": f"{kwh:,.0f}"
                }
                for duration in [12, 24, 36]:
                    sc = row.get(f'Final Standing Charge ({duration}m)', 0)
                    unit = row.get(f'Final Unit Rate ({duration}m)', 0)
                    tac = row.get(f'TAC £({duration}m)', 0)
                    
                    preview_data[f"Standing Charge ({duration}m)"] = f"{sc:.2f}p/day"
                    preview_data[f"Unit Rate ({duration}m)"] = f"{unit:.3f}p/kWh"
                    preview_data[f"Annual Cost ({duration}m)"] = f"£{tac:,.2f}"
                
                preview_rows.append(preview_data)

        if preview_rows:
            preview_df = pd.DataFrame(preview_rows)
            st.dataframe(preview_df, use_container_width=True, hide_index=True)
            
            # Export functionality
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                preview_df.to_excel(writer, index=False, sheet_name="Customer Quote")
                # Also export the full data for internal use
                st.session_state.quote_df.to_excel(writer, index=False, sheet_name="Internal Data")
            
            output.seek(0)

            st.download_button(
                label="📥 Download Quote (Excel)",
                data=output,
                file_name=f"{output_filename}_quote.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # Summary metrics
            total_sites = len(preview_rows)
            total_margin_12m = sum(row.get('Margin £(12m)', 0) for _, row in st.session_state.quote_df.iterrows())
            total_margin_24m = sum(row.get('Margin £(24m)', 0) for _, row in st.session_state.quote_df.iterrows())
            total_margin_36m = sum(row.get('Margin £(36m)', 0) for _, row in st.session_state.quote_df.iterrows())

            st.info(f"📊 **Quote Summary:** {total_sites} sites | Projected Margins: 12m: £{total_margin_12m:,.2f} | 24m: £{total_margin_24m:,.2f} | 36m: £{total_margin_36m:,.2f}")

    else:
        st.info("👆 Add sites above to start building your quote")

else:
    st.info("📁 Please upload a supplier flat file to begin creating quotes.")
