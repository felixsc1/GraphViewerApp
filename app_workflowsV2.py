import streamlit as st
import pandas as pd
import os
import pickle
from graphviz import Digraph

def initialize_state():
    if 'user_dict' not in st.session_state:
        # Create workflows directory if it doesn't exist
        workflows_dir = os.path.join(st.session_state['cwd'], 'data', 'workflows')
        os.makedirs(workflows_dir, exist_ok=True)
        
        # Try to load existing dictionary
        pickle_path = os.path.join(workflows_dir, 'user_dict.pickle')
        if os.path.exists(pickle_path):
            try:
                with open(pickle_path, 'rb') as f:
                    st.session_state['user_dict'] = pickle.load(f)
                st.info(f"Loaded existing user dictionary with {len(st.session_state['user_dict'])} entries")
            except Exception as e:
                st.error(f"Benutzerliste konnte nicht geladen werden: {str(e)}")
                st.session_state['user_dict'] = {}
        else:
            st.session_state['user_dict'] = {}

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
            
            # Check if all required columns were found
            if not all([transport_id_col, vorname_col, nachname_col]):
                missing = []
                if not transport_id_col: missing.append('TransportID')
                if not vorname_col: missing.append('Vorname')
                if not nachname_col: missing.append('Nachname')
                st.error(f"Could not find columns starting with: {', '.join(missing)}")
                return
            
            # Create dictionary with TransportID as key and concatenated name as value
            user_dict = {
                str(row[transport_id_col]): f"{row[vorname_col]} {row[nachname_col]}"
                for _, row in df.iterrows()
                if pd.notna(row[transport_id_col])
            }
            
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
                # Clean the Empfänger column by applying extract_id to remove suffixes
                temp_df["Empfänger"] = df[empfaenger_col].apply(extract_id)
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
                    groups_df.at[idx, "parallel_condition_name"] = ";".join(map(str, condition_names))
                    groups_df.at[idx, "parallel_condition_expression"] = ";".join(map(str, condition_expressions))

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
    Generates additional nodes (gateways, decision, rule) for parallel groups based on their Erledigungsmodus:
    - "AnyBranch": Adds decision node, rule node, and gateways with 'X' labels
    - "OnlyOneBranch": Adds decision node, rule node, and gateways with empty labels
    - "AllBranches": Adds only gateways with '+' labels (no decision or rule nodes)
    
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
    
    # Helper function to generate unique node IDs
    def generate_node_id(base):
        return f"{base}_{pd.Timestamp.now().strftime('%Y%m%d%H%M%S%f')}"
    
    # Process each group with Erledigungsmodus that needs special handling
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
            rule_node_id = generate_node_id('rule')
            decision_node_id = generate_node_id('decision')
            gateway_split_id = generate_node_id('gateway_split')
            gateway_join_id = generate_node_id('gateway_join')
            
            # Place nodes in sequence
            decision_seq = min_seq - 2  # Decision comes before gateway
            gateway_split_seq = min_seq - 1  # Gateway split comes just before the first child
            gateway_join_seq = max_seq + 1  # Gateway join comes just after the last child
            rule_seq = -1  # Rule not in main sequence
            
            # Set gateway labels based on the erledigungsmodus
            if erledigungsmodus == 'AnyBranch':
                gateway_split_label = 'X'  # Gateway split symbol for AnyBranch
                gateway_join_label = 'X'   # Gateway join symbol for AnyBranch
            else:  # OnlyOneBranch
                gateway_split_label = ''   # Empty diamond for OnlyOneBranch
                gateway_join_label = ''    # Empty diamond for OnlyOneBranch
            
            # Create nodes dataframe for AnyBranch or OnlyOneBranch
            new_nodes = pd.DataFrame({
                'node_id': [rule_node_id, decision_node_id, gateway_split_id, gateway_join_id],
                'node_type': ['rule', 'decision', 'gateway', 'gateway'],
                'ParentActivity': [decision_node_id, group_id, group_id, group_id],
                'SequenceNumber': [rule_seq, decision_seq, gateway_split_seq, gateway_join_seq],
                'label': [
                    groups_table.loc[group_id, 'parallel_condition_expression'],
                    "Entscheid\n" + str(groups_table.loc[group_id, 'parallel_condition_name']).replace(';', '\n'),
                    gateway_split_label,
                    gateway_join_label
                ],
                'shape': ['note', 'box', 'diamond', 'diamond']
            }).set_index('node_id')
        
        # Append new nodes to the updated table
        updated_nodes = pd.concat([updated_nodes, new_nodes])
    
    # Sort by ParentActivity and SequenceNumber for correct flow
    updated_nodes.sort_values(by=['ParentActivity', 'SequenceNumber'], inplace=True)
    
    return updated_nodes, updated_groups

# --- Main Page Structure ---

def show():
    initialize_state()
    upload_user_list()
    xls = upload_dossier()
    if xls is not None:
        activities_table = build_activities_table(xls)
        st.dataframe(activities_table)
        groups_table = build_groups_table(xls)
        st.dataframe(groups_table)
        
        # Set the correct indices before calling generate_additional_nodes
        activities_index = activities_table.set_index('TransportID').copy()
        groups_index = groups_table.set_index('group_id').copy()
        
        # Now call the function with properly indexed dataframes
        try:
            updated_nodes, updated_groups = generate_additional_nodes(activities_index, groups_index)
            st.dataframe(updated_nodes.reset_index())
            st.dataframe(updated_groups.reset_index())
        except Exception as e:
            st.error(f"Error in generate_additional_nodes: {str(e)}")
            st.exception(e)

