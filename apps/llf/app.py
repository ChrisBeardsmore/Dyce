import streamlit as st
import pandas as pd

st.set_page_config(page_title="Electricity Pricing App", layout="wide")

# Title
st.title("Electricity Pricing Tool")

# Load data
@st.cache_data
def load_flat_file():
    return pd.read_excel("Elec Flat File 230625.xlsx")

@st.cache_data
def load_llf_mapping():
    return pd.read_excel("llf_mapping.xlsx")

flat_file = load_flat_file()
llf_mapping = load_llf_mapping()

# Sidebar filters
st.sidebar.header("Filter Criteria")

# DNO selection
dno_options = sorted(flat_file["DNO_ID"].dropna().unique())
dno_id = st.sidebar.selectbox("DNO ID", dno_options)

# LLF code input
llf_code = st.sidebar.text_input("LLF Code (e.g., 199, N10, X20)")

# Annual consumption
annual_consumption = st.sidebar.number_input("Annual Consumption (kWh)", min_value=0)

# Contract duration
contract_durations = sorted(flat_file["Contract_Duration"].dropna().unique())
contract_duration = st.sidebar.selectbox("Contract Duration (months)", contract_durations)

# Green energy preference
green_energy = st.sidebar.radio("Green Energy", ["False", "True"])

# Validate LLF input
if not llf_code:
    st.warning("Please enter an LLF Code.")
    st.stop()

# Map LLF to Band
band_row = llf_mapping[
    (llf_mapping["DNO"].astype(str) == str(dno_id)) &
    (llf_mapping["LLF"].astype(str) == str(llf_code))
]

if band_row.empty:
    st.error("No LLF mapping found for this DNO and LLF code.")
    st.stop()

llf_band = band_row.iloc[0]["Band"]
st.write(f"**Mapped LLF Band:** `{llf_band}`")

# Filter flat file
filtered = flat_file[
    (flat_file["DNO_ID"] == int(dno_id)) &
    (flat_file["LLF_Band"] == llf_band) &
    (flat_file["Contract_Duration"] == int(contract_duration)) &
    (flat_file["Green_Energy"].astype(str).str.upper() == green_energy.upper()) &
    (flat_file["Minimum_Annual_Consumption"] <= annual_consumption) &
    (flat_file["Maximum_Annual_Consumption"] >= annual_consumption)
]

# Display results
if filtered.empty:
    st.warning("No matching pricing records found.")
else:
    st.success(f"Found {len(filtered)} matching record(s).")
    st.dataframe(filtered, use_container_width=True)

    # Download button
    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download results as CSV",
        data=csv,
        file_name="pricing_results.csv",
        mime="text/csv"
    )
