# import pandas as pd
# import modin.pandas as pd
import pandas as pd
import networkx as nx


def match_organizations_internally(df):
    rows_list = []

    for i, row in df.iterrows():
        source = row["ReferenceID"]

        # Handling 'VerknuepftesObjektID_list' and 'Verknuepfungsart_list'
        targets = row["VerknuepftesObjektID_list"]
        match_types = row["Verknuepfungsart_list"]

        if not all(pd.isna(x) for x in targets) and not all(
            pd.isna(x) for x in match_types
        ):
            for target, match_type in zip(targets, match_types):
                if not pd.isna(target) and not pd.isna(match_type):
                    if target in df["ReferenceID"].values:
                        new_row = {
                            "source": source,
                            "target": target,
                            "match_type": match_type,
                        }
                        rows_list.append(new_row)

        # Handling 'Telefonnummer' and 'EMailAdresse' and Name
        for contact_type, column_name in [
            ("Telefon", "Telefonnummer"),
            ("Email", "EMailAdresse"),
            ("Name", "unified_name"),
        ]:
            contact_info = row[column_name]
            if pd.isna(contact_info) or contact_info == "":
                continue

            matching_rows = df[df[column_name] == contact_info]
            for _, match_row in matching_rows.iterrows():
                target = match_row["ReferenceID"]
                if target != source:
                    new_row = {
                        "source": source,
                        "target": target,
                        "match_type": contact_type,
                    }
                    rows_list.append(new_row)

    output_df = pd.DataFrame(rows_list)

    # Adding 'bidirectional' flag
    output_df["bidirectional"] = False

    to_drop = []

    for i, row in output_df.iterrows():
        source, target, match_type = row["source"], row["target"], row["match_type"]

        # If this pair was already marked for drop, continue
        if i in to_drop:
            continue

        reverse_match = output_df[
            (output_df["source"] == target)
            & (output_df["target"] == source)
            & (output_df["match_type"] == match_type)
        ]

        # Skip the row itself
        reverse_match = reverse_match.drop(i, errors="ignore")

        if not reverse_match.empty:
            output_df.at[i, "bidirectional"] = True
            to_drop.extend(reverse_match.index.tolist())

    # Remove identified duplicate 'bidirectional' rows
    output_df.drop(index=to_drop, inplace=True)
    output_df = output_df.reset_index(drop=True)

    # Logic for merging edges with "Name", "Telefon", and "Email" into one:
    merge_df = output_df[output_df["match_type"].isin(["Name", "Telefon", "Email"])]
    keep_df = output_df[~output_df["match_type"].isin(["Name", "Telefon", "Email"])]

    # Grouping rows by 'source' and 'target', aggregating 'match_type' with join
    merge_df = (
        merge_df.groupby(["source", "target"])
        .agg(
            {"match_type": lambda x: ", ".join(sorted(set(x))), "bidirectional": "any"}
        )
        .reset_index()
    )

    # Concatenate both DataFrames back together
    output_df = pd.concat([merge_df, keep_df]).reset_index(drop=True)

    return output_df


def match_organizations_internally_simplified(df, personen=False):
    # Currently used in production.
    rows_list = []

    # Handling 'VerknuepftesObjektID_list' and 'Verknuepfungsart_list'
    for i, row in df.iterrows():
        source = row["ReferenceID"]
        targets = row["VerknuepftesObjektID_list"]
        match_types = row["Verknuepfungsart_list"]

        if not all(pd.isna(x) for x in targets) and not all(
            pd.isna(x) for x in match_types
        ):
            for target, match_type in zip(targets, match_types):
                if not pd.isna(target) and not pd.isna(match_type):
                    if target in df["ReferenceID"].values:
                        new_row = {
                            "source": source,
                            "target": target,
                            "match_type": match_type,
                        }
                        rows_list.append(new_row)

    # Optimized handling of 'Telefonnummer', 'EMailAdresse', 'Name', and 'Adresse'
    if not personen:
        columns_to_check = [
            ("Telefon", "Telefonnummer"),
            ("Email", "EMailAdresse"),
            ("Name", "Name_Zeile2"),
            ("Adresse", "address_full"),
        ]
    else:
        columns_to_check = [
            ("Telefon", "Telefonnummer"),
            ("Email", "EMailAdresse"),
            ("Name", "Name"),
            ("Adresse", "address_full"),
        ]

    for contact_type, column_name in columns_to_check:
        # Remove rows with NA values (during cleanup empty strings and "nan" must have been replaced)
        df.replace("", pd.NA, inplace=True)
        valid_contacts = df.loc[df[column_name].notna()]

        # Self merge to find matching rows
        merged = valid_contacts.merge(
            valid_contacts[[column_name, "ReferenceID"]], on=column_name
        )
        merged = merged[merged["ReferenceID_x"] != merged["ReferenceID_y"]]
        merged = merged.rename(
            columns={"ReferenceID_x": "source", "ReferenceID_y": "target"}
        )
        merged["match_type"] = contact_type

        # Append the results to the list
        rows_list.extend(merged[["source", "target", "match_type"]].to_dict("records"))

    output_df = pd.DataFrame(rows_list)

    return output_df


def match_organizations_between_dataframes(d1, df2):
    # Very similar to match_organizations_internally_simplified, but checks if target is present in df2.
    # Currently only finds VerknuepftesObjekt edges (no name, address, etc.)
    rows_list = []

    # Handling 'VerknuepftesObjektID_list' and 'Verknuepfungsart_list'
    for i, row in d1.iterrows():
        source = row["ReferenceID"]
        targets = row["VerknuepftesObjektID_list"]
        match_types = row["Verknuepfungsart_list"]

        if not all(pd.isna(x) for x in targets) and not all(
            pd.isna(x) for x in match_types
        ):
            for target, match_type in zip(targets, match_types):
                if not pd.isna(target) and not pd.isna(match_type):
                    if target in df2["ReferenceID"].values:
                        new_row = {
                            "source": source,
                            "target": target,
                            "match_type": match_type,
                        }
                        rows_list.append(new_row)

    output_df = pd.DataFrame(rows_list)

    return output_df


def cleanup_edges_df_OLD(df):
    """
    Assuming edges_df checked column separately.
    Merges edges with "Name", "Telefon", "Email", "Adresse" into one.
    Adds bidirectional flag.
    """
    # Adding 'bidirectional' flag
    df["bidirectional"] = False

    to_drop = []

    for i, row in df.iterrows():
        source, target, match_type = row["source"], row["target"], row["match_type"]

        # If this pair was already marked for drop, continue
        if i in to_drop:
            continue

        reverse_match = df[
            (df["source"] == target)
            & (df["target"] == source)
            & (df["match_type"] == match_type)
        ]

        # Skip the row itself
        reverse_match = reverse_match.drop(i, errors="ignore")

        if not reverse_match.empty:
            df.at[i, "bidirectional"] = True
            to_drop.extend(reverse_match.index.tolist())

    # Remove identified duplicate 'bidirectional' rows
    df.drop(index=to_drop, inplace=True)
    df = df.reset_index(drop=True)

    # Logic for merging edges with "Name", "Telefon", and "Email" into one:
    merge_df = df[df["match_type"].isin(["Name", "Telefon", "Email", "Adresse"])]
    keep_df = df[~df["match_type"].isin(["Name", "Telefon", "Email", "Adresse"])]

    # Grouping rows by 'source' and 'target', aggregating 'match_type' with join
    merge_df = (
        merge_df.groupby(["source", "target"])
        .agg(
            {"match_type": lambda x: ", ".join(sorted(set(x))), "bidirectional": "any"}
        )
        .reset_index()
    )

    # Concatenate both DataFrames back together
    output_df = pd.concat([merge_df, keep_df]).reset_index(drop=True)
    return output_df


