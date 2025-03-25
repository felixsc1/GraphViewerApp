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
            labels.extend([
                "Entscheid\n" + str(groups_table.loc[group_id, 'parallel_condition_name']).replace(';', '\n'),
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

def add_group(group_id, dot, updated_nodes, updated_groups, edge_set, processed_substeps=None):
    if processed_substeps is None:
        processed_substeps = set()
        
    group = updated_groups.loc[group_id]
    children = []

    # Collect nodes and subgroups
    nodes = updated_nodes[updated_nodes['ParentActivity'] == group_id]
    
    # First pass to collect regular nodes (non-rules)
    node_ids = []
    for node_id in nodes.index:
        # Get sequence number as a scalar value
        seq_num = nodes.loc[node_id, 'SequenceNumber']
        if isinstance(seq_num, pd.Series):
            seq_num = seq_num.iloc[0] if not seq_num.empty else 0
            
        children.append(('node', node_id, seq_num))
        node_ids.append(node_id)
    
    # Second pass to find rule nodes connected to decision nodes within this group
    for decision_id in nodes[nodes['node_type'] == 'decision'].index:
        rule_nodes = updated_nodes[(updated_nodes['ParentActivity'] == decision_id) & 
                                  (updated_nodes['node_type'] == 'rule')]
        for rule_id in rule_nodes.index:
            # Get sequence number as a scalar value
            seq_num = updated_nodes.loc[rule_id, 'SequenceNumber']
            if isinstance(seq_num, pd.Series):
                seq_num = seq_num.iloc[0] if not seq_num.empty else 0
                
            children.append(('node', rule_id, seq_num))
    
    # Third pass to find substep nodes connected to activities in this group
    for activity_id in node_ids:
        substep_nodes = updated_nodes[(updated_nodes['ParentActivity'] == activity_id) & 
                                     (updated_nodes['node_type'] == 'substeps')]
        for substep_id in substep_nodes.index:
            # Skip if we've already processed this substep
            if substep_id in processed_substeps:
                continue
                
            processed_substeps.add(substep_id)
            
            # Get sequence number as a scalar value
            seq_num = updated_nodes.loc[substep_id, 'SequenceNumber']
            if isinstance(seq_num, pd.Series):
                seq_num = seq_num.iloc[0] if not seq_num.empty else 0
                
            children.append(('node', substep_id, seq_num))

    # Add subgroups
    subgroups = updated_groups[updated_groups['parent_group_id'] == group_id]
    for subgroup_id in subgroups.index:
        # Get sequence number as a scalar value
        seq_num = subgroups.loc[subgroup_id, 'SequenceNumber']
        if isinstance(seq_num, pd.Series):
            seq_num = seq_num.iloc[0] if not seq_num.empty else 0
            
        children.append(('group', subgroup_id, seq_num))

    children.sort(key=lambda x: x[2])  # Sort by sequence number

    # Handle parallel groups and skip conditions
    gateway_split = None
    gateway_join = None
    skip_gateway_split = None
    skip_gateway_join = None
    repeat_gateway = None
    repeat_helper = None
    parallel_branches = []
    gateway_connected_nodes = set()  # Track nodes connected to gateways

    # Check for repeat connections
    if pd.notna(group.get('repeat_connections')):
        repeat_data = group['repeat_connections']
        repeat_gateway = repeat_data.get('gateway')
        repeat_helper = repeat_data.get('helper')

    # Extract labels for parallel conditions
    labels = []
    if group['type'] == 'parallel' and pd.notna(group.get('parallel_condition_name')):
        labels = group['parallel_condition_name'].split(';')

    # First identify gateways in this group
    for child_type, child_id, seq in children:
        if child_type == 'node':
            # Get node_type as a scalar value
            node_type = updated_nodes.loc[child_id, 'node_type']
            if isinstance(node_type, pd.Series):
                node_type = node_type.iloc[0] if not node_type.empty else ''
                
            # Now compare the scalar value
            if node_type == 'gateway':
                if 'gateway_split' in child_id and 'skip' not in child_id:
                    gateway_split = child_id
                elif 'gateway_join' in child_id and 'skip' not in child_id:
                    gateway_join = child_id
                elif 'skip_gateway_split' in child_id:
                    skip_gateway_split = child_id
                elif 'skip_gateway_join' in child_id:
                    skip_gateway_join = child_id

    # Handle parallel gateways
    if group['type'] == 'parallel' and gateway_split and gateway_join:
        split_seq = updated_nodes.loc[gateway_split, 'SequenceNumber']
        join_seq = updated_nodes.loc[gateway_join, 'SequenceNumber']
        parallel_branches = [child for child in children if split_seq < child[2] < join_seq]
        for branch in parallel_branches:
            if branch[0] == 'node':
                gateway_connected_nodes.add(branch[1])

    # Process children and manage connections
    prev_node = None
    first_node = None
    last_node = None
    first_real_node = None  # First node that's not a helper

    for child_type, child_id, seq in children:
        if child_type == 'node':
            # Get node data and ensure we have scalar values
            node = updated_nodes.loc[child_id]
            
            # Helper function to get scalar value from a potentially Series object
            def get_scalar(value):
                if isinstance(value, pd.Series):
                    return value.iloc[0] if not value.empty else ''
                return value
            
            # Get node properties as scalar values
            node_type = get_scalar(node['node_type'])
            
            # Now the rest of the code comparing to node_type will work
            if node_type == 'rule':
                # Get label as scalar value
                label = str(get_scalar(node['label'])) if pd.notna(get_scalar(node['label'])) else ''
                
                if child_id.startswith('repeat_rule') or child_id.startswith('skip_rule'):
                    # Display with a sheet of paper icon and label underneath
                    label = f"📄\n{label}"
                    # show label without border
                    shape = 'none'
                elif child_id.startswith('rule'):
                    # Display just the label without a border
                    shape = 'none'
                else:
                    # Default shape for other rule nodes (optional fallback)
                    shape = 'none'
                dot.node(child_id, label=label, shape=shape)

                # Connect to ParentActivity with a dotted arrow
                parent_activity = get_scalar(node['ParentActivity'])
                if pd.notna(parent_activity) and (child_id, parent_activity) not in edge_set:
                    dot.edge(child_id, parent_activity, style='dotted')
                    edge_set.add((child_id, parent_activity))
                
            elif node_type == 'substeps':
                # Get label as scalar value
                label = str(get_scalar(node['label'])) if pd.notna(get_scalar(node['label'])) else ''
                
                # Use a note shape with improved styling for better visibility
                dot.node(
                    child_id, 
                    label=label,
                    shape='note',
                    style='filled,dashed',
                    fillcolor='lightyellow',
                    fontsize='10',
                    # Add positioning hints to keep substeps close to parent
                    pos='same'  # This encourages placement on the same rank
                )

                # Connect to ParentActivity with a dotted line (no arrowheads)
                parent_activity = get_scalar(node['ParentActivity'])
                if pd.notna(parent_activity) and (child_id, parent_activity) not in edge_set:
                    # Remove constraint=false to keep substeps closer to parents
                    dot.edge(
                        parent_activity,  # Reverse the direction: parent to substep
                        child_id, 
                        style='dotted', 
                        dir='none',
                        color='gray',
                        # Add weight to pull the substep closer to its parent
                        weight='2.0',
                        len='0.8'  # Shorter preferred edge length
                    )
                    edge_set.add((parent_activity, child_id))  # Note the reversed order
                    
            elif node_type in ['activity', 'decision']:
                if node_type == 'activity':
                    empfanger = get_scalar(node['Empfänger']) if pd.notna(get_scalar(node['Empfänger'])) else ''
                    name_de = get_scalar(node['Name:de']) if pd.notna(get_scalar(node['Name:de'])) else ''
                    label = f"{empfanger}\n{name_de}" if empfanger else name_de
                elif node_type == 'decision':
                    label = str(get_scalar(node['label'])) if pd.notna(get_scalar(node['label'])) else ''
                
                shape = 'box'
                dot.node(child_id, label=label, shape=shape)
                
                # Track nodes for flow
                if first_node is None:
                    first_node = child_id
                if first_real_node is None and node_type != 'helper':
                    first_real_node = child_id
                last_node = child_id

            elif node_type == 'gateway':
                label = str(get_scalar(node['label'])) if pd.notna(get_scalar(node['label'])) else ''
                dot.node(child_id, label=label, shape='diamond', fontsize='16')
                
                # Track nodes for flow
                if first_node is None:
                    first_node = child_id
                if first_real_node is None:
                    first_real_node = child_id
                last_node = child_id
            
            elif node_type == 'helper':
                dot.node(child_id, label='', shape='point', width='0.1', height='0.1')
                if first_node is None:
                    first_node = child_id
                last_node = child_id
                if child_id == repeat_helper:
                    continue
            
            # Connect with prev_node (don't connect rule or substep nodes in the flow)
            if node_type not in ['rule', 'substeps'] and prev_node and (prev_node, child_id) not in edge_set:
                if group['type'] != 'parallel' or (
                    prev_node not in gateway_connected_nodes and child_id not in gateway_connected_nodes
                ):
                    dot.edge(prev_node, child_id)
                    edge_set.add((prev_node, child_id))
            
            # Update prev_node (don't use rule or substep nodes as prev_node)
            if node_type not in ['rule', 'substeps']:
                prev_node = child_id

        elif child_type == 'group':
            with dot.subgraph(name=f'cluster_{child_id}', graph_attr={
                'label': updated_groups.loc[child_id, 'name'],
                'style': 'dashed'
            }) as sub_dot:
                subgroup_first, subgroup_last = add_group(child_id, sub_dot, updated_nodes, updated_groups, edge_set, processed_substeps)
            
            if subgroup_first and subgroup_last:
                if first_node is None:
                    first_node = subgroup_first
                if first_real_node is None:
                    first_real_node = subgroup_first
                last_node = subgroup_last

                # Handle parallel connections with labels for subgroups
                if group['type'] == 'parallel' and (child_type, child_id, seq) in parallel_branches:
                    index = parallel_branches.index((child_type, child_id, seq))
                    label = labels[index] if index < len(labels) else None
                    if gateway_split and (gateway_split, subgroup_first) not in edge_set:
                        dot.edge(gateway_split, subgroup_first, label=label)
                        edge_set.add((gateway_split, subgroup_first))
                        gateway_connected_nodes.add(subgroup_first)
                    if gateway_join and (subgroup_last, gateway_join) not in edge_set:
                        dot.edge(subgroup_last, gateway_join)
                        edge_set.add((subgroup_last, gateway_join))
                        gateway_connected_nodes.add(subgroup_last)
                elif prev_node and (prev_node, subgroup_first) not in edge_set:
                    if prev_node not in gateway_connected_nodes and subgroup_first not in gateway_connected_nodes:
                        dot.edge(prev_node, subgroup_first)
                        edge_set.add((prev_node, subgroup_first))
                prev_node = subgroup_last

    # Ensure gateway connections in parallel groups with labels for nodes
    if group['type'] == 'parallel' and gateway_split and gateway_join:
        for i, branch in enumerate(parallel_branches):
            if branch[0] == 'node':
                branch_start = branch_last = branch[1]
                label = labels[i] if i < len(labels) else None
                if (gateway_split, branch_start) not in edge_set:
                    dot.edge(gateway_split, branch_start, label=label)
                    edge_set.add((gateway_split, branch_start))
                if (branch_last, gateway_join) not in edge_set:
                    dot.edge(branch_last, gateway_join)
                    edge_set.add((branch_last, gateway_join))
            # For subgroups, edge is already created with label in the child loop

    # Handle skip gateway (assuming prior identification)
    if skip_gateway_split and skip_gateway_join and (skip_gateway_split, skip_gateway_join) not in edge_set:
        if pd.notna(group.get('skip_name')):
            dot.edge(skip_gateway_split, skip_gateway_join, label=group['skip_name'])
        else:
            dot.edge(skip_gateway_split, skip_gateway_join)
        edge_set.add((skip_gateway_split, skip_gateway_join))
        
    # Handle repeat gateway
    if pd.notna(group.get('repeat_connections')):
        repeat_data = group['repeat_connections']
        repeat_gateway = repeat_data.get('gateway')
        repeat_helper = repeat_data.get('helper')
        if repeat_gateway and repeat_helper and (repeat_gateway, repeat_helper) not in edge_set:
            if pd.notna(group.get('repeat_name')):
                dot.edge(repeat_gateway, repeat_helper, label=group['repeat_name'])
            else:
                dot.edge(repeat_gateway, repeat_helper)
            edge_set.add((repeat_gateway, repeat_helper))
        # Connect helper to first real node (unchanged)
        if repeat_helper and first_real_node and (repeat_helper, first_real_node) not in edge_set:
            dot.edge(repeat_helper, first_real_node)
            edge_set.add((repeat_helper, first_real_node))

    return first_node, last_node


# Main function (for completeness)
def build_workflow_diagram(updated_nodes, updated_groups):
    dot = Digraph(format='svg', graph_attr={'rankdir': 'LR', 'splines': 'ortho', 'fontname': 'sans-serif'},
                  node_attr={'fontname': 'sans-serif'}, edge_attr={'fontname': 'sans-serif'})
    dot.node('start', shape='circle', label='', width='0.5', height='0.5')
    dot.node('end', shape='circle', label='', width='0.5', height='0.5')
    edge_set = set()

    top_group_id = updated_groups[updated_groups['parent_group_id'].isna()].index[0]
    with dot.subgraph(name=f'cluster_{top_group_id}', graph_attr={
        'label': updated_groups.loc[top_group_id, 'name'],
        'style': 'dashed'
    }) as c:
        first_node, last_node = add_group(top_group_id, c, updated_nodes, updated_groups, edge_set, set())

    dot.edge('start', first_node)
    dot.edge(last_node, 'end')
    return dot

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
            # st.markdown(updated_nodes.to_dict())
            # st.markdown(updated_groups.to_dict())
            
            # Display the workflow diagram
            try:
                st.subheader("Workflow Diagram")
                diagram = build_workflow_diagram(updated_nodes, updated_groups)
                diagram.render('workflow_diagram', view=True)
            except Exception as e:
                st.error(f"Error generating workflow diagram: {str(e)}")
                st.exception(e)
        except Exception as e:
            st.error(f"Error in generate_additional_nodes: {str(e)}")
            st.exception(e)
        

