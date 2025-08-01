# Gas Direct Final (V6.0)
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

# Cached data loaders
@st.cache_data
def load_ldz_data():
    url = "https://raw.githubusercontent.com/ChrisBeardsmore/Gas-Pricing/main/postcode_ldz_full.csv"
    df = pd.read_csv(url)
    df["Postcode"] = df["Postcode"].astype(str).str.upper().str.replace(r"\s+", "", regex=True)
    return df

@st.cache_data
def load_flat_file(uploaded_file):
    df = pd.read_excel(uploaded_file)
    df["LDZ"] = df["LDZ"].astype(str).str.strip().str.upper()
    df["Contract_Duration"] = pd.to_numeric(df["Contract_Duration"], errors='coerce').fillna(0).astype(int)
    df["Minimum_Annual_Consumption"] = pd.to_numeric(df["Minimum_Annual_Consumption"], errors='coerce').fillna(0)
    df["Maximum_Annual_Consumption"] = pd.to_numeric(df["Maximum_Annual_Consumption"], errors='coerce').fillna(0)
    return df

def match_postcode_to_ldz(postcode, ldz_df):
    postcode = postcode.replace(" ", "").upper()
    for length in [7, 6, 5, 4, 3]:
        match = ldz_df[ldz_df["Postcode"].str.startswith(postcode[:length])]
        if not match.empty:
            return match.iloc[0]["LDZ"]
    return ""

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
    uplift_fields = ["Standing Charge Uplift ({d}m)", "Uplift Unit Rate ({d}m)"]
    all_cols = base_cols.copy()

    for d in durations:
        all_cols += [
            f"Base Standing Charge ({d}m)", f"Base Unit Rate ({d}m)",
            f"Standing Charge Uplift ({d}m)", f"Uplift Unit Rate ({d}m)",
            f"TAC £({d}m)", f"Margin £({d}m)"
        ]

    # Prepopulate input grid with base prices
    input_rows = []
    for _ in range(10):
        row_data = {col: "" if col in ["Site Name", "Post Code"] else 0 for col in all_cols}
        input_rows.append(row_data)

    input_df = pd.DataFrame(input_rows)

    # Apply base rates before editing
    for idx, row in input_df.iterrows():
        postcode = row["Post Code"]
        kwh = row["Annual KWH"]
        if not postcode or kwh <= 0:
            continue
        ldz = match_postcode_to_ldz(postcode, ldz_df)

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
                input_df.at[idx, f"Base Standing Charge ({duration}m)"] = round(t["Standing_Charge"], 2)
                input_df.at[idx, f"Base Unit Rate ({duration}m)"] = round(t["Unit_Rate"], 3)

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

        row_data = {"Site Name": site, "Post Code": postcode, "Annual KWH": kwh}

        for duration in durations:
            base_sc = float(row.get(f"Base Standing Charge ({duration}m)", 0))
            base_unit = float(row.get(f"Base Unit Rate ({duration}m)", 0))
            uplift_sc = min(float(row.get(f"Standing Charge Uplift ({duration}m)", 0)), 100.0)
            uplift_unit = min(float(row.get(f"Uplift Unit Rate ({duration}m)", 0)), 3.000)

            sell_sc = base_sc + uplift_sc
            sell_unit = base_unit + uplift_unit

            base_tac = round((base_unit * kwh + base_sc * 365) / 100, 2)
            sell_tac = round((sell_unit * kwh + sell_sc * 365) / 100, 2)
            margin = round(sell_tac - base_tac, 2)

            row_data[f"Sell Standing Charge ({duration}m)"] = round(sell_sc, 2)
            row_data[f"Sell Unit Rate ({duration}m)"] = round(sell_unit, 3)
            row_data[f"TAC £({duration}m)"] = sell_tac
            row_data[f"Margin £({duration}m)"] = margin

        result_rows.append(row_data)

    if result_rows:
        output_df = pd.DataFrame(result_rows)
        output_cols = ["Site Name", "Post Code", "Annual KWH"] + [f"Sell Standing Charge ({d}m)" for d in durations] + [f"Sell Unit Rate ({d}m)" for d in durations] + [f"TAC £({d}m)" for d in durations]
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
