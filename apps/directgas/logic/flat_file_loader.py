import pandas as pd

# 🔴 -----------------------------------------
# 🔴 Function: load_flat_file
# 🔴 Purpose: Load and clean the supplier flat file uploaded by the user.
# 🔴 Inputs:
# 🔴   - uploaded_file: A Streamlit file object (XLSX format)
# 🔴 Returns:
# 🔴   - pd.DataFrame: Cleaned version of the flat file, ready for base rate lookups
# 🔴 Notes:
# 🔴   - Ensures LDZ column is uppercased and trimmed
# 🔴   - Contract_Duration is coerced to integer (invalids → 0)
# 🔴   - Min/Max Annual Consumption are coerced to numeric
# 🔴 -----------------------------------------
def load_flat_file(uploaded_file) -> pd.DataFrame:
    """Read and clean the uploaded supplier flat file (XLSX)."""
    
    # Load raw Excel file
    df = pd.read_excel(uploaded_file)

    # Clean and standardise required columns
    df["LDZ"] = df["LDZ"].astype(str).str.strip().str.upper()
    df["Contract_Duration"] = pd.to_numeric(df["Contract_Duration"], errors='coerce').fillna(0).astype(int)
    df["Minimum_Annual_Consumption"] = pd.to_numeric(df["Minimum_Annual_Consumption"], errors='coerce').fillna(0)
    df["Maximum_Annual_Consumption"] = pd.to_numeric(df["Maximum_Annual_Consumption"], errors='coerce').fillna(0)

    return df
