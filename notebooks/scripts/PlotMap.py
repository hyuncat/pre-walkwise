import folium
from folium.plugins import MousePosition
import colour
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pandas as pd

class PlotMap:
    def __init__(self, person_df):
        self.person_df = person_df
        # Always assume a person_df contains 'lat' and 'long' columns
        self.folium_map = folium.Map(location=[person_df['lat'].mean(), 
                                               person_df['long'].mean()])
        
        # Color dicts for original, kalman, vs. road snapped data
        self.full_polyline_colors = {
            "original": "#006EC7",
            "kalman": "#9D0B24",
            "road_snapped": "#FF87D5"
        }
        self.segment_lineweights = {
            "original": 14,
            "kalman": 14,
            "road_snapped": 14
        }
        self.segment_colors = {
            "original": "#1395FFB3",
            "kalman": "#EB3856B3",
            "road_snapped": "#FF87D5B3"
        }
        self.circle_colors = {
            "original": "#1395FF",
            "kalman": "#EB3856",
            "road_snapped": "#f2f2f2"
        }
        self.circle_radiuses = {
            "original": 5,
            "kalman": 5,
            "road_snapped": 5
        }
        self.tooltips = {
            "original": "<b>Original GPS data</b>",
            "kalman": "<b>Kalman filtered GPS data</b>",
            "road_snapped": "<b>Road snapped GPS data</b>"
        }
        # Column names for original, kalman, vs. road snapped data
        self.coord_cols = {
            "original": ['lat', 'long'],
            "kalman": ['kalman_lat', 'kalman_long'],
            "road_snapped": ['roadsnap_lat', 'roadsnap_long']
        }

    def show(self):
        """Display the map"""
        MousePosition(position="topright").add_to(self.folium_map)
        self.folium_map.fit_bounds([[self.person_df['lat'].min(), self.person_df['long'].min()], 
                                    [self.person_df['lat'].max(), self.person_df['long'].max()]])
        return self.folium_map
    
    def full_polyline(self, gps_df, coord_type="original"):
        """Add a thin line connecting all coordinates with the given column names"""
        coord_cols = self.coord_cols[coord_type]
        full_polyline_color = self.full_polyline_colors[coord_type]
        full_polyline_tooltip = self.tooltips[coord_type]
        folium.PolyLine(
            locations=gps_df[coord_cols], 
            color=full_polyline_color,
            weight=3, 
            tooltip=full_polyline_tooltip
        ).add_to(self.folium_map)

    def segment_polyline(self, segment_df, coord_type="original"):
        """Add thicker lines connecting all coordinates within the same time segment"""

        coord_cols = self.coord_cols[coord_type]
        segment_color = self.segment_colors[coord_type]
        segment_lineweight = self.segment_lineweights[coord_type]

        for i, df in segment_df.groupby('segment'):
            segment_tooltip = self.tooltips[coord_type] + f"<br>Segment {i}"
            folium.PolyLine(
                locations=df[coord_cols], 
                color=segment_color,
                weight=segment_lineweight, 
                tooltip=segment_tooltip
            ).add_to(self.folium_map)

    def circles(self, gps_df, coord_type="original"):
        """Add circles to the map with the given column names"""
        coord_cols = self.coord_cols[coord_type]
        circle_color = self.circle_colors[coord_type]
        circle_radius = self.circle_radiuses[coord_type]
        
        # Make a darker version of the circle color for outline
        hsl_color = colour.Color(circle_color) # Convert hex color to HSL
        # Decrease lightness by 20%
        hsl_color.luminance = max(0, hsl_color.luminance - 0.2)  # Ensure luminance doesn't go below 0
        darker_circle_color = hsl_color.hex_l
        
        for i, row in gps_df.iterrows():
            # Tooltip content
            if coord_type == "original" or coord_type == "kalman":
                # Convert date to datetime, then to string (just in case)
                date = pd.to_datetime(row['cst_datetime'])
                date_string = date.strftime('%Y-%m-%d') if 'cst_datetime' in row else ''
                circle_tooltip = self.tooltips[coord_type] + f"<br>Coordinates: {row[coord_cols[0]]}, {row[coord_cols[1]]}<br>Time: {date_string}"
            elif coord_type == "road_snapped":
                circle_tooltip = self.tooltips[coord_type] + f"<br>Snapped Coordinates: {row[coord_cols[0]]}, {row[coord_cols[1]]}<br>Batch: {row['batch_index']}<br>Matching: {row['matchings_index']}<br>Confidence: {row['confidence']}"
            
            folium.CircleMarker(
                location=[row[coord_cols[0]], row[coord_cols[1]]],
                radius=circle_radius,
                fill_color=circle_color,
                fill_opacity=0.4,
                color=darker_circle_color, # outline color
                weight=1,
                tooltip=circle_tooltip,
                popup=circle_tooltip
            ).add_to(self.folium_map)


    def snap_leglines(self, snap_legdf, colormap='viridis'):
        # Create column with hex colors
        snap_legdf['color'] = snap_legdf['confidence'].apply(
            lambda x: mcolors.to_hex(plt.get_cmap(colormap)(x)[:3])
        )
        
        # Add LineStrings to the Map
        lineweight = self.segment_lineweights['road_snapped']
        for _, row in snap_legdf.iterrows():
            # Extracting the coordinates for the LineString and reversing them to (lat, lon)
            line_coords = [(y, x) for x, y in row.geometry.coords]

            # Convert hex color to HSL
            hsl_color = colour.Color(row['color'])
            # Increase lightness by 20%
            hsl_color.luminance = min(hsl_color.luminance + 0.2, 1)  # Ensure luminance doesn't go above 1
            lighter_color_hex = hsl_color.hex_l
            
            # Create tooltip and popup content
            tooltip = self.tooltips['road_snapped'] + f"<br>Batch: {row['batch_index']}<br>Confidence: {row['confidence']}<br>Distance: {row['distance']}<br>Duration: {row['duration']}"
            
            # Create a PolyLine with the tooltip and popup
            folium.PolyLine(
                locations=line_coords, 
                color=lighter_color_hex,
                weight=lineweight,
                tooltip=tooltip, 
                popup=tooltip
            ).add_to(self.folium_map)