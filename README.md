# Graph Viewer App

Allows uploading the raw output of Expertensuche queries (.xlsx files) to viszualize and explore relationships in the database.

The app is split into 3 parts, accessible from the left menu bar:

1. Data Processing: 
   Files can be dragged&dropped in the upload field. Click the "Check Data" button to show which files are still missing.
   Click then "Run Processing" button to run basic data cleanup and combine all queries into a network representation of edges and nodes. Result is stored for future use.
2. Search RefID
3. Graph Viewer



## Developer Notes

Good [Link](https://medium.com/@Brice_KENGNI_ZANGUIM/guide-to-convert-a-streamlit-application-into-an-executable-using-nativefier-windows-linux-mac-1d4dc5376a38) about how to turn streamlit app into Windows executable.

To compile a new standalone desktop app: `nativefier --name graphviewer https://graphviewerapp-nqnayqshznfmbsz7zacwfq.streamlit.app/ --platform 'windows'`