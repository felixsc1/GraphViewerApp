import pandas as pd
import streamlit as st


# Define a Node class to represent each element in the hierarchy
class Node:
    def __init__(self, name, description, parent=None):
        self.name = name
        self.description = description
        self.parent = parent
        self.children = []


def build_tree(df):
    """
    Build a tree structure from the Excel DataFrame.
    Assumes columns 'Knoten 1' to 'Knoten 10' and 'Beschreibung des Knoteninhalts'.
    """
    # Create the root node from the first row
    root_name = df.iloc[0, 0]  # 'Knoten 1'
    root_description = df["Beschreibung des Knoteninhalts"].iloc[0]
    root = Node(root_name, root_description)

    # List to keep track of the current parent at each level (1-based indexing in Excel)
    current_parents = [root]

    # Process each row starting from the second one
    for index in range(1, len(df)):
        row = df.iloc[index]
        # Find the deepest non-empty level in this row
        max_level = 0
        for level in range(1, 11):  # Levels 1 to 10
            col_name = f"Knoten {level}"
            if pd.notna(row[col_name]):
                max_level = level

        if max_level == 0:
            continue  # Skip rows with no node information

        # Get the node name and description
        node_name = row[f"Knoten {max_level}"]
        description = row["Beschreibung des Knoteninhalts"]

        # Determine the parent (node at previous level)
        parent_level = max_level - 1
        if parent_level == 0:
            parent = root
        else:
            # Ensure we have enough parents in our list
            while len(current_parents) <= parent_level:
                # This shouldn't happen with well-formed data, but let's handle it
                current_parents.append(root)
            parent = current_parents[parent_level]

        # Create the new node
        new_node = Node(node_name, description, parent)
        parent.children.append(new_node)

        # Update current_parents list for this level and truncate any deeper levels
        while len(current_parents) <= max_level:
            current_parents.append(None)
        current_parents[max_level] = new_node
        # Remove any deeper levels as they are no longer valid parents
        if max_level < len(current_parents) - 1:
            current_parents = current_parents[: max_level + 1]

    return root


def search_tree(node, keyword):
    """
    Recursively search the tree for nodes matching the keyword in name or description.
    Returns a list of dictionaries with path and description.
    """
    results = []
    # Check if keyword matches name or description (case-insensitive)
    if (
        str(keyword).lower() in str(node.name).lower()
        or str(keyword).lower() in str(node.description).lower()
    ):
        path = get_path(node)
        results.append(
            {
                "path": " > ".join(path),  # Join path with ' > ' for readability
                "description": node.description,
                "node": node,  # Store node for future visualization
            }
        )

    # Recurse through children
    for child in node.children:
        results.extend(search_tree(child, keyword))

    return results


def get_path(node):
    """
    Get the full path from root to the given node using parent references.
    """
    path = []
    current = node
    while current:
        path.append(current.name)
        current = current.parent
    path.reverse()  # Root to leaf order
    return path


def get_all_node_names(node, name_set=None):
    """
    Recursively collect all unique node names in the tree.
    """
    if name_set is None:
        name_set = set()
    name_set.add(node.name)
    for child in node.children:
        get_all_node_names(child, name_set)
    return name_set


# Main application
def show():
    # Streamlit interface
    st.subheader("XML Schema Search Tool")

    # Load the Excel file
    uploaded_file = st.file_uploader("Upload Excel", type=["xlsx"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)

        # Build the tree
        root = build_tree(df)

        # Get all unique node names for multiselect options
        node_names = sorted(list(get_all_node_names(root)))

        # Search bar
        keyword = st.text_input("Enter search keyword:", "")

        # Initialize path_filters
        path_filters = []

        if keyword:
            # Perform search
            results = search_tree(root, keyword)

            # Get unique node names from paths in search results, ordered by appearance and excluding root node and keyword
            relevant_node_names = []
            seen = set()
            for result in results:
                path_nodes = result["path"].split(" > ")
                for node in path_nodes:
                    if (
                        node not in seen
                        and node != root.name
                        and str(keyword).lower() not in str(node).lower()
                    ):
                        relevant_node_names.append(node)
                        seen.add(node)

            # Multiselect for path filtering, only shown after keyword is entered
            path_filters = st.multiselect(
                "Filter by path (select multiple):", options=relevant_node_names
            )

            # Apply path filters if any
            if path_filters:
                filtered_results = []
                for result in results:
                    path_str = result["path"].lower()
                    if all(
                        filter_str.lower() in path_str for filter_str in path_filters
                    ):
                        filtered_results.append(result)
                results = filtered_results

            if results:
                st.write(
                    f"Found {len(results)} results for '{keyword}'{' with path filters: ' + ', '.join(path_filters) if path_filters else ''}:"
                )

                # Checkbox to hide first node
                hide_first_node = st.checkbox("Knoten 1 ausblenden", value=True)

                # Prepare results for display
                if hide_first_node:
                    results_df = pd.DataFrame(
                        [
                            {
                                "Path": (
                                    " > ".join(r["path"].split(" > ")[1:])
                                    if len(r["path"].split(" > ")) > 1
                                    else r["path"]
                                ),
                                "Description": r["description"],
                            }
                            for r in results
                        ]
                    )
                else:
                    results_df = pd.DataFrame(
                        [
                            {"Path": r["path"], "Description": r["description"]}
                            for r in results
                        ]
                    )
                st.dataframe(results_df)

            else:
                st.write(
                    f"No results found for '{keyword}'{' with path filters: ' + ', '.join(path_filters) if path_filters else ''}."
                )
