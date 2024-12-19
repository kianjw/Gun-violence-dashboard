import sqlite3
import pandas as pd
import dash
from dash import dcc, html, Input, Output
import dash_leaflet as dl
import plotly.express as px
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from datetime import datetime

########################################
# DATABASE CONNECTION AND QUERIES
########################################

db_path = "FinalProject.db"
conn = sqlite3.connect(db_path)

query_totals = """
SELECT 
    COUNT(*) AS TotalIncidents, 
    SUM(VictimKilled) AS TotalVictimsKilled, 
    SUM(VictimInjured) AS TotalVictimsInjured
FROM Victims;
"""
totals = conn.execute(query_totals).fetchone()
totals_dict = {
    "Total Incidents": totals[0],
    "Total Victims Killed": totals[1],
    "Total Victims Injured": totals[2]
}

query_death_ratio = """
SELECT 
    Locations.StateName AS Location,
    Victims.VictimKilled AS Victims_Killed,
    Victims.VictimInjured AS Victims_Injured,
    Incidents.IncidentDate
FROM 
    Incidents
NATURAL JOIN 
    Locations
NATURAL JOIN 
    Victims;
"""
victim_data = pd.read_sql_query(query_death_ratio, conn)

query_incident_count = """
SELECT 
    Locations.StateName AS State,
    Incidents.IncidentDate,
    COUNT(Incidents.IncidentID) AS IncidentCount
FROM 
    Incidents
JOIN 
    Locations
ON 
    Incidents.LocationID = Locations.LocationID
GROUP BY 
    Locations.StateName, Incidents.IncidentDate
"""
incident_data = pd.read_sql_query(query_incident_count, conn)

query_gun_violence = """
SELECT 
    Locations.StateName AS Location,
    Victims.VictimKilled AS Victims_Killed,
    Victims.VictimInjured AS Victims_Injured
FROM Incidents 
NATURAL JOIN Locations 
NATURAL JOIN Victims;
"""
gun_violence_data = pd.read_sql_query(query_gun_violence, conn)
conn.close()

########################################
# DATA PROCESSING (First Snippet)
########################################

victim_data['IncidentDate'] = pd.to_datetime(victim_data['IncidentDate'])
victim_data['IncidentMonth'] = victim_data['IncidentDate'].dt.strftime('%m')
victim_data['Total_Victims'] = victim_data['Victims_Killed'] + victim_data['Victims_Injured']

grouped_victim = victim_data.groupby(['Location', 'IncidentMonth']).agg({
    'Total_Victims': 'sum',
    'Victims_Killed': 'sum'
}).reset_index()

grouped_victim['Death_Ratio'] = grouped_victim.apply(
    lambda row: round((row['Victims_Killed'] / row['Total_Victims']) * 100, 2) if row['Total_Victims'] > 0 else 0,
    axis=1
)

all_months_victim = grouped_victim.groupby('Location').agg({
    'Total_Victims': 'sum',
    'Victims_Killed': 'sum'
}).reset_index()
all_months_victim['Death_Ratio'] = all_months_victim.apply(
    lambda row: round((row['Victims_Killed'] / row['Total_Victims']) * 100, 2) if row['Total_Victims'] > 0 else 0,
    axis=1
)
all_months_victim['IncidentMonth'] = 'All'

complete_victim_data = pd.concat([grouped_victim, all_months_victim], ignore_index=True)

incident_data['IncidentDate'] = pd.to_datetime(incident_data['IncidentDate'])
incident_data['IncidentMonth'] = incident_data['IncidentDate'].dt.strftime('%m')
incident_grouped = incident_data.groupby(['State', 'IncidentMonth'], as_index=False)['IncidentCount'].sum()

all_months_incident = incident_data.groupby('State', as_index=False)['IncidentCount'].sum()
all_months_incident['IncidentMonth'] = 'All'
complete_incident_data = pd.concat([incident_grouped, all_months_incident], ignore_index=True)

state_full_name_map = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
    'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
    'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID',
    'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS',
    'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN',
    'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE',
    'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
    'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC',
    'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR',
    'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
    'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT',
    'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA',
    'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'
}

complete_victim_data['Abbreviation'] = complete_victim_data['Location'].map(state_full_name_map)
complete_incident_data['Abbreviation'] = complete_incident_data['State'].map(state_full_name_map)

