import streamlit as st
from app_helper_functions import get_data_version, load_data
from app_processing import find_all_data
from app_search import success_temporary
from analysis_helper_functions import find_name_adresse_doubletten, final_touch, filter_clusters_with_mixed_produkt_roles, apply_excel_styling_organisationen_nur_master_hat_produkte
import os
import shutil

def controls():
    col1, col2 = st.columns(2)
    with col1:
        st.write("Select outputs:")
        st.checkbox("Organisationen_nur_master_hat_produkte", key="organisationen_nur_master_hat_produkte")
    with col2:
        st.write("General filters:")
        st.checkbox("No Geschaeftspartner", key="no_geschaeftspartner", value=True)
        st.checkbox("No Servicerole", key="no_servicerole", value=True)
        
def analyze(df_list):
    df_organisationen = df_list["organisationen"]
    output_directory = os.path.join(st.session_state['cwd'], "output/")
    if os.path.exists(output_directory):
        shutil.rmtree(output_directory)
    os.makedirs(output_directory)
    organisationen_doubletten = find_name_adresse_doubletten(df_organisationen, organisationen=True, only_with_Geschaeftspartner=False)
    
    if st.session_state["organisationen_nur_master_hat_produkte"]:
        file_path = os.path.join(output_directory, "organisationen_nur_master_hat_produkte.xlsx")
        organisationen_nur_master_hat_produkte = filter_clusters_with_mixed_produkt_roles(organisationen_doubletten, no_Geschaeftspartner=st.session_state["no_geschaeftspartner"], no_Servicerole=st.session_state["no_servicerole"])
        cols_to_keep=["ReferenceID", "Name_Zeile2", "Objekt_link", "address_full", "VerknuepftesObjekt_list", "VerknuepftesObjektID_list", "Produkt_Inhaber", "Produkt_Adressant", "AnzahlGeschaeftsobjekte", "Geschaeftspartner", "Servicerole_string", "cluster_id", "score_details", "score", "master", "masterID"]
        organisationen_nur_master_hat_produkte = final_touch(organisationen_nur_master_hat_produkte, cols_to_keep)
        organisationen_nur_master_hat_produkte.to_excel(file_path, index=False)
        apply_excel_styling_organisationen_nur_master_hat_produkte(file_path)
        

def show():
    cluster_dfs, data_dfs = load_data()
    if cluster_dfs:
        success_temporary("Data loaded")

    if "file_versions" not in st.session_state:
        find_all_data()
        _, _, _ = get_data_version()
    with st.expander(
        f"oldest file: {st.session_state['file_versions']['earliest_date']}, newest file: {st.session_state['file_versions']['latest_date']}"
    ):
        st.write(st.session_state["file_versions"]["ordered_filenames"])
    controls()
    if st.button("🚀 Run",type="primary"):
        analyze(data_dfs)
    st.divider()
    # Display and allow download of files in the output directory
    output_directory = os.path.join(st.session_state['cwd'], "output/")
    if os.path.exists(output_directory):
        files = os.listdir(output_directory)
        for file in files:
            file_path = os.path.join(output_directory, file)
            with open(file_path, "rb") as f:
                st.download_button(
                    label=f"Download {file}",
                    data=f,
                    file_name=file
                )

