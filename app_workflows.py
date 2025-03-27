import streamlit as st
import pandas as pd
import os
import pickle
from graphviz import Digraph

# --- Diagram Spacing Configuration ---
# These variables control the spacing in the generated diagram
# Adjust these values to fine-tune the layout
GRAPH_NODE_SEPARATION = '0.5'    # Horizontal space between nodes (increased a bit for better flow)
GRAPH_RANK_SEPARATION = '0.7'    # Vertical space between ranks (increased slightly)
EDGE_MIN_LENGTH = '1.0'          # Minimum edge length (increased to help with flow)
EDGE_LABEL_DISTANCE = '1.5'      # Distance of labels from their edges

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
            temp_df.columns = common_column_patterns
            
            # Clean the ParentActivity column by applying extract_id to remove suffixes
            temp_df["ParentActivity"] = temp_df["ParentActivity"].apply(extract_id)
            
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
    
    # Step 8: Sort by ParentActivity and SequenceNumber for readability (optional)
    activities_df.sort_values(by=["ParentActivity", "SequenceNumber"], inplace=True)
    
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
        temp_df.columns = required_columns
        
        # Apply extract_id to ParentActivity column to clean it
        temp_df["ParentActivity"] = temp_df["ParentActivity"].apply(extract_id)
        
        temp_df["type"] = group_type
        temp_df.rename(columns={
            "TransportID": "group_id",
            "Name:de": "name",
            "ParentActivity": "parent_group_id",
            "SequenceNumber": "SequenceNumber"
        }, inplace=True)

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
                group_id = row["group_id"]
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
    if groups_df["group_id"].duplicated().any():
        print("Warning: Duplicate group IDs detected.")

    # Sort for readability
    groups_df.sort_values(by=["parent_group_id", "SequenceNumber"], inplace=True)

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
    - groups_table: pd.DataFrame with groups (indexed by group_id)
    
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
    def generate_node_id(base, counter=None):
        """Generate a unique ID by combining base, timestamp, and optional counter"""
        timestamp = pd.Timestamp.now().strftime('%Y%m%d%H%M%S%f')
        if counter is not None:
            return f"{base}_{timestamp}_{counter}"
        return f"{base}_{timestamp}"

    # Track substep nodes with a counter to ensure uniqueness
    substep_counter = 0
    substep_nodes_list = []

    for activity_id, activity in activities_table.iterrows():
        if pd.notna(activity.get('substeps')):
            # Use counter for unique IDs
            substep_node_id = generate_node_id('substeps', substep_counter)
            substep_counter += 1
            
            # Create a substep node
            substep_node = pd.Series({
                'node_type': 'substeps',
                'ParentActivity': activity_id,
                'SequenceNumber': -1,  # Not in main sequence
                'label': activity['substeps'],
                'shape': 'note',
                # Copy other relevant columns with None values
                'Empfänger': None,
                'Name:de': None,
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
        child_activities = activities_table[activities_table['ParentActivity'] == group_id]
        child_subgroups = groups_table[groups_table['parent_group_id'] == group_id]
        
        # Get existing sequence numbers of children
        existing_seq = pd.concat([child_activities['SequenceNumber'], 
                                 child_subgroups['SequenceNumber']]).sort_values()
        
        # Determine sequence numbers for new nodes
        min_seq = existing_seq.min() if not existing_seq.empty else 0
        max_seq = existing_seq.max() if not existing_seq.empty else 0
        
        # Handle different Erledigungsmodus types
        if erledigungsmodus == 'AllBranches':
            # For AllBranches, we only need gateway nodes with + symbol
            gateway_split_id = generate_node_id('gateway_split')
            gateway_join_id = generate_node_id('gateway_join')
            
            # Place gateways at the beginning and end
            gateway_split_seq = min_seq - 1  # Just before first child
            gateway_join_seq = max_seq + 1   # Just after last child
            
            # Create nodes dataframe for AllBranches (only gateways)
            new_nodes = pd.DataFrame({
                'node_id': [gateway_split_id, gateway_join_id],
                'node_type': ['gateway', 'gateway'],
                'ParentActivity': [group_id, group_id],
                'SequenceNumber': [gateway_split_seq, gateway_join_seq],
                'label': ['+', '+'],  # Plus symbol for AllBranches
                'shape': ['diamond', 'diamond']
            }).set_index('node_id')
            
        else:
            # For AnyBranch and OnlyOneBranch, include decision and rule nodes
            # Check if there's a valid parallel_condition_expression
            has_condition_expr = pd.notna(groups_table.loc[group_id, 'parallel_condition_expression'])
            
            # For AnyBranch and OnlyOneBranch, always create decision and gateway nodes
            decision_node_id = generate_node_id('decision')
            gateway_split_id = generate_node_id('gateway_split')
            gateway_join_id = generate_node_id('gateway_join')
            
            # Only create rule node if there's a condition expression
            if has_condition_expr:
                rule_node_id = generate_node_id('rule')
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
            shapes = []
            
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
            shapes.extend(['box', 'diamond', 'diamond'])
            
            # Add rule node only if there's a condition expression
            if has_condition_expr:
                node_ids.append(rule_node_id)
                node_types.append('rule')
                parent_activities.append(decision_node_id)
                sequence_numbers.append(rule_seq)
                labels.append(groups_table.loc[group_id, 'parallel_condition_expression'])
                shapes.append('note')
            
            # Create nodes dataframe for AnyBranch or OnlyOneBranch
            new_nodes = pd.DataFrame({
                'node_id': node_ids,
                'node_type': node_types,
                'ParentActivity': parent_activities,
                'SequenceNumber': sequence_numbers,
                'label': labels,
                'shape': shapes
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
        child_activities = activities_table[activities_table['ParentActivity'] == group_id]
        child_subgroups = groups_table[groups_table['parent_group_id'] == group_id]
        
        # Get existing sequence numbers of children
        existing_seq = pd.concat([child_activities['SequenceNumber'], 
                                 child_subgroups['SequenceNumber']]).sort_values()
        
        # Determine sequence numbers for new nodes
        min_seq = existing_seq.min() if not existing_seq.empty else 0
        max_seq = existing_seq.max() if not existing_seq.empty else 0
        
        # Generate node IDs
        rule_node_id = generate_node_id('skip_rule')
        decision_node_id = generate_node_id('skip_decision')
        gateway_split_id = generate_node_id('skip_gateway_split')
        gateway_join_id = generate_node_id('skip_gateway_join')
        
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
            'ParentActivity': [decision_node_id, group_id, group_id, group_id],
            'SequenceNumber': [rule_seq, decision_seq, gateway_split_seq, gateway_join_seq],
            'label': [
                skip_condition if pd.notna(skip_condition) else '',
                "Überspringen, falls\n" + (skip_name if pd.notna(skip_name) else ''),
                'X',  # X symbol for skip gateway split
                'X'   # X symbol for skip gateway join
            ],
            'shape': ['note', 'box', 'diamond', 'diamond']
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
        child_activities = activities_table[activities_table['ParentActivity'] == group_id]
        child_subgroups = groups_table[groups_table['parent_group_id'] == group_id]
        
        # Get existing sequence numbers of children
        existing_seq = pd.concat([child_activities['SequenceNumber'], 
                                 child_subgroups['SequenceNumber']]).sort_values()
        
        # Determine sequence numbers for new nodes
        min_seq = existing_seq.min() if not existing_seq.empty else 0
        max_seq = existing_seq.max() if not existing_seq.empty else 0
        
        # Generate node IDs
        rule_node_id = generate_node_id('repeat_rule')
        decision_node_id = generate_node_id('repeat_decision')
        gateway_node_id = generate_node_id('repeat_gateway')
        
        # As a target for the repeat, we'll use an invisible helper node at the beginning
        # This will allow us to connect back to the start of the group
        helper_node_id = generate_node_id('repeat_helper')
        
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
            'ParentActivity': [decision_node_id, group_id, group_id, group_id],
            'SequenceNumber': [rule_seq, decision_seq, gateway_seq, helper_seq],
            'label': [
                repeat_condition if pd.notna(repeat_condition) else '',
                "Wiederholen, falls\n" + (repeat_name if pd.notna(repeat_name) else ''),
                'X',  # X symbol for gateway
                ''    # Empty label for helper node
            ],
            'shape': ['note', 'box', 'diamond', 'point']  # Point shape for helper - nearly invisible
        }).set_index('node_id')
        
        # Store the helper node ID to refer back to in add_group function
        updated_groups.at[group_id, 'repeat_connections'] = {
            'gateway': gateway_node_id,
            'helper': helper_node_id
        }
        
        # Append new nodes to the updated table
        updated_nodes = pd.concat([updated_nodes, new_nodes])
    
    # Sort by ParentActivity and SequenceNumber for correct flow
    updated_nodes.sort_values(by=['ParentActivity', 'SequenceNumber'], inplace=True)
    
    return updated_nodes, updated_groups

## -- Generate BPMN Diagram --

def add_node(dot, node_id, node, edge_set):
    """Add a node to the Graphviz diagram based on its type."""
    node_type = node['node_type']
    label = str(node['label']) if pd.notna(node['label']) else ''

    if node_type == 'rule':
        if node_id.startswith('repeat_rule') or node_id.startswith('skip_rule'):
            label = f"📄\n{label}"
        dot.node(node_id, label=label, shape='none')
        parent_activity = node['ParentActivity']
        if pd.notna(parent_activity) and (node_id, parent_activity) not in edge_set:
            dot.edge(node_id, parent_activity, style='dotted')
            edge_set.add((node_id, parent_activity))
        return False

    elif node_type == 'substeps':
        # Create the substep node with parent's group to ensure vertical alignment
        dot.node(
            node_id,
            label=label,
            shape='none',     # No border
            style='',         # No style
            fontsize='14',
            align='left',     # Left justify text
            group=node['ParentActivity']  # Key change: use parent's ID as group
        )
        
        parent_activity = node['ParentActivity']
        if pd.notna(parent_activity) and (parent_activity, node_id) not in edge_set:
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
        if node_type == 'activity':
            empfanger = node['Empfänger'] if pd.notna(node['Empfänger']) else ''
            name_de = node['Name:de'] if pd.notna(node['Name:de']) else ''
            activity_type = node['type'] if pd.notna(node['type']) else ''
            
            # Add emoji based on activity type
            emoji = ''
            if activity_type == 'manual':
                emoji = '👤 '
            elif activity_type == 'system':
                emoji = '⚙️ '
            elif activity_type == 'script':
                emoji = '📜 '
                
            # Format empfanger with emoji
            formatted_empfanger = f"{emoji}{empfanger}" if empfanger else emoji
            
            # Create HTML-like label for better formatting
            # Use a table with reduced width and word wrapping
            # Add line breaks for long text (approx 15-20 chars per line)
            
            # Format name_de with line breaks if needed
            formatted_name = name_de
            if len(name_de) > 18:
                # Find a space near the middle to break
                mid_point = len(name_de) // 2
                space_pos = name_de.find(' ', mid_point - 5)
                if space_pos > 0:
                    formatted_name = name_de[:space_pos] + '<BR/>' + name_de[space_pos+1:]
            
            html_label = f'''<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="6" WIDTH="130">
<TR><TD ALIGN="left" VALIGN="top"><FONT POINT-SIZE="14">{formatted_empfanger}</FONT></TD></TR>
<TR><TD ALIGN="center" BALIGN="center"><FONT>{formatted_name}</FONT></TD></TR>
</TABLE>>'''
            label = html_label
        elif node_type == 'helper':
            label = ''
        
        # Include shape in attrs dictionary
        attrs = {}
        if node_type == 'gateway':
            attrs['fontsize'] = '16'
            attrs['shape'] = 'diamond'
        elif node_type == 'helper':
            attrs['width'] = '0.1'
            attrs['height'] = '0.1'
            attrs['shape'] = 'point'
        elif node_type == 'activity':
            # Set attributes for activity nodes to handle HTML labels
            attrs['shape'] = 'box'
            attrs['style'] = 'rounded'
            attrs['margin'] = '0'
            attrs['group'] = node_id  # Key change: set group attribute to own ID for activities
        else:
            attrs['shape'] = 'box'  # Default shape
            
        dot.node(node_id, label=label, **attrs)
        return True
    
def add_group(group_id, dot, updated_nodes, updated_groups, edge_set, processed_substeps=None):
    """Build a group in the BPMN diagram recursively."""
    if processed_substeps is None:
        processed_substeps = set()
    
    group = updated_groups.loc[group_id]
    children = []
    
    # Format the group name for display in the upper left corner
    group_name = group['name'] if pd.notna(group['name']) else ''

    # Collect all nodes and subgroups
    nodes = updated_nodes[updated_nodes['ParentActivity'] == group_id]
    for node_id in nodes.index:
        children.append(('node', node_id, nodes.at[node_id, 'SequenceNumber']))

    # Rule nodes under decisions
    for decision_id in nodes[nodes['node_type'] == 'decision'].index:
        rule_nodes = updated_nodes[(updated_nodes['ParentActivity'] == decision_id) & 
                                   (updated_nodes['node_type'] == 'rule')]
        for rule_id in rule_nodes.index:
            children.append(('node', rule_id, updated_nodes.at[rule_id, 'SequenceNumber']))

    # Substep nodes under activities
    for activity_id in nodes[nodes['node_type'] == 'activity'].index:
        substep_nodes = updated_nodes[(updated_nodes['ParentActivity'] == activity_id) & 
                                      (updated_nodes['node_type'] == 'substeps')]
        for substep_id in substep_nodes.index:
            if substep_id not in processed_substeps:
                processed_substeps.add(substep_id)
                children.append(('node', substep_id, updated_nodes.at[substep_id, 'SequenceNumber']))

    # Subgroups
    subgroups = updated_groups[updated_groups['parent_group_id'] == group_id]
    for subgroup_id in subgroups.index:
        children.append(('group', subgroup_id, subgroups.at[subgroup_id, 'SequenceNumber']))

    children.sort(key=lambda x: x[2])  # Sort by sequence number

    # Gateway and parallel handling
    gateway_split = gateway_join = skip_gateway_split = skip_gateway_join = repeat_gateway = repeat_helper = None
    parallel_branches = []
    gateway_connected_nodes = set()
    labels = group['parallel_condition_name'].split(';') if group['type'] == 'parallel' and pd.notna(group.get('parallel_condition_name')) else []

    if pd.notna(group.get('repeat_connections')):
        repeat_data = group['repeat_connections']
        repeat_gateway, repeat_helper = repeat_data.get('gateway'), repeat_data.get('helper')

    # Identify gateways
    for child_type, child_id, _ in children:
        if child_type == 'node' and updated_nodes.at[child_id, 'node_type'] == 'gateway':
            if 'gateway_split' in child_id and 'skip' not in child_id:
                gateway_split = child_id
            elif 'gateway_join' in child_id and 'skip' not in child_id:
                gateway_join = child_id
            elif 'skip_gateway_split' in child_id:
                skip_gateway_split = child_id
            elif 'skip_gateway_join' in child_id:
                skip_gateway_join = child_id

    # Parallel branches
    if group['type'] == 'parallel' and gateway_split and gateway_join:
        split_seq, join_seq = updated_nodes.at[gateway_split, 'SequenceNumber'], updated_nodes.at[gateway_join, 'SequenceNumber']
        parallel_branches = [child for child in children if split_seq < child[2] < join_seq]

    # Process children
    prev_node = first_node = last_node = first_real_node = None
    for child_type, child_id, seq in children:
        if child_type == 'node':
            node = updated_nodes.loc[child_id]
            in_flow = add_node(dot, child_id, node, edge_set)
            if in_flow:
                if first_node is None:
                    first_node = child_id
                if first_real_node is None and node['node_type'] != 'helper':
                    first_real_node = child_id
                last_node = child_id
                if prev_node and (prev_node, child_id) not in edge_set:
                    if group['type'] != 'parallel' or (prev_node not in gateway_connected_nodes and child_id not in gateway_connected_nodes):
                        # Standard edge without labels
                        dot.edge(prev_node, child_id, minlen=EDGE_MIN_LENGTH, weight='2', constraint='true')
                        edge_set.add((prev_node, child_id))
                prev_node = child_id

        elif child_type == 'group':
            # Create a subgraph with HTML-like label for the child group
            with dot.subgraph(name=f'cluster_{child_id}') as sub_dot:
                # Apply styling to the cluster before adding content
                sub_dot.attr(
                    label=f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="2"><TR><TD ALIGN="left"><B>{updated_groups.at[child_id, "name"]}</B></TD></TR></TABLE>>',
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
                if group['type'] == 'parallel' and (child_type, child_id, seq) in parallel_branches:
                    idx = parallel_branches.index((child_type, child_id, seq))
                    label = labels[idx] if idx < len(labels) else None
                    if gateway_split and (gateway_split, subgroup_first) not in edge_set:
                        # Edge with label, add parameters to prevent overlap
                        dot.edge(gateway_split, subgroup_first, 
                                xlabel=label, 
                                labelangle='0', 
                                labeldistance=EDGE_LABEL_DISTANCE,
                                minlen=str(float(EDGE_MIN_LENGTH) + 0.2),
                                weight='2',
                                constraint='true')
                        edge_set.add((gateway_split, subgroup_first))
                        gateway_connected_nodes.add(subgroup_first)
                    if gateway_join and (subgroup_last, gateway_join) not in edge_set:
                        dot.edge(subgroup_last, gateway_join, minlen=EDGE_MIN_LENGTH, weight='2', constraint='true')
                        edge_set.add((subgroup_last, gateway_join))
                        gateway_connected_nodes.add(subgroup_last)
                elif prev_node and (prev_node, subgroup_first) not in edge_set:
                    if prev_node not in gateway_connected_nodes and subgroup_first not in gateway_connected_nodes:
                        dot.edge(prev_node, subgroup_first, minlen=EDGE_MIN_LENGTH, weight='2', constraint='true')
                        edge_set.add((prev_node, subgroup_first))
                prev_node = subgroup_last

    # Connect parallel branches
    if group['type'] == 'parallel' and gateway_split and gateway_join:
        for i, branch in enumerate(parallel_branches):
            if branch[0] == 'node':
                node_id = branch[1]
                label = labels[i] if i < len(labels) else None
                if (gateway_split, node_id) not in edge_set:
                    # Edge with label, add parameters to prevent overlap
                    dot.edge(gateway_split, node_id, 
                            xlabel=label, 
                            labelangle='0', 
                            labeldistance=EDGE_LABEL_DISTANCE,
                            minlen=str(float(EDGE_MIN_LENGTH) + 0.2),
                            weight='2',
                            constraint='true')
                    edge_set.add((gateway_split, node_id))
                    gateway_connected_nodes.add(node_id)
                if (node_id, gateway_join) not in edge_set:
                    dot.edge(node_id, gateway_join, minlen=EDGE_MIN_LENGTH, weight='2', constraint='true')
                    edge_set.add((node_id, gateway_join))
                    gateway_connected_nodes.add(node_id)

    # Handle skip and repeat gateways
    if skip_gateway_split and skip_gateway_join and (skip_gateway_split, skip_gateway_join) not in edge_set:
        label = group['skip_name'] if pd.notna(group.get('skip_name')) else None
        # Edge with label, add parameters to prevent overlap
        dot.edge(skip_gateway_split, skip_gateway_join, 
                xlabel=label, 
                labelangle='0', 
                labeldistance=EDGE_LABEL_DISTANCE,
                constraint='false',  # Must be false to allow skipping
                minlen=str(float(EDGE_MIN_LENGTH) + 0.5),
                weight='1')  # Lower weight for skip edges
        edge_set.add((skip_gateway_split, skip_gateway_join))

    if repeat_gateway and repeat_helper and (repeat_gateway, repeat_helper) not in edge_set:
        label = group['repeat_name'] if pd.notna(group.get('repeat_name')) else None
        # Edge with label, add parameters to prevent overlap
        dot.edge(repeat_gateway, repeat_helper, 
                xlabel=label, 
                labelangle='0', 
                labeldistance=EDGE_LABEL_DISTANCE,
                constraint='false',  # Must be false to allow going back
                minlen=str(float(EDGE_MIN_LENGTH) + 0.5),
                weight='1')  # Lower weight for repeat edges
        edge_set.add((repeat_gateway, repeat_helper))
    if repeat_helper and first_real_node and (repeat_helper, first_real_node) not in edge_set:
        dot.edge(repeat_helper, first_real_node, minlen=EDGE_MIN_LENGTH, weight='2', constraint='true')
        edge_set.add((repeat_helper, first_real_node))

    return first_node, last_node


def build_workflow_diagram(updated_nodes, updated_groups):
    """Generate the complete BPMN diagram."""
    # Create the digraph with more spacing and overlap prevention
    dot = Digraph(format='svg', 
                 graph_attr={
                     'rankdir': 'LR', 
                     'splines': 'ortho', 
                     'fontname': 'sans-serif',
                     'nodesep': GRAPH_NODE_SEPARATION,  # Horizontal space between nodes
                     'ranksep': GRAPH_RANK_SEPARATION,  # Vertical space between ranks
                     'overlap': 'false',                # Prevent node overlap
                     'sep': '+5',                       # Reduced additional separation
                     'margin': '0.1',                   # Reduce margin around nodes
                     'concentrate': 'true',             # Merge edges where possible
                     'ordering': 'out',                 # Maintain order of successors to each node
                     'newrank': 'true'                  # Enhanced ranking algorithm
                 },
                 node_attr={'fontname': 'sans-serif', 'margin': '0.1'}, 
                 edge_attr={'fontname': 'sans-serif', 'weight': '2'})  # Increase edge weight
    
    # Create invisible rank constraints to force left-to-right flow
    with dot.subgraph(name='cluster_flow_control') as flow:
        flow.attr(style='invis')  # Make this subgraph invisible
        # Create rank constraints
        flow.node('rank_start', style='invis', shape='none', width='0')
        flow.node('rank_end', style='invis', shape='none', width='0')
        flow.edge('rank_start', 'rank_end', style='invis')
    
    # Start and end nodes with stronger positioning
    dot.node('start', shape='circle', label='', width='0.5', height='0.5', rank='source')
    dot.node('end', shape='circle', label='', width='0.5', height='0.5', rank='sink')
    
    # Force start to be at same rank as rank_start
    dot.edge('rank_start', 'start', style='invis', weight='100')
    
    # Force end to be at same rank as rank_end
    dot.edge('rank_end', 'end', style='invis', weight='100')
    
    edge_set = set()

    top_group_id = updated_groups[updated_groups['parent_group_id'].isna()].index[0]
    
    # Create top-level cluster with HTML-formatted label
    with dot.subgraph(name=f'cluster_{top_group_id}') as c:
        # Format the top-level cluster
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

    dot.edge('start', first_node, minlen='0.8', weight='10', constraint='true')
    dot.edge(last_node, 'end', minlen='0.8', weight='10', constraint='true')
    return dot

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
        groups_index = groups_table.set_index('group_id').copy()
        
        # Now call the function with properly indexed dataframes
        try:
            updated_nodes, updated_groups = generate_additional_nodes(activities_index, groups_index)
            with st.expander("Data Details", expanded=False):
                st.write("Aktivitäten")
                st.dataframe(activities_table)
                st.write("Platzhalter")
                st.dataframe(groups_table)
                st.write("Nodes")
                st.dataframe(updated_nodes.reset_index())
                st.write("Groups")
                st.dataframe(updated_groups.reset_index())
            try:
                st.subheader("Workflow Diagram")
                
                # Configuration section in an expander element
                # with st.expander("Advanced Graph Settings", expanded=False):
                #     global GRAPH_NODE_SEPARATION, GRAPH_RANK_SEPARATION, EDGE_MIN_LENGTH, EDGE_LABEL_DISTANCE
                    
                #     col1, col2 = st.columns(2)
                #     with col1:
                #         GRAPH_NODE_SEPARATION = st.text_input("Node Separation", GRAPH_NODE_SEPARATION, 
                #                                           help="Horizontal space between nodes (default: 0.6)")
                #         EDGE_MIN_LENGTH = st.text_input("Edge Minimum Length", EDGE_MIN_LENGTH,
                #                                       help="Minimum edge length (default: 1.2)")
                #     with col2:
                #         GRAPH_RANK_SEPARATION = st.text_input("Rank Separation", GRAPH_RANK_SEPARATION,
                #                                           help="Vertical space between ranks (default: 0.8)")
                #         EDGE_LABEL_DISTANCE = st.text_input("Edge Label Distance", EDGE_LABEL_DISTANCE,
                #                                           help="Distance of labels from edges (default: 1.8)")
                                    
                diagram = build_workflow_diagram(updated_nodes, updated_groups)
                diagram.render('workflow_diagram', view=True)
            except Exception as e:
                st.error(f"Error generating workflow diagram: {str(e)}")
                st.exception(e)
        except Exception as e:
            st.error(f"Error in generate_additional_nodes: {str(e)}")
            st.exception(e)
        

