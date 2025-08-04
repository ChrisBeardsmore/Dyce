
# 🔧 Dyce Gas Quote Builder (Streamlit App)

This is the official internal tool used by Dyce to build multi-site gas quotes for SME customers. It reads supplier flat files, matches postcodes to regions (LDZs), applies pricing logic and uplifts, and generates a customer-facing output with total cost and margin breakdown.

---

## 📦 Project Structure

```
apps/
├── directgas/
│   ├── app.py                   # Main production Streamlit app
│   ├── test/
│   │   ├── app_test.py          # Test version of the app (safe sandbox)
│   │   ├── test_flat_file.xlsx  # Sample supplier file for testing
│   │   ├── test_ldz.csv         # Optional test version of postcode-to-LDZ map
│   │   └── test_notes.md        # Manual test plans, notes, or bugs
│   ├── logic/                   # Core pricing logic modules
│   │   ├── base_rate_lookup.py
│   │   ├── tac_calculator.py
│   │   ├── ldz_lookup.py
│   │   ├── flat_file_loader.py
│   │   ├── input_setup.py
│   ├── shared/                  # Static assets (e.g. logos)
│   │   └── DYCE-DARK BG.png
```

---

## 🚀 What the App Does

1. ✅ Uploads a supplier flat file (XLSX)
2. ✅ Accepts site-by-site inputs: Site Name, Postcode, Annual kWh
3. ✅ Automatically:
   - Matches postcode to LDZ
   - Looks up base Standing Charge & Unit Rate from flat file
   - Allows user to apply custom uplifts
4. ✅ Calculates:
   - Customer-facing Total Annual Cost (TAC)
   - Dyce £ margin (difference between base and uplifted cost)
5. ✅ Displays results in an output table
6. ✅ Allows Excel download of results

---

## 🧠 Built-In Rules

- 📍 Uplift caps:
  - Max 3.000p/kWh on unit rates
  - Max 100p/day on standing charges
- 📍 365-day standing charge assumed
- 📍 All prices are in pence except output, which is in £
- 📍 Supports durations: 12, 24, 36 months
- 📍 Carbon Off pricing logic is supported via flat file

---

## 🛠 Development Setup

1. Create virtual environment (optional)
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the app:
   - Production version:
     ```
     streamlit run apps/directgas/app.py
     ```
   - Test version (with flat file & logic debug):
     ```
     streamlit run apps/directgas/test/app_test.py
     ```

---

## 🔍 Logic Files (Modular)

| File | Purpose |
|------|---------|
| `ldz_lookup.py` | Match postcodes to LDZ codes using prefix matching |
| `base_rate_lookup.py` | Find best-matching base SC/unit rates from supplier flat file |
| `tac_calculator.py` | Apply uplifts, calculate customer TAC and Dyce margin |
| `flat_file_loader.py` | Load and clean the supplier pricing file |
| `input_setup.py` | Create the editable input grid structure for the Streamlit UI |

---

## 📦 Version Notes

- All logic files follow **Anna GPT coding standards**: fully documented, type-hinted, red-highlighted headers for fast scanning
- Output formatting (Excel styling) is still basic but functional
- Test folder is sandboxed: safe to experiment and debug

---

## 🧪 Testing Instructions

1. Open `app_test.py`
2. Use `test_flat_file.xlsx` to simulate pricing
3. Enter dummy sites and check:
   - Are base prices appearing after postcode entry?
   - Do uplifts calculate TAC and margin correctly?
   - Does output export to Excel cleanly?

---

## 🧑‍💻 Maintainer Notes

- Future features may include:
  - Export formatting (logos, £ signs)
  - Bulk uplift presets
  - LDZ overrides for edge cases
  - Advanced quote types (portfolio, block)

---

Dyce Energy Ltd | Internal Tool | Built August 2025
