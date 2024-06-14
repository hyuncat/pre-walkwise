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

from MapVisualization import MapVisualization

app = Flask(__name__)

# Load your data
# Again, load in demo data if you don't have access to all_plt_data
all_plt_data = pd.read_csv('static/all_plt_data.csv')
# all_plt_data = pd.read_csv('static/demo_all_plt_data.csv')

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

# @app.route('/map', methods=['POST'])
# def map_view():
#     person = request.form.get('person')
#     date = request.form.get('date')
#     person_data = filter_person_and_date(all_plt_data, int(person), date)
#     gps_df = kalman_filtering(person_data)
#     folium_map = folium.Map(location=[gps_df['lat'].mean(), 
#                                       gps_df['long'].mean()])
#     # Vanilla polyline
#     folium.PolyLine(locations=gps_df[['lat', 'long']], 
#                     color="#3480eb",
#                     weight=10, 
#                     tooltip="Original GPS data").add_to(folium_map)
    
#     # Filtered polyline
#     new_lat, new_long = ['lat_filtered', 'long_filtered']
#     folium.PolyLine(locations=gps_df[[new_lat, new_long]], 
#                     color="#FF0000",
#                     weight=3, 
#                     tooltip="Kalman filtered GPS data").add_to(folium_map)
    
#     MousePosition(position="topright").add_to(folium_map)
#     folium_map.fit_bounds([[gps_df['lat'].min(), gps_df['long'].min()], 
#                             [gps_df['lat'].max(), gps_df['long'].max()]])
#     return folium_map.get_root().render()
#     # return iframe

# def json_serial(obj):
#     """JSON serializer for objects not serializable by default json code"""

#     if isinstance(obj, (datetime, date)):
#         return obj.isoformat()
#     raise TypeError ("Type %s not serializable" % type(obj))

@app.route('/geojsondata', methods=['POST'])
def geojson_data():
    person = int(request.form.get('person'))
    date = request.form.get('date')
    person_data = filter_person_and_date(all_plt_data, person, date)
    kalman_data = kalman_filtering(person_data)
    
    # Convert DataFrame to GeoDataFrame
    gdf_original = gpd.GeoDataFrame(kalman_data, geometry=[Point(xy) for xy in zip(kalman_data.long, kalman_data.lat)])
    # radius = 0.0001  # Example radius in degrees. Adjust based on your needs.
    # gdf['geometry'] = gdf.geometry.buffer(radius)
    
    gdf_original.crs = {'init': 'epsg:4326'}  # Define coordinate reference system
    gdf_original['cst_datetime'] = gdf_original['cst_datetime'].astype(str)
    gdf_original['date'] = pd.to_datetime(gdf_original['date']).dt.date.astype(str)
    gdf_original['time'] = gdf_original['time'].astype(str)

    # Do same for filtered gdf
    gdf_filtered = gpd.GeoDataFrame(kalman_data, geometry=[Point(xy) for xy in zip(kalman_data.long_filtered, kalman_data.lat_filtered)])
    gdf_filtered.crs = {'init': 'epsg:4326'}  # Define coordinate reference system
    gdf_filtered['cst_datetime'] = gdf_filtered['cst_datetime'].astype(str)
    gdf_filtered['date'] = pd.to_datetime(gdf_filtered['date']).dt.date.astype(str)
    gdf_filtered['time'] = gdf_filtered['time'].astype(str)
    
    gdf_original['type'] = 'original'
    gdf_filtered['type'] = 'filtered'

    combined_gdf = gdf_original._append(gdf_filtered)
    
    # Convert GeoDataFrame to GeoJSON
    geojson = combined_gdf.to_json()

    return jsonify(geojson)

def filter_person_and_date(data, person, date):
    """
    Filter all_plt_data for a specific person and date.
    @param:
        data: all_plt_data df (or any df with c('person', 'lat', 'long', 'date', 'time') columns)
        person: int corresponding to the person (e.g. 161)
        date: str in the format 'YYYY-MM-DD'
    """
    person_data = data[data['person'] == person]
    person_data.loc[:, 'date'] = pd.to_datetime(person_data['date']).dt.date
    person_data = person_data[person_data['date'] == pd.to_datetime(date).date()]
    return person_data


def kalman_filtering(data):
    """ 
    Apply Kalman Filter to 'lat' and 'long' columns of the input df
    @param: 
        data: pd.DataFrame with 'lat' and 'long' columns
    @return: 
        df with 2 additional columns: 'lat_filtered' and 'long_filtered'
    """
    
    data_copy = data.copy()

    # Initialize Kalman Filter with initial lat/long (why?), with 2 dimensions
    initial_state_mean = [data_copy['lat'].iloc[0], 
                          data_copy['long'].iloc[0]]
    transition_matrix = [[1, 0], 
                         [0, 1]]
    observation_matrix = [[1, 0], 
                          [0, 1]]
    kf1 = KalmanFilter(transition_matrices=transition_matrix,
                      observation_matrices=observation_matrix,
                      initial_state_mean=initial_state_mean, 
                      n_dim_obs=2)

    # Use the 'lat' and 'long' columns as the observed values
    measurements = np.asarray(data_copy[['lat', 'long']])

    
    kf1 = kf1.em(measurements) # Use expectation-maximization to estimate the initial parameters
    (smoothed_state_means, smoothed_state_covariances) = kf1.smooth(measurements) # Apply Kalman smoothing

    kf2 = KalmanFilter(n_dim_obs=2, n_dim_state=2,
                      initial_state_mean=initial_state_mean,
                      initial_state_covariance = kf1.initial_state_covariance,
                      transition_matrices=transition_matrix,
                      observation_matrices=observation_matrix,
                      observation_covariance = kf1.observation_covariance,
                      transition_covariance = kf1.transition_covariance)
    
    kf2 = kf2.em(measurements)

    # Estimate the hidden states using all observations.  These estimates
    # will be 'smoother' (and are to be preferred) to those produced by
    # simply filtering as they are made with later observations in mind.
    # Probabilistically, this method produces the mean and covariance
    # characterizing,
    #    P(x_t | z_{1:n_timesteps})
    (smoothed_state_means2, smoothed_state_covariances2) = kf2.smooth(measurements)

    # Add the filtered latitude and longitude to the DataFrame
    data_copy.loc[:, 'lat_filtered'] = smoothed_state_means2[:, 0]
    data_copy.loc[:, 'long_filtered'] = smoothed_state_means2[:, 1]

    return data_copy

def polyline(gps_df, new_coords):
    # Existing polyline function here
    MapVisualization.polyline(gps_df, new_coords)

if __name__ == '__main__':
    app.run(debug=True)
