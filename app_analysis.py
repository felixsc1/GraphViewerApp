import streamlit as st
from app_helper_functions import get_data_version, load_data
from app_processing import find_all_data
from app_search import success_temporary
from analysis_helper_functions import find_name_adresse_doubletten, create_excel_files_from_nested_dict, organisationsrollen_filter_and_format_batch, final_touch, final_touch_batch, filter_clusters_with_mixed_produkt_roles, apply_excel_styling_organisationen_nur_master_hat_produkte, general_exclusion_criteria, batch_process_produkte
import os
import shutil
import zipfile


def controls():
    col1, col2 = st.columns(2)
    with col1:
        st.write("Select outputs:")
        st.checkbox("Organisationen_nur_master_hat_produkte", key="organisationen_nur_master_hat_produkte", help="Findet Fälle in denen ein Master alle Produktrollen besitzt, weitere Doubletten haben keine Rollen.")
        # st.checkbox("Personen_nur_master_hat_produkte", key="personen_nur_master_hat_produkte")
        st.checkbox("Organisationen_Produktrollenanalysen", key="organisationen_produktrollenanalysen", help="Analysen für jeden Produkttypen, der unter Optional Settings ausgewählt wurde.")
    with col2.expander("Optional Settings", expanded=False):
        st.write("General filters:")
        st.checkbox("No Geschaeftspartner/Mandanten", key="no_geschaeftspartner", value=True, help="Zeige nur Doubletten, die bei keinem anderen Mandanten vorkommen.")
        st.checkbox("No Servicerole", key="no_servicerole", value=True, help="Zeige nur Doubletten, die keine Servicerolle besitzen.")
        
        # Add multiselect for produktnamen with a key
        produktnamen = [
            '116xyz-Kurznummer',
            '18xy-Kurznummer',
            '1xy-Kurznummer',
            'Carrier Selection Code (CSC)', 
            'E.164-Nummernblock', 
            'E.164-Zugangskennzahl', 
            'Einzelnummer', 
            'International Signalling Point Code (ISPC)', 
            'Issuer Identifier Number (IIN)', 
            'Mobile Network Code (MNC)', 
            'National Signalling Point Code (NSPC)', 
            'Objektbezeichner (OID)', 
            'Weiteres Adressierungselement', 
            'Packet Radio Rufzeichen', 
            'Rufzeichen Amateurfunk', 
            'Rufzeichen Hochseeyacht', 
            'Rufzeichen Luftfahrzeug', 
            'Rufzeichen Rheinschiff', 
            'Rufzeichen SOLAS-Schiff', 
            'Handsprechfunkgeräte mit DSC (Maritime Kennung)', 
            'FDA'
        ]
        
        st.multiselect(
            "Select Produktnamen",
            options=produktnamen,
            default=produktnamen,  # Default to all selected
            key="produktnamen"  # Set a key for session state
        )
        
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
        
    # if st.session_state["personen_nur_master_hat_produkte"]:
    #     file_path = os.path.join(output_directory, "personen_nur_master_hat_produkte.xlsx")
    #     personen_nur_master_hat_produkte = filter_clusters_with_mixed_produkt_roles(organisationen_doubletten, no_Geschaeftspartner=st.session_state["no_geschaeftspartner"], no_Servicerole=st.session_state["no_servicerole"])
        
    if st.session_state["organisationen_produktrollenanalysen"]:
        df_organisationsrollen = df_list["organisationsrollen_all"]

        
        with st.status("Processing...", expanded=True):
            st.write("Finding Doubletten for product types...")
            organisationen_doubletten_filtered = general_exclusion_criteria(organisationen_doubletten, no_Produkte=False, no_Geschaeftspartner=st.session_state["no_geschaeftspartner"], no_Servicerole=st.session_state["no_servicerole"], only_with_Geschaeftspartner=False)
            organisationsrollen_results_3_roles, organisationsrollen_results_2_roles = batch_process_produkte(organisationen_doubletten_filtered, df_organisationsrollen, st.session_state['produktnamen']) 
            
            st.write("Formatting results... (takes several minutes)")
            organisationsrollen_results_formatted_2, s_df1 = organisationsrollen_filter_and_format_batch(organisationsrollen_results_2_roles, roles_per_product=2)
            organisationsrollen_results_formatted_komplette_doublette, s_df2 = organisationsrollen_filter_and_format_batch(organisationsrollen_results_3_roles, rows_per_product=3, roles_per_product=3)
            organisationsrollen_results_formatted_3, s_df3 = organisationsrollen_filter_and_format_batch(organisationsrollen_results_3_roles, rows_per_product=2, roles_per_product=3)
            
            cols_to_keep=["ReferenceID", "Name", "Objekt_link", "address_full", "VerknuepftesObjekt_list", "VerknuepftesObjektID_list", "Geschaeftspartner", "cluster_id", "score_details", "score", "master", "masterID", "Inhaber_Objekt", "Rechempf_Objekt", "Korrempf_Objekt", "Inhaber_ProduktID", "Rechempf_ProduktID", "Korrempf_ProduktID"]
            organisationsrollen_results_formatted_2 = final_touch_batch(organisationsrollen_results_formatted_2, cols_to_keep, two_roles=True)
            organisationsrollen_results_formatted_3 = final_touch_batch(organisationsrollen_results_formatted_3, cols_to_keep, alphanumeric=True)
            organisationsrollen_results_formatted_komplette_doublette = final_touch_batch(organisationsrollen_results_formatted_komplette_doublette, cols_to_keep, alphanumeric=True)
            
            st.write("Storing results in separate excel files...")
            create_excel_files_from_nested_dict(organisationsrollen_results_formatted_2, output_dir=os.path.join(output_directory, "2_organisationsrollen")) 
            create_excel_files_from_nested_dict(organisationsrollen_results_formatted_3, output_dir=os.path.join(output_directory, "3_organisationsrollen"))
            create_excel_files_from_nested_dict(organisationsrollen_results_formatted_komplette_doublette, output_dir=os.path.join(output_directory, "organisationsrollen_komplette_doublette"))           
        
            st.write("✔️ All Done! Please download zip file below.")
            # Create a zip file containing all files in the output directory
        zip_file_path = os.path.join(output_directory, "analysis_results.zip")
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(output_directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Skip the zip file itself
                    if file_path != zip_file_path:
                        zipf.write(file_path, os.path.relpath(file_path, output_directory))

        # Delete the original files and subfolders
        for root, dirs, files in os.walk(output_directory, topdown=False):
            for file in files:
                file_path = os.path.join(root, file)
                if file_path != zip_file_path:  # Ensure the zip file is not deleted
                    os.remove(file_path)
            for dir in dirs:
                os.rmdir(os.path.join(root, dir))                
                      
        
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
            if os.path.isfile(file_path):  # Check if it's a file
                with open(file_path, "rb") as f:
                    st.download_button(
                        label=f"Download {file}",
                        data=f,
                        file_name=file
                    )

