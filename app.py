import dash
from dash import dcc, html, Input, Output
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import streamlit as st

=== Load Data from Google Sheets ===

def load_data(): scope = [ "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive" ] creds_dict = st.secrets["gcp_service_account"] creds = Credentials.from_service_account_info(creds_dict, scopes=scope) client = gspread.authorize(creds)

sheet = client.open_by_key("1XDWbJTfucsUvKq8PXVVQ2oap4reTYp10tPHe49Xejmw")
worksheet = sheet.get_worksheet(0)
data = worksheet.get_all_values()[1:]  # Skip row 1 (first header row)
headers = worksheet.row_values(2)      # Use row 2 as headers

df = pd.DataFrame(data, columns=headers)
df.columns = df.columns.str.strip().str.upper()
return df

Load and clean data

df = load_data() df.replace('', pd.NA, inplace=True) df = df.dropna(how='all')

Convert relevant columns to numeric safely

if 'TOTAL CONTRACT SUM EDITED' in df.columns: df['TOTAL CONTRACT SUM EDITED'] = pd.to_numeric(df['TOTAL CONTRACT SUM EDITED'], errors='coerce')

Initialize Dash App

app = dash.Dash(name) app.title = "Programme Performance Dashboard"

Layout

app.layout = html.Div([ html.H1("Programme Performance Dashboard"),

html.Div([
    html.Div([
        html.H4("Total Contract Sum"),
        html.P(id='kpi-total-contract-sum')
    ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'}),
], style={'display': 'flex'}),

html.Label("Filter by Sector"),
dcc.Dropdown(
    options=[{'label': s, 'value': s} for s in df['SECTOR'].dropna().unique()],
    id='sector-filter', multi=True
),

html.Label("Filter by MDA"),
dcc.Dropdown(
    options=[{'label': m, 'value': m} for m in df['MDA'].dropna().unique()],
    id='mda-filter', multi=True
),

html.Label("Filter by Year"),
dcc.Dropdown(
    options=[{'label': y, 'value': y} for y in df['YEAR'].dropna().unique()],
    id='year-filter', multi=True
),

dcc.Graph(id='bar-chart'),
dcc.Graph(id='donut-chart'),

html.H3("Summary Table by MDA and Year"),
html.Div(id='summary-table')

])

Callback

@app.callback( Output('bar-chart', 'figure'), Output('donut-chart', 'figure'), Output('summary-table', 'children'), Output('kpi-total-contract-sum', 'children'), Input('sector-filter', 'value'), Input('mda-filter', 'value'), Input('year-filter', 'value') ) def update_dashboard(sector, mda, year): filtered_df = df.copy()

if sector:
    filtered_df = filtered_df[filtered_df['SECTOR'].isin(sector)]
if mda:
    filtered_df = filtered_df[filtered_df['MDA'].isin(mda)]
if year:
    filtered_df = filtered_df[filtered_df['YEAR'].isin(year)]

bar_fig = {
    'data': [{
        'x': filtered_df['SECTOR'].value_counts().index,
        'y': filtered_df['SECTOR'].value_counts().values,
        'type': 'bar'
    }],
    'layout': {'title': 'Projects by Sector'}
}

donut_fig = {
    'data': [{
        'labels': filtered_df['MDA'].value_counts().index,
        'values': filtered_df['MDA'].value_counts().values,
        'type': 'pie',
        'hole': .4
    }],
    'layout': {'title': 'Distribution by MDA'}
}

table_df = filtered_df.groupby(['YEAR', 'MDA']).size().reset_index(name='Project Count')
table = html.Table([
    html.Thead(html.Tr([html.Th(col) for col in table_df.columns])),
    html.Tbody([
        html.Tr([html.Td(row[col]) for col in table_df.columns]) for _, row in table_df.iterrows()
    ])
])

total_contract_sum = f"₦{filtered_df['TOTAL CONTRACT SUM EDITED'].sum():,.0f}" if 'TOTAL CONTRACT SUM EDITED' in filtered_df.columns else "₦0"

return bar_fig, donut_fig, table, total_contract_sum

Run server

if name == 'main': app.run_server(debug=True)

