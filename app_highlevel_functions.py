from app_helper_functions import (
    calculate_scores_organisationen,
    calculate_scores_personen,
    get_geschaeftspartner,
)
from cleanup_helper_functions import (
    aggregate_identical_UIDs,
    basic_cleanup,
    construct_address_string,
    get_true_lists_generic,
)
from organisationen_helper_functions import (
    add_personen_produkte_columns,
    add_produkte_columns,
    add_servicerole_column,
    add_servicerole_column_string,
    cleanup_edges_df,
    find_clusters_all,
    generate_edge_list_from_orginationsrollen_aggregate,
    match_organizations_between_dataframes,
    match_organizations_internally_simplified,
    organisationsrollen_group_aggregate,
)
import pandas as pd
import streamlit as st
import pickle
import os

@st.cache_data
def load_data(file):
    data = pd.read_excel(file)
    return data


def raw_cleanup(toggle_gmaps=False):
    file_paths = st.session_state.get("file_paths", {})

    # Combine all files and basic processing personen & organisationen
    df_organisationen = load_data(file_paths["organisationen"])
    df_personen = load_data(file_paths["personen"])

    df_organisationen = basic_cleanup(df_organisationen, organisation=True)
    df_personen = basic_cleanup(df_personen)

    df_organisationen = aggregate_identical_UIDs(df_organisationen)
    df_personen = aggregate_identical_UIDs(df_personen)

    df_organisationen[["address_full", "address_partial"]] = df_organisationen.apply(
        lambda row: construct_address_string(row, organisation=True), axis=1
    )
    df_personen[["address_full", "address_partial"]] = df_personen.apply(
        lambda row: construct_address_string(row, organisation=False), axis=1
    )
    
    df_organisationen["Name_Zeile2"] = df_organisationen.apply(
                lambda x: x["Name"] + "|" + str(x["Zeile2"])
                if pd.notna(x["Zeile2"]) and x["Zeile2"] != ""
                else x["Name"],
                axis=1,
            )

    # SERVICEROLES. TODO: check if the dicts for the names in this function are still up to date.
    personenservicerolle_df = load_data(file_paths["personenservicerolle"])
    organisationservicerolle_df = load_data(file_paths["organisationservicerolle"])
    df_personen = add_servicerole_column_string(df_personen, personenservicerolle_df)
    df_organisationen = add_servicerole_column_string(
        df_organisationen, organisationservicerolle_df
    )
    df_organisationen = add_servicerole_column(
        df_organisationen, organisationservicerolle_df
    )  # only for score

    # PRODUKTE / ROLLEN
    organisationsrollen_df_1 = load_data(file_paths["organisationsrollen"])
    organisationsrollenFDA_df = load_data(file_paths["organisationsrollenFDA"])
    organisationsrollen_df = pd.concat(
        [organisationsrollen_df_1, organisationsrollenFDA_df], ignore_index=True
    )
    df_organisationen = add_produkte_columns(
        df_organisationen, organisationsrollen_df
    )  # only needed for score.

    df_personenrollen = load_data(file_paths["personenrollen"])
    df_personen = add_personen_produkte_columns(
        df_personen, df_personenrollen
    )  # Technikperson, Statistikperson, etc.

    # GESCHÄFTSPARTNER
    df_organisationen = get_geschaeftspartner(
        df_organisationen, "data/mandanten/organisationen"
    )
    df_personen = get_geschaeftspartner(df_personen, "data/mandanten/personen")

    # Processing list column, to have both string and true list representation.
    columns_to_convert = ["VerknuepftesObjektID", "VerknuepftesObjekt", "Verknuepfungsart", "Geschaeftspartner"]
    for col in columns_to_convert:
        df_organisationen[col] = df_organisationen[col].apply(str)
        df_personen[col] = df_personen[col].apply(str)
    df_organisationen = get_true_lists_generic(df_organisationen)
    df_personen = get_true_lists_generic(df_personen)

    # Now we have information to calculate scores
    df_organisationen = calculate_scores_organisationen(df_organisationen)
    df_personen = calculate_scores_personen(df_personen)
    
    # Store dataframes as pickle
    dfs = {'personen': df_personen, 'organisationen': df_organisationen}
    
    # Create the directory if it doesn't exist
    directory = "data/calculated"
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, "personen_organisationen_dfs_processed.pickle"), 'wb') as file:
        pickle.dump(dfs, file)
        
    st.success("Processing finished!", icon="✅")

    return df_organisationen, df_personen


def create_edges_and_clusters():
    file_paths = st.session_state.get("file_paths", {})

    # Assuming pickle file was created by raw_cleanup()
    with open(
        "data/calculated/personen_organisationen_dfs_processed.pickle", "rb"
    ) as file:
        dfs = pickle.load(file)
    df_personen = dfs["personen"]
    df_organisationen = dfs["organisationen"]

    edges_organisationen = match_organizations_internally_simplified(df_organisationen)

    organisationsrollen_df = load_data(file_paths["organisationsrollen"])
    edges_organisationsrollen = organisationsrollen_group_aggregate(
        organisationsrollen_df
    )
    edges_organisationsrollen = generate_edge_list_from_orginationsrollen_aggregate(
        edges_organisationsrollen
    )

    edges_personen = match_organizations_internally_simplified(
        df_personen, personen=True
    )

    edges_personen_to_organisationen = match_organizations_between_dataframes(df_personen, df_organisationen)

    #TODO: Personenrollen-edges hinzufügen.

    # Summarize and clean up everything.
    edge_list = []
    edge_list.append(edges_organisationen)
    edge_list.append(edges_personen)
    edge_list.append(edges_organisationsrollen)
    edge_list.append(edges_personen_to_organisationen)
    all_edges = pd.concat(edge_list, ignore_index=True)

    all_edges = cleanup_edges_df(all_edges)

    special_nodes = set(edges_organisationsrollen['source'].unique()) # should not count towards cluster sizes or be central nodes.


    all_clusters = find_clusters_all(all_edges, special_nodes, skip_singular_clusters=False)

    # Store dataframes as pickle
    dfs = {'edges': all_edges, 'clusters': all_clusters}   
    # Create the directory if it doesn't exist
    directory = "data/calculated"
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, "edges_clusters_dfs.pickle"), 'wb') as file:
        pickle.dump(dfs, file)

    st.success("Cluster data stored!", icon="✅")
    return