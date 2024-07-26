import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import colour

# This file contains utility functions for preparing GPS data 
# for kalman filtering and visualization

def filter_person_and_date(data: pd.DataFrame, person: int, date: str):
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


def create_geodataframe(gps_df, lat_col: str, long_col: str):
    """
    Converts DataFrame to GeoDataFrame with specified latitude and longitude columns
    @param:
        - df: pd.DataFrame containing GPS coordinates and times in a 'cst_datetime' column
        - lat_col: name of column to create latitude coordinates
        - long_col: name of column to create longitude coordinates
    @return:
        - gdf: gpd.GeoDataFrame
    """
    gps_gdf = gpd.GeoDataFrame(
        gps_df, 
        geometry=[Point(xy) for xy in zip(gps_df[long_col], gps_df[lat_col])]
    )
    gps_gdf.crs = {'init': 'epsg:4326'}  # Define coordinate reference system
    gps_gdf['cst_datetime'] = gps_gdf['cst_datetime'].astype(str)
    gps_gdf['date'] = pd.to_datetime(gps_gdf['date']).dt.date.astype(str)
    gps_gdf['time'] = gps_gdf['time'].astype(str)

    return gps_gdf


def darken_color(hex_color, decrease_by=0.2):
    """
    Return a darker version of the given hex color.
    @param:
        - hex_color: str in the format '#RRGGBB'
        - decrease_by: float between 0 and 1
    """
    assert 0 <= decrease_by <= 1, "decrease_by must be between 0 and 1"
    hsl_color = colour.Color(hex_color)  # Convert hex color to HSL
    # Decrease luminance by [decrease_by], ensuring it doesn't go below 0
    hsl_color.luminance = max(0, hsl_color.luminance - decrease_by)  
    return hsl_color.hex_l

def lighten_color(hex_color, increase_by=0.2):
    """
    Return a lighter version of the given hex color.
    @param:
        - hex_color: str in the format '#RRGGBB'
        - increase_by: float between 0 and 1
    """
    assert 0 <= increase_by <= 1, "increase_by must be between 0 and 1"
    hsl_color = colour.Color(hex_color)  # Convert hex color to HSL
    # Increase luminance by [increase_by], ensuring it doesn't go above 1
    hsl_color.luminance = min(1, hsl_color.luminance + increase_by) 
    return hsl_color.hex_l