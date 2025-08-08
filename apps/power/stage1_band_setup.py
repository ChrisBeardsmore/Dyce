import streamlit as st
import pandas as pd
import io

st.set_page_config(layout="wide")
st.title("NHH Pricing Tool – Margin Sculptor")

# --- STEP 1: Upload Flat File ---
st.markdown("### 🔳 **Step 1: Upload Electricity Flat File (.xlsx)**")

uploaded_file = st.file_uploader("Upload the pricing flat file", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        st.success("File uploaded successfully. Preview below:")
        st.dataframe(df.head())

        # Basic validation
        required_cols = [
            'Contract_Duration', 'Minimum_Annual_Consumption', 'Maximum_Annual_Consumption',
            'Standing_Charge', 'Standard_Rate', 'Day_Rate', 'Night_Rate', 'Evening_And_Weekend_Rate', 'Green_Energy'
        ]
        if not all(col in df.columns for col in required_cols):
            st.error("One or more required columns are missing from the flat file.")
            st.stop()

    except Exception as e:
        st.error(f"Error reading file: {e}")
        st.stop()

    # --- STEP 2: Define Custom Consumption Bands ---
    st.markdown("### 🔳 **Step 2: Define Custom Consumption Bands**")

    if "num_bands" not in st.session_state:
        st.session_state["num_bands"] = 5

    def update_band_count():
        st.session_state["num_bands"] = st.session_state["band_input"]

    st.number_input(
        "Number of Bands",
        min_value=1,
        max_value=10,
        value=st.session_state["num_bands"],
        key="band_input",
        on_change=update_band_count
    )

    custom_bands = []
    for i in range(st.session_state["num_bands"]):
        st.markdown(f"**Band {i+1}**")
        cols = st.columns(2)
        min_kwh = cols[0].number_input(f"Min kWh – Band {i+1}", key=f"min_{i}", min_value=0)
        max_kwh = cols[1].number_input(f"Max kWh – Band {i+1}", key=f"max_{i}", min_value=min_kwh + 1)
        custom_bands.append((min_kwh, max_kwh))

    # --- STEP 3: Recovery and Margin Settings ---
    st.markdown("### 🔳 **Step 3: Define Recovery & Margin Targets**")

    recovery_cost = st.number_input("Cost to Recover per Meter (£/year)", value=100.0, step=5.0)

    margin_type = st.selectbox("Margin Type", options=["£ per meter", "p/kWh"])
    if margin_type == "£ per meter":
        margin_value = st.number_input("Margin (£/year)", value=40.0, step=5.0)
    else:
        margin_value = st.number_input("Margin (p/kWh)", value=2.0, step=0.1)

    # --- STEP 4: Price Generation Preview ---
    st.markdown("### 🔳 **Step 4: Generate Price Book**")

    contract_duration = st.selectbox("Contract Duration (Months)", sorted(df['Contract_Duration'].unique()))
    green_option = st.selectbox("Tariff Type", ["Standard", "Green"])
    report_title = st.text_input("Output Filename (no extension)", value="nhh_price_book")

    if st.button("Generate Pricing"):
        results = []
        for min_kwh, max_kwh in custom_bands:
            band_df = df[
                (df['Minimum_Annual_Consumption'] <= max_kwh) &
                (df['Maximum_Annual_Consumption'] >= min_kwh) &
                (df['Contract_Duration'] == contract_duration)
            ]

            if green_option == "Green":
                band_df = band_df[df['Green_Energy'].astype(str).str.upper().isin(["TRUE", "YES"])]
            else:
                band_df = band_df[df['Green_Energy'].astype(str).str.upper().isin(["FALSE", "NO"])]

            if band_df.empty:
                results.append({
                    "Band": f"{min_kwh:,} – {max_kwh:,}",
                    "Standing Charge (p/day)": "N/A",
                    "Standard Rate (p/kWh)": "N/A",
                    "Total Annual Cost (£)": "N/A"
                })
                continue

            row = band_df.iloc[0]
            mid_kwh = (min_kwh + max_kwh) / 2

            total_cost_pence = (recovery_cost + (margin_value if margin_type == "£ per meter" else (margin_value * mid_kwh / 100))) * 100

            # Default 50/50 cost split
            standing = round((total_cost_pence * 0.5) / 365, 4)
            unit = round((total_cost_pence * 0.5) / mid_kwh, 4)

            results.append({
                "Band": f"{min_kwh:,} – {max_kwh:,}",
                "Standing Charge (p/day)": round(row['Standing_Charge'] + standing, 4),
                "Standard Rate (p/kWh)": round(row['Standard_Rate'] + unit, 4),
                "Total Annual Cost (£)": round(recovery_cost + (margin_value if margin_type == "£ per meter" else (margin_value * mid_kwh / 100)), 2)
            })

        result_df = pd.DataFrame(results)
        st.success("Price Book Ready:")
        st.dataframe(result_df)

        # Export to Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            result_df.to_excel(writer, index=False, sheet_name="Price Book")
        st.download_button(
            label="Download Excel File",
            data=output.getvalue(),
            file_name=f"{report_title}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Please upload the pricing flat file to begin.")