merged_data = pd.merge(
    complete_victim_data[['Abbreviation', 'IncidentMonth', 'Death_Ratio']],
    complete_incident_data[['Abbreviation', 'IncidentMonth', 'IncidentCount']],
    on=['Abbreviation', 'IncidentMonth'],
    how='outer'
)

merged_data = merged_data.dropna(subset=['IncidentCount', 'Death_Ratio'], how='all')
state_names = pd.DataFrame(list(state_full_name_map.items()), columns=['FullName', 'Abbreviation'])
combined_data = pd.merge(merged_data, state_names, on='Abbreviation', how='left')

gun_violence_data['Incident_Count'] = 1
gun_violence_data['Total_Victims'] = gun_violence_data['Victims_Killed'] + gun_violence_data['Victims_Injured']
location_data = gun_violence_data.groupby('Location').agg({
    'Incident_Count': 'sum',
    'Total_Victims': 'sum',
    'Victims_Killed': 'sum',
    'Victims_Injured': 'sum'
}).reset_index()

location_data['Death_Ratio'] = location_data.apply(
    lambda row: round(row['Victims_Killed'] / row['Total_Victims'], 2) 
    if row['Total_Victims'] > 0 else 0,
    axis=1
)

########################################
# SECOND CODE SNIPPET DATA FETCH & PROCESSING
########################################

conn2 = sqlite3.connect('FinalProject.db')
query_map = """
SELECT 
    Locations.StateName AS StateName_2,
    Locations.City_CountyName AS City_CountyName_2,
    Locations.Latitude AS Latitude_2,
    Locations.Longitude AS Longitude_2,
    GROUP_CONCAT(DISTINCT Incidents.IncidentID) AS IncidentIDs_2,
    COUNT(Incidents.IncidentID) AS TotalIncidents_2,
    SUM(Victims.VictimKilled) AS TotalKilled_2,
    SUM(Victims.VictimInjured) AS TotalInjured_2,
    Incidents.IncidentDate AS IncidentDate_2
FROM 
    Incidents
JOIN 
    Locations
ON 
    Incidents.LocationID = Locations.LocationID
JOIN 
    Victims
ON 
    Incidents.VictimID = Victims.VictimID
GROUP BY 
    Locations.Latitude, Locations.Longitude, Locations.StateName, Locations.City_CountyName, Incidents.IncidentDate
"""
incidents_data_2 = pd.read_sql_query(query_map, conn2)

query2_2 = """
SELECT 
    IncidentDate AS Date_2,
    VictimKilled AS Victims_Killed_2,
    VictimInjured AS Victims_Injured_2
FROM Incidents NATURAL JOIN Victims;
"""
data_2 = pd.read_sql_query(query2_2, conn2)

incidents_query_2 = "SELECT IncidentDate AS IncidentDate_3 FROM incidents"
df_incidents_2 = pd.read_sql_query(incidents_query_2, conn2)

death_ratio_query_2 = """
SELECT 
    Victims.VictimKilled AS Victims_Killed_3,
    Victims.VictimInjured AS Victims_Injured_3,
    Incidents.IncidentDate AS IncidentDate_4
FROM 
    Incidents
NATURAL JOIN 
    Victims
"""
df_victims_2 = pd.read_sql_query(death_ratio_query_2, conn2)
conn2.close()

incidents_data_2['TotalVictims_2'] = incidents_data_2['TotalKilled_2'] + incidents_data_2['TotalInjured_2']
incidents_data_2['IncidentDate_2'] = pd.to_datetime(incidents_data_2['IncidentDate_2'])
min_date_2 = incidents_data_2['IncidentDate_2'].min()
max_date_2 = incidents_data_2['IncidentDate_2'].max()

data_2['Date_2'] = pd.to_datetime(data_2['Date_2'], format='%B %d, %Y', errors='coerce')
data_2 = data_2.dropna(subset=['Date_2'])
data_2['Incident_Count_2'] = 1
data_2['Month_2'] = data_2['Date_2'].dt.month

monthly_data_2 = data_2.groupby('Month_2').agg({
    'Incident_Count_2': 'sum',
    'Victims_Killed_2': 'sum',
    'Victims_Injured_2': 'sum'
}).reset_index()

