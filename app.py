# === IMPORTS ===
import streamlit as st
import gspread
import pandas as pd
import plotly.express as px
from google.oauth2.service_account import Credentials

# === LOAD DATA FROM GOOGLE SHEETS ===
def load_data():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)

    sheet = client.open_by_key("1XDWbJTfucsUvKq8PXVVQ2oap4reTYp10tPHe49Xejmw")
    worksheet = sheet.worksheet("REGISTER")

    raw = worksheet.get_all_values()
    if len(raw) < 3:
        st.error("The REGISTER sheet does not contain enough rows.")
        return pd.DataFrame()

    headers = raw[1]
    data = raw[2:]
    df = pd.DataFrame(data, columns=headers)
    df.columns = df.columns.map(str).str.strip().str.upper()
    return df

# === CLEAN CURRENCY FIELDS ===
def clean_currency(val):
    if isinstance(val, str):
        return val.replace("₦", "").replace(",", "").replace("\xa0", "").strip()
    return val

# === LOAD & CLEAN DATA ===
df = load_data()
if df.empty:
    st.stop()

df.replace('', pd.NA, inplace=True)
df = df.dropna(how='all')

# === DYNAMIC KPI COLUMN MATCHING ===
column_map = {
    "TOTAL CONTRACT SUM EDITED": None,
    "ADVANCE PAYMENT": None,
    "PREVIOUS PAYMENT": None,
    "AMOUNT NOW DUE": None,
    "CONTRACTOR JOB RATING": None,
}
for col in df.columns:
    for key in column_map.keys():
        if key in col:
            column_map[key] = col

# === CLEAN & CONVERT KPI COLUMNS ===
for col in column_map.values():
    if col and col in df.columns:
        df[col] = df[col].apply(clean_currency)
        df[col] = pd.to_numeric(df[col], errors='coerce')

# === PAGE CONFIG ===
st.set_page_config(page_title="Project Performance Dashboard", layout="wide")
st.title("📊🧾 MED Certification Approvals Dashboard")

# === FILTERS ===
def get_unique_with_all(column):
    values = df[column].dropna().astype(str).str.strip().unique().tolist() if column in df.columns else []
    return ['All'] + sorted(values)

year = st.sidebar.multiselect("Filter by Year", get_unique_with_all('YEAR'), default=['All'])

# === COLUMN CLEANUP & RENAMING ===
if 'MONTH' in df.columns:
    df.rename(columns={'MONTH': 'APPROVAL MONTH'}, inplace=True)

# Clean strings safely
for col in ['APPROVAL MONTH', 'MONTH APPLICABLE']:
    if col in df.columns:
        df[col] = df[col].apply(lambda x: str(x).strip() if pd.notna(x) else x)

# === COLUMN CLEANUP & RENAMING ===
if 'MONTH' in df.columns:
    df.rename(columns={'MONTH': 'APPROVAL MONTH'}, inplace=True)

# === Safe string cleaning function ===
def safe_strip(val):
    try:
        return str(val).strip() if pd.notnull(val) else val
    except:
        return val

# === SAFE STRING CLEANING FUNCTION ===
def safe_strip(val):
    try:
        return str(val).strip() if pd.notnull(val) else val
    except:
        return val

# === CLEAN TARGET COLUMNS SAFELY ===
for col in ['APPROVAL MONTH', 'MONTH APPLICABLE']:
    if col in df.columns:
        df[col] = df[col].apply(safe_strip)

# === MONTH FILTER BASED ON YEAR ===
if 'All' in year or not year:
    approval_month_values = df['APPROVAL MONTH'].dropna().unique().tolist()
else:
    approval_month_values = df[df['YEAR'].astype(str).str.strip().isin(year)]['APPROVAL MONTH'].dropna().unique().tolist()

if 'MONTH APPLICABLE' in df.columns:
    if 'All' in year or not year:
        month_values = df['MONTH APPLICABLE'].dropna().unique().tolist()
    else:
        month_values = df[df['YEAR'].astype(str).str.strip().isin(year)]['MONTH APPLICABLE'].dropna().unique().tolist()
else:
    month_values = []

# === SIDEBAR FILTERS ===
month = st.sidebar.multiselect("Filter by MONTH APPLICABLE", ['All'] + sorted(month_values), default=['All'])
approval_month = st.sidebar.multiselect("Filter by APPROVAL MONTH", ['All'] + sorted(approval_month_values), default=['All'])
status = st.sidebar.multiselect("Filter by STATUS", get_unique_with_all('STATUS'), default=['All'])
lga = st.sidebar.multiselect("Filter by LGA", get_unique_with_all('LGA'), default=['All'])
cofog = st.sidebar.multiselect("Filter by COFOG", get_unique_with_all('COFOG'), default=['All'])
theme = st.sidebar.multiselect("Filter by THEMES PILLAR", get_unique_with_all('THEMES PILLAR'), default=['All'])

