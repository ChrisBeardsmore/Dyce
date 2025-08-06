# -----------------------------------------
# File: app_robust_network.py - ROBUST NETWORK HANDLING
# Purpose: Handle network connections and LDZ lookups robustly
# -----------------------------------------

import sys
import os
import io
import streamlit as st
import pandas as pd
from PIL import Image
import traceback

# Fix: Add /apps to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", "apps")))

try:
    # Import ORIGINAL logic modules
    from directgas.logic.base_rate_lookup import get_base_rates
    from directgas.logic.tac_calculator import calculate_tac_and_margin
    from directgas.logic.flat_file_loader import load_flat_file
    from directgas.logic.input_setup import create_input_dataframe
    st.success("✅ Core modules imported successfully")
except Exception as e:
    st.error(f"❌ Import error: {str(e)}")
    st.stop()

# -----------------------------------------
# ROBUST LDZ FUNCTIONS - HANDLE NETWORK ISSUES
# -----------------------------------------

@st.cache_data
def robust_load_ldz_data():
    """Load LDZ data from local file."""
    try:
        # Use the local file path
        file_path = "apps/directgas/data/postcode_ldz_full.csv"
        
        with st.spinner("Loading LDZ reference data..."):
            df = pd.read_csv(file_path)
            
        if df.empty:
            st.error("❌ LDZ data file is empty")
            return pd.DataFrame()
            
        # Clean postcode column
        df["Postcode"] = df["Postcode"].astype(str).str.upper().str.replace(r"\s+", "", regex=True)
        st.success(f"✅ LDZ data loaded: {len(df):,} postcodes")
        return df
        
    except FileNotFoundError:
        st.error(f"❌ LDZ file not found at: {file_path}")
        st.error("Please ensure the postcode_ldz_full.csv file is in the correct location.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Failed to load LDZ data: {str(e)}")
        return pd.DataFrame()

def robust_postcode_to_ldz(postcode: str, ldz_df: pd.DataFrame) -> str:
    """Clean postcode to LDZ lookup without debug spam."""
    try:
        if ldz_df.empty:
            return ""
            
        postcode = str(postcode).replace(" ", "").upper().strip()
        if not postcode:
            return ""
        
        # Try longest-to-shortest prefix match (NO DEBUG OUTPUT)
        for length in [7, 6, 5, 4, 3]:
            if len(postcode) >= length:
                prefix = postcode[:length]
                match = ldz_df[ldz_df["Postcode"].str.startswith(prefix)]
                if not match.empty:
                    return match.iloc[0]["LDZ"]
        
        return ""  # No match found
        
    except Exception as e:
        st.error(f"❌ LDZ lookup error: {str(e)}")
        return ""

def calculate_site_data_robust(site_name: str, postcode: str, kwh: float, ldz_df: pd.DataFrame, flat_df: pd.DataFrame, carbon_offset_required: bool, uplifts: dict = None) -> dict:
    """Calculate site data with robust error handling."""
    try:
        if uplifts is None:
            uplifts = {}
        
        # Use robust LDZ lookup (no debug output)
        ldz = robust_postcode_to_ldz(postcode.strip(), ldz_df)
        if not ldz:
            st.error(f"❌ Could not find LDZ for postcode: {postcode}")
            return {}
        
        site_data = {
            "MPXN": site_name,
            "Post Code": postcode,
            "Annual Consumption KWh": kwh
        }
        
        # Calculate for each duration
        for duration in [12, 24, 36]:
            try:
                # Use ORIGINAL get_base_rates function
                base_sc, base_unit = get_base_rates(ldz, kwh, duration, carbon_offset_required, flat_df)
                
                # Get uplifts (default to 0)
                uplift_sc = uplifts.get(f"Standing Charge (uplift {duration}m)", 0.0)
                uplift_unit = uplifts.get(f"Unit Rate (Uplift {duration}m)", 0.0)
                
                # Calculate final values
                final_sc = base_sc + uplift_sc
                final_unit = base_unit + uplift_unit
                
                # Use ORIGINAL calculate_tac_and_margin function
                sell_tac, margin = calculate_tac_and_margin(kwh, base_sc, base_unit, uplift_sc, uplift_unit)
                
                # Add to site data
                site_data.update({
                    f"Standing Charge (Base {duration}m)": round(base_sc, 2),
                    f"Unit Rate (Base {duration}m)": round(base_unit, 3),
                    f"Standing Charge (uplift {duration}m)": uplift_sc,
                    f"Unit Rate (Uplift {duration}m)": uplift_unit,
                    f"Sell Standing Charge ({duration}m)": round(final_sc, 2),
                    f"Sell Unit Rate ({duration}m)": round(final_unit, 3),
                    f"TAC ({duration}m)": sell_tac,
                    f"Margin £({duration}m)": margin
                })
                
            except Exception as duration_error:
                st.error(f"❌ Error calculating {duration}m rates: {str(duration_error)}")
                # Set default values for this duration
                site_data.update({
                    f"Standing Charge (Base {duration}m)": 0.0,
                    f"Unit Rate (Base {duration}m)": 0.0,
                    f"Standing Charge (uplift {duration}m)": 0.0,
                    f"Unit Rate (Uplift {duration}m)": 0.0,
                    f"Sell Standing Charge ({duration}m)": 0.0,
                    f"Sell Unit Rate ({duration}m)": 0.0,
                    f"TAC ({duration}m)": 0.0,
                    f"Margin £({duration}m)": 0.0
                })
        
        return site_data
        
    except Exception as e:
        st.error(f"❌ Site calculation error: {str(e)}")
        return {}