monthly_data_2['Victim_Killed_Ratio_2'] = monthly_data_2.apply(
    lambda row: round((row['Victims_Killed_2'] / (row['Victims_Killed_2'] + row['Victims_Injured_2'])) * 100, 2) 
    if (row['Victims_Killed_2'] + row['Victims_Injured_2']) > 0 else 0,
    axis=1
)

df_incidents_2['IncidentDate_3'] = pd.to_datetime(df_incidents_2['IncidentDate_3'])
df_victims_2['IncidentDate_4'] = pd.to_datetime(df_victims_2['IncidentDate_4'])

daily_incident_data_2 = df_incidents_2.groupby(df_incidents_2['IncidentDate_3'].dt.day_name()).size().reset_index()
daily_incident_data_2.columns = ['day_2', 'incidents_2']

day_order_2 = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
daily_incident_data_2['day_2'] = pd.Categorical(daily_incident_data_2['day_2'], categories=day_order_2, ordered=True)
daily_incident_data_2 = daily_incident_data_2.sort_values('day_2')

df_victims_2['Total_Victims_3'] = df_victims_2['Victims_Killed_3'] + df_victims_2['Victims_Injured_3']
df_victims_2['day_2'] = df_victims_2['IncidentDate_4'].dt.day_name()
daily_victim_data_2 = df_victims_2.groupby('day_2').agg({'Victims_Killed_3': 'sum', 'Total_Victims_3': 'sum'}).reset_index()
daily_victim_data_2['Death_Ratio_2'] = daily_victim_data_2.apply(
    lambda row: round((row['Victims_Killed_3'] / row['Total_Victims_3']) * 100, 2) 
    if row['Total_Victims_3'] > 0 else 0,
    axis=1
)
daily_victim_data_2['day_2'] = pd.Categorical(daily_victim_data_2['day_2'], categories=day_order_2, ordered=True)
daily_victim_data_2 = daily_victim_data_2.sort_values('day_2')

combined_daily_data_2 = pd.merge(daily_incident_data_2, daily_victim_data_2, on='day_2', how='outer')

########################################
# DASH APP SETUP
########################################

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server

########################################
# APP LAYOUT
########################################

navbar = dbc.Navbar(
    dbc.Container([
        dbc.NavbarBrand(
            "U.S. Gun Violence 2024 Dashboard",
            className="mx-auto",  
            style={"fontWeight": "bold", "fontSize": "24px", "color": "#FFFFFF", "textAlign": "center"}
        ),
    ]),
    color="black",  
    dark=True,
    sticky="top"
)

footer = html.Div(
    "Provided by U.S National Public Safety Institute (NPSI)",
    style={
        "bottom": "10px",
        "right": "10px",
        "fontSize": "14px",
        "color": "#7F8C8D",
        "textAlign": "right",
        "zIndex": "1000"
    }
)

top_metrics_row = dbc.Row(
    [
        dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H4("Total Incidents", className="card-title text-center", style={"color": "#2C3E50"}),
                        html.H5(
                            f"{totals_dict['Total Incidents']:,}",
                            className="card-text text-center",
                            style={"fontSize": "30px", "color": "#E74C3C"}
                        ),
                        html.Div(html.I(className="bi bi-exclamation-octagon-fill", style={"fontSize": "40px", "color": "#E74C3C"}), className="text-center")
                    ]
                ),
                style={"box-shadow": "0 2px 8px rgba(0,0,0,0.1)", "text-align": "center", "border": "none"}
            ),
            width=4
        ),
        dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H4("Victims Killed", className="card-title text-center", style={"color": "#2C3E50"}),
                        html.H5(
                            f"{totals_dict['Total Victims Killed']:,}",
                            className="card-text text-center",
                            style={"fontSize": "30px", "color": "#E74C3C"}
                        ),
                        html.Div(html.I(className="bi bi-person-x-fill", style={"fontSize": "40px", "color": "#C0392B"}), className="text-center")
                    ]
                ),
                style={"box-shadow": "0 2px 8px rgba(0,0,0,0.1)", "text-align": "center", "border": "none"}
            ),
            width=4
        ),
        dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H4("Victims Injured", className="card-title text-center", style={"color": "#2C3E50"}),
                        html.H5(
                            f"{totals_dict['Total Victims Injured']:,}",
                            className="card-text text-center",
                            style={"fontSize": "30px", "color": "#E74C3C"}
                        ),
                        html.Div(html.I(className="bi bi-activity", style={"fontSize": "40px", "color": "#E67E22"}), className="text-center")
                    ]
                ),
                style={"box-shadow": "0 2px 8px rgba(0,0,0,0.1)", "text-align": "center", "border": "none"}
            ),
            width=4
        ),
    ],
    className="g-4 mt-4"
)