# === MDA Filter Based on COFOG and THEMES ===
filtered_for_mda = df.copy()
if 'All' not in cofog and cofog:
    filtered_for_mda = filtered_for_mda[filtered_for_mda['COFOG'].astype(str).str.strip().isin(cofog)]
if 'All' not in theme and theme:
    filtered_for_mda = filtered_for_mda[filtered_for_mda['THEMES PILLAR'].astype(str).str.strip().isin(theme)]

mda_options = filtered_for_mda['MDA'].dropna().astype(str).str.strip().unique().tolist()
mda = st.sidebar.multiselect("Filter by MDA", ['All'] + sorted(mda_options), default=['All'])

# === PAYMENT STAGE Filter Based on filters ===
filtered_for_stage = df.copy()
if 'All' not in year and year:
    filtered_for_stage = filtered_for_stage[filtered_for_stage['YEAR'].astype(str).str.strip().isin(year)]
if 'All' not in month and month:
    filtered_for_stage = filtered_for_stage[filtered_for_stage['MONTH APPLICABLE'].astype(str).str.strip().isin(month)]
if 'All' not in approval_month and approval_month:
    filtered_for_stage = filtered_for_stage[filtered_for_stage['APPROVAL MONTH'].astype(str).str.strip().isin(approval_month)]
if 'All' not in lga and lga:
    filtered_for_stage = filtered_for_stage[filtered_for_stage['LGA'].astype(str).str.strip().isin(lga)]
if 'All' not in mda and mda:
    filtered_for_stage = filtered_for_stage[filtered_for_stage['MDA'].astype(str).str.strip().isin(mda)]

payment_options = filtered_for_stage['PAYMENT STAGE'].dropna().astype(str).str.strip().unique().tolist()
payment_stage = st.sidebar.multiselect("Filter by Payment Stage", ['All'] + sorted(payment_options), default=['All'])

# === FINAL FILTERS (filtered_df) ===
filtered_df = df.copy()

if 'All' not in year and year:
    filtered_df = filtered_df[filtered_df['YEAR'].astype(str).str.strip().isin(year)]
if 'All' not in month and month:
    filtered_df = filtered_df[filtered_df['MONTH APPLICABLE'].astype(str).str.strip().isin(month)]
if 'All' not in approval_month and approval_month:
    filtered_df = filtered_df[filtered_df['APPROVAL MONTH'].astype(str).str.strip().isin(approval_month)]
if 'All' not in lga and lga:
    filtered_df = filtered_df[filtered_df['LGA'].astype(str).str.strip().isin(lga)]
if 'All' not in cofog and cofog:
    filtered_df = filtered_df[filtered_df['COFOG'].astype(str).str.strip().isin(cofog)]
if 'All' not in theme and theme:
    filtered_df = filtered_df[filtered_df['THEMES PILLAR'].astype(str).str.strip().isin(theme)]
if 'All' not in mda and mda:
    filtered_df = filtered_df[filtered_df['MDA'].astype(str).str.strip().isin(mda)]
if 'STATUS' in filtered_df.columns and status and 'All' not in status:
    status_clean = [s.strip() for s in status]
    filtered_df = filtered_df[filtered_df['STATUS'].astype(str).str.strip().isin(status_clean)]
if 'All' not in payment_stage and payment_stage:
    filtered_df = filtered_df[filtered_df['PAYMENT STAGE'].astype(str).str.strip().isin(payment_stage)]


    
# === KPI UTILS ===
def safe_sum(df, col_key):
    col = column_map.get(col_key)
    if col and col in df.columns:
        return pd.to_numeric(df[col], errors="coerce").sum()
    return 0

def safe_avg(df, col_key):
    col = column_map.get(col_key)
    if col and col in df.columns:
        return pd.to_numeric(df[col], errors="coerce").mean()
    return 0

# === KPI CALCULATIONS ===
kpi1 = safe_sum(filtered_df, "TOTAL CONTRACT SUM EDITED")
kpi2 = safe_sum(filtered_df, "ADVANCE PAYMENT")
kpi3 = safe_sum(filtered_df, "PREVIOUS PAYMENT")
kpi4 = safe_sum(filtered_df, "AMOUNT NOW DUE")
kpi5 = filtered_df['DATE OF APPROVAL'].notna().sum() if 'DATE OF APPROVAL' in filtered_df else 0
kpi6 = safe_avg(filtered_df, "CONTRACTOR JOB RATING")

# === KPI CARDS ===
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("TOTAL CONTRACT SUM", f"₦{kpi1:,.2f}")
with col2:
    st.metric("TOTAL ADVANCE PAYMENT", f"₦{kpi2:,.2f}")
