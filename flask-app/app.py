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

from scripts.utils import filter_person_and_date, create_geodataframe
from scripts.KalmanFilter import kalman_filter
from scripts.Segment import Segment
from scripts.MapMatch import MapMatch

app = Flask(__name__)

# Load the gps walking data
all_plt_data = pd.read_csv('static/data/all_plt_data.csv')
# Again, load in demo data if you don't have access to all_plt_data
# all_plt_data = pd.read_csv('static/data/demo_all_plt_data.csv')

@app.route('/')
def index():
    """Only info needed to render index is all unique people for dropdown"""
    all_unique_people = all_plt_data['person'].unique().tolist()
    all_unique_people.sort()
    return render_template('index.html', persons=all_unique_people)


@app.route('/dates/<int:person>')
def get_dates(person):
    """Get unique dates for a specific person"""
    dates = all_plt_data[all_plt_data['person'] == person]['date'].unique()
    dates = [pd.to_datetime(date).strftime('%Y-%m-%d') for date in sorted(pd.to_datetime(dates))]
    return jsonify(dates)


@app.route('/init_map', methods=['POST'])
def init_map():
    """
    Process and return GeoJSON data for the selected person and date.

    This function does the following:
        - Filters the data for the selected person and date
        - Applies Kalman filtering,
        - Converts result (pd) to geodataframe
    
    @return: The processed data as a GeoJSON object
    """
    person = int(request.form.get('person'))
    date = request.form.get('date')

    # Filter data for the selected person and date
    person_data = filter_person_and_date(all_plt_data, person, date)
    # kalman_data = kalman_filter(person_data)
    
    # Convert pandas dataframes to GeoDataFrames
    gdf_original = create_geodataframe(person_data, 'lat', 'long')
    # gdf_original = create_geodataframe(kalman_data, 'lat', 'long')
    # gdf_filtered = create_geodataframe(kalman_data, 'kalman_lat', 'kalman_long')

    # Get list of time segmented dataframes for original data
    # person_segments = time_segmentation(person_data)
    # kalman_segments = kalman_with_segment(person_segments)
    
    # Add labels (to distinguish when plotting on map)
    gdf_original['type'] = 'original'
    # gdf_filtered['type'] = 'kalman'

    # Combine the two GeoDataFrames
    # combined_gdf = gdf_original._append(gdf_filtered)
    
    # Convert GeoDataFrame to GeoJSON
    # geojson = combined_gdf.to_json()
    geojson = gdf_original.to_json()
    return jsonify(geojson)


@app.route('/preprocess', methods=['POST'])
def preprocess():
    print('Preprocessing...')
    person = int(request.form.get('person'))
    date = request.form.get('date')
    to_kalman_filter = request.form.get('kalmanFilter') == "true"
    map_match = request.form.get('mapMatch') == "true"
    n_iter = request.form.get('n_iter')
    time_segment = request.form.get('timeSegment')
    search_radius = request.form.get('searchRadius')
    gps_accuracy = request.form.get('gpsAccuracy')
    breakage_distance = request.form.get('breakageDistance')
    interpolation_distance = request.form.get('interpolationDistance')

    print(f"Person: {person}, Date: {date}, Kalman: {to_kalman_filter}, MapMatch: {map_match}, TimeSegment: {time_segment}, SearchRadius: {search_radius}")

    original_df = filter_person_and_date(all_plt_data, person, date)
    original_gdf = create_geodataframe(original_df, 'lat', 'long')
    original_gdf['type'] = 'original'

    full_geojson = json.loads(original_gdf.to_json())
    df_to_match = original_df
    colnames_to_match = ['lat', 'long', 'cst_datetime']

    if to_kalman_filter:
        if n_iter == "" or n_iter is None:
            n_iter = 5
        n_iter = int(n_iter)
        if time_segment != "":
            segment_df = Segment.segment_df(original_df, time_cutoff=int(time_segment))
            kalman_df = Segment.kalman_filter_segments(segment_df, n_iter)
           
        else:
            kalman_df = kalman_filter(original_df, n_iter)

        kalman_gdf = create_geodataframe(kalman_df, 'kalman_lat', 'kalman_long')
        kalman_gdf['type'] = 'kalman'

        print(f"Kalman and segment{time_segment}")
        
        # Append ksegment_gdf to full_geojson
        kalman_geojson = json.loads(kalman_gdf.to_json())
        full_geojson['features'].extend(kalman_geojson['features'])
        
        df_to_match = kalman_df
        colnames_to_match = ['kalman_lat', 'kalman_long', 'cst_datetime']

    if map_match:

        match_options = {
            'search_radius': search_radius,
            'gps_accuracy': gps_accuracy,
            'breakage_distance': breakage_distance,
            'interpolation_distance': interpolation_distance
        }
        meili_json = MapMatch.meili_match(df_to_match, colnames_to_match, match_options)
        trace_df = MapMatch.make_tracedf(meili_json, original_df)
        # print colnames of trace_df
        print(trace_df.columns)
        matched_gdf = create_geodataframe(trace_df, 'matched_lat', 'matched_long')
        matched_gdf['type'] = 'matched'

        print(f"Map Matched with options: {match_options}")

        # Append matched_gdf to full_geojson
        matched_geojson = json.loads(matched_gdf.to_json())
        full_geojson['features'].extend(matched_geojson['features'])
    
    return jsonify(full_geojson)


if __name__ == '__main__':
    app.run(debug=True)
