import streamlit as st
import pandas as pd
from app_helper_functions import get_data_version, load_data
from app_processing import find_all_data
from app_search import success_temporary
from graphviz_helper_functions import GraphvizWrapper_organisationen
import os
from organisationen_helper_functions import find_singular_cluster
import re
import html
import warnings
import urllib.parse


# Supress pandas warnings
warnings.filterwarnings("ignore")


def controls():
    st.text_input("ReferenceID", key="ReferenceID")
    col1, col2, _ = st.columns(3)
    with col1:
        st.radio(
            "Select the type of edges",
            ["Normal", "Advanced"],
            key="edge_type",
            captions=[
                "Only database links",
                "Inferred links (same Name/Address/Email)",
            ],
        )
    with col2:
        st.select_slider("Depth of graph", options=[1, 2, 3, 4, 5, "all"], key="depth")


def convert_special_string(row):
    # Modify the row for special cases where the 'source' or 'target' is a string that needs to be converted
    # Assuming for now, this is only necessary for Produkte/Organisationsrollen.
    # The list part is now always the ReferenceID of nodes.
    modified = False
    for col in ["source", "target"]:
        val = row[col]
        actual_list, _, _, _ = process_produkte_strings(val)
        if actual_list:
            row[col] = str(actual_list)
            modified = True

    if modified:
        row["bidirectional"] = False
        row["special_formatting"] = "Produkt"
    return row


def sanitize_string(s):
    """ Fixes a rare bug where a name somehow contains HTML tags.
    Remove HTML tags and escape special characters."""
    s = str(s)
    # Remove HTML tags
    s = re.sub('<[^<]+?>', '', s)
    # Escape special characters
    s = html.escape(s)
    return s

def process_produkte_strings(input_string):
    """
    The "source" entries in the cluster df, contain values that look like this:
    "['0848 848188', '0848 848288']Einzelnummer\n2"  a list part with the individual Produkt objects,,
    The type of the products, a newline and the number of products.
    Turn each of them into a separate variable here.
    Now it can also handle an additional list at the end.
    """
    # Ensure there are no breaking errors, if the string is not a Produkt name, just return False
    if "\n" not in input_string:
        return False, False, False, False
    
    # Define the maximum length threshold
    MAX_LENGTH = 16384

    # Check if the input string exceeds the maximum length
    if len(input_string) > MAX_LENGTH:
        st.error("Warning: Too many products to display.")
        return False, False, False, False

    # Extract the first list part using a more robust regex
    first_list_match = re.match(r'\[(.*?)\](?=\w)', input_string, re.DOTALL)
    if not first_list_match:
        return False, False, False, False
    
    first_list_part_raw = first_list_match.group(1)
    first_list_part = re.findall(r"'([^']*)'", first_list_part_raw)
    
    # Extract the remaining parts
    remaining_part = input_string[first_list_match.end():].strip()
    name, number_part = remaining_part.split("\n", 1)

    # Check if there is an additional list at the end
    if "[" in number_part:
        start_of_second_list_index = number_part.find("[")
        number = int(number_part[:start_of_second_list_index].strip())
        second_list_part_raw = number_part[start_of_second_list_index + 1:-1]
        second_list_part = [item.strip("'") for item in second_list_part_raw.split(", ")]
    else:
        number = int(number_part.strip())
        second_list_part = []
        
    # print("input string:", input_string)
    # print("first list part:", first_list_part)
    # print("name:", name)
    # print("number:", number)
    # print("second list part:", second_list_part)

    return first_list_part, name, number, second_list_part



def de_americanize_columns(df):
    """
    By default dates are shown like this: 2002-10-27 10:50:00, we want them like this: 27.10.2002 10:50:00
    Also long integers are shown like "5,624,434", we want to remove commas.
    """
    df["CreatedAt"] = df["CreatedAt"].dt.strftime("%d.%m.%Y %H:%M:%S")
    df["score"] = df["score"].astype(str)
    df["UID_CHID"] = df["UID_CHID"].astype(str)
    return df


def show_subset_of_columns(df):
    df = de_americanize_columns(df)
    columns_to_keep = [
        "ReferenceID",
        "Name_original",
        "UID_CHID",
        "address_full",
        "Versandart",
        "AnzahlGeschaeftsobjekte",
        "CreatedAt",
        "Servicerole_string",
        "Geschaeftspartner",
        "Verknuepfungsart",
        "VerknuepftesObjekt",
        "VerknuepftesObjektID",
        "score",
    ]
    df_subset = df[columns_to_keep]
    df_subset = df_subset.rename(
        columns={"Name_original": "Name", "Servicerole_string": "Servicerole"}
    )
    return df_subset

