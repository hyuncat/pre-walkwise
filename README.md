# GPS-kalman
Scripts and web app to implement and visualize Kalman filtering for GPS time-series data.

## Installation notes

Install package dependencies:
```shell
pip install -r requirements.txt
```

### Notebook scripts

Current jupyter notebook scripts are found in `/notebooks` and include code for the following:

1. Kalman filtering GPS data
2. Map visualizations
3. Time segmentation
4. Road snapping

All code can be tested with data from `/notebooks/data`, though if you want to run it with all the training data you should download a file `all_plt_data` from the project Google Drive.

### Explore the data in the flask app

You can visualize the data (either full or demo) in a simple flask app to explore any given person's movement on all available dates they had walked. You can test this locally by running:

```shell
cd flask-app
python app.py
```

The app looks something like this:

<img width="500" alt="Screenshot 2024-06-14 at 3 06 02 AM" src="https://github.com/hyuncat/GPS-kalman/assets/114366569/8aa7d173-43dd-4b44-898a-88061643d895">