# def cleanup_edges_df(df):
#     """
#     Merges edges with "Name", "Telefon", "Email", "Adresse" into one.
#     Adds bidirectional flag.
#     """
#     # Directly set 'bidirectional' to True for specific match types
#     df["bidirectional"] = df["match_type"].isin(["Name", "Telefon", "Email", "Adresse"])

#     # Step 1: Create a column with sorted tuples of 'source' and 'target'
#     df["sorted_edge"] = df.apply(
#         lambda row: tuple(sorted([row["source"], row["target"]])), axis=1
#     )

#     # Group by 'sorted_edge' and 'match_type', and aggregate
#     df = (
#         df.groupby(["sorted_edge", "match_type"])
#         .agg({"source": "first", "target": "first", "bidirectional": "first"})
#         .reset_index()
#     )

#     # Step 3: Remove the 'sorted_edge' column
#     df.drop("sorted_edge", axis=1, inplace=True)

#     # Splitting DataFrame based on 'match_type'
#     merge_df = df[df["match_type"].isin(["Name", "Telefon", "Email", "Adresse"])]
#     keep_df = df[~df["match_type"].isin(["Name", "Telefon", "Email", "Adresse"])]

#     # Grouping rows by 'source', 'target', and 'bidirectional', aggregating 'match_type'
#     merge_df = (
#         merge_df.groupby(["source", "target", "bidirectional"])
#         .agg({"match_type": lambda x: ", ".join(sorted(set(x)))})
#         .reset_index()
#     )

#     # Concatenate both DataFrames back together
#     output_df = pd.concat([merge_df, keep_df]).reset_index(drop=True)
#     return output_df

# TODO: Apparently function above had mistakes, remove it if that below works:


def cleanup_edges_df(df):
    """
    Merges edges with "Name", "Telefon", "Email", "Adresse" into one.
    Adds bidirectional flag.
    We also remove edges where labels are only "Name" or "Adresse", that should never be enough for a Doublette.
    """
    # Set 'bidirectional' based on specified match_types.
    df["bidirectional"] = df["match_type"].isin(["Name", "Telefon", "Email", "Adresse"])

    # Sort 'source' and 'target' to create a unique identifier for each edge.
    df["sorted_edge"] = df.apply(
        lambda row: tuple(sorted([row["source"], row["target"]])), axis=1
    )

    # Initial split based on match_type criteria.
    specific_match_types = df["match_type"].isin(
        ["Name", "Telefon", "Email", "Adresse"]
    )
    merge_df = df[specific_match_types].copy()
    keep_df = df[~specific_match_types].copy()

    # Group by 'sorted_edge' to merge specific match_types, ensuring to capture all variations of 'source' and 'target'.
    merged = (
        merge_df.groupby("sorted_edge")
        .agg(
            {
                "source": "first",
                "target": "first",
                "bidirectional": "max",  # Ensures True if any are True.
                "match_type": lambda x: ", ".join(
                    sorted(set(x))
                ),  # Combines match_types.
            }
        )
        .reset_index(drop=True)
    )

    # Final output without 'sorted_edge'.
    output_df = pd.concat([merged, keep_df], ignore_index=True).drop(
        columns=["sorted_edge"], errors="ignore"
    )

    # Filter out rows where match_type is only "Name" or "Adresse".
    output_df = output_df[~output_df["match_type"].isin(["Name", "Adresse"])]

    return output_df


# def match_organizations_internally_optimized(df):
#     # Explode 'VerknuepftesObjektID_list' and 'Verknuepfungsart_list'
#     explode_df = df[
#         ["ReferenceID", "VerknuepftesObjektID_list", "Verknuepfungsart_list"]
#     ].explode(["VerknuepftesObjektID_list", "Verknuepfungsart_list"])
#     explode_df = explode_df.dropna(
#         subset=["VerknuepftesObjektID_list", "Verknuepfungsart_list"]
#     )
#     explode_df = explode_df[
#         explode_df["VerknuepftesObjektID_list"].isin(df["ReferenceID"])
#     ]
#     explode_df.rename(
#         columns={
#             "ReferenceID": "source",
#             "VerknuepftesObjektID_list": "target",
#             "Verknuepfungsart_list": "match_type",
#         },
#         inplace=True,
#     )

#     contact_dfs = []

#     # Handle 'Telefonnummer' (renamed to 'Telefon') and 'EMailAdresse' (renamed to 'Email')
#     for contact_type, new_name in [
#         ("Telefonnummer", "Telefon"),
#         ("EMailAdresse", "Email"),
#     ]:
#         temp_df = df.dropna(subset=[contact_type])
#         temp_df = temp_df[["ReferenceID", contact_type]].merge(
#             temp_df[["ReferenceID", contact_type]], on=contact_type
#         )
#         temp_df = temp_df[temp_df["ReferenceID_x"] != temp_df["ReferenceID_y"]]
#         temp_df["match_type"] = new_name
#         temp_df.rename(
#             columns={"ReferenceID_x": "source", "ReferenceID_y": "target"}, inplace=True
#         )
#         contact_dfs.append(temp_df[["source", "target", "match_type"]])

#     # Handle 'Name' & 'Zeile2'
#     # Create a temporary column for combined 'Name' and 'Zeile2' comparison
#     df["Name_Zeile2"] = df.apply(
#         lambda x: x["Name"] + "|" + str(x["Zeile2"])
#         if pd.notna(x["Zeile2"]) and x["Zeile2"] != ""
#         else x["Name"],
#         axis=1,
#     )

#     name_df = df.dropna(subset=["Name"])
#     name_df = name_df[["ReferenceID", "Name_Zeile2"]].merge(
#         name_df[["ReferenceID", "Name_Zeile2"]], on="Name_Zeile2"
#     )
#     name_df = name_df[name_df["ReferenceID_x"] != name_df["ReferenceID_y"]]
#     name_df["match_type"] = "Name"
#     name_df.rename(
#         columns={"ReferenceID_x": "source", "ReferenceID_y": "target"}, inplace=True
#     )
#     contact_dfs.append(name_df[["source", "target", "match_type"]])

#     # Remove the temporary column after use
#     df.drop(columns=["Name_Zeile2"], inplace=True)

#     # Handle 'address_full' (new match type 'Adresse')
#     address_df = df.dropna(subset=["address_full"])
#     address_df = address_df[["ReferenceID", "address_full"]].merge(
#         address_df[["ReferenceID", "address_full"]], on="address_full"
#     )
#     address_df = address_df[address_df["ReferenceID_x"] != address_df["ReferenceID_y"]]
#     address_df["match_type"] = "Adresse"
#     address_df.rename(
#         columns={"ReferenceID_x": "source", "ReferenceID_y": "target"}, inplace=True
#     )
#     contact_dfs.append(address_df[["source", "target", "match_type"]])

#     contact_df = pd.concat(contact_dfs).drop_duplicates()

#     # Combine all matches
#     all_matches_df = pd.concat([explode_df, contact_df]).drop_duplicates()

#     # Identify bidirectional edges
#     all_matches_df["bidirectional"] = (
#         all_matches_df[["source", "target"]]
#         .apply(frozenset, axis=1)
#         .duplicated(keep=False)
#     )

#     # Separate 'Name', 'Telefon', 'Email', and 'Adresse' for aggregation
#     aggregated_match_types = ["Name", "Telefon", "Email", "Adresse"]
#     aggregated_df = all_matches_df[
#         all_matches_df["match_type"].isin(aggregated_match_types)
#     ]
#     non_aggregated_df = all_matches_df[
#         ~all_matches_df["match_type"].isin(aggregated_match_types)
#     ]

#     # Aggregate only specified match types
#     aggregated_df = (
#         aggregated_df.groupby(["source", "target", "bidirectional"])["match_type"]
#         .agg(lambda x: ", ".join(sorted(set(x))))
#         .reset_index()
#     )

