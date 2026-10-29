import streamlit as st
import app_graph
from app_helper_functions import get_data_version
import app_processing
import app_search
import app_analysis
import app_workflows
import app_pathviewer
import pandas as pd
import os
import logging
import warnings

# Suppress Streamlit warnings
logging.getLogger("streamlit").setLevel(
    logging.CRITICAL
)  # prevent spam during multiprocessing functions
# Suppress specific Streamlit warnings
warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")

# Suppress Streamlit warnings
logging.getLogger("streamlit.runtime.scriptrunner_utils").setLevel(logging.CRITICAL)
logging.getLogger("streamlit.runtime.caching.cache_data_api").setLevel(logging.CRITICAL)

st.set_page_config(page_title="GraphViewer App", page_icon="📊", layout="wide")

# Sidebar
# st.sidebar.title("Navigation")
# selection = st.sidebar.selectbox(
#     "Go to", ["Data Processing", "Search RefID", "Graph Viewer"]
# )

if "selection" not in st.session_state:
    st.session_state["selection"] = "Search RefID"

# Use buttons instead of radio for navigation with icons
st.sidebar.title("Navigation")

# Streamlit centers labels in a full-width flex wrapper inside the button.
# Left-align that wrapper so sidebar page buttons read as a menu.
st.sidebar.markdown(
    """
<style>
    section[data-testid="stSidebar"] [data-testid="stButton"] button {
        text-align: left;
        justify-content: flex-start;
    }
    section[data-testid="stSidebar"] [data-testid="stButton"] button > div {
        justify-content: flex-start;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Dictionary mapping selections to their titles with icons
page_options = {
    "Data Processing": "🗄️ Data Processing",
    "Search RefID": "🔍 Search ReferenceIDs",
    "Graph Viewer": "📊 Graph Viewer",
    "Analysis": "👨‍💻 Analysis",
    "Prozess Viewer": "🔀 Prozess Viewer",
    "Path Viewer": "🏞 Path Viewer",
}

# Create a button for each page
for page_key, page_title in page_options.items():
    if st.sidebar.button(page_title, use_container_width=True):
        st.session_state["selection"] = page_key

selection = st.session_state["selection"]

if "cwd" not in st.session_state:
    # Get the directory where the current file (app.py) is located
    app_dir = os.path.dirname(os.path.abspath(__file__))
    st.session_state["cwd"] = app_dir
if "file_versions" not in st.session_state or not st.session_state["file_versions"]:
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

elif selection == "Prozess Viewer":
    st.title("🔀 Prozess Viewer")
    app_workflows.show()

elif selection == "Path Viewer":
    st.title("🏞 Path Viewer")
    app_pathviewer.show()