def create_produkte_table(df):
    if df is None:
        return None
    
    # Convert string representations of lists to actual lists
    df['Objekt'] = df['Objekt'].apply(eval)
    df['Produkt_RefID'] = df['Produkt_RefID'].apply(eval)
    
    # Create a list to store the expanded rows
    expanded_rows = []
    
    for _, row in df.iterrows():
        for obj, ref_id in zip(row['Objekt'], row['Produkt_RefID']):
            new_row = row.copy()
            new_row['Objekt'] = obj
            new_row['Produkt_RefID'] = ref_id.strip()
            expanded_rows.append(new_row)
    
    # Create a new DataFrame from the list of expanded rows
    expanded_df = pd.DataFrame(expanded_rows, columns=df.columns)
    
    # Add example links to the 'Objekt' column
    expanded_df['Produkt_RefID'] = expanded_df['Produkt_RefID'].apply(
        lambda x: f"https://www.egov-uvek.gever.admin.ch/web/?ObjectToOpenID=%24SpecialdataHostingBaseDataObject%7C{urllib.parse.quote(str(x))}&TenantID=208"
    )

    # Display the DataFrame with links in Streamlit if it is not empty
    if not expanded_df.empty:
        st.subheader("🛒 Produkte:")
        st.data_editor(
            expanded_df,
            column_config={"Produkt_RefID": st.column_config.LinkColumn(display_text=r'https://www\.egov-uvek\.gever\.admin\.ch/web/\?ObjectToOpenID=%24SpecialdataHostingBaseDataObject%7C(.*)&TenantID=208')},
            hide_index=True
        )
    
    return expanded_df


def create_serviceroles_table(df):
    if df is None:
        return None
    
    # Convert comma-separated strings to actual lists
    df['Servicerole'] = df['Servicerole'].apply(lambda x: x.split(',') if isinstance(x, str) else x)
    df['Servicerole_RefID'] = df['Servicerole_RefID'].apply(lambda x: x.split(',') if isinstance(x, str) else x)
    
    # Create a list to store the expanded rows
    expanded_rows = []
    
    for _, row in df.iterrows():
        for obj, ref_id in zip(row['Servicerole'], row['Servicerole_RefID']):
            new_row = row.copy()
            new_row['Servicerole'] = obj
            new_row['Servicerole_RefID'] = ref_id.strip()
            expanded_rows.append(new_row)
    
    # Create a new DataFrame from the list of expanded rows
    expanded_df = pd.DataFrame(expanded_rows, columns=df.columns)
    
    expanded_df['Servicerole_RefID'] = expanded_df['Servicerole_RefID'].apply(
        lambda x: f"https://www.egov-uvek.gever.admin.ch/web/?ObjectToOpenID=%24SpecialdataHostingBaseDataObject%7C{urllib.parse.quote(str(x))}&TenantID=208"
    )
    
    # Display the DataFrame with links in Streamlit if it is not empty
    if not expanded_df.empty:
        st.subheader("📺 Serviceroles:")
        st.data_editor(
            expanded_df,
            column_config={"Servicerole_RefID": st.column_config.LinkColumn(display_text=r'https://www\.egov-uvek\.gever\.admin\.ch/web/\?ObjectToOpenID=%24SpecialdataHostingBaseDataObject%7C(.*)&TenantID=208')},
            hide_index=True
        )
            
    return expanded_df
    