#     # Combine aggregated and non-aggregated data
#     final_df = (
#         pd.concat([aggregated_df, non_aggregated_df])
#         .drop_duplicates()
#         .reset_index(drop=True)
#     )

#     return final_df


def match_organizations_internally_optimized(df):
    # Optimize the first loop
    reference_ids = df["ReferenceID"].dropna().unique()
    rows_list = [
        {"source": row["ReferenceID"], "target": target, "match_type": match_type}
        for _, row in df.iterrows()
        for target, match_type in zip(
            row["VerknuepftesObjektID_list"], row["Verknuepfungsart_list"]
        )
        if target in reference_ids and pd.notna(match_type)
    ]

    # Handle 'Telefonnummer', 'EMailAdresse', 'Name' with 'Zeile2', and 'address_full'
    contact_types = ["Telefonnummer", "EMailAdresse", "Name_Zeile2", "address_full"]
    for contact_type in contact_types:
        if contact_type == "Name_Zeile2":
            df["Name_Zeile2"] = df.apply(
                lambda x: x["Name"] + "|" + str(x["Zeile2"])
                if pd.notna(x["Zeile2"]) and x["Zeile2"] != ""
                else x["Name"],
                axis=1,
            )

        # Use merge for matching rows
        merged_df = df.merge(df[[contact_type, "ReferenceID"]], on=contact_type)
        matched_rows = merged_df[
            merged_df["ReferenceID_x"] != merged_df["ReferenceID_y"]
        ]
        for _, row in matched_rows.iterrows():
            rows_list.append(
                {
                    "source": row["ReferenceID_x"],
                    "target": row["ReferenceID_y"],
                    "match_type": contact_type,
                }
            )

    # Convert to DataFrame
    all_matches_df = pd.DataFrame(rows_list)

    # Identify bidirectional edges
    all_matches_df["bidirectional"] = (
        all_matches_df[["source", "target"]]
        .apply(lambda x: frozenset(x), axis=1)
        .duplicated(keep=False)
    )

    # Aggregate match types
    aggregated_match_types = ["Name", "Telefon", "Email", "Adresse"]
    aggregated_df = all_matches_df[
        all_matches_df["match_type"].isin(aggregated_match_types)
    ]
    non_aggregated_df = all_matches_df[
        ~all_matches_df["match_type"].isin(aggregated_match_types)
    ]

    aggregated_df = (
        aggregated_df.groupby(["source", "target", "bidirectional"])["match_type"]
        .agg(lambda x: ", ".join(sorted(set(x))))
        .reset_index()
    )

    # Combine aggregated and non-aggregated data
    final_df = (
        pd.concat([aggregated_df, non_aggregated_df])
        .drop_duplicates()
        .reset_index(drop=True)
    )

    return final_df


# import dask.dataframe as dd
# def match_organizations_internally_dask(df):
#     # Convert Pandas DataFrame to Dask DataFrame if not already
#     df = dd.from_pandas(df, npartitions=10)  # Adjust npartitions based on your dataset and system

#     # Use Dask's explode method
#     explode_df = df.explode(['VerknuepftesObjektID_list', 'Verknuepfungsart_list'])
#     explode_df = explode_df.dropna(subset=['VerknuepftesObjektID_list', 'Verknuepfungsart_list'])
#     explode_df = explode_df[explode_df['VerknuepftesObjektID_list'].isin(df['ReferenceID'].compute())]
#     explode_df = explode_df.rename(columns={'ReferenceID': 'source', 'VerknuepftesObjektID_list': 'target', 'Verknuepfungsart_list': 'match_type'})

#     contact_dfs = []

#     # Handle 'Telefonnummer' (renamed to 'Telefon') and 'EMailAdresse' (renamed to 'Email')
#     for contact_type, new_name in [("Telefonnummer", "Telefon"), ("EMailAdresse", "Email")]:
#         temp_df = df.dropna(subset=[contact_type])
#         temp_df = temp_df[["ReferenceID", contact_type]].merge(temp_df[["ReferenceID", contact_type]], on=contact_type)
#         temp_df = temp_df[temp_df["ReferenceID_x"] != temp_df["ReferenceID_y"]]
#         temp_df["match_type"] = new_name
#         temp_df = temp_df.rename(columns={"ReferenceID_x": "source", "ReferenceID_y": "target"})
#         contact_dfs.append(temp_df[["source", "target", "match_type"]])

#     # Handle 'Name' & 'Zeile2'
#     df['Name_Zeile2'] = df.apply(lambda x: x['Name'] + '|' + x['Zeile2'] if pd.notna(x['Zeile2']) and x['Zeile2'] != '' else x['Name'], axis=1, meta=('x', 'str'))
#     name_df = df.dropna(subset=['Name'])
#     name_df = name_df[['ReferenceID', 'Name_Zeile2']].merge(name_df[['ReferenceID', 'Name_Zeile2']], on='Name_Zeile2')
#     name_df = name_df[name_df['ReferenceID_x'] != name_df['ReferenceID_y']]
#     name_df['match_type'] = 'Name'
#     name_df = name_df.rename(columns={"ReferenceID_x": "source", "ReferenceID_y": "target"})
#     contact_dfs.append(name_df[["source", "target", "match_type"]])
#     df = df.drop(columns=['Name_Zeile2'])

#     # Handle 'address_full' (new match type 'Adresse')
#     address_df = df.dropna(subset=['address_full'])
#     address_df = address_df[['ReferenceID', 'address_full']].merge(address_df[['ReferenceID', 'address_full']], on='address_full')
#     address_df = address_df[address_df['ReferenceID_x'] != address_df['ReferenceID_y']]
#     address_df['match_type'] = 'Adresse'
#     address_df = address_df.rename(columns={"ReferenceID_x": "source", "ReferenceID_y": "target"})
#     contact_dfs.append(address_df[["source", "target", "match_type"]])

#     contact_df = dd.concat(contact_dfs).drop_duplicates()

#     # Combine all matches
#     all_matches_df = dd.concat([explode_df, contact_df]).drop_duplicates()

#     # Create a DataFrame with sorted pairs
#     sorted_edges = all_matches_df.map_partitions(
#         lambda df: df.apply(lambda row: tuple(sorted([row['source'], row['target']])), axis=1),
#         meta=('x', 'object')
#     )
#     sorted_edges_df = sorted_edges.to_frame(name='sorted_edge')

#     # Count occurrences of each pair
#     edge_counts = sorted_edges_df.groupby('sorted_edge').size().compute()

#     # Identify bidirectional edges
#     bidirectional_edges = edge_counts[edge_counts > 1].index

#     # Map this information back to the original DataFrame
#     all_matches_df['bidirectional'] = all_matches_df.map_partitions(
#         lambda df: df.apply(lambda row: tuple(sorted([row['source'], row['target']])) in bidirectional_edges, axis=1),
#         meta=('x', 'bool')
#     )

#     # Aggregate only specified match types
#     aggregated_df = aggregated_df.groupby(['source', 'target', 'bidirectional'])['match_type'].apply(lambda x: ', '.join(sorted(set(x))), meta=('x', 'str')).reset_index()

#     # Combine aggregated and non-aggregated data
#     final_df = dd.concat([aggregated_df, non_aggregated_df]).drop_duplicates().reset_index(drop=True)

#     # Compute the final result back to Pandas DataFrame at the very end
#     final_result = final_df.compute()

#     return final_result


