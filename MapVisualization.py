import folium
from folium.plugins import HeatMap, HeatMapWithTime, MousePosition
import pandas as pd


class MapVisualization:
    def __init__(self):
        pass

    @staticmethod
    def polyline(gps_df, new_coords):
        """
        Create a folium map with a polyline comparing the original GPS data (blue) 
        to some new filtered data (red).

        @param:
            - gps_df: DataFrame containing the original GPS data and some new filtered data
            - new_coords: List of strings containing the column names of the new filtered data
        
        Currently comparing original coordinates to:
            - kalman filtered data
            - road snapped data
        """
        folium_map = folium.Map(location=[gps_df['lat'].mean(), 
                                          gps_df['long'].mean()])
        # Vanilla polyline
        folium.PolyLine(locations=gps_df[['lat', 'long']], 
                        color="#3480eb",
                        weight=10, 
                        tooltip="Original GPS data").add_to(folium_map)
        
        # Filtered polyline
        new_lat, new_long = new_coords
        folium.PolyLine(locations=gps_df[[new_lat, new_long]], 
                        color="#FF0000",
                        weight=3, 
                        tooltip="Kalman filtered GPS data").add_to(folium_map)
        
        MousePosition(position="topright").add_to(folium_map)
        folium_map.fit_bounds([[gps_df['lat'].min(), gps_df['long'].min()], 
                               [gps_df['lat'].max(), gps_df['long'].max()]])
        return folium_map

    @staticmethod
    def heatmap(gps_df, new_coords):
        """
        Create a heatmap comparing the original GPS data (blue-cyan) to some new filtered data (yellow-red)
        @param:
            - gps_df: DataFrame containing the original GPS data and some new filtered data
            - new_coords: List of strings containing the column names of the new filtered data
        """
        # Create a folium map object
        folium_map = folium.Map(location=[gps_df['lat'].mean(), 
                                          gps_df['long'].mean()])
        
        # Vanilla heatmap
        HeatMap(data=gps_df[['lat', 'long']], 
                gradient={0.4: 'blue', 0.65: 'cyan'}, 
                blur=15, 
                radius=10
        ).add_to(folium_map)

        # Filtered heatmap
        new_lat, new_long = new_coords
        HeatMap(data=gps_df[[new_lat, new_long]], 
                gradient={0.3: 'yellow', 0.65: 'red'}, 
                blur=6, 
                radius=5
        ).add_to(folium_map)

        MousePosition(position="topright").add_to(folium_map)
        folium_map.fit_bounds([[gps_df['lat'].min(), gps_df['long'].min()], 
                               [gps_df['lat'].max(), gps_df['long'].max()]])
        return folium_map


    @staticmethod
    def animated_heatmap(gps_df, new_coords, animate_new_data=True):

        # Create a folium map object
        folium_map = folium.Map(location=[gps_df['lat'].mean(), gps_df['long'].mean()], zoom_start=13)

        # Convert 'cst_datetime' column to datetime
        gps_df['cst_datetime'] = pd.to_datetime(gps_df['cst_datetime'])

        # Initialize an empty list to store cumulative data
        data = []  
        filtered_data = []
        
        new_lat, new_long = new_coords

        # Transform each row into a list and accumulate
        for _, row in gps_df.iterrows():
            current_data = [[row['lat'], row['long']]]
            current_filtered_data = [row[[new_lat, new_long]].tolist()]
            if data:
                # Add current data point to the last list in 'data'
                data.append(data[-1] + current_data)
                filtered_data.append(filtered_data[-1] + current_filtered_data)
            else:
                # First entry, start with just the current data
                data.append(current_data)
                filtered_data.append(current_filtered_data)


        # Select which data to animate (sorry kind of repetitive)
        if animate_new_data is True:
            HeatMap(data=gps_df[['lat', 'long']], 
                        gradient={0.4: 'blue', 0.65: 'cyan'}, 
                        min_opacity=0.01,
                        blur=6, 
                        radius=10,
            ).add_to(folium_map)
            # Animate the new filtered data
            HeatMapWithTime(
                data=filtered_data,
                index=gps_df['cst_datetime'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                gradient={0.3: 'yellow', 0.65: 'red'}, 
                radius=8,
                display_index=True
            ).add_to(folium_map)
        else:
            # Create HeatMapWithTime instance and add to the folium map
            HeatMap(data=gps_df[[new_lat, new_long]], 
                        gradient={0.3: 'yellow', 0.65: 'red'}, 
                        min_opacity=0.01,
                        blur=6, 
                        radius=10,
            ).add_to(folium_map)
            HeatMapWithTime(
                data=data,
                index=gps_df['cst_datetime'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                gradient={0.4: 'blue', 0.65: 'cyan'}, 
                radius=10,
                display_index=True
            ).add_to(folium_map)

        MousePosition(position="topright").add_to(folium_map)
        folium_map.fit_bounds([[gps_df['lat'].min(), gps_df['long'].min()], 
                               [gps_df['lat'].max(), gps_df['long'].max()]])
        
        return folium_map
