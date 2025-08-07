import streamlit as st
import pandas as pd
import io
from datetime import datetime
from utils.llf import load_llf_mapping, get_llf_band

st.set_page_config(page_title="Direct Sales LLF Multi-tool", layout="wide")
st.title("Direct Sales LLF Multi-tool")

# Load LLF Mapping Table from shared inputs folder
llf_mapping = load_llf_mapping()

# --- File Upload ---
uploaded_file = st.file_uploader("Upload Electricity Flat File (.xlsx)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    st.subheader("Quote Details")
    customer_name = st.text_input("Customer Name")
    contract_duration = st.selectbox("Contract Duration (months)", options=[12, 24, 36])
    green_energy = st.radio("Green Energy", ["False", "True"])
    contract_start_date = st.date_input("Contract Start Date", value=datetime.today())

    output_filename = st.text_input("Output file name (without .xlsx)", value="llf_multi_site_quote")

    st.subheader("Multi-site Input")
    input_rows = []

    for i in range(10):
        st.markdown(f"### Site {i+1}")
        cols = st.columns([1.2, 1.2, 1, 1, 1])

        site = cols[0].text_input("Site Name", key=f"site_{i}")
        dno_id = cols[1].text_input("DNO ID", key=f"dno_{i}")
        llf_code = cols[2].text_input("LLF Code", key=f"llf_{i}")
        consumption = cols[3].number_input("Annual Consumption (kWh)", min_value=0, value=0, step=1000, key=f"consumption_{i}")
        rate_structure = cols[4].selectbox("Rate Structure", options=["DayNight", "Standard"], key=f"rate_struct_{i}")

        llf_band = get_llf_band(llf_mapping, dno_id, llf_code)

        if llf_band:
            st.write(f"LLF Band for Site {i+1}: {llf_band}")

            matched = df[
                (df["DNO_ID"].astype(str) == str(dno_id)) &
                (df["LLF_Band"] == llf_band) &
                (df["Contract_Duration"] == contract_duration) &
                (df["Green_Energy"].astype(str).str.upper() == green_energy.upper()) &
                (df["Rate_Structure"] == rate_structure) &
                (df["Minimum_Annual_Consumption"] <= consumption) &
                (df["Maximum_Annual_Consumption"] >= consumption) &
                (pd.to_datetime(df["Minimum_Contract_Start_Date"]) <= pd.to_datetime(contract_start_date)) &
                (pd.to_datetime(df["Maximum_Contract_Start_Date"]) >= pd.to_datetime(contract_start_date))
            ]

            if not matched.empty:
                price = matched.iloc[0]

                cost_components = {
                    "Standing_Charge": price.get("Standing_Charge", 0),
                    "Standard_Rate": price.get("Standard_Rate", 0),
                    "Day_Rate": price.get("Day_Rate", 0),
                    "Night_Rate": price.get("Night_Rate", 0),
                    "Evening_And_Weekend_Rate": price.get("Evening_And_Weekend_Rate", 0),
                    "Capacity_Rate": price.get("Capacity_Rate", 0),
                    "Metering_Charge": price.get("Metering_Charge", 0)
                }

                st.write("**Cost Prices:**")
                for comp, val in cost_components.items():
                    st.write(f"{comp}: {val} p")

                input_rows.append({
                    "Customer": customer_name,
                    "Site": site,
                    "DNO ID": dno_id,
                    "LLF Code": llf_code,
                    "LLF Band": llf_band,
                    "Annual Consumption (kWh)": consumption,
                    **cost_components
                })
            else:
                st.warning(f"No pricing found for Site {i+1} with current selections.")

        else:
            st.warning(f"LLF Band not found for Site {i+1}.")

    if input_rows:
        st.subheader("Pricing Results")
        results_df = pd.DataFrame(input_rows)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            results_df.to_excel(writer, index=False, sheet_name="Quote")
        output.seek(0)

        st.download_button(
            label="Download Quote as Excel",
            data=output,
            file_name=f"{output_filename}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Please upload the electricity flat file to begin.")