def find_clusters_all(df, special_nodes, skip_singular_clusters=False):
    """
    Here we use the networkx package for graph-based analyses.
    Input is any df that has a source, target and label column.
    Special_nodes is a set of nodes that should not be considered as central nodes nor included in cluster sizes.
    Note: this finds all clusters, i.e. nodes that just have any kind of connection. They are not necessarily Doubletten!
    """
    # Create a new graph from edge list
    G = nx.from_pandas_edgelist(
        df, "source", "target", edge_attr="match_type", create_using=nx.Graph()
    )

    # Find connected components
    connected_components = nx.connected_components(G)

    # Collect connected components (clusters) in a list
    clusters = []
    for i, component in enumerate(connected_components):
        # note: if singular clusters are skipped, i count may not be continuous.
        subgraph = G.subgraph(component)

        # Filter out the special nodes
        filtered_nodes = [node for node in component if node not in special_nodes]

        # Skip clusters of size 1
        if (len(filtered_nodes) < 2) and skip_singular_clusters:
            continue

        # Finding the most central node based on degree
        central_node = (
            max((node for node in subgraph.degree(filtered_nodes)), key=lambda x: x[1])[
                0
            ]
            if filtered_nodes
            else None
        )
        cluster_size = len(filtered_nodes)

        clusters.append(
            {
                "cluster_id": i,
                "nodes": list(component),
                "cluster_size": cluster_size,
                "central_node": central_node,
            }
        )

    # Convert to DataFrame for better visualization and further analysis
    cluster_df = pd.DataFrame(clusters)

    return cluster_df


def find_singular_cluster(
    df, starting_node, depth="all", skip_singular_clusters=False, mode="Normal"
):
    """
    Simplified version of find_clusters_all, only returns the cluster of the starting node with a given depth.
    E.g. depth=1 will only show the neighboring, directly connected nodes.
    """
    # Filter edges based on mode
    if mode == "Normal":
        df_filtered = df[
            ~df["match_type"].str.contains("Name|Email|Telefon|Adresse", na=False)
        ]
    else:
        df_filtered = df

    # Create a new graph from the filtered edge list
    G = nx.from_pandas_edgelist(
        df_filtered, "source", "target", edge_attr="match_type", create_using=nx.Graph()
    )

    # Check if starting_node is in the graph
    if starting_node not in G:
        return (
            pd.DataFrame(), df_filtered
        )  # Return an empty DataFrame if starting_node is not in graph

    if depth == "all":
        # Find the full cluster for the starting node without depth limitation
        connected_components = [nx.node_connected_component(G, starting_node)]
    else:
        # Use BFS to find nodes within the specified depth from the starting node
        edges_within_depth = list(
            nx.bfs_edges(G, source=starting_node, depth_limit=depth)
        )
        # Create a subgraph based on the edges within the specified depth
        subgraph = G.edge_subgraph(edges_within_depth).copy()
        # Find connected components in the subgraph
        connected_components = nx.connected_components(subgraph)

    # Collect connected components (clusters) in a list
    clusters = []
    for i, component in enumerate(connected_components):
        # Skip clusters of size 1 if required
        if (len(component) < 2) and skip_singular_clusters:
            continue

        clusters.append(
            {
                "cluster_id": i,
                "nodes": list(component),
            }
        )

    # Convert to DataFrame for better visualization and further analysis
    cluster_df = pd.DataFrame(clusters)

    return cluster_df, df_filtered


def find_clusters_only_doubletten(df, special_nodes):
    """
    Currently most advanced function for org: checks if there are any edges with "Adresse" and "Name" are within a cluster.
    Only returns those node1 and node2 that are thus true Doubletten.
    """

    # Create a MultiGraph from edge list to handle multiple edges between same nodes
    G = nx.from_pandas_edgelist(
        df, "source", "target", edge_attr="match_type", create_using=nx.MultiGraph()
    )

    # Find connected components
    connected_components = nx.connected_components(G)

    # Collect pairs meeting criteria in a list
    pairs = []
    for i, component in enumerate(connected_components):
        subgraph = G.subgraph(component)

        # Filter out the special nodes
        filtered_nodes = [node for node in component if node not in special_nodes]

        # Check every pair of nodes in the cluster
        for node1 in filtered_nodes:
            for node2 in filtered_nodes:
                if node1 < node2:  # Ensure each pair is only considered once
                    edge_data_list = subgraph.get_edge_data(node1, node2, default={})

                    # Check if edge_data_list is not a list
                    if not isinstance(edge_data_list, list):
                        for edge_data in edge_data_list.values():
                            if (
                                "Name" in edge_data["match_type"]
                                and "Adresse" in edge_data["match_type"]
                            ):
                                pairs.append(
                                    {
                                        "cluster_id": i,
                                        "node1": node1,
                                        "node2": node2,
                                        "match_type": edge_data["match_type"],
                                    }
                                )
                                break  # Break after finding the first matching edge

    # Convert to DataFrame for better visualization and further analysis
    pairs_df = pd.DataFrame(pairs)

    return pairs_df


def organisationen_get_doubletten(node_data):
    """
    OBSOLETE?
    Expects the node_data df that is generated by the generate_graph function.
    Doublette is defined by identical unified_name, address_gmaps and Address1/2, whereas if Address1/2 are empty, Korr_Address1/2 are used.
    """
    df_check = node_data.copy()
    df_check["Address1"] = node_data.apply(
        lambda row: row["Korr_Address1"]
        if (row["Address1"] == "" or pd.isna(row["Address1"]))
        else row["Address1"],
        axis=1,
    )
    df_check["Address2"] = node_data.apply(
        lambda row: row["Korr_Address2"]
        if (row["Address2"] == "" or pd.isna(row["Address2"]))
        else row["Address2"],
        axis=1,
    )
    # Extract duplicates
    duplicates = df_check[
        df_check.duplicated(
            subset=["unified_name", "address_gmaps", "Address1", "Address2"], keep=False
        )
    ]

    output_messages = []
    # Check for mismatches in Zusatzzeilen
    for i, row1 in df_check.iterrows():
        for j, row2 in df_check.iterrows():
            if i < j:  # To ensure each pair is only checked once
                if (
                    row1["unified_name"] == row2["unified_name"]
                    and row1["address_gmaps"] == row2["address_gmaps"]
                ):
                    if (
                        not (pd.isna(row1["Address1"]) and pd.isna(row2["Address1"]))
                        and row1["Address1"] != row2["Address1"]
                    ):
                        output_messages.append(
                            f"Mismatch in Address1 between {row1['ReferenceID'][-3:]} ({row1['Address1']}) and {row2['ReferenceID'][-3:]} ({row2['Address1']})"
                        )
                    if (
                        not (pd.isna(row1["Address2"]) and pd.isna(row2["Address2"]))
                        and row1["Address2"] != row2["Address2"]
                    ):
                        output_messages.append(
                            f"Mismatch in Address2 between {row1['ReferenceID'][-3:]} ({row1['Address2']}) and {row2['ReferenceID'][-3:]} ({row2['Address2']})"
                        )
    return duplicates, output_messages


def find_twin_duplicates(all_clusters, df_organisationen):
    """
    probably obsolete
    """
    twin_duplicates_list = []
    new_cluster_id = (
        0  # Initialize a counter for new unique cluster IDs for twin duplicates
    )

    for _, cluster_row in all_clusters.iterrows():
        cluster_nodes = cluster_row["nodes_list"]

        # Select rows from df_organisationen that match the cluster nodes
        temp_node_data = df_organisationen[
            df_organisationen["ReferenceID"].isin(cluster_nodes)
        ]

        # Handle NaN or empty values before running organisationen_get_doubletten
        temp_node_data["Address1"].fillna("No Address", inplace=True)
        temp_node_data["Address2"].fillna("No Address", inplace=True)

        duplicates_info = organisationen_get_doubletten(temp_node_data)
        duplicates_df = (
            duplicates_info[0]
            if isinstance(duplicates_info, tuple)
            else duplicates_info
        )

        # Group by duplicate criteria and find groups of size 2
        for _, dup_group in duplicates_df.groupby(
            ["unified_name", "address_gmaps", "Address1", "Address2"]
        ):
            if len(dup_group) == 2:
                # Assign a new, unique cluster_id to each pair of duplicates
                twin_duplicates_list.append(dup_group.assign(cluster_id=new_cluster_id))
                new_cluster_id += 1  # Increment the new cluster ID

    # Concatenate all individual DataFrames to create the final DataFrame for twin duplicates
    twin_duplicates_df = (
        pd.concat(twin_duplicates_list, ignore_index=True)
        if twin_duplicates_list
        else pd.DataFrame()
    )
    return twin_duplicates_df


