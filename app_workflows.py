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

def get_column_name(columns, starts_with):
    """Helper function to find column that starts with given string"""
    matching_cols = [col for col in columns if col.startswith(starts_with)]
    if matching_cols:
        # Strip any leading/trailing whitespace characters from the column names
        return matching_cols[0].strip()
    return None

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
            
            
            
# --- Generating Workflow Table ---

def upload_dossier():
    uploaded_file = st.file_uploader("Upload Dossier", type=["xlsx"])
    if uploaded_file is not None:
        xls = pd.ExcelFile(uploaded_file)
        return xls
    
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

def generate_workflow_table(xls):
    # Read relevant sheets
    activity_df = pd.read_excel(xls, "Aktivität")
    command_activity_df = pd.read_excel(xls, "Befehlsaktivität")
    sequential_placeholder_df = pd.read_excel(xls, "Platzhalter für sequentielle Ak")
    parallel_placeholder_df = pd.read_excel(xls, "Platzhalter für parallele Aktiv")
    process_df = pd.read_excel(xls, "Prozess")
    branch_info_df = pd.read_excel(xls, "Zweiginformation")
    condition_df = pd.read_excel(xls, "Bedingung für Zweig")

    # Step 1: Prepare activities
    activities = activity_df[[
        get_column_name(activity_df.columns, "TransportID"),
        get_column_name(activity_df.columns, "Name:de"),
        get_column_name(activity_df.columns, "Empfänger"),
        get_column_name(activity_df.columns, "SequenceNumber"),
        get_column_name(activity_df.columns, "ParentActivity")
    ]]
    activities.columns = ["id", "name", "responsible", "sequence", "parent"]
    activities["parent"] = activities["parent"].apply(extract_id)

    command_activities = command_activity_df[[
        get_column_name(command_activity_df.columns, "TransportID"),
        get_column_name(command_activity_df.columns, "Befehl"),
        get_column_name(command_activity_df.columns, "SequenceNumber"),
        get_column_name(command_activity_df.columns, "ParentActivity")
    ]]
    command_activities["responsible"] = "system"
    command_activities.columns = ["id", "name", "sequence", "parent", "responsible"]

    # Extract ID from the command/Befehl column
    command_activities["name"] = command_activities["name"].apply(extract_id)

    # Process parent column as before
    command_activities["parent"] = command_activities["parent"].apply(extract_id)

    all_activities = pd.concat([activities, command_activities], ignore_index=True)
    all_activities["type"] = "activity"

    # Step 2: Identify groups with names
    seq_groups = sequential_placeholder_df[[
        get_column_name(sequential_placeholder_df.columns, "TransportID"),
        get_column_name(sequential_placeholder_df.columns, "Name:de"),
        get_column_name(sequential_placeholder_df.columns, "ParentActivity")
    ]]
    seq_groups.columns = ["id", "name", "parent"]
    seq_groups["parent"] = seq_groups["parent"].apply(extract_id)

    par_groups = parallel_placeholder_df[[
        get_column_name(parallel_placeholder_df.columns, "TransportID"),
        get_column_name(parallel_placeholder_df.columns, "Name:de"),
        get_column_name(parallel_placeholder_df.columns, "ParentActivity")
    ]]
    par_groups.columns = ["id", "name", "parent"]
    par_groups["parent"] = par_groups["parent"].apply(extract_id)

    # Combine all groups without filtering
    all_groups = pd.concat([seq_groups, par_groups], ignore_index=True)

    # Use the updated function
    def find_nearest_group(activity_parent, groups):
        if pd.isna(activity_parent):
            return None
            
        # Build a parent-child relationship dictionary for faster lookups
        parent_map = {}
        for _, row in groups.iterrows():
            parent_map[row['id']] = row['parent']
            
        # Build a name dictionary for faster lookups
        name_map = {}
        for _, row in groups.iterrows():
            if pd.notna(row['name']) and row['name'] != "":
                name_map[row['id']] = row['name']
        
        # Traverse up the hierarchy
        current = activity_parent
        visited = set()
        
        while current and current not in visited:
            visited.add(current)
            
            # Check if current has a name
            if current in name_map:
                return name_map[current]
                
            # Move up to parent
            if current in parent_map and pd.notna(parent_map[current]):
                current = parent_map[current]
            else:
                # If not in our map, try to find in activities
                matching_activities = all_activities[all_activities["id"] == current]
                if not matching_activities.empty and pd.notna(matching_activities["parent"].iloc[0]):
                    current = matching_activities["parent"].iloc[0]
                else:
                    break
                    
        return None

    # Apply to activities
    all_activities["group"] = all_activities["parent"].apply(
        lambda x: find_nearest_group(x, all_groups)
    )

    # Step 3: Assign sequence numbers and infer flow
    all_activities = all_activities.sort_values(by=["group", "sequence"]).reset_index(drop=True)
    all_activities["seq"] = range(1, len(all_activities) + 1)
    all_activities["sub_steps"] = ""
    all_activities["next"] = ""

    # Step 4: Handle parallel activities and gateways
    parallel_groups = par_groups[par_groups["name"].notna() & (par_groups["name"] != "")]["id"].tolist()
    for group_id in parallel_groups:
        group_activities = all_activities[all_activities["parent"] == group_id]
        if len(group_activities) > 1:
            split_seq = group_activities["seq"].min() - 0.5
            split_row = pd.DataFrame({
                "seq": [split_seq], "type": ["gateway"], "name": ["Parallel Split"], "responsible": [""],
                "sub_steps": [""], "next": [""],
                "group": [group_activities["group"].iloc[0] if not group_activities["group"].isna().all() else ""]
            })
            merge_seq = group_activities["seq"].max() + 0.5
            merge_row = pd.DataFrame({
                "seq": [merge_seq], "type": ["gateway"], "name": ["Parallel Merge"], "responsible": [""],
                "sub_steps": [""], "next": [""],
                "group": [group_activities["group"].iloc[0] if not group_activities["group"].isna().all() else ""]
            })
            all_activities = pd.concat([all_activities, split_row, merge_row], ignore_index=True)

    all_activities = all_activities.sort_values("seq").reset_index(drop=True)
    all_activities["seq"] = range(1, len(all_activities) + 1)

    # Step 5: Define the "next" column
    for i, row in all_activities.iterrows():
        if row["type"] == "activity":
            next_idx = i + 1
            if next_idx < len(all_activities):
                all_activities.at[i, "next"] = str(all_activities.at[next_idx, "seq"])
        elif row["type"] == "gateway" and "Split" in row["name"]:
            group_activities = all_activities[(all_activities["group"] == row["group"]) &
                                              (all_activities["type"] == "activity") &
                                              (all_activities["seq"] > row["seq"])]
            next_seqs = group_activities["seq"].tolist()
            all_activities.at[i, "next"] = ",".join(map(str, next_seqs))

    # Step 6: Check for sequential activities inside parallel activities
    # Create a mapping from sequential placeholder IDs to their parallel parent IDs
    seq_to_parallel_map = {}
    for _, seq_row in sequential_placeholder_df.iterrows():
        seq_id = seq_row[get_column_name(sequential_placeholder_df.columns, "TransportID")]
        seq_parent = seq_row[get_column_name(sequential_placeholder_df.columns, "ParentActivity")]
        seq_parent_id = extract_id(seq_parent) if not pd.isna(seq_parent) else None
        
        # Check if this sequential activity's parent is in parallel_placeholder_df
        if seq_parent_id:
            for _, par_row in parallel_placeholder_df.iterrows():
                par_id = par_row[get_column_name(parallel_placeholder_df.columns, "TransportID")]
                if seq_parent_id == par_id:
                    seq_to_parallel_map[seq_id] = par_id
                    break
    
    # Update parent column for activities whose parent is in the mapping
    for i, row in all_activities.iterrows():
        if pd.notna(row["parent"]) and row["parent"] in seq_to_parallel_map:
            all_activities.at[i, "parent"] = seq_to_parallel_map[row["parent"]]

    # Finalize the table
    workflow_table = all_activities[["seq", "id", "type", "name", "responsible", "sub_steps", "next", "group", "parent"]]
    
    # Reset index to ensure it's dropped in the returned DataFrame
    workflow_table = workflow_table.reset_index(drop=True)
    
    return workflow_table


