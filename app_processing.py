import streamlit as st
from processing_helper_functions import detect_raw_files
from app_highlevel_functions import create_edges_and_clusters, raw_cleanup
from app_helper_functions import upload_files, clear_data_directory

def initialize_state():
    if "file_paths" not in st.session_state:
        st.session_state["file_paths"] = {}
    if 'clear_data' not in st.session_state:
        st.session_state['clear_data'] = False 

    
def find_all_data():
    # To ensure files are there before proceeding.
    raw_files, error_message = detect_raw_files()
    # keys are: "organisationen" "organisationsrollen" "organisationsrollenFDA" "organisationservicerolle" "personen" "personenservicerolle" "personenrollen"
    if error_message:
        st.error(error_message)
        return

    st.session_state["file_paths"] = raw_files
    st.success("All data found!", icon="✅")


# --------------------Main App Structure--------------------------
def show():
    initialize_state()
    
    upload_files()
    
    if st.button("Clear Data Directory"):
        clear_data_directory()

    if st.button("Check Data"):
        find_all_data()
    
    # Reset the flag after the Clear button is clicked
    if st.session_state['clear_data']:
        st.session_state['clear_data'] = False

    if st.button("Run Basic cleanup"):
        raw_cleanup()

    if st.button("Create Edges and Clusters"):
        create_edges_and_clusters()