# def add_produkte_columns(df_organisationen, organisationsrollen_df):
#     # Only needed for score.
#     # Neue Kolonnen:
#     # "Produkt_Inhaber": Wie oft diese orginsation inhaber ist
#     # "Produkt_Adressant": Wie oft diese orginsation Korrempf. oder Rechempf. ist
#     df_organisationen["Produkt_Inhaber"] = 0
#     df_organisationen["Produkt_Adressant"] = 0

#     # Increment 'Produkt_Inhaber' and 'Produkt_Adressant' within a single loop
#     for ref_id in df_organisationen["ReferenceID"]:
#         # Increment for 'Produkt_Inhaber'
#         inhaber_count = organisationsrollen_df["Inhaber_RefID"].eq(ref_id).sum()
#         df_organisationen.loc[
#             df_organisationen["ReferenceID"] == ref_id, "Produkt_Inhaber"
#         ] += inhaber_count

#         # Increment for 'Produkt_Adressant' for both 'Rechnungsempfaenger_RefID' and 'Korrespondenzempfaenger_RefID'
#         adressant_count = (
#             organisationsrollen_df["Rechnungsempfaenger_RefID"].eq(ref_id).sum()
#             + organisationsrollen_df["Korrespondenzempfaenger_RefID"].eq(ref_id).sum()
#         )
#         df_organisationen.loc[
#             df_organisationen["ReferenceID"] == ref_id, "Produkt_Adressant"
#         ] += adressant_count
#     return df_organisationen


def add_produkte_columns(df_organisationen, organisationsrollen_df):
    # optimized version of function above
    # Calculate counts for 'Produkt_Inhaber'
    inhaber_counts = organisationsrollen_df["Inhaber_RefID"].value_counts()
    # Map these counts to df_organisationen
    df_organisationen["Produkt_Inhaber"] = (
        df_organisationen["ReferenceID"].map(inhaber_counts).fillna(0).astype(int)
    )

    # Calculate counts for 'Produkt_Adressant'
    adressant_counts = (
        organisationsrollen_df["Rechnungsempfaenger_RefID"].value_counts()
        + organisationsrollen_df["Korrespondenzempfaenger_RefID"].value_counts()
    )
    # Map these counts to df_organisationen
    df_organisationen["Produkt_Adressant"] = (
        df_organisationen["ReferenceID"].map(adressant_counts).fillna(0).astype(int)
    )

    return df_organisationen


# def add_singular_produkte_columns(row, organisationsrollen_df, produkt):
#     """
#       Very slow, optimized version below
#     Specify which produkt by providing a name in produkte_dict (must be in same module as this function).
#     Will check if a given ReferenceID has a role associated with that type of produkt (and ONLY that type, if it has none or also other produkt-types its marked for removal)
#     """

#     # Find the FullID corresponding to the given produkt
#     full_id = None
#     for key, value in produkte_dict.items():
#         if value == produkt:
#             full_id = key
#             break

#     if not full_id:
#         raise ValueError(f"Produkt '{produkt}' not found in produkte_dict")

#     roles = [
#         "Inhaber_RefID",
#         "Rechnungsempfaenger_RefID",
#         "Korrespondenzempfaenger_RefID",
#     ]
#     ref_id = row["ReferenceID"]

#     # Check if ReferenceID is associated with a different FullID in any role
#     different_full_id = organisationsrollen_df.loc[
#         (organisationsrollen_df["FullID"] != full_id)
#         & (organisationsrollen_df[roles].apply(lambda x: ref_id in x.values, axis=1))
#     ].any(axis=None)

#     # Check if ReferenceID does not occur in any role for the specified FullID
#     not_in_roles = not organisationsrollen_df.loc[
#         (organisationsrollen_df["FullID"] == full_id)
#         & (organisationsrollen_df[roles].apply(lambda x: ref_id in x.values, axis=1))
#     ].any(axis=None)

#     if different_full_id or not_in_roles:
#         return "removal"

#     # If ReferenceID is present for the specified FullID, construct the role string (e.g. "1x Inhaber")
#     produkt_role_strings = []
#     for role in roles:
#         ref_id_count = organisationsrollen_df.loc[
#             (organisationsrollen_df["FullID"] == full_id)
#             & (organisationsrollen_df[role] == ref_id),
#             role,
#         ].count()

#         if ref_id_count > 0:
#             role_name = role.split("_")[0]  # Extract the role name without "_RefID"
#             produkt_role_strings.append(f"{ref_id_count}x {role_name}")

#     return ", ".join(produkt_role_strings) if produkt_role_strings else "removal"


def add_singular_produkte_columns_group(group, organisationsrollen_df, produkt):
    """
    Specify which produkt by providing a name in produkte_dict (must be in same module as this function).
    Will check if a given ReferenceID has a role associated with that type of produkt (and ONLY that type, if it has none or also other produkt-types its marked for removal)
    """
    # Find the FullID corresponding to the given produkt
    full_id = produkte_dict_name_first.get(produkt)
    if not full_id:
        raise ValueError(f"Produkt '{produkt}' not found in produkte_dict")

    roles = [
        "Inhaber_RefID",
        "Rechnungsempfaenger_RefID",
        "Korrespondenzempfaenger_RefID",
    ]
    role_columns = {
        "Inhaber_RefID": ("Inhaber_Objekt", "Inhaber_ProduktID"),
        "Rechnungsempfaenger_RefID": ("Rechempf_Objekt", "Rechempf_ProduktID"),
        "Korrespondenzempfaenger_RefID": ("Korrempf_Objekt", "Korrempf_ProduktID"),
    }

    # Initialize new columns if they don't exist
    for column in role_columns.values():
        for col in column:
            if col not in group.columns:
                group[col] = [[] for _ in range(len(group))]

    # Pre-filter organisationsrollen_df by FullID
    filtered_organisationsrollen_df = organisationsrollen_df[
        organisationsrollen_df["FullID"] == full_id
    ]

    # Iterate over each row in the group
    for index, ref_id in group["ReferenceID"].items():
        # Filter rows based on ref_id
        filtered_df = filtered_organisationsrollen_df[
            filtered_organisationsrollen_df[roles].isin([ref_id]).any(axis=1)
        ]

        for role in roles:
            # Filter for the specific role
            role_filtered_df = filtered_df[filtered_df[role] == ref_id]

            # Check if the role exists
            if not role_filtered_df.empty:
                objekt_col, produktid_col = role_columns[role]
                group.at[index, objekt_col] = role_filtered_df["ProduktObj"].tolist()
                group.at[index, produktid_col] = role_filtered_df[
                    "Produkt_RefID"
                ].tolist()

    return group


# def add_singular_produkte_columns_group(group, organisationsrollen_df, produkt):
#     # Find the FullID corresponding to the given produkt
#     full_id = None
#     for key, value in produkte_dict.items():
#         if value == produkt:
#             full_id = key
#             break

#     if not full_id:
#         raise ValueError(f"Produkt '{produkt}' not found in produkte_dict")

#     roles = [
#         "Inhaber_RefID",
#         "Rechnungsempfaenger_RefID",
#         "Korrespondenzempfaenger_RefID",
#     ]

#     # Initialize columns if they don't exist
#     if 'Produkt_Objekt' not in group.columns:
#         group['Produkt_Objekt'] = [[] for _ in range(len(group))]
#     if 'Produkt_RefID' not in group.columns:
#         group['Produkt_RefID'] = [[] for _ in range(len(group))]
#     if 'Result' not in group.columns:
#         group['Result'] = ['' for _ in range(len(group))]