def add_parallel_conditions(workflow_table, xls):
    branch_info_df = pd.read_excel(xls, "Zweiginformation")
    condition_df = pd.read_excel(xls, "Bedingung für Zweig")
    
    # Add new columns to workflow_table
    workflow_table["condition"] = ""
    workflow_table["condition_name"] = ""
    
    # Create a dictionary to map parallel activities to their conditions
    parallel_conditions = {}
    for _, row in branch_info_df.iterrows():
        parallel_id = extract_id(row[get_column_name(branch_info_df.columns, "ParallelActivity")])
        if parallel_id not in parallel_conditions:
            parallel_conditions[parallel_id] = []
        parallel_conditions[parallel_id].append(row[get_column_name(condition_df.columns, "TransportID")])
    
    # Create a dictionary to map condition IDs to branch info
    condition_to_branch = {}
    for _, row in condition_df.iterrows():
        base_branch = row[get_column_name(condition_df.columns, "BaseBranchInfo")]
        base_branch_id = extract_id(base_branch)
        if base_branch_id:
            condition_to_branch[base_branch_id] = {
                'name': row[get_column_name(condition_df.columns, "Anzeigen als")],
                'expression': row[get_column_name(condition_df.columns, "Ausdruck")]
            }
    
    # Process each parent in workflow_table
    for parent_value in workflow_table["parent"].unique():
        if pd.isna(parent_value):
            continue
            
        # Check if this parent exists in our parallel conditions dictionary
        if parent_value in parallel_conditions:
            # Get activities with this parent
            parent_activities = workflow_table[workflow_table["parent"] == parent_value]
            
            # Get conditions for this parent
            conditions = parallel_conditions[parent_value]
            
            # Match activities with conditions based on order
            for i, (idx, activity_row) in enumerate(parent_activities.iterrows()):
                if i < len(conditions):
                    condition_id = conditions[i]
                    
                    # Find matching branch info
                    if condition_id in condition_to_branch:
                        branch_info = condition_to_branch[condition_id]
                        # Update workflow_table with condition info
                        workflow_table.loc[idx, "condition_name"] = branch_info['name']
                        workflow_table.loc[idx, "condition"] = branch_info['expression']
    
    return workflow_table


