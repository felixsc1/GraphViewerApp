import re
import graphviz
import pandas as pd
import math
import ast
from cleanup_helper_functions import (
    get_flat_list,
    get_additional_organizations,
    find_internal_matches,
    get_stammdaten_info,
    obtain_uvek_matches,
)
from graphviz import Digraph
import subprocess, os


def xml_escape(s):
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


class GraphWrapper:
    """
    Creates a graph object that remembers details about nodes and edges.
    Explanation about the statistics: has_unconnected_person: if a person has no connections to a organisation
    independent_clusters: whether there are person nodes that have no edges between them (not considering geschaeftsobjekte)
    """

    def __init__(self, graph):
        self.graph = graph
        self.statistics = {
            "has_organisations": False,
            "has_master": 0,
            "has_unconnected_person": False,
            "has_active": 0,
        }
        # Need to keep track of person nodes for unconnected statistic
        self.added_person_nodes = set()
        self.connected_nodes = set()
        # Adjacency list (this is for the "independent_clusters" statistic)
        self.adjacency_list = {}

        self.node_data = {}  # For managing cells added to nodes

        self.clusters = {}  # This will store the node_ids for each cluster

    def add_edge(self, source, target, label, bidirectional, **attrs):
        # Preserve previous logic where certain labels have specific colors and directions
        if label not in [
            "Sonstiges",
            "Mitarbeiter",
            "Administrator",
            "Geschaeftsobjekte",
            "Zuständiger Fernmeldedienstanbieter",
        ]:
            attrs = dict(attrs, color="#9c9c9c", fontcolor="#9c9c9c")
        if bidirectional:
            attrs["dir"] = "both"
        else:
            attrs["dir"] = "forward"  # or whichever default direction you prefer

        self.graph.edge(source, target, label=label, **attrs)
        self.connected_nodes.add(source)
        self.connected_nodes.add(target)

        # self.adjacency_list.setdefault(source, set()).add(target)
        # self.adjacency_list.setdefault(target, set()).add(source)  # Add this line to ensure the adjacency list is symmetrical
        # we dont want to use Geschaeftsobjekte when checking for independent clusters
        if label != "Geschaeftsobjekte":
            self.adjacency_list.setdefault(source, {})[target] = label
            if bidirectional:
                self.adjacency_list.setdefault(target, {})[source] = label

    def dfs(self, start, visited):
        # DFS = Depth-first search algorithm. Traverses the graph given a starting point.
        if start not in visited:
            visited.add(start)
            for neighbor in self.adjacency_list.get(start, {}):
                # Directly use neighbors as keys since they are now stored as dictionary keys
                self.dfs(neighbor, visited)
        return visited

    def compute_clusters(self, filter_node_type=None):
        all_person_nodes = self.added_person_nodes
        visited_total = set()
        clusters = []
        cluster_id = 1  # To uniquely identify each cluster

        for person_node in all_person_nodes:
            if person_node not in visited_total:
                reachable_nodes = self.dfs(person_node, set())
                visited_total.update(reachable_nodes)

                # Filter the nodes if filter_node_type is specified
                if filter_node_type:
                    reachable_nodes = {
                        node
                        for node in reachable_nodes
                        if self.get_node_type(node) == filter_node_type
                    }

                # Create a new cluster with the reachable nodes
                clusters.append(reachable_nodes)

                # Store the cluster information in self.clusters
                self.clusters[f"Cluster {cluster_id}"] = reachable_nodes
                cluster_id += 1

        # Check for independent clusters
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                if clusters[i].intersection(clusters[j]):
                    # Merge clusters
                    clusters[i].update(clusters[j])
                    clusters[j] = set()

        # Remove empty clusters and update self.clusters
        clusters = [c for c in clusters if c]
        self.clusters = {f"Cluster {i+1}": c for i, c in enumerate(clusters)}

        # Update statistics
        self.statistics["independent_clusters"] = len(clusters) > 1
        return len(clusters) > 1

        # Check for independent clusters
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                if not clusters[i].intersection(clusters[j]):
                    self.statistics["independent_clusters"] = True
                    return True

        self.statistics["independent_clusters"] = False
        return False

    def add_edges(self, source_list, label_list, target_list, bidirectional_list):
        # Check if the provided lists have the same length:
        assert (
            len(source_list)
            == len(label_list)
            == len(target_list)
            == len(bidirectional_list)
        )

        for source, label, target, bidirectional in zip(
            source_list, label_list, target_list, bidirectional_list
        ):
            # Check if source and target are identical or if any of them are nan.
            if source == target or any(
                x is pd.NA or (isinstance(x, float) and math.isnan(x))
                for x in [source, label, target]
            ):
                continue

            # Add the edge
            try:
                self.add_edge(source, target, label, bidirectional)
            except:
                print("Problem with: ", source, target, label, bidirectional)

    def add_node(self, df, node_type="person", uvek_match=False, sub_cluster_name=None):
        # Set shape and subgraph attributes based on node type
        if node_type == "person":
            shape = "ellipse"
            cluster_name = "cluster_people"
            cluster_label = ""
            cluster_color = "lightyellow"
            # manage nodes for statistics:
            ids = df["ReferenceID"].tolist()
            self.added_person_nodes.update(ids)
        elif node_type == "person_additional":
            shape = "ellipse"
            cluster_name = "cluster_additional_people"
            cluster_label = ""
            cluster_color = "#F9C326"
        elif node_type == "organisation":
            if not df.empty:
                self.statistics["has_organisations"] = True  # Update statistics dict
            shape = "box"
            cluster_name = "cluster_organisations"
            cluster_label = ""
            cluster_color = "lightblue"
        else:
            shape = "box"
            cluster_name = "cluster_zeiger"
            cluster_label = ""
            cluster_color = "lightpink"

        # Check if Objekt_link exists in the dataframe
        has_links = "Objekt_link" in df.columns

        # Create the subgraph or retrieve the existing one
        with self.graph.subgraph(name=cluster_name) as c:
            c.attr(label=cluster_label, color=cluster_color, style="filled")

            if sub_cluster_name:
                with c.subgraph(name=f"cluster_{sub_cluster_name}") as sc:
                    sc.attr(label=sub_cluster_name, color="white", style="filled")
                    self.add_nodes_to_subgraph(
                        sc, node_type, df, uvek_match, shape, has_links
                    )
            else:
                self.add_nodes_to_subgraph(
                    c, node_type, df, uvek_match, shape, has_links
                )

    def add_nodes_to_subgraph(
        self, subgraph, node_type, df, uvek_match, shape, has_links
    ):
        """
        Since add_node() has the optional parameter sub_cluster_name=None,
        this function will add nodes either to a sub-cluster or if none provided to a main cluster.
        """
        if uvek_match:
            ids = df["ReferenceID"].tolist()
            names = df["Organisationsname"].tolist()
            node_attrs = {"shape": shape, "color": "red"}
            for node_id, node_name in zip(ids, names):
                node_label = node_name + " (UVEK) \n" + node_id
                subgraph.node(node_id, node_label, **node_attrs)
            return

        if node_type == "zeiger":
            ids = [str(value) for value in df["AnzahlGeschaeftsobjekte"] if value > 0]
            node_labels = ids
            node_attrs = {"shape": shape}
            for node_id, node_label in zip(ids, node_labels):
                subgraph.node(node_id, node_label, **node_attrs)
        else:
            names = df["Name"].tolist()
            ids = df["ReferenceID"].tolist()
            links = df["Objekt_link"].tolist() if has_links else [None] * len(names)
            versandart = df["Versandart"].tolist()
            chid = df["UID_CHID"].tolist()
            aktiv = df["Aktiv"].tolist()
            typ = df["Typ"].tolist()

            for node_id, node_name, link, versand, chid, aktiv, typ in zip(
                ids, names, links, versandart, chid, aktiv, typ
            ):
                p = (
                    " ✅"
                    if (versand == "Portal") and (chid is not pd.NA) and (aktiv)
                    else ""
                )
                if p and typ == "Person":
                    self.statistics["has_master"] += 1
                if aktiv and typ == "Person":
                    self.statistics["has_active"] += 1
                node_label = node_name + "\n" + node_id[-3:] + p
                node_attrs = {"shape": shape}
                if link:
                    node_attrs["URL"] = xml_escape(link)

                subgraph.node(node_id, node_label, **node_attrs)

                # Add or update the label in the node_data dictionary (so that "append_cells_to_node" can see it and not overwrite i t)
                if node_id not in self.node_data:
                    self.node_data[node_id] = {
                        "label": node_label,
                        "cells": [],
                        "type": node_type,
                    }
                else:
                    self.node_data[node_id]["label"] = node_label
                    self.node_data[node_id]["type"] = node_type

    def get_node_type(self, node_id):
        return self.node_data.get(node_id, {}).get("type", None)

    def update_statistics(self):
        # Check for unconnected person nodes
        unconnected_person_nodes = self.added_person_nodes - self.connected_nodes
        if unconnected_person_nodes:
            self.statistics["has_unconnected_person"] = True
        # Update statistics with info about independent clusters
        # if self.compute_clusters(filter_node_type="person"):
        if self.compute_clusters():
            self.statistics["independent_clusters"] = True
        else:
            self.statistics["independent_clusters"] = False
        # print(self.adjacency_list)
        # print(self.clusters)

    def append_cells_to_node(self, node_id, cells):
        # If node doesn't exist in node_data, initialize it
        if node_id not in self.node_data:
            self.node_data[node_id] = {"label": node_id, "cells": []}

        # Update cells data
        self.node_data[node_id]["cells"].extend(cells)

        # Convert special characters to HTML-like entities
        # This list may have to be extended, if Stammdaten dont show correctly.
        formatted_label = self.node_data[node_id]["label"].replace("\n", "<BR/>")
        formatted_label = (
            self.node_data[node_id]["label"]
            .replace("&", "&amp;")
            .replace("\n", "<BR/>")
        )

        # Generate label from node_data
        label_content = f"<TD BORDER='0'>{formatted_label}</TD>"
        for label, color in self.node_data[node_id]["cells"]:
            label_content += (
                f'<TD BGCOLOR="{color}" WIDTH="20" HEIGHT="20">{label}</TD>'
            )

        node_label = f"""<
        <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">
        <TR>
            {label_content}
        </TR>
        </TABLE>
        >"""

        self.graph.node(node_id, label=node_label)


