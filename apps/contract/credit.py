# ======================================================================================
# 🔴 SECTION: METADATA, STYLE, LOGO
# ======================================================================================
import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from fpdf import FPDF

st.set_page_config(page_title="Dyce Contract Decision Engine V2", layout="wide")

VERSION = "2.0 - July 2025"
LOGO_PATH = "shared/DYCE-DARK BG.png"
CONFIG_URL = "inputs/Credit_Decision_Config_Template.xlsx"
SIC_CODES_URL = "inputs/Sic Codes.xlsx"

st.markdown("""
    <style>
        .stApp { background-color: white; color: rgb(15,42,52); }
        label { color: rgb(15,42,52) !important; }
        div.stButton > button, div.stDownloadButton > button {
            background-color: rgb(222,0,185) !important; color: white !important;
        }
        div.stRadio > div > label > div[data-testid="stMarkdownContainer"] > p {
            color: rgb(15,42,52) !important;
        }
        div.stCheckbox > label > div[data-testid="stMarkdownContainer"] > p {
            color: rgb(15,42,52) !important;
        }
        div.stCheckbox > label {
            color: rgb(15,42,52) !important;
        }
    </style>
""", unsafe_allow_html=True)

st.image(LOGO_PATH, width=200)

st.title(f"⚡ Dyce Contract Decision Engine (v{VERSION})")


# ======================================================================================
# 🔴 SECTION: LOAD CONFIGURATION + APPROVAL MATRIX
# ======================================================================================
@st.cache_data
def load_config():
    config_df = pd.read_excel(CONFIG_URL, sheet_name='CreditCriteria')
    approval_df = pd.read_excel(CONFIG_URL, sheet_name='ApprovalMatrix')

    config = {
        row['Parameter']: {
            'min': float(row['Min Value']),
            'max': float(row['Max Value'])
        }
        for _, row in config_df.iterrows()
    }

    numeric_columns = [
        'Min sites', 'Max Sites',
        'Min Annual Spend', 'Max Annual Spend',  # Fixed typo here
        'Min Annual Volume (kWh)', 'Max Annual Volume (kWh)'
    ]

    for col in numeric_columns:
        approval_df[col] = (
            approval_df[col]
            .astype(str)
            .str.replace('[^\\d.]', '', regex=True)
            .astype(float)
        )

    return config, approval_df

@st.cache_data
def load_sic_codes():
    df = pd.read_excel(SIC_CODES_URL)
    df['SIC_Code'] = df['SIC_Code'].astype(str).str.strip()
    return df

config, approval_matrix_df = load_config()
sic_df = load_sic_codes()


# ======================================================================================
# 🔴 SECTION: USER INPUTS (BUSINESS, SIC, CREDIT)
# ======================================================================================

st.header("1️⃣ Business Information")
business_type = st.selectbox("Business Type", ["Sole Trader", "Partnership", "Limited Company", "Limited Liability Partnership (LLP)", "Public Limited Company (PLC)", "Community Interest Company (CIC)", "Charity", "Co-operative"])
number_of_sites = st.number_input("Number of Sites", 1)
annual_volume_kwh = st.number_input("Estimated Annual Volume (kWh)", 0.0)
contract_value = st.number_input("Total Contract Spend (£)", 0.0)
contract_term = st.number_input("Contract Term (Years)", 1, 10)
unit_margin_ppkwh = st.number_input("Proposed Unit Margin (p/kWh)", 0.0)
broker_uplift_standing = st.number_input("Broker Uplift - Standing Charge (p/day)", 0.0)
broker_uplift_unit_rate = st.number_input("Broker Uplift - Unit Rate (p/kWh)", 0.0)

st.header("2️⃣ SIC Code Information")
sic_code = st.text_input("SIC Code (5-digit)").strip()
sic_risk = "Medium"
sic_description = "Unknown"

if sic_code:
    matched = sic_df[sic_df['SIC_Code'] == sic_code]
    if not matched.empty:
        sic_description = matched.iloc[0]['SIC_Description']
        sic_risk = matched.iloc[0]['Typical_Risk_Rating']
        st.markdown(f"**SIC Description:** {sic_description}")
        st.markdown(f"**Typical Risk Rating:** {sic_risk}")
    else:
        st.warning("SIC Code not found. Please manually select risk.")
        sic_risk = st.selectbox("Manual Sector Risk", ["Low", "Medium", "High", "Very High"], index=1)

st.header("3️⃣ Credit Information")
credit_score = st.number_input("Creditsafe Score", 0, 100)
years_trading = st.number_input("Years Trading", 0)
ccjs = st.selectbox("Any CCJs/Defaults in last 2 years?", ["No", "Yes"])
payment_terms = st.selectbox("Requested Payment Terms", ["Direct Debit", "BACS"])