def recalculate_dataframe_robust(df: pd.DataFrame, ldz_df: pd.DataFrame, flat_df: pd.DataFrame, carbon_offset_required: bool) -> pd.DataFrame:
    """Recalculate with robust error handling."""
    updated_rows = []
    
    progress_bar = st.progress(0)
    total_rows = len(df)
    
    for idx, row in df.iterrows():
        progress_bar.progress((idx + 1) / total_rows)
        
        site_name = str(row.get("MPXN", "") or "").strip()
        postcode = str(row.get("Post Code", "") or "").strip()
        
        try:
            kwh = float(row.get("Annual Consumption KWh", 0) or 0)
        except (ValueError, TypeError):
            kwh = 0.0
        
        if not site_name or not postcode or kwh <= 0:
            updated_rows.append(row.to_dict())
            continue
        
        # Get current uplifts from the row
        uplifts = {}
        for duration in [12, 24, 36]:
            try:
                uplifts[f"Standing Charge (uplift {duration}m)"] = float(row.get(f"Standing Charge (uplift {duration}m)", 0) or 0)
                uplifts[f"Unit Rate (Uplift {duration}m)"] = float(row.get(f"Unit Rate (Uplift {duration}m)", 0) or 0)
            except (ValueError, TypeError):
                uplifts[f"Standing Charge (uplift {duration}m)"] = 0.0
                uplifts[f"Unit Rate (Uplift {duration}m)"] = 0.0
        
        # Calculate site data
        site_data = calculate_site_data_robust(site_name, postcode, kwh, ldz_df, flat_df, carbon_offset_required, uplifts)
        if site_data:
            updated_rows.append(site_data)
        else:
            updated_rows.append(row.to_dict())
    
    progress_bar.empty()
    return pd.DataFrame(updated_rows)

# -----------------------------------------
# UI Setup: Page settings and branding
# -----------------------------------------
st.set_page_config(page_title="Gas Quote Builder - Robust Network", layout="wide")
st.title("Gas Multi-site Quote Builder – Robust Network Version 🌐")

# Load logo
col1, col2 = st.columns([9, 1])
with col2:
    try:
        logo = Image.open("shared/DYCE-DARK BG.png")
        st.image(logo, width=120)
    except FileNotFoundError:
        st.warning("⚠️ Logo not found")

# Show connection status
st.sidebar.header("System Status")

# -----------------------------------------
# Step 1: Load LDZ reference data with robust handling
# -----------------------------------------
st.subheader("Step 1: Loading Reference Data")

ldz_df = robust_load_ldz_data()
if ldz_df.empty:
    st.error("❌ Cannot proceed without LDZ reference data")
    st.info("💡 This requires an internet connection to load postcode mappings")
    st.stop()
else:
    st.sidebar.success("✅ LDZ Data Loaded")

# -----------------------------------------
# Step 2: Upload Supplier Flat File
# -----------------------------------------
st.subheader("Step 2: Upload Supplier Data")
uploaded_file = st.file_uploader("Upload Supplier Flat File (XLSX)", type=["xlsx"])