def resolve_responsible_usernames(workflow_table, xls):
    user_dict = st.session_state['user_dict']
    empfaenger_df = pd.read_excel(xls, "Empfänger")
    
    # Get the actual column names from empfaenger_df
    transport_id_col = get_column_name(empfaenger_df.columns, 'TransportID')
    gruppe_col = get_column_name(empfaenger_df.columns, 'Gruppe')
    dynamic_recipient_col = get_column_name(empfaenger_df.columns, 'DynamicRecipientIdentifier')
    benutzer_col = get_column_name(empfaenger_df.columns, 'Benutzer')
    
    # Create a copy to avoid SettingWithCopyWarning
    workflow_table = workflow_table.copy()
    
    # Process each row in workflow_table
    for idx, row in workflow_table.iterrows():
        if pd.isna(row['responsible']) or row['responsible'] == 'system':
            continue
            
        # Extract ID from responsible field
        resp_id = extract_id(row['responsible'])
        if not resp_id:
            continue
            
        # Find matching row in empfaenger_df
        matching_rows = empfaenger_df[empfaenger_df[transport_id_col] == resp_id]
        
        if matching_rows.empty:
            continue
            
        matching_row = matching_rows.iloc[0]
        
        # Case 1: Check for Benutzer first (highest priority)
        if benutzer_col and pd.notna(matching_row[benutzer_col]) and matching_row[benutzer_col]:
            user_id = extract_id(matching_row[benutzer_col])
            if user_id and user_id in user_dict:
                workflow_table.at[idx, 'responsible'] = user_dict[user_id]
                continue  # Skip other checks
        
        # Case 2: Check for DynamicRecipientIdentifier
        elif dynamic_recipient_col and pd.notna(matching_row[dynamic_recipient_col]) and matching_row[dynamic_recipient_col]:
            workflow_table.at[idx, 'responsible'] = "FFOG"
            
        # Case 3: Check for Gruppe
        elif gruppe_col and pd.notna(matching_row[gruppe_col]) and matching_row[gruppe_col]:
            gruppe_value = matching_row[gruppe_col]
            # Handle BAKOM-TP-NA:TenantGroup pattern
            if gruppe_value.startswith("BAKOM-") and ":" in gruppe_value:
                # Extract the middle part between "BAKOM-" and ":"
                parts = gruppe_value.split(":", 1)
                prefix = parts[0]
                if prefix.startswith("BAKOM-"):
                    gruppe_value = prefix[6:]  # Remove "BAKOM-" prefix
            # Handle simpler cases
            elif gruppe_value.startswith("BAKOM-"):
                gruppe_value = gruppe_value[6:]
            # Handle any other prefix beginning with colon
            elif ":" in gruppe_value:
                gruppe_value = gruppe_value.split(":", 1)[1]
                
            workflow_table.at[idx, 'responsible'] = gruppe_value
    
    return workflow_table


