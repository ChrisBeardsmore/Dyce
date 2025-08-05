# Bespoke App - Version V26
# Tweaks:
# 1. Removed redundant Company Name & Company Reg inputs.
# 2. All rows read and grouped by MPXN, pivoted into 12/24/36 columns.
# 3. Single EAC column used across all contract lengths.
# 4. TAC columns added (Total Annual Cost) for 12/24/36 months and displayed in grid.

import streamlit as st
import pandas as pd
from io import BytesIO
from dateutil.relativedelta import relativedelta
from utils.versioning import get_current_version

st.set_page_config(layout="wide")
st.markdown(f"**App Version:** `{get_current_version()}`")

# --- Helper Functions ---
def load_supplier_data(uploaded_file, sheet_name):
    return pd.read_excel(uploaded_file, sheet_name=sheet_name)

def calculate_annual_cost(sc, unit_rate, eac):
    # Convert pence to pounds (assuming pence input)
    return round(((sc * 365) + (unit_rate * eac)) / 100, 2)

@st.cache_data
def convert_df(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return output

def calculate_months(start, end):
    return (end.year - start.year) * 12 + (end.month - start.month)

# --- Streamlit UI ---
st.title('Bespoke Power Pricing Tool – Broker Output Format')

uploaded_file = st.file_uploader("Upload Supplier Tender File (Excel)", type=["xlsx"])

if uploaded_file:
    sheet_option = st.selectbox("Select Pricing Type:", ('Standard', 'Green'))
    df_all = load_supplier_data(uploaded_file, sheet_name=sheet_option)

    # Date conversions and contract length calculation
    df_all['CSD'] = pd.to_datetime(df_all['CSD'], dayfirst=True)
    df_all['CED'] = pd.to_datetime(df_all['CED'], dayfirst=True)
    df_all['Contract Length'] = df_all.apply(lambda row: calculate_months(row['CSD'], row['CED']), axis=1)
    df_all = df_all[df_all['Contract Length'].isin([12, 24, 36])]
    df_all['Contract Length'] = df_all['Contract Length'].astype(str)

    if 'EAC' not in df_all.columns:
        st.error("Missing 'EAC' column in input file.")
        st.stop()

    # Count total rows read
    total_rows = len(df_all)
    st.info(f"Total rows read from Excel: {total_rows}")

    # Use first EAC per MPXN
    eac_map = df_all.groupby('MPXN')['EAC'].first().reset_index()

    # Pivot Standing Charge & Unit Rate
    cost_fields = ['Standing Charge (p/day)', 'Standard Rate (p/kWh)']
    df_grouped = df_all.groupby(['MPXN', 'Contract Length'])[cost_fields].first().reset_index()
    df_pivot = df_grouped.pivot(index='MPXN', columns='Contract Length', values=cost_fields)
    df_pivot.columns = [f"{col[0]} {col[1]}m" for col in df_pivot.columns]
    df_pivot.reset_index(inplace=True)

    displayed_rows = len(df_pivot)
    st.info(f"Rows displayed in grid (unique MPXN): {displayed_rows}")

    # Merge EAC and pivoted values
    full_df = pd.merge(eac_map, df_pivot, on='MPXN', how='left')

    # Add Uplift and TAC columns
    for term in ['12', '24', '36']:
        full_df[f'S/C Uplift {term}m'] = 0.000
        full_df[f'Unit Rate Uplift {term}m'] = 0.000
        full_df[f'TAC {term}m (£)'] = 0.00

    # Data Editor
    st.subheader("Enter Uplifts Per MPXN & Contract Length")
    editable_cols = ['MPXN', 'EAC']
    for term in ['12', '24', '36']:
        editable_cols += [
            f"Standing Charge (p/day) {term}m",
            f"Standard Rate (p/kWh) {term}m",
            f"S/C Uplift {term}m",
            f"Unit Rate Uplift {term}m",
            f"TAC {term}m (£)"
        ]

    input_editor = st.data_editor(
        full_df[editable_cols],
        use_container_width=True,
        hide_index=True,
        height=500,  # Scrollable grid
        column_config={col: st.column_config.NumberColumn(step=0.001) for col in full_df.columns if 'Uplift' in col},
        num_rows="dynamic"
    )

    if st.button("Generate Broker Output"):
        output_rows = []

        for _, row in input_editor.iterrows():
            base = {
                'MPXN': row['MPXN'],
                'EAC': row['EAC']
            }

            for term in ['12', '24', '36']:
                sc_col = f'Standing Charge (p/day) {term}m'
                ur_col = f'Standard Rate (p/kWh) {term}m'

                sc_uplift = row.get(f'S/C Uplift {term}m', 0)
                ur_uplift = row.get(f'Unit Rate Uplift {term}m', 0)

                sc = row.get(sc_col, 0) + sc_uplift
                ur = row.get(ur_col, 0) + ur_uplift
                eac = row['EAC']

                total_cost = calculate_annual_cost(sc, ur, eac)

                base.update({
                    f'Standing Charge {term}m (p/day)': round(sc, 3),
                    f'Unit Rate {term}m (p/kWh)': round(ur, 3),
                    f'TAC {term}m (£)': total_cost
                })

            output_rows.append(base)

        final_output = pd.DataFrame(output_rows)
        st.success("Broker Output Generated")
        st.dataframe(final_output, use_container_width=True)

        excel_data = convert_df(final_output)
        st.download_button(
            label="Download Broker Output",
            data=excel_data,
            file_name='broker_output_dyce_prices.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
