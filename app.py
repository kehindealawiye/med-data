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
    headers = worksheet.row_values(1)         # Use row 1 as headers
    data = worksheet.get_all_values()[1:]     # Skip row 1 (header row)

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
    # Bar Chart
    sector_counts = filtered_df['SECTOR'].value_counts().reset_index()
    sector_counts.columns = ['Sector', 'Count']

    bar_chart = px.bar(
        sector_counts,
        x='Sector',
        y='Count',
        labels={'Sector': 'Sector', 'Count': 'Project Count'},
        title="Projects by Sector"
    )
    st.plotly_chart(bar_chart, use_container_width=True)

    # Donut Chart
    mda_counts = filtered_df['MDA'].value_counts().reset_index()
    mda_counts.columns = ['MDA', 'Count']

    donut_chart = px.pie(
        mda_counts,
        names='MDA',
        values='Count',
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
