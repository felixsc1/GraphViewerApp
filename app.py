import streamlit as st
import app_graph
import app_processing
import app_search
import pandas as pd
import os

st.set_page_config(layout="wide")

# Sidebar
st.sidebar.title("Navigation")
selection = st.sidebar.selectbox(
    "Go to", ["Data Processing", "Search RefID", "Graph Viewer"]
)

if 'cwd' not in st.session_state:
    st.session_state['cwd'] = os.getcwd()

# --- Loading all data for the sub-pages   obsolete?---
# @st.cache_data
# def load_data(file_path, csv=False):
#     if csv:
#         df = pd.read_csv(file_path)  # evtl. index_col=[0]
#     else:
#         df = pd.read_excel(file_path)
#     return df


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
