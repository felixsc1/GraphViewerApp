# Graph Viewer App

## Installation

- Clone this repo.
- Optionally, create and activate a virtual python environment (any python >=3.9).
- Install the requirements `pip install -r requirements.txt`
- Launch the app with `streamlit run app.py`

A browser window should pop up, or visit `http://localhost:8501/`


#### Deployment 
To use it on a server, the port 8501 needs to be forwarded.

Since the app is still under development, it would be best to create a script that checks this git repo once per day and re-runs the installation.

## Usage

Allows uploading the raw output of Expertensuche queries (.xlsx files) to viszualize and explore relationships in the database.

The app is split into 3 parts, accessible from the left menu bar:

1. Data Processing: 
   Files can be dragged&dropped in the upload field. Click the "Check Data" button to show which files are still missing.
   Click then "Run Processing" button to run basic data cleanup and combine all queries into a network representation of edges and nodes. Result is stored for future use.
2. Search RefID
3. Graph Viewer
   
 [to be continued...]

