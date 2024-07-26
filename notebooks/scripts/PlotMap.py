import folium
from folium import FeatureGroup
from folium.plugins import MousePosition
from shapely.geometry import LineString
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pandas as pd
from .utils import darken_color, lighten_color
from dataclasses import dataclass

@dataclass
class MapStyle:
    polyline_color: str
    segment_lineweight: float
    segment_color: str
    circle_color: str
    circle_radius: float
    tooltip: str

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

        # Initialize MapStyles for each coord_type
        self.map_styles = {
            "original": MapStyle(
                polyline_color="#006EC7",
                segment_lineweight=15,
                segment_color="#1395FFB3",
                circle_color="#1395FF",
                circle_radius=4.5,
                tooltip="<b>Original GPS data</b>"
            ),
            "kalman": MapStyle(
                polyline_color="#931310",
                segment_lineweight=15,
                segment_color="#E1515BB3",
                circle_color="#C61613",
                circle_radius=4.5,
                tooltip="<b>Kalman filtered GPS data</b>"
            ),
            "road_snapped": MapStyle(
                polyline_color="#FF87D5",
                segment_lineweight=15,
                segment_color="#FF87D5B3",
                circle_color="#f2f2f2",
                circle_radius=4.5,
                tooltip="<b>Road snapped GPS data</b>"
            ),
            "matched": MapStyle(
                polyline_color="#FF87D5",
                segment_lineweight=15,
                segment_color="#FF87D5B3",
                circle_color="#EB96CE",
                circle_radius=4.5,
                tooltip="<b>Map matched GPS data</b>"
            ),
            "network": MapStyle(
                polyline_color="#747474",
                segment_lineweight=5,
                segment_color="#B3B3B3B3",
                circle_color="#C4C4C4",
                circle_radius=3,
                tooltip="<b>OSMNX</b>"
            ),
            "interpolated": MapStyle(
                polyline_color="#5A8E26",
                segment_lineweight=5,
                segment_color="#B3B3B3B3",
                circle_color="#89C250",
                circle_radius=3,
                tooltip="<b>OSMNX</b>"
            )
        }
        # Column names for original, kalman, vs. road snapped data
        self.coord_cols = {
            "original": ['lat', 'long'],
            "kalman": ['kalman_lat', 'kalmanlong'],
            "road_snapped": ['roadsnap_lat', 'roadsnap_long'],
            "matched": ['matched_lat', 'matched_long'],
            "network": ['node_lat', 'node_long'],
            "interpolated": ['interp_lat', 'interp_long']
        }

    def show(self) -> folium.Map:
        """Display the map"""
        MousePosition(position="topright").add_to(self.folium_map)
        self.folium_map.fit_bounds([[self.person_df['lat'].min(), self.person_df['long'].min()], 
                                    [self.person_df['lat'].max(), self.person_df['long'].max()]])
        folium.LayerControl(position='topright', collapsed=False).add_to(self.folium_map)
        return self.folium_map
    
    def polyline(self, gps_df, coord_type="original") -> None:
        """
        Add a thin line connecting all coordinates with the given column names
        to the PlotMap instance
        """
        coord_cols = self.coord_cols[coord_type]
        map_style = self.map_styles[coord_type]
        name = 'Polyline: ' + coord_type
        
        # Drop rows with NaN values in coord_cols
        gps_df = gps_df.dropna(subset=coord_cols)
        
        polyline = folium.PolyLine(
            locations=gps_df[coord_cols], 
            color=map_style.polyline_color,
            weight=3, 
            tooltip=map_style.tooltip,
            name=name
        )
        
        # Add polyline to feature group to allow layer control
        fg = FeatureGroup(name=name)
        polyline.add_to(fg)
        fg.add_to(self.folium_map)

    def circles(self, gps_df, coord_type="original"):
        """Add circles to the map with the given column names"""
        # Get column names and map style for the given coord_type
        coord_cols = self.coord_cols[coord_type]
        map_style = self.map_styles[coord_type]
        name = 'Circles: ' + coord_type
        if coord_type == "network":
            name = 'Network: nodes'
        
        # Make a darker version of the circle color for outline
        darker_circle_color = darken_color(map_style.circle_color, decrease_by=0.2)
        
        # Create feature group to allow layer control
        fg = folium.FeatureGroup(name=name)

        # Create each circle indvidually for custom tooltips
        for i, row in gps_df.iterrows():
            # Tooltip content
            if coord_type == "original" or coord_type == "kalman":
                # Convert date to datetime, then to string (just in case)
                date = pd.to_datetime(row['cst_datetime'])
                date_string = date.strftime('%Y-%m-%d %H:%M:%S') if 'cst_datetime' in row else ''
                circle_tooltip = (
                    f"{map_style.tooltip}<br>"
                    f"Coordinates: {row[coord_cols[0]]}, {row[coord_cols[1]]}<br>"
                    f"Time: {date_string}"
                )
            elif coord_type == "road_snapped":
                circle_tooltip = (
                    f"{map_style.tooltip}<br>"
                    f"Coordinates: {row[coord_cols[0]]}, {row[coord_cols[1]]}<br>"
                    f"Batch: {row['batch_index']}<br>"
                    f"Matching: {row['matchings_index']}<br>"
                    f"Confidence: {row['confidence']}"
                )
            elif coord_type == "matched":
                # Skip rows with NaN values in coord_cols
                if pd.isnull(row[coord_cols]).any():
                    continue
                date = pd.to_datetime(row['cst_datetime'])
                date_string = date.strftime('%Y-%m-%d %H:%M:%S') if 'cst_datetime' in row else ''
                circle_tooltip = (
                    f"{map_style.tooltip}<br>"
                    f"Coordinates: {row[coord_cols[0]]}, {row[coord_cols[1]]}<br>"
                    f"Time: {date_string}<br>"
                    f"matchings_index: {row['matchings_index']}<br>"
                    f"Alternatives: {row['alternatives_count']}<br>"
                    f"Name: {row['trace_name']}"
                )
                if not pd.isnull(row['waypoint_index']):
                    circle_tooltip += f"<br>Waypoint Index: {row['waypoint_index']}"

            elif coord_type == "network" or coord_type == "interpolated":
                circle_tooltip = (
                    f"{map_style.tooltip} <b>Nodes</b><br>"
                    f"Coordinates: {row.get(coord_cols[0], '')}, {row.get(coord_cols[1], '')}<br>"
                    f"osmid: {row.get('osmid', '')}<br>"
                    f"highway: {row.get('highway', '')}<br>"
                    f"street_count: {row.get('street_count', '')}"
                )
            
            folium.CircleMarker(
                location=[row[coord_cols[0]], row[coord_cols[1]]],
                radius=map_style.circle_radius,
                fill_color=map_style.circle_color,
                fill_opacity=0.4,
                color=darker_circle_color, # outline color
                weight=1,
                tooltip=circle_tooltip,
                popup=circle_tooltip,
                name=name
            ).add_to(fg)
        
        fg.add_to(self.folium_map)


    def segment_polyline(self, segment_df, coord_type="original"):
        """
        Add thicker lines connecting all coordinates within the same time segment
        """
        # Get column names and map style for the given coord_type
        coord_cols = self.coord_cols[coord_type]
        map_style = self.map_styles[coord_type]
        name = 'Segment Polyline: ' + coord_type

        for i, df in segment_df.groupby('segment'):
            segment_tooltip = self.tooltips[coord_type] + f"<br>Segment {i}"
            folium.PolyLine(
                locations=df[coord_cols], 
                color=map_style.segment_color,
                weight=map_style.segment_lineweight, 
                tooltip=segment_tooltip,
                name=name
            ).add_to(self.folium_map)

    def edge_polyline(self, edge_df):
        """
        Add thicker lines connecting all coordinates within the same edge
        """
        map_style = self.map_styles['network']
        name = 'Network: edges'

        fg = folium.FeatureGroup(name=name)
        for _, edge in edge_df.iterrows():

            edge_tooltip = (
                    f"{map_style.tooltip} <b>Edges</b><br>"
                    f"(u,v,key): {edge.get('u', '')},{edge.get('v', '')},{edge.get('key', '')}<br>"
                    f"osmid: {edge.get('osmid', '')}<br>"
                    f"highway: {edge.get('highway', '')}<br>"
                    f"oneway: {edge.get('oneway', '')}<br>"
                    f"reversed: {edge.get('reversed', '')}<br>"
                    f"length: {edge.get('length', '')}<br>"
                    f"name: {edge.get('name', '')}<br>"
                    f"lanes: {edge.get('lanes', '')}<br>"
                    f"bridge: {edge.get('bridge', '')}<br>"
                    f"maxspeed: {edge.get('maxspeed', '')}<br>"
                    f"ref: {edge.get('ref', '')}<br>"
                    f"width: {edge.get('width', '')}<br>"
                    f"tunnel: {edge.get('tunnel', '')}<br>"
                    f"service: {edge.get('service', '')}"
                )

            # Extract coords from LINESTRING geometry column
            line = edge['geometry']
            if isinstance(line, LineString):
                line_coords = [(point[1], point[0]) for point in line.coords]
            else:
                continue

            folium.PolyLine(
                locations=line_coords, 
                color=map_style.segment_color,
                weight=map_style.segment_lineweight, 
                tooltip=edge_tooltip,
                name=name
            ).add_to(fg)
        fg.add_to(self.folium_map)

    def snap_leglines(self, snap_legdf, colormap='viridis'):
        """
        Add snapped road legs as LineStrings to the map. For use with OSRM road_snapped data.
        """

        map_style = self.map_styles['road_snapped']

        # Create column with hex colors based on 'confidence'
        snap_legdf['color'] = snap_legdf['confidence'].apply(
            lambda x: mcolors.to_hex(plt.get_cmap(colormap)(x)[:3])
        )
        name='Road Snapped Legs'
        
        # Add LineStrings to the Map
        lineweight = map_style.segment_lineweight['road_snapped']
        for leg_index, row in snap_legdf.iterrows():
            # Extracting the coordinates for the LineString and reversing them to (lat, lon)
            line_coords = [(y, x) for x, y in row.geometry.coords]
            lighter_color_hex = lighten_color(row['color'], increase_by=0.2)
            
            # Create tooltip and popup content
            tooltip = map_style.tooltip['road_snapped'] + f"<br>Batch: {row['batch_index']}<br>Leg: {leg_index}<br>Confidence: {row['confidence']}<br>Distance: {row['distance']}<br>Duration: {row['duration']}"
            
            # Create a PolyLine with the tooltip and popup
            folium.PolyLine(
                locations=line_coords, 
                color=lighter_color_hex,
                weight=lineweight,
                tooltip=tooltip, 
                popup=tooltip,
                name=name
            ).add_to(self.folium_map)