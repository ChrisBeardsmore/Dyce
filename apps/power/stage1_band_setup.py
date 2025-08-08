import streamlit as st
import pandas as pd

st.set_page_config(page_title="NHH Margin Sculpting – Stage 1", layout="wide")
st.title("🔧 NHH Margin Sculpting Tool – Stage 1: Band Setup & Margin Targets")

# --- STEP 1: Upload Flat File ---
st.markdown("### 🟥 **Step 1: Upload Supplier Flat File**")
uploaded_file = st.file_uploader("Upload the pricing flat file (.xlsx)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("File uploaded successfully. Preview below:")
    st.dataframe(df.head())

    # --- STEP 2: Define Custom Consumption Bands ---
    st.markdown("### 🟥 **Step 2: Define Custom Consumption Bands**")
    num_bands = st.number_input("Number of Bands", min_value=1, max_value=10, value=5)
    custom_bands = []

    for i in range(num_bands):
        st.markdown(f"**Band {i+1}**")
        cols = st.columns(2)
        min_kwh = cols[0].number_input(f"Min Consumption (kWh) – Band {i+1}", key=f"min_{i}", min_value=0)
        max_kwh = cols[1].number_input(f"Max Consumption (kWh) – Band {i+1}", key=f"max_{i}", min_value=min_kwh+1)
        custom_bands.append((min_kwh, max_kwh))

    # --- STEP 3: Target Recovery & Margin ---
    st.markdown("### 🟥 **Step 3: Set Recovery & Margin Targets per Band**")
    recovery_margin_data = []

    for idx, (min_val, max_val) in enumerate(custom_bands):
        st.markdown(f"**Band {idx+1}: {min_val:,} – {max_val:,} kWh**")
        cols = st.columns([1.5, 1.5, 1.5, 1.5])

        recovery_cost = cols[0].number_input("Recovery (£/meter)", min_value=0.0, step=1.0, key=f"recovery_{idx}")
        margin_type = cols[1].selectbox("Margin Type", options=["£/meter", "p/kWh"], key=f"margin_type_{idx}")
        margin_value = cols[2].number_input("Margin Value", min_value=0.0, step=0.1, key=f"margin_value_{idx}")

        sc_split = cols[3].number_input("Standing Charge %", min_value=0, max_value=100, value=50, key=f"split_{idx}")
        ur_split = 100 - sc_split

        recovery_margin_data.append({
            "Band": f"{min_val:,} – {max_val:,} kWh",
            "Min_kWh": min_val,
            "Max_kWh": max_val,
            "Recovery (£/meter)": recovery_cost,
            "Margin Type": margin_type,
            "Margin Value": margin_value,
            "SC %": sc_split,
            "Unit %": ur_split
        })

    # --- STEP 4: Review & Export Config ---
    st.markdown("### 🟥 **Step 4: Review Band Configuration**")
    output_df = pd.DataFrame(recovery_margin_data)
    st.dataframe(output_df)

    st.download_button(
        label="📥 Download Band & Margin Config as CSV",
        data=output_df.to_csv(index=False).encode('utf-8'),
        file_name="nhh_band_margin_config.csv",
        mime="text/csv"
    )
else:
    st.info("Please upload a flat file to begin.")