def render_with_links_opening_in_new_tab(graph, filename="output/output", view=False):
    # First, let's render the SVG using the graphviz package
    svg_filename = graph.graph.render(filename=filename, format="svg", cleanup=True)

    # Now, let's read this SVG and modify the links
    with open(svg_filename, "r") as f:
        svg_content = f.read()

    # Use regex to add target="_blank" to URLs
    modified_svg_content = re.sub(
        r'<a xlink:href="([^"]+)"', r'<a xlink:href="\1" target="_blank"', svg_content
    )

    # Overwrite the SVG with the modified content
    with open(svg_filename, "w") as f:
        f.write(modified_svg_content)

    # If view is True, open the SVG file with the default viewer
    if view:
        graphviz.backend.view(svg_filename)

    return svg_filename


def render_as_pdf(graph, filename="output/output", view=False):
    # First, let's render the PDF using the graphviz package
    pdf_filename = graph.render(filename=filename, format="pdf", cleanup=True)

    # Now, let's read this PDF and modify the links (Note: PDF modification is more complex)
    # You might need to use a PDF manipulation library to modify links in the PDF content

    # If view is True, open the PDF file with the default viewer
    if view:
        graphviz.backend.view(pdf_filename)

    return pdf_filename


def convert_string_to_list(s):
    if s == "[nan]":
        return [float("nan")]
    else:
        try:
            return ast.literal_eval(s)
        except ValueError:
            # Handle or log other unexpected values, if any
            return s


