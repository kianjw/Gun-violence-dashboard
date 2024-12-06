import dash
from dash import dcc, html, Input, Output
import pandas as pd
import sqlite3
import plotly.graph_objects as go

# Load and prepare data from SQLite
conn = sqlite3.connect('FinalProject.sqlite')
query = """
SELECT 
    `IncidentDate` AS Date,
    `VictimKilled` AS Victims_Killed,
    `VictimInjured` AS Victims_Injured
FROM Incidents NATURAL JOIN Victims;
"""
data = pd.read_sql_query(query, conn)
conn.close()

# Convert Date to datetime and handle invalid dates
data['Date'] = pd.to_datetime(data['Date'], format='%B %d, %Y', errors='coerce')

# Drop rows with invalid dates
data = data.dropna(subset=['Date'])

# Add columns for incidents and extract months
data['Incident_Count'] = 1
data['Month'] = data['Date'].dt.month

# Aggregate data by month
monthly_data = data.groupby('Month').agg({
    'Incident_Count': 'sum',
    'Victims_Killed': 'sum',
    'Victims_Injured': 'sum'
}).reset_index()

# Calculate Victim Killed Ratio (handling division by zero)
monthly_data['Victim_Killed_Ratio'] = monthly_data.apply(
    lambda row: row['Victims_Killed'] / (row['Victims_Killed'] + row['Victims_Injured']) if (row['Victims_Killed'] + row['Victims_Injured']) > 0 else 0,
    axis=1
)

# Initialize Dash app
app = dash.Dash(__name__)
server = app.server

# Layout of the Dash app
app.layout = html.Div([
    html.H1("Gun Violence Trends Over Months"),
    dcc.Dropdown(
        id='metric-picker',
        options=[
            {'label': 'Incidents Over Months', 'value': 'Incident_Count'},
            {'label': 'Victims Over Months (Killed and Injured)', 'value': 'Victims_Over_Months'},
            {'label': 'Victim Killed Ratio Over Months', 'value': 'Victim_Killed_Ratio_Over_Months'}
        ],
        value='Incident_Count',
        clearable=False,
        style={'width': '50%'}
    ),
    dcc.Graph(id='monthly-trends-line-chart')
])

# Callback to update the chart based on dropdown selection
@app.callback(
    Output('monthly-trends-line-chart', 'figure'),
    [Input('metric-picker', 'value')]
)
def update_chart(selected_metric):
    if selected_metric == 'Incident_Count':
        # Create line chart for number of incidents over months
        line_trace = go.Scatter(
            x=monthly_data['Month'],
            y=monthly_data['Incident_Count'],
            mode='lines+markers',
            name='Incidents (Line)',
            line=dict(color='blue', width=3),
            marker=dict(size=6, color='blue')
        )
        
        fig = go.Figure(data=[line_trace])
        fig.update_layout(
            title="Monthly Trends of Incidents",
            xaxis=dict(title='Month', tickvals=list(range(1, 13)), ticktext=['January', 'February', 'March', 'April', 'May', 'June', 
                                                                          'July', 'August', 'September', 'October', 'November', 'December']),
            yaxis=dict(title='Incident Count'),
            title_x=0.5
        )

    elif selected_metric == 'Victims_Over_Months':
        # Create line chart for victims killed and injured over months
        killed_trace = go.Scatter(
            x=monthly_data['Month'],
            y=monthly_data['Victims_Killed'],
            mode='lines+markers',
            name='Victims Killed',
            line=dict(color='red', width=3),
            marker=dict(size=6, color='red')
        )

        injured_trace = go.Scatter(
            x=monthly_data['Month'],
            y=monthly_data['Victims_Injured'],
            mode='lines+markers',
            name='Victims Injured',
            line=dict(color='orange', width=3),
            marker=dict(size=6, color='orange')
        )
        
        fig = go.Figure(data=[killed_trace, injured_trace])
        fig.update_layout(
            title="Monthly Trends of Victims (Killed and Injured)",
            xaxis=dict(title='Month', tickvals=list(range(1, 13)), ticktext=['January', 'February', 'March', 'April', 'May', 'June', 
                                                                          'July', 'August', 'September', 'October', 'November', 'December']),
            yaxis=dict(title='Victim Count'),
            title_x=0.5
        )

    elif selected_metric == 'Victim_Killed_Ratio_Over_Months':
        # Create line chart for Victim Killed Ratio
        killed_ratio_trace = go.Scatter(
            x=monthly_data['Month'],
            y=monthly_data['Victim_Killed_Ratio'],
            mode='lines+markers',
            name='Victim Killed Ratio',
            line=dict(color='blue', width=3),
            marker=dict(size=6, color='blue')
        )

        fig = go.Figure(data=[killed_ratio_trace])
        fig.update_layout(
            title="Monthly Trends of Victim Killed Ratio",
            xaxis=dict(title='Month', tickvals=list(range(1, 13)), ticktext=['January', 'February', 'March', 'April', 'May', 'June', 
                                                                          'July', 'August', 'September', 'October', 'November', 'December']),
            yaxis=dict(title='Ratio'),
            title_x=0.5
        )
        fig.update_traces(texttemplate='%{y:.2%}')  # Format as percentage

    return fig

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
