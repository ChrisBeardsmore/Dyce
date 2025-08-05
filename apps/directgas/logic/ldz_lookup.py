# -----------------------------------------
# File: ldz_lookup.py
# Purpose: Provides functions to load postcode → LDZ mappings 
#          and to match postcodes to LDZ regions for pricing logic
# Author: Dyce (using Anna GPT coding standards)
# -----------------------------------------

import pandas as pd
import streamlit as st
# -----------------------------------------
# Function: load_ldz_data
# Purpose: Load the postcode-to-LDZ mapping table from GitHub
# Inputs: None
# Returns:
#   - pd.DataFrame: Cleaned LDZ reference table with uppercased, space-stripped postcodes
# -----------------------------------------
def load_ldz_data() -> pd.DataFrame:
    """Fetch LDZ mapping data from remote CSV and clean postcode column."""
    url = "https://raw.githubusercontent.com/ChrisBeardsmore/Gas-Pricing/main/postcode_ldz_full.csv"
    
    df = pd.read_csv(url)
    # Standardise postcodes: uppercase and remove spaces
    df["Postcode"] = df["Postcode"].astype(str).str.upper().str.replace(r"\s+", "", regex=True)
    
    return df


# -----------------------------------------
# Function: match_postcode_to_ldz
# Purpose: Match a given postcode to its LDZ by reducing postcode length 
#          until a match is found in the reference table
# Inputs:
#   - postcode (str): User-input postcode (e.g. "LS1 4DT")
#   - ldz_df (pd.DataFrame): LDZ reference DataFrame from load_ldz_data()
# Returns:
#   - str: Matching LDZ code (e.g. "NE", "SW") or empty string if not found
# -----------------------------------------
def match_postcode_to_ldz(postcode: str, ldz_df: pd.DataFrame) -> str:
    """Match a postcode to its corresponding LDZ region."""
    postcode = postcode.replace(" ", "").upper()
    
def match_postcode_to_ldz(postcode: str, ldz_df: pd.DataFrame) -> str:
    """Match a postcode to its corresponding LDZ region."""
    postcode = postcode.replace(" ", "").upper()
    
    # Debug: Show what we're working with
    st.write(f"🔍 Debug: Looking for postcode: {postcode}")
    st.write(f"🔍 Debug: LDZ dataframe columns: {list(ldz_df.columns)}")
    
    # Try longest-to-shortest prefix match (7 to 3 characters)
    for length in [7, 6, 5, 4, 3]:
        match = ldz_df[ldz_df["Postcode"].str.startswith(postcode[:length])]
        if not match.empty:
            result = match.iloc[0]["LDZ"]
            st.write(f"✅ Debug: Found match for {postcode[:length]}: {result}")
            return result
    
    # No match found
    st.write(f"❌ Debug: No match found for {postcode}")
    return ""
