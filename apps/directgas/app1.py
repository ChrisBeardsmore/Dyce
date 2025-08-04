
import streamlit as st
import pandas as pd
import io
from PIL import Image
from apps.directgas.logic.ldz_lookup import load_ldz_data, match_postcode_to_ldz
from apps.directgas.logic.base_price_lookup import get_base_rates
from apps.directgas.logic.tac_calculator import calculate_tac_and_margin
from apps.directgas.logic.flat_file_loader import load_flat_file
from apps.directgas.logic.input_setup import create_input_dataframe

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


input_df, all_cols = create_input_dataframe(base_cols, durations)
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
            base_sc, base_unit = get_base_rates(ldz, kwh, duration, carbon_offset_required, flat_df)

            row_data[f"Base Standing Charge ({duration}m)"] = round(base_sc, 2)
            row_data[f"Base Unit Rate ({duration}m)"] = round(base_unit, 3)

            uplift_unit = row.get(f"Uplift Unit Rate ({duration}m)", 0)
            uplift_sc = row.get(f"Standing Charge Uplift ({duration}m)", 0)

            sell_tac, margin = calculate_tac_and_margin(kwh, base_sc, base_unit, uplift_sc, uplift_unit)

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
