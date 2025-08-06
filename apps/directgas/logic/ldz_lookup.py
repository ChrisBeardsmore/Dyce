# -----------------------------------------
# File: ldz_lookup.py (Fixed)
# Purpose: Load postcode → LDZ mappings with reliable path handling
# -----------------------------------------

import os
import pandas as pd
import streamlit as st

def load_ldz_data() -> pd.DataFrame:
    """Load LDZ mapping data from local CSV and clean postcode column."""
    # Get absolute path to the CSV file relative to this script
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, "..", "..", "inputs", "postcode_ldz_full.csv")
    file_path = os.path.abspath(file_path)

    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        st.error(f"❌ LDZ file not found at: {file_path}")
        raise

    # Standardise postcodes: uppercase and remove spaces
    df["Postcode"] = df["Postcode"].astype(str).str.upper().str.replace(r"\s+", "", regex=True)
    
    return df

def match_postcode_to_ldz(postcode: str, ldz_df: pd.DataFrame) -> str:
    """Match a postcode to its corresponding LDZ region."""
    postcode = postcode.replace(" ", "").upper()
    
    for length in [7, 6, 5, 4, 3]:
        match = ldz_df[ldz_df["Postcode"].str.startswith(postcode[:length])]
        if not match.empty:
            result = match.iloc[0]["LDZ"]
            st.write(f"✅ Debug: Found match for {postcode[:length]}: {result}")
            return result
    
    st.write(f"❌ Debug: No match found for {postcode}")
    return ""