#     # Iterate over each row in the group
#     for index, row in group.iterrows():
#         ref_id = row["ReferenceID"]

#         # Check if ReferenceID is associated with a different FullID in any role
#         different_full_id = organisationsrollen_df.loc[
#             (organisationsrollen_df["FullID"] != full_id)
#             & (organisationsrollen_df[roles].apply(lambda x: ref_id in x.values, axis=1))
#         ].any(axis=None)

#         # Check if ReferenceID does not occur in any role for the specified FullID
#         not_in_roles = not organisationsrollen_df.loc[
#             (organisationsrollen_df["FullID"] == full_id)
#             & (organisationsrollen_df[roles].apply(lambda x: ref_id in x.values, axis=1))
#         ].any(axis=None)

#         if different_full_id or not_in_roles:
#             group.at[index, "Result"] = "removal"
#         else:
#             role_counts = {role: 0 for role in roles}  # Initialize a count dictionary for each role
#             produkt_objekte = []
#             produkt_ref_ids = []

#             matching_rows = organisationsrollen_df[
#                 (organisationsrollen_df["FullID"] == full_id)
#                 & (organisationsrollen_df[roles].apply(lambda x: ref_id in x.values, axis=1))
#             ]

#             for _, matching_row in matching_rows.iterrows():
#                 produkt_objekte.append(matching_row['ProduktObj'])
#                 produkt_ref_ids.append(matching_row['Produkt_RefID'])

#                 for role in roles:
#                     if matching_row[role] == ref_id:
#                         role_counts[role] += 1  # Increment the count for the role

#             produkt_role_strings = [f"{count}x {role.split('_')[0]}" for role, count in role_counts.items() if count > 0]

#             group.at[index, "Produkt_Objekt"] = produkt_objekte
#             group.at[index, "Produkt_RefID"] = produkt_ref_ids
#             group.at[index, "Result"] = ", ".join(produkt_role_strings) if produkt_role_strings else "removal"

#     return group


def add_singular_produkte_columns_group(group, organisationsrollen_df, produkt):
    """
    Inputs are simply all groups (cluster_id). If any group has no Produkete of the specified type, the newly created columns will just be empty.
    By running cleanup_produkte_columns() after this one, we eventually get the clusters for the specific produkt as expected.
    """
    # Find the FullID corresponding to the given produkt
    full_id = None
    for key, value in produkte_dict.items():
        if value == produkt:
            full_id = key
            break

    if not full_id:
        raise ValueError(f"Produkt '{produkt}' not found in produkte_dict")

    roles = [
        "Inhaber_RefID",
        "Rechnungsempfaenger_RefID",
        "Korrespondenzempfaenger_RefID",
    ]

    role_columns = {
        "Inhaber_RefID": ("Inhaber_Objekt", "Inhaber_ProduktID"),
        "Rechnungsempfaenger_RefID": ("Rechempf_Objekt", "Rechempf_ProduktID"),
        "Korrespondenzempfaenger_RefID": ("Korrempf_Objekt", "Korrempf_ProduktID"),
    }

    # Initialize new columns if they don't exist
    for column in role_columns.values():
        for col in column:
            if col not in group.columns:
                group[col] = [[] for _ in range(len(group))]

    # Iterate over each row in the group
    for index, row in group.iterrows():
        ref_id = row["ReferenceID"]

        # Filter rows in organisationsrollen_df based on ref_id and roles
        filtered_df = organisationsrollen_df[
            organisationsrollen_df[roles].apply(lambda x: ref_id in x.values, axis=1)
        ]

        for role in roles:
            # Filter for the specific role
            role_filtered_df = filtered_df[filtered_df[role] == ref_id]

            # Check if the role exists for the specified FullID
            if not role_filtered_df[role_filtered_df["FullID"] == full_id].empty:
                objekt_col, produktid_col = role_columns[role]
                group.at[index, objekt_col] = role_filtered_df["ProduktObj"].tolist()
                group.at[index, produktid_col] = role_filtered_df[
                    "Produkt_RefID"
                ].tolist()

    return group


# def cleanup_produkte_columns(df):
#     """
#     To be executed after add_singular_produkte_columns_group()
#     input df still has groups with empty lists in Inhaber_Objekt etc., which will be removed here.
#     Also if any group member has e.g. a produkt listed as Inhaber, but that produkt is nowhere listed as korrempf/rechempf in the group, discards the whole group.
#     It does not however care how the products are distributed (e.g. all roles for one org, or distributed across 3)
#     """

#     def check_group(group):
#         # Check if all three columns are empty in the entire group
#         if (
#             group["Inhaber_Objekt"].apply(len).sum() == 0
#             and group["Rechempf_Objekt"].apply(len).sum() == 0
#             and group["Korrempf_Objekt"].apply(len).sum() == 0
#         ):
#             return False  # Mark group for removal

#         # Flatten the lists in each column and count occurrences
#         all_inhaber = [item for sublist in group["Inhaber_Objekt"] for item in sublist]
#         all_rechempf = [
#             item for sublist in group["Rechempf_Objekt"] for item in sublist
#         ]
#         all_korrempf = [
#             item for sublist in group["Korrempf_Objekt"] for item in sublist
#         ]

#         # Create a set of all unique items across the columns
#         unique_items = set(all_inhaber + all_rechempf + all_korrempf)

#         # Check if each item appears exactly three times across the columns
#         for item in unique_items:
#             if (
#                 all_inhaber.count(item) != 1
#                 or all_rechempf.count(item) != 1
#                 or all_korrempf.count(item) != 1
#             ):
#                 return False  # Mark group for removal

#         return True  # Keep the group

#     # Apply the check to each group and filter the DataFrame
#     filtered_df = df.groupby("cluster_id").filter(check_group)

#     return filtered_df


def cleanup_produkte_columns(df, ignore_rechempf=False):
    """
    To be executed after add_singular_produkte_columns_group()
    input df still has groups with empty lists in Inhaber_Objekt etc., which will be removed here.
    Also if any group member has e.g. a produkt listed as Inhaber, but that produkt is nowhere listed as korrempf/rechempf in the group, discards the whole group.
    It does not however care how the products are distributed (e.g. all roles for one org, or distributed across 3)

    New option for FDA: ignore Rechempf from check since it doesn't exist there.
    """

    def check_group(group):
        # Check if Inhaber_Objekt and Korrempf_Objekt columns are empty in the entire group
        if (
            group["Inhaber_Objekt"].apply(len).sum() == 0
            and group["Korrempf_Objekt"].apply(len).sum() == 0
        ):
            return False  # Mark group for removal

        # Flatten the lists in each column and count occurrences
        all_inhaber = [item for sublist in group["Inhaber_Objekt"] for item in sublist]
        all_korrempf = [
            item for sublist in group["Korrempf_Objekt"] for item in sublist
        ]

        # If not ignoring Rechempf_Objekt, include its values
        if not ignore_rechempf:
            all_rechempf = [
                item for sublist in group["Rechempf_Objekt"] for item in sublist
            ]
            unique_items = set(all_inhaber + all_rechempf + all_korrempf)
        else:
            unique_items = set(all_inhaber + all_korrempf)

        # Check if each item appears in the required columns
        for item in unique_items:
            if all_inhaber.count(item) != 1 or all_korrempf.count(item) != 1:
                return False  # Mark group for removal

            if not ignore_rechempf and all_rechempf.count(item) != 1:
                return False  # Mark group for removal if Rechempf_Objekt is considered

        return True  # Keep the group

    # Apply the check to each group and filter the DataFrame
    filtered_df = df.groupby("cluster_id").filter(check_group)

    return filtered_df


