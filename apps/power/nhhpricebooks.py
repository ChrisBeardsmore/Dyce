import streamlit as st
import pandas as pd
import io

st.set_page_config(layout="wide")
st.title("NHH Pricing Tool with Manual Cost Allocation")

uploaded_file = st.file_uploader("Upload the Flat File (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    st.write("Flat file loaded successfully. Preview:")
    st.dataframe(df.head())

    green_option = st.selectbox("Select Tariff Type:", options=["Standard", "Green"])
    contract_duration = st.selectbox("Select Contract Duration (Months):", options=[12, 24, 36])

    st.subheader("Manual Cost Allocation")

    total_cost_input = st.number_input("Enter Total Cost per Meter (£/year)", value=120.0, step=1.0)
    cost_split_slider = st.slider("Allocate Cost to Standing Charge (%)", min_value=0, max_value=100, value=50)

    cost_pence = total_cost_input * 100  # Convert £ to pence
    standing_pct = cost_split_slider / 100
    unit_pct = 1 - standing_pct

    st.subheader("Consumption Profile Split (%)")

    col_day, col_night, col_evw = st.columns(3)

    day_pct = col_day.slider("Day (%)", min_value=0, max_value=100, value=70)
    night_pct = col_night.slider("Night (%)", min_value=0, max_value=100, value=20)
    evw_pct = col_evw.slider("Evening & Weekend (%)", min_value=0, max_value=100, value=10)

    profile_total = day_pct + night_pct + evw_pct
    st.markdown(f"**Total: {profile_total}%**")

    if profile_total != 100:
        st.error("The total profile split must equal 100%. Please adjust the sliders.")
        st.stop()

    st.subheader("Uplifts per Consumption Band")
    bands = [
        (1000, 3000),
        (3001, 12500),
        (12501, 26000),
        (26001, 100000),
        (100001, 175000),
        (175001, 225000),
        (225001, 300000)
    ]

    uplift_inputs = []
    for idx, (min_val, max_val) in enumerate(bands):
        st.markdown(f"**Band {idx+1}: {min_val:,} – {max_val:,} kWh**")
        cols = st.columns(4)
        uplift_standing = cols[0].number_input(
            f"Standing Charge Uplift (p/day) - Band {idx+1}", value=0.0, step=0.1, key=f"sc_{idx}")
        uplift_day = cols[1].number_input(
            f"Day Rate Uplift (p/kWh) - Band {idx+1}", value=0.0, step=0.1, key=f"day_{idx}")
        uplift_night = cols[2].number_input(
            f"Night Rate Uplift (p/kWh) - Band {idx+1}", value=0.0, step=0.1, key=f"night_{idx}")
        uplift_evw = cols[3].number_input(
            f"Evening & Weekend Uplift (p/kWh) - Band {idx+1}", value=0.0, step=0.1, key=f"evw_{idx}")
        uplift_inputs.append({
            "min": min_val,
            "max": max_val,
            "uplift_standing": uplift_standing,
            "uplift_day": uplift_day,
            "uplift_night": uplift_night,
            "uplift_evw": uplift_evw
        })

    report_title = st.text_input("Enter Report Filename (without .xlsx):", value="nhh_price_book")

    if st.button("Generate Excel Price Book"):
        output_rows = []

        for band in uplift_inputs:
            filtered = df[
                (df["Minimum_Annual_Consumption"] <= band["max"]) &
                (df["Maximum_Annual_Consumption"] >= band["min"]) &
                (df["Contract_Duration"] == contract_duration) &
                ((df["Green_Energy"].str.upper() == "YES") if green_option == "Green" else (df["Green_Energy"].str.upper() == "NO"))
            ]

            if filtered.empty:
                output_rows.append({
                    "Band": f"{band['min']:,} – {band['max']:,}",
                    "Standing Charge (p/day)": "N/A",
                    "Day Rate (p/kWh)": "N/A",
                    "Night Rate (p/kWh)": "N/A",
                    "Evening & Weekend Rate (p/kWh)": "N/A",
                    "Total Annual Cost (£)": "N/A"
                })
            else:
                row = filtered.iloc[0]
                mid_consumption = (band['min'] + band['max']) / 2

                allocated_standing = (cost_pence * standing_pct) / 365  # p/day
                allocated_unit = (cost_pence * unit_pct) / mid_consumption  # p/kWh

                base_standing = row["Standing_Charge"] + allocated_standing
                base_day = row["Day_Rate"] + allocated_unit
                base_night = row["Night_Rate"] + allocated_unit
                base_evw = row["Evening_And_Weekend_Rate"] + allocated_unit

                final_standing = base_standing + band["uplift_standing"]
                final_day = base_day + band["uplift_day"]
                final_night = base_night + band["uplift_night"]
                final_evw = base_evw + band["uplift_evw"]

                annual_cost = (
                    mid_consumption * (
                        final_day * (day_pct / 100) +
                        final_night * (night_pct / 100) +
                        final_evw * (evw_pct / 100)
                    ) / 100
                ) + (365 * final_standing / 100)

                output_rows.append({
                    "Band": f"{band['min']:,} – {band['max']:,}",
                    "Standing Charge (p/day)": round(final_standing, 4),
                    "Day Rate (p/kWh)": round(final_day, 4),
                    "Night Rate (p/kWh)": round(final_night, 4),
                    "Evening & Weekend Rate (p/kWh)": round(final_evw, 4),
                    "Total Annual Cost (£)": round(annual_cost, 2)
                })

        result_df = pd.DataFrame(output_rows)

        st.success("Excel file prepared. Preview:")
        st.dataframe(result_df)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            result_df.to_excel(writer, index=False, sheet_name="Price Book")

        processed_data = output.getvalue()

        st.download_button(
            label="Download Excel Price Book",
            data=processed_data,
            file_name=f"{report_title}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.warning("Please upload the flat file to start.")
