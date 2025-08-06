# -----------------------------------------
# File: ldz_lookup.py
# Purpose: Load postcode → LDZ mappings from GitHub
# Author: Dyce (using Anna GPT coding standards)
# -----------------------------------------

import pandas as pd
import streamlit as st

def load_ldz_data() -> pd.DataFrame:
    """Load LDZ mapping data from GitHub and clean postcode column."""

    # ✅ Replace this with the *actual* raw GitHub URL to the CSV file
    github_url = "https://raw.githubusercontent.com/ChrisBeardsmore/Dyce/main/inputs/postcode_ldz_full.csv"

    try:
        df = pd.read_csv(github_url)
        st.success("✅ Loaded LDZ mapping from GitHub.")
    except Exception as e:
        st.error("❌ Failed to load LDZ mapping file from GitHub.")
        st.exception(e)
        raise

    # Clean postcodes: uppercase and strip spaces
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