def split_produkte_groups(df):
    df_inhaber_korrempf = pd.DataFrame(columns=df.columns)
    df_inhaber_rechempf = pd.DataFrame(columns=df.columns)
    df_korrempf_rechempf = pd.DataFrame(columns=df.columns)
    df_remaining = pd.DataFrame(columns=df.columns)

    for cluster_id, group in df.groupby("cluster_id"):
        # Initialize sets to track common elements
        common_inhaber_korrempf = set()
        common_inhaber_rechempf = set()
        common_korrempf_rechempf = set()

        # Check each row for common elements
        for _, row in group.iterrows():
            inhaber = set(row["Inhaber_Objekt"])
            rechempf = set(row["Rechempf_Objekt"])
            korrempf = set(row["Korrempf_Objekt"])

            if inhaber & korrempf and not inhaber & rechempf:
                common_inhaber_korrempf.update(inhaber & korrempf)
            if inhaber & rechempf and not inhaber & korrempf:
                common_inhaber_rechempf.update(inhaber & rechempf)
            if korrempf & rechempf and not korrempf & inhaber:
                common_korrempf_rechempf.update(korrempf & rechempf)

        # Function to determine if row contains common elements (Just for sorting, the row that contains two common element shows first now)
        def contains_common(row, common_elements):
            return any(elem in row for elem in common_elements)

        # Sort and classify the group based on the common elements found
        if common_inhaber_korrempf:
            group["sort_key"] = group["Inhaber_Objekt"].apply(
                lambda x: contains_common(x, common_inhaber_korrempf)
            )
            df_inhaber_korrempf = pd.concat(
                [
                    df_inhaber_korrempf,
                    group.sort_values(by="sort_key", ascending=False).drop(
                        "sort_key", axis=1
                    ),
                ]
            )
        elif common_inhaber_rechempf:
            group["sort_key"] = group["Rechempf_Objekt"].apply(
                lambda x: contains_common(x, common_inhaber_rechempf)
            )
            df_inhaber_rechempf = pd.concat(
                [
                    df_inhaber_rechempf,
                    group.sort_values(by="sort_key", ascending=False).drop(
                        "sort_key", axis=1
                    ),
                ]
            )
        elif common_korrempf_rechempf:
            group["sort_key"] = group["Korrempf_Objekt"].apply(
                lambda x: contains_common(x, common_korrempf_rechempf)
            )
            df_korrempf_rechempf = pd.concat(
                [
                    df_korrempf_rechempf,
                    group.sort_values(by="sort_key", ascending=False).drop(
                        "sort_key", axis=1
                    ),
                ]
            )
        else:
            df_remaining = pd.concat([df_remaining, group])

    return df_inhaber_korrempf, df_inhaber_rechempf, df_korrempf_rechempf, df_remaining


def renumber_pairs(column):
    # To recognize clusters I have a continous cluster-id, e.g. 1,1,2,2,3,3, but due to filtering there are some gaps, 1,1,3,3, ...
    # this will just renumber it to 1,1,2,2
    # numbers dont even have to be in ascending order, e.g. if i sorted dataframe by name before and cluster_ids become 3,3,1,1,2,2
    # will just respect the order of appearance and re-number starting with 1.
    mapping = {}
    new_id = 1

    for val in column:
        if val not in mapping:
            mapping[val] = new_id
            new_id += 1

    new_values = [mapping[val] for val in column]
    return new_values


produkte_dict = {
    "29B43D7B-960F-494F-B260-33368AE9ACE2": "116xyz-Kurznummer",
    "A899AEA6-3033-46E5-A242-8A0F3A425EF5": "18xy-Kurznummer",
    "5D4C0871-C63D-49BB-850F-606E70817CE1": "1xy-Kurznummer",
    "D75E0240-0C9D-4DAD-B31D-BF8C5CF86A54": "Carrier Selection Code (CSC)",
    "8D4C2F35-E90A-4D77-8D76-F453A7FF7CBE": "E.164-Nummernblock",
    "FD2FCD2D-37D9-4BA1-A93E-4F8AB22C635A": "E.164-Zugangskennzahl",
    "99FF60D9-9B43-4C47-8948-14EAAE686677": "Einzelnummer",
    "B24663B2-9E1E-40DC-9055-12FB4799CFDF": "International Signalling Point Code (ISPC)",
    "D0679B9A-2EE4-4A23-A32D-814B256B321B": "Issuer Identifier Number (IIN)",
    "315E0746-3047-45F2-B5AC-AFD30F9412E7": "Mobile Network Code (MNC)",
    "EA974444-4AF0-4E8F-86CC-3CF4BB587E26": "National Signalling Point Code (NSPC)",
    "C50E13E2-391C-48D4-96E8-F7EB8D7E30C0": "Objektbezeichner (OID)",
    "D57A30D1-1C04-46CD-9E6C-F66D6A86C55B": "Weiteres Adressierungselement",
    "87CE18A7-A3D5-43E5-A445-72AD21B351FF": "Packet Radio Rufzeichen",
    "31D7DED6-CA00-4309-8529-833272055D5B": "Rufzeichen Amateurfunk",
    "FF1B2DFE-39CE-457C-A0E9-9B5C44FB52CA": "Rufzeichen Hochseeyacht",
    "B015893F-82C4-45E7-AC6D-8F81FC54795E": "Rufzeichen Luftfahrzeug",
    "63FBD550-0EE0-4AD3-9893-DB10855DB242": "Rufzeichen Rheinschiff",
    "B90ED2E5-14EA-4539-B4E6-FABFC915A113": "Rufzeichen SOLAS-Schiff",
    "9EDF7CB3-33E9-4743-98C9-E0B6B87F2EDF": "Handsprechfunkgeräte mit DSC (Maritime Kennung)",
    "978F554D-5DD4-4FA7-8654-E099D56304C2": "FDA",
}

produkte_dict_name_first = {
    "116xyz-Kurznummer": "29B43D7B-960F-494F-B260-33368AE9ACE2",
    "18xy-Kurznummer": "A899AEA6-3033-46E5-A242-8A0F3A425EF5",
    "1xy-Kurznummer": "5D4C0871-C63D-49BB-850F-606E70817CE1",
    "Carrier Selection Code (CSC)": "D75E0240-0C9D-4DAD-B31D-BF8C5CF86A54",
    "E.164-Nummernblock": "8D4C2F35-E90A-4D77-8D76-F453A7FF7CBE",
    "E.164-Zugangskennzahl": "FD2FCD2D-37D9-4BA1-A93E-4F8AB22C635A",
    "Einzelnummer": "99FF60D9-9B43-4C47-8948-14EAAE686677",
    "International Signalling Point Code (ISPC)": "B24663B2-9E1E-40DC-9055-12FB4799CFDF",
    "Issuer Identifier Number (IIN)": "D0679B9A-2EE4-4A23-A32D-814B256B321B",
    "Mobile Network Code (MNC)": "315E0746-3047-45F2-B5AC-AFD30F9412E7",
    "National Signalling Point Code (NSPC)": "EA974444-4AF0-4E8F-86CC-3CF4BB587E26",
    "Objektbezeichner (OID)": "C50E13E2-391C-48D4-96E8-F7EB8D7E30C0",
    "Weiteres Adressierungselement": "D57A30D1-1C04-46CD-9E6C-F66D6A86C55B",
    "Packet Radio Rufzeichen": "87CE18A7-A3D5-43E5-A445-72AD21B351FF",
    "Rufzeichen Amateurfunk": "31D7DED6-CA00-4309-8529-833272055D5B",
    "Rufzeichen Hochseeyacht": "FF1B2DFE-39CE-457C-A0E9-9B5C44FB52CA",
    "Rufzeichen Luftfahrzeug": "B015893F-82C4-45E7-AC6D-8F81FC54795E",
    "Rufzeichen Rheinschiff": "63FBD550-0EE0-4AD3-9893-DB10855DB242",
    "Rufzeichen SOLAS-Schiff": "B90ED2E5-14EA-4539-B4E6-FABFC915A113",
    "Handsprechfunkgeräte mit DSC (Maritime Kennung)": "9EDF7CB3-33E9-4743-98C9-E0B6B87F2EDF",
    "FDA": "978F554D-5DD4-4FA7-8654-E099D56304C2",
}


