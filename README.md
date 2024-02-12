# Graph Viewer App

## Installation

### For Servers (offline installation)
1. Install Python 3.11.7
2. Download venv.zip in this repo by clicking on the Download Raw button. This only works for windows and contains some hardcoded paths, therefore:
   - Create the folder C:\GitRepos\GraphViewerApp and unzip venv.zip into /venv there.
   - Open /venv/pyenv.cfg and change the path to the python executable to the one on the server
3. Download this reposirory as a zip file and unzip it into C:\GitRepot\GraphViewerApp
4. Open an administrator PowerShell of the folder and run the following commands:
   - `.\venv\Scripts\Activate.ps1` to activate the local python environment.
   - `streamlit run app.py --server.port 80` (or any other port you want to use)
- Keep the PowerShell open

To install an updated version of the app, repeat steps 3 and 4.


### For local machine
- Clone this repo.
- Optionally, create and activate a virtual python environment (any python >=3.9).
- Install the requirements `pip install -r requirements.txt`
- Launch the app with `streamlit run app.py`

A browser window should pop up, or visit `http://localhost:8501/`




## Usage

Allows uploading the raw output of Expertensuche queries (.xlsx files) to viszualize and explore relationships in the database.

The app is split into 3 parts, accessible from the left menu bar:

1. Data Processing: 
   Files can be dragged&dropped in the upload field. Click the "Check Data" button to show which files are still missing.
   Click then "Run Processing" button to run basic data cleanup and combine all queries into a network representation of edges and nodes. Result is stored for future use.
2. Search RefID
3. Graph Viewer
   
 [to be continued...]

