import streamlit as st
import pandas as pd
import os
import pickle
from graphviz import Digraph
import xml.etree.ElementTree as ET
from xml.dom import minidom
import streamlit.components.v1 as components
import hashlib
from collections import defaultdict
import re

def initialize_state():
    # Create workflows directory if it doesn't exist
    workflows_dir = os.path.join(st.session_state['cwd'], 'data', 'workflows')
    os.makedirs(workflows_dir, exist_ok=True)

    # Default user dictionary entry
    default_user_dict = {"3639e0c9-14a3-4021-9d95-c5ea60d296b6": "FFOG"}

    # Load existing dictionary from the pickle file, if possible
    pickle_path = os.path.join(workflows_dir, 'user_dict.pickle')
    loaded_dict = {}
    if os.path.exists(pickle_path):
        try:
            with open(pickle_path, 'rb') as f:
                loaded_dict = pickle.load(f)
            st.info(f"Loaded existing user dictionary with {len(loaded_dict)} entries")
        except Exception as e:
            st.error(f"Benutzerliste konnte nicht geladen werden: {str(e)}")

    # Always update the dictionary with the default entry
    loaded_dict.update(default_user_dict)
    st.session_state['user_dict'] = loaded_dict

def upload_user_list():
    uploaded_file = st.file_uploader("Upload Benutzerliste", type=["xlsx"])
    
    if uploaded_file is not None:
        try:
            # Read the second sheet of the Excel file
            df = pd.read_excel(uploaded_file, sheet_name=1, header=0)  # explicitly set header row
            
            # Get the actual column names
            transport_id_col = get_column_name(df.columns, 'TransportID')
            vorname_col = get_column_name(df.columns, 'Vorname')
            nachname_col = get_column_name(df.columns, 'Nachname')
            name_de_col = get_column_name(df.columns, 'Name:de')
            
            # Check if TransportID is found
            if not transport_id_col:
                st.error("Could not find column starting with: TransportID")
                return
            
            # Determine how to create user names
            # Option 1: Use Vorname + Nachname if both exist
            # Option 2: Otherwise use Name:de if it exists
            use_names = vorname_col and nachname_col
            use_name_de = name_de_col is not None
            
            if not (use_names or use_name_de):
                st.error("Could not find either (Vorname and Nachname) or Name:de columns")
                return
            
            # Load existing user_dict from session state or create new one
            user_dict = st.session_state.get('user_dict', {}).copy()
            
            # Add new entries to user_dict
            for _, row in df.iterrows():
                transport_id = row[transport_id_col]
                
                # Skip rows with missing TransportID
                if pd.isna(transport_id):
                    continue
                
                # Convert TransportID to string
                transport_id = str(transport_id)
                
                if use_names:
                    # First try Vorname + Nachname
                    if pd.notna(row[vorname_col]) and pd.notna(row[nachname_col]):
                        user_dict[transport_id] = f"{row[vorname_col]} {row[nachname_col]}"
                    # If either is missing but Name:de exists, use that instead
                    elif use_name_de and pd.notna(row[name_de_col]):
                        user_dict[transport_id] = row[name_de_col]
                # If we can't use names, try Name:de
                elif use_name_de and pd.notna(row[name_de_col]):
                    user_dict[transport_id] = row[name_de_col]
            
            # Store in session state
            st.session_state['user_dict'] = user_dict
            
            # Save to pickle file
            workflows_dir = os.path.join(st.session_state['cwd'], 'data', 'workflows')
            pickle_path = os.path.join(workflows_dir, 'user_dict.pickle')
            with open(pickle_path, 'wb') as f:
                pickle.dump(user_dict, f)
            
            st.success(f"Benutzerliste erfolgreich geladen mit {len(user_dict)} Einträgen")
            
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.exception(e)
            
def upload_dossier():
    uploaded_file = st.file_uploader("Upload Dossier", type=["xlsx"])
    if uploaded_file is not None:
        xls = pd.ExcelFile(uploaded_file)
        return xls
            
# --- Helper Functions ---
def extract_id(parent_str):
    """
    Extract the ID portion from a string by removing suffixes that start with ":" or "+".
    
    Args:
        parent_str: String potentially containing ID with suffixes
        
    Returns:
        Cleaned ID string or None if input is NaN
    """
    if pd.isna(parent_str):
        return None
        
    # First, strip suffix that starts with ":"
    result = parent_str.split(":", 1)[0]
    
    # Then, strip suffix that starts with "+"
    if "+" in result:
        result = result.split("+", 1)[0]
        
    return result.strip()

def get_column_name(columns, starts_with):
    """Helper function to find column that starts with given string"""
    matching_cols = [col for col in columns if col.startswith(starts_with)]
    if matching_cols:
        # Strip any leading/trailing whitespace characters from the column names
        return matching_cols[0].strip()
    return None

def resolve_empfaenger(xls, empfaenger_id):
    """
    Resolves an Empfänger ID to its actual value by looking it up in the "Empfänger" sheet.
    
    Args:
        xls: Excel file containing the "Empfänger" sheet
        empfaenger_id: The TransportID to look up
        
    Returns:
        Resolved empfänger value or the original ID if not found
    """
    if pd.isna(empfaenger_id):
        return None
        
    # Check if the "Empfänger" sheet exists
    if "Empfänger" not in xls.sheet_names:
        # Skip to final lookup in user_dict
        resolved_id = empfaenger_id
    else:
        # Read the Empfänger sheet
        empfaenger_df = pd.read_excel(xls, sheet_name="Empfänger")
        
        # Get the TransportID column
        transport_id_col = get_column_name(empfaenger_df.columns, "TransportID")
        if transport_id_col is None:
            # Skip to final lookup in user_dict
            resolved_id = empfaenger_id
        else:
            # Look for the row with matching TransportID
            matching_rows = empfaenger_df[empfaenger_df[transport_id_col] == empfaenger_id]
            if matching_rows.empty:
                # Skip to final lookup in user_dict
                resolved_id = empfaenger_id
            else:
                # Potential recipient columns to check
                recipient_cols = ["Benutzer", "Stelle", "Gruppe", "Verteiler", "DynamicRecipientIdentifier"]
                
                # Track if we found a value
                found_value = False
                
                # Look through all columns to find a non-empty value
                for col_pattern in recipient_cols:
                    col_name = get_column_name(empfaenger_df.columns, col_pattern)
                    if col_name is not None:
                        value = matching_rows[col_name].iloc[0]
                        if pd.notna(value):
                            # Clean the value by applying extract_id
                            resolved_id = extract_id(value)
                            found_value = True
                            break
                
                # If no value found in specified columns, check all columns
                if not found_value:
                    for col in empfaenger_df.columns:
                        if col != transport_id_col:  # Skip the TransportID column
                            value = matching_rows[col].iloc[0]
                            if pd.notna(value):
                                # Clean the value by applying extract_id
                                resolved_id = extract_id(value)
                                found_value = True
                                break
                
                # If no matching non-empty value found, use the original ID
                if not found_value:
                    resolved_id = empfaenger_id
    
    # FINAL STEP: Check if the ID exists in the user dictionary
    if 'user_dict' in st.session_state and resolved_id in st.session_state['user_dict']:
        return st.session_state['user_dict'][resolved_id]
    
    # If we get here, return the resolved_id (which might be the original ID if no match was found)
    return resolved_id

        
# --- Generating Workflow Tables ---


def build_activities_table(xls):
    """
    Builds an activities table from an Excel file by combining data from specified sheets.
    
    Returns:
    - pd.DataFrame: A DataFrame containing the activities table.
    """
    
    # Step 2: Define the common columns and activity types
    common_column_patterns = ["TransportID", "Name:de", "ParentActivity", "SequenceNumber"]
    activity_types = {
        "Aktivität": "manual",
        "Befehlsaktivität": "system"
    }
    
    # Step 3: Identify DialogPortal sheets
    dialog_portal_sheets = [sheet for sheet in xls.sheet_names if sheet.startswith("DialogPortal")]
    
    # Step 4: Initialize a list to collect DataFrames from each sheet
    activities_list = []
    
    # Step 5: Process each relevant sheet
    for sheet_name in xls.sheet_names:
        # Check if the sheet is relevant
        if sheet_name in activity_types or sheet_name in dialog_portal_sheets:
            # Read the sheet data
            df = pd.read_excel(xls, sheet_name=sheet_name)
            
            # Determine the activity type
            activity_type = activity_types.get(sheet_name, "script")  # "script" for DialogPortal sheets
            
            # Map column patterns to actual column names in the dataframe
            column_mapping = {pattern: get_column_name(df.columns, pattern) for pattern in common_column_patterns}
            
            # Verify that all common columns exist in the sheet
            missing_cols = [pattern for pattern, col in column_mapping.items() if col is None]
            if missing_cols:
                print(f"Warning: Sheet '{sheet_name}' is missing columns: {missing_cols}")
                continue  # Skip this sheet if critical columns are missing
            
            # Extract common columns
            temp_df = df[[column_mapping[pattern] for pattern in common_column_patterns]].copy()
            # Rename columns to standard names
            temp_df.columns = ["TransportID", "name", "parent", "SequenceNumber"]
            
            # Clean the parent column by applying extract_id to remove suffixes
            temp_df["parent"] = temp_df["parent"].apply(extract_id)
            
            # Add the activity type
            temp_df["type"] = activity_type
            
            # Add "Empfänger" for manual activities; set to None for others
            empfaenger_col = get_column_name(df.columns, "Empfänger")
            if sheet_name == "Aktivität" and empfaenger_col is not None:
                # Get the raw Empfänger IDs
                raw_empfaenger = df[empfaenger_col].apply(extract_id)
                
                # Resolve each Empfänger ID to its actual value
                temp_df["Empfänger"] = raw_empfaenger.apply(lambda x: resolve_empfaenger(xls, x))
            else:
                temp_df["Empfänger"] = None
            
            # Append to the list
            activities_list.append(temp_df)
    
    # Step 6: Combine all DataFrames into one
    if not activities_list:
        raise ValueError("No valid activity data found in the Excel file.")
    
    activities_df = pd.concat(activities_list, ignore_index=True)
    
    # Step 7: Check for duplicate TransportIDs
    if activities_df["TransportID"].duplicated().any():
        print("Warning: Duplicate TransportIDs found in the activities table.")
    else:
        print("All TransportIDs are unique.")
    
    # Step 7.5: Add substeps from "Manueller Arbeitsschritt" sheet
    activities_df["substeps"] = None  # Initialize the substeps column as None
    
    # Check if the "Manueller Arbeitsschritt" sheet exists
    if "Manueller Arbeitsschritt" in xls.sheet_names:
        # Read the sheet
        manual_steps_df = pd.read_excel(xls, sheet_name="Manueller Arbeitsschritt")
        
        # Get the column names using get_column_name
        activity_col = get_column_name(manual_steps_df.columns, "Activity")
        name_col = get_column_name(manual_steps_df.columns, "Name")
        
        # Check if both required columns exist
        if activity_col is not None and name_col is not None:
            # Clean the Activity column by applying extract_id to remove suffixes
            manual_steps_df["CleanActivity"] = manual_steps_df[activity_col].apply(extract_id)
            
            # Create a dictionary to store TransportID -> list of substep names
            substeps_dict = {}
            
            # Group by cleaned Activity and collect all associated Names
            for activity, group in manual_steps_df.groupby("CleanActivity"):
                if pd.notna(activity):  # Ensure activity is not NaN
                    # Collect all non-null Name values for this activity
                    substeps = [name for name in group[name_col] if pd.notna(name)]
                    if substeps:  # Only add if there are substeps
                        substeps_dict[activity] = "\n".join(substeps)
            
            # Apply the substeps to the activities dataframe
            for idx, row in activities_df.iterrows():
                transport_id = row["TransportID"]
                if transport_id in substeps_dict:
                    activities_df.at[idx, "substeps"] = substeps_dict[transport_id]
    
    # Step 8: Sort by parent and SequenceNumber for readability (optional)
    activities_df.sort_values(by=["parent", "SequenceNumber"], inplace=True)
    
    return activities_df


