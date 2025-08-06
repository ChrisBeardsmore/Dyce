import streamlit as st
import pandas as pd
import io
from logic import generate_price_book

# Step 0: Page Setup
st.set_page_config(layout="wide")
st.title("⚡ NHH Pricing Tool – Manual Cost Allocation")

# Step 1: Upload Flat File
uploaded_file = st.file_uploader("Upload the Flat File (.xlsx)", type=["xlsx"])
if uploaded_file is None:
    st.warning("Please upload the flat file to start.")
    st.stop()

df = pd.read_excel(uploaded_file)
st.success("Flat file loaded successfully.")
st.dataframe(df.head())

# Step 2: Select Tariff and Contract Duration
st.header("Step 2: Contract Settings")
green_option = st.selectbox("Select Tariff Type:", options=["Standard", "Green"])
contract_duration = st.selectbox("Select Contract Duration (Months):", options=[12, 24, 36])

# Step 3: Manual Cost Allocation
st.header("Step 3: Manual Cost Allocation")
total_cost_input = st.number_input("Enter Total Cost per Meter (£/year)", value=120.0, step=1.0)
cost_split_slider = st.slider("Allocate Cost to Standing Charge (%)", min_value=0, max_value=100, value=50)

# Step 4: Set Consumption Profile Split
st.header("Step 4: Consumption Profile Split (%)")
col_day, col_night, col_evw = st.columns(3)
day_pct = col_day.slider("Day (%)", min_value=0, max_value=100, value=70)
night_pct = col_night.slider("Night (%)", min_value=0, max_value=100, value=20)
evw_pct = col_evw.slider("Evening & Weekend (%)", min_value=0, max_value=100, value=10)

profile_total = day_pct + night_pct + evw_pct
if profile_total != 100:
    st.error("The total profile split must equal 100%.")
    st.stop()

profile_split = {"day": day_pct, "night": night_pct, "evw": evw_pct}

# Step 5: Set Uplifts per Consumption Band
st.header("Step 5: Uplifts per Consumption Band")
bands = [
    (1000, 3000),
    (3001, 12500),
    (12501, 26000),
    (26001, 100000),
    (100001, 175000),
    (175001, 225000),
    (225001, 300000)
]

# Step 5A: Load or Save Uplift Config
import json
from utils.config_handler import load_uplift_config  # You must have this file in /utils/

st.header("Step 5A: Load or Save Uplift Config")

uploaded_config = st.file_uploader("Load Existing Uplift Config (.json)", type=["json"])
uplift_inputs = []

if uploaded_config:
    loaded_config = load_uplift_config(uploaded_config)
    uplift_inputs = loaded_config["bands"]
    st.success(f"Loaded config: {loaded_config['name']} ({loaded_config['date']})")
else:
    for idx, (min_val, max_val) in enumerate(bands):
        uplift_inputs.append({
            "min": min_val,
            "max": max_val,
            "uplift_standing": 0.0,
            "uplift_day": 0.0,
            "uplift_night": 0.0,
            "uplift_evw": 0.0
        })

with st.expander("💾 Save Current Uplift Config", expanded=False):
    config_name = st.text_input("Name this uplift version", value="Sep24_Sculpted")
    config_notes = st.text_area("Notes", value="Trial pricing for September")
    if st.button("Download Config as JSON"):
        config_dict = {
            "name": config_name,
            "date": str(pd.Timestamp.today().date()),
            "notes": config_notes,
            "bands": uplift_inputs
        }
        st.download_button(
            label="Download JSON",
            data=json.dumps(config_dict, indent=2),
            file_name=f"{config_name}.json",
            mime="application/json"
        )

uplift_inputs = []

for idx, (min_val, max_val) in enumerate(bands):
    st.markdown(f"**Band {idx+1}: {min_val:,} – {max_val:,} kWh**")
    cols = st.columns(4)
    uplift_inputs.append({
        "min": min_val,
        "max": max_val,
        "uplift_standing": cols[0].number_input(f"SC Uplift (p/day) - Band {idx+1}", value=0.0, step=0.1, key=f"sc_{idx}"),
        "uplift_day": cols[1].number_input(f"Day Uplift (p/kWh) - Band {idx+1}", value=0.0, step=0.1, key=f"day_{idx}"),
        "uplift_night": cols[2].number_input(f"Night Uplift (p/kWh) - Band {idx+1}", value=0.0, step=0.1, key=f"night_{idx}"),
        "uplift_evw": cols[3].number_input(f"E/W Uplift (p/kWh) - Band {idx+1}", value=0.0, step=0.1, key=f"evw_{idx}")
    })

# Step 6: Generate and Download Excel Price Book
st.header("Step 6: Generate Excel Price Book")
report_title = st.text_input("Enter Report Filename (without .xlsx):", value="nhh_price_book")

if st.button("Generate Excel Price Book"):
    result_df = generate_price_book(
        df=df,
        bands=bands,
        uplifts=uplift_inputs,
        total_cost=total_cost_input,
        standing_pct=cost_split_slider / 100,
        contract_duration=contract_duration,
        green_option=green_option,
        profile_split=profile_split
    )

    st.success("Excel file prepared. Preview:")
    st.dataframe(result_df)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        result_df.to_excel(writer, index=False, sheet_name="Price Book")

    st.download_button(
        label="Download Excel Price Book",
        data=output.getvalue(),
        file_name=f"{report_title}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
