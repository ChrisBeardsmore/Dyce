# -----------------------------------------
# Deployment-Ready Gas Tool with Enhanced Input
# -----------------------------------------

import sys
import os
import io
import streamlit as st
import pandas as pd
from datetime import datetime, date

# Try to import PIL, with fallback
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    st.warning("PIL not available - logo display disabled")

# -----------------------------------------
# UI Setup
# -----------------------------------------
st.set_page_config(page_title="Direct Sales Gas Tool", layout="wide")
st.title("Direct Sales Gas Tool")

# Logo with error handling
col1, col2 = st.columns([8, 2])
with col2:
    if PIL_AVAILABLE:
        try:
            logo = Image.open("shared/DYCE-DARK BG.png")
            st.image(logo, width=180)
        except FileNotFoundError:
            st.write("⚡ DYCE Energy")  # Fallback
    else:
        st.write("⚡ DYCE Energy")  # Fallback

# -----------------------------------------
# Logic Module Imports with Fallbacks
# -----------------------------------------
try:
    # Fix: Add /apps to Python path
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", "apps")))
    
    from logic.ldz_lookup import load_ldz_data, match_postcode_to_ldz
    from logic.base_rate_lookup import get_base_rates
    from logic.tac_calculator import calculate_tac_and_margin
    from logic.flat_file_loader import load_flat_file
    
    LOGIC_MODULES_AVAILABLE = True
    
except ImportError as e:
    st.error(f"❌ Logic modules not found: {e}")
    st.error("Please ensure all logic modules are in the /apps/directgas/logic/ directory")
    LOGIC_MODULES_AVAILABLE = False
    
    # Create dummy functions for testing
    def load_ldz_data():
        return pd.DataFrame({"PostCode": ["AB1 1AA", "CD2 2BB"], "LDZ": ["EA", "WM"]})
    
    def match_postcode_to_ldz(postcode, ldz_df):
        return "EA"  # Dummy LDZ
    
    def get_base_rates(ldz, consumption, duration, carbon_offset, flat_df):
        return 25.0, 4.5  # Dummy rates
    
    def calculate_tac_and_margin(consumption, base_sc, base_unit, uplift_sc, uplift_unit):
        base_tac = (base_sc * 365 + base_unit * consumption) / 100
        sell_tac = ((base_sc + uplift_sc) * 365 + (base_unit + uplift_unit) * consumption) / 100
        margin = sell_tac - base_tac
        return round(sell_tac, 2), round(margin, 2)
    
    def load_flat_file(uploaded_file):
        return pd.DataFrame()  # Dummy flat file

# -----------------------------------------
# Initialize Data
# -----------------------------------------
if LOGIC_MODULES_AVAILABLE:
    try:
        ldz_df = load_ldz_data()
        st.sidebar.success(f"✅ LDZ data loaded: {len(ldz_df)} postcodes")
    except Exception as e:
        st.sidebar.error(f"❌ Error loading LDZ data: {e}")
        ldz_df = pd.DataFrame()
else:
    ldz_df = load_ldz_data()  # Use dummy function

# -----------------------------------------
# File Upload
# -----------------------------------------
uploaded_file = st.file_uploader("Upload Supplier Flat File (XLSX)", type=["xlsx"])