# Initialize session state
if "quote_df" not in st.session_state:
    st.session_state.quote_df = pd.DataFrame()
if "needs_recalc" not in st.session_state:
    st.session_state.needs_recalc = False

if uploaded_file:
    try:
        flat_df = load_flat_file(uploaded_file)
        st.success(f"✅ Flat file loaded: {len(flat_df):,} pricing rows")
        st.sidebar.success("✅ Supplier Data Loaded")
        
    except Exception as e:
        st.error(f"❌ Error loading flat file: {str(e)}")
        st.stop()

    # -----------------------------------------
    # Step 3: Quote Configuration
    # -----------------------------------------
    st.subheader("Step 3: Quote Setup")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        customer_name = st.text_input("Customer Name")
    with col2:
        product_type = st.selectbox("Product Type", ["Standard Gas", "Carbon Off"])
        carbon_offset_required = product_type == "Carbon Off"
    with col3:
        output_filename = st.text_input("Output filename", value="dyce_quote")
    
    if st.button("🔄 Reset All Data"):
        st.session_state.quote_df = pd.DataFrame()
        st.session_state.needs_recalc = False
        st.rerun()

    # -----------------------------------------
    # Step 4: Add Sites
    # -----------------------------------------
    st.subheader("Step 4: Add Sites")

    with st.form("add_site_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            site_name = st.text_input("MPXN")
        with col2:
            postcode = st.text_input("Post Code")
        with col3:
            try:
                consumption = float(st.text_input("Annual Consumption (kWh)", "0") or 0)
            except ValueError:
                consumption = 0.0
        
        submitted = st.form_submit_button("➕ Add Site")

    if submitted and site_name and postcode and consumption > 0:
        with st.spinner(f"Adding {site_name}..."):
            try:
                site_data = calculate_site_data_robust(
                    site_name.strip(), 
                    postcode.strip(), 
                    consumption, 
                    ldz_df, 
                    flat_df, 
                    carbon_offset_required
                )
                
                if site_data:
                    if st.session_state.quote_df.empty:
                        st.session_state.quote_df = pd.DataFrame([site_data])
                    else:
                        st.session_state.quote_df = pd.concat([
                            st.session_state.quote_df,
                            pd.DataFrame([site_data])
                        ], ignore_index=True)
                    
                    st.success(f"✅ Added {site_name}")
                else:
                    st.error("❌ Failed to add site")
                    
            except Exception as e:
                st.error(f"❌ Error adding site: {str(e)}")

    # -----------------------------------------
    # Step 5: Data Editor & Recalculation
    # -----------------------------------------
    if not st.session_state.quote_df.empty:
        st.subheader("Step 5: Quote Editor")
        
        # Show current site count
        st.info(f"📊 Current quote: {len(st.session_state.quote_df)} sites")
        
        # Manual recalculation
        if st.button("🔄 Recalculate All Sites"):
            st.session_state.needs_recalc = True

        # Column configuration for new headers
        column_config = {
            "MPXN": st.column_config.TextColumn("MPXN"),
            "Post Code": st.column_config.TextColumn("Post Code"),
            "Annual Consumption KWh": st.column_config.NumberColumn("Annual Consumption KWh", min_value=0, step=1, format="%.0f")
        }

        for duration in [12, 24, 36]:
            column_config.update({
                f"Standing Charge (Base {duration}m)": st.column_config.NumberColumn(
                    f"Standing Charge (Base {duration}m)", format="%.2f", disabled=True
                ),
                f"Unit Rate (Base {duration}m)": st.column_config.NumberColumn(
                    f"Unit Rate (Base {duration}m)", format="%.3f", disabled=True
                ),
                f"Standing Charge (uplift {duration}m)": st.column_config.NumberColumn(
                    f"Standing Charge (uplift {duration}m)", min_value=0, max_value=100.0, step=0.01, format="%.2f"
                ),
                f"Unit Rate (Uplift {duration}m)": st.column_config.NumberColumn(
                    f"Unit Rate (Uplift {duration}m)", min_value=0, max_value=3.000, step=0.001, format="%.3f"
                ),
                f"Sell Standing Charge ({duration}m)": st.column_config.NumberColumn(
                    f"Sell Standing Charge ({duration}m)", format="%.2f", disabled=True
                ),
                f"Sell Unit Rate ({duration}m)": st.column_config.NumberColumn(
                    f"Sell Unit Rate ({duration}m)", format="%.3f", disabled=True
                ),
                f"TAC ({duration}m)": st.column_config.NumberColumn(
                    f"TAC ({duration}m)", format="£%.2f", disabled=True
                ),
                f"Margin £({duration}m)": st.column_config.NumberColumn(
                    f"Margin £({duration}m)", format="£%.2f", disabled=True
                )
            })

        # Data editor
        edited_df = st.data_editor(
            st.session_state.quote_df,
            use_container_width=True,
            num_rows="dynamic",
            hide_index=True,
            column_config=column_config,
            key="quote_editor"
        )

        # Update session state
        st.session_state.quote_df = edited_df

        # Perform recalculation if requested
        if st.session_state.needs_recalc:
            with st.spinner("Recalculating all sites..."):
                st.session_state.quote_df = recalculate_dataframe_robust(
                    edited_df, ldz_df, flat_df, carbon_offset_required
                )
                st.session_state.needs_recalc = False
                st.success("✅ Recalculation complete!")
                st.rerun()

        # -----------------------------------------
        # Step 6: Export
        # -----------------------------------------
        st.subheader("Step 6: Export Quote")

        if st.button("📥 Generate Export"):
            try:
                # Create customer preview
                preview_rows = []
                for _, row in st.session_state.quote_df.iterrows():
                    site = str(row.get("MPXN", "") or "").strip()
                    postcode = str(row.get("Post Code", "") or "").strip()
                    try:
                        kwh = float(row.get("Annual Consumption KWh", 0) or 0)
                    except (ValueError, TypeError):
                        kwh = 0.0
                    
                    if site and postcode and kwh > 0:
                        preview_data = {
                            "MPXN": site,
                            "Post Code": postcode, 
                            "Annual Consumption KWh": f"{kwh:,.0f}"
                        }
                        for duration in [12, 24, 36]:
                            sc = row.get(f'Sell Standing Charge ({duration}m)', 0)
                            unit = row.get(f'Sell Unit Rate ({duration}m)', 0)
                            tac = row.get(f'TAC ({duration}m)', 0)
                            
                            preview_data[f"Standing Charge ({duration}m)"] = f"{sc:.2f}p/day"
                            preview_data[f"Unit Rate ({duration}m)"] = f"{unit:.3f}p/kWh"
                            preview_data[f"Annual Cost ({duration}m)"] = f"£{tac:,.2f}"
                        
                        preview_rows.append(preview_data)

                if preview_rows:
                    preview_df = pd.DataFrame(preview_rows)
                    st.success(f"✅ Ready to export {len(preview_rows)} sites")
                    
                    # Export
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        preview_df.to_excel(writer, index=False, sheet_name="Customer Quote")
                        st.session_state.quote_df.to_excel(writer, index=False, sheet_name="Internal Data")
                    
                    output.seek(0)

                    st.download_button(
                        label="📥 Download Excel File",
                        data=output,
                        file_name=f"{output_filename}_quote.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                    # Summary
                    total_margin_12m = sum(row.get('Margin £(12m)', 0) for _, row in st.session_state.quote_df.iterrows() if pd.notna(row.get('Margin £(12m)', 0)))
                    total_margin_24m = sum(row.get('Margin £(24m)', 0) for _, row in st.session_state.quote_df.iterrows() if pd.notna(row.get('Margin £(24m)', 0)))
                    total_margin_36m = sum(row.get('Margin £(36m)', 0) for _, row in st.session_state.quote_df.iterrows() if pd.notna(row.get('Margin £(36m)', 0)))

                    st.info(f"📊 **Quote Summary:** {len(preview_rows)} sites | Margins: 12m: £{total_margin_12m:,.2f} | 24m: £{total_margin_24m:,.2f} | 36m: £{total_margin_36m:,.2f}")
                
            except Exception as e:
                st.error(f"❌ Export error: {str(e)}")

    else:
        st.info("👆 Add sites above to start building your quote")

else:
    st.info("📁 Please upload a supplier flat file to begin")
    st.sidebar.warning("⚠️ Awaiting Supplier Data")
