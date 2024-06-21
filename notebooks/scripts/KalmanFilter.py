import pandas as pd
import numpy as np
from pykalman import KalmanFilter

#TODO:
# maybe average building height as a parameter
# rolling average of building height, address lookup for each gps point, 
# adding building height of nearest building to rolling average

def kalman_filter(gps_data: pd.DataFrame):
    """ 
    Apply Kalman Filter to 'lat' and 'long' columns of the input df
    @param: 
        - gps_data: pd.DataFrame with 'lat' and 'long' columns
    @return: 
        - The gps_data with 2 additional columns: 'lat_filtered' and 'long_filtered'
    """
    
    gps_data = gps_data.copy()

    # Initialize Kalman Filter with initial lat/long (why?), with 2 dimensions
    initial_state_mean = [gps_data['lat'].iloc[0], 
                          gps_data['long'].iloc[0]]
    transition_matrix = [[1, 0], 
                         [0, 1]]
    observation_matrix = [[1, 0], 
                          [0, 1]]
    kf1 = KalmanFilter(transition_matrices=transition_matrix,
                      observation_matrices=observation_matrix,
                      initial_state_mean=initial_state_mean, 
                      n_dim_obs=2)

    # Use the 'lat' and 'long' columns as the observed values
    measurements = np.asarray(gps_data[['lat', 'long']])

    
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
    gps_data.loc[:, 'lat_filtered'] = smoothed_state_means2[:, 0]
    gps_data.loc[:, 'long_filtered'] = smoothed_state_means2[:, 1]

    return gps_data
