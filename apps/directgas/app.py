# Gas Direct Final (V6.1)
# -----------------------------------------------------------------------------
# ✅ Unified Input Grid (Editable + Base Rates + TAC + Margin)
# ✅ Postcode -> LDZ mapping
# ✅ Base prices pulled from supplier file
# ✅ Uplift inputs in pence (SC ≤ 100, Unit ≤ 3.000)
# ✅ Sell pricing: SC, Unit Rate, TAC
# ✅ Base rates never shown in output
# ✅ Summary of TACs
# ✅ Small Dyce logo (top-right)
# ✅ Clean Excel export
# -----------------------------------------------------------------------------

import streamlit as st
import pandas as pd
import io
from PIL import Image
from apps.directgas.logic.ldz_lookup import load_ldz_data, match_postcode_to_ldz

st.set_page_config(page_title="Gas Multi-tool (Final)", layout="wide")
st.title("Gas Multi-site Quote Builder – Final Version")

# Load logo (top-right)
col1, col2 = st.columns([9, 1])
with col2:
    try:
        logo = Image.open("shared/DYCE-DARK BG.png")
        st.image(logo, width=120)
    except:
        st.warning("⚠️ Logo not found")

# File upload and input config
ldz_df = load_ldz_data()
uploaded_file = st.file_uploader("Upload Supplier Flat File (XLSX)", type=["xlsx"])

if uploaded_file:
    flat_df = load_flat_file(uploaded_file)

    st.subheader("Quote Configuration")
    customer_name = st.text_input("Customer Name")
    product_type = st.selectbox("Product Type", ["Standard Gas", "Carbon Off"])
    carbon_offset_required = product_type == "Carbon Off"
    output_filename = st.text_input("Output file name", value="dyce_quote")

    st.subheader("Input Grid (Editable)")
    base_cols = ["Site Name", "Post Code", "Annual KWH"]
    durations = [12, 24, 36]
    all_cols = base_cols.copy()

    for d in durations:
        all_cols += [
            f"Base Standing Charge ({d}m)", f"Base Unit Rate ({d}m)",
            f"Standing Charge Uplift ({d}m)", f"Uplift Unit Rate ({d}m)",
            f"TAC £({d}m)", f"Margin £({d}m)"
        ]

    input_df = pd.DataFrame([{col: "" if col in ["Site Name", "Post Code"] else 0 for col in all_cols} for _ in range(10)])

    edited_df = st.data_editor(
        input_df,
        use_container_width=True,
        num_rows="fixed",
        hide_index=True,
        disabled=[]
    )

    st.subheader("Customer-Facing Output Preview")
    result_rows = []
    for _, row in edited_df.iterrows():
        site = row["Site Name"]
        postcode = row["Post Code"]
        kwh = row["Annual KWH"]
        if not postcode or kwh <= 0:
            continue

        ldz = match_postcode_to_ldz(postcode, ldz_df)
        row_data = {"Site Name": site, "Post Code": postcode, "Annual KWH": kwh}

        for duration in durations:
            match = flat_df[
                (flat_df["LDZ"] == ldz) &
                (flat_df["Contract_Duration"] == duration) &
                (flat_df["Minimum_Annual_Consumption"] <= kwh) &
                (flat_df["Maximum_Annual_Consumption"] >= kwh) &
                (flat_df["Carbon_Offset"] == carbon_offset_required)
            ]

            if not match.empty:
                t = match.sort_values("Unit_Rate").iloc[0]
                base_unit = t["Unit_Rate"]
                base_sc = t["Standing_Charge"]
            else:
                base_unit = 0.0
                base_sc = 0.0

            row_data[f"Base Standing Charge ({duration}m)"] = round(base_sc, 2)
            row_data[f"Base Unit Rate ({duration}m)"] = round(base_unit, 3)

            uplift_unit = min(float(row.get(f"Uplift Unit Rate ({duration}m)", 0)), 3.000)
            uplift_sc = min(float(row.get(f"Standing Charge Uplift ({duration}m)", 0)), 100.0)

            sell_unit = base_unit + uplift_unit
            sell_sc = base_sc + uplift_sc
            base_tac = round((base_unit * kwh + base_sc * 365) / 100, 2)
            sell_tac = round((sell_unit * kwh + sell_sc * 365) / 100, 2)
            margin = round(sell_tac - base_tac, 2)

            row_data[f"TAC £({duration}m)"] = sell_tac
            row_data[f"Margin £({duration}m)"] = margin

        result_rows.append(row_data)

    if result_rows:
        output_df = pd.DataFrame(result_rows)
        output_cols = ["Site Name", "Post Code", "Annual KWH"] + [f"TAC £({d}m)" for d in durations]
        st.dataframe(output_df[output_cols], use_container_width=True, height=400)

        st.subheader("Summary Totals")
        totals = {f"Total TAC £({d}m)": output_df[f"TAC £({d}m)"].sum() for d in durations}
        st.write(pd.DataFrame([totals]))

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            output_df[output_cols].to_excel(writer, index=False, sheet_name="Customer Quote")
        output.seek(0)

        st.download_button(
            label="📥 Download Quote as Excel",
            data=output,
            file_name=f"{output_filename}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Please upload the supplier flat file to begin.")