def add_sub_steps(workflow_table, xls):
    sub_steps_df = pd.read_excel(xls, "Manueller Arbeitsschritt")
    activity_col = get_column_name(sub_steps_df.columns, "Activity")
    sub_step_col = get_column_name(sub_steps_df.columns, "Name")
    
    # Create a copy to avoid SettingWithCopyWarning
    workflow_table = workflow_table.copy()
    
    # Process each activity in the workflow table
    for idx, row in workflow_table.iterrows():
        if pd.isna(row['id']):
            continue
            
        # Find all matching sub-steps for this activity
        activity_id = row['id']
        matching_rows = sub_steps_df[sub_steps_df[activity_col].apply(
            lambda x: pd.notna(x) and extract_id(x) == activity_id
        )]
        
        if matching_rows.empty:
            continue
            
        # Collect and clean sub-step names
        sub_steps = []
        for _, sub_step_row in matching_rows.iterrows():
            sub_step_name = sub_step_row[sub_step_col]
            if pd.notna(sub_step_name):
                # Remove any suffix that begins with parentheses
                if "(" in sub_step_name:
                    sub_step_name = sub_step_name.split("(")[0].strip()
                sub_steps.append(sub_step_name)
        
        # Add the sub-steps to the workflow table
        if sub_steps:
            workflow_table.at[idx, 'sub_steps'] = "; ".join(sub_steps)
    
    return workflow_table


def generate_graphviz_diagram(workflow_table):
    dot = Digraph(comment='Workflow', format='png')
    dot.attr(rankdir='LR')
    
    # Create nodes first
    for _, row in workflow_table.iterrows():
        seq = str(row['seq'])
        if row['type'] == 'activity':
            dot.node(seq, label=f"{row['name']}\n({row['responsible']})", shape='box')
        elif row['type'] == 'gateway':
            dot.node(seq, shape='diamond')
    
    # Create edges
    for _, row in workflow_table.iterrows():
        seq = str(row['seq'])
        next_seqs = row['next'].split(",") if row['next'] else []
        for next_seq in next_seqs:
            if next_seq.strip():
                dot.edge(seq, next_seq.strip())
    
    # Group nodes by their group value
    groups = workflow_table[workflow_table['group'].notna() & (workflow_table['group'] != '')]['group'].unique()
    
    # Create subgraphs for each group
    for group_name in groups:
        with dot.subgraph(name=f"cluster_{group_name}") as c:
            c.attr(label=group_name, labeljust='l', style='dotted', color='black')
            
            # Add all nodes that belong to this group
            group_rows = workflow_table[workflow_table['group'] == group_name]
            for _, row in group_rows.iterrows():
                c.node(str(row['seq']))
    
    dot.render('workflow_diagram', view=True)
 
