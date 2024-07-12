import folium
from folium import FeatureGroup
from folium.plugins import MousePosition
import colour
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pandas as pd

class PlotMap:
    def __init__(self, person_df, tile_type='osm'):
        self.person_df = person_df

        # Base tiles
        tiles = {
            'osm': 'OpenStreetMap',
            'dark': 'CartoDB dark_matter',
            'light': 'CartoDB positron'
        }

        # Always assume a person_df contains 'lat' and 'long' columns
        # Initialize the map with the first tile option
        self.folium_map = folium.Map(location=[person_df['lat'].mean(), person_df['long'].mean()],
                                     tiles=tiles[tile_type])

        
        # Color dicts for original, kalman, vs. road snapped data
        self.full_polyline_colors = {
            "original": "#006EC7",
            "kalman": "#931310",
            "road_snapped": "#FF87D5",
            "matched": "#FF87D5"
        }
        self.segment_lineweights = {
            "original": 15,
            "kalman": 15,
            "road_snapped": 15,
            "matched": 15
        }
        self.segment_colors = {
            "original": "#1395FFB3",
            "kalman": "#E1515BB3",
            "road_snapped": "#FF87D5B3",
            "matched": "#FF87D5B3"
        }
        self.circle_colors = {
            "original": "#1395FF",
            "kalman": "#C61613",
            "road_snapped": "#f2f2f2",
            "matched": "#EB96CE"
        }
        self.circle_radiuses = {
            "original": 4.5,
            "kalman": 4.5,
            "road_snapped": 4.5,
            "matched": 4.5
        }
        self.tooltips = {
            "original": "<b>Original GPS data</b>",
            "kalman": "<b>Kalman filtered GPS data</b>",
            "road_snapped": "<b>Road snapped GPS data</b>",
            "matched": "<b>Map matched GPS data</b>"
        }
        # Column names for original, kalman, vs. road snapped data
        self.coord_cols = {
            "original": ['lat', 'long'],
            "kalman": ['kalman_lat', 'kalman_long'],
            "road_snapped": ['roadsnap_lat', 'roadsnap_long'],
            "matched": ['matched_lat', 'matched_long']
        }

    def show(self):
        """Display the map"""
        MousePosition(position="topright").add_to(self.folium_map)
        self.folium_map.fit_bounds([[self.person_df['lat'].min(), self.person_df['long'].min()], 
                                    [self.person_df['lat'].max(), self.person_df['long'].max()]])
        folium.LayerControl(position='topright', collapsed=False).add_to(self.folium_map)
        return self.folium_map
    
    def full_polyline(self, gps_df, coord_type="original"):
        """Add a thin line connecting all coordinates with the given column names"""
        coord_cols = self.coord_cols[coord_type]
        full_polyline_color = self.full_polyline_colors[coord_type]
        full_polyline_tooltip = self.tooltips[coord_type]
        name = 'Polyline: ' + coord_type
        
        # Drop rows with NaN values in coord_cols
        gps_df = gps_df.dropna(subset=coord_cols)
        
        full_polyline = folium.PolyLine(
            locations=gps_df[coord_cols], 
            color=full_polyline_color,
            weight=3, 
            tooltip=full_polyline_tooltip,
            name=name
        )
        
        # Add polyline to feature group to allow layer control
        fg = FeatureGroup(name=name)
        full_polyline.add_to(fg)
        fg.add_to(self.folium_map)

    def segment_polyline(self, segment_df, coord_type="original"):
        """Add thicker lines connecting all coordinates within the same time segment"""

        coord_cols = self.coord_cols[coord_type]
        segment_color = self.segment_colors[coord_type]
        segment_lineweight = self.segment_lineweights[coord_type]
        name = 'Segment Polyline: ' + coord_type

        for i, df in segment_df.groupby('segment'):
            segment_tooltip = self.tooltips[coord_type] + f"<br>Segment {i}"
            folium.PolyLine(
                locations=df[coord_cols], 
                color=segment_color,
                weight=segment_lineweight, 
                tooltip=segment_tooltip,
                name=name
            ).add_to(self.folium_map)

    def circles(self, gps_df, coord_type="original"):
        """Add circles to the map with the given column names"""
        coord_cols = self.coord_cols[coord_type]
        circle_color = self.circle_colors[coord_type]
        circle_radius = self.circle_radiuses[coord_type]
        name = 'Circles: ' + coord_type
        
        # Make a darker version of the circle color for outline
        hsl_color = colour.Color(circle_color) # Convert hex color to HSL
        # Decrease lightness by 20%
        hsl_color.luminance = max(0, hsl_color.luminance - 0.2)  # Ensure luminance doesn't go below 0
        darker_circle_color = hsl_color.hex_l
        
        # Create feature group to allow layer control
        fg = folium.FeatureGroup(name=name)

        for i, row in gps_df.iterrows():

            # Tooltip content
            if coord_type == "original" or coord_type == "kalman":
                # Convert date to datetime, then to string (just in case)
                date = pd.to_datetime(row['cst_datetime'])
                date_string = date.strftime('%Y-%m-%d %H:%M:%S') if 'cst_datetime' in row else ''
                circle_tooltip = self.tooltips[coord_type] + f"<br>Coordinates: {row[coord_cols[0]]}, {row[coord_cols[1]]}<br>Time: {date_string}"
            elif coord_type == "road_snapped":
                circle_tooltip = self.tooltips[coord_type] + f"<br>Coordinates: {row[coord_cols[0]]}, {row[coord_cols[1]]}<br>Batch: {row['batch_index']}<br>Matching: {row['matchings_index']}<br>Confidence: {row['confidence']}"
            elif coord_type == "matched":
                # Skip rows with NaN values in coord_cols
                if pd.isnull(row[coord_cols]).any():
                    continue
                date = pd.to_datetime(row['cst_datetime'])
                date_string = date.strftime('%Y-%m-%d %H:%M:%S') if 'cst_datetime' in row else ''
                circle_tooltip = self.tooltips[coord_type] + f"<br>Coordinates: {row[coord_cols[0]]}, {row[coord_cols[1]]}<br>Time: {date_string}<br>matchings_index: {row['matchings_index']}<br>Alternatives: {row['alternatives_count']}<br>Name: {row['trace_name']}"
                if not pd.isnull(row['waypoint_index']):
                    circle_tooltip += f"<br>Waypoint Index: {row['waypoint_index']}"
            
            folium.CircleMarker(
                location=[row[coord_cols[0]], row[coord_cols[1]]],
                radius=circle_radius,
                fill_color=circle_color,
                fill_opacity=0.4,
                color=darker_circle_color, # outline color
                weight=1,
                tooltip=circle_tooltip,
                popup=circle_tooltip,
                name=name
            ).add_to(fg)
        
        fg.add_to(self.folium_map)


    def snap_leglines(self, snap_legdf, colormap='viridis'):
        """Add snapped road legs as LineStrings to the map"""
        # Create column with hex colors
        snap_legdf['color'] = snap_legdf['confidence'].apply(
            lambda x: mcolors.to_hex(plt.get_cmap(colormap)(x)[:3])
        )
        name='Road Snapped Legs'
        
        # Add LineStrings to the Map
        lineweight = self.segment_lineweights['road_snapped']
        for leg_index, row in snap_legdf.iterrows():
            # Extracting the coordinates for the LineString and reversing them to (lat, lon)
            line_coords = [(y, x) for x, y in row.geometry.coords]

            # Convert hex color to HSL
            hsl_color = colour.Color(row['color'])
            # Increase lightness by 20%
            hsl_color.luminance = min(hsl_color.luminance + 0.2, 1)  # Ensure luminance doesn't go above 1
            lighter_color_hex = hsl_color.hex_l
            
            # Create tooltip and popup content
            tooltip = self.tooltips['road_snapped'] + f"<br>Batch: {row['batch_index']}<br>Leg: {leg_index}<br>Confidence: {row['confidence']}<br>Distance: {row['distance']}<br>Duration: {row['duration']}"
            
            # Create a PolyLine with the tooltip and popup
            folium.PolyLine(
                locations=line_coords, 
                color=lighter_color_hex,
                weight=lineweight,
                tooltip=tooltip, 
                popup=tooltip,
                name=name
            ).add_to(self.folium_map)