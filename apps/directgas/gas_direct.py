# Gas Direct Final (V6.0)
# -----------------------------------------------------------------------------
# ✅ Unified Input Grid: SC, Unit, TAC + Uplifts all visible per site
# ✅ Postcode -> LDZ matching
# ✅ Base prices pulled live from flat file
# ✅ Excel export of customer-facing quote
# -----------------------------------------------------------------------------

import streamlit as st
import pandas as pd
import io
from PIL import Image

st.set_page_config(page_title="Gas Multi-tool (V6)", layout="wide")
st.title("Gas Multi-site Quote Builder – Final v6")

# --- Logo ---
col1, col2 = st.columns([9, 1])
with col2:
    try:
        logo = Image.open("shared/DYCE-DARK BG.png")
        st.image(logo, width=120)
    except:
        st.warning("⚠️ Logo not found")

# --- Loaders ---
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

# --- File Upload ---
ldz_df = load_ldz_data()
uploaded_file = st.file_uploader("Upload Supplier Flat File (XLSX)", type=["xlsx"])

if uploaded_file:
    flat_df = load_flat_file(uploaded_file)

    st.subheader("Quote Configuration")
    customer_name = st.text_input("Customer Name")
    product_type = st.selectbox("Product Type", ["Standard Gas", "Carbon Off"])
    carbon_offset_required = product_type == "Carbon Off"
    output_filename = st.text_input("Output file name", value="dyce_quote")

    st.subheader("Input Grid – With Base Rates")
    durations = [12, 24, 36]
    input_cols = ["Site Name", "Post Code", "Annual KWH"]
    for d in durations:
        input_cols += [
            f"Base SC ({d}m)", f"Base Unit ({d}m)",
            f"SC Uplift ({d}m)", f"Unit Uplift ({d}m)",
            f"TAC £({d}m)", f"Margin ({d}m)"
        ]

    default_row = {col: "" if "Site" in col or "Post" in col else 0 for col in input_cols}
    input_df = pd.DataFrame([default_row.copy() for _ in range(10)])

    edited_df = st.data_editor(
        input_df,
        use_container_width=True,
        num_rows="fixed",
        hide_index=True,
        key="final_v6_input"
    )

    # --- Populate Base Rates and Calculations ---
    for i, row in edited_df.iterrows():
        postcode = str(row["Post Code"]).strip()
        kwh = float(row["Annual KWH"] or 0)
        if not postcode or kwh <= 0:
            continue

        ldz = match_postcode_to_ldz(postcode, ldz_df)

        for d in durations:
            match = flat_df[
                (flat_df["LDZ"] == ldz) &
                (flat_df["Contract_Duration"] == d) &
                (flat_df["Minimum_Annual_Consumption"] <= kwh) &
                (flat_df["Maximum_Annual_Consumption"] >= kwh) &
                (flat_df["Carbon_Offset"] == carbon_offset_required)
            ]

            base_unit = base_sc = 0.0
            if not match.empty:
                best = match.sort_values("Unit_Rate").iloc[0]
                base_unit = best["Unit_Rate"]
                base_sc = best["Standing_Charge"]

            sc_uplift = float(row.get(f"SC Uplift ({d}m)", 0))
            unit_uplift = float(row.get(f"Unit Uplift ({d}m)", 0))

            sell_sc = base_sc + sc_uplift
            sell_unit = base_unit + unit_uplift
            tac = round((sell_unit * kwh + sell_sc * 365) / 100, 2)
            margin = round((unit_uplift * kwh + sc_uplift * 365) / 100, 2)

            edited_df.at[i, f"Base SC ({d}m)"] = round(base_sc, 2)
            edited_df.at[i, f"Base Unit ({d}m)"] = round(base_unit, 3)
            edited_df.at[i, f"TAC £({d}m)"] = tac
            edited_df.at[i, f"Margin ({d}m)"] = margin

    st.subheader("Updated Customer Grid")
    st.dataframe(edited_df, use_container_width=True, height=500)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        edited_df.to_excel(writer, index=False, sheet_name="Customer Quote")
    output.seek(0)

    st.download_button(
        label="📥 Download Quote as Excel",
        data=output,
        file_name=f"{output_filename}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Please upload the supplier flat file to begin.")