def build_groups_table(xls):
    """
    Builds a groups table from an Excel file by combining data from specified sheets.
    
    Returns:
    - pd.DataFrame: A DataFrame containing the groups table with all necessary details.
    """
    # Define group sheets and their types
    group_sheets = {
        "Prozess": "process",
        "Platzhalter für sequentielle Ak": "sequential",
        "Platzhalter für parallele Aktiv": "parallel"
    }

    # Initialize a list to collect group DataFrames
    groups_list = []

    # Process each group sheet
    for sheet_name, group_type in group_sheets.items():
        if sheet_name not in xls.sheet_names:
            print(f"Warning: Sheet '{sheet_name}' not found in the Excel file.")
            continue

        df = pd.read_excel(xls, sheet_name=sheet_name)
        
        # Map column patterns to actual column names in the dataframe
        required_columns = ["TransportID", "Name:de", "ParentActivity", "SequenceNumber"]
        column_mapping = {pattern: get_column_name(df.columns, pattern) for pattern in required_columns}
        
        # Verify that all common columns exist in the sheet
        missing_cols = [pattern for pattern, col in column_mapping.items() if col is None]
        if missing_cols:
            print(f"Warning: Sheet '{sheet_name}' is missing columns: {missing_cols}")
            continue  # Skip this sheet if critical columns are missing
        
        # Extract common columns
        temp_df = df[[column_mapping[pattern] for pattern in required_columns]].copy()
        # Rename columns to standard names
        temp_df.columns = ["id", "name", "parent", "SequenceNumber"]
        
        # Apply extract_id to parent column to clean it
        temp_df["parent"] = temp_df["parent"].apply(extract_id)
        
        temp_df["type"] = group_type

        # Initialize additional columns
        temp_df["skip_name"] = None
        temp_df["skip_condition"] = None
        temp_df["repeat_name"] = None
        temp_df["repeat_condition"] = None
        temp_df["Erledigungsmodus"] = None
        temp_df["parallel_condition_name"] = None
        temp_df["parallel_condition_expression"] = None

        # Preserve condition IDs if present (and clean them with extract_id)
        skip_col = get_column_name(df.columns, "Überspringen, falls")
        if skip_col is not None:
            temp_df["Überspringen, falls"] = df[skip_col].apply(extract_id)
            
        repeat_col = get_column_name(df.columns, "Wiederholen, falls")
        if repeat_col is not None:
            temp_df["Wiederholen, falls"] = df[repeat_col].apply(extract_id)
            
        erledigung_col = get_column_name(df.columns, "Erledigungsmodus")
        if group_type == "parallel" and erledigung_col is not None:
            temp_df["Erledigungsmodus"] = df[erledigung_col]

        groups_list.append(temp_df)

    # Combine all group DataFrames
    if not groups_list:
        raise ValueError("No valid group data found in the Excel file.")
    groups_df = pd.concat(groups_list, ignore_index=True)

    # Handle skip conditions
    skip_sheet = "Bedingung für das Überspringen "
    if skip_sheet in xls.sheet_names:
        skip_conditions = pd.read_excel(xls, skip_sheet)
        skip_transport_col = get_column_name(skip_conditions.columns, "TransportID")
        skip_name_col = get_column_name(skip_conditions.columns, "Anzeigen als")
        skip_expr_col = get_column_name(skip_conditions.columns, "Ausdruck")
        
        if all([skip_transport_col, skip_name_col, skip_expr_col]):
            skip_conditions_set = set(skip_conditions[skip_transport_col])
            
            # Create a dictionary of skip conditions for easier lookup
            skip_dict = {}
            for _, row in skip_conditions.iterrows():
                skip_id = row[skip_transport_col]
                if pd.notna(skip_id):
                    skip_dict[skip_id] = {
                        "name": row[skip_name_col],
                        "condition": row[skip_expr_col]
                    }
                        
            # Track how many matches we find
            matches_found = 0
            
            for idx, row in groups_df.iterrows():
                skip_id = row.get("Überspringen, falls")
                if pd.notna(skip_id):
                    if skip_id in skip_dict:
                        groups_df.at[idx, "skip_name"] = skip_dict[skip_id]["name"]
                        groups_df.at[idx, "skip_condition"] = skip_dict[skip_id]["condition"]
                        matches_found += 1

    # Handle repeat conditions
    repeat_sheet = "Bedingung für die Wiederholung "
    if repeat_sheet in xls.sheet_names:
        repeat_conditions = pd.read_excel(xls, repeat_sheet)
        repeat_transport_col = get_column_name(repeat_conditions.columns, "TransportID") 
        repeat_name_col = get_column_name(repeat_conditions.columns, "Anzeigen als")
        repeat_expr_col = get_column_name(repeat_conditions.columns, "Ausdruck")
        
        if all([repeat_transport_col, repeat_name_col, repeat_expr_col]):
            repeat_conditions_set = set(repeat_conditions[repeat_transport_col])
            
            # Create a dictionary of repeat conditions for easier lookup
            repeat_dict = {}
            for _, row in repeat_conditions.iterrows():
                repeat_id = row[repeat_transport_col]
                if pd.notna(repeat_id):
                    repeat_dict[repeat_id] = {
                        "name": row[repeat_name_col],
                        "condition": row[repeat_expr_col]
                    }
                        
            # Track how many matches we find
            matches_found = 0
            
            for idx, row in groups_df.iterrows():
                repeat_id = row.get("Wiederholen, falls")
                if pd.notna(repeat_id):
                    if repeat_id in repeat_dict:
                        groups_df.at[idx, "repeat_name"] = repeat_dict[repeat_id]["name"]
                        groups_df.at[idx, "repeat_condition"] = repeat_dict[repeat_id]["condition"]
                        matches_found += 1

    # Handle parallel group branch conditions
    if "Zweiginformation" in xls.sheet_names and "Bedingung für Zweig" in xls.sheet_names:
        branch_info = pd.read_excel(xls, "Zweiginformation")
        branch_conditions = pd.read_excel(xls, "Bedingung für Zweig")
        
        # Get column names using the pattern matching function
        parallel_col = get_column_name(branch_info.columns, "ParallelActivity")
        condition_col = get_column_name(branch_info.columns, "Condition")
        
        if all([parallel_col, condition_col]):
            # Clean IDs by applying extract_id to the condition column
            branch_info[condition_col] = branch_info[condition_col].apply(extract_id)
            # Also clean the parallel activity column
            branch_info[parallel_col] = branch_info[parallel_col].apply(extract_id)
        
        bc_transport_col = get_column_name(branch_conditions.columns, "TransportID")
        bc_name_col = get_column_name(branch_conditions.columns, "Anzeigen als")
        bc_expr_col = get_column_name(branch_conditions.columns, "Ausdruck")
        
        if all([parallel_col, condition_col, bc_transport_col, bc_name_col, bc_expr_col]):
            branch_conditions = branch_conditions.set_index(bc_transport_col)
            for idx, row in groups_df[groups_df["type"] == "parallel"].iterrows():
                group_id = row["id"]
                branches = branch_info[branch_info[parallel_col] == group_id]
                if not branches.empty:
                    condition_names = []
                    condition_expressions = []
                    for _, branch in branches.iterrows():
                        condition_id = branch.get(condition_col)
                        if pd.notna(condition_id) and condition_id in branch_conditions.index:
                            condition_names.append(branch_conditions.at[condition_id, bc_name_col])
                            condition_expressions.append(branch_conditions.at[condition_id, bc_expr_col])
                        else:
                            condition_names.append("")
                            condition_expressions.append("")
                    # Filter out empty condition names before joining with semicolons
                    non_empty_names = [name for name in condition_names if name]
                    if non_empty_names:
                        groups_df.at[idx, "parallel_condition_name"] = ";".join(map(str, non_empty_names))
                    else:
                        groups_df.at[idx, "parallel_condition_name"] = None
                    
                    # Create formatted string with name: expression pairs
                    formatted_expressions = []
                    for i in range(len(condition_names)):
                        if condition_names[i]:  # Only include non-empty names
                            formatted_expressions.append(f"{condition_names[i]}: {condition_expressions[i]}")
                    if formatted_expressions:
                        groups_df.at[idx, "parallel_condition_expression"] = "\n".join(formatted_expressions)
                    else:
                        groups_df.at[idx, "parallel_condition_expression"] = None

    # Clean up temporary columns
    groups_df.drop(columns=["Überspringen, falls", "Wiederholen, falls"], errors="ignore", inplace=True)

    # Validate group IDs
    if groups_df["id"].duplicated().any():
        print("Warning: Duplicate group IDs detected.")

    # Sort for readability
    groups_df.sort_values(by=["parent", "SequenceNumber"], inplace=True)

    return groups_df

