from flask import Flask, render_template, request, Response, json, jsonify
from json import JSONEncoder

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import folium
from folium.plugins import MousePosition
from pykalman import KalmanFilter
import numpy as np
from datetime import date, datetime

from KalmanFilter import filter_person_and_date, time_segmentation, kalman_with_segment, kalman_filtering, create_geodataframe
from MapVisualization import MapVisualization

app = Flask(__name__)

# Load your data
# Again, load in demo data if you don't have access to all_plt_data
all_plt_data = pd.read_csv('static/data/all_plt_data.csv')
# all_plt_data = pd.read_csv('static/data/demo_all_plt_data.csv')

@app.route('/')
def index():
    # Get unique persons for the dropdown
    persons = all_plt_data['person'].unique().tolist()
    persons.sort()
    return render_template('index.html', persons=persons)


@app.route('/dates/<int:person>')
def get_dates(person):
    # Get unique dates for a specific person
    dates = all_plt_data[all_plt_data['person'] == person]['date'].unique()
    dates = [pd.to_datetime(date).strftime('%Y-%m-%d') for date in sorted(pd.to_datetime(dates))]
    return jsonify(dates)


@app.route('/geojsondata', methods=['POST'])
def geojson_data():
    person = int(request.form.get('person'))
    date = request.form.get('date')

    # Filter data for the selected person and date
    person_data = filter_person_and_date(all_plt_data, person, date)
    kalman_data = kalman_filtering(person_data)
    
    # Convert pandas dataframes to GeoDataFrames
    gdf_original = create_geodataframe(kalman_data, 'lat', 'long')
    gdf_filtered = create_geodataframe(kalman_data, 'lat_filtered', 'long_filtered')
    
    # Add labels (to distinguish when plotting on map)
    gdf_original['type'] = 'original'
    gdf_filtered['type'] = 'filtered'

    # Combine the two GeoDataFrames
    combined_gdf = gdf_original._append(gdf_filtered)
    
    # Convert GeoDataFrame to GeoJSON
    geojson = combined_gdf.to_json()

    return jsonify(geojson)



def polyline(gps_df, new_coords):
    MapVisualization.polyline(gps_df, new_coords)

if __name__ == '__main__':
    app.run(debug=True)
