# Direct Sales LLF Multi-tool

This app allows Dyce Direct Sales users to generate site-specific electricity quotes using LLF & DNO mappings.

## How it works
- Upload the electricity flat file
- Enter site-level info (DNO ID, LLF Code, consumption, etc.)
- Tool looks up LLF band and returns matched prices
- Generates Excel-ready quote file

## Requirements
- Python 3.10+
- Streamlit
- Pandas

## Run locally
```bash
streamlit run app.py