# --- Generate Updated tables with additional BPMN nodes ---

def generate_additional_nodes(activities_table, groups_table):
    """
    Generates additional nodes (gateways, decision, rule) for:
    1. Parallel groups based on their Erledigungsmodus:
       - "AnyBranch": Adds decision node, rule node, and gateways with 'X' labels
       - "OnlyOneBranch": Adds decision node, rule node, and gateways with empty labels
       - "AllBranches": Adds only gateways with '+' labels (no decision or rule nodes)
    2. Groups with skip conditions:
       - Adds decision node, rule node, and gateways with 'X' labels
    3. Groups with repeat conditions:
       - Adds decision node, rule node, and a gateway with 'X' label that connects back 
         to the beginning of the group
    4. Activities with substeps:
       - Adds a substep node with the list of substeps as a label
    
    Parameters:
    - activities_table: pd.DataFrame with activities (indexed by TransportID)
    - groups_table: pd.DataFrame with groups (indexed by id)
    
    Returns:
    - updated_nodes_table: pd.DataFrame with all nodes (activities + additional nodes)
    - updated_groups_table: pd.DataFrame with updated SequenceNumbers
    """
    # Create a copy of activities_table to build the updated nodes table
    updated_nodes = activities_table.copy()
    updated_nodes['node_type'] = 'activity'  # Mark original activities
    
    # Create a copy of groups_table (no sequence number changes needed)
    updated_groups = groups_table.copy()
    
    # Track special connections for repeat conditions
    if 'repeat_connections' not in updated_groups.columns:
        updated_groups['repeat_connections'] = None
    
    # Helper function to generate unique node IDs
    def generate_node_id(base, properties=None):
        """Generate a stable ID based on node properties"""
        # Check if properties is an integer (backward compatibility)
        if isinstance(properties, int):
            return f"{base}_{properties}"
        elif properties:
            # Create a hash from properties that uniquely identify this node
            props_str = str(sorted(properties.items()))
            node_hash = hashlib.md5(props_str.encode()).hexdigest()[:8]
            return f"{base}_{node_hash}"
        else:
            # Fallback to counter-based approach
            if base + '_counter' not in st.session_state:
                st.session_state[base + '_counter'] = 0
            st.session_state[base + '_counter'] += 1
            return f"{base}_{st.session_state[base + '_counter']}"

    # Track substep nodes with a counter to ensure uniqueness
    substep_nodes_list = []

    for activity_id, activity in activities_table.iterrows():
        if pd.notna(activity.get('substeps')):
            # Use properties for unique IDs
            substep_node_id = generate_node_id('substeps', {'activity_id': activity_id})
            
            # Create a substep node
            substep_node = pd.Series({
                'node_type': 'substeps',
                'parent': activity_id,
                'SequenceNumber': -1,  # Not in main sequence
                'label': activity['substeps'],
                # Copy other relevant columns with None values
                'Empfänger': None,
                'name': None,
                'TransportID': None,
                'type': None
            }, name=substep_node_id)
            
            substep_nodes_list.append(substep_node)
    
    # Add all substep nodes to the updated_nodes table
    if substep_nodes_list:
        substep_nodes_df = pd.DataFrame(substep_nodes_list)
        updated_nodes = pd.concat([updated_nodes, substep_nodes_df])
    
    # Process groups with Erledigungsmodus
    eligible_groups = groups_table[
        (groups_table['Erledigungsmodus'] == 'AnyBranch') | 
        (groups_table['Erledigungsmodus'] == 'OnlyOneBranch') |
        (groups_table['Erledigungsmodus'] == 'AllBranches')
    ]
    
    for group_id in eligible_groups.index:
        # Get the erledigungsmodus for this group
        erledigungsmodus = groups_table.loc[group_id, 'Erledigungsmodus']
        
        # Identify child activities and subgroups of this group
        child_activities = activities_table[activities_table['parent'] == group_id]
        child_subgroups = groups_table[groups_table['parent'] == group_id]
        
        # Get existing sequence numbers of children
        existing_seq = pd.concat([child_activities['SequenceNumber'], 
                                 child_subgroups['SequenceNumber']]).sort_values()
        
        # Determine sequence numbers for new nodes
        min_seq = existing_seq.min() if not existing_seq.empty else 0
        max_seq = existing_seq.max() if not existing_seq.empty else 0
        
        # Handle different Erledigungsmodus types
        if erledigungsmodus == 'AllBranches':
            # For AllBranches, we only need gateway nodes with + symbol
            gateway_split_id = generate_node_id('gateway_split', {'group_id': group_id, 'type': 'split'})
            gateway_join_id = generate_node_id('gateway_join', {'group_id': group_id, 'type': 'join'})
            
            # Place gateways at the beginning and end
            gateway_split_seq = min_seq - 1  # Just before first child
            gateway_join_seq = max_seq + 1   # Just after last child
            
            # Create nodes dataframe for AllBranches (only gateways)
            new_nodes = pd.DataFrame({
                'node_id': [gateway_split_id, gateway_join_id],
                'node_type': ['gateway', 'gateway'],
                'parent': [group_id, group_id],
                'SequenceNumber': [gateway_split_seq, gateway_join_seq],
                'label': ['+', '+']  # Plus symbol for AllBranches
            }).set_index('node_id')
            
        else:
            # For AnyBranch and OnlyOneBranch, include decision and rule nodes
            # Check if there's a valid parallel_condition_expression
            has_condition_expr = pd.notna(groups_table.loc[group_id, 'parallel_condition_expression'])
            
            # For AnyBranch and OnlyOneBranch, always create decision and gateway nodes
            decision_node_id = generate_node_id('decision', {'group_id': group_id, 'type': erledigungsmodus})
            gateway_split_id = generate_node_id('gateway_split', {'group_id': group_id, 'type': erledigungsmodus})
            gateway_join_id = generate_node_id('gateway_join', {'group_id': group_id, 'type': erledigungsmodus})
            
            # Only create rule node if there's a condition expression
            if has_condition_expr:
                rule_node_id = generate_node_id('rule', {'group_id': group_id, 'type': erledigungsmodus})
                rule_seq = -1  # Rule not in main sequence
            
            # Place nodes in sequence
            decision_seq = min_seq - 2  # Decision comes before gateway
            gateway_split_seq = min_seq - 1  # Gateway split comes just before the first child
            gateway_join_seq = max_seq + 1  # Gateway join comes just after the last child
            
            # Set gateway labels based on the erledigungsmodus
            if erledigungsmodus == 'AnyBranch':
                gateway_split_label = 'X'  # Gateway split symbol for AnyBranch
                gateway_join_label = 'X'   # Gateway join symbol for AnyBranch
            else:  # OnlyOneBranch
                gateway_split_label = ''   # Empty diamond for OnlyOneBranch
                gateway_join_label = ''    # Empty diamond for OnlyOneBranch
            
            # Prepare node data for DataFrame
            node_ids = []
            node_types = []
            parent_activities = []
            sequence_numbers = []
            labels = []
            
            # Always add decision and gateway nodes
            node_ids.extend([decision_node_id, gateway_split_id, gateway_join_id])
            node_types.extend(['decision', 'gateway', 'gateway'])
            parent_activities.extend([group_id, group_id, group_id])
            sequence_numbers.extend([decision_seq, gateway_split_seq, gateway_join_seq])
            parallel_condition = groups_table.loc[group_id, 'parallel_condition_name']
            if pd.isna(parallel_condition) or str(parallel_condition) == "None":
                decision_label = "Entscheid"
            else:
                decision_label = "Entscheid\n" + str(parallel_condition).replace(';', '\n')
            labels.extend([
                decision_label,
                gateway_split_label,
                gateway_join_label
            ])
            
            # Add rule node only if there's a condition expression
            if has_condition_expr:
                node_ids.append(rule_node_id)
                node_types.append('rule')
                parent_activities.append(decision_node_id)
                sequence_numbers.append(rule_seq)
                labels.append(groups_table.loc[group_id, 'parallel_condition_expression'])
            
            # Create nodes dataframe for AnyBranch or OnlyOneBranch
            new_nodes = pd.DataFrame({
                'node_id': node_ids,
                'node_type': node_types,
                'parent': parent_activities,
                'SequenceNumber': sequence_numbers,
                'label': labels
            }).set_index('node_id')
        
        # Append new nodes to the updated table
        updated_nodes = pd.concat([updated_nodes, new_nodes])
    
    # Next, process groups with skip conditions
    skip_condition_groups = groups_table[
        groups_table['skip_name'].notna() | groups_table['skip_condition'].notna()
    ]
    
    for group_id in skip_condition_groups.index:
        # Skip if this group was already processed for Erledigungsmodus
        if group_id in eligible_groups.index:
            continue
            
        # Identify child activities and subgroups of this group
        child_activities = activities_table[activities_table['parent'] == group_id]
        child_subgroups = groups_table[groups_table['parent'] == group_id]
        
        # Get existing sequence numbers of children
        existing_seq = pd.concat([child_activities['SequenceNumber'], 
                                 child_subgroups['SequenceNumber']]).sort_values()
        
        # Determine sequence numbers for new nodes
        min_seq = existing_seq.min() if not existing_seq.empty else 0
        max_seq = existing_seq.max() if not existing_seq.empty else 0
        
        # Generate node IDs
        rule_node_id = generate_node_id('skip_rule', {'group_id': group_id})
        decision_node_id = generate_node_id('skip_decision', {'group_id': group_id})
        gateway_split_id = generate_node_id('skip_gateway_split', {'group_id': group_id})
        gateway_join_id = generate_node_id('skip_gateway_join', {'group_id': group_id})
        
        # Place nodes in sequence
        decision_seq = min_seq - 2  # Decision comes before gateway
        gateway_split_seq = min_seq - 1  # Gateway split comes just before the first child
        gateway_join_seq = max_seq + 1  # Gateway join comes just after the last child
        rule_seq = -1  # Rule not in main sequence
        
        # Get skip condition labels
        skip_name = groups_table.loc[group_id, 'skip_name']
        skip_condition = groups_table.loc[group_id, 'skip_condition']
        
        # Create nodes dataframe for skip condition
        new_nodes = pd.DataFrame({
            'node_id': [rule_node_id, decision_node_id, gateway_split_id, gateway_join_id],
            'node_type': ['rule', 'decision', 'gateway', 'gateway'],
            'parent': [decision_node_id, group_id, group_id, group_id],
            'SequenceNumber': [rule_seq, decision_seq, gateway_split_seq, gateway_join_seq],
            'label': [
                skip_condition if pd.notna(skip_condition) else '',
                "Überspringen, falls\n" + (skip_name if pd.notna(skip_name) else ''),
                'X',  # X symbol for skip gateway split
                'X'   # X symbol for skip gateway join
            ]
        }).set_index('node_id')
        
        # Append new nodes to the updated table
        updated_nodes = pd.concat([updated_nodes, new_nodes])
    
    # Finally, process groups with repeat conditions
    repeat_condition_groups = groups_table[
        groups_table['repeat_name'].notna() | groups_table['repeat_condition'].notna()
    ]
    
    for group_id in repeat_condition_groups.index:
        # Skip if this group was already processed for Erledigungsmodus
        if group_id in eligible_groups.index:
            continue
            
        # Identify child activities and subgroups of this group
        child_activities = activities_table[activities_table['parent'] == group_id]
        child_subgroups = groups_table[groups_table['parent'] == group_id]
        
        # Get existing sequence numbers of children
        existing_seq = pd.concat([child_activities['SequenceNumber'], 
                                 child_subgroups['SequenceNumber']]).sort_values()
        
        # Determine sequence numbers for new nodes
        min_seq = existing_seq.min() if not existing_seq.empty else 0
        max_seq = existing_seq.max() if not existing_seq.empty else 0
        
        # Generate node IDs
        rule_node_id = generate_node_id('repeat_rule', {'group_id': group_id})
        decision_node_id = generate_node_id('repeat_decision', {'group_id': group_id})
        gateway_node_id = generate_node_id('repeat_gateway', {'group_id': group_id})
        
        # As a target for the repeat, we'll use an invisible helper node at the beginning
        # This will allow us to connect back to the start of the group
        helper_node_id = generate_node_id('repeat_helper', {'group_id': group_id})
        
        # Place nodes in sequence
        # Helper node comes first, before any children
        helper_seq = min_seq - 1
        # Decision and gateway come at the end
        decision_seq = max_seq + 1  # Decision comes second-to-last
        gateway_seq = max_seq + 2   # Gateway comes last
        rule_seq = -1  # Rule not in main sequence (it's connected to the decision)
        
        # Get repeat condition labels
        repeat_name = groups_table.loc[group_id, 'repeat_name']
        repeat_condition = groups_table.loc[group_id, 'repeat_condition']
        
        # Create nodes dataframe for repeat condition
        new_nodes = pd.DataFrame({
            'node_id': [rule_node_id, decision_node_id, gateway_node_id, helper_node_id],
            'node_type': ['rule', 'decision', 'gateway', 'helper'],
            'parent': [decision_node_id, group_id, group_id, group_id],
            'SequenceNumber': [rule_seq, decision_seq, gateway_seq, helper_seq],
            'label': [
                repeat_condition if pd.notna(repeat_condition) else '',
                "Wiederholen, falls\n" + (repeat_name if pd.notna(repeat_name) else ''),
                'X',  # X symbol for gateway
                ''    # Empty label for helper node
            ]
        }).set_index('node_id')
        
        # Store the helper node ID to refer back to in add_group function
        updated_groups.at[group_id, 'repeat_connections'] = {
            'gateway': gateway_node_id,
            'helper': helper_node_id
        }
        
        # Append new nodes to the updated table
        updated_nodes = pd.concat([updated_nodes, new_nodes])
    
    # Sort by parent and SequenceNumber for correct flow
    updated_nodes.sort_values(by=['parent', 'SequenceNumber'], inplace=True)
    
    return updated_nodes, updated_groups