app.layout = dbc.Container([
    navbar,
    top_metrics_row,  
    # Row 1: First snippet visualization
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Geographical Distribution of Gun Violence", className="text-center mb-0", style={"color":"white"}), style={"backgroundColor": "#000000"}), 
                dbc.CardBody([
                    html.Label("Select Metric:", style={'font-weight': 'bold'}),
                    dcc.Dropdown(
                        id='metric-filter',
                        options=[
                            {'label': 'Incident Counts', 'value': 'IncidentCount'},
                            {'label': 'Death Ratio (%)', 'value': 'Death_Ratio'}
                        ],
                        value='IncidentCount',
                        className="mb-3"
                    ),
                    html.Label("Filter by Month:", style={'font-weight': 'bold'}),
                    dcc.Dropdown(
                        id='month-filter',
                        options=[
                            {'label': 'All Months', 'value': 'All'},
                            {'label': 'January', 'value': '01'},
                            {'label': 'February', 'value': '02'},
                            {'label': 'March', 'value': '03'},
                            {'label': 'April', 'value': '04'},
                            {'label': 'May', 'value': '05'},
                            {'label': 'June', 'value': '06'},
                            {'label': 'July', 'value': '07'},
                            {'label': 'August', 'value': '08'},
                            {'label': 'September', 'value': '09'},
                            {'label': 'October', 'value': '10'},
                            {'label': 'November', 'value': '11'},
                            {'label': 'December', 'value': '12'}
                        ],
                        value='All',
                        className="mb-3"
                    ),
                    dcc.Graph(id='choropleth-map', style={'height': '550px'})
                ])
            ], style={'box-shadow': '0 2px 8px rgba(0,0,0,0.1)', 'border': 'none'})
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Top 10 States Impacted by Gun Violence", className="text-center mb-0", style={"color":"white"}), style={"backgroundColor": "#000000"}), 
dbc.CardBody([
    html.Label("Select a Metric:", style={'font-weight': 'bold'}),
    dcc.Dropdown(
        id='metric-picker',
        options=[
            {'label': 'Incident Counts', 'value': 'Incident_Count'},
            {'label': 'Death Ratio (%)', 'value': 'Death_Ratio'}
        ],
        value='Incident_Count',
        className="mb-3"
    ),
    html.Label("Filter by Month:", style={'font-weight': 'bold'}),
    dcc.Dropdown(
        id='month-filter-bar-chart',
        options=[
            {'label': 'All Months', 'value': 'All'},
            {'label': 'January', 'value': '01'},
            {'label': 'February', 'value': '02'},
            {'label': 'March', 'value': '03'},
            {'label': 'April', 'value': '04'},
            {'label': 'May', 'value': '05'},
            {'label': 'June', 'value': '06'},
            {'label': 'July', 'value': '07'},
            {'label': 'August', 'value': '08'},
            {'label': 'September', 'value': '09'},
            {'label': 'October', 'value': '10'},
            {'label': 'November', 'value': '11'},
            {'label': 'December', 'value': '12'}
        ],
        value='All',
        className="mb-3"
    ),
    dcc.Graph(id='top-locations-bar-chart', style={'height': '550px'})
])
            ], style={'box-shadow': '0 2px 8px rgba(0,0,0,0.1)', 'border': 'none'})
        ], width=6)
    ], className="g-4 mt-4"),

    # Row 2: Second snippet visualization
    dbc.Row([
        dbc.Col([
dbc.Card([
    dbc.CardHeader(html.H5("Clusters of Gun Violence Incidents", className="text-center mb-0", style={"color":"white"}), style={"backgroundColor": "#000000"}), 
        dbc.CardBody([
            html.Label("Filter by Date Range:", style={'font-weight': 'bold'}),
            dcc.DatePickerRange(
                id='date-picker-range_2',
                start_date=min_date_2,
                end_date=max_date_2,
                min_date_allowed=min_date_2,
                max_date_allowed=max_date_2,
            ),
            html.Br(),
            dl.Map(
                id='incident-map_2',
                children=[
                    dl.TileLayer(),
                    dl.LayerGroup(id="marker-layer_2")
                ],
                style={'width': '100%', 'height': '350px', 'margin-top': '10px', 'border-radius': '5px'},
                center=[39.8283, -98.5795],
                zoom=5
            ),
            html.Div(
                "Note: The intensity of marker color reflects the death ratio in the incidents.",
                style={'font-size': '12px', 'margin-top': '10px', 'color': '#7F8C8D'}
            )
        ])
    ], style={'box-shadow': '0 2px 8px rgba(0,0,0,0.1)', 'border': 'none'})
        ], width=4),
        
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Gun Violence Trends Over Months", className="text-center mb-0", style={"color":"white"}), style={"backgroundColor": "#000000"}), 
                dbc.CardBody([
                    html.Label("Select a Metric:", style={'font-weight': 'bold'}),
                    dcc.Dropdown(
                        id='metric-picker_2',
                        options=[
                            {'label': 'Incidents Counts', 'value': 'Incident_Count_2'},
                            {'label': 'Total Victims', 'value': 'Victims_Over_Months_2'},
                            {'label': 'Death Ratio (%)', 'value': 'Victim_Killed_Ratio_Over_Months_2'}
                        ],
                        value='Incident_Count_2',
                        clearable=False,
                        style={'width': '90%', 'margin-top': '10px'}
                    ),
                    dcc.Graph(id='monthly-trends-line-chart_2', style={'height': '355px', 'margin-top': '10px'})
                ])
            ], style={'box-shadow': '0 2px 8px rgba(0,0,0,0.1)', 'border': 'none'})
        ], width=4),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Gun Violence Trends by Day of the Week", className="text-center mb-0", style={"color":"white"}), style={"backgroundColor": "#000000"}), 
                dbc.CardBody([
                    html.Label("Select Metric:", style={'font-weight': 'bold'}),
                    dcc.Dropdown(
                        id='metric-dropdown_2',
                        options=[
                            {'label': 'Incident Counts', 'value': 'incidents_2'},
                            {'label': 'Death Ratio (%)', 'value': 'Death_Ratio_2'}
                        ],
                        value='incidents_2',
                        placeholder="Select a Metric",
                        style={'width': '90%', 'margin-top': '10px'}
                    ),
                    dcc.Graph(id='bar-chart_2', style={'height': '355px', 'margin-top': '10px'})
                ])
            ], style={'box-shadow': '0 2px 8px rgba(0,0,0,0.1)', 'border': 'none'})
        ], width=4)
    ], className="g-4 mt-4 mb-4"),
    footer
], fluid=True, style={'background': '#ECF0F1', 'min-height': '100vh'})


