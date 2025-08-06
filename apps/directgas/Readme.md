Gas Direct Final

Direct Sales Gas Tool
A Streamlit-based application for generating multi-site gas quotes with automated pricing calculations and margin analysis.
Overview
The Direct Sales Gas Tool streamlines the process of creating gas quotes for multiple sites by:

Automatically matching postcodes to Local Distribution Zones (LDZ)
Looking up base rates from supplier flat files
Calculating final pricing with configurable uplifts
Computing Total Annual Cost (TAC) and profit margins
Generating customer-ready quote exports

Features
Core Functionality

Multi-site quote generation - Add multiple sites to a single quote
Automatic LDZ matching - Postcodes automatically mapped to gas distribution zones
Base rate lookup - Retrieves supplier rates based on LDZ, consumption, and contract duration
Uplift calculations - Apply standing charge and unit rate uplifts with built-in caps
Margin analysis - Real-time profit margin calculations for sales visibility
Multiple contract terms - Support for 12, 24, and 36-month contracts
Carbon offset products - Separate pricing for carbon offset gas products

User Interface

Clean data grid - Professional column headers for agent use
Manual calculation - Calculate button prevents performance lag
Customer preview - Clean quote preview for client presentation
Excel export - One-click download of customer quotes
Reset functionality - Clear all data and start fresh

File Structure
apps/
├── directgas/
│   ├── logic/
│   │   ├── __init__.py
│   │   ├── base_rate_lookup.py     # Supplier rate lookup logic
│   │   ├── ldz_lookup.py           # Postcode to LDZ mapping
│   │   ├── tac_calculator.py       # Total Annual Cost calculations
│   │   ├── flat_file_loader.py     # Supplier data file handling
│   │   └── input_setup.py          # Data structure setup
│   ├── data/
│   │   └── postcode_ldz_full.csv   # Local postcode-to-LDZ mapping
│   └── app2.py                     # Main Streamlit application
└── shared/
    └── DYCE-DARK BG.png           # Company logo
Installation & Setup
Prerequisites

Python 3.8+
Streamlit
Pandas
PIL (Python Imaging Library)
xlsxwriter

Installation

Clone or download the application files
Install required packages:
bashpip install streamlit pandas pillow xlsxwriter

Ensure the file structure matches the layout above
Verify the postcode LDZ file exists at apps/directgas/data/postcode_ldz_full.csv

Running the Application
bashstreamlit run apps/directgas/app2.py
Usage Guide
Step 1: Upload Supplier Data

Launch the application
Upload your supplier flat file (XLSX format)
The system will validate and load the pricing data

Step 2: Configure Quote

Customer Name: Enter the client name for the quote
Product Type: Choose between "Standard Gas" or "Carbon Off"
Output Filename: Set the export filename (defaults to "dyce_quote")

Step 3: Add Sites
Use the form to add sites individually:

MPXN: Site identifier or meter point reference
Post Code: Site postcode (automatically matched to LDZ)
Annual Consumption: Annual gas consumption in kWh

Step 4: Edit and Calculate

Use the data grid to:

Edit site details
Add standing charge uplifts (max 100p/day)
Add unit rate uplifts (max 3.000p/kWh)


Click "🔄 Calculate Rates" to update all calculations
Review the calculated fields:

Base rates (from supplier data)
Final sell rates (base + uplift)
TAC (Total Annual Cost)
Profit margins



Step 5: Export Quote

Review the customer quote preview
Click "📥 Download Customer Quote" to export Excel file
The export includes both customer-facing and internal data sheets

Data Specifications
Supplier Flat File Format
The uploaded XLSX file must contain these columns:

LDZ: Local Distribution Zone code
Contract_Duration: Contract length in months (12, 24, or 36)
Minimum_Annual_Consumption: Lower consumption band limit
Maximum_Annual_Consumption: Upper consumption band limit
Carbon_Offset: Boolean for carbon offset products
Standing_Charge: Base standing charge in pence per day
Unit_Rate: Base unit rate in pence per kWh

LDZ Reference Data

Local file: apps/directgas/data/postcode_ldz_full.csv
Contains UK postcode to LDZ mappings
Postcodes standardized (uppercase, no spaces)
Supports prefix matching for postcode lookup

Business Logic
Pricing Calculations

LDZ Matching: Postcode mapped to distribution zone using longest-match algorithm
Base Rate Lookup: LDZ + consumption + duration matched against supplier data
Uplift Application: User-defined uplifts added to base rates (with caps)
TAC Calculation: (Standing Charge × 365 + Unit Rate × Consumption) ÷ 100
Margin Calculation: Difference between uplifted and base TAC

Validation Rules

Standing Charge Uplift: Maximum 100.0p per day
Unit Rate Uplift: Maximum 3.000p per kWh
Consumption: Must be positive number
Postcode: Must exist in LDZ database

Technical Notes
Performance Optimizations

Manual calculation trigger: Prevents recalculation on every keystroke
Local data files: No network calls during operation
Streamlit caching: LDZ data cached for performance

Error Handling

Missing postcodes: Clear error messages with validation
Invalid consumption: Defaults to zero with user warning
File format issues: Validation on supplier file upload
Empty fields: Graceful handling of incomplete data

Data Privacy

No external API calls: All processing happens locally
No data persistence: Session data cleared on reset
Local file processing: Supplier data never leaves the application

Troubleshooting
Common Issues
"Postcode not found" errors:

Verify postcode format and spelling
Check if postcode exists in LDZ reference file
Try shorter postcode variants (e.g., "M1 1" instead of "M1 1AA")

Calculation not updating:

Click the "🔄 Calculate Rates" button after making changes
Check that consumption values are positive numbers
Verify supplier flat file contains matching LDZ data

Export issues:

Ensure at least one complete site exists (MPXN, postcode, consumption)
Check browser download settings
Try refreshing the page and recalculating

Performance issues:

Keep site count reasonable (< 100 sites per quote)
Use the manual calculate button instead of auto-calculation
Clear data and restart if session becomes slow

File Path Issues
If the app cannot find reference files:

Verify the postcode LDZ file exists at the correct path
Check file permissions and accessibility
Ensure the working directory is set correctly

Support
For technical issues or feature requests, contact the development team with:

Error messages (if any)
Steps to reproduce the issue
Screenshots of unexpected behavior
Sample data files (if applicable)

Version History
Final Version Features:

Professional column headers (MPXN, etc.)
Local data files (no network dependencies)
Manual calculation trigger
Clean customer quote preview
Excel export functionality
Comprehensive error handling


Direct Sales Gas Tool - Streamlined multi-site gas quoting for energy sales teams