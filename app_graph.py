import streamlit as st
import pickle
import pandas as pd
from graphviz_helper_functions import GraphvizWrapper_organisationen
import os

@st.cache_data
def load_data():
    try:
        with open(os.path.join(st.session_state["cwd"], "data/calculated/edges_clusters_dfs.pickle"), "rb") as file:
            cluster_dfs = pickle.load(file)

        with open(
            os.path.join(st.session_state["cwd"], "data/calculated/personen_organisationen_dfs_processed.pickle"), "rb"
        ) as file:
            data_dfs = pickle.load(file)
            st.success("Data loaded", icon="✅")
            
            # Store it in session state for later use
            st.session_state["file_versions"] = {}
            st.session_state["file_versions"]["earliest_date"] = data_dfs["file_versions"]["earliest_date"]
            st.session_state["file_versions"]["latest_date"] = data_dfs["file_versions"]["latest_date"]
            st.session_state["file_versions"]["ordered_filenames"] = data_dfs["file_versions"]["ordered_filenames"]      
                    
        return cluster_dfs, data_dfs
    except FileNotFoundError:
        print("No data found. Please upload and process data.")
        return None, None


def controls():
    st.text_input("ReferenceID", key="ReferenceID")


def convert_special_string(row):
    # Modify the row for special cases where the 'source' or 'target' is a string that needs to be converted
    # Assuming for now, this is only necessary for Produkte/Organisationsrollen.
    # The list part is now always the ReferenceID of nodes.
    modified = False
    for col in ["source", "target"]:
        val = row[col]
        actual_list, name, number = process_produkte_strings(val)
        if actual_list:
            row[col] = str(actual_list)
            modified = True

    if modified:
        row["bidirectional"] = False
        row["special_formatting"] = "Produkt"
    return row


def process_produkte_strings(input_string):
    """
    The "source" entries in the cluster df, contain values that look like this:
    "['0848 848188', '0848 848288']Einzelnummer\n2"  a list part with the individual Produkt objects,,
    The type of the products, a newline and the number of products.
    Turn each of them into a separate variable here
    """
    # Ensure there are no breaking errors, if the string is not a Produkt name, just return False
    if "\n" not in input_string:
        return False, False, False

    # Find the ending of the list part (ignoring "[]" at the beginning and "]" at the end)
    end_of_list_index = input_string.find("]")

    # Extract the list part and convert it into a list
    # Strip the "['" at the beginning and "']" at the end, then split by "', '"
    list_part_raw = input_string[2:end_of_list_index]
    list_part = [item.strip("'") for item in list_part_raw.split("', '")]
    # print("actual list:", list_part)

    # Extract the remaining part after the list
    remaining_part = input_string[end_of_list_index + 1 :]

    # Split the remaining part into name and number based on the newline character
    name, number_part = remaining_part.split("\n")

    # Extract the number from the number_part
    number = int(number_part.strip())

    return list_part, name, number


def show_subset_of_columns(df):
    columns_to_keep = [
        "ReferenceID",
        "Name",
        "UID_CHID",
        "address_full",
        "Versandart",
        "AnzahlGeschaeftsobjekte",
        "CreatedAt",
        "Servicerole",
        "Geschaeftspartner",
        "Verknuepfungsart",
        "VerknuepftesObjekt",
        "VerknuepftesObjektID",
        "score",
    ]
    return df[columns_to_keep]


def generate_graph(cluster_dfs, data_dfs, filter_refid):
    df_clusters = cluster_dfs["clusters"]
    df_edges = cluster_dfs["edges"]
    df_personen = data_dfs["personen"]
    df_organisationen = data_dfs["organisationen"]

    if filter_refid != "":
        # lets get all nodes that are part of filter_refid's cluster
        node_list = df_clusters.loc[
            df_clusters["nodes"].apply(lambda x: filter_refid in x), "nodes"
        ].iloc[0]

        # Display Dataframes of Personen & Organisationen of that cluster
        organisationen_of_cluster = df_organisationen[
            df_organisationen["ReferenceID"].isin(node_list)
        ]
        personen_of_cluster = df_personen[df_personen["ReferenceID"].isin(node_list)]
        st.write("Personen:")
        st.dataframe(show_subset_of_columns(personen_of_cluster))
        st.write("Organisationen:")
        st.write(show_subset_of_columns(organisationen_of_cluster))

        # Generate nodes of that cluster (reminder: graphviz wrapper function expects dataframe with Name, RefID)
        node_data = pd.concat(
            [organisationen_of_cluster, personen_of_cluster], axis=0, sort=False
        )

        # Add new rows for special entries in cluster_nodes that are not organizations
        # Here the code to add Produkte, which based on cleanup steps appear in the form of: "[1000299836, 1000300252, 2]", i.e. the produkt ids and the number of products.
        for node in node_list:
            # print(node)
            actual_list, name, number = process_produkte_strings(str(node))
            # print("list:", actual_list)
            if actual_list:
                new_row = pd.DataFrame(
                    {
                        "ReferenceID": [str(actual_list)],
                        "Name": [str(name) + "\n" + str(number)],
                    }
                )
                node_data = pd.concat([node_data, new_row], ignore_index=True)

        edge_data = df_edges[
            (df_edges["source"].isin(node_list)) & (df_edges["target"].isin(node_list))
        ]
        edge_data = edge_data.apply(
            convert_special_string, axis=1
        )  # Modify Produkte entries
        edge_data = edge_data.drop_duplicates(subset=["source", "target", "match_type"])

        # Generate Graph
        graph = GraphvizWrapper_organisationen()
        graph.add_nodes(node_data)
        graph.add_edges(edge_data)

        return graph


def show():
    cluster_dfs, data_dfs = load_data()
    
    with st.expander(f"oldest file: {st.session_state['file_versions']['earliest_date']}, newest file: {st.session_state['file_versions']['latest_date']}"):
            st.write(st.session_state["file_versions"]["ordered_filenames"])

    controls()
    filter_refid = st.session_state.get(
        "ReferenceID", ""
    ).replace('"', '')  # this session state is automatically created by st.text_input

    if cluster_dfs and data_dfs:
        g = generate_graph(cluster_dfs, data_dfs, filter_refid)
        if g:
            st.write(g.graph)
