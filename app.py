import streamlit as st
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

def load_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    creds_dict = st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    sheet = client.open_by_key("1XDWbJTfucsUvKq8PXVVQ2oap4reTYp10tPHe49Xejmw")
    worksheet = sheet.get_worksheet(0)
    data = worksheet.get_all_values()[1:]
    headers = worksheet.row_values(2)
    df = pd.DataFrame(data, columns=headers)
    return df


    # Drop unwanted columns
    drop_cols = ['N', 'O', 'P', 'R', 'S', 'W', 'AJ'] + \
            [col for col in ['AL', 'AM', 'AN', 'AP', 'AQ', 'AR', 'AS','AT','AU']]
    drop_by_index = [ord(c) - ord('A') for c in drop_cols if c >= 'A' and c <= 'Z']
    df.drop(df.columns[drop_by_index], axis=1, inplace=True, errors='ignore')

    return df

# Load and clean data
df = load_data()
df.replace('', pd.NA, inplace=True)
df = df.dropna(how='all')

# Convert relevant columns to numeric
for col in ['Budget Approved', 'Budget Released', 'Output Performance', 'Programme Count']:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Initialize Dash App
app = dash.Dash(__name__)
app.title = "Programme Performance Dashboard"

# Layout
app.layout = html.Div([
    html.H1("Programme Performance Dashboard"),

    html.Div([
        html.Div([
            html.H4("Total Budget Approved"),
            html.P(id='kpi-budget-approved')
        ], className="kpi-card"),

        html.Div([
            html.H4("Total Budget Released"),
            html.P(id='kpi-budget-released')
        ], className="kpi-card"),

        html.Div([
            html.H4("Avg Output Performance (%)"),
            html.P(id='kpi-output-performance')
        ], className="kpi-card"),

        html.Div([
            html.H4("Total Programmes"),
            html.P(id='kpi-programmes')
        ], className="kpi-card"),
    ], style={'display': 'flex', 'gap': '40px'}),

    html.Br(),

    html.Div([
        html.Label("Sector"),
        dcc.Dropdown(
            options=[{'label': s, 'value': s} for s in df['Sector'].dropna().unique()],
            id='sector-filter', multi=True
        ),

        html.Label("MDA"),
        dcc.Dropdown(
            options=[{'label': m, 'value': m} for m in df['MDA'].dropna().unique()],
            id='mda-filter', multi=True
        ),

        html.Label("Year"),
        dcc.Dropdown(
            options=[{'label': y, 'value': y} for y in df['Year'].dropna().unique()],
            id='year-filter', multi=True
        ),

        html.Label("Output Performance (%) Range"),
        dcc.RangeSlider(id='performance-range', min=0, max=100, step=1, value=[0, 100],
                        marks={0: '0%', 50: '50%', 100: '100%'})
    ], style={'width': '60%', 'margin': 'auto'}),

    html.Br(),

    dcc.Graph(id='bar-chart'),
    dcc.Graph(id='donut-chart'),

    html.H3("Summary Table by MDA and Year"),
    html.Div(id='summary-table')
])

# Callbacks
@app.callback(
    Output('bar-chart', 'figure'),
    Output('donut-chart', 'figure'),
    Output('summary-table', 'children'),
    Output('kpi-budget-approved', 'children'),
    Output('kpi-budget-released', 'children'),
    Output('kpi-output-performance', 'children'),
    Output('kpi-programmes', 'children'),
    Input('sector-filter', 'value'),
    Input('mda-filter', 'value'),
    Input('year-filter', 'value'),
    Input('performance-range', 'value')
)
def update_dashboard(sector, mda, year, perf_range):
    filtered_df = df.copy()

    if sector:
        filtered_df = filtered_df[filtered_df['Sector'].isin(sector)]
    if mda:
        filtered_df = filtered_df[filtered_df['MDA'].isin(mda)]
    if year:
        filtered_df = filtered_df[filtered_df['Year'].astype(str).isin([str(y) for y in year])]

    filtered_df = filtered_df[
        (filtered_df['Output Performance'] >= perf_range[0]) &
        (filtered_df['Output Performance'] <= perf_range[1])
    ]

    bar_fig = px.bar(
        filtered_df.groupby('Sector')['Output Performance'].mean().reset_index(),
        x='Sector', y='Output Performance', title='Avg Output Performance by Sector'
    )

    donut_fig = px.pie(
        filtered_df, names='Sector', values='Budget Released', hole=0.4,
        title='Budget Released by Sector'
    )

    table_df = filtered_df.groupby(['Year', 'MDA']).agg({
        'Budget Approved': 'sum',
        'Budget Released': 'sum',
        'Output Performance': 'mean',
        'Programme Count': 'sum'
    }).reset_index()

    table = html.Table([
        html.Thead(html.Tr([html.Th(col) for col in table_df.columns])),
        html.Tbody([
            html.Tr([html.Td(row[col]) for col in table_df.columns]) for _, row in table_df.iterrows()
        ])
    ])

    total_budget_approved = f"₦{filtered_df['Budget Approved'].sum():,.0f}"
    total_budget_released = f"₦{filtered_df['Budget Released'].sum():,.0f}"
    avg_output_perf = f"{filtered_df['Output Performance'].mean():.1f}%"
    total_programmes = int(filtered_df['Programme Count'].sum())

    return bar_fig, donut_fig, table, total_budget_approved, total_budget_released, avg_output_perf, total_programmes

# Run server
if __name__ == '__main__':
    app.run_server(debug=True)
