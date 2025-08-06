import streamlit as st
import pandas as pd
import io
from logic import generate_price_book

st.set_page_config(layout="wide")
st.title("NHH Pricing Tool with Manual Cost Allocation")

uploaded_file = st.file_uploader("Upload the Flat File (.xlsx)", type=["xlsx"])

if uploaded_file is None:
    st.warning("Please upload the flat file to start.")
    st.stop()

df = pd.read_excel(uploaded_file)
st.write("Flat file loaded successfully. Preview:")
st.dataframe(df.head())

green_option = st.selectbox("Select Tariff Type:", options=["Standard", "Green"])
contract_duration = st.selectbox("Select Contract Duration (Months):", options=[12, 24, 36])

st.subheader("Manual Cost Allocation")
total_cost_input = st.number_input("Enter Total Cost per Meter (£/year)", value=120.0, step=1.0)
cost_split_slider = st.slider("Allocate Cost to Standing Charge (%)", min_value=0, max_value=100, value=50)

st.subheader("Consumption Profile Split (%)")
col_day, col_night, col_evw = st.columns(3)
day_pct = col_day.slider("Day (%)", min_value=0, max_value=100, value=70)
night_pct = col_night.slider("Night (%)", min_value=0, max_value=100, value=20)
evw_pct = col_evw.slider("Evening & Weekend (%)", min_value=0, max_value=100, value=10)

if day_pct + night_pct + evw_pct != 100:
    st.error("The total profile split must equal 100%.")
    st.stop()

profile_split = {"day": day_pct, "night": night_pct, "evw": evw_pct}

st.subheader("Uplifts per Consumption Band")
bands = [(1000, 3000), (3001, 12500), (12501, 26000), (26001, 100000), (100001, 175000), (175001, 225000), (225001, 300000)]
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
    )
