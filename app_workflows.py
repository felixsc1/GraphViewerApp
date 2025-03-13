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
    if pd.isna(parent_str):
        return None
    return parent_str.split(":")[0]  # Strips suffix like ":SequentialActivity"

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
    all_activities["gateway_type"] = ""
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
                "gateway_type": ["parallel"], "sub_steps": [""], "next": [""],
                "group": [group_activities["group"].iloc[0] if not group_activities["group"].isna().all() else ""]
            })
            merge_seq = group_activities["seq"].max() + 0.5
            merge_row = pd.DataFrame({
                "seq": [merge_seq], "type": ["gateway"], "name": ["Parallel Merge"], "responsible": [""],
                "gateway_type": ["parallel"], "sub_steps": [""], "next": [""],
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
        elif row["type"] == "gateway" and row["gateway_type"] == "parallel" and "Split" in row["name"]:
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
    workflow_table = all_activities[["seq", "type", "name", "responsible", "gateway_type", "sub_steps", "next", "group", "parent"]]
    
    return workflow_table


def add_parallel_conditions(workflow_table, xls):
    branch_info_df = pd.read_excel(xls, "Zweiginformation")
    condition_df = pd.read_excel(xls, "Bedingung für Zweig")
    
    # Add new columns to workflow_table
    workflow_table["condition"] = ""
    workflow_table["condition_name"] = ""
    
    # Get column names
    # parallel_activity_col = get_column_name(branch_info_df.columns, "ParallelActivity")
    # transport_id_col = get_column_name(condition_df.columns, "TransportID")
    # base_branch_info_col = get_column_name(branch_info_df.columns, "BaseBranchInfo")
    # display_as_col = get_column_name(condition_df.columns, "Anzeigen als")
    # expression_col = get_column_name(condition_df.columns, "Ausdruck")
    
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

def generate_graphviz_diagram(workflow_table):
    dot = Digraph(comment='Workflow', format='png')
    dot.attr(rankdir='TB')
    
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


# --- Main App Structure ---

def show():
    initialize_state()
    upload_user_list()
    xls = upload_dossier()
    workflow_table = generate_workflow_table(xls)
    workflow_table = add_parallel_conditions(workflow_table, xls)
    st.dataframe(workflow_table)
    generate_graphviz_diagram(workflow_table)
