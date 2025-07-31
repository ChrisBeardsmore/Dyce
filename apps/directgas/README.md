\# Gas Direct Final 6 – Streamlit App README



\## 📌 Overview

This Streamlit app, \*\*Gas Direct Final 6\*\*, is designed to simplify the process of building multi-site gas quotes using editable data tables and live supplier rate lookups. It is part of the Dyce internal tools ecosystem and resides in the `/directgas` folder of the mono repo.



---



\## ✅ Features

\- \*\*Unified Input Grid\*\*: One editable row per site using `st.data\_editor`

\- \*\*Editable Fields\*\*: Site Name, Post Code, Annual KWH, SC Uplift, Unit Uplift (pence)

\- \*\*Auto-Lookup\*\*: Pulls base rates from a supplier flat file based on:

&nbsp; - LDZ (via postcode match)

&nbsp; - Contract Duration

&nbsp; - KWH Band

&nbsp; - Carbon Offset Flag

\- \*\*Calculated Fields\*\*:

&nbsp; - Sell Standing Charge

&nbsp; - Sell Unit Rate

&nbsp; - Total Annual Cost (TAC)

\- \*\*Output\*\*:

&nbsp; - Streamlit table with core pricing (SC, Unit, TAC)

&nbsp; - Total TAC summary

&nbsp; - Excel download of customer-facing quote



---



\## 🔄 How It Works

1\. \*\*Upload\*\* the supplier flat file (XLSX) with LDZ-based pricing.

2\. \*\*Edit\*\* customer site details and uplifts via an interactive grid.

3\. \*\*LDZs\*\* are automatically matched via postcode prefixes.

4\. \*\*Base rates\*\* are retrieved and uplifts applied to calculate final sell prices.

5\. \*\*Download\*\* the customer-ready quote as an Excel file.



---



\## 🗂️ Required Files

\- `DYCE-DARK BG.png` – Optional company logo displayed in-app

\- `postcode\_ldz\_full.csv` – LDZ matching data from GitHub

\- Uploaded XLSX flat file – Supplier pricing matrix



---



\## 🚀 To Run the App

From the root of your cloned mono repo:



```bash

streamlit run directgas/app.py

```



Make sure dependencies are installed via `requirements.txt`.



---



\## 📎 Dependencies

\- `pandas`

\- `streamlit`

\- `xlsxwriter`

\- `Pillow`



---



\## 💡 Notes

\- SC Uplift is capped at 100p/day

\- Unit Uplift is capped at 3.000p/kWh

\- Base rates will default to 0 if no match is found



---



\## 🛠️ Future Enhancements

\- Save/load editable grid state between sessions

\- Historical quote archive via SQLite or cloud store

\- Optional email export feature



---



\*Maintained by Dyce Energy – Internal Tooling\*