# --- Generate Edges Table ---

def build_edges_table(updated_nodes, updated_groups):
    """
    Builds a table of edges by traversing the group hierarchy, respecting sequential and parallel flows.

    Args:
        updated_nodes: DataFrame with node_id (index), parent, SequenceNumber, node_type
        updated_groups: DataFrame with group_id (index), parent, SequenceNumber, type, etc.
    Returns:
        DataFrame with columns: source, target
    """
    edges = []
    edge_set = set()  # Prevent duplicate edges

    def process_group(group_id, prev_node=None):
        """
        Process a group based on its type, returning first and last nodes for connection.
        """
        group = updated_groups.loc[group_id]
        children = []

        # Collect nodes and subgroups
        nodes = updated_nodes[updated_nodes['parent'] == group_id]
        for node_id in nodes.index:
            children.append(('node', node_id, nodes.at[node_id, 'SequenceNumber']))

        subgroups = updated_groups[updated_groups['parent'] == group_id]
        for subgroup_id in subgroups.index:
            children.append(('group', subgroup_id, subgroups.at[subgroup_id, 'SequenceNumber']))

        # Sort by SequenceNumber
        children.sort(key=lambda x: x[2])

        # Handle both 'sequential' and 'process' types similarly
        if get_safe_value_bpmn(group, 'type') in ['sequential', 'process']:
            first_node = None
            last_node = None
            local_prev = prev_node

            for child_type, child_id, _ in children:
                if child_type == 'node':
                    node_type = get_safe_value_bpmn(updated_nodes.loc[child_id], 'node_type')
                    # Skip special nodes in main flow
                    if node_type in ['substeps', 'rule']:
                        continue
                    if local_prev and (local_prev, child_id) not in edge_set:
                        edges.append((local_prev, child_id))
                        edge_set.add((local_prev, child_id))
                    local_prev = child_id
                    if first_node is None:
                        first_node = child_id
                    last_node = child_id
                elif child_type == 'group':
                    subgroup_first, subgroup_last = process_group(child_id, local_prev)
                    if subgroup_first:
                        if first_node is None:
                            first_node = subgroup_first
                        if local_prev and (local_prev, subgroup_first) not in edge_set:
                            edges.append((local_prev, subgroup_first))
                            edge_set.add((local_prev, subgroup_first))
                    if subgroup_last:
                        local_prev = subgroup_last
                        last_node = subgroup_last

            # Handle skip and repeat within sequential/process groups
            handle_skip(group, children)
            handle_repeat(group, children)
            return first_node, last_node

        elif get_safe_value_bpmn(group, 'type') == 'parallel':
            decision = split = join = None
            for c_type, c_id, seq in children:
                if c_type == 'node':
                    if 'decision' in c_id:
                        decision = c_id
                    elif 'gateway_split' in c_id and 'skip' not in c_id:
                        split = c_id
                    elif 'gateway_join' in c_id and 'skip' not in c_id:
                        join = c_id

            if not (decision and split and join):
                print(f"Warning: Parallel group {group_id} missing decision/split/join.")
                return None, None

            # Connect decision to split
            if (decision, split) not in edge_set:
                edges.append((decision, split))
                edge_set.add((decision, split))

            # Identify branches (between split and join)
            split_seq = next(seq for _, c_id, seq in children if c_id == split)
            join_seq = next(seq for _, c_id, seq in children if c_id == join)
            branches = [c for c in children if split_seq < c[2] < join_seq]

            for b_type, b_id, _ in branches:
                if b_type == 'node':
                    node_type = get_safe_value_bpmn(updated_nodes.loc[b_id], 'node_type')
                    if node_type in ['substeps', 'rule']:
                        continue
                    if (split, b_id) not in edge_set:
                        edges.append((split, b_id))
                        edge_set.add((split, b_id))
                    if (b_id, join) not in edge_set:
                        edges.append((b_id, join))
                        edge_set.add((b_id, join))
                elif b_type == 'group':
                    b_first, b_last = process_group(b_id)
                    if b_first and (split, b_first) not in edge_set:
                        edges.append((split, b_first))
                        edge_set.add((split, b_first))
                    if b_last and (b_last, join) not in edge_set:
                        edges.append((b_last, join))
                        edge_set.add((b_last, join))

            return decision, join

        else:
            print(f"Unknown group type: {get_safe_value_bpmn(group, 'type')}")
            return None, None

    def handle_skip(group, children):
        """Handle skip constructs within a group."""
        decision = split = join = activity = None
        for c_type, c_id, _ in children:
            if c_type == 'node':
                if 'skip_decision' in c_id:
                    decision = c_id
                elif 'skip_gateway_split' in c_id:
                    split = c_id
                elif 'skip_gateway_join' in c_id:
                    join = c_id
                elif get_safe_value_bpmn(updated_nodes.loc[c_id], 'node_type') == 'activity':
                    activity = c_id

        if decision and split and join and activity:
            if (decision, split) not in edge_set:
                edges.append((decision, split))
                edge_set.add((decision, split))
            if (split, activity) not in edge_set:
                edges.append((split, activity))
                edge_set.add((split, activity))
            if (activity, join) not in edge_set:
                edges.append((activity, join))
                edge_set.add((activity, join))
            if (split, join) not in edge_set:
                edges.append((split, join))
                edge_set.add((split, join))

    def handle_repeat(group, children):
        """Handle repeat constructs within a group."""
        decision = gateway = helper = activity = None
        for c_type, c_id, _ in children:
            if c_type == 'node':
                if 'repeat_decision' in c_id:
                    decision = c_id
                elif 'repeat_gateway' in c_id:
                    gateway = c_id
                elif 'repeat_helper' in c_id:
                    helper = c_id
                elif get_safe_value_bpmn(updated_nodes.loc[c_id], 'node_type') == 'activity':
                    activity = c_id

        if decision and gateway and helper and activity:
            if (helper, activity) not in edge_set:
                edges.append((helper, activity))
                edge_set.add((helper, activity))
            if (activity, decision) not in edge_set:
                edges.append((activity, decision))
                edge_set.add((activity, decision))
            if (decision, gateway) not in edge_set:
                edges.append((decision, gateway))
                edge_set.add((decision, gateway))
            if (gateway, helper) not in edge_set:
                edges.append((gateway, helper))
                edge_set.add((gateway, helper))

    # Process top-level group
    top_group_id = updated_groups[updated_groups['parent'].isna()].index[0]
    first_node, last_node = process_group(top_group_id)

    # Add start and end connections
    if first_node and ('start', first_node) not in edge_set:
        edges.append(('start', first_node))
        edge_set.add(('start', first_node))
    if last_node and (last_node, 'end') not in edge_set:
        edges.append((last_node, 'end'))
        edge_set.add((last_node, 'end'))

    # Add special node connections
    for node_id in updated_nodes.index:
        node_type = get_safe_value_bpmn(updated_nodes.loc[node_id], 'node_type')
        parent_id = get_safe_value_bpmn(updated_nodes.loc[node_id], 'parent')
        if node_type == 'substeps' and pd.notna(parent_id) and (parent_id, node_id) not in edge_set:
            edges.append((parent_id, node_id))
            edge_set.add((parent_id, node_id))
        elif node_type == 'rule' and pd.notna(parent_id) and (node_id, parent_id) not in edge_set:
            edges.append((node_id, parent_id))
            edge_set.add((node_id, parent_id))

    # Create edges DataFrame
    edges_df = pd.DataFrame(edges, columns=['source', 'target'])
    edges_df['label'] = None
    edges_df['style'] = 'solid_arrow'
    return edges_df


