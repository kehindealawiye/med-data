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
st.set_page_config(page_title="Programme Performance Dashboard", layout="wide")
st.title("Programme Performance Dashboard")

# === FILTERS ===
def get_unique_with_all(column):
    values = df[column].dropna().astype(str).str.strip().unique().tolist() if column in df.columns else []
    return ['All'] + sorted(values)

year = st.selectbox("Filter by Year", get_unique_with_all('YEAR'))

# === MONTH FILTER BASED ON YEAR ===
month_col = 'MONTH'
if month_col in df.columns:
    df[month_col] = df[month_col].astype(str).str.strip()

month_values = df[month_col].dropna().unique().tolist() if year == 'All' else df[df['YEAR'].astype(str).str.strip() == year][month_col].dropna().unique().tolist()
month = st.selectbox("Filter by Month", ['All'] + sorted(month_values))

lga = st.selectbox("Filter by LGA", get_unique_with_all('LGA'))
cofog = st.selectbox("Filter by COFOG", get_unique_with_all('COFOG'))
theme = st.selectbox("Filter by THEMES PILLAR", get_unique_with_all('THEMES PILLAR'))

# === MDA Filter Based on COFOG and THEMES ===
filtered_for_mda = df.copy()
if cofog != 'All':
    filtered_for_mda = filtered_for_mda[filtered_for_mda['COFOG'].astype(str).str.strip() == cofog]
if theme != 'All':
    filtered_for_mda = filtered_for_mda[filtered_for_mda['THEMES PILLAR'].astype(str).str.strip() == theme]

mda_options = filtered_for_mda['MDA'].dropna().astype(str).str.strip().unique().tolist()
mda = st.selectbox("Filter by MDA", ['All'] + sorted(mda_options))

# === PAYMENT STAGE Filter Based on Year, Month, MDA, LGA ===
filtered_for_stage = df.copy()
if year != 'All':
    filtered_for_stage = filtered_for_stage[filtered_for_stage['YEAR'].astype(str).str.strip() == year]
if month != 'All':
    filtered_for_stage = filtered_for_stage[filtered_for_stage['MONTH'].astype(str).str.strip() == month]
if lga != 'All':
    filtered_for_stage = filtered_for_stage[filtered_for_stage['LGA'].astype(str).str.strip() == lga]
if mda != 'All':
    filtered_for_stage = filtered_for_stage[filtered_for_stage['MDA'].astype(str).str.strip() == mda]

payment_options = filtered_for_stage['PAYMENT STAGE'].dropna().astype(str).str.strip().unique().tolist()
payment_stage = st.selectbox("Filter by Payment Stage", ['All'] + sorted(payment_options))

# === APPLY FILTERS ===
filtered_df = df.copy()
if year != 'All':
    filtered_df = filtered_df[filtered_df['YEAR'].astype(str).str.strip() == year]
if month != 'All':
    filtered_df = filtered_df[filtered_df['MONTH'].astype(str).str.strip() == month]
if lga != 'All':
    filtered_df = filtered_df[filtered_df['LGA'].astype(str).str.strip() == lga]
if cofog != 'All':
    filtered_df = filtered_df[filtered_df['COFOG'].astype(str).str.strip() == cofog]
if theme != 'All':
    filtered_df = filtered_df[filtered_df['THEMES PILLAR'].astype(str).str.strip() == theme]
if mda != 'All':
    filtered_df = filtered_df[filtered_df['MDA'].astype(str).str.strip() == mda]
if payment_stage != 'All':
    filtered_df = filtered_df[filtered_df['PAYMENT STAGE'].astype(str).str.strip() == payment_stage]

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
        sector_counts = filtered_df['SECTOR'].value_counts().reset_index()
        sector_counts.columns = ['Sector', 'Count']
        st.plotly_chart(px.bar(sector_counts, x='Sector', y='Count', title="Projects by Sector"), use_container_width=True)

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
