import streamlit as st
import pandas as pd
import io
import numpy as np

st.set_page_config(layout="wide")
st.title("NHH Pricing Tool with Manual Cost Allocation")

uploaded_file = st.file_uploader("Upload the Flat File (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.write("Flat file loaded successfully. Preview:")
        st.dataframe(df.head())
        
        # Data validation
        required_columns = ['Contract_Duration', 'Minimum_Annual_Consumption', 'Maximum_Annual_Consumption', 
                          'Green_Energy', 'Standing_Charge', 'Rate_Structure']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"Missing required columns: {missing_columns}")
            st.stop()
            
        # Check available rate structures
        available_structures = df['Rate_Structure'].unique()
        st.info(f"Available rate structures in data: {', '.join(available_structures)}")
        
        # Check available rate columns and their data
        rate_columns = ['Standard_Rate', 'Day_Rate', 'Night_Rate', 'Evening_And_Weekend_Rate']
        available_rates = {}
        for col in rate_columns:
            if col in df.columns and not df[col].isna().all():
                available_rates[col] = df[col].notna().sum()
        
        st.info(f"Available rate columns with data: {list(available_rates.keys())}")
        
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        st.stop()

    # Filter options
    green_option = st.selectbox("Select Tariff Type:", options=["Standard", "Green"])
    contract_duration = st.selectbox("Select Contract Duration (Months):", 
                                   options=sorted(df['Contract_Duration'].unique()))

    st.subheader("Manual Cost Allocation")

    total_cost_input = st.number_input("Enter Total Cost per Meter (£/year)", value=120.0, step=1.0)
    cost_split_slider = st.slider("Allocate Cost to Standing Charge (%)", min_value=0, max_value=100, value=50)

    cost_pence = total_cost_input * 100  # Convert £ to pence
    standing_pct = cost_split_slider / 100
    unit_pct = 1 - standing_pct

    # Dynamic consumption profile based on available rates
    st.subheader("Consumption Profile Split (%)")
    
    profile_splits = {}
    
    if 'Standard_Rate' in available_rates:
        profile_splits['Standard'] = st.slider("Standard Rate (%)", min_value=0, max_value=100, value=100)
    else:
        # Multi-rate structure
        col1, col2, col3 = st.columns(3)
        
        if 'Day_Rate' in available_rates:
            profile_splits['Day'] = col1.slider("Day (%)", min_value=0, max_value=100, value=70)
        if 'Night_Rate' in available_rates:
            profile_splits['Night'] = col2.slider("Night (%)", min_value=0, max_value=100, value=20)
        if 'Evening_And_Weekend_Rate' in available_rates:
            profile_splits['Evening_Weekend'] = col3.slider("Evening & Weekend (%)", min_value=0, max_value=100, value=10)

    profile_total = sum(profile_splits.values())
    st.markdown(f"**Total: {profile_total}%**")

    if profile_total != 100:
        st.error("The total profile split must equal 100%. Please adjust the sliders.")
        if st.button("Auto-normalize to 100%"):
            # This would require session state to persist the normalization
            st.info("Please adjust sliders manually to total 100%")
        st.stop()

    # Dynamic band creation based on actual data
    st.subheader("Consumption Bands")
    
    # Extract unique consumption ranges from the data
    consumption_ranges = df[['Minimum_Annual_Consumption', 'Maximum_Annual_Consumption']].drop_duplicates()
    consumption_ranges = consumption_ranges.sort_values('Minimum_Annual_Consumption')
    
    st.write("Available consumption bands in data:")
    st.dataframe(consumption_ranges.reset_index(drop=True))
    
    # Allow manual band definition or use data bands
    use_data_bands = st.checkbox("Use consumption bands from data", value=True)
    
    if use_data_bands:
        bands = []
        for _, row in consumption_ranges.iterrows():
            bands.append((int(row['Minimum_Annual_Consumption']), int(row['Maximum_Annual_Consumption'])))
    else:
        # Manual band definition (original logic)
        bands = [
            (1000, 3000), (3001, 12500), (12501, 26000), (26001, 100000),
            (100001, 175000), (175001, 225000), (225001, 300000)
        ]

    st.subheader("Uplifts per Consumption Band")
    
    uplift_inputs = []
    for idx, (min_val, max_val) in enumerate(bands):
        st.markdown(f"**Band {idx+1}: {min_val:,} – {max_val:,} kWh**")
        
        # Dynamic columns based on available rates
        num_cols = 1 + len(available_rates)  # +1 for standing charge
        cols = st.columns(num_cols)
        
        uplift_standing = cols[0].number_input(
            f"Standing Charge Uplift (p/day) - Band {idx+1}", 
            value=0.0, step=0.1, key=f"sc_{idx}")
        
        uplift_rates = {}
        col_idx = 1
        
        for rate_col in ['Standard_Rate', 'Day_Rate', 'Night_Rate', 'Evening_And_Weekend_Rate']:
            if rate_col in available_rates:
                rate_name = rate_col.replace('_Rate', '').replace('_', ' ')
                uplift_rates[rate_col] = cols[col_idx].number_input(
                    f"{rate_name} Uplift (p/kWh) - Band {idx+1}", 
                    value=0.0, step=0.1, key=f"{rate_col}_{idx}")
                col_idx += 1
        
        uplift_inputs.append({
            "min": min_val,
            "max": max_val,
            "uplift_standing": uplift_standing,
            "uplift_rates": uplift_rates
        })

    report_title = st.text_input("Enter Report Filename (without .xlsx):", value="nhh_price_book")

    if st.button("Generate Excel Price Book"):
        output_rows = []

        for band in uplift_inputs:
            # Improved filtering logic
            filtered = df[
                (df["Minimum_Annual_Consumption"] <= band["max"]) &
                (df["Maximum_Annual_Consumption"] >= band["min"]) &
                (df["Contract_Duration"] == contract_duration)
            ]
            
            # Handle green energy filtering with both boolean and string values
            if green_option == "Green":
                filtered = filtered[
                    (filtered["Green_Energy"] == True) | 
                    (filtered["Green_Energy"].astype(str).str.upper() == "TRUE") |
                    (filtered["Green_Energy"].astype(str).str.upper() == "YES")
                ]
            else:
                filtered = filtered[
                    (filtered["Green_Energy"] == False) | 
                    (filtered["Green_Energy"].astype(str).str.upper() == "FALSE") |
                    (filtered["Green_Energy"].astype(str).str.upper() == "NO")
                ]

            if filtered.empty:
                # Create N/A row
                row_data = {
                    "Band": f"{band['min']:,} – {band['max']:,}",
                    "Standing Charge (p/day)": "N/A",
                    "Total Annual Cost (£)": "N/A"
                }
                
                for rate_col in available_rates.keys():
                    rate_name = rate_col.replace('_Rate', '').replace('_', ' ') + " (p/kWh)"
                    row_data[rate_name] = "N/A"
                    
                output_rows.append(row_data)
            else:
                # Take the first matching row (consider adding logic to handle multiple matches)
                row = filtered.iloc[0]
                mid_consumption = (band['min'] + band['max']) / 2

                # Cost allocation
                allocated_standing = (cost_pence * standing_pct) / 365  # p/day
                allocated_unit = (cost_pence * unit_pct) / mid_consumption  # p/kWh

                # Calculate final rates
                final_standing = row["Standing_Charge"] + allocated_standing + band["uplift_standing"]
                
                final_rates = {}
                for rate_col in available_rates.keys():
                    base_rate = row[rate_col] if pd.notna(row[rate_col]) else 0
                    final_rate = base_rate + allocated_unit + band["uplift_rates"].get(rate_col, 0)
                    final_rates[rate_col] = final_rate

                # Calculate annual cost based on available rates and profile
                annual_unit_cost = 0
                
                if 'Standard_Rate' in final_rates:
                    annual_unit_cost = mid_consumption * final_rates['Standard_Rate'] / 100
                else:
                    # Multi-rate calculation
                    rate_mapping = {
                        'Day_Rate': profile_splits.get('Day', 0) / 100,
                        'Night_Rate': profile_splits.get('Night', 0) / 100,
                        'Evening_And_Weekend_Rate': profile_splits.get('Evening_Weekend', 0) / 100
                    }
                    
                    for rate_col, proportion in rate_mapping.items():
                        if rate_col in final_rates:
                            annual_unit_cost += mid_consumption * final_rates[rate_col] * proportion / 100

                annual_standing_cost = 365 * final_standing / 100
                total_annual_cost = annual_unit_cost + annual_standing_cost

                # Build output row
                row_data = {
                    "Band": f"{band['min']:,} – {band['max']:,}",
                    "Standing Charge (p/day)": round(final_standing, 4),
                    "Total Annual Cost (£)": round(total_annual_cost, 2)
                }
                
                for rate_col, final_rate in final_rates.items():
                    rate_name = rate_col.replace('_Rate', '').replace('_', ' ') + " (p/kWh)"
                    row_data[rate_name] = round(final_rate, 4)
                
                output_rows.append(row_data)

        result_df = pd.DataFrame(output_rows)

        st.success("Excel file prepared. Preview:")
        st.dataframe(result_df)

        # Create Excel file
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            result_df.to_excel(writer, index=False, sheet_name="Price Book")
            
            # Add a summary sheet with parameters used
            summary_data = {
                'Parameter': ['Contract Duration', 'Tariff Type', 'Total Cost per Meter', 
                            'Standing Charge Allocation', 'Unit Rate Allocation'] + 
                           [f'{k} Profile Split' for k in profile_splits.keys()],
                'Value': [f"{contract_duration} months", green_option, f"£{total_cost_input}", 
                         f"{cost_split_slider}%", f"{100-cost_split_slider}%"] + 
                        [f"{v}%" for v in profile_splits.values()]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, index=False, sheet_name="Parameters")

        processed_data = output.getvalue()

        st.download_button(
            label="Download Excel Price Book",
            data=processed_data,
            file_name=f"{report_title}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.warning("Please upload the flat file to start.")