def clean_and_merge_lists(sources, targets, labels):
    """
    Cleans up edges before drawing.
    Input: Lists that may contain duplicates.
    Determines if there are edges going in both directions, if so, create a single bidirectional edge.
    Some edges like Telefon, Email, Adresse are always bidirectional and are merged into one edge with the combined string as label.
    """
    inversed_duplicates_labels = {"Telefon", "Email", "Adresse"}
    edge_dict = {}
    bidirectional_dict = {}
    label_dict = {}
    final_sources = []
    final_targets = []
    final_labels = []
    bidirectional = []

    for s, t, l in zip(sources, targets, labels):
        if s == t or not isinstance(l, str):
            continue
        key = (s, t)
        reverse_key = (t, s)

        if reverse_key in edge_dict and edge_dict[reverse_key] == l:
            bidirectional_dict[reverse_key] = True
            bidirectional_dict[key] = True
            if key not in edge_dict:
                edge_dict[key] = l
                label_dict[key] = l
        else:
            if l in inversed_duplicates_labels:
                combined_key = tuple(sorted([s, t])) + ("combined",)
                if combined_key not in edge_dict:
                    edge_dict[combined_key] = l
                    label_dict[combined_key] = l
                    bidirectional_dict[combined_key] = True
                else:
                    if l not in label_dict[combined_key].split(", "):
                        label_dict[combined_key] = label_dict[combined_key] + ", " + l
            else:
                if key not in edge_dict:
                    edge_dict[key] = l
                    label_dict[key] = l
                    bidirectional_dict[key] = l in inversed_duplicates_labels

    seen_edges = set()
    for key, label in edge_dict.items():
        s, t = key[:2]
        edge_tuple = (s, t, label_dict[key])
        reverse_edge_tuple = (t, s, label_dict[key])
        if edge_tuple not in seen_edges and reverse_edge_tuple not in seen_edges:
            final_sources.append(s)
            final_targets.append(t)
            final_labels.append(label_dict[key])
            bidirectional.append(bidirectional_dict[key])
            seen_edges.add(edge_tuple)

    return final_sources, final_targets, final_labels, bidirectional