########################################
# CALLBACKS FOR FIRST SNIPPET
########################################
@app.callback(
    Output('choropleth-map', 'figure'),
    [Input('metric-filter', 'value'),
     Input('month-filter', 'value')]
)
def update_map(selected_metric, selected_month):
    if selected_month == 'All':
        filtered_data = combined_data[combined_data['IncidentMonth'] == 'All']
        title_month = "All Months"
    else:
        filtered_data = combined_data[combined_data['IncidentMonth'] == selected_month]
        title_month = datetime.strptime(selected_month, "%m").strftime("%B")

    if selected_metric == 'IncidentCount':
        color_scale = px.colors.sequential.Reds
        title = f"Total Number of Incidents by State for {title_month}"
        color_label = "Incident Counts"
    else:
        color_scale = px.colors.sequential.Reds
        title = f"Death Ratio (%) by State for {title_month}"
        color_label = "Death Ratio (%)"

    if filtered_data.empty:
        fig = px.choropleth(scope="usa", title="No data available for this selection.")
        fig.update_layout(template='plotly_white')
        return fig

    fig = px.choropleth(
        filtered_data,
        locations="Abbreviation",
        locationmode="USA-states",
        color=selected_metric,
        color_continuous_scale=color_scale,
        scope="usa",
        title=title,
        labels={selected_metric: color_label},
        hover_name="FullName",
        hover_data={
            'FullName': True,
            'IncidentCount': True,
            'Death_Ratio': True
        }
    )
    fig.update_layout(template='plotly_white', title_x=0.5)
    return fig