def create_activity_label(name, responsible, sub_steps=None, max_chars=25):
    """
    Create a label for an activity node with automatic text wrapping.
    
    Args:
        name: The name of the activity
        responsible: The person responsible
        sub_steps: Optional steps to display
        max_chars: Maximum characters per line before wrapping
    """
    # Create HTML table-based layout
    label = '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="2" WIDTH="200">'
    
    # First row: Responsible person in upper left with emoji
    if responsible.lower() == 'system':
        resp_text = '⚙️ System'
    else:
        resp_text = f'👤 {responsible}'
    
    label += f'<TR><TD ALIGN="left"><FONT FACE="Arial, Helvetica, sans-serif" POINT-SIZE="10">{resp_text}</FONT></TD></TR>'
    
    # Second row: Activity name centered with automatic line breaks
    wrapped_name = wrap_text(name, max_chars)
    label += f'<TR><TD ALIGN="center"><FONT FACE="Arial, Helvetica, sans-serif"><B>{wrapped_name}</B></FONT></TD></TR>'
    
    # Add sub-steps if available
    if sub_steps and pd.notna(sub_steps) and sub_steps.strip():
        steps = sub_steps.split('; ')
        for step in steps:
            wrapped_step = wrap_text(step, max_chars)
            label += f'<TR><TD ALIGN="left"><FONT FACE="Arial, Helvetica, sans-serif" POINT-SIZE="9">{wrapped_step}</FONT></TD></TR>'
    
    label += '</TABLE>>'
    return label

def wrap_text(text, max_chars):
    """
    Wrap text at word boundaries to fit within max_chars per line.
    
    Args:
        text: The text to wrap
        max_chars: Maximum characters per line
    
    Returns:
        String with <BR/> tags inserted for line breaks
    """
    if len(text) <= max_chars:
        return text
        
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        # Check if adding this word exceeds the maximum length
        if current_length + len(word) + len(current_line) > max_chars:
            # Add the current line to lines and start a new one
            if current_line:  # Only if we have words in the current line
                lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
            else:
                # If a single word is longer than max_chars, add it anyway
                current_line.append(word)
                lines.append(' '.join(current_line))
                current_line = []
                current_length = 0
        else:
            # Add the word to the current line
            current_line.append(word)
            current_length += len(word)
    
    # Add any remaining words
    if current_line:
        lines.append(' '.join(current_line))
    
    # Join lines with HTML line breaks
    return '<BR/>'.join(lines)

