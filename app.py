import streamlit as st
import gspread
import pandas as pd
import plotly.express as px
from google.oauth2.service_account import Credentials

# === Load Data from Google Sheets ===
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

    headers = raw[1]  # Use row 2 as headers
    data = raw[2:]    # Start data from row 3

    df = pd.DataFrame(data, columns=headers)
    df.columns = df.columns.str.strip().str.upper()
    return df

# === Load & Clean Data ===
df = load_data()
if df.empty:
    st.stop()

df.replace('', pd.NA, inplace=True)
df = df.dropna(how='all')

# === Convert Numeric Columns ===
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

# === KPI Calculations ===
kpi1 = df['TOTAL CONTRACT SUM EDITED'].sum() if 'TOTAL CONTRACT SUM EDITED' in df else 0
kpi2 = df['ADVANCE PAYMENT'].sum() if 'ADVANCE PAYMENT' in df else 0
kpi3 = df['PREVIOUS PAYMENT'].sum() if 'PREVIOUS PAYMENT' in df else 0
kpi4 = df['AMOUNT NOW DUE'].sum() if 'AMOUNT NOW DUE' in df else 0
kpi5 = df['DATE OF APPROVAL'].notna().sum() if 'DATE OF APPROVAL' in df else 0
kpi6 = df[rating_col].mean() if rating_col in df else 0

# === Streamlit Setup ===
st.set_page_config(page_title="Programme Performance Dashboard", layout="wide")
st.title("Programme Performance Dashboard")

# === KPI Cards ===
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

# === Filter Section ===
cofog_options = df['COFOG'].dropna().unique() if 'COFOG' in df.columns else []
themes_options = df['THEMES PILLAR'].dropna().unique() if 'THEMES PILLAR' in df.columns else []
year_options = df['YEAR'].dropna().unique() if 'YEAR' in df.columns else []

selected_year = st.multiselect("Filter by Year", year_options)
selected_cofog = st.selectbox("Filter by COFOG", cofog_options) if cofog_options.size > 0 else None
selected_theme = st.selectbox("Filter by THEMES PILLAR", themes_options) if themes_options.size > 0 else None

# Narrow MDA list based on COFOG and THEMES PILLAR
filtered_for_mda = df.copy()
if selected_cofog:
    filtered_for_mda = filtered_for_mda[filtered_for_mda['COFOG'] == selected_cofog]
if selected_theme:
    filtered_for_mda = filtered_for_mda[filtered_for_mda['THEMES PILLAR'] == selected_theme]

mda_options = filtered_for_mda['MDA'].dropna().unique() if 'MDA' in filtered_for_mda.columns else []
selected_mda = st.multiselect("Filter by MDA", mda_options)

# Apply filters to data
filtered_df = df.copy()
if selected_cofog:
    filtered_df = filtered_df[filtered_df['COFOG'] == selected_cofog]
if selected_theme:
    filtered_df = filtered_df[filtered_df['THEMES PILLAR'] == selected_theme]
if selected_mda:
    filtered_df = filtered_df[filtered_df['MDA'].isin(selected_mda)]
if selected_year:
    filtered_df = filtered_df[filtered_df['YEAR'].isin(selected_year)]

# === Charts & Summary Table ===
if not filtered_df.empty:
    if 'SECTOR' in filtered_df.columns:
        sector_counts = filtered_df['SECTOR'].value_counts().reset_index()
        sector_counts.columns = ['Sector', 'Count']
        bar_chart = px.bar(sector_counts, x='Sector', y='Count', title="Projects by Sector")
        st.plotly_chart(bar_chart, use_container_width=True)

    if 'MDA' in filtered_df.columns:
        mda_counts = filtered_df['MDA'].value_counts().reset_index()
        mda_counts.columns = ['MDA', 'Count']
        donut_chart = px.pie(mda_counts, names='MDA', values='Count', title="Distribution by MDA", hole=0.4)
        st.plotly_chart(donut_chart, use_container_width=True)

    if 'YEAR' in filtered_df.columns and 'MDA' in filtered_df.columns:
        table_df = filtered_df.groupby(['YEAR', 'MDA']).size().reset_index(name='Project Count')
        st.subheader("Summary Table by MDA and Year")
        st.dataframe(table_df)
else:
    st.info("No data matches the selected filters.")