def generate_graph(cluster_dfs, data_dfs, filter_refid):
    df_clusters = cluster_dfs["clusters"]

    df_edges = cluster_dfs["edges"]
    df_personen = data_dfs["personen"]
    df_organisationen = data_dfs["organisationen"]

    if filter_refid != "":
        cluster_selected, df_edges = find_singular_cluster(
            df_edges,
            filter_refid,
            mode=st.session_state["edge_type"],
            depth=st.session_state["depth"],
        )

        if cluster_selected.empty:
            # Look for the filter_refid in df_personen and df_organisationen, even if its not in df_edges in case there is no edge from it
            person = df_personen[df_personen["ReferenceID"] == filter_refid]
            organisation = df_organisationen[df_organisationen["ReferenceID"] == filter_refid]
            
            if not person.empty:
                node_data = person
            elif not organisation.empty:
                node_data = organisation
            else:
                st.error(
                    "ReferenceID not found in any dataset.",
                    icon="🚨",
                )
                return None, None, None, None, None
            
            # Create a simple graph with just this node
            graph = GraphvizWrapper_organisationen()
            graph.add_nodes(node_data)
            return graph, person, organisation, None, None

        node_list = cluster_selected.iloc[0]["nodes"]

        # Extract the cluster and corresponding links for filter_refid
        cluster_row = df_clusters[
            df_clusters["nodes"].apply(lambda x: filter_refid in x)
        ].iloc[0]
        node_list_full = cluster_row["nodes"]
        link_list_full = cluster_row["link"]

        link_list = []
        for node in node_list:
            index = node_list_full.index(node)
            link_list.append(link_list_full[index])

        # Create a dictionary mapping ReferenceID to Objekt_link
        link_mapping = dict(zip(node_list, link_list))

        # Display Dataframes of Personen & Organisationen of that cluster
        organisationen_of_cluster = df_organisationen[
            df_organisationen["ReferenceID"].isin(node_list)
        ]
        personen_of_cluster = df_personen[df_personen["ReferenceID"].isin(node_list)]

        # Generate nodes of that cluster (reminder: graphviz wrapper function expects dataframe with Name, RefID)
        node_data = pd.concat(
            [organisationen_of_cluster, personen_of_cluster], axis=0, sort=False
        )
        
        # Convert all relevant columns to string
        string_columns = ['ReferenceID', 'Name_original', 'Name']
        for col in string_columns:
            if col in node_data.columns:
                node_data[col] = node_data[col].astype(str)

        if len(node_data) > 50:
            st.warning(
                "The cluster has more than 50 nodes. Please change the filter settings.",
                icon="⚠️",
            )
            return None, None, None, None, None
        
        
        # Initialize edge data here, to have connections to produkte available below
        edge_data = df_edges[
            (df_edges["source"].isin(node_list)) & (df_edges["target"].isin(node_list))
        ]
        edge_data['source'] = edge_data['source'].astype(str)
        edge_data['target'] = edge_data['target'].astype(str)
        edge_data = edge_data.apply(
            convert_special_string, axis=1
        )  # Modify Produkte entries
        

        # Add new rows for special entries in cluster_nodes that are not organizations
        # Here the code to add Produkte, which based on cleanup steps appear in the form of: "[1000299836, 1000300252, 2]", i.e. the produkt ids and the number of products.
        produkte_of_cluster = pd.DataFrame(columns=["Parents", "Produkt_Typ", "Objekt", "Produkt_RefID"])
        for node in node_list:
            # print("node:", node)
            actual_list, name, number, produkt_id_list = process_produkte_strings(str(node))
            # print("list:", actual_list)
            # print("list:", produkt_id_list)
            if actual_list:
                new_row = pd.DataFrame(
                    {
                        "ReferenceID": [str(actual_list)],
                        "Name_original": [str(name) + "\n" + str(number)],
                    }
                )
                node_data = pd.concat([node_data, new_row], ignore_index=True)
                
                # Retrieve the ReferenceIDs from the edge data
                connected_nodes = edge_data[edge_data["source"] == str(actual_list)]["target"].tolist()
                # Take only the last three characters of each connected node
                connected_nodes = [node[-3:] for node in connected_nodes]
                if len(connected_nodes) > 0:
                    # Add to produkte_of_cluster DataFrame
                    produkt_row = pd.DataFrame(
                        {
                            "Parents": [connected_nodes],
                            "Objekt": [str(actual_list)],
                            "Produkt_Typ": [str(name)],
                            "Produkt_RefID": [str(produkt_id_list)],
                        }
                    )
                    produkte_of_cluster = pd.concat([produkte_of_cluster, produkt_row], ignore_index=True)

                

        # Add 'link' information to node_data
        node_data["link"] = node_data["ReferenceID"].map(link_mapping)
        # print(node_data)
        
        # Add servicerole nodes and edges
        servicerole_nodes = []
        servicerole_edges = []
        serviceroles_of_cluster = pd.DataFrame(columns=["Parent", "Servicerole", "Servicerole_RefID"])

        for df in [organisationen_of_cluster, personen_of_cluster]:
            for _, row in df.iterrows():
                if row['Servicerole_string'] and not pd.isna(row['Servicerole_string']):
                    servicerole_nodes.append({
                        'ReferenceID': row['ServiceroleID_string'],
                        'Name_original': row['Servicerole_string'],
                        'Typ': 'Servicerole'
                    })
                    servicerole_edges.append({
                        'source': row['ReferenceID'],
                        'target': row['ServiceroleID_string'],
                        'match_type': 'Servicerolle',
                        'bidirectional': False
                    })
                    servicerole_row = pd.DataFrame(
                        {
                            "Parent": [row['ReferenceID']],
                            "Servicerole": [row['Servicerole_string']],
                            "Servicerole_RefID": [row['ServiceroleID_string']]
                        }
                    )
                    serviceroles_of_cluster = pd.concat([serviceroles_of_cluster, servicerole_row], ignore_index=True)
                    
        # Add servicerole nodes to node_data
        node_data = pd.concat([node_data, pd.DataFrame(servicerole_nodes)], ignore_index=True)
        
        
        # Add servicerole edges to edge_data
        edge_data = pd.concat([edge_data, pd.DataFrame(servicerole_edges)], ignore_index=True)

        
        edge_data = edge_data.drop_duplicates(subset=["source", "target", "match_type"])

        # st.write(edge_data) # Debugging
        # st.write(node_data)
        
        # Just before generating the graph, sanitize the node names
        if 'Name_original' in node_data.columns:
            node_data['Name_original'] = node_data['Name_original'].apply(sanitize_string)
        if 'Name' in node_data.columns:
            node_data['Name'] = node_data['Name'].apply(sanitize_string)

        # Generate Graph
        graph = GraphvizWrapper_organisationen()
        graph.add_nodes(node_data)
        graph.add_edges(edge_data)

        return graph, personen_of_cluster, organisationen_of_cluster, produkte_of_cluster, serviceroles_of_cluster

    return None, None, None, None, None


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
    st.divider()
    filter_refid = st.session_state.get("ReferenceID", "").replace(
        '"', ""
    )  # this session state is automatically created by st.text_input

    if cluster_dfs and data_dfs:

        col1, _ = st.columns([1, 1])
        with col1.expander("Advanced Graph Settings", expanded=False):

            st.selectbox(
                "Select Graph Engine:",
                key="graph_engine",
                options=["dot", "neato", "circo", "fdp", "twopi"],
                index=0,  # Default to 'dot'
            )

            splines_options = {
                "Straight lines": "false",
                "Curved lines": "true",
                "Orthogonal lines": "ortho",
                "Polyline": "polyline",
                "Curved and Straight": "curved",
            }

            selected_option = st.selectbox(
                "Edge shape:",
                key="edge_shape",
                options=list(splines_options.keys()),
                index=1,
            )

            st.selectbox(
                "Vertical Spacing:",
                key="vertical_spacing",
                options=["0", "1", "2", "3"],
                index=0,
            )

        technical_value = splines_options[selected_option]
        st.session_state["edge_shape2"] = technical_value
        g = False
        try:
            g, personen_of_cluster, organisationen_of_cluster, produkte_of_cluster, serviceroles_of_cluster = generate_graph(
                cluster_dfs, data_dfs, filter_refid
            )
            svg_path, svg_str = g.render()
        except Exception as e:
            st.error(
                "Cannot display graph. Please check the settings.",
                icon="🚨",
            )
            with st.expander("Show detailed error message"):
                import traceback
                st.code(traceback.format_exc())

        if g:
            st.divider()
            st.write(g.graph)
            # st.image(svg_path)
            # st.components.v1.html(svg_str, height=500)

            # This feature requires installation on Graphviz for windows.
            try:
                with open(svg_path, "rb") as file:
                    btn = st.download_button(
                        label="Download Graph as SVG",
                        data=file,
                        file_name=svg_path,
                        mime="image/svg+xml",
                    )
            except Exception as e:
                st.warning(f"Could not create download button. Error: {str(e)}")

            st.subheader("👨‍💼 Personen:")
            st.dataframe(show_subset_of_columns(personen_of_cluster), hide_index=True)
            st.subheader("🏭 Organisationen:")
            st.dataframe(
                show_subset_of_columns(organisationen_of_cluster), hide_index=True
            )
            # Function below places the Produkte/Servicrole Subheaders and tables.
            produkte_of_cluster = create_produkte_table(produkte_of_cluster)
            serviceroles_of_cluster = create_serviceroles_table(serviceroles_of_cluster)
        