import pandas as pd
from .KalmanFilter import kalman_filter

class Segment:
    def __init__(self):
        pass

    @staticmethod
    def segment_df(gps_df: pd.DataFrame, time_cutoff: int = 60):
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

        # Sort the DataFrame by ascending 'cst_datetime'
        gps_df['cst_datetime'] = pd.to_datetime(gps_df['cst_datetime']) # convert if not already
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
            one_segment_df = gps_df.iloc[split_indices[i]:split_indices[i+1]].copy()
            one_segment_df.loc[:, 'segment'] = i  # Assign segment number
            gps_df_segments.append(one_segment_df)
            # print(f"Segment {i}: {len(one_segment_df)} rows")  # Debugging
        
        segment_df = pd.concat(gps_df_segments, ignore_index=True)
        # Reorder columns to make 'segment' the first column
        cols = ['segment'] + [col for col in segment_df.columns if col != 'segment']
        segment_df = segment_df[cols]

        return segment_df
    
    # @staticmethod
    # def combine_segments(gps_df_segments):
    #     """
    #     Accepts a list of segmented dataframes, creates a new column 'segment' corresponding to its
    #     index in the list and concatenates them into a single dataframe.
    #     """
    #     segments = []
    #     for i, df in enumerate(gps_df_segments):
    #         df['segment'] = i
    #         segments.append(df)
    #     all_segments_df = pd.concat(segments, ignore_index=True)
    #     return all_segments_df

    @staticmethod
    def kalman_filter_segments(segment_df):
        """
        Kalman filters each unique segment in segment_df
        """
        kalman_segments = []
        for i, df in segment_df.groupby('segment'):
            df = df.copy()  # Ensure that we are working with a copy
            kalman_segment = kalman_filter(df)
            kalman_segments.append(kalman_segment)
        
        ksegment_df = pd.concat(kalman_segments, ignore_index=True)
        return ksegment_df

    # @staticmethod
    # def kfilter_segments(segment_df_list):
    #     """
    #     Accepts a list of DataFrames
    #     """
    #     segments = []
    #     for i, df in enumerate(segment_df_list):
    #         df = df.copy()  # Ensure that we are working with a copy
    #         kalman_df = kalman_filter(df)
    #         kalman_df['segment'] = i  # Assign segment number
    #         segments.append(kalman_df)
    #         print(f"Segment {i} assigned with {len(kalman_df)} rows.")  # Debugging: Print number of rows in each segment
    #         print(kalman_df.head())  # Debugging: Print the head of the DataFrame

    #     all_segments_df = pd.concat(segments, ignore_index=True)
    #     print(f"Unique segments in combined DataFrame: {all_segments_df['segment'].unique()}")  # Should show an array of unique segment numbers
    #     return all_segments_df