with col3:
    st.metric("TOTAL PREVIOUS PAYMENT", f"₦{kpi3:,.2f}")

col4, col5, col6 = st.columns(3)
with col4:
    st.metric("TOTAL AMOUNT NOW DUE", f"₦{kpi4:,.2f}")
with col5:
    st.metric("TOTAL APPROVED CERTIFICATES", f"{kpi5:,}")
with col6:
    st.metric("AVG CONTRACTOR JOB RATING", f"{kpi6:.1f} / 5")

# === CHARTS & TABLES ===
if not filtered_df.empty:
    if 'SECTOR' in filtered_df.columns:
        sector_counts = filtered_df['COFOG'].value_counts().reset_index()
        sector_counts.columns = ['COFOG', 'Count']
        st.plotly_chart(px.bar(sector_counts, x='COFOG', y='Count', title="Projects by Sector"), use_container_width=True)

    if 'MDA' in filtered_df.columns:
        mda_counts = filtered_df['MDA'].value_counts().reset_index()
        mda_counts.columns = ['MDA', 'Count']
        st.plotly_chart(px.pie(mda_counts, names='MDA', values='Count', title="Distribution by MDA", hole=0.4), use_container_width=True)

    if 'YEAR' in filtered_df.columns and 'MDA' in filtered_df.columns:
        summary_table = filtered_df.groupby(['YEAR', 'MDA']).size().reset_index(name='Project Count')
        st.subheader("Summary Table by MDA and Year")
        st.dataframe(summary_table)

    st.subheader("Table: Sector Head, MDA, Project Title, Contractor, Amount Now Due")
    cols1 = ['SECTOR HEAD', 'MDA', 'PROJECT TITLE', 'CONTRACTOR', column_map["AMOUNT NOW DUE"]]
    if all(c in filtered_df.columns for c in cols1):
        display_df = filtered_df[cols1].copy()
        display_df[column_map["AMOUNT NOW DUE"]] = display_df[column_map["AMOUNT NOW DUE"]].apply(lambda x: f"₦{x:,.2f}")
        st.dataframe(display_df)

    st.subheader("Table: COFOG – No. of Projects and Amount Now Due")
    if 'COFOG' in filtered_df.columns and 'PROJECT TITLE' in filtered_df.columns:
        cofog_table = filtered_df.groupby(filtered_df['COFOG'].astype(str).str.strip()).agg({
            'PROJECT TITLE': 'count',
            column_map["AMOUNT NOW DUE"]: 'sum'
        }).reset_index().rename(columns={'PROJECT TITLE': 'NO. OF PROJECTS'})

        cofog_table['₦ AMOUNT NOW DUE'] = cofog_table[column_map["AMOUNT NOW DUE"]].apply(lambda x: f"₦{x:,.2f}")
        cofog_table = cofog_table[['COFOG', 'NO. OF PROJECTS', '₦ AMOUNT NOW DUE']]

        total_row = pd.DataFrame({
            'COFOG': ['Total'],
            'NO. OF PROJECTS': [cofog_table['NO. OF PROJECTS'].sum()],
            '₦ AMOUNT NOW DUE': [f"₦{safe_sum(filtered_df, 'AMOUNT NOW DUE'):,.2f}"]
        })
        cofog_table = pd.concat([cofog_table, total_row], ignore_index=True)

        st.dataframe(cofog_table)

    st.subheader("Table: THEMES PILLAR – No. of Projects and Amount Now Due")
    if 'THEMES PILLAR' in filtered_df.columns and 'PROJECT TITLE' in filtered_df.columns:
        theme_table = filtered_df.groupby(filtered_df['THEMES PILLAR'].astype(str).str.strip()).agg({
            'PROJECT TITLE': 'count',
            column_map["AMOUNT NOW DUE"]: 'sum'
        }).reset_index().rename(columns={'PROJECT TITLE': 'NO. OF PROJECTS'})

        theme_table['₦ AMOUNT NOW DUE'] = theme_table[column_map["AMOUNT NOW DUE"]].apply(lambda x: f"₦{x:,.2f}")
        theme_table = theme_table[['THEMES PILLAR', 'NO. OF PROJECTS', '₦ AMOUNT NOW DUE']]

        total_row = pd.DataFrame({
            'THEMES PILLAR': ['Total'],
            'NO. OF PROJECTS': [theme_table['NO. OF PROJECTS'].sum()],
            '₦ AMOUNT NOW DUE': [f"₦{safe_sum(filtered_df, 'AMOUNT NOW DUE'):,.2f}"]
        })
        theme_table = pd.concat([theme_table, total_row], ignore_index=True)

        st.dataframe(theme_table)
else:
    st.info("No data matches the selected filters.")
