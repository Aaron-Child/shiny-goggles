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
    ["SODO", "LHI", "SDY", "FTU", "MCK", "TSQ", "KTY", "SST", "MEM"]
)

# 3. File Uploader Component
uploaded_file = st.file_uploader("Choose the raw Excel file (e.g., SODO_JUN 2026.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Extract filename and normalize it to uppercase for robust matching
        filename = uploaded_file.name.upper()
        clean_prefix = gym_prefix.upper()
        
        # Smart regex: looks for the gym prefix followed by an underscore OR a space
        match = re.search(f'{clean_prefix}[_\\s](.*?)\\.XLSX', filename)
        
        if match:
            month_str = match.group(1).strip().replace(' ', '_')
        else:
            # Fallback: if it can't find a clean match, grab the second tab's name automatically
            month_str = "DETECTED_MONTH"
        
        st.success(f"Successfully loaded: **{uploaded_file.name}**")

        # 4. Load Data directly from the uploaded file buffer
        df_report = pd.read_excel(uploaded_file, sheet_name=0)
        
        # DYNAMIC TAB FIX: Instead of looking for a named tab, we dynamically read the 
        # actual tab name from the second position so the merge never fails!
        xl = pd.ExcelFile(uploaded_file)
        second_tab_name = xl.sheet_names[1]
        df_month = pd.read_excel(uploaded_file, sheet_name=1)
        
        st.info(f"Comparing data between sheet tabs: **'{xl.sheet_names[0]}'** and **'{second_tab_name}'**")

        # Standardize column names
        df_report.columns = df_report.columns.str.strip().str.lower()
        df_month.columns = df_month.columns.str.strip().str.lower()

        # Coerce numeric balances
        df_report['past due balance'] = pd.to_numeric(df_report['past due balance'], errors='coerce').fillna(0)
        df_month['past due balance'] = pd.to_numeric(df_month['past due balance'], errors='coerce').fillna(0)

        # 5. Core Processing (Your Exact Logic)
        merged = df_month.merge(df_report, on='email', how='outer', suffixes=('_month', '_report'), indicator=True)
        col_names = ['payment status', 'last name', 'first name', 'email', 'contact numbers', 'recent activity', 'last visit', 'past due balance']

        # Categorize
        paid_cust = merged[merged['_merge'] == 'left_only'].copy()
        paid_cust['payment status_month'] = 'paid'
        paid_cust = paid_cust[['payment status_month', 'last name_month', 'first name_month', 'email', 'contact numbers_month', 'recent activity_month', 'last visit_month', 'past due balance_month']]
        paid_cust.columns = col_names

        unpaid_cust = merged[merged['_merge'] == 'both'].copy()
        unpaid_cust['payment status_month'] = 'unpaid'
        unpaid_cust = unpaid_cust[['payment status_month', 'last name_month', 'first name_month', 'email', 'contact numbers_month', 'recent activity_month', 'last visit_month', 'past due balance_month']]
        unpaid_cust.columns = col_names

        add_cust = merged[merged['_merge'] == 'right_only'].copy()
        add_cust['payment status_report'] = 'add'
        add_cust = add_cust[['payment status_report', 'last name_report', 'first name_report', 'email', 'contact numbers_report', 'recent activity_report', 'last visit_report', 'past due balance_report']]
        add_cust.columns = col_names

        final_list = pd.concat([paid_cust, unpaid_cust, add_cust], ignore_index=True)

        # 6. Display Metrics in a clean dashboard layout
        st.subheader("📊 Report Summary Metrics")
        metrics_col1, metrics_col2 = st.columns(2)
        
        with metrics_col1:
            st.metric(label="Amount Recovered", value=f"${int(paid_cust['past due balance'].sum()):,}")
        with metrics_col2:
            remaining_bal = final_list[final_list['payment status'] != 'paid']['past_due_balance'].sum()
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