if uploaded_file:
    try:
        flat_df = load_flat_file(uploaded_file)
        st.sidebar.success(f"✅ Flat file loaded: {len(flat_df)} rows")
    except Exception as e:
        st.sidebar.error(f"❌ Error loading flat file: {e}")
        flat_df = pd.DataFrame()

    # -----------------------------------------
    # Quote Configuration
    # -----------------------------------------
    st.subheader("Quote Details")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        customer_name = st.text_input("Customer Name")
    with col2:
        contract_duration = st.selectbox("Contract Duration (months)", options=[12, 24, 36], index=1)
    with col3:
        product_type = st.selectbox("Product Type", ["Standard Gas", "Carbon Off"])
    with col4:
        contract_start_date = st.date_input("Contract Start Date", value=date.today())
    
    carbon_offset_required = product_type == "Carbon Off"
    output_filename = st.text_input("Output file name (without .xlsx)", value="dyce_gas_quote")

    # Clear session button
    if st.button("🔄 Reset All Data"):
        st.session_state.clear()
        st.rerun()

    # -----------------------------------------
    # Multi-site Input
    # -----------------------------------------
    st.subheader("Multi-site Input")
    
    input_rows = []
    num_sites = st.number_input("Number of Sites", min_value=1, max_value=20, value=5, step=1)
    
    for i in range(num_sites):
        with st.expander(f"🏢 Site {i+1}", expanded=(i < 3)):
            
            # Site input columns
            cols = st.columns([1.2, 1.2, 1, 1, 1])
            
            site_name = cols[0].text_input("Site Name", key=f"site_{i}")
            postcode = cols[1].text_input("Post Code", key=f"postcode_{i}")
            consumption = cols[2].number_input("Annual Consumption (kWh)", 
                                             min_value=0, value=0, step=1000, key=f"consumption_{i}")
            site_reference = cols[3].text_input("Site Reference (optional)", key=f"ref_{i}")
            preferred_term = cols[4].selectbox("Preferred Term", 
                                             options=["Show All", "12 months", "24 months", "36 months"], 
                                             key=f"term_{i}")
            
            # Only process if minimum fields provided
            if site_name and postcode and consumption > 0:
                
                try:
                    # LDZ Lookup
                    ldz = match_postcode_to_ldz(postcode.strip(), ldz_df)
                    
                    if not ldz:
                        st.error(f"❌ Postcode '{postcode}' not found in LDZ database")
                        continue
                    else:
                        st.success(f"✅ Found LDZ: {ldz}")
                    
                    # Determine contract terms to show
                    if preferred_term == "Show All":
                        terms_to_show = [12, 24, 36]
                    else:
                        term_months = int(preferred_term.split()[0])
                        terms_to_show = [term_months]
                    
                    # Calculate rates
                    st.write("**Base Rates from Supplier:**")
                    rate_cols = st.columns(len(terms_to_show))
                    
                    site_data = {
                        "Customer": customer_name,
                        "Site": site_name,
                        "Post Code": postcode,
                        "LDZ": ldz,
                        "Annual Consumption (kWh)": consumption,
                        "Site Reference": site_reference,
                        "Contract Start Date": contract_start_date.strftime("%d/%m/%Y")
                    }
                    
                    for idx, duration in enumerate(terms_to_show):
                        with rate_cols[idx]:
                            st.write(f"**{duration} Month Contract:**")
                            
                            try:
                                # Get base rates
                                base_sc, base_unit = get_base_rates(ldz, consumption, duration, carbon_offset_required, flat_df)
                                base_tac = round((base_sc * 365 + base_unit * consumption) / 100, 2)
                                
                                # Display base rates
                                st.write(f"Standing Charge: {base_sc:.2f}p/day")
                                st.write(f"Unit Rate: {base_unit:.3f}p/kWh")
                                st.write(f"Annual Cost: £{base_tac:.2f}")
                                
                                # Agent uplift inputs
                                st.write("**Agent Uplifts:**")
                                uplift_sc = st.number_input(
                                    f"SC Uplift (p/day)", 
                                    min_value=0.0, max_value=100.0, step=0.01, value=0.0,
                                    key=f"uplift_sc_{i}_{duration}",
                                    help="Additional standing charge margin"
                                )
                                uplift_unit = st.number_input(
                                    f"Unit Uplift (p/kWh)", 
                                    min_value=0.0, max_value=3.0, step=0.001, value=0.0,
                                    key=f"uplift_unit_{i}_{duration}",
                                    help="Additional unit rate margin"
                                )
                                
                                # Calculate final rates
                                final_sc = base_sc + uplift_sc
                                final_unit = base_unit + uplift_unit
                                sell_tac, margin = calculate_tac_and_margin(consumption, base_sc, base_unit, uplift_sc, uplift_unit)
                                
                                # Display final rates
                                if uplift_sc > 0 or uplift_unit > 0:
                                    st.write("**Final Sell Rates:**")
                                    st.write(f"Sell SC: {final_sc:.2f}p/day")
                                    st.write(f"Sell Unit: {final_unit:.3f}p/kWh")
                                    st.write(f"**Sell TAC: £{sell_tac:.2f}**")
                                    st.write(f"**Margin: £{margin:.2f}**")
                                
                                # Add to site data
                                site_data.update({
                                    f"Base_SC_{duration}m": f"{base_sc:.2f}p",
                                    f"Base_Unit_{duration}m": f"{base_unit:.3f}p",
                                    f"Base_TAC_{duration}m": f"£{base_tac:.2f}",
                                    f"Uplift_SC_{duration}m": f"{uplift_sc:.2f}p",
                                    f"Uplift_Unit_{duration}m": f"{uplift_unit:.3f}p",
                                    f"Sell_SC_{duration}m": f"{final_sc:.2f}p",
                                    f"Sell_Unit_{duration}m": f"{final_unit:.3f}p",
                                    f"Sell_TAC_{duration}m": f"£{sell_tac:.2f}",
                                    f"Margin_{duration}m": f"£{margin:.2f}"
                                })
                                
                            except Exception as e:
                                st.error(f"❌ Error calculating rates for {duration}m: {e}")
                    
                    # Add to results
                    input_rows.append(site_data)
                    st.markdown("---")
                    
                except Exception as e:
                    st.error(f"❌ Error processing site {i+1}: {e}")

    # -----------------------------------------
    # Results & Export
    # -----------------------------------------
    if input_rows:
        st.subheader("Quote Summary")
        
        try:
            # Create results DataFrame
            results_df = pd.DataFrame(input_rows)
            st.dataframe(results_df, use_container_width=True, hide_index=True)
            
            # Customer quote (clean version)
            st.subheader("Customer Quote Preview")
            customer_columns = ["Customer", "Site", "Post Code", "Annual Consumption (kWh)", "Contract Start Date"]
            
            # Add available rate columns
            for duration in [12, 24, 36]:
                if any(f"Sell_SC_{duration}m" in row for row in input_rows):
                    customer_columns.extend([
                        f"Sell_SC_{duration}m", 
                        f"Sell_Unit_{duration}m", 
                        f"Sell_TAC_{duration}m"
                    ])
            
            customer_df = results_df[[col for col in customer_columns if col in results_df.columns]].copy()
            st.dataframe(customer_df, use_container_width=True, hide_index=True)
            
            # Download buttons
            col1, col2 = st.columns(2)
            
            with col1:
                # Full data download
                output_full = io.BytesIO()
                with pd.ExcelWriter(output_full, engine="openpyxl") as writer:
                    results_df.to_excel(writer, index=False, sheet_name="Full_Quote_Data")
                output_full.seek(0)
                
                st.download_button(
                    label="📊 Download Full Quote Data",
                    data=output_full,
                    file_name=f"{output_filename}_full.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            with col2:
                # Customer quote download
                output_customer = io.BytesIO()
                with pd.ExcelWriter(output_customer, engine="openpyxl") as writer:
                    customer_df.to_excel(writer, index=False, sheet_name="Customer_Quote")
                output_customer.seek(0)
                
                st.download_button(
                    label="📋 Download Customer Quote",
                    data=output_customer,
                    file_name=f"{output_filename}_customer.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            # Quick stats
            st.subheader("Quote Statistics")
            stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
            
            with stats_col1:
                st.metric("Total Sites", len(input_rows))
            with stats_col2:
                total_consumption = sum(row["Annual Consumption (kWh)"] for row in input_rows)
                st.metric("Total Consumption", f"{total_consumption:,} kWh")
            with stats_col3:
                # Calculate total margin
                total_margin = 0
                for row in input_rows:
                    for key, value in row.items():
                        if key.startswith("Margin_") and isinstance(value, str) and value.startswith("£"):
                            try:
                                total_margin += float(value.replace("£", ""))
                            except:
                                pass
                st.metric("Total Annual Margin", f"£{total_margin:.2f}")
            with stats_col4:
                st.metric("Contract Start", contract_start_date.strftime("%d/%m/%Y"))
                
        except Exception as e:
            st.error(f"❌ Error generating results: {e}")
            st.write("Debug info:", str(e))

    else:
        st.info("👆 Enter site details above to generate quotes")

else:
    st.info("📁 Please upload a supplier flat file to begin creating quotes.")

# -----------------------------------------
# Deployment Info (can remove for production)
# -----------------------------------------
if st.sidebar.checkbox("Show Deployment Info"):
    st.sidebar.subheader("🚀 Deployment Status")
    st.sidebar.write(f"Logic Modules: {'✅' if LOGIC_MODULES_AVAILABLE else '❌'}")
    st.sidebar.write(f"PIL/Logo: {'✅' if PIL_AVAILABLE else '❌'}")
    st.sidebar.write(f"Python Path: {sys.path}")
