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
    data = worksheet.get_all_values()[1:]  # Skip row 1
    headers = worksheet.row_values(2)      # Use row 2 as headers

    df = pd.DataFrame(data, columns=headers)
    df.columns = df.columns.str.strip().str.upper()
    return df

# === Load and clean data ===
df = load_data()
df.replace('', pd.NA, inplace=True)
df = df.dropna(how='all')

# === Convert relevant columns to numeric safely ===
if 'TOTAL CONTRACT SUM EDITED' in df.columns:
    df['TOTAL CONTRACT SUM EDITED'] = pd.to_numeric(
        df['TOTAL CONTRACT SUM EDITED'], errors='coerce'
    )

# === Streamlit App ===
st.set_page_config(page_title="Programme Performance Dashboard", layout="wide")
st.title("Programme Performance Dashboard")

# === KPI Card ===
total_contract_sum = df['TOTAL CONTRACT SUM EDITED'].sum() if 'TOTAL CONTRACT SUM EDITED' in df.columns else 0
st.metric("Total Contract Sum", f"₦{total_contract_sum:,.0f}")

# === Filters ===
sector_options = df['SECTOR'].dropna().unique() if 'SECTOR' in df.columns else []
mda_options = df['MDA'].dropna().unique() if 'MDA' in df.columns else []
year_options = df['YEAR'].dropna().unique() if 'YEAR' in df.columns else []

selected_sector = st.multiselect("Filter by Sector", sector_options)
selected_mda = st.multiselect("Filter by MDA", mda_options)
selected_year = st.multiselect("Filter by Year", year_options)

# === Apply filters ===
filtered_df = df.copy()
if selected_sector:
    filtered_df = filtered_df[filtered_df['SECTOR'].isin(selected_sector)]
if selected_mda:
    filtered_df = filtered_df[filtered_df['MDA'].isin(selected_mda)]
if selected_year:
    filtered_df = filtered_df[filtered_df['YEAR'].isin(selected_year)]

# === Charts ===
if not filtered_df.empty:
    bar_chart = px.bar(
        filtered_df['SECTOR'].value_counts().reset_index(),
        x='index',
        y='SECTOR',
        labels={'index': 'Sector', 'SECTOR': 'Project Count'},
        title="Projects by Sector"
    )
    st.plotly_chart(bar_chart, use_container_width=True)

    donut_chart = px.pie(
        filtered_df['MDA'].value_counts().reset_index(),
        names='index',
        values='MDA',
        title="Distribution by MDA",
        hole=0.4
    )
    st.plotly_chart(donut_chart, use_container_width=True)

    # === Table ===
    table_df = filtered_df.groupby(['YEAR', 'MDA']).size().reset_index(name='Project Count')
    st.subheader("Summary Table by MDA and Year")
    st.dataframe(table_df)
else:
    st.info("No data matches the selected filters.")
