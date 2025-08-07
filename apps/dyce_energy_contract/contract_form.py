import streamlit as st
import pandas as pd
import json
from datetime import date, datetime
import io

# Page configuration
st.set_page_config(
    page_title="Dyce Energy - Contract Acceptance",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling with brand colors
st.markdown("""
<style>
    /* Brand Colors:
       Blue: rgb(154, 252, ???) - need clarification, using reasonable blue
       Pink: rgb(222, 0, 185) = #de00b9
    */
    
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
    
    .utility-section:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
    }
    
    .gas-section {
        border-color: #4A90E2;
        background: linear-gradient(145deg, #f8fcff 0%, #e3f2fd 100%);
    }
    
    .electricity-section {
        border-color: #de00b9;
        background: linear-gradient(145deg, #fdf2f8 0%, #f3e8ff 100%);
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #4A90E2 0%, #357ABD 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.75rem 2rem;
        font-weight: bold;
        font-size: 1.1rem;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #357ABD 0%, #2563EB 100%);
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(74, 144, 226, 0.4);
    }
    
    /* Form submit button special styling */
    div[data-testid="stForm"] .stButton > button {
        background: linear-gradient(135deg, #de00b9 0%, #b8008a 100%);
        width: 100%;
        padding: 1rem 2rem;
        font-size: 1.2rem;
        margin-top: 1rem;
    }
    
    div[data-testid="stForm"] .stButton > button:hover {
        background: linear-gradient(135deg, #b8008a 0%, #9a0073 100%);
        box-shadow: 0 8px 25px rgba(222, 0, 185, 0.4);
    }
    
    .success-message {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border: 2px solid #28a745;
        color: #155724;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        box-shadow: 0 4px 16px rgba(40, 167, 69, 0.2);
    }
    
    .info-message {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border: 2px solid #4A90E2;
        color: #1565c0;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        box-shadow: 0 4px 16px rgba(74, 144, 226, 0.2);
    }
    
    /* Streamlit specific customizations */
    .stSelectbox > div > div {
        border: 2px solid #ddd;
        border-radius: 6px;
        transition: border-color 0.3s ease;
    }
    
    .stSelectbox > div > div:focus-within {
        border-color: #4A90E2;
        box-shadow: 0 0 0 2px rgba(74, 144, 226, 0.2);
    }
    
    .stTextInput > div > div > input {
        border: 2px solid #ddd;
        border-radius: 6px;
        transition: border-color 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #4A90E2;
        box-shadow: 0 0 0 2px rgba(74, 144, 226, 0.2);
    }
    
    .stNumberInput > div > div > input {
        border: 2px solid #ddd;
        border-radius: 6px;
        transition: border-color 0.3s ease;
    }
    
    .stNumberInput > div > div > input:focus {
        border-color: #de00b9;
        box-shadow: 0 0 0 2px rgba(222, 0, 185, 0.2);
    }
    
    /* Header customization */
    .main .block-container {
        padding-top: 1rem;
        max-width: 1200px;
    }
    
    /* Radio button styling */
    .stRadio > div {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
    }
    
    /* Checkbox styling */
    .stCheckbox > label {
        font-weight: 500;
        color: #2c3e50;
    }
    
    /* Sidebar hide */
    .css-1d391kg {
        display: none;
    }
    
    /* Custom metric styling */
    .metric-container {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #4A90E2;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'form_submitted' not in st.session_state:
    st.session_state.form_submitted = False

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>⚡ Dyce Energy</h1>
        <h2>Contract Acceptance Form</h2>
        <p>Energy Supply Agreement - Please complete all sections</p>
        <div style="margin-top: 1rem; padding: 0.5rem; background: rgba(222, 0, 185, 0.1); border-radius: 5px; display: inline-block;">
            <strong>✨ Streamlit Powered</strong>
        </div>
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
            st.write("")  # Spacer
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
            st.write("")  # Spacer
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
            st.write("")  # Spacer for alignment
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
            st.write("")  # Spacer
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
            st.write("")  # Spacer
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
            st.write("")  # Spacer
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
            # Collect all required fields
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
                    st.download_button(
                        label="📊 Download as Excel",
                        data=excel_data,
                        file_name=f"contract_{contract_ref}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

if __name__ == "__main__":
    main()# TPI Details
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
                
                # Display success message
                st.success("✅ Contract submitted successfully!")
                
                contract_ref = form_data['contract_reference']
                st.markdown(f"""
                <div class="success-message">
                    <h3>🎉 Submission Successful!</h3>
                    <p><strong>Contract Reference:</strong> {contract_ref}</p>
                    <p><strong>Submission Time:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                    <p><strong>Estimated TPI Commission:</strong> £{estimated_commission:.2f}</p>
                    <p>You will receive a confirmation email shortly.</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Convert to DataFrame for display
                df = pd.DataFrame([form_data])
                
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
                
                # Provide download options
                st.subheader("📥 Download Contract Data")
                
                col_dl1, col_dl2 = st.columns(2)
                with col_dl1:
                    # JSON download
                    json_str = json.dumps(form_data, indent=2, default=str)
                    st.download_button(
                        label="📄 Download as JSON",
                        data=json_str,
                        file_name=f"contract_{contract_ref}.json",
                        mime="application/json"
                    )
                
                with col_dl2:
                    # Excel download
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, sheet_name='Contract_Data', index=False)
                    excel_data = output.getvalue()
                    
                 