# ======================================================================================
# 🔴 SECTION: DECISION ENGINE LOGIC
# ======================================================================================
def run_decision():
    reasons = []
    decision = "Approved"  # Start with approved

    # Check for decline conditions first
    if credit_score < config['refer_threshold']['min']:
        decision = "Declined"
        reasons.append("Declined: Credit Score below referral threshold")
    if ccjs == "Yes":
        decision = "Declined"
        reasons.append("Declined: CCJs or Defaults present")

    # If not declined, check all criteria for referral reasons
    if decision != "Declined":
        if config['refer_threshold']['min'] <= credit_score < config['approve_threshold']['min']:
            reasons.append("Referral: Credit Score between thresholds")

        if (business_type in ["Sole Trader", "Partnership"] and years_trading < 1) or (business_type == "Limited Company" and years_trading < 2):
            reasons.append("Referral: Insufficient trading history")

        if sic_risk in ["High", "Very High"]:
            reasons.append("Referral: SIC Risk is High/Very High")

        if payment_terms != "Direct Debit":
            reasons.append("Referral: Payment terms - BACS selected")

        if unit_margin_ppkwh < config['minimum_unit_margin_ppkwh']['min']:
            reasons.append("Referral: Unit Margin below minimum")

        if broker_uplift_standing > config['max_broker_uplift_standing']['max']:
            reasons.append("Referral: Standing charge uplift exceeds maximum")

        if broker_uplift_unit_rate > config['max_broker_uplift_unit_rate']['max']:
            reasons.append("Referral: Unit rate uplift exceeds maximum")

        # If ANY referral reasons exist, change decision to Referral
        if any("Referral:" in reason for reason in reasons):
            decision = "Referral"

    if decision == "Declined":
        required_approver = None
    elif contract_value >= 1000000:
        # Any deal £1M+ always goes to Managing Director
        required_approver = "Managing Director"
    elif decision == "Approved":
        # Deal under £1M that passes all criteria = no approver needed
        required_approver = "Auto-Approved"
    else:
        # Deal under £1M with referral reasons = refer to appropriate level
        if contract_value <= 250000:
            required_approver = "Sales Admin"
        elif contract_value <= 500000:
            required_approver = "TPI/ Direct Sales Manager"
        else:  # contract_value <= 1000000
            required_approver = "Commercial Manager"

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return decision, required_approver, reasons, timestamp


# ======================================================================================
# 🔴 SECTION: PDF EXPORT + RESULTS DISPLAY
# ======================================================================================
class PDF(FPDF):
    def header(self):
        self.image(LOGO_PATH, x=10, y=8, w=50)
        self.ln(35)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(15, 42, 52)
        self.cell(0, 10, f'Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 0, 'C')

def export_to_pdf(inputs, decision, approver, reasons, timestamp):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(15, 42, 52)
    pdf.cell(0, 10, 'Dyce Credit Decision Report', ln=True, align='C')
    pdf.ln(10)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Inputs Summary:', ln=True)
    pdf.set_font('Arial', '', 12)
    for k, v in inputs.items():
        pdf.multi_cell(0, 10, f"{k}: {v}")

    pdf.ln(5)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Decision:', ln=True)
    pdf.set_font('Arial', '', 12)
    pdf.multi_cell(0, 10, f"Decision: {decision}\nApprover Required: {approver if approver else 'N/A'}\nTimestamp: {timestamp}")

    pdf.ln(5)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Reasons / Stipulations:', ln=True)
    pdf.set_font('Arial', '', 12)
    for reason in reasons:
        pdf.multi_cell(0, 10, f"- {reason}")

    pdf_bytes = pdf.output(dest='S').encode('latin1')
    return BytesIO(pdf_bytes)

if st.button("Run Decision Engine"):
    inputs = {
        'Business Type': business_type,
        'Number of Sites': number_of_sites,
        'Annual Volume': annual_volume_kwh,
        'Contract Value': contract_value,
        'Contract Term': contract_term,
        'Unit Margin': unit_margin_ppkwh,
        'Broker Uplift Standing': broker_uplift_standing,
        'Broker Uplift Unit Rate': broker_uplift_unit_rate,
        'SIC Code': sic_code,
        'SIC Description': sic_description,
        'SIC Risk': sic_risk,
        'Credit Score': credit_score,
        'Years Trading': years_trading,
        'CCJs': ccjs,
        'Payment Terms': payment_terms
    }

    final_decision, required_approver, reasons, timestamp = run_decision()

    st.subheader("Decision Results")
    st.write(f"**Final Decision:** {final_decision}")
    if required_approver:
        st.write(f"**Required Approver:** {required_approver}")
        
        # Email actions based on approver level
        if required_approver == "Managing Director":
            st.info("📧 **Action Required:** Please email this decision report to: **TenderApprovals@dyce-energy.co.uk**")
        
        elif required_approver == "Sales Admin":
            st.success("✅ **No approval required** - Sales Admin level (default authorization)")
            
        elif required_approver in ["TPI/ Direct Sales Manager", "Commercial Manager"]:
            st.warning("📋 **Next Step:** This referral requires approval. Please email the decision report to the appropriate approver.")
            
            # Email dropdown for manager levels only
            email_options = {
                "TPI/ Direct Sales Manager": "dan.owen@dyce-energy.co.uk", 
                "Commercial Manager": "chris.beardsmore@dyce-energy.co.uk"
            }
            
            if required_approver in email_options:
                selected_email = email_options[required_approver]
                st.info(f"📧 **Email to:** {selected_email}")
                
                # Add mailto link
                subject = f"Credit Decision Approval Required - {datetime.now().strftime('%Y%m%d')}"
                mailto_link = f"mailto:{selected_email}?subject={subject}&body=Please find attached credit decision report requiring approval."
                st.markdown(f"[📧 Open Email Client]({mailto_link})")
    
    st.write(f"**Timestamp:** {timestamp}")

    st.markdown("**Reasons / Stipulations:**")
    for reason in reasons:
        st.markdown(f"- {reason}")

    pdf_data = export_to_pdf(inputs, final_decision, required_approver, reasons, timestamp)
    st.download_button("Download PDF Report", pdf_data, "Credit_Decision_Report.pdf", "application/pdf")
