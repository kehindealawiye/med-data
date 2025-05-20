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
    worksheet = sheet.get_worksheet(0)

    raw = worksheet.get_all_values()
    if len(raw) < 2:
        st.error("The Google Sheet doesn't contain enough rows.")
        return pd.DataFrame()

    headers = raw[1]
    data = raw[2:]
    df = pd.DataFrame(data, columns=headers)
    df.columns = df.columns.str.strip().str.upper()
    return df

# === LOAD & CLEAN DATA ===
df = load_data()
if df.empty:
    st.stop()

df.replace('', pd.NA, inplace=True)
df = df.dropna(how='all')

# === CONVERT NUMERIC COLUMNS ===
rating_col = 'CONTRACTOR JOB RATING \n(VERY GOOD (5), GOOD (4), AVERAGE (3), POOR (2), VERY POOR (1)'
numeric_columns = [
    'TOTAL CONTRACT SUM EDITED',
    'ADVANCE PAYMENT',
    'PREVIOUS PAYMENT',
    'AMOUNT NOW DUE',
    rating_col
]
for col in numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# === PAGE CONFIG ===
st.set_page_config(page_title="Programme Performance Dashboard", layout="wide")
st.title("Programme Performance Dashboard")

# === FILTERS ===
def get_unique_with_all(column):
    values = df[column].dropna().str.strip().unique().tolist() if column in df.columns else []
    return ['All'] + sorted(values)

year = st.selectbox("Filter by Year", get_unique_with_all('YEAR'))
lga = st.selectbox("Filter by LGA", get_unique_with_all('LGA'))
cofog = st.selectbox("Filter by COFOG", get_unique_with_all('COFOG'))
theme = st.selectbox("Filter by THEMES PILLAR", get_unique_with_all('THEMES PILLAR'))
payment_stage = st.selectbox("Filter by Payment Stage", get_unique_with_all('PAYMENT STAGE'))

# Filter MDA options based on COFOG + Theme
filtered_for_mda = df.copy()
if cofog != 'All':
    filtered_for_mda = filtered_for_mda[filtered_for_mda['COFOG'].str.strip() == cofog]
if theme != 'All':
    filtered_for_mda = filtered_for_mda[filtered_for_mda['THEMES PILLAR'].str.strip() == theme]

mda_options = get_unique_with_all('MDA')
mda = st.multiselect("Filter by MDA", mda_options, default=['All'])

# === APPLY FILTERS ===
filtered_df = df.copy()
if year != 'All':
    filtered_df = filtered_df[filtered_df['YEAR'].str.strip() == year]
if lga != 'All':
    filtered_df = filtered_df[filtered_df['LGA'].str.strip() == lga]
if cofog != 'All':
    filtered_df = filtered_df[filtered_df['COFOG'].str.strip() == cofog]
if theme != 'All':
    filtered_df = filtered_df[filtered_df['THEMES PILLAR'].str.strip() == theme]
if payment_stage != 'All':
    filtered_df = filtered_df[filtered_df['PAYMENT STAGE'].str.strip() == payment_stage]
if 'All' not in mda and mda:
    filtered_df = filtered_df[filtered_df['MDA'].isin(mda)]

# === KPI CALCULATIONS ===
kpi1 = filtered_df['TOTAL CONTRACT SUM EDITED'].sum() if 'TOTAL CONTRACT SUM EDITED' in filtered_df else 0
kpi2 = filtered_df['ADVANCE PAYMENT'].sum() if 'ADVANCE PAYMENT' in filtered_df else 0
kpi3 = filtered_df['PREVIOUS PAYMENT'].sum() if 'PREVIOUS PAYMENT' in filtered_df else 0
kpi4 = filtered_df['AMOUNT NOW DUE'].sum() if 'AMOUNT NOW DUE' in filtered_df else 0
kpi5 = filtered_df['DATE OF APPROVAL'].notna().sum() if 'DATE OF APPROVAL' in filtered_df else 0
kpi6 = filtered_df[rating_col].mean() if rating_col in filtered_df else 0

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

# === CHART VISUALIZATIONS ===
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

    # === SUMMARY TABLES ===
    st.subheader("Table: Sector Head, MDA, Project Title, Contractor, Amount Now Due")
    cols1 = ['SECTOR HEAD', 'MDA', 'PROJECT TITLE', 'CONTRACTOR', 'AMOUNT NOW DUE']
    if all(c in filtered_df.columns for c in cols1):
        st.dataframe(filtered_df[cols1])

    st.subheader("Table: COFOG – No. of Projects and Amount Now Due")
    if 'COFOG' in filtered_df.columns and 'PROJECT TITLE' in filtered_df.columns:
        cofog_table = filtered_df.groupby(filtered_df['COFOG'].str.strip()).agg({
            'PROJECT TITLE': 'count',
            'AMOUNT NOW DUE': 'sum'
        }).reset_index().rename(columns={'PROJECT TITLE': 'NO. OF PROJECTS'})
        st.dataframe(cofog_table)

    st.subheader("Table: THEMES PILLAR – No. of Projects and Amount Now Due")
    if 'THEMES PILLAR' in filtered_df.columns and 'PROJECT TITLE' in filtered_df.columns:
        theme_table = filtered_df.groupby(filtered_df['THEMES PILLAR'].str.strip()).agg({
            'PROJECT TITLE': 'count',
            'AMOUNT NOW DUE': 'sum'
        }).reset_index().rename(columns={'PROJECT TITLE': 'NO. OF PROJECTS'})
        st.dataframe(theme_table)
else:
    st.info("No data matches the selected filters.")
