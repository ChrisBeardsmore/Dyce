import pandas as pd
from pathlib import Path

LLF_PATH = Path(__file__).resolve().parents[2] / "shared" / "inputs" / "llf_mapping.xlsx"

def load_llf_mapping(path=LLF_PATH):
    return pd.read_excel(path, skiprows=1)

def get_llf_band(mapping_df, dno_id, llf_code):
    match = mapping_df[
        (mapping_df["DNO"].astype(str) == str(dno_id)) &
        (mapping_df["LLF"].astype(str) == str(llf_code))
    ]
    return match.iloc[0]["Band"] if not match.empty else None