## -- Generate BPMN Diagram --

# Constants
ACTIVITY_TABLE_WIDTH = "180"
ACTIVITY_MAX_CHARS_PER_LINE = 20
ACTIVITY_FONT_SIZE = "14"
ACTIVITY_SMALL_FONT_SIZE = "12"
ACTIVITY_SMALL_MAX_CHARS_PER_LINE = 24
EDGE_MIN_LENGTH = '1.0'  # Define if not already present
EDGE_LABEL_DISTANCE = '2.0'  # Define if not already present
GRAPH_NODE_SEPARATION = '0.5'  # Define if not already present
GRAPH_RANK_SEPARATION = '0.5'  # Define if not already present

def wrap_text(text, max_chars_per_line):
    """Wrap text into lines not exceeding max_chars_per_line."""
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    for word in words:
        if current_length + len(word) + len(current_line) > max_chars_per_line:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = []
                current_length = 0
            else:
                lines.append(word)
                continue
        current_line.append(word)
        current_length += len(word)
    if current_line:
        lines.append(' '.join(current_line))
    return lines

def get_port(node_id, updated_nodes, direction):
    """Return the port for edge connections based on node type and direction."""
    if node_id in updated_nodes.index:
        try:
            # Handle Series objects safely
            node_type = updated_nodes.loc[node_id, 'node_type']
            if hasattr(node_type, 'iloc'):
                node_type = node_type.iloc[0]
                
            if isinstance(node_type, str) and node_type == 'activity':
                return ':w' if direction == 'in' else ':e'
        except (IndexError, KeyError, AttributeError):
            # If any error occurs, return default empty string
            pass
    return ''

def add_node(dot, node_id, node, edge_set, updated_nodes):
    """Add a node to the Graphviz diagram based on its type."""
    # Get node_type and handle if it's a Series
    node_type = node['node_type']
    if hasattr(node_type, 'iloc'):
        node_type = node_type.iloc[0]
    
    label_value = get_safe_value_bpmn(node, 'label', '')
    label = str(label_value)
    
    if is_node_type(node_type, 'rule'):
        if node_id.startswith('repeat_rule') or node_id.startswith('skip_rule'):
            label = f"📄\n{label}"
        dot.node(node_id, label=label, shape='none')
        parent_activity = get_safe_value_bpmn(node, 'parent', '')
        if parent_activity and (node_id, parent_activity) not in edge_set:
            dot.edge(node_id, parent_activity, style='dotted')
            edge_set.add((node_id, parent_activity))
        return False
    
    elif is_node_type(node_type, 'substeps'):
        dot.node(
            node_id,
            label=label,
            shape='none',
            style='',
            fontsize='14',
            align='left',
            group=get_safe_value_bpmn(node, 'parent', '')
        )
        parent_activity = get_safe_value_bpmn(node, 'parent', '')
        if parent_activity and (parent_activity, node_id) not in edge_set:
            dot.edge(
                parent_activity,
                node_id,
                style='dotted',
                dir='none',
                color='black',
                weight='3.0',
                len='0.8'
            )
            edge_set.add((parent_activity, node_id))
        return False
    else:
        if is_node_type(node_type, 'activity'):
            empfanger = get_safe_value_bpmn(node, 'Empfänger', '')
            name_de = get_safe_value_bpmn(node, 'name', '')
            activity_type = get_safe_value_bpmn(node, 'type', '')
            
            emoji = ''
            if activity_type == 'manual':
                emoji = '👤 '
            elif activity_type == 'system':
                emoji = '⚙️ '
            elif activity_type == 'script':
                emoji = '📜 '
            
            formatted_empfanger = f"{emoji}{empfanger}" if empfanger else emoji
            
            wrapped_lines = wrap_text(name_de, ACTIVITY_MAX_CHARS_PER_LINE)
            if len(wrapped_lines) > 2:
                font_size = ACTIVITY_SMALL_FONT_SIZE
                wrapped_lines_small = wrap_text(name_de, ACTIVITY_SMALL_MAX_CHARS_PER_LINE)
                if len(wrapped_lines_small) > 2:
                    wrapped_lines = wrapped_lines_small[:2]
                    wrapped_lines[-1] += " ..."
                else:
                    wrapped_lines = wrapped_lines_small
            else:
                font_size = ACTIVITY_FONT_SIZE
            
            formatted_name = '<BR/>'.join(wrapped_lines)
            
            html_label = f'''<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="6" WIDTH="{ACTIVITY_TABLE_WIDTH}">
<TR><TD ALIGN="left" VALIGN="top"><FONT POINT-SIZE="{ACTIVITY_FONT_SIZE}">{formatted_empfanger}</FONT></TD></TR>
<TR><TD ALIGN="center"><FONT POINT-SIZE="{font_size}">{formatted_name}</FONT></TD></TR>
</TABLE>>''' 
            label = html_label
        elif is_node_type(node_type, 'helper'):
            label = ''
        attrs = {}
        if is_node_type(node_type, 'gateway'):
            attrs['fontsize'] = '16'
            attrs['shape'] = 'diamond'
        elif is_node_type(node_type, 'helper'):
            attrs['width'] = '0.1'
            attrs['height'] = '0.1'
            attrs['shape'] = 'point'
        elif is_node_type(node_type, 'activity'):
            attrs['shape'] = 'box'
            attrs['style'] = 'rounded'
            attrs['margin'] = '0'
            attrs['group'] = node_id
        else:
            attrs['shape'] = 'box'
        dot.node(node_id, label=label, **attrs)
        return True

def is_node_type(value, type_to_check):
    """Safely check if a node type equals a specific value, handling Series."""
    if pd.isna(value):
        return False
        
    # If it's a Series, extract the first value
    if hasattr(value, 'iloc'):
        try:
            value = value.iloc[0]
        except (IndexError, AttributeError):
            return False
            
    return value == type_to_check

