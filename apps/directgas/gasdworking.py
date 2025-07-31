# Gas Direct Final 6 – Locked Logic, Unified Input Grid, Correct Live Base Rate Pulling
# ------------------------------------------------------------------------------------------------
# ✅ Unified input grid (1 row = 1 site) using st.data_editor
# ✅ Editable fields: Site Name, Post Code, Annual KWH, SC Uplift, Unit Uplift (pence, 3dp)
# ✅ Pulls base prices based on LDZ, Duration, KWH band, Carbon flag
# ✅ Calculates Sell Prices, TAC, Margin
# ✅ Shows only Sell SC, Sell Unit Rate, TAC in output (no uplift/margin)
# ✅ Total TAC summary
# ✅ Excel download

import streamlit as st
import pandas as pd
import io
from PIL import Image

st.set_page_config(page_title="Gas Direct Final 6", layout="wide")
st.title("Gas Multi-site Quote Builder (Final 6)")

# ----------------------------
# Load LDZ + Flat File
# ----------------------------
@st.cache_data
def load_ldz_data():
    url = "https://raw.githubusercontent.com/ChrisBeardsmore/Gas-Pricing/main/postcode_ldz_full.csv"
    df = pd.read_csv(url)
    df["Postcode"] = df["Postcode"].astype(str).str.upper().str.replace(r"\\s+", "", regex=True)
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
    for length in [7,6,5,4,3]:
        match = ldz_df[ldz_df["Postcode"].str.startswith(postcode[:length])]
        if not match.empty:
            return match.iloc[0]["LDZ"]
    return ""

# ----------------------------
# App Starts Here
# ----------------------------
ldz_df = load_ldz_data()
uploaded_file = st.file_uploader("Upload Supplier Flat File (XLSX)", type=["xlsx"])

if uploaded_file:
    flat_df = load_flat_file(uploaded_file)

    st.subheader("Customer & Quote Details")
    customer_name = st.text_input("Customer Name")
    product_type = st.selectbox("Product Type", ["Standard Gas", "Carbon Off"])
    carbon_offset_required = (product_type == "Carbon Off")
    output_filename = st.text_input("Output filename (no .xlsx)", value="dyce_quote")

    try:
        logo = Image.open("DYCE-DARK BG.png")
        st.image(logo, width=120)
    except:
        st.warning("Logo not found – please upload 'DYCE-DARK BG.png'.")

    st.markdown("### Multi-site Input Grid (All values in pence)")
    st.caption("SC Uplift max = 100p/day | Unit Rate Uplift max = 3.000p/kWh")

    durations = [12, 24, 36]
    base_cols = ["Site Name", "Post Code", "Annual KWH"]
    dynamic_cols = [
        f"Standing charge ({d}m)" for d in durations
    ] + [
        f"Unit Rate ({d}m)" for d in durations
    ] + [
        f"Standing Charge Uplift ({d}m)" for d in durations
    ] + [
        f"Uplift unit rate ({d}m)" for d in durations
    ] + [
        f"Sell Standing Charge ({d}m)" for d in durations
    ] + [
        f"Sell Unit Rate ({d}m)" for d in durations
    ] + [
        f"TAC £({d}m)" for d in durations
    ]

    all_cols = base_cols + dynamic_cols
    editable = base_cols + [f"Standing Charge Uplift ({d}m)" for d in durations] + [f"Uplift unit rate ({d}m)" for d in durations]

    init_df = pd.DataFrame([{col: 0 if "KWH" in col or "Uplift" in col else "" for col in all_cols} for _ in range(10)])

    edited = st.data_editor(
        init_df,
        use_container_width=True,
        num_rows="fixed",
        hide_index=True,
        disabled=[col for col in all_cols if col not in editable],
        key="grid_final6"
    )

    # ------------------------------------------
    # Apply LDZ + Band Matching + Uplift Logic
    # ------------------------------------------
    results = []
    for _, row in edited.iterrows():
        site = row["Site Name"]
        postcode = row["Post Code"]
        kwh = row["Annual KWH"]
        if not postcode or kwh <= 0:
            continue

        ldz = match_postcode_to_ldz(postcode, ldz_df)
        out = {"Site Name": site, "Post Code": postcode, "Annual KWH": kwh}

        for dur in durations:
            uplift_sc = min(float(row.get(f"Standing Charge Uplift ({dur}m)", 0)), 100.0)
            uplift_unit = min(float(row.get(f"Uplift unit rate ({dur}m)", 0)), 3.000)

            match = flat_df[
                (flat_df["LDZ"] == ldz) &
                (flat_df["Contract_Duration"] == dur) &
                (flat_df["Minimum_Annual_Consumption"] <= kwh) &
                (flat_df["Maximum_Annual_Consumption"] >= kwh) &
                (flat_df["Carbon_Offset"] == carbon_offset_required)
            ]

            if not match.empty:
                best = match.sort_values("Unit_Rate").iloc[0]
                base_unit = best["Unit_Rate"]
                base_sc = best["Standing_Charge"]
            else:
                base_unit = base_sc = 0.0

            sell_unit = base_unit + uplift_unit
            sell_sc = base_sc + uplift_sc
            tac = round((sell_unit * kwh + sell_sc * 365) / 100, 2)

            out[f"Standing charge ({dur}m)"] = round(base_sc, 2)
            out[f"Unit Rate ({dur}m)"] = round(base_unit, 3)
            out[f"Standing Charge Uplift ({dur}m)"] = round(uplift_sc, 2)
            out[f"Uplift unit rate ({dur}m)"] = round(uplift_unit, 3)
            out[f"Sell Standing Charge ({dur}m)"] = round(sell_sc, 2)
            out[f"Sell Unit Rate ({dur}m)"] = round(sell_unit, 3)
            out[f"TAC £({dur}m)"] = tac

        results.append(out)

    # -----------------------------
    # Show Customer-Facing Output
    # -----------------------------
    if results:
        df = pd.DataFrame(results)
        st.subheader("Customer-Facing Output")
        sell_cols = base_cols + [f"Sell Standing Charge ({d}m)" for d in durations] + [f"Sell Unit Rate ({d}m)" for d in durations] + [f"TAC £({d}m)" for d in durations]
        st.dataframe(df[sell_cols], use_container_width=True)

        st.subheader("Summary")
        total_tac = df[[c for c in df.columns if "TAC" in c]].sum().sum()
        st.metric("Total TAC (£)", f"£{total_tac:,.2f}")

        # Export
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df[sell_cols].to_excel(writer, index=False, sheet_name="Customer Quote")
        output.seek(0)

        st.download_button(
            label="Download Customer Quote",
            data=output,
            file_name=f"{output_filename}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Please upload the supplier flat file to begin.")
