import pandas as pd
import numpy as np
from pykalman import KalmanFilter

#TODO:
# maybe average building height as a parameter
# rolling average of building height, address lookup for each gps point, 
#  adding building height of nearest building to rolling average
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

def time_segmentation(data: pd.DataFrame, time_cutoff: int = 60):
    """
    If two gps traces are deteced over [time cutoff] apart then split data at that 
    point into separate dataframes
    @param:
        data: pd.DataFrame with 'time' column
        time_cutoff: int representing the time difference in seconds
    @return:
        List of pd.DataFrames
    """
    data_copy = data.copy()
    data_copy['cst_datetime'] = pd.to_datetime(data_copy['cst_datetime'])
    data_copy = data_copy.sort_values(by='cst_datetime').reset_index(drop=True)

    data_copy['time_diff'] = data_copy['cst_datetime'].diff().dt.total_seconds()
    split_indices = data_copy[data_copy['time_diff'] > time_cutoff].index.tolist()

    # Ensure the last index is within bounds
    split_indices = [0] + split_indices + [len(data_copy)-1]

    print("Split indices:", split_indices)  # Debugging

    split_dfs = []
    for i in range(len(split_indices)-1):
        segment_df = data_copy.iloc[split_indices[i]:split_indices[i+1]]
        split_dfs.append(segment_df)
        print(f"Segment {i}: {len(segment_df)} rows")  # Debugging

    return split_dfs

def kalman_with_segment(segment_df_list):
    """
    Accepts a list of DataFrames
    """
    segments = []
    for i, df in enumerate(segment_df_list):
        df = df.copy()  # Ensure that we are working with a copy
        kalman_df = kalman_filtering(df)
        kalman_df['segment'] = i  # Assign segment number
        segments.append(kalman_df)
        print(f"Segment {i} assigned with {len(kalman_df)} rows.")  # Debugging: Print number of rows in each segment
        print(kalman_df.head())  # Debugging: Print the head of the DataFrame

    kalman_segment = pd.concat(segments, ignore_index=True)
    print(f"Unique segments in combined DataFrame: {kalman_segment['segment'].unique()}")  # Should show an array of unique segment numbers
    return kalman_segment


def kalman_filtering(data):
    """ 
    Apply Kalman Filter to 'lat' and 'long' columns of the input df
    @param: 
        data: pd.DataFrame with 'lat' and 'long' columns
    @return: 
        df with 2 additional columns: 'lat_filtered' and 'long_filtered'
    """
    
    data_copy = data.copy()

    # Initialize Kalman Filter with initial lat/long (why?), with 2 dimensions
    initial_state_mean = [data_copy['lat'].iloc[0], 
                          data_copy['long'].iloc[0]]
    transition_matrix = [[1, 0], 
                         [0, 1]]
    observation_matrix = [[1, 0], 
                          [0, 1]]
    kf1 = KalmanFilter(transition_matrices=transition_matrix,
                      observation_matrices=observation_matrix,
                      initial_state_mean=initial_state_mean, 
                      n_dim_obs=2)

    # Use the 'lat' and 'long' columns as the observed values
    measurements = np.asarray(data_copy[['lat', 'long']])

    
    kf1 = kf1.em(measurements) # Use expectation-maximization to estimate the initial parameters
    (smoothed_state_means, smoothed_state_covariances) = kf1.smooth(measurements) # Apply Kalman smoothing

    kf2 = KalmanFilter(n_dim_obs=2, n_dim_state=2,
                      initial_state_mean=initial_state_mean,
                      initial_state_covariance = kf1.initial_state_covariance,
                      transition_matrices=transition_matrix,
                      observation_matrices=observation_matrix,
                      observation_covariance = kf1.observation_covariance,
                      transition_covariance = kf1.transition_covariance)
    
    kf2 = kf2.em(measurements)

    # Estimate the hidden states using all observations.  These estimates
    # will be 'smoother' (and are to be preferred) to those produced by
    # simply filtering as they are made with later observations in mind.
    # Probabilistically, this method produces the mean and covariance
    # characterizing,
    #    P(x_t | z_{1:n_timesteps})
    (smoothed_state_means2, smoothed_state_covariances2) = kf2.smooth(measurements)

    # Add the filtered latitude and longitude to the DataFrame
    data_copy.loc[:, 'lat_filtered'] = smoothed_state_means2[:, 0]
    data_copy.loc[:, 'long_filtered'] = smoothed_state_means2[:, 1]

    return data_copy