def organisationsrollen_group_aggregate(df):
    # Input is das raw xlsx vom Organisationsrollen query.
    # Benutzt dictionary oben Produkt_typ als string, Count für eine Kombination aus typ/inh./rechempf/korrempf und liste der produkt-objekte zu generieren.
    grouped_df = (
        df.groupby(
            [
                "Inhaber_RefID",
                "Rechnungsempfaenger_RefID",
                "Korrespondenzempfaenger_RefID",
                "FullID",
            ]
        )
        .agg(
            Produkt_count=pd.NamedAgg(column="Produkt_RefID", aggfunc="size"),
            Produkte=pd.NamedAgg(column="ProduktObj", aggfunc=list),
            **{
                col: pd.NamedAgg(column=col, aggfunc="first")
                for col in df.columns
                if col
                not in [
                    "Inhaber_RefID",
                    "Rechnungsempfaenger_RefID",
                    "Korrespondenzempfaenger_RefID",
                    "Produkt_RefID",
                    "FullID",
                    "ProduktObj",
                ]
            },
        )
        .reset_index()
    )

    # Create 'Produkt_typ' by mapping 'FullID' through the data dictionary
    grouped_df["Produkt_typ"] = grouped_df["FullID"].map(produkte_dict)

    return grouped_df


def generate_edge_list_from_orginationsrollen_aggregate(df):
    """
    "source" eines edges ist kombination aus liste der objekte+produkttyp newline count. um eindeutig zu sein.
    Für eine source gibt es jeweils 3 row / Targets (inh. rechempf. korrempf.) mit RefID und label.
    diese edge list kann dann mit internen endge list der organisationen concateniert werden.
    """
    edge_list = []
    for _, row in df.iterrows():
        source = (
            str(row["Produkte"])
            + str(row["Produkt_typ"])
            + "\n"
            + str([row["Produkt_count"]][0])
        )
        for target, target_type in [
            (row["Rechnungsempfaenger_RefID"], "Rechnungsempfaenger"),
            (row["Korrespondenzempfaenger_RefID"], "Korrespondenzempfaenger"),
            (row["Inhaber_RefID"], "Inhaber"),
        ]:
            edge_list.append(
                {"source": source, "target": target, "match_type": target_type}
            )

    # Create a DataFrame from the edge list
    edges_df = pd.DataFrame(edge_list)
    return edges_df


def add_servicerole_column(df_organisationen, serviceroles_df):
    # Very similar to "add_Produkte_columns()"
    # This one just adds a count, to filter out those that have a service role.
    df_organisationen["Servicerole_count"] = 0

    for ref_id in df_organisationen["ReferenceID"]:
        role_count = serviceroles_df["Rechtsträger_RefID"].eq(ref_id).sum()
        df_organisationen.loc[
            df_organisationen["ReferenceID"] == ref_id, "Servicerole_count"
        ] += role_count
    return df_organisationen


servicerollen = {
    "AC441A4D-0BB7-4363-ACFF-DFAEECF2AF12": "FDA",
    "0DA55C52-B526-4FEC-A663-5AC9919B1C9D": "Veranstalterkonzessionär",
    "C440845B-1DA5-4663-B37C-BD3E0466E9A8": "BORS",
    "393C48AA-2986-4F08-BADE-D97ADE0BB332": "Ausweis",
}


def add_servicerole_column_string(df_data, serviceroles_df):
    # This one adds the actual name of the service role. For personen to give Ausweis higher score later on.
    df_data["Servicerole_string"] = ""

    for index, row in df_data.iterrows():
        ref_id = row["ReferenceID"]
        matching_roles = serviceroles_df[
            serviceroles_df["Rechtsträger_RefID"] == ref_id
        ]

        roles = []
        for _, role_row in matching_roles.iterrows():
            role_ref_id = role_row["ServiceRoleReferenceID"]
            role = servicerollen.get(role_ref_id, "")
            if role:
                roles.append(role)

        df_data.at[index, "Servicerole_string"] = ", ".join(roles)

    return df_data


produkte_dict_personen = {
    "B015893F-82C4-45E7-AC6D-8F81FC54795E": "Rufzeichen Luftfahrzeug",
    "63FBD550-0EE0-4AD3-9893-DB10855DB242": "Rufzeichen Rheinschiff",
    "B90ED2E5-14EA-4539-B4E6-FABFC915A113": "Rufzeichen SOLAS-Schiff",
    "978F554D-5DD4-4FA7-8654-E099D56304C2": "FDA",
}


def add_personen_produkte_columns(df_data, df_produktrollen):
    # Creating dictionaries for quick lookup with lists to handle non-unique indices
    kontaktperson_dict = (
        df_produktrollen.groupby("Kontaktperson_RefID")
        .apply(lambda x: x.to_dict("records"))
        .to_dict()
    )
    technikperson_dict = (
        df_produktrollen.groupby("Technikperson_RefID")
        .apply(lambda x: x.to_dict("records"))
        .to_dict()
    )
    statistikperson_dict = (
        df_produktrollen.groupby("Statistikperson_RefID")
        .apply(lambda x: x.to_dict("records"))
        .to_dict()
    )

    # Initialize new columns as lists
    df_data["Produkt_rolle"] = [[] for _ in range(len(df_data))]
    df_data["Produkt_RefID"] = [[] for _ in range(len(df_data))]

    # Iterate over each row in df_data
    for index, row in df_data.iterrows():
        reference_id = row["ReferenceID"]

        # Check for matches in dictionaries
        for ref_dict, role in [
            (kontaktperson_dict, "Kontaktperson"),
            (technikperson_dict, "Technikperson"),
            (statistikperson_dict, "Statistikperson"),
        ]:
            if reference_id in ref_dict:
                for produktrollen_row in ref_dict[reference_id]:
                    # Lookup in dictionary and append role with additional information
                    full_id = produktrollen_row["FullID"]
                    additional_info = produkte_dict_personen.get(full_id, "")
                    role_with_info = (
                        f"{role} ({additional_info})" if additional_info else role
                    )

                    df_data.at[index, "Produkt_rolle"].append(role_with_info)
                    df_data.at[index, "Produkt_RefID"].append(
                        produktrollen_row["Produkt_RefID"]
                    )

    return df_data


def add_organisationsrollen_string_columns(df1, df2):
    """
    Inputs are df_organisationen and organisationsrollen_df.
    Adds a column "Organisationsrollen", a list where each element is a string like "Inhaber (FDA)"
    and a corresponding column "Organisationrollen_ProduktID" with the corresponding ProduktID for which this organisation is Inhaber.
    """
    # Initialize the new columns with empty lists
    df1["Organisationsrollen"] = [[] for _ in range(len(df1))]
    df1["Organisationrollen_ProduktID"] = [[] for _ in range(len(df1))]

    # Iterate over each row in df1
    for idx, row in df1.iterrows():
        # Check for matches in df2
        for ref_id in [
            "Inhaber_RefID",
            "Rechnungsempfaenger_RefID",
            "Korrespondenzempfaenger_RefID",
        ]:
            matched_rows = df2[df2[ref_id] == row["ReferenceID"]]
            for _, matched_row in matched_rows.iterrows():
                role = ref_id.split("_")[0]  # Extracts the role from the column name
                fullid_value = produkte_dict.get(
                    matched_row["FullID"], matched_row["FullID"]
                )
                df1.at[idx, "Organisationsrollen"].append(f"{role} ({fullid_value})")
                df1.at[idx, "Organisationrollen_ProduktID"].append(
                    matched_row["Produkt_RefID"]
                )

    return df1