def construct_personen_organisationen_graph(
    df_personen,
    df_organisationen,
    df_stammdaten,
    df_uvek_matches,
    name,
    additional_edges=False,
    additional_personen=False,
    stammdaten_toggle=False,
    address_toggle=False,
):
    g = graphviz.Digraph(format="svg", engine="dot")
    g = GraphWrapper(g)

    # Combine all edge data into single lists
    all_sources = []
    all_targets = []
    all_labels = []

    df_unique_name = df_personen[df_personen["unified_name"] == name]

    df_unique_name["VerknuepftesObjektID"] = df_unique_name[
        "VerknuepftesObjektID"
    ].apply(convert_string_to_list)
    df_unique_name["Verknuepfungsart"] = df_unique_name["Verknuepfungsart"].apply(
        convert_string_to_list
    )
    # explode currently causes lot of duplicate edges.. maybe improve this code here
    df_exploded = (
        df_unique_name.explode(column="VerknuepftesObjektID")
        .explode(column="Verknuepfungsart")
        .reset_index(drop=True)
    )
    person_id_list = df_exploded["ReferenceID"].tolist()
    verknuepfung_list = df_exploded["VerknuepftesObjektID"].tolist()
    verknuepfungsart_list = df_exploded["Verknuepfungsart"].tolist()

    # person_id_list = df_unique_name['ReferenceID'].tolist()
    # verknuepfung_list = df_unique_name['VerknuepftesObjektID'].tolist()
    # verknuepfung_list = get_flat_list(verknuepfung_list)
    # verknuepfungsart_list = get_flat_list(df_unique_name['Verknuepfungsart'].tolist()) # to label edges
    # unique_keys = list(set(verknuepfung_list))

    # Filter df2 based on the unique_keys
    filtered_organisationen = df_organisationen[
        df_organisationen["ReferenceID"].isin(verknuepfung_list)
    ]
    # if len(filtered_organisationen) == 0:
    #     print("No organisations")

    # Adding nodes to graph
    g.add_node(df_unique_name, node_type="person")
    g.add_node(filtered_organisationen, node_type="organisation")
    all_sources.extend(person_id_list)
    all_targets.extend(verknuepfung_list)
    all_labels.extend(verknuepfungsart_list)
    # g.add_edges(person_id_list, verknuepfungsart_list, verknuepfung_list)

    # Add organisations that are not directly linked to the person, but have same address, email, etc. as directly linked organisationen
    additional_organisations = get_additional_organizations(
        filtered_organisationen,
        df_organisationen,
        check_columns="all",
        include_address=address_toggle,
    )
    g.add_node(additional_organisations, node_type="organisation")
    sources = additional_organisations["source"].tolist()
    targets = additional_organisations["ReferenceID"].tolist()
    label = additional_organisations["match_type"].tolist()
    # print("organisation sources: ", sources, "targets: ", targets, "labels: ", label)
    all_sources.extend(sources)
    all_targets.extend(targets)
    all_labels.extend(label)
    # g.add_edges(sources, label, targets)

    # Also get connections between duplicate Personen
    df_unique_name = df_personen[
        df_personen["unified_name"] == name
    ]  # reset to original because of changes i made above
    person_matches, output_message_personen_internal_matches = find_internal_matches(
        df_unique_name
    )
    # print(person_matches)
    sources = person_matches["source"].tolist()
    targets = person_matches["ReferenceID"].tolist()
    label = person_matches["match_type"].tolist()

    all_sources.extend(sources)
    all_targets.extend(targets)
    all_labels.extend(label)
    # g.add_edges(sources, label, targets)

    # Optionally also get Geschäfsobjekte
    g.add_node(df_unique_name, node_type="zeiger")
    sources = [
        str(value)
        for index, value in zip(df_unique_name.index, df_unique_name["ReferenceID"])
        if df_unique_name.loc[index, "AnzahlGeschaeftsobjekte"] > 0
    ]
    targets = [
        str(value) for value in df_unique_name["AnzahlGeschaeftsobjekte"] if value > 0
    ]
    label = ["Geschaeftsobjekte"] * len(targets)
    all_sources.extend(sources)
    all_targets.extend(targets)
    all_labels.extend(label)
    # g.add_edges(sources, label, targets)

    # New: Try to find additional organizations that simply have same email/phone/address as person
    more_organizations = pd.DataFrame()
    if additional_edges:
        more_organizations = get_additional_organizations(
            df_unique_name, df_organisationen, check_columns="email_phone"
        )
        sources = more_organizations["source"].tolist()
        targets = more_organizations["ReferenceID"].tolist()
        label = more_organizations["match_type"].tolist()
        all_sources.extend(sources)
        all_targets.extend(targets)
        all_labels.extend(label)

    combined_organisations = pd.concat(
        [filtered_organisationen, additional_organisations, more_organizations], axis=0
    )

    more_personen = pd.DataFrame()
    if additional_personen:
        # Weitere Personen anzeigen, die mit den Organisationen verbunden sind.
        more_personen = get_additional_organizations(
            combined_organisations, df_personen, check_columns="ID_only"
        )
        if not more_personen.empty:
            g.add_node(more_personen, node_type="person_additional")
            sources = more_personen["source"].tolist()
            targets = more_personen["ReferenceID"].tolist()
            label = more_personen["match_type"].tolist()
            all_sources.extend(sources)
            all_targets.extend(targets)
            all_labels.extend(label)

    # --- Update organisation node with stammdaten cells

    # g.append_cells_to_node("AA0A094A-C39A-4D25-903A-4C496A3CB46D", [("A", "red")]) # A. Blaser
    # g.append_cells_to_node("AA0A094A-C39A-4D25-903A-4C496A3CB46D", [("B", "blue")])

    if not combined_organisations.empty and stammdaten_toggle:
        cell_ids, cell_labels, stammdaten = get_stammdaten_info(
            combined_organisations, df_stammdaten
        )
        for cell_id, cell_label in zip(cell_ids, cell_labels):
            g.append_cells_to_node(cell_id, [cell_label])

        # --- Experimental: In case of Stammdaten ON, show organisations that are UVEK-only with matching names
        uvek_matches = obtain_uvek_matches(combined_organisations, df_uvek_matches)
        # print(uvek_matches)
        g.add_node(uvek_matches, node_type="organisation", uvek_match=True)
        sources = uvek_matches["matches"].tolist()
        targets = uvek_matches["ReferenceID"].tolist()
        uvek_matches["score"] = uvek_matches["score"].astype(
            int
        )  # Convert scores from float to int
        label = [f"Name ({score})" for score in uvek_matches["score"]]

        all_sources.extend(sources)
        all_targets.extend(targets)
        all_labels.extend(label)

    # print("sources = ", all_sources, "targets = ", all_targets, "labels = ", all_labels)
    all_sources, all_targets, all_labels, bidirectional = clean_and_merge_lists(
        all_sources, all_targets, all_labels
    )

    g.add_edges(all_sources, all_labels, all_targets, bidirectional)

    # display additonal Geschäftspartner:
    all_nodes_unique = set(all_sources + all_targets)
    for ref_id in all_nodes_unique:
        # Extract rows that match the current ReferenceID
        matching_rows = df_personen[df_personen["ReferenceID"] == ref_id]

        for _, row in matching_rows.iterrows():
            # Check if Geschaeftspartner has one or more entries
            if row["Geschaeftspartner"] != "[]":
                # Convert the list to a string and print it
                g.append_cells_to_node(
                    ref_id,
                    [
                        (
                            str(row["Geschaeftspartner"])
                            .strip("[]")
                            .replace(" ", "")
                            .replace("'", ""),
                            "#C940BA",
                        )
                    ],
                )

    return (
        g,
        df_unique_name,
        combined_organisations,
        more_personen,
        output_message_personen_internal_matches,
    )