def add_group(group_id, dot, updated_nodes, updated_groups, edge_set, processed_substeps=None):
    """Build a group in the BPMN diagram recursively."""
    if processed_substeps is None:
        processed_substeps = set()
    
    group = updated_groups.loc[group_id]
    children = []
    group_name = get_safe_value_bpmn(group, 'name')
    
    nodes = updated_nodes[updated_nodes['parent'] == group_id]
    for node_id in nodes.index:
        seq_num = get_safe_value_bpmn(nodes.loc[node_id], 'SequenceNumber', 0)
        children.append(('node', node_id, seq_num))

    # Find decision node IDs safely
    decision_ids = []
    for node_id in nodes.index:
        node_type = get_safe_value_bpmn(nodes.loc[node_id], 'node_type')
        if is_node_type(node_type, 'decision'):
            decision_ids.append(node_id)
    
    for decision_id in decision_ids:
        # Find rule nodes connected to this decision
        rule_ids = []
        for node_id in updated_nodes[updated_nodes['parent'] == decision_id].index:
            node_type = get_safe_value_bpmn(updated_nodes.loc[node_id], 'node_type')
            if is_node_type(node_type, 'rule'):
                rule_ids.append(node_id)
        for rule_id in rule_ids:
            seq_num = get_safe_value_bpmn(updated_nodes.loc[rule_id], 'SequenceNumber', 0)
            children.append(('node', rule_id, seq_num))

    # Find activity node IDs safely
    activity_ids = []
    for node_id in nodes.index:
        node_type = get_safe_value_bpmn(nodes.loc[node_id], 'node_type')
        if is_node_type(node_type, 'activity'):
            activity_ids.append(node_id)
    
    for activity_id in activity_ids:
        # Find substep nodes connected to this activity
        substep_ids = []
        for node_id in updated_nodes[updated_nodes['parent'] == activity_id].index:
            node_type = get_safe_value_bpmn(updated_nodes.loc[node_id], 'node_type')
            if is_node_type(node_type, 'substeps'):
                substep_ids.append(node_id)
        for substep_id in substep_ids:
            if substep_id not in processed_substeps:
                processed_substeps.add(substep_id)
                seq_num = get_safe_value_bpmn(updated_nodes.loc[substep_id], 'SequenceNumber', 0)
                children.append(('node', substep_id, seq_num))

    subgroups = updated_groups[updated_groups['parent'] == group_id]
    for subgroup_id in subgroups.index:
        seq_num = get_safe_value_bpmn(subgroups.loc[subgroup_id], 'SequenceNumber', 0)
        children.append(('group', subgroup_id, seq_num))

    children.sort(key=lambda x: x[2])
    
    gateway_split = gateway_join = skip_gateway_split = skip_gateway_join = repeat_gateway = repeat_helper = None
    parallel_branches = []
    gateway_connected_nodes = set()
    
    # Safely get group type
    group_type = get_safe_value_bpmn(group, 'type')
    
    # Safely get parallel condition names and compute labels
    parallel_condition_name = get_safe_value_bpmn(group, 'parallel_condition_name')
    labels = parallel_condition_name.split(';') if group_type == 'parallel' and parallel_condition_name else []
    
    # Safely get repeat connections
    repeat_connections = get_safe_value_bpmn(group, 'repeat_connections')
    if repeat_connections:
        if isinstance(repeat_connections, dict):
            repeat_gateway = repeat_connections.get('gateway')
            repeat_helper = repeat_connections.get('helper')
        elif isinstance(repeat_connections, str) and "gateway" in repeat_connections:
            import ast
            try:
                repeat_dict = ast.literal_eval(repeat_connections)
                repeat_gateway = repeat_dict.get('gateway')
                repeat_helper = repeat_dict.get('helper')
            except:
                repeat_gateway = repeat_helper = None
    
    for child_type, child_id, _ in children:
        if child_type == 'node':
            # Safely get node_type for further checks
            node_type = get_safe_value_bpmn(updated_nodes.loc[child_id], 'node_type')
            if is_node_type(node_type, 'gateway'):
                if 'gateway_split' in child_id and 'skip' not in child_id:
                    gateway_split = child_id
                elif 'gateway_join' in child_id and 'skip' not in child_id:
                    gateway_join = child_id
                elif 'skip_gateway_split' in child_id:
                    skip_gateway_split = child_id
                elif 'skip_gateway_join' in child_id:
                    skip_gateway_join = child_id
        
    if group_type == 'parallel' and gateway_split and gateway_join:
        split_seq = get_safe_value_bpmn(updated_nodes.loc[gateway_split], 'SequenceNumber', 0)
        join_seq = get_safe_value_bpmn(updated_nodes.loc[gateway_join], 'SequenceNumber', float('inf'))
        parallel_branches = [child for child in children if split_seq < child[2] < join_seq]
    
    prev_node = first_node = last_node = first_real_node = None
    for child in children:
        child_type, child_id, _ = child
        if child_type == 'node':
            node = updated_nodes.loc[child_id]
            in_flow = add_node(dot, child_id, node, edge_set, updated_nodes)
            if in_flow:
                if first_node is None:
                    first_node = child_id
                node_type = get_safe_value_bpmn(node, 'node_type')
                if first_real_node is None and not is_node_type(node_type, 'helper'):
                    first_real_node = child_id
                last_node = child_id
                if prev_node and (prev_node, child_id) not in edge_set:
                    if group_type != 'parallel' or (prev_node not in gateway_connected_nodes and child_id not in gateway_connected_nodes):
                        from_port = get_port(prev_node, updated_nodes, 'out')
                        to_port = get_port(child_id, updated_nodes, 'in')
                        dot.edge(prev_node + from_port, child_id + to_port, minlen=EDGE_MIN_LENGTH, weight='2', constraint='true')
                        edge_set.add((prev_node, child_id))
                prev_node = child_id
        elif child_type == 'group':
            with dot.subgraph(name=f'cluster_{child_id}') as sub_dot:
                subgroup_name = get_safe_value_bpmn(updated_groups.loc[child_id], "name", "")
                sub_dot.attr(
                    label=f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="2"><TR><TD ALIGN="left"><B>{subgroup_name}</B></TD></TR></TABLE>>',
                    style='rounded,dashed',
                    penwidth='1.0',
                    labelloc='t',
                    labeljust='l',
                    margin='10',
                    fontname='sans-serif'
                )
                subgroup_first, subgroup_last = add_group(child_id, sub_dot, updated_nodes, updated_groups, edge_set, processed_substeps)
            if subgroup_first and subgroup_last:
                if first_node is None:
                    first_node = subgroup_first
                if first_real_node is None:
                    first_real_node = subgroup_first
                last_node = subgroup_last
                if group_type == 'parallel' and (child, child_id, _) in parallel_branches:
                    idx = parallel_branches.index((child, child_id, _))
                    label = labels[idx] if idx < len(labels) else None
                    if gateway_split and (gateway_split, subgroup_first) not in edge_set:
                        from_port = ''
                        to_port = get_port(subgroup_first, updated_nodes, 'in')
                        dot.edge(gateway_split + from_port, subgroup_first + to_port, xlabel=label, labelangle='0', labeldistance=EDGE_LABEL_DISTANCE, minlen=str(float(EDGE_MIN_LENGTH) + 0.2), weight='2', constraint='true')
                        edge_set.add((gateway_split, subgroup_first))
                        gateway_connected_nodes.add(subgroup_first)
                    if gateway_join and (subgroup_last, gateway_join) not in edge_set:
                        from_port = get_port(subgroup_last, updated_nodes, 'out')
                        to_port = ''
                        dot.edge(subgroup_last + from_port, gateway_join + to_port, minlen=EDGE_MIN_LENGTH, weight='2', constraint='true')
                        edge_set.add((subgroup_last, gateway_join))
                        gateway_connected_nodes.add(subgroup_last)
                elif prev_node and (prev_node, subgroup_first) not in edge_set:
                    if prev_node not in gateway_connected_nodes and subgroup_first not in gateway_connected_nodes:
                        from_port = get_port(prev_node, updated_nodes, 'out')
                        to_port = get_port(subgroup_first, updated_nodes, 'in')
                        dot.edge(prev_node + from_port, subgroup_first + to_port, minlen=EDGE_MIN_LENGTH, weight='2', constraint='true')
                        edge_set.add((prev_node, subgroup_first))
                prev_node = subgroup_last
    
    if group_type == 'parallel' and gateway_split and gateway_join:
        for i, branch in enumerate(parallel_branches):
            if branch[0] == 'node':
                node_id = branch[1]
                label = labels[i] if i < len(labels) else None
                if (gateway_split, node_id) not in edge_set:
                    from_port = ''
                    to_port = get_port(node_id, updated_nodes, 'in')
                    dot.edge(gateway_split + from_port, node_id + to_port, xlabel=label, labelangle='0', labeldistance=EDGE_LABEL_DISTANCE, minlen=str(float(EDGE_MIN_LENGTH) + 0.2), weight='2', constraint='true')
                    edge_set.add((gateway_split, node_id))
                    gateway_connected_nodes.add(node_id)
                if (node_id, gateway_join) not in edge_set:
                    from_port = get_port(node_id, updated_nodes, 'out')
                    to_port = ''
                    dot.edge(node_id + from_port, gateway_join + to_port, minlen=EDGE_MIN_LENGTH, weight='2', constraint='true')
                    edge_set.add((node_id, gateway_join))
                    gateway_connected_nodes.add(node_id)
    
    if skip_gateway_split and skip_gateway_join and (skip_gateway_split, skip_gateway_join) not in edge_set:
        skip_name = get_safe_value_bpmn(group, 'skip_name')
        label = skip_name if skip_name else None
        dot.edge(skip_gateway_split, skip_gateway_join, xlabel=label, labelangle='0', labeldistance=EDGE_LABEL_DISTANCE, constraint='false', minlen=str(float(EDGE_MIN_LENGTH) + 0.5), weight='1')
        edge_set.add((skip_gateway_split, skip_gateway_join))
    
    if repeat_gateway and repeat_helper and (repeat_gateway, repeat_helper) not in edge_set:
        repeat_name = get_safe_value_bpmn(group, 'repeat_name')
        label = repeat_name if repeat_name else None
        dot.edge(repeat_gateway, repeat_helper, xlabel=label, labelangle='0', labeldistance=EDGE_LABEL_DISTANCE, constraint='false', minlen=str(float(EDGE_MIN_LENGTH) + 0.5), weight='1')
        edge_set.add((repeat_gateway, repeat_helper))
    if repeat_helper and first_real_node and (repeat_helper, first_real_node) not in edge_set:
        from_port = get_port(repeat_helper, updated_nodes, 'out')
        to_port = get_port(first_real_node, updated_nodes, 'in')
        dot.edge(repeat_helper + from_port, first_real_node + to_port, minlen=EDGE_MIN_LENGTH, weight='2', constraint='true')
        edge_set.add((repeat_helper, first_real_node))
    
    return first_node, last_node

