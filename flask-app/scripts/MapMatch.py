import pandas as pd
import requests

class MapMatch:
    HEADERS = {'Content-Type': 'application/json'}
    URL = 'http://localhost:8002/trace_route'
    def __init__(self):
        """
        MapMatch is a utility class encapsulating all functions required for 
        map matching with Valhalla's Meili match service
        """
        pass

    @staticmethod
    def prepare_meili(person_df, colnames=['lat', 'long', 'cst_datetime'], search_radius=150):
        """
        Prepare a person_df for map matching with Meili
        @param:
            - person_df: a pandas DataFrame containing the person's data
            - colnames: a list of the column names for latitude, longitude, and time
        @return:
            - request_body: a JSON string to be sent to the Meili API
        """
        lat_col, long_col, time_col = colnames
        person_df['time'] = pd.to_datetime(person_df[time_col]).dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        prepared_df = person_df[[long_col, lat_col, 'time']].copy()
        prepared_df.columns = ['lon', 'lat', 'time']
        
        meili_coordinates = prepared_df.to_json(orient='records')
        request_body = f'{{"shape": {meili_coordinates}, "search_radius": 150, "shape_match":"map_snap", "costing":"auto", "format":"osrm"}}'
        return request_body


    @classmethod
    def meili_match(cls, person_df, colnames=['lat', 'long', 'cst_datetime'], search_radius=150):
        """
        Match a person's data to the road network using Meili
        @param:
            - person_df: a pandas DataFrame containing the person's data
            - colnames: a list of the column names for latitude, longitude, and time
        @return:
            - matched_df: a pandas DataFrame containing the matched data
        """
        request_body = MapMatch.prepare_meili(person_df, colnames, search_radius)
        response = requests.post(cls.URL, data=request_body, headers=cls.HEADERS)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to match map: {response.status_code}\n{response.text}")
        
    @staticmethod
    def make_matchdf(meili_json):
        """
        Create a dataframe of 'matchings' array from meili json response which includes 
        bearing / intersection / duration / distance / transportation type information
        @param:
            - meili_json: a json response from meili API
        @return:   
            - matching_df: pd.DataFrame containing matching information
        """
        matching_rows = []
        for matching_index, matching in enumerate(meili_json['matchings']):
            for leg_index, leg in enumerate(matching['legs']):

                # Extract via waypoints for the current leg
                via_waypoints = leg.get('via_waypoints', [])

                for step_index, step in enumerate(leg['steps']):
                    # All step info
                    step_row = {
                        'matching_index': matching_index,
                        # 'leg_index': leg_index,
                        'step_index': step['intersections'][0].get('geometry_index', 0),
                        'weight_name': matching.get('weight_name', ''),
                        'match_weight': matching.get('weight', 0),
                        'match_duration_sec': matching.get('duration', 0),
                        'match_distance': matching.get('distance', 0),
                        'leg_distance': leg.get('distance', 0),
                        'leg_duration': leg.get('duration', 0),
                        'leg_weight': leg.get('weight', 0),
                        'step_name': step.get('name', ''),
                        'step_duration': step.get('duration', 0),
                        'step_distance': step.get('distance', 0),
                        'step_weight': step.get('weight', 0),
                        'step_mode': step.get('mode', ''),
                        'driving_side': step.get('driving_side', ''),
                        'step_geometry': step.get('geometry', ''),
                        'instruction': step['maneuver'].get('instruction', ''),
                        'type': step['maneuver'].get('type', ''),
                        'bearing_after': step['maneuver'].get('bearing_after', 0),
                        'bearing_before': step['maneuver'].get('bearing_before', 0),
                        'maneuver_location': step['maneuver']['location']  # Assuming 'location' always exists in 'maneuver'
                    }

                    # Identify and include waypoint information that correlates to the current step
                    for waypoint in via_waypoints:
                        if waypoint.get('geometry_index', -1) == step['intersections'][0].get('geometry_index', -2):
                            waypoint_index = waypoint.get('waypoint_index', None)
                            waypoint_distance_from_start = waypoint.get('distance_from_start', None)
                        else:
                            waypoint_index = None
                            waypoint_distance_from_start = None
                        step_row.update({
                            'waypoint_index': waypoint_index,
                            'waypoint_distance_from_start': waypoint_distance_from_start
                        })
                    
                    # Append the step_row information to matching_rows
                    matching_rows.append(step_row)

        # Create a DataFrame from the list of rows
        matching_df = pd.DataFrame(matching_rows)
        return matching_df
    
    @staticmethod
    def make_tracedf(meili_json, person_df):
        """
        Create a dataframe containing all tracepoints corresponding to each input coordinate
        from the person_df
        """
        trace_rows = []
        for trace_index, tracepoint in enumerate(meili_json['tracepoints']):
            if tracepoint is None:
                trace_row = {
                    'trace_index': trace_index,
                    'matchings_index': None,
                    'matched_lat': None,
                    'matched_long': None,
                    'alternatives_count': None,
                    'trace_distance_from_start': None,
                    'trace_name': None,
                    'trace_waypoint_index': None,
                    'cst_datetime': person_df.iloc[trace_index]['cst_datetime'],
                    'date': person_df.iloc[trace_index]['date'],
                    'time': person_df.iloc[trace_index]['time']
                }
            else:
                trace_row = {
                    'trace_index': trace_index,
                    'matchings_index': tracepoint.get('matchings_index', None),
                    'matched_lat': tracepoint.get('location', [None, None])[1],
                    'matched_long': tracepoint.get('location', [None, None])[0],
                    'alternatives_count': tracepoint.get('alternatives_count', 0),
                    'trace_distance_from_start': tracepoint.get('distance_from_start', 0),
                    'trace_name': tracepoint.get('name', ''),
                    'waypoint_index': tracepoint.get('waypoint_index', None),
                    'cst_datetime': person_df.iloc[trace_index]['cst_datetime'],
                    'date': person_df.iloc[trace_index]['date'],
                    'time': person_df.iloc[trace_index]['time']
                }
            trace_rows.append(trace_row)

        trace_df = pd.DataFrame(trace_rows)
        return trace_df