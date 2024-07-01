import pandas as pd
import requests
from shapely.geometry import shape, LineString
import geopandas as gpd
import json

class RoadSnap:
    def __init__(self):
        pass    

    @staticmethod
    def make_snapdf(snapped_responses):
        """Parse list of json responses into snapped coordinates dataframe"""

        # Initialize list to store flattened rows
        all_batches_rows = []
        for batch_index, snapped_json in enumerate(snapped_responses):
            snapped_df = pd.json_normalize(snapped_json['matchings'])

            # Flattening the DataFrame
            batch_rows = []
            for idx, row in snapped_df.iterrows():
                for coord in row['geometry.coordinates']:
                    # Create a new row for each coordinate pair, retaining the original data
                    new_row = {
                        'batch_index': batch_index, 
                        'matchings_index': idx,
                        'confidence': row['confidence'],
                        'distance': row['distance'],
                        'duration': row['duration'],
                        'weight_name': row['weight_name'],
                        'weight': row['weight'],
                        'roadsnap_lat': coord[1],
                        'roadsnap_long': coord[0]
                    }
                    batch_rows.append(new_row)
            all_batches_rows.extend(batch_rows)
        # Convert list of dictionaries to a DataFrame
        flatsnap_df = pd.DataFrame(all_batches_rows)
        flatsnap_gdf = gpd.GeoDataFrame(flatsnap_df, 
                               geometry=gpd.points_from_xy(flatsnap_df.roadsnap_lat, flatsnap_df.roadsnap_lat),
                               crs="EPSG:4326")
        return flatsnap_gdf 

    @staticmethod
    def make_legdf(snapped_responses):
        # Initialize list to store flattened rows
        all_batches_rows = []
        for batch_index, snapped_json in enumerate(snapped_responses):
            snapped_df = pd.json_normalize(snapped_json['matchings'])

            geometries = [LineString(coords) for coords in snapped_df['geometry.coordinates']]
            geo_series = gpd.GeoSeries(geometries)
            gdf = gpd.GeoDataFrame(
                snapped_df.drop(columns=['geometry.coordinates', 'geometry.type']), 
                geometry=geo_series, 
                crs="EPSG:4326"
            )
            gdf['batch_index'] = batch_index
            all_batches_rows.append(gdf)

        all_legs_df = pd.concat(all_batches_rows)
        # reorder so batch_index is the first column
        all_legs_df = all_legs_df[['batch_index'] + [col for col in all_legs_df.columns if col != 'batch_index']]
        return all_legs_df


    @staticmethod
    def make_tracedf(snapped_responses):
        all_traces = []
        for batch_index, snapped_json in enumerate(snapped_responses):
            batch_trace_df = pd.json_normalize(snapped_json['tracepoints'])
            batch_trace_df['batch_index'] = batch_index
            all_traces.append(batch_trace_df)
        all_traces_df = pd.concat(all_traces)
        # reorder so batch_index is the first column
        all_traces_df = all_traces_df[['batch_index'] + [col for col in all_traces_df.columns if col != 'batch_index']]
        return all_traces_df

    @staticmethod
    def evaluate_snap(snapdf, snap_tracedf):
        # Trying to get some quantitative evaluations of road snapping
        # 1. Proportion of properly matched coordinates
        matched_coords = (snap_tracedf['location'].notna().sum() / len(snap_tracedf))

        # 2. Average distance from original coordinates to snapped coordinates
        avg_snap_difference = snap_tracedf['distance'].mean()

        # 3. Subdataframe where 'alternatives_count' is not 0 or None
        coords_with_alternates = snap_tracedf[(snap_tracedf['alternatives_count'] != 0) & (snap_tracedf['alternatives_count'].notna())]

        # 4. Proportion of matched coordinates that have alternatives
        matched_coords_with_alternates = (len(coords_with_alternates) / len(snap_tracedf))

        # 5. Average number of alternatives (including 0's but not None's)
        avg_alternates = snap_tracedf['alternatives_count'].mean()

        # 6. Average confidence of snapped coordinates
        avg_confidence = snapdf['confidence'].mean()

        print(f"Proportion of original coordinates which successfully snapped:\n{matched_coords}\n")
        print(f"Avg distance from original and snapped coordinates:\n{avg_snap_difference} meters\n")
        print(f"Proportion of matched coordinates with alternatives:\n{matched_coords_with_alternates}\n")
        print(f"Average number of alternatives:\n{avg_alternates}\n")
        print(f"Average confidence of snapped coordinates:\n{avg_confidence}\n")



    def format_for_osrm(gps_df: pd.DataFrame, format_cols=['lat', 'long'], batch_size=1000, radius=50):
        """
        Convert dataframe of gps coordinates and times to send to OSRM match API in batches

        @param:
            - gps_df: pd.DataFrame with 'lat', 'long', and 'cst_datetime' columns
            - batch_size: Maximum number of coordinate-timestamp pairs per batch
        @return:
            Yields two batches (lists) of strings:
            - coords: list[str, ...], each string of semicolon-separated coordinates
            - timestamps: list[str, ...] of semicolon-separated timestamps
            - radiuses: list[str, ...] of semicolon-separated radiuses
        """
        # Convert datetime to Unix timestamp (seconds since epoch)
        gps_df['unix_time'] = pd.to_datetime(gps_df['cst_datetime']).astype('int64') // 10**9

        # Sort the DataFrame by the 'unix_time' column in ascending order
        gps_df = gps_df.sort_values(by='unix_time')
        
        # Calculate total number of batches
        #TODO: Use itertools batch
        total_batches = (len(gps_df) + batch_size - 1) // batch_size
        
        lat_col, long_col = format_cols
        for i in range(total_batches):
            batch_df = gps_df.iloc[i*batch_size:(i+1)*batch_size]
            coords = ';'.join(f"{lon},{lat}" for lon, lat in zip(batch_df[long_col], batch_df[lat_col]))
            timestamps = ';'.join(batch_df['unix_time'].astype(str))
            radiuses = ';'.join(str(radius) for _ in range(len(batch_df)))
            yield coords, timestamps, radiuses

    @staticmethod 
    def snap_roads(gps_df: pd.DataFrame, format_cols=['lat', 'long'], batch_size=1000, radius=50):
        """
        Send requests to the OSRM match API to snap GPS coordinates to the road network in batches
        @param:
            - gps_df: pd.DataFrame with 'lat', 'long', and 'cst_datetime' columns
        @return:
            - List of JSON responses from the OSRM match API
        """
        responses = []
        for coords, timestamps, radiuses in RoadSnap.format_for_osrm(gps_df, format_cols=format_cols, batch_size=batch_size, radius=radius):
            url = f"http://127.0.0.1:9000/match/v1/foot/{coords}?steps=true&geometries=geojson&annotations=true&overview=full&timestamps={timestamps}&radiuses={radiuses}"
            response = requests.get(url)
            if response.status_code == 200:
                responses.append(response.json())
            else:
                # Raises an exception with the error status and message for the first failed request
                raise Exception(f"Request failed with status {response.status_code}: {response.text}")
        return responses

    

    # @staticmethod
    # def parse_match_response(match_response):
    #     """
    #     Parse a JSON response from OSRM match API to extract the 
    #     snapped coordinates to a pandas dataframe

    #     @param:
    #         - response: JSON response from OSRM match API
    #     @return:
    #         - snapped_df: pd.DataFrame with 'snapped_long' and 'snapped_lat' columns
    #     """
    #     #TODO: assign each matching to a different array, maybe pd.df['matchings_index', 'confidence', 'coords_list']
    #     #TODO: display confidence + exact matched coords
    #     # Also, need to map time information of original data to snapped data (using tracepoints)
        
    #     # Extract the route geometries from the matchings

    #     matchings = match_response.get('matchings', [])
    #     road_snapped_coords = []

    #     for matched_coordinate in matchings:
    #         if 'geometry' in matched_coordinate:
    #             geom = shape(matched_coordinate['geometry'])  # Convert GeoJSON to Shapely geometry
    #             road_snapped_coords.extend(list(geom.coords))

    #     # Create DataFrame for the new coordinates
    #     snapped_df = pd.DataFrame(road_snapped_coords, columns=['snapped_long', 'snapped_lat'])
    #     return snapped_df

    # @staticmethod
    # def snap_all_segments(gps_segments):
    #     """
    #     Snap all time-separated gps segments to the road network using OSRM
    #     @param (output from time_segmentation):
    #         - gps_segments: List of pd.DataFrames with 'lat', 'long', and 'cst_datetime' columns
    #     @return:
    #         - List of pd.DataFrames with 'snapped_long', 'snapped_lat', and 'segment' columns
    #     """
    #     snapped_dfs = []
    #     for segment_df in gps_segments:
    #         coords, timestamps = format_for_osrm(segment_df)
    #         try:
    #             match_response = send_osrm_match_request(coords, timestamps)
    #             snapped_df = parse_osrm_match_response(match_response)
    #             snapped_dfs.append(snapped_df)
    #         except Exception as e:
    #             print(f"Failed to process segment: {e}")
    #     return snapped_dfs
    # def _format_coords(gps_df: pd.DataFrame, format_cols=['lat', 'long', 'cst_datetime']):
    #     """
    #     Convert dataframe of gps coordinates and times to send to OSRM match API
    #     Dataframe should contain 'lat', 'long', and 'cst_datetime' columns.

    #     @param:
    #         - gps_df: pd.DataFrame with coordinate + timestamp information
    #         - format_cols: list, names of the columns to format (if not default)
    #     @return:
    #         - coords_string: str, of semicolon-separated coordinates
    #         - times_string: str, of semicolon-separated timestamps
    #     """
    #     # Convert datetime to Unix timestamp (seconds since epoch)
    #     gps_df = gps_df.copy()
    #     lat_col, long_col, time_col = format_cols
    #     gps_df['unix_time'] = pd.to_datetime(gps_df[time_col]).astype('int64') // 10**9

    #     # Turn column of coords into a string of semicolon-separated coordinates
    #     coords_string = ';'.join(f"{long},{lat}" for long, lat in zip(gps_df[long_col], gps_df[lat_col]))
    #     times_string = ';'.join(gps_df['unix_time'].astype(str))

    #     return coords_string, times_string

    # def _send_match_request(coords: str, timestamps: str):
    #     """
    #     Send a request to the OSRM match API to snap GPS coordinates to the road network
    #     @param (results from format_for_osrm):
    #         - coords: String of semicolon-separated coordinates
    #         - timestamps: String of semicolon-separated timestamps
    #     @return:
    #         - JSON response from the OSRM match API
    #     """
    #     url = f"http://127.0.0.1:9000/match/v1/foot/{coords}?steps=true&geometries=geojson&annotations=true&overview=full&timestamps={timestamps}"
    #     match_response = requests.get(url)
    #     if match_response.status_code == 200:
    #         return match_response.json()  # Returns JSON directly
    #     else:
    #         # Raises an exception with the error status and message
    #         raise Exception(f"Request failed with status {match_response.status_code}: {match_response.text}")
        

    # def snap_request(gps_df, format_cols=['lat', 'long', 'cst_datetime'], batch_size=1000):
    #     """
    #     Snap GPS coordinates to the road network using the OSRM match API
    #     @param:
    #         - gps_df: pd.DataFrame with 'lat', 'long', and 'cst_datetime' columns
    #         - batch_size: maximum batch size for each request
    #     @return:
    #         - pd.DataFrame with 'snapped_long', 'snapped_lat', and 'segment' columns
    #     """
    #     coords, timestamps = RoadSnap._format_coords(gps_df, format_cols)

    #     snapped_responses = []
    #     for coord, time in zip(coords, timestamps):
    #         try:
    #             match_response = RoadSnap._send_match_request(coord, time)
    #             snapped_responses.append(match_response)
    #         except Exception as e:
    #             print(f"Failed to process segment: {e}")
    #     return snapped_responses