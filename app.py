import streamlit as st
import pandas as pd
import re
import io

# 1. App Header Configuration
st.set_page_config(page_title="Gym Past Due Report Generator", page_icon="💪", layout="centered")
st.title("🏋️‍♂️ Gym Past Due Report Generator")
st.write("Upload the raw Excel spreadsheet below to automatically generate your clean contact list.")

# 2. Sidebar Configuration for Gym Selection
gym_prefix = st.sidebar.selectbox(
    "Select Gym Location",
    ["LHI", "SDY", "FTU", "MCK", "TSQ", "KTY", "SST", "MEM", "SODO"]
)

# 3. File Uploader Component
uploaded_file = st.file_uploader("Choose the raw Excel file (e.g., SODO_JUN 2026.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Normalize naming conventions to prevent case mismatches
        filename = uploaded_file.name.upper()
        clean_prefix = gym_prefix.upper()
        
        # Flexibly match spaces or underscores in the filename
        match = re.search(f'{clean_prefix}[_\\s](.*?)\\.XLSX', filename)
        month_str = match.group(1).strip().replace(' ', '_') if match else 'REPORT_MONTH'
        
        st.success(f"Successfully loaded: **{uploaded_file.name}**")

        # 4. Load Data from the uploaded file buffer
        df_report = pd.read_excel(uploaded_file, sheet_name=0)
        df_month = pd.read_excel(uploaded_file, sheet_name=1)
        
        xl = pd.ExcelFile(uploaded_file)
        st.info(f"Comparing data between sheet tabs: **'{xl.sheet_names[0]}'** and **'{xl.sheet_names[1]}'**")

        # Standardize raw column names to lowercase
        df_report.columns = df_report.columns.str.strip().str.lower()
        df_month.columns = df_month.columns.str.strip().str.lower()

        # Ensure numeric balances exist under standard names
        df_report['past due balance'] = pd.to_numeric(df_report['past due balance'], errors='coerce').fillna(0)
        df_month['past due balance'] = pd.to_numeric(df_month['past due balance'], errors='coerce').fillna(0)

        # 5. Core Processing & Merging
        merged = df_month.merge(df_report, on='email', how='outer', suffixes=('_month', '_report'), indicator=True)
        
        # Core structured output column names (Notice: spaces used consistently)
        col_names = ['payment status', 'last name', 'first name', 'email', 'contact numbers', 'recent activity', 'last visit', 'past due balance']

        # --- PAID CUSTOMERS ---
        paid_cust = merged[merged['_merge'] == 'left_only'].copy()
        paid_cust['payment status_month'] = 'paid'
        paid_cust = paid_cust[['payment status_month', 'last name_month', 'first name_month', 'email', 
                               'contact numbers_month', 'recent activity_month', 'last visit_month', 'past due balance_month']]
        paid_cust.columns = col_names

        # --- UNPAID CUSTOMERS ---
        unpaid_cust = merged[merged['_merge'] == 'both'].copy()
        unpaid_cust['payment status_month'] = 'unpaid'
        unpaid_cust = unpaid_cust[['payment status_month', 'last name_month', 'first name_month', 'email', 
                                   'contact numbers_month', 'recent activity_month', 'last visit_month', 'past due balance_month']]
        unpaid_cust.columns = col_names

        # --- ADDED CUSTOMERS ---
        add_cust = merged[merged['_merge'] == 'right_only'].copy()
        add_cust['payment status_report'] = 'add'
        add_cust = add_cust[['payment status_report', 'last name_report', 'first name_report', 'email', 
                             'contact numbers_report', 'recent activity_report', 'last visit_report', 'past due balance_report']]
        add_cust.columns = col_names

        # Combine all processed segments together
        final_list = pd.concat([paid_cust, unpaid_cust, add_cust], ignore_index=True)

        # 6. Display Metrics
        st.subheader("📊 Report Summary Metrics")
        metrics_col1, metrics_col2 = st.columns(2)
        
        with metrics_col1:
            # FIX: Adjusted key mapping to match exactly ('past due balance')
            st.metric(label="Amount Recovered", value=f"${int(paid_cust['past due balance'].sum()):,}")
        with metrics_col2:
            # FIX: Adjusted key mapping here as well
            remaining_bal = final_list[final_list['payment status'] != 'paid']['past due balance'].sum()
            st.metric(label="Total Remaining Balance", value=f"${int(remaining_bal):,}")

        # Preview Data Table
        st.subheader("👀 Preview Cleaned Data (First 5 Rows)")
        st.dataframe(final_list.head())

        # 7. Convert DataFrame back to CSV bytes for download button
        csv_buffer = io.StringIO()
        final_list.to_csv(csv_buffer, index=False)
        csv_bytes = csv_buffer.getvalue()

        # Dynamic Download Button
        st.download_button(
            label="⬇️ Download Cleaned CSV Report",
            data=csv_bytes,
            file_name=f"{gym_prefix}_{month_str}_Past_Due_Contact_List.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"An error occurred: {e}. Please check that your selected Gym Prefix matches the uploaded file format.")
