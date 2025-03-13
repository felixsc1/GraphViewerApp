import streamlit as st
import app_graph
from app_helper_functions import get_data_version
import app_processing
import app_search
import app_analysis
import app_workflows
import pandas as pd
import os
import logging
import warnings

# Suppress Streamlit warnings
logging.getLogger('streamlit').setLevel(logging.CRITICAL) # prevent spam during multiprocessing functions
# Suppress specific Streamlit warnings
warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")

# Suppress Streamlit warnings
logging.getLogger('streamlit.runtime.scriptrunner_utils').setLevel(logging.CRITICAL)
logging.getLogger('streamlit.runtime.caching.cache_data_api').setLevel(logging.CRITICAL)

st.set_page_config(page_title="GraphViewer App", page_icon="📊", layout="wide")

# Sidebar
# st.sidebar.title("Navigation")
# selection = st.sidebar.selectbox(
#     "Go to", ["Data Processing", "Search RefID", "Graph Viewer"]
# )

st.sidebar.title("Navigation")
if 'selection' not in st.session_state:
    st.session_state['selection'] = "Search RefID"

# Use the session state to determine the current selection
selection = st.sidebar.radio(
    "Go to", ["Data Processing", "Search RefID", "Graph Viewer", "Analysis", "Prozess-Workflows"],
    index=["Data Processing", "Search RefID", "Graph Viewer", "Analysis", "Prozess-Workflows"].index(st.session_state['selection'])
)

# Update session state based on sidebar selection
st.session_state['selection'] = selection


if 'cwd' not in st.session_state:
    st.session_state['cwd'] = os.getcwd()
if 'file_versions' not in st.session_state or not st.session_state['file_versions']:
    _, _, _ = get_data_version()

# --- used in sub-pages---
@st.cache_data
def load_data(file_path, csv=False):
    if csv:
        df = pd.read_csv(file_path)  # evtl. index_col=[0]
    else:
        df = pd.read_excel(file_path)
    return df


# Main Content
if selection == "Data Processing":
    st.title("🗄️ Data Processing")
    app_processing.show()

elif selection == "Graph Viewer":
    # st.title("Organisationen")
    app_graph.show()
    
elif selection == "Search RefID":
    st.title("🔍 Search ReferenceIDs")
    app_search.show()

elif selection == "Analysis":
    st.title("👨‍💻 Analysis")
    app_analysis.show()

elif selection == "Prozess-Workflows":
    st.title("📥Prozess-Workflows")
    app_workflows.show()