def split_df_by_clusters(df, g):
    """
    uses the g.clusters attribute to split a DataFrame into multiple DataFrames.
    Clusters containing only a single person go into one df, those with multiple go in another.
    Update: People that are in a cluster but have different addresses are now split.
    Tested only for personen df as input, organisationen in cluster are ignored. but should also work the other way around.
    """
    # Initialize empty DataFrames for single and multiple entries
    df_single = pd.DataFrame(columns=df.columns.tolist() + ["cluster"])
    df_multiple = pd.DataFrame(columns=df.columns.tolist() + ["cluster"])

    # Split DataFrame
    for cluster, ids in g.clusters.items():
        temp_df = df[df["ReferenceID"].isin(ids)]
        cluster_number = int(cluster.split(" ")[-1])
        temp_df["cluster"] = cluster_number  # Add 'cluster' column

        if len(temp_df) == 1:
            df_single = pd.concat([df_single, temp_df])
        elif len(temp_df) > 1:
            df_multiple = pd.concat([df_multiple, temp_df])

    true_doubletten = df_multiple.duplicated(
        subset=["unified_name", "address_gmaps", "Address1", "Address2"], keep=False
    )
    df_doubletten = df_multiple[true_doubletten]
    df_doubletten_verschiedene_addresse = df_multiple[~true_doubletten]
    return df_single, df_doubletten, df_doubletten_verschiedene_addresse


