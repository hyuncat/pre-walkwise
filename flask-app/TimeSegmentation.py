import pandas as pd
from KalmanFilter import kalman_filter

def time_segmentation(gps_df: pd.DataFrame, time_cutoff: int = 60):
    """
    Splits a dataframe of time-ordered GPS traces into a list of separate dataframes 
    based on the time difference between consecutive rows.
    @param:
        data: pd.DataFrame with 'cst_datetime' column
        time_cutoff: int representing the maximum time difference in seconds before splitting
    @return:
        List of pd.DataFrames
    """
    gps_df = gps_df.copy() # To avoid modifying the original DataFrame
    gps_df['cst_datetime'] = pd.to_datetime(gps_df['cst_datetime'])
    gps_df = gps_df.sort_values(by='cst_datetime').reset_index(drop=True)

    # Calculate the time difference between consecutive GPS readings
    time_differences = gps_df['cst_datetime'].diff()

    # Convert time differences to total seconds
    time_differences_in_seconds = time_differences.dt.total_seconds()
    gps_df['time_diff'] = time_differences_in_seconds

    # Identify indices of rows where the time difference between it and the preceeding row
    # exceeds [time_cutoff] seconds
    rows_exceeding_cutoff = gps_df['time_diff'] > time_cutoff
    split_indices = gps_df[rows_exceeding_cutoff].index.tolist()

    # Ensures gps_df doesn't truncate the beginning and end
    split_indices = [0] + split_indices + [len(gps_df)-1]
    print("Split indices:", split_indices)  # Debugging

    # Use split_indices as the start and end indices to slice gps_df into segments
    gps_df_segments = []
    for i in range(len(split_indices)-1):
        segment_df = gps_df.iloc[split_indices[i]:split_indices[i+1]]
        gps_df_segments.append(segment_df)
        print(f"Segment {i}: {len(segment_df)} rows")  # Debugging

    return gps_df_segments

def kalman_with_segment(segment_df_list):
    """
    Accepts a list of DataFrames
    """
    segments = []
    for i, df in enumerate(segment_df_list):
        df = df.copy()  # Ensure that we are working with a copy
        kalman_df = kalman_filter(df)
        kalman_df['segment'] = i  # Assign segment number
        segments.append(kalman_df)
        print(f"Segment {i} assigned with {len(kalman_df)} rows.")  # Debugging: Print number of rows in each segment
        print(kalman_df.head())  # Debugging: Print the head of the DataFrame

    kalman_segment = pd.concat(segments, ignore_index=True)
    print(f"Unique segments in combined DataFrame: {kalman_segment['segment'].unique()}")  # Should show an array of unique segment numbers
    return kalman_segment