@app.callback(
    Output('top-locations-bar-chart', 'figure'),
    [Input('metric-picker', 'value'),
     Input('month-filter-bar-chart', 'value')]
)
def update_chart(selected_metric, selected_month):
    if selected_month == 'All':
        filtered_data = complete_incident_data[complete_incident_data['IncidentMonth'] == 'All'] if selected_metric == 'Incident_Count' else complete_victim_data[complete_victim_data['IncidentMonth'] == 'All']
    else:
        filtered_data = complete_incident_data[complete_incident_data['IncidentMonth'] == selected_month] if selected_metric == 'Incident_Count' else complete_victim_data[complete_victim_data['IncidentMonth'] == selected_month]
    
    if selected_metric == 'Death_Ratio':
        filtered_data = filtered_data.groupby('Location', as_index=False).agg({
            'Total_Victims': 'sum',
            'Victims_Killed': 'sum'
        })
        filtered_data['Death_Ratio'] = filtered_data.apply(
            lambda row: (row['Victims_Killed'] / row['Total_Victims']) * 100 if row['Total_Victims'] > 0 else 0,
            axis=1
        )
        top_10_locations = filtered_data.nlargest(10, 'Death_Ratio')
        y_axis_title = 'Death Ratio (%)'
        x_data = 'Death_Ratio'
    else:  
        top_10_locations = filtered_data.nlargest(10, 'IncidentCount')
        y_axis_title = 'Incident Count'
        x_data = 'IncidentCount'
    
    top_10_locations = top_10_locations.sort_values(by=x_data, ascending=True)
    fig = px.bar(
        top_10_locations,
        x=x_data,
        y='State' if selected_metric == 'Incident_Count' else 'Location',
        orientation='h',
        title=f"Top 10 States by {y_axis_title} ({'All Months' if selected_month == 'All' else datetime.strptime(selected_month, '%m').strftime('%B')})",
        labels={x_data: y_axis_title, 'Location': 'State'},
        text=x_data,
        color=x_data,
        color_continuous_scale=px.colors.sequential.Reds
    )

    if selected_metric == 'Death_Ratio':
        fig.update_traces(texttemplate='%{text:.2f}%')

    fig.update_traces(textposition='outside')
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(t=50, l=25, r=25, b=25),
        xaxis=dict(title=y_axis_title),
        yaxis=dict(title="State"),
        template='plotly_white',
        title_x=0.5
    )
    return fig

########################################
# CALLBACKS FOR SECOND SNIPPET (With _2 suffix)
########################################
@app.callback(
    Output('marker-layer_2', 'children'),
    [Input('date-picker-range_2', 'start_date'),
     Input('date-picker-range_2', 'end_date')]
)
def update_markers_2(start_date, end_date):
    filtered_data_2 = incidents_data_2[
        (incidents_data_2['IncidentDate_2'] >= pd.to_datetime(start_date)) &
        (incidents_data_2['IncidentDate_2'] <= pd.to_datetime(end_date))
    ]

    max_victims_2 = filtered_data_2['TotalVictims_2'].max() if not filtered_data_2.empty else 1

    markers = []
    for _, row in filtered_data_2.iterrows():
        if row['TotalVictims_2'] > 0:
            death_ratio = (row['TotalKilled_2'] / row['TotalVictims_2']) * 100
        else:
            death_ratio = 0

        markers.append(
            dl.CircleMarker(
                center=[row['Latitude_2'], row['Longitude_2']],
                radius=15 + (row['TotalIncidents_2'] / filtered_data_2['TotalIncidents_2'].max() * 10),
                color=f"rgba(255, 0, 0, {row['TotalVictims_2'] / max_victims_2})",
                fill=True,
                fillColor=f"rgba(255, 0, 0, {row['TotalVictims_2'] / max_victims_2})",
                fillOpacity=0.7,
                children=[
                    dl.Popup(
                        html.Div([
                    html.P(f"IncidentIDs: {row['IncidentIDs_2']}"),
                    html.P(f"State: {row['StateName_2']}"),
                    html.P(f"City/County: {row['City_CountyName_2']}"),
                    html.P(f"Date: {row['IncidentDate_2'].date()}"),
                    html.P(f"Total Killed: {row['TotalKilled_2']}"),
                    html.P(f"Total Injured: {row['TotalInjured_2']}"),
                    html.P(f"Total Victims: {row['TotalVictims_2']}"),
                    html.P(f"Death Ratio: {death_ratio:.2f}%")
                        ], style={'font-size': '12px'})
                    )
                ]
            )
        )
    return markers

