import streamlit as st
import pandas as pd
import json
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import date, datetime
import io
import os

# Page configuration
st.set_page_config(
    page_title="Dyce Energy - Contract Acceptance",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Database setup
def init_database():
    conn = sqlite3.connect('contracts.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_reference TEXT UNIQUE NOT NULL,
            submission_timestamp TEXT NOT NULL,
            tpi_business_name TEXT,
            tpi_first_name TEXT,
            tpi_last_name TEXT,
            tpi_contact_email TEXT,
            site_business_name TEXT,
            site_contact_email TEXT,
            gas_contract_length INTEGER,
            elec_contract_length INTEGER,
            estimated_commission REAL,
            form_data TEXT,
            email_sent BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    return conn

# Email function
def send_contract_email(contract_data, contract_ref):
    try:
        smtp_server = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
        smtp_port = int(os.getenv('EMAIL_PORT', '587'))
        email_user = os.getenv('EMAIL_USER')
        email_pass = os.getenv('EMAIL_PASS')
        office_email = os.getenv('OFFICE_EMAIL')
        
        if not all([email_user, email_pass, office_email]):
            st.warning("Email configuration not complete. Contract saved locally.")
            return False
        
        msg = MIMEMultipart()
        msg['From'] = email_user
        msg['To'] = office_email
        msg['Subject'] = f"New Energy Contract - {contract_ref}"
        
        body = f"""
New Energy Contract Submission
============================

Contract Reference: {contract_ref}
Submission Time: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

TPI Details:
- Business: {contract_data.get('tpi_business_name', 'N/A')}
- Contact: {contract_data.get('tpi_first_name', '')} {contract_data.get('tpi_last_name', '')}
- Email: {contract_data.get('tpi_contact_email', 'N/A')}

Client Details:
- Business: {contract_data.get('site_business_name', 'N/A')}
- Contact: {contract_data.get('site_first_name', '')} {contract_data.get('site_last_name', '')}
- Email: {contract_data.get('site_contact_email', 'N/A')}

Contract Summary:
- Gas Contract: {contract_data.get('gas_contract_length', 0)} months
- Electricity Contract: {contract_data.get('elec_contract_length', 0)} months
- Estimated Commission: £{contract_data.get('estimated_commission', 0):.2f}

Full details attached.

Best regards,
Dyce Energy Contract System
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach JSON
        json_data = json.dumps(contract_data, indent=2, default=str)
        json_attachment = MIMEApplication(json_data.encode('utf-8'), _subtype='json')
        json_attachment.add_header('Content-Disposition', f'attachment; filename={contract_ref}.json')
        msg.attach(json_attachment)
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_user, email_pass)
        server.send_message(msg)
        server.quit()
        
        return True
        
    except Exception as e:
        st.error(f"Email failed: {str(e)}")
        return False

# Save to database
def save_contract_to_db(conn, contract_data, contract_ref):
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO contracts (
                contract_reference, submission_timestamp, tpi_business_name, 
                tpi_first_name, tpi_last_name, tpi_contact_email,
                site_business_name, site_contact_email, gas_contract_length,
                elec_contract_length, estimated_commission, form_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            contract_ref, contract_data['submission_timestamp'],
            contract_data.get('tpi_business_name'), contract_data.get('tpi_first_name'),
            contract_data.get('tpi_last_name'), contract_data.get('tpi_contact_email'),
            contract_data.get('site_business_name'), contract_data.get('site_contact_email'),
            contract_data.get('gas_contract_length'), contract_data.get('elec_contract_length'),
            contract_data.get('estimated_commission'), json.dumps(contract_data, default=str)
        ))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Database error: {str(e)}")
        return False

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        background: linear-gradient(135deg, #4A90E2 0%, #357ABD 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(74, 144, 226, 0.3);
    }
    
    .section-header {
        background: linear-gradient(135deg, #de00b9 0%, #b8008a 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1.5rem 0 1rem 0;
        font-weight: bold;
        box-shadow: 0 4px 16px rgba(222, 0, 185, 0.3);
    }
    
    .utility-section {
        border: 2px solid #e9ecef;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        transition: all 0.3s ease;
    }
    
    .gas-section {
        border-color: #4A90E2;
        background: linear-gradient(145deg, #f8fcff 0%, #e3f2fd 100%);
    }
    
    .electricity-section {
        border-color: #de00b9;
        background: linear-gradient(145deg, #fdf2f8 0%, #f3e8ff 100%);
    }
    
    div[data-testid="stForm"] .stButton > button {
        background: linear-gradient(135deg, #de00b9 0%, #b8008a 100%);
        color: white;
        width: 100%;
        padding: 1rem 2rem;
        font-size: 1.2rem;
        border-radius: 25px;
        border: none;
        font-weight: bold;
    }
    
    .success-message {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border: 2px solid #28a745;
        color: #155724;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .info-message {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border: 2px solid #4A90E2;
        color: #1565c0;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database
if 'db_initialized' not in st.session_state:
    conn = init_database()
    st.session_state.db_initialized = True
    st.session_state.db_connection = conn

def main():
    # Header with Logo
    col_logo, col_title = st.columns([1, 3])
    
    with col_logo:
        try:
            st.image("logo.png", width=150)
        except:
            st.markdown("⚡", unsafe_allow_html=True)
    
    with col_title:
        st.markdown("""
        <div style="padding-top: 2rem;">
            <h1 style="color: #4A90E2; margin-bottom: 0.5rem;">Dyce Energy</h1>
            <h2 style="color: #de00b9; margin-bottom: 0.5rem;">Contract Acceptance Form</h2>
            <p style="color: #666; font-size: 1.1rem;">Energy Supply Agreement - Please complete all sections</p>
        </div>
        """, unsafe_allow_html=True)

    # Create form
    with st.form("energy_contract_form", clear_on_submit=False):
        
        # TPI Details Section
        st.markdown('<div class="section-header">🏢 TPI Details</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            tpi_business_name = st.text_input("Business Name *", key="tpi_business_name")
            tpi_first_name = st.text_input("First Name *", key="tpi_first_name")
        with col2:
            st.write("")
            tpi_last_name = st.text_input("Last Name *", key="tpi_last_name")
        
        col3, col4 = st.columns(2)
        with col3:
            tpi_contact_tel = st.text_input("Contact Tel *", key="tpi_contact_tel")
        with col4:
            tpi_contact_email = st.text_input("Contact Email *", key="tpi_contact_email")

        # Meter Details Section
        st.markdown('<div class="section-header">📊 Meter Details</div>', unsafe_allow_html=True)
        
        col5, col6 = st.columns(2)
        with col5:
            st.markdown('<div class="utility-section gas-section"><h4>🔥 Gas</h4></div>', unsafe_allow_html=True)
            gas_meter_ref = st.text_input("Meter Point Ref No", key="gas_meter_ref")
            
        with col6:
            st.markdown('<div class="utility-section electricity-section"><h4>⚡ Electricity</h4></div>', unsafe_allow_html=True)
            elec_mpan = st.text_input("Meter Point Administration Number", key="elec_mpan")

        # Supply Site Details Section
        st.markdown('<div class="section-header">🏢 Supply Site Details</div>', unsafe_allow_html=True)
        
        col7, col8 = st.columns(2)
        with col7:
            site_business_name = st.text_input("Business Name *", key="site_business_name")
            site_first_name = st.text_input("First Name *", key="site_first_name")
            site_contact_email = st.text_input("Contact Email *", key="site_contact_email")
        with col8:
            st.write("")
            site_last_name = st.text_input("Last Name *", key="site_last_name")
            site_contact_tel = st.text_input("Contact Tel *", key="site_contact_tel")

        st.subheader("📍 Address Details")
        col9, col10 = st.columns(2)
        with col9:
            building_no = st.text_input("Building No", key="building_no")
            address_1 = st.text_input("Address 1 *", key="address_1")
            town = st.text_input("Town *", key="town")
        with col10:
            building_name = st.text_input("Building Name", key="building_name")
            st.write("")
            city = st.text_input("City *", key="city")
        
        post_code = st.text_input("Post Code *", key="post_code")

        # Contract Details Section
        st.markdown('<div class="section-header">📋 Contract Details</div>', unsafe_allow_html=True)
        
        col11, col12 = st.columns(2)
        
        with col11:
            st.markdown('<div class="utility-section gas-section"><h4>🔥 Gas Contract</h4></div>', unsafe_allow_html=True)
            gas_contract_length = st.number_input("Contract Length (Months)", min_value=1, max_value=60, value=12, key="gas_contract_length")
            gas_standing_charge = st.number_input("Standing Charge (P/day)", min_value=0.0, format="%.2f", key="gas_standing_charge")
            gas_unit_rate = st.number_input("Unit Rate (P/kWh)", min_value=0.0, format="%.3f", key="gas_unit_rate")
            gas_annual_usage = st.number_input("Annual Usage AQ (kWh)", min_value=0, key="gas_annual_usage")
            gas_start_date = st.date_input("Proposed Gas Supply Start Date", key="gas_start_date")
            gas_current_end = st.date_input("Current Contract End Date", key="gas_current_end")
            
        with col12:
            st.markdown('<div class="utility-section electricity-section"><h4>⚡ Electricity Contract</h4></div>', unsafe_allow_html=True)
            elec_contract_length = st.number_input("Contract Length (Months)", min_value=1, max_value=60, value=12, key="elec_contract_length")
            elec_standing_charge = st.number_input("Standing Charge (P/day)", min_value=0.0, format="%.2f", key="elec_standing_charge")
            elec_unit_rate_single = st.number_input("Single Rate (P/kWh)", min_value=0.0, format="%.3f", key="elec_unit_rate_single")
            elec_unit_rate_day = st.number_input("Day Rate (P/kWh)", min_value=0.0, format="%.3f", key="elec_unit_rate_day")
            elec_unit_rate_night = st.number_input("Night Rate (P/kWh)", min_value=0.0, format="%.3f", key="elec_unit_rate_night")
            elec_unit_rate_weekend = st.number_input("E/WE Rate (P/kWh)", min_value=0.0, format="%.3f", key="elec_unit_rate_weekend")
            elec_capacity_charge = st.number_input("Capacity Charge (P/kVa/day)", min_value=0.0, format="%.2f", key="elec_capacity_charge")
            elec_supply_capacity = st.number_input("Agreed Supply Capacity (kVa)", min_value=0, key="elec_supply_capacity")
            elec_metering_charge = st.number_input("Metering Charge (P/day)", min_value=0.0, format="%.2f", key="elec_metering_charge")
            elec_annual_usage = st.number_input("Annual Usage EAC (kWh)", min_value=0, key="elec_annual_usage")
            elec_start_date = st.date_input("Proposed Electric Supply Start Date", key="elec_start_date")
            elec_current_end = st.date_input("Current Contract End Date", key="elec_current_end")
        
        tariff_identifier = st.text_input("Tariff Identifier Code", key="tariff_identifier")

        # Credit Check Details Section
        st.markdown('<div class="section-header">🔍 Credit Check Details</div>', unsafe_allow_html=True)
        
        col13, col14 = st.columns(2)
        with col13:
            business_charity_number = st.text_input("Registered Business/Charity Number", key="business_charity_number")
        with col14:
            business_type = st.selectbox("Business Type *", 
                ["", "Limited Company", "Partnership", "Sole Trader", "Club", "Non-profit Organisation", "Charity", "Other"],
                key="business_type")

        st.subheader("Complete if sole trader / club / non-profit organisation")
        col15, col16 = st.columns(2)
        with col15:
            trader_first_name = st.text_input("First Name", key="trader_first_name")
            trader_dob = st.date_input("Date of Birth", key="trader_dob", value=None)
            trader_contact_email = st.text_input("Contact Email", key="trader_contact_email")
        with col16:
            trader_last_name = st.text_input("Last Name", key="trader_last_name")
            trader_contact_tel = st.text_input("Contact Tel", key="trader_contact_tel")

        st.subheader("📍 Home Address (Resident for Minimum Of 3 Years)")
        col17, col18 = st.columns(2)
        with col17:
            home_building_no = st.text_input("Building No", key="home_building_no")
            home_address_1 = st.text_input("Address 1", key="home_address_1")
            home_town = st.text_input("Town", key="home_town")
            home_post_code = st.text_input("Post Code", key="home_post_code")
        with col18:
            home_building_name = st.text_input("Building Name", key="home_building_name")
            st.write("")
            home_city = st.text_input("City", key="home_city")

        st.subheader("📍 Previous Home Address (If applicable)")
        col19, col20 = st.columns(2)
        with col19:
            prev_building_no = st.text_input("Building No", key="prev_building_no")
            prev_address_1 = st.text_input("Address 1", key="prev_address_1")
            prev_town = st.text_input("Town", key="prev_town")
            prev_post_code = st.text_input("Post Code", key="prev_post_code")
        with col20:
            prev_building_name = st.text_input("Building Name", key="prev_building_name")
            st.write("")
            prev_city = st.text_input("City", key="prev_city")

        # TPI Commission Details Section
        st.markdown('<div class="section-header">💰 TPI Commission Details</div>', unsafe_allow_html=True)
        
        col21, col22 = st.columns(2)
        with col21:
            tpi_sc_uplift_gas = st.number_input("TPI S/C Uplift Gas (P/day)", min_value=0.0, format="%.2f", key="tpi_sc_uplift_gas")
            tpi_unit_rate_uplift_gas = st.number_input("TPI Unit Rate Uplift Gas (P/kWh)", min_value=0.0, format="%.3f", key="tpi_unit_rate_uplift_gas")
        with col22:
            tpi_sc_uplift_elec = st.number_input("TPI S/C Uplift Electricity (P/day)", min_value=0.0, format="%.2f", key="tpi_sc_uplift_elec")
            tpi_unit_rate_uplift_elec = st.number_input("TPI Unit Rate Uplift Electricity (P/kWh)", min_value=0.0, format="%.3f", key="tpi_unit_rate_uplift_elec")

        # Calculate estimated commission
        gas_commission = ((tpi_sc_uplift_gas * 365 * (gas_contract_length/12)) + (tpi_unit_rate_uplift_gas * gas_annual_usage * (gas_contract_length/12))) / 100
        elec_commission = ((tpi_sc_uplift_elec * 365 * (elec_contract_length/12)) + (tpi_unit_rate_uplift_elec * elec_annual_usage * (elec_contract_length/12))) / 100
        estimated_commission = gas_commission + elec_commission

        st.markdown(f"**Estimated Contract TPI Commission: £{estimated_commission:.2f}**")

        # Additional Contract Options Section
        st.markdown('<div class="section-header">⚙️ Additional Contract Options</div>', unsafe_allow_html=True)
        
        col23, col24 = st.columns(2)
        with col23:
            advanced_saver = st.radio("Advanced Saver Tariff", ["", "Yes", "No"], key="advanced_saver")
            sale_type = st.radio("Sale Type", ["", "Acquisition", "Renewal"], key="sale_type")
        with col24:
            climate_agreement = st.radio("Climate Change Agreement", ["", "Yes", "No"], key="climate_agreement")
            additional_sites = st.radio("Additional Site/s Attached", ["", "Yes", "No"], key="additional_sites")

        # Payment Details Section
        st.markdown('<div class="section-header">💳 Payment Details</div>', unsafe_allow_html=True)
        
        col25, col26 = st.columns(2)
        with col25:
            billing_first_name = st.text_input("First Name *", key="billing_first_name")
            billing_contact_tel = st.text_input("Contact Tel *", key="billing_contact_tel")
        with col26:
            billing_last_name = st.text_input("Last Name *", key="billing_last_name")
            billing_contact_email = st.text_input("Contact Email *", key="billing_contact_email")

        st.subheader("📍 Billing Address")
        col27, col28 = st.columns(2)
        with col27:
            billing_building_no = st.text_input("Building No", key="billing_building_no")
            billing_address_1 = st.text_input("Address 1 *", key="billing_address_1")
            billing_town = st.text_input("Town *", key="billing_town")
        with col28:
            billing_building_name = st.text_input("Building Name", key="billing_building_name")
            st.write("")
            billing_city = st.text_input("City *", key="billing_city")
        
        billing_post_code = st.text_input("Post Code *", key="billing_post_code")
        billing_email_only = st.checkbox("Email Only Billing", key="billing_email_only")

        # Privacy Preferences Section
        st.markdown('<div class="section-header">🔒 Your Privacy</div>', unsafe_allow_html=True)
        st.markdown('<div class="info-message">Please select how you would like us to contact you:</div>', unsafe_allow_html=True)
        
        contact_mail = st.checkbox("By Mail", key="contact_mail")
        contact_telephone = st.checkbox("Telephone", key="contact_telephone")
        contact_sms = st.checkbox("SMS", key="contact_sms")
        contact_email = st.checkbox("Email", key="contact_email")

        # Terms and Conditions Section
        st.markdown('<div class="section-header">📝 Terms & Conditions</div>', unsafe_allow_html=True)
        
        terms_accepted = st.checkbox("I have read and accept the Terms & Conditions *", key="terms_accepted")
        
        st.subheader("✍️ Signature Details")
        col29, col30 = st.columns(2)
        with col29:
            signature_name = st.text_input("Print Name *", key="signature_name")
        with col30:
            job_title = st.text_input("Job Title *", key="job_title")
        
        signature_date = st.date_input("Date *", value=date.today(), key="signature_date")

        # Direct Debit Section
        st.markdown('<div class="section-header">🏦 Direct Debit Information</div>', unsafe_allow_html=True)
        st.markdown('<div class="info-message"><strong>Note:</strong> If you wish to set up a Direct Debit, this section will need to be completed separately with your bank details.</div>', unsafe_allow_html=True)
        
        dd_customer_name = st.text_input("Customer Name or Company Name", key="dd_customer_name")
        dd_account_holder = st.text_input("Name(s) of Account Holder(s)", key="dd_account_holder")
        dd_setup = st.checkbox("I wish to set up a Direct Debit (separate authorization required)", key="dd_setup")

        # Submit button
        submitted = st.form_submit_button("🚀 Submit Contract", use_container_width=True)
        
        # Validation and submission handling
        if submitted:
            # Collect required fields
            required_fields = {
                'TPI Business Name': tpi_business_name,
                'TPI First Name': tpi_first_name,
                'TPI Last Name': tpi_last_name,
                'TPI Contact Tel': tpi_contact_tel,
                'TPI Contact Email': tpi_contact_email,
                'Site Business Name': site_business_name,
                'Site First Name': site_first_name,
                'Site Last Name': site_last_name,
                'Site Contact Email': site_contact_email,
                'Site Contact Tel': site_contact_tel,
                'Address 1': address_1,
                'Town': town,
                'City': city,
                'Post Code': post_code,
                'Business Type': business_type,
                'Billing First Name': billing_first_name,
                'Billing Last Name': billing_last_name,
                'Billing Contact Tel': billing_contact_tel,
                'Billing Contact Email': billing_contact_email,
                'Billing Address 1': billing_address_1,
                'Billing Town': billing_town,
                'Billing City': billing_city,
                'Billing Post Code': billing_post_code,
                'Signature Name': signature_name,
                'Job Title': job_title
            }
            
            missing_fields = [field for field, value in required_fields.items() if not value]
            
            if missing_fields:
                st.error(f"Please fill in the following required fields: {', '.join(missing_fields)}")
            elif not terms_accepted:
                st.error("Please accept the Terms & Conditions to proceed.")
            else:
                # Collect all form data
                form_data = {
                    # TPI Details
                    'tpi_business_name': tpi_business_name,
                    'tpi_first_name': tpi_first_name,
                    'tpi_last_name': tpi_last_name,
                    'tpi_contact_tel': tpi_contact_tel,
                    'tpi_contact_email': tpi_contact_email,
                    
                    # Meter Details
                    'gas_meter_ref': gas_meter_ref,
                    'elec_mpan': elec_mpan,
                    
                    # Site Details
                    'site_business_name': site_business_name,
                    'site_first_name': site_first_name,
                    'site_last_name': site_last_name,
                    'site_contact_email': site_contact_email,
                    'site_contact_tel': site_contact_tel,
                    'building_no': building_no,
                    'building_name': building_name,
                    'address_1': address_1,
                    'town': town,
                    'city': city,
                    'post_code': post_code,
                    
                    # Contract Details
                    'gas_contract_length': gas_contract_length,
                    'gas_standing_charge': gas_standing_charge,
                    'gas_unit_rate': gas_unit_rate,
                    'gas_annual_usage': gas_annual_usage,
                    'gas_start_date': gas_start_date.isoformat() if gas_start_date else None,
                    'gas_current_end': gas_current_end.isoformat() if gas_current_end else None,
                    'elec_contract_length': elec_contract_length,
                    'elec_standing_charge': elec_standing_charge,
                    'elec_unit_rate_single': elec_unit_rate_single,
                    'elec_unit_rate_day': elec_unit_rate_day,
                    'elec_unit_rate_night': elec_unit_rate_night,
                    'elec_unit_rate_weekend': elec_unit_rate_weekend,
                    'elec_capacity_charge': elec_capacity_charge,
                    'elec_supply_capacity': elec_supply_capacity,
                    'elec_metering_charge': elec_metering_charge,
                    'elec_annual_usage': elec_annual_usage,
                    'elec_start_date': elec_start_date.isoformat() if elec_start_date else None,
                    'elec_current_end': elec_current_end.isoformat() if elec_current_end else None,
                    'tariff_identifier': tariff_identifier,
                    
                    # Credit Check
                    'business_charity_number': business_charity_number,
                    'business_type': business_type,
                    'trader_first_name': trader_first_name,
                    'trader_last_name': trader_last_name,
                    'trader_dob': trader_dob.isoformat() if trader_dob else None,
                    'trader_contact_tel': trader_contact_tel,
                    'trader_contact_email': trader_contact_email,
                    'home_building_no': home_building_no,
                    'home_building_name': home_building_name,
                    'home_address_1': home_address_1,
                    'home_town': home_town,
                    'home_city': home_city,
                    'home_post_code': home_post_code,
                    'prev_building_no': prev_building_no,
                    'prev_building_name': prev_building_name,
                    'prev_address_1': prev_address_1,
                    'prev_town': prev_town,
                    'prev_city': prev_city,
                    'prev_post_code': prev_post_code,
                    
                    # TPI Commission
                    'tpi_sc_uplift_gas': tpi_sc_uplift_gas,
                    'tpi_unit_rate_uplift_gas': tpi_unit_rate_uplift_gas,
                    'tpi_sc_uplift_elec': tpi_sc_uplift_elec,
                    'tpi_unit_rate_uplift_elec': tpi_unit_rate_uplift_elec,
                    'estimated_commission': estimated_commission,
                    
                    # Additional Options
                    'advanced_saver': advanced_saver,
                    'climate_agreement': climate_agreement,
                    'sale_type': sale_type,
                    'additional_sites': additional_sites,
                    
                    # Payment Details
                    'billing_first_name': billing_first_name,
                    'billing_last_name': billing_last_name,
                    'billing_contact_tel': billing_contact_tel,
                    'billing_contact_email': billing_contact_email,
                    'billing_building_no': billing_building_no,
                    'billing_building_name': billing_building_name,
                    'billing_address_1': billing_address_1,
                    'billing_town': billing_town,
                    'billing_city': billing_city,
                    'billing_post_code': billing_post_code,
                    'billing_email_only': billing_email_only,
                    
                    # Privacy
                    'contact_preferences': [pref for pref, selected in [
                        ('mail', contact_mail), ('telephone', contact_telephone),
                        ('sms', contact_sms), ('email', contact_email)
                    ] if selected],
                    
                    # Terms & Signature
                    'terms_accepted': terms_accepted,
                    'signature_name': signature_name,
                    'job_title': job_title,
                    'signature_date': signature_date.isoformat(),
                    
                    # Direct Debit
                    'dd_customer_name': dd_customer_name,
                    'dd_account_holder': dd_account_holder,
                    'dd_setup': dd_setup,
                    
                    # Metadata
                    'submission_timestamp': datetime.now().isoformat(),
                    'contract_reference': f"CA-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                }
                
                contract_ref = form_data['contract_reference']
                
                # Save to database
                conn = st.session_state.db_connection
                if save_contract_to_db(conn, form_data, contract_ref):
                    # Try to send email
                    email_sent = send_contract_email(form_data, contract_ref)
                    
                    # Display success message
                    st.success("✅ Contract submitted successfully!")
                    
                    st.markdown(f"""
                    <div class="success-message">
                        <h3>🎉 Submission Successful!</h3>
                        <p><strong>Contract Reference:</strong> {contract_ref}</p>
                        <p><strong>Submission Time:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                        <p><strong>Estimated TPI Commission:</strong> £{estimated_commission:.2f}</p>
                        <p><strong>Email Status:</strong> {"✅ Sent to office" if email_sent else "⚠️ Saved locally (email config needed)"}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show contract summary
                    with st.expander("📋 Contract Summary", expanded=True):
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.write("**Client Details:**")
                            st.write(f"Business: {site_business_name}")
                            st.write(f"Contact: {site_first_name} {site_last_name}")
                            st.write(f"Email: {site_contact_email}")
                            st.write(f"Phone: {site_contact_tel}")
                            
                            st.write("**Gas Contract:**")
                            st.write(f"Length: {gas_contract_length} months")
                            st.write(f"Standing Charge: {gas_standing_charge}p/day")
                            st.write(f"Unit Rate: {gas_unit_rate}p/kWh")
                            st.write(f"Annual Usage: {gas_annual_usage:,} kWh")
                            
                        with col_b:
                            st.write("**TPI Details:**")
                            st.write(f"Business: {tpi_business_name}")
                            st.write(f"Contact: {tpi_first_name} {tpi_last_name}")
                            st.write(f"Email: {tpi_contact_email}")
                            st.write(f"Commission: £{estimated_commission:.2f}")
                            
                            st.write("**Electricity Contract:**")
                            st.write(f"Length: {elec_contract_length} months")
                            st.write(f"Standing Charge: {elec_standing_charge}p/day")
                            st.write(f"Single Rate: {elec_unit_rate_single}p/kWh")
                            st.write(f"Annual Usage: {elec_annual_usage:,} kWh")
                    
                    # Download options
                    st.subheader("📥 Download Contract Data")
                    
                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        json_str = json.dumps(form_data, indent=2, default=str)
                        st.download_button(
                            label="📄 Download as JSON",
                            data=json_str,
                            file_name=f"contract_{contract_ref}.json",
                            mime="application/json"
                        )
                    
                    with col_dl2:
                        df = pd.DataFrame([form_data])
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df.to_excel(writer, sheet_name='Contract_Data', index=False)
                        excel_data = output.getvalue()
                        
                        st.download_button(
                            label="📊 Download as Excel",
                            data=excel_data,
                            file_name=f"contract_{contract_ref}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

    # Admin Dashboard (optional - in sidebar)
    if st.sidebar.button("📊 Admin Dashboard"):
        st.sidebar.markdown("---")
        
        conn = st.session_state.db_connection
        cursor = conn.cursor()
        
        # Get stats
        cursor.execute("SELECT COUNT(*) FROM contracts")
        total_contracts = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(estimated_commission) FROM contracts WHERE estimated_commission IS NOT NULL")
        total_commission = cursor.fetchone()[0] or 0
        
        st.sidebar.metric("Total Contracts", total_contracts)
        st.sidebar.metric("Total Commission", f"£{total_commission:,.2f}")
        
        # Recent submissions
        st.sidebar.markdown("**Recent Submissions:**")
        cursor.execute("""
            SELECT contract_reference, tpi_business_name, estimated_commission, 
                   DATE(created_at) as submission_date
            FROM contracts 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        
        recent = cursor.fetchall()
        for row in recent:
            st.sidebar.text(f"{row[0][:8]}... - £{row[2] or 0:.0f}")

if __name__ == "__main__":
    main()
