import folium
from folium.plugins import HeatMap, HeatMapWithTime, MousePosition
import pandas as pd
import geopandas as gpd
import json 
class MapVisualization:
    def __init__(self, gps_df):
        self.gps_df = gps_df
        self.gps_df['date'] = self.gps_df['date'].apply(lambda x: x.strftime('%Y-%m-%d') if not pd.isnull(x) else '')
        self.folium_map = folium.Map(location=[gps_df['lat'].mean(), 
                                               gps_df['long'].mean()])
        gps_json = json.loads(self.gps_df.to_json())
        self.gps_df = pd.read_json(json.dumps(gps_json), convert_dates=False)
    def view_map(self):
        MousePosition(position="topright").add_to(self.folium_map)
        self.folium_map.fit_bounds([[self.gps_df['lat'].min(), self.gps_df['long'].min()], 
                                    [self.gps_df['lat'].max(), self.gps_df['long'].max()]])
        return self.folium_map


    def polyline(self, new_coords):
        """
        Create a folium map with a polyline comparing the original GPS data (blue) 
        to some new filtered data (red).

        @param:
            - new_coords: List of strings containing the column names of the new filtered data
        
        Currently comparing original coordinates to:
            - kalman filtered data
            - road snapped data
        """
        # Vanilla polyline
        folium.PolyLine(locations=self.gps_df[['lat', 'long']], 
                        color="#3480eb",
                        weight=10, 
                        tooltip="Original GPS data").add_to(self.folium_map)
        
        # Filtered polyline
        new_lat, new_long = new_coords
        folium.PolyLine(locations=self.gps_df[[new_lat, new_long]], 
                        color="#FF0000",
                        weight=3, 
                        tooltip="Kalman filtered GPS data").add_to(self.folium_map)
    
    

    def add_geojson_circles(self, new_coords):
        """
        Compare the original GPS data (blue) to some new filtered data (red) as hoverable GoeJSON circles
        """
        

        # Convert both vanilla and new pandas dataframes to geodataframes
        new_lat, new_long = new_coords
        vanilla_gdf = gpd.GeoDataFrame(self.gps_df, 
                                       geometry=gpd.points_from_xy(self.gps_df['long'], 
                                                                   self.gps_df['lat']), 
                                       crs="EPSG:4326")
        new_gdf = gpd.GeoDataFrame(self.gps_df, 
                                   geometry=gpd.points_from_xy(self.gps_df[new_long], 
                                                               self.gps_df[new_lat]), 
                                   crs="EPSG:4326")
        
        # vanilla_gdf['date'] = vanilla_gdf['date'].apply(lambda x: x.strftime('%Y-%m-%d') if not pd.isnull(x) else '')
        # new_gdf['date'] = new_gdf['date'].apply(lambda x: x.strftime('%Y-%m-%d') if not pd.isnull(x) else '')

        folium.GeoJson(
            vanilla_gdf,
            name=f'Person {self.gps_df["person"].iloc[0]}',
            marker=folium.Circle(radius=10, fill_color="blue", fill_opacity=0.4, color="black", weight=1),
            tooltip=folium.GeoJsonTooltip(fields=["person", "date", "time"]),
            popup=folium.GeoJsonPopup(fields=["person", "date", "time"]),
            highlight_function=lambda x: {"fillOpacity": 0.8},
            zoom_on_click=True,
        ).add_to(self.folium_map)

        folium.GeoJson(
            new_gdf,
            name=f'Person {self.gps_df["person"].iloc[0]}',
            marker=folium.Circle(radius=10, fill_color="red", fill_opacity=0.4, color="black", weight=1),
            tooltip=folium.GeoJsonTooltip(fields=["person", "date", "time"]),
            popup=folium.GeoJsonPopup(fields=["person", "date", "time"]),
            highlight_function=lambda x: {"fillOpacity": 0.8},
            zoom_on_click=True,
        ).add_to(self.folium_map)
       


    def heatmap(self, new_coords):
        """
        Create a heatmap comparing the original GPS data (blue-cyan) to some new filtered data (yellow-red)
        @param:
            - new_coords: List of strings containing the column names of the new filtered data
        """
        
        # Vanilla heatmap
        HeatMap(data=self.gps_df[['lat', 'long']], 
                gradient={0.4: 'blue', 0.65: 'cyan'}, 
                blur=15, 
                radius=10
        ).add_to(self.folium_map)

        # Filtered heatmap
        new_lat, new_long = new_coords
        HeatMap(data=self.gps_df[[new_lat, new_long]], 
                gradient={0.3: 'yellow', 0.65: 'red'}, 
                blur=6, 
                radius=5
        ).add_to(self.folium_map)


    def animated_heatmap(self, new_coords, animate_new_data=True):

        # Convert 'cst_datetime' column to datetime
        self.gps_df['cst_datetime'] = pd.to_datetime(self.gps_df['cst_datetime'])

        # Initialize an empty list to store cumulative data
        data = []  
        filtered_data = []
        
        new_lat, new_long = new_coords

        # Transform each row into a list and accumulate
        for _, row in self.gps_df.iterrows():
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
            HeatMap(data=self.gps_df[['lat', 'long']], 
                        gradient={0.4: 'blue', 0.65: 'cyan'}, 
                        min_opacity=0.01,
                        blur=6, 
                        radius=10,
            ).add_to(self.folium_map)
            # Animate the new filtered data
            HeatMapWithTime(
                data=filtered_data,
                index=self.gps_df['cst_datetime'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                gradient={0.3: 'yellow', 0.65: 'red'}, 
                radius=8,
                display_index=True
            ).add_to(self.folium_map)
        else:
            # Create HeatMapWithTime instance and add to the folium map
            HeatMap(data=self.gps_df[[new_lat, new_long]], 
                    gradient={0.3: 'yellow', 0.65: 'red'}, 
                    min_opacity=0.01,
                    blur=6, 
                    radius=10,
            ).add_to(self.folium_map)
            HeatMapWithTime(
                data=data,
                index=self.gps_df['cst_datetime'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                gradient={0.4: 'blue', 0.65: 'cyan'}, 
                radius=10,
                display_index=True
            ).add_to(self.folium_map)
