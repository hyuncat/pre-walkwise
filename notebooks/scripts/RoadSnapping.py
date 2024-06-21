import pandas as pd
import requests
from shapely.geometry import shape

def format_for_osrm(gps_df: pd.DataFrame):
    """
    Convert dataframe of gps coordinates and times to send to OSRM match API

    @param:
        - gps_df: pd.DataFrame with 'lat', 'long', and 'cst_datetime' columns
    @return:
        - coords: String of semicolon-separated coordinates
        - timestamps: String of semicolon-separated timestamps
    """
    # Convert datetime to Unix timestamp (seconds since epoch)
    gps_df['unix_time'] = pd.to_datetime(gps_df['cst_datetime']).astype('int64') // 10**9
    coords = ';'.join(f"{lon},{lat}" for lon, lat in zip(gps_df['long'], gps_df['lat']))
    timestamps = ';'.join(gps_df['unix_time'].astype(str))
    return coords, timestamps

def send_osrm_match_request(coords: str, timestamps: str):
    """
    Send a request to the OSRM match API to snap GPS coordinates to the road network
    @param (results from format_for_osrm):
        - coords: String of semicolon-separated coordinates
        - timestamps: String of semicolon-separated timestamps
    @return:
        - JSON response from the OSRM match API
    """
    url = f"http://127.0.0.1:9000/match/v1/foot/{coords}?steps=true&geometries=geojson&annotations=true&overview=full&timestamps={timestamps}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()  # Returns JSON directly
    else:
        # Raises an exception with the error status and message
        raise Exception(f"Request failed with status {response.status_code}: {response.text}")
    
def parse_osrm_match_response(match_response):
    """
    Parse a JSON response from OSRM match API to extract the 
    snapped coordinates to a pandas dataframe

    @param:
        - response: JSON response from OSRM match API
    @return:
        - snapped_df: pd.DataFrame with 'snapped_long' and 'snapped_lat' columns
    """
    # Extract the route geometries from the matchings
    matchings = match_response.get('matchings', [])
    road_snapped_coords = []

    for matched_coordinate in matchings:
        if 'geometry' in matched_coordinate:
            geom = shape(matched_coordinate['geometry'])  # Convert GeoJSON to Shapely geometry
            road_snapped_coords.extend(list(geom.coords))

    # Create DataFrame for the new coordinates
    snapped_df = pd.DataFrame(road_snapped_coords, columns=['snapped_long', 'snapped_lat'])
    return snapped_df

def snap_all_segments(gps_segments):
    """
    Snap all time-separated gps segments to the road network using OSRM
    @param (output from time_segmentation):
        - gps_segments: List of pd.DataFrames with 'lat', 'long', and 'cst_datetime' columns
    @return:
        - List of pd.DataFrames with 'snapped_long', 'snapped_lat', and 'segment' columns
    """
    snapped_dfs = []
    for segment_df in gps_segments:
        coords, timestamps = format_for_osrm(segment_df)
        try:
            match_response = send_osrm_match_request(coords, timestamps)
            snapped_df = parse_osrm_match_response(match_response)
            snapped_dfs.append(snapped_df)
        except Exception as e:
            print(f"Failed to process segment: {e}")
    return snapped_dfs