# class GraphvizWrapper_organisationen:
#     def __init__(self):
#         self.graph = Digraph("G", node_attr={"style": "filled"})

#     def add_nodes(self, node_data):
#         # Expects a DataFrame with columns 'ReferenceID', 'Name'

#         # Add nodes to the graph with labels from original_df['Name']
#         for _, row in node_data.iterrows():
#             node_id = row["ReferenceID"]
#             node_name = row["Name"]

#             attributes = {}

#             # Check if node_id is a string that starts and ends with brackets (assuming only Produkte are formatted like this)
#             if (
#                 isinstance(node_id, str)
#                 and node_id.startswith("[")
#                 and node_id.endswith("]")
#             ):
#                 # Format the node_label for Produkte
#                 node_label = node_name  # NOTE: can now have multiple nodes with this name, but hovering over it shows id.
#                 attributes["style"] = "filled"
#                 attributes["fillcolor"] = "#FFC107"
#             else:
#                 # Else use the existing formatting for the label
#                 node_id_short = str(node_id)[-3:]
#                 node_label = f"{node_name}\n{node_id_short}"

#             self.graph.node(str(node_id), label=node_label, **attributes)

#     def add_edges(self, edge_data):
#         for _, row in edge_data.iterrows():
#             source = row["source"]
#             target = row["target"]
#             match_type = row["match_type"]
#             bidirectional = row["bidirectional"]
#             special_formatting = row.get(
#                 "special_formatting", ""
#             )  # Safely get the value or default to empty string

#             arrow_shape = "normal"  # Always normal shape for the head of the arrow
#             arrowtail_shape = (
#                 "normal" if bidirectional else "none"
#             )  # normal if bidirectional, none otherwise

#             # Initialize edge attributes with default values
#             edge_attributes = {
#                 "label": match_type,
#                 "dir": "both",
#                 "arrowhead": arrow_shape,
#                 "arrowtail": arrowtail_shape,
#             }

#             if special_formatting == "Produkt":
#                 edge_attributes["color"] = "#FFC107"

#             self.graph.edge(str(source), str(target), **edge_attributes)

import streamlit as st


class GraphvizWrapper_organisationen:
    """
    Simplified version. Most processing should be done before now.
    """

    def __init__(self):
        self.graph = Digraph(
            "G", engine=st.session_state["graph_engine"], node_attr={"style": "filled"}
        )
        self.graph.attr(splines=st.session_state["edge_shape2"])
        self.graph.attr(rankdir="TB")
        self.graph.attr(ratio="auto")
        self.graph.attr(overlap="expand")
        self.graph.attr(ranksep=st.session_state["vertical_spacing"])

    def render(self, filename="output_graph", format="svg", cleanup=False):
        unflattened_graph = self.graph.unflatten(stagger=3)
        # Render the unflattened graph
        output_path = unflattened_graph.render(
            filename=filename, format=format, cleanup=cleanup
        )
        svg_str = unflattened_graph.pipe(format=format).decode("utf-8")
        return output_path, svg_str

    @staticmethod
    def xml_escape(s):
        if isinstance(s, str):
            return (
                s.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;")
            )
        return s

    def add_nodes(self, node_data):
        # Expects a DataFrame with columns 'ReferenceID', 'Name', and optionally 'link'

        # Add nodes to the graph with labels from original_df['Name']
        for _, row in node_data.iterrows():
            node_id = row["ReferenceID"]
            node_name = row["Name_original"]
            node_type = row["Typ"]
            node_servicerole = row["Servicerole_string"]
            attributes = {}

            # # Add 'URL' only if 'link' is present and is a non-empty string
            if "link" in row and row["link"] and isinstance(row["link"], str):
                attributes["URL"] = self.xml_escape(row["link"])
                attributes["target"] = '_blank'  # 
                
            if node_type == "Person":
                attributes["style"] = "filled"
                attributes["fillcolor"] = "#7296d1"
                

            # Check if node_id is a string that starts and ends with brackets (assuming only Produkte are formatted like this)
            if (
                isinstance(node_id, str)
                and node_id.startswith("[")
                and node_id.endswith("]")
            ):
                # Format the node_label for Produkte
                node_label = node_name  # NOTE: can have multiple nodes with this name, but hovering over it shows id.
                attributes["style"] = "filled"
                attributes["fillcolor"] = "#FFC107"
            else:
                # Else use the existing formatting for the label
                node_id_short = str(node_id)[-3:]
                # if node_servicerole:  # Obsolete, is now added as separate node.
                #     node_label = f"<{node_name}<BR/>{node_id_short}<BR/><B>{node_servicerole}</B>>"
                # else:
                if node_type == "Servicerole":
                    attributes["style"] = "filled"
                    attributes["fillcolor"] = "#1fddd4"
                    node_label = node_name
                else:
                    node_label = f"{node_name}\n{node_id_short}"
                    
                # mark inaktive nodes
                if not row["Aktiv"]:
                    node_label = f"<{node_name} <B>[inaktiv]</B><BR/>{node_id_short}>" # I assume there are no inactives with service roles.
                

            self.graph.node(str(node_id), label=node_label, **attributes)

    def add_edges(self, edge_data):
        for _, row in edge_data.iterrows():
            source = row["source"]
            target = row["target"]
            match_type = row["match_type"]
            bidirectional = row["bidirectional"]
            special_formatting = row.get(
                "special_formatting", ""
            )  # Safely get the value or default to empty string

            arrow_shape = "normal"  # Always normal shape for the head of the arrow
            arrowtail_shape = (
                "normal" if bidirectional else "none"
            )  # normal if bidirectional, none otherwise

            # Initialize edge attributes with default values
            edge_attributes = {
                "label": match_type,
                "dir": "both",
                "arrowhead": arrow_shape,
                "arrowtail": arrowtail_shape,
            }

            if special_formatting == "Produkt":
                edge_attributes["color"] = "#FFC107"

            self.graph.edge(str(source), str(target), **edge_attributes)