@app.callback(
    Output('monthly-trends-line-chart_2', 'figure'),
    [Input('metric-picker_2', 'value')]
)
def update_monthly_chart_2(selected_metric):
    month_labels = ['January', 'February', 'March', 'April', 'May', 'June',
                    'July', 'August', 'September', 'October', 'November', 'December']
    if selected_metric == 'Incident_Count_2':
        line_trace = go.Scatter(
            x=monthly_data_2['Month_2'],
            y=monthly_data_2['Incident_Count_2'],
            mode='lines+markers',
            name='Incidents',
            line=dict(color='red', width=3),
            marker=dict(size=6, color='red')
        )
        fig = go.Figure(data=[line_trace])
        fig.update_layout(
            title="Monthly Trends of Incidents",
            xaxis=dict(title='Month', tickvals=list(range(1,13)), ticktext=month_labels),
            yaxis=dict(title='Incident Count'),
            title_x=0.5,
            template='plotly_white'
        )
    elif selected_metric == 'Victims_Over_Months_2':
        killed_trace = go.Scatter(
            x=monthly_data_2['Month_2'],
            y=monthly_data_2['Victims_Killed_2'],
            mode='lines+markers',
            name='Victims Killed',
            line=dict(color='red', width=3),
            marker=dict(size=6, color='red')
        )
        injured_trace = go.Scatter(
            x=monthly_data_2['Month_2'],
            y=monthly_data_2['Victims_Injured_2'],
            mode='lines+markers',
            name='Victims Injured',
            line=dict(color='orange', width=3),
            marker=dict(size=6, color='orange')
        )
        fig = go.Figure(data=[killed_trace, injured_trace])
        fig.update_layout(
            title="Monthly Trends of Victims (Killed and Injured)",
            xaxis=dict(title='Month', tickvals=list(range(1,13)), ticktext=month_labels),
            yaxis=dict(title='Victim Count'),
            title_x=0.5,
            template='plotly_white'
        )
    elif selected_metric == 'Victim_Killed_Ratio_Over_Months_2':
        killed_ratio_trace = go.Scatter(
            x=monthly_data_2['Month_2'],
            y=monthly_data_2['Victim_Killed_Ratio_2'],
            mode='lines+markers',
            name='Victim Killed Ratio',
            line=dict(color='red', width=3),
            marker=dict(size=6, color='red')
        )
        fig = go.Figure(data=[killed_ratio_trace])
        fig.update_layout(
            title="Monthly Trends of Victim Killed Ratio",
            xaxis=dict(title='Month', tickvals=list(range(1,13)), ticktext=month_labels),
            yaxis=dict(title='Ratio'),
            title_x=0.5,
            template='plotly_white'
        )
    return fig

@app.callback(
    Output('bar-chart_2', 'figure'),
    [Input('metric-dropdown_2', 'value')]
)
def update_day_of_week_chart_2(selected_metric):
    if selected_metric == 'incidents_2':
        title = "Total Number of Incidents by Day of Week"
        y_data = combined_daily_data_2['incidents_2']
        y_axis_title = "Incident Counts"
    else:
        title = "Death Ratio (%) by Day of Week"
        y_data = combined_daily_data_2['Death_Ratio_2']
        y_axis_title = "Death Ratio (%)"
    
    fig = go.Figure(data=[
        go.Bar(
            x=combined_daily_data_2['day_2'],
            y=y_data,
            marker=dict(
                color=y_data,
                colorscale='Reds',
                cmin=y_data.min(),
                cmax=y_data.max(),
                colorbar=dict(title=y_axis_title)
            )
        )
    ])
    
    fig.update_layout(
        title=title,
        xaxis_title="Day of Week",
        yaxis_title=y_axis_title,
        template='plotly_white',
        title_x=0.5
    )
    return fig

########################################
# RUN THE APP
########################################

if __name__ == '__main__':
    app.run_server(debug=True, port=8051)