def build_workflow_diagram(updated_nodes, updated_groups):
    """Generate the complete BPMN diagram."""
    dot = Digraph(format='svg', 
                  graph_attr={
                      'rankdir': 'LR', 
                      'splines': 'ortho', 
                      'fontname': 'sans-serif',
                      'nodesep': GRAPH_NODE_SEPARATION,
                      'ranksep': GRAPH_RANK_SEPARATION,
                      'overlap': 'false',
                      'sep': '+5',
                      'margin': '0.1',
                      'concentrate': 'true',
                      'ordering': 'out',
                      'newrank': 'true'
                  },
                  node_attr={'fontname': 'sans-serif', 'margin': '0.1'}, 
                  edge_attr={'fontname': 'sans-serif', 'weight': '2'})
    
    with dot.subgraph(name='cluster_flow_control') as flow:
        flow.attr(style='invis')
        flow.node('rank_start', style='invis', shape='none', width='0')
        flow.node('rank_end', style='invis', shape='none', width='0')
        flow.edge('rank_start', 'rank_end', style='invis')
    
    dot.node('start', shape='circle', label='', width='0.5', height='0.5', rank='source')
    dot.node('end', shape='circle', label='', width='0.5', height='0.5', rank='sink')
    
    dot.edge('rank_start', 'start', style='invis', weight='100')
    dot.edge('rank_end', 'end', style='invis', weight='100')
    
    edge_set = set()
    top_group_id = updated_groups[updated_groups['parent'].isna()].index[0]
    
    with dot.subgraph(name=f'cluster_{top_group_id}') as c:
        c.attr(
            label=f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="2"><TR><TD ALIGN="left"><B>{updated_groups.at[top_group_id, "name"]}</B></TD></TR></TABLE>>',
            style='rounded,dashed',
            penwidth='1.5',
            labelloc='t',
            labeljust='l',
            margin='10',
            fontname='sans-serif'
        )
        first_node, last_node = add_group(top_group_id, c, updated_nodes, updated_groups, edge_set, set())

    from_port = ''
    to_port = get_port(first_node, updated_nodes, 'in')
    dot.edge('start' + from_port, first_node + to_port, minlen='0.8', weight='10', constraint='true')
    
    from_port = get_port(last_node, updated_nodes, 'out')
    to_port = ''
    dot.edge(last_node + from_port, 'end' + to_port, minlen='0.8', weight='10', constraint='true')
    
    return dot

# --- BPMN XML HELPER FUNCTIONS ---


def get_safe_value_bpmn(data, key, default='something'):
    """Safely get a value from a data row, handling Series or scalar."""
    value = data.get(key, default)
    if isinstance(value, pd.Series):
        return value.iloc[0] if not value.empty else default
    return value if pd.notna(value) else default

def is_node_type(node_type, target_type):
    """Check if node_type matches or contains target_type."""
    return str(node_type).lower() == target_type.lower() or target_type.lower() in str(node_type).lower()


