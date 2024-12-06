import dash
from dash import dcc, html, Input, Output
import pandas as pd
import sqlite3
import plotly.express as px

# Load and prepare data from SQLite
conn = sqlite3.connect('FinalProject.sqlite')
query = """
SELECT 
    `StateName` AS Location,
    `VictimKilled` AS Victims_Killed,
    `VictimInjured` AS Victims_Injured
FROM Incidents NATURAL JOIN Locations NATURAL JOIN Victims;
"""
gun_violence_data = pd.read_sql_query(query, conn)
conn.close()

# Preprocess data to calculate the number of incidents per location
gun_violence_data['Incident_Count'] = 1
gun_violence_data['Total_Victims'] = gun_violence_data['Victims_Killed'] + gun_violence_data['Victims_Injured']

# Group by location and aggregate data
location_data = gun_violence_data.groupby('Location').agg({
    'Incident_Count': 'sum',
    'Total_Victims': 'sum',
    'Victims_Killed': 'sum',
    'Victims_Injured': 'sum'
}).reset_index()

# Calculate Victim Ratio (handling division by zero)
location_data['Victim_Ratio'] = location_data.apply(
    lambda row: row['Victims_Killed'] / row['Total_Victims'] if row['Total_Victims'] > 0 else 0,
    axis=1
)

# Define a valid sequential color scale (e.g., Blues for darker higher values)
color_scales = px.colors.sequential.Reds

# Initialize Dash app
app = dash.Dash(__name__)
server = app.server

# Layout of the Dash app
app.layout = html.Div([
    html.H1("Top 10 States for Gun Violence Incidents"),
    dcc.Dropdown(
        id='metric-picker',
        options=[
            {'label': 'Number of Incidents', 'value': 'Incident_Count'},
            {'label': 'Total Victims', 'value': 'Total_Victims'},
            {'label': 'Victim Ratio (Killed/Total)', 'value': 'Victim_Ratio'}
        ],
        value='Incident_Count',
        clearable=False,
        style={'width': '50%'}
    ),
    dcc.Graph(id='top-locations-bar-chart')
])

# Callback to update the chart based on the selected metric
@app.callback(
    Output('top-locations-bar-chart', 'figure'),
    [Input('metric-picker', 'value')]
)
def update_chart(selected_metric):
    # Sort and select top 10 locations based on the selected metric
    top_10_locations = location_data.nlargest(10, selected_metric)
    top_10_locations = top_10_locations.sort_values(by=selected_metric, ascending=False)

    # Create the horizontal bar chart
    fig = px.bar(
        top_10_locations,
        x=selected_metric,  # Value goes on the x-axis
        y='Location',       # Locations on the y-axis
        orientation='h',    # Set orientation to horizontal
        title=f"Top 10 Locations by {selected_metric.replace('_', ' ').title()}",
        labels={selected_metric: 'Value', 'Location': 'Location'},
        text=selected_metric,
        color=selected_metric,  # Color bars based on the metric
        color_continuous_scale=color_scales,
        category_orders={"Location": top_10_locations['Location'].tolist()}  # Ensure the order
    )
    
    # Adjust text formatting for Victim Ratio
    if selected_metric == 'Victim_Ratio':
        fig.update_traces(texttemplate='%{text:.2%}')  # Format as percentage
    
    fig.update_traces(textposition='outside')
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(t=50, l=25, r=25, b=25),
        xaxis=dict(title=selected_metric.replace('_', ' ').title()),
        yaxis=dict(title="Location")
    )
    return fig

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