def generate_workflow_diagram(df, output_file='workflow_diagram', view=True):
    """Generate a BPMN-style diagram from a DataFrame."""
    # Change format from png to svg for better emoji support
    dot = Digraph(comment='Workflow Diagram', format='svg')
    # Set global font attributes to use a clean sans-serif font
    dot.attr('graph', fontname='Arial')
    dot.attr('node', fontname='Arial')
    dot.attr('edge', fontname='Arial')
    dot.attr(rankdir='LR')
    
    # Set node attributes to fix width
    dot.attr('node', width='2.5', height='0', fixedsize='false')

    # Add start and end events
    dot.node('start', shape='circle', label='', width='0.3')
    dot.node('end', shape='circle', style='bold', label='', width='0.3')

    # Sort DataFrame by seq for overall order, though we'll ignore seq within parallel groups
    df = df.sort_values('seq')
    groups = df['group'].unique()

    # Step 1: Identify parallel groups
    parallel_groups = set()
    for group in groups:
        group_df = df[df['group'] == group]
        if (group_df['condition'].notna().any() or group_df['condition_name'].notna().any()) and not (group_df['condition'].eq('').any() and group_df['condition_name'].eq('').any()):
            parallel_groups.add(group)

    # Step 2: Create subgraphs for each group
    for group in groups:
        with dot.subgraph(name=f'cluster_{group}') as c:
            c.attr(label=group, style='dashed', labeljust='l', labelloc='t')
            group_df = df[df['group'] == group]
            if group in parallel_groups:
                # Add split gateway
                split_gateway = f'split_{group}'
                c.node(split_gateway, shape='diamond', label='X', width='0.3')
                # Add activities on the same rank
                with c.subgraph() as s:
                    s.attr(rank='same')
                    for _, row in group_df.iterrows():
                        node_id = str(row['id'])
                        label = create_activity_label(row['name'], row['responsible'], row['sub_steps'])
                        s.node(node_id, label=label, shape='box', style='rounded')
                # Add join gateway
                join_gateway = f'join_{group}'
                c.node(join_gateway, shape='diamond', label='X', width='0.3')
            else:
                # Sequential group: add activities without gateways
                for _, row in group_df.iterrows():
                    node_id = str(row['id'])
                    label = create_activity_label(row['name'], row['responsible'], row['sub_steps'])
                    c.node(node_id, label=label, shape='box', style='rounded')

    # Step 3: Connect activities within sequential groups only
    for group in groups:
        if group not in parallel_groups:
            group_df = df[df['group'] == group]
            for i in range(len(group_df) - 1):
                current_id = str(group_df.iloc[i]['id'])
                next_id = str(group_df.iloc[i + 1]['id'])
                dot.edge(current_id, next_id)

    # Step 4: Connect activities within parallel groups via gateways
    for group in parallel_groups:
        split_gateway = f'split_{group}'
        join_gateway = f'join_{group}'
        group_df = df[df['group'] == group]
        for _, row in group_df.iterrows():
            node_id = str(row['id'])
            # Add condition label if present
            condition_label = (f"{row['condition_name']} {row['condition']}"
                             if pd.notna(row['condition']) and pd.notna(row['condition_name']) else '')
            dot.edge(split_gateway, node_id, label=condition_label)
            dot.edge(node_id, join_gateway)

    # Step 5: Connect between groups
    group_order = df.groupby('group')['seq'].min().sort_values().index.tolist()
    for i in range(len(group_order) - 1):
        current_group = group_order[i]
        next_group = group_order[i + 1]
        current_group_df = df[df['group'] == current_group]
        next_group_df = df[df['group'] == next_group]

        # Determine exit point of current group
        if current_group in parallel_groups:
            current_exit = f'join_{current_group}'
        else:
            current_exit = str(current_group_df.iloc[-1]['id'])

        # Determine entry point of next group
        if next_group in parallel_groups:
            next_entry = f'split_{next_group}'
        else:
            next_entry = str(next_group_df.iloc[0]['id'])

        dot.edge(current_exit, next_entry)

    # Step 6: Connect start to first group
    first_group = group_order[0]
    first_group_df = df[df['group'] == first_group]
    first_entry = f'split_{first_group}' if first_group in parallel_groups else str(first_group_df.iloc[0]['id'])
    dot.edge('start', first_entry)

    # Step 7: Connect last group to end
    last_group = group_order[-1]
    last_group_df = df[df['group'] == last_group]
    last_exit = f'join_{last_group}' if last_group in parallel_groups else str(last_group_df.iloc[-1]['id'])
    dot.edge(last_exit, 'end')

    # Render the diagram
    dot.render(output_file, view=view)


# --- Main App Structure ---

def show():
    initialize_state()
    upload_user_list()
    xls = upload_dossier()
    if xls is not None:
        workflow_table = generate_workflow_table(xls)
        workflow_table = add_parallel_conditions(workflow_table, xls)
        workflow_table = resolve_responsible_usernames(workflow_table, xls)
        workflow_table = add_sub_steps(workflow_table, xls)
        st.dataframe(workflow_table)
        # generate_graphviz_diagram(workflow_table)
        generate_workflow_diagram(workflow_table)
