# -----------------------------------------
# File: flat_file_loader.py
# Purpose: Load and clean the supplier flat file for gas quote builder
# Notes:
#   - Caches file using Streamlit to prevent lag on repeat interactions
#   - Ensures required fields are typed and standardised
# -----------------------------------------

import pandas as pd
import streamlit as st

# -----------------------------------------
# Function: load_flat_file
# Purpose: Load and clean the supplier flat file uploaded by the user.
# Inputs:
#   - uploaded_file: A Streamlit file object (XLSX format)
# Returns:
#   - pd.DataFrame: Cleaned version of the flat file, ready for base rate lookups
# Notes:
#   - Ensures LDZ column is uppercased and trimmed
#   - Contract_Duration is coerced to integer (invalids → 0)
#   - Min/Max Annual Consumption are coerced to numeric
# -----------------------------------------
@st.cache_data(show_spinner=False)
def load_flat_file(uploaded_file) -> pd.DataFrame:
    """Read and clean the uploaded supplier flat file (XLSX)."""
    
    df = pd.read_excel(uploaded_file)

    # Standardise column formats
    df["LDZ"] = df["LDZ"].astype(str).str.strip().str.upper()
    df["Contract_Duration"] = pd.to_numeric(df["Contract_Duration"], errors='coerce').fillna(0).astype(int)
    df["Minimum_Annual_Consumption"] = pd.to_numeric(df["Minimum_Annual_Consumption"], errors='coerce').fillna(0)
    df["Maximum_Annual_Consumption"] = pd.to_numeric(df["Maximum_Annual_Consumption"], errors='coerce').fillna(0)