# Function to encode file as base64 (for embedding JS)
import base64
def get_base64_of_file(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


# --- BPMN XML ---

def create_main_flow_bpmn_xml(node_df, edges_df):
    # Define namespaces
    namespaces = {
        "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
        "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
        "dc": "http://www.omg.org/spec/DD/20100524/DC",
        "di": "http://www.omg.org/spec/DD/20100524/DI",
        "xsi": "http://www.w3.org/2001/XMLSchema-instance"
    }
    
    # Register namespaces
    for prefix, uri in namespaces.items():
        ET.register_namespace(prefix, uri)

    # Create root element
    root = ET.Element("bpmn:definitions", {
        "id": "definitions_1",
        "targetNamespace": "http://bpmn.io/schema/bpmn",
        "xmlns:bpmn": namespaces["bpmn"],
        "xmlns:bpmndi": namespaces["bpmndi"],
        "xmlns:dc": namespaces["dc"],
        "xmlns:di": namespaces["di"],
        "xmlns:xsi": namespaces["xsi"]
    })

    # Create process element
    process = ET.SubElement(root, "bpmn:process", {"id": "process_1", "isExecutable": "true"})

    # Identify connected nodes (nodes with edges)
    connected_nodes = set(edges_df["source"]).union(set(edges_df["target"]))
    connected_nodes.discard("start")
    connected_nodes.discard("end")

    # Filter main flow nodes (exclude "rule" and "substeps")
    flow_nodes = [n for n in connected_nodes if get_safe_value_bpmn(node_df.loc[n], "node_type", "") not in ["rule", "substeps"]]

    # Create ID mapping for flow nodes and start/end
    id_mapping = {}
    for node_id in flow_nodes + ["start", "end"]:
        cleaned_id = "id_" + node_id.replace("-", "").replace("_", "") if node_id in connected_nodes else f"id_{node_id}"
        id_mapping[node_id] = cleaned_id
    reverse_id_mapping = {v: k for k, v in id_mapping.items()}

    # Filter edges for sequence flows (only between flow nodes)
    flow_edges = edges_df[
        (edges_df["source"].isin(flow_nodes + ["start"])) &
        (edges_df["target"].isin(flow_nodes + ["end"]))
    ]

    # Track incoming and outgoing sequence flows
    incoming_flows = {id_mapping[n]: [] for n in flow_nodes + ["start", "end"]}
    outgoing_flows = {id_mapping[n]: [] for n in flow_nodes + ["start", "end"]}

    # Create sequence flows and track them
    sequence_flows = []
    for idx, edge in flow_edges.iterrows():
        source = id_mapping[edge["source"]]
        target = id_mapping[edge["target"]]
        flow_id = f"flow_{idx}"
        sequence_flows.append({"id": flow_id, "source": source, "target": target, "label": edge["label"]})
        outgoing_flows[source].append(flow_id)
        incoming_flows[target].append(flow_id)

    # Create elements for flow nodes
    element_mapping = {}
    for node_id in flow_nodes:
        cleaned_id = id_mapping[node_id]
        node_data = node_df.loc[node_id]
        node_type = get_safe_value_bpmn(node_data, "node_type", "")
        name = get_safe_value_bpmn(node_data, "name", "")
        label = get_safe_value_bpmn(node_data, "label", "")

        if is_node_type(node_type, "activity"):
            task_type = get_safe_value_bpmn(node_data, "type", "")
            if task_type == "manual":
                element = ET.SubElement(process, "bpmn:userTask", {"id": cleaned_id, "name": name})
            elif task_type in ["system", "script"]:
                element = ET.SubElement(process, "bpmn:scriptTask", {"id": cleaned_id, "name": name})
            else:
                element = ET.SubElement(process, "bpmn:task", {"id": cleaned_id, "name": name})
        elif is_node_type(node_type, "decision"):
            element = ET.SubElement(process, "bpmn:businessRuleTask", {"id": cleaned_id, "name": label or name})
        elif is_node_type(node_type, "gateway"):
            gateway_label = label if pd.notna(label) else ""
            gateway_type = "bpmn:parallelGateway" if gateway_label == "+" else "bpmn:exclusiveGateway"
            element = ET.SubElement(process, gateway_type, {"id": cleaned_id})
        elif is_node_type(node_type, "helper"):
            element = ET.SubElement(process, "bpmn:intermediateThrowEvent", {"id": cleaned_id})
        else:
            element = ET.SubElement(process, "bpmn:task", {"id": cleaned_id, "name": name})

        for flow_id in incoming_flows.get(cleaned_id, []):
            ET.SubElement(element, "bpmn:incoming").text = flow_id
        for flow_id in outgoing_flows.get(cleaned_id, []):
            ET.SubElement(element, "bpmn:outgoing").text = flow_id
        element_mapping[cleaned_id] = element

    # Add start and end events
    start_element = ET.SubElement(process, "bpmn:startEvent", {"id": id_mapping["start"]})
    for flow_id in outgoing_flows[id_mapping["start"]]:
        ET.SubElement(start_element, "bpmn:outgoing").text = flow_id

    end_element = ET.SubElement(process, "bpmn:endEvent", {"id": id_mapping["end"]})
    for flow_id in incoming_flows[id_mapping["end"]]:
        ET.SubElement(end_element, "bpmn:incoming").text = flow_id

    # Add sequence flows to process
    for flow in sequence_flows:
        flow_element = ET.SubElement(process, "bpmn:sequenceFlow", {
            "id": flow["id"],
            "sourceRef": flow["source"],
            "targetRef": flow["target"]
        })
        if pd.notna(flow["label"]):
            source_orig = reverse_id_mapping[flow["source"]]
            if source_orig in node_df.index and is_node_type(node_df.loc[source_orig, "node_type"], "gateway"):
                condition = ET.SubElement(flow_element, "bpmn:conditionExpression", {"xsi:type": "bpmn:tFormalExpression"})
                condition.text = str(flow["label"])

    # Create diagram
    diagram = ET.SubElement(root, "bpmndi:BPMNDiagram", {"id": "BPMNDiagram_1"})
    plane = ET.SubElement(diagram, "bpmndi:BPMNPlane", {"id": "BPMNPlane_1", "bpmnElement": "process_1"})
    node_positions = {}

    # Position flow nodes minimally (horizontal line)
    x_pos = 50
    for node_id in ["start"] + flow_nodes + ["end"]:
        cleaned_id = id_mapping[node_id]
        if node_id in ["start", "end"] or is_node_type(node_df.loc[node_id, "node_type"], "helper"):
            width, height = 36, 36
        elif is_node_type(node_df.loc[node_id, "node_type"], "gateway"):
            width, height = 50, 50
        else:
            width, height = 100, 80
        node_positions[cleaned_id] = {"x": x_pos, "y": 100, "width": width, "height": height}
        x_pos += 150

    # Create shapes
    for element_id, pos in node_positions.items():
        shape = ET.SubElement(plane, "bpmndi:BPMNShape", {"id": f"{element_id}_di", "bpmnElement": element_id})
        ET.SubElement(shape, "dc:Bounds", {k: str(v) for k, v in pos.items()})

    # Create sequence flow edges (no waypoints, let layout engine handle)
    for flow in sequence_flows:
        ET.SubElement(plane, "bpmndi:BPMNEdge", {"id": f"{flow['id']}_di", "bpmnElement": flow["id"]})

    # Format XML
    rough_string = ET.tostring(root, "utf-8")
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")
    return pretty_xml

# --- Generate BPMN Diagram ---

def get_base64_of_file(file_path):
    import base64
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


def process_bpmn_layout(basic_xml):
    """
    Process the BPMN XML with auto-layout and return the result.
    
    Args:
        basic_xml (str): The basic BPMN XML to process
        
    Returns:
        str: The processed BPMN XML with layout information
    """
    import os
    import uuid
    import streamlit as st
    import streamlit.components.v1 as components
    
    # Load bpmn-auto-layout.js
    js_path = os.path.join(st.session_state['cwd'], "js/bpmn-auto-layout.js")
    
    # Encode JS file as base64 to embed in HTML
    js_base64 = get_base64_of_file(js_path)

    # Escape XML for JavaScript
    xml_output_escaped = basic_xml.replace("'", "\\'").replace("\n", "\\n")
    
    # Create a container for the processed XML
    layout_container = st.container()
    with layout_container:
        result_placeholder = st.empty()
        status_placeholder = st.empty()
        status_placeholder.info("Processing layout...")
    
    # Create unique key for this session
    if 'bpmn_layout_key' not in st.session_state:
        st.session_state['bpmn_layout_key'] = str(uuid.uuid4())
    layout_key = st.session_state['bpmn_layout_key']
    
    # HTML with JS to run layout and store in page
    html_content = f"""
    <html>
    <body>
        <script src="data:text/javascript;base64,{js_base64}"></script>
        <textarea id="bpmn_layout_result_{layout_key}" style="display:none;"></textarea>
        <script>
            const inputXML = '{xml_output_escaped}';
            
            // Run layout process - use the exported BpmnAutoLayout global object
            BpmnAutoLayout.layoutProcess(inputXML)
                .then(layoutedXML => {{
                    // Store the result in the hidden textarea
                    document.getElementById('bpmn_layout_result_{layout_key}').value = layoutedXML;
                    
                    // Signal completion to Streamlit
                    const event = new CustomEvent('streamlit:message', {{ 
                        detail: {{
                            type: 'streamlit:custom',
                            key: 'bpmn_layout_{layout_key}',
                            value: 'complete'
                        }}
                    }});
                    window.dispatchEvent(event);
                    
                    // Also create download for convenience
                    const blob = new Blob([layoutedXML], {{type: 'application/xml'}});
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'laid_out_workflow.bpmn';
                    a.style.display = 'none';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                }})
                .catch(err => {{
                    console.error('Error laying out BPMN:', err);
                    document.getElementById('bpmn_layout_result_{layout_key}').value = 'ERROR: ' + err.message;
                    
                    // Signal error to Streamlit
                    const event = new CustomEvent('streamlit:message', {{ 
                        detail: {{
                            type: 'streamlit:custom',
                            key: 'bpmn_layout_{layout_key}',
                            value: 'error'
                        }}
                    }});
                    window.dispatchEvent(event);
                }});
                
            // Function to check for result and report back to Streamlit
            function checkForResult() {{
                const result = document.getElementById('bpmn_layout_result_{layout_key}').value;
                if (result) {{
                    // Send the result to Streamlit via URL parameters
                    const baseUrl = window.location.pathname;
                    const params = new URLSearchParams(window.location.search);
                    params.set('bpmn_result_{layout_key}', 'ready');
                    
                    fetch(baseUrl + '?' + params.toString(), {{
                        method: 'GET',
                        headers: {{
                            'Content-Type': 'application/x-www-form-urlencoded',
                        }},
                    }});
                }}
            }}
            
            // Check periodically
            setInterval(checkForResult, 1000);
        </script>
    </body>
    </html>
    """

    # Render HTML component
    components.html(html_content, height=0)
    
    # Check if we have a result parameter in the URL
    params = st.experimental_get_query_params()
    result_key = f'bpmn_result_{layout_key}'
    
    if result_key in params and params[result_key][0] == 'ready':
        # Need to re-run the script to extract the data
        if 'bpmn_layout_extracted' not in st.session_state:
            st.session_state['bpmn_layout_extracted'] = False
            
            # Create HTML to extract the result
            extract_html = f"""
            <html>
            <body>
                <script>
                    window.onload = function() {{
                        const result = document.getElementById('bpmn_layout_result_{layout_key}').value;
                        if (result) {{
                            // Store the result
                            fetch('/_stcore/upload_file', {{
                                method: 'POST',
                                headers: {{
                                    'Content-Type': 'application/octet-stream',
                                }},
                                body: result,
                            }})
                            .then(response => response.json())
                            .then(data => {{
                                // Set the file_id parameter to signal Streamlit
                                const baseUrl = window.location.pathname;
                                const params = new URLSearchParams(window.location.search);
                                params.set('bpmn_file_id_{layout_key}', data.file_id);
                                window.location.href = baseUrl + '?' + params.toString();
                            }});
                        }}
                    }};
                </script>
            </body>
            </html>
            """
            components.html(extract_html, height=0)
            
    # Check if we have a file_id parameter (indicating upload completed)
    file_id_key = f'bpmn_file_id_{layout_key}'
    if file_id_key in params:
        file_id = params[file_id_key][0]
        
        # Get the file content from Streamlit's storage
        import streamlit.runtime.uploaded_file_manager as ufm
        result_xml = ufm.get_uploaded_file_info(file_id).file.getvalue().decode('utf-8')
        
        # Now you have the XML in a Python variable!
        st.session_state['bpmn_layout_result'] = result_xml
        
        # Show success and update placeholders
        status_placeholder.success("Layout processing complete!")
        
        # Download button for the result
        st.download_button(
            label="Download Laid-Out BPMN XML",
            data=result_xml,
            file_name="laid_out_workflow.bpmn",
            mime="application/xml"
        )
        
        # You can do further processing here with result_xml
        # For example, display a preview or save to a file
        with st.expander("Preview XML"):
            st.code(result_xml[:1000] + "..." if len(result_xml) > 1000 else result_xml, language="xml")
        
        # Example: Save to a file for later use
        output_path = os.path.join(st.session_state['cwd'], "data", "workflows", "latest_layout.bpmn")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(result_xml)
        st.info(f"XML saved to: {output_path}")
        
        return result_xml
    else:
        status_placeholder.info("Waiting for layout processing to complete...")
        return None


# --- Main Page Structure ---

def show():
    initialize_state()
    
    st.subheader("Upload Data")
    upload_user_list()
    if st.button("Reset Benutzerliste"):
        st.session_state['user_dict'] = {}
        st.info("User list has been reset.")
    xls = upload_dossier()
    if xls is not None:
        activities_table = build_activities_table(xls)
        groups_table = build_groups_table(xls)
        # Set the correct indices before calling generate_additional_nodes
        activities_index = activities_table.set_index('TransportID').copy()
        groups_index = groups_table.set_index('id').copy()
               
        
        # Now call the function with properly indexed dataframes
        try:
            updated_nodes, updated_groups = generate_additional_nodes(activities_index, groups_index)
            edges_table = build_edges_table(updated_nodes, updated_groups)
            # Debugging
            # st.write(updated_nodes.to_dict())
            # st.write(updated_groups.to_dict())
            # st.write(edges_table.to_dict())
            with st.expander("Data Details", expanded=False):
                st.write("Aktivitäten")
                st.dataframe(activities_table)
                st.write("Platzhalter")
                st.dataframe(groups_table)
                st.write("Nodes")
                st.dataframe(updated_nodes.reset_index())
                st.write("Groups")
                st.dataframe(updated_groups.reset_index())
                st.write("Edges")
                st.dataframe(edges_table)
            try:
                st.subheader("Workflow Diagram")
                
                                    
                diagram = build_workflow_diagram(updated_nodes, updated_groups)
                
                # Save the DOT representation to a file (for debugging if needed)
                diagram.save('bpmn_diagram.dot')
                
                # Render the diagram with view=False to prevent it from opening automatically
                svg_path = diagram.render('workflow_diagram', format='svg', cleanup=False, view=False)
                
                # Display the diagram directly in Streamlit
                st.graphviz_chart(diagram)
                
                basic_xml = create_main_flow_bpmn_xml(updated_nodes, edges_table)

                
                # Create download buttons for the SVG and BPMN XML
                col1, col2 = st.columns(2)
                with col1:
                    try:
                        with open(svg_path, "rb") as file:
                            btn = st.download_button(
                                label="Download as SVG",
                                data=file,
                                file_name="workflow_diagram.svg",
                                mime="image/svg+xml",
                            )
                    except Exception as e:
                        st.warning(f"Could not create download button. Error: {str(e)}")
                
                with col2:
                    if st.button("Generate BPMN XML"):                        
                        # Create download button for basic XML
                        st.download_button(
                            label="Download Basic BPMN XML",
                            data=basic_xml,
                            file_name="basic_workflow.bpmn",
                            mime="application/xml"
                        )
                        
                    if st.button("Generate Laid-Out BPMN XML"):
                        # Process BPMN layout with the refactored function
                        process_bpmn_layout(basic_xml)
                            
            except Exception as e:
                st.error(f"Error generating workflow diagram: {str(e)}")
                st.exception(e)
        except Exception as e:
            st.error(f"Error in generate_additional_nodes: {str(e)}")
            st.exception(e)
        

