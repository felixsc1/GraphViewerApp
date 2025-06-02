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
import json
import base64


def initialize_state():
    # Create workflows directory if it doesn't exist
    workflows_dir = os.path.join(st.session_state["cwd"], "data", "workflows")
    os.makedirs(workflows_dir, exist_ok=True)

    # Default user dictionary entry
    default_user_dict = {
        "3639e0c9-14a3-4021-9d95-c5ea60d296b6": "FFOG",
        "43b07445-67a7-4c1b-9f51-f91da288add9": "FFOE",
        "bdb15dcd-1c1c-4e7c-8ffa-4654c3c3f9f1": "FFMG",
        "ad319f3a-c5f8-4f3c-a737-63eec86ddf12": "PEMG",
        "b1ad934c-7efb-4b82-aa20-5bfc555cdad8": "PEOG",
        "f931b8d3-0d53-48cf-823f-76585736d041": "SB",
        "96a9a6a3-91e3-46f6-8da6-3d85173c2a98": "SGP",
        "ca278b77-7de4-42f5-afa9-3d1e802dfa72": "SGÜP",
        "fff9f05c-55c8-4778-ae13-e9782f684b86": "ZREG",
        "402b1d27-2c02-41a5-bf37-77ba2a74ae1a": "ÜGFOA",
    }

    # Create legend dictionary
    default_user_legend = {
        "FFOE": "Federführende Organisationseinheit",
        "FFMG": "Federführung mit Gruppenbeteiligung",
        "FFOG": "Federführung ohne Gruppenbeteiligung",
        "PEMG": "Prozesseigentümer mit Gruppe",
        "PEOG": "Prozesseigentümer ohne Gruppe",
        "SB": "Sicherheitsbeauftragter",
        "SGP": "Stelle in der Gruppe des Prozesseigentümers",
        "SGÜP": "Stelle in der übergeordneten Gruppe des Prozesseigentümers",
        "ZREG": "Zuständige Registratur",
        "ÜGFOA": "Übergeordnete Gruppe der federführenden Organisationseinheit des Aktivitätsobjekts",
    }

    default_standard_activities = ["DialogPortal", "Mdg", "Hintergrundaktivität"]

    # Load existing dictionaries from the pickle file, if possible
    pickle_path = os.path.join(workflows_dir, "user_dict.pickle")
    loaded_dict = {}
    loaded_legend = {}
    if os.path.exists(pickle_path):
        try:
            with open(pickle_path, "rb") as f:
                data = pickle.load(f)
                loaded_dict = data.get("user_dict", {})
                loaded_legend = data.get("user_legend", {})
                loaded_standard_activities = data.get("standard_activities", [])
        except Exception as e:
            st.error(f"Benutzerliste konnte nicht geladen werden: {str(e)}")

    # Always update the dictionaries with the default entries
    loaded_dict.update(default_user_dict)
    loaded_legend.update(default_user_legend)
    st.session_state["user_dict"] = loaded_dict
    st.session_state["user_legend"] = loaded_legend
    st.session_state["standard_activities"] = loaded_standard_activities

    # Save the updated dictionaries
    with open(pickle_path, "wb") as f:
        pickle.dump(
            {
                "user_dict": loaded_dict,
                "user_legend": loaded_legend,
                "standard_activities": default_standard_activities,
            },
            f,
        )


def upload_user_list():
    uploaded_files = st.file_uploader(
        "Upload exported list for Benutzer / Gruppen / Stellen",
        type=["xlsx"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        try:
            # Initialize dictionaries if they don't exist
            if "user_dict" not in st.session_state:
                st.session_state["user_dict"] = {}
            if "user_legend" not in st.session_state:
                st.session_state["user_legend"] = {}

            # Track processed files to avoid duplicates
            if "processed_files" not in st.session_state:
                st.session_state["processed_files"] = set()

            # Process each uploaded file
            for uploaded_file in uploaded_files:
                # Skip if we've already processed this file
                file_hash = hashlib.md5(uploaded_file.getvalue()).hexdigest()
                if file_hash in st.session_state["processed_files"]:
                    continue

                st.session_state["processed_files"].add(file_hash)

                # Read the second sheet of the Excel file
                df = pd.read_excel(uploaded_file, sheet_name=1, header=0)

                # Get the actual column names
                transport_id_col = get_column_name(df.columns, "TransportID")
                vorname_col = get_column_name(df.columns, "Vorname")
                nachname_col = get_column_name(df.columns, "Nachname")
                name_de_col = get_column_name(df.columns, "Name:de")
                name_abbreviation_col = get_column_name(
                    df.columns, "Erweiterte Einstellungen.Zeichen"
                )
                kurzbezeichnung_col = get_column_name(df.columns, "Kurzbezeichnung:de")

                # Check if TransportID is found
                if not transport_id_col:
                    st.error(
                        f"Could not find column starting with: TransportID in {uploaded_file.name}"
                    )
                    continue

                # Determine how to create user names
                use_names = vorname_col and nachname_col
                use_kurzbezeichnung = kurzbezeichnung_col is not None
                use_name_de = name_de_col is not None

                if not (use_names or use_kurzbezeichnung or use_name_de):
                    st.error(
                        f"Could not find either (Vorname and Nachname), Kurzbezeichnung:de, or Name:de columns in {uploaded_file.name}"
                    )
                    continue

                # Load existing dictionaries from session state
                user_dict = st.session_state.get("user_dict", {}).copy()
                user_legend = st.session_state.get("user_legend", {}).copy()

                # Create reverse lookup for name combinations to abbreviations
                name_to_abbr = {v: k for k, v in user_legend.items()}

                # Add new entries to user_dict and user_legend
                for _, row in df.iterrows():
                    transport_id = row[transport_id_col]

                    # Skip rows with missing TransportID
                    if pd.isna(transport_id):
                        continue

                    transport_id = str(transport_id)

                    # Skip if this TransportID already exists
                    if transport_id in user_dict:
                        continue

                    # Get the full name (for legend)
                    full_name = None
                    if (
                        use_names
                        and pd.notna(row[vorname_col])
                        and pd.notna(row[nachname_col])
                    ):
                        full_name = f"{row[vorname_col]} {row[nachname_col]}"
                    elif use_kurzbezeichnung and pd.notna(row[kurzbezeichnung_col]):
                        full_name = row[kurzbezeichnung_col]
                    elif use_name_de and pd.notna(row[name_de_col]):
                        full_name = row[name_de_col]

                    # Skip if we can't determine a name
                    if not full_name:
                        continue

                    # Case 1: We have Vorname/Nachname (need abbreviation)
                    if (
                        use_names
                        and pd.notna(row[vorname_col])
                        and pd.notna(row[nachname_col])
                    ):
                        # Check if we already have an abbreviation for this name
                        if full_name in name_to_abbr:
                            user_dict[transport_id] = name_to_abbr[full_name]
                            continue

                        # Get or generate the abbreviation
                        abbreviation = None
                        if name_abbreviation_col and pd.notna(
                            row.get(name_abbreviation_col)
                        ):
                            abbreviation = str(row[name_abbreviation_col]).strip()

                        # Generate abbreviation if not provided or empty
                        if not abbreviation:
                            # First two letters of last name + first letter of first name
                            last_part = (
                                row[nachname_col][:2].upper()
                                if pd.notna(row[nachname_col])
                                else ""
                            )
                            first_part = (
                                row[vorname_col][:1].upper()
                                if pd.notna(row[vorname_col])
                                else ""
                            )
                            base_abbr = f"{last_part}{first_part}".lower()

                            # Handle duplicates
                            if base_abbr in user_legend:
                                counter = 1
                                while f"{base_abbr}{counter}" in user_legend:
                                    counter += 1
                                abbreviation = f"{base_abbr}{counter}"
                            else:
                                abbreviation = base_abbr

                        # Update dictionaries
                        if abbreviation:
                            user_dict[transport_id] = abbreviation
                            user_legend[abbreviation] = full_name
                            name_to_abbr[full_name] = abbreviation

                    # Case 2: Use Kurzbezeichnung:de if available
                    elif use_kurzbezeichnung and pd.notna(row[kurzbezeichnung_col]):
                        user_dict[transport_id] = full_name

                    # Case 3: Fallback to Name:de (use directly without abbreviation)
                    elif use_name_de and pd.notna(row[name_de_col]):
                        user_dict[transport_id] = full_name

                # Update session state with new entries
                st.session_state["user_dict"].update(user_dict)
                st.session_state["user_legend"].update(user_legend)

            # Save to pickle file after processing all files
            workflows_dir = os.path.join(st.session_state["cwd"], "data", "workflows")
            pickle_path = os.path.join(workflows_dir, "user_dict.pickle")
            with open(pickle_path, "wb") as f:
                pickle.dump(
                    {
                        "user_dict": st.session_state["user_dict"],
                        "user_legend": st.session_state["user_legend"],
                    },
                    f,
                )

        except Exception as e:
            st.error(f"Error processing files: {str(e)}")
            st.exception(e)


def modify_user_entries():
    """Handles displaying and editing user entries in the User Management section."""
    st.subheader("Current Entries")
    if st.session_state["user_dict"] or st.session_state["user_legend"]:
        # Create a DataFrame for display
        entries = []
        for transport_id, abbr in st.session_state["user_dict"].items():
            full_name = st.session_state["user_legend"].get(abbr, "")
            entries.append(
                {
                    "Transport ID": transport_id,
                    "Display Name": abbr,
                    "Full Name": full_name,
                }
            )
        df = pd.DataFrame(entries)
        st.dataframe(df)

        # Allow editing
        st.subheader("Edit Entries")
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_id = st.selectbox(
                "Select ID to Edit",
                options=list(st.session_state["user_dict"].keys()),
                key="edit_id",
            )
        with col2:
            new_abbr = st.text_input(
                "New Display Name",
                value=st.session_state["user_dict"].get(selected_id, ""),
                key="edit_abbr",
            )
        with col3:
            new_full_name = st.text_input(
                "New Full Name (Optional, for Legend)",
                value=st.session_state["user_legend"].get(
                    st.session_state["user_dict"].get(selected_id, ""), ""
                ),
                key="edit_full_name",
            )

        if st.button("Save Changes"):
            # Update session state
            old_abbr = st.session_state["user_dict"][selected_id]
            st.session_state["user_dict"][selected_id] = new_abbr
            if old_abbr in st.session_state["user_legend"]:
                del st.session_state["user_legend"][old_abbr]
            if new_full_name:
                st.session_state["user_legend"][new_abbr] = new_full_name

            # Save to pickle
            workflows_dir = os.path.join(st.session_state["cwd"], "data", "workflows")
            pickle_path = os.path.join(workflows_dir, "user_dict.pickle")
            with open(pickle_path, "wb") as f:
                pickle.dump(
                    {
                        "user_dict": st.session_state["user_dict"],
                        "user_legend": st.session_state["user_legend"],
                    },
                    f,
                )
            st.success("Changes saved successfully!")

    # Add new entries
    st.subheader("Add New Entry")
    new_id = st.text_input("Transport ID", key="new_id")
    new_abbr = st.text_input("Display Name", key="new_abbr")
    new_full_name = st.text_input("Full Name", key="new_full_name")
    if st.button("Add Entry"):
        if new_id and new_abbr:
            st.session_state["user_dict"][new_id] = new_abbr
            if new_full_name:
                st.session_state["user_legend"][new_abbr] = new_full_name

            # Save to pickle
            workflows_dir = os.path.join(st.session_state["cwd"], "data", "workflows")
            pickle_path = os.path.join(workflows_dir, "user_dict.pickle")
            with open(pickle_path, "wb") as f:
                pickle.dump(
                    {
                        "user_dict": st.session_state["user_dict"],
                        "user_legend": st.session_state["user_legend"],
                    },
                    f,
                )
            st.success("New entry added successfully!")
        else:
            st.error("Transport ID and Display Name are required!")

    if st.button("⚠️ Reset Benutzerliste", type="primary"):
        # Reset session state
        st.session_state["user_dict"] = {}
        st.session_state["user_legend"] = {}

        # Delete the pickle file if it exists
        workflows_dir = os.path.join(st.session_state["cwd"], "data", "workflows")
        pickle_path = os.path.join(workflows_dir, "user_dict.pickle")
        try:
            if os.path.exists(pickle_path):
                os.remove(pickle_path)
                st.success("User list and pickle file successfully reset")
            else:
                st.info("No pickle file found to delete")
        except Exception as e:
            st.error(f"Error deleting pickle file: {str(e)}")
        else:
            st.info("User list has been reset")


def upload_dossier():
    uploaded_file = st.file_uploader("Excel File with Process Export", type=["xlsx"])
    if uploaded_file is not None:
        xls = pd.ExcelFile(uploaded_file)
        st.session_state["dossier_filename"] = uploaded_file.name.split(".")[0]
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
            matching_rows = empfaenger_df[
                empfaenger_df[transport_id_col] == empfaenger_id
            ]
            if matching_rows.empty:
                # Skip to final lookup in user_dict
                resolved_id = empfaenger_id
            else:
                # Potential recipient columns to check
                recipient_cols = [
                    "Benutzer",
                    "Stelle",
                    "Gruppe",
                    "Verteiler",
                    "DynamicRecipientIdentifier",
                ]

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
    if "user_dict" in st.session_state and resolved_id in st.session_state["user_dict"]:
        return st.session_state["user_dict"][resolved_id]

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
    common_column_patterns = [
        "TransportID",
        "Name:de",
        "ParentActivity",
        "SequenceNumber",
    ]
    activity_types = {"Aktivität": "manual", "Befehlsaktivität": "system"}

    # Step 3: Identify sheets based on standard_activities
    standard_activities_sheets = [
        sheet
        for sheet in xls.sheet_names
        if any(
            sheet.startswith(activity)
            for activity in st.session_state["standard_activities"]
        )
    ]

    # Step 4: Initialize a list to collect DataFrames from each sheet
    activities_list = []

    # Step 5: Process each relevant sheet
    for sheet_name in xls.sheet_names:
        # Check if the sheet is relevant
        if sheet_name in activity_types or sheet_name in standard_activities_sheets:
            # Read the sheet data
            df = pd.read_excel(xls, sheet_name=sheet_name)

            # Determine the activity type
            activity_type = activity_types.get(
                sheet_name, "script"
            )  # "script" for standard activity sheets

            # Map column patterns to actual column names in the dataframe
            column_mapping = {
                pattern: get_column_name(df.columns, pattern)
                for pattern in common_column_patterns
            }

            # Verify that all common columns exist in the sheet
            missing_cols = [
                pattern for pattern, col in column_mapping.items() if col is None
            ]
            if missing_cols:
                print(
                    f"Warning: Sheet '{sheet_name}' is missing columns: {missing_cols}"
                )
                continue  # Skip this sheet if critical columns are missing

            # Extract common columns
            temp_df = df[
                [column_mapping[pattern] for pattern in common_column_patterns]
            ].copy()
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
                temp_df["Empfänger"] = raw_empfaenger.apply(
                    lambda x: resolve_empfaenger(xls, x)
                )
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
        # print("All TransportIDs are unique.")
        pass

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
            manual_steps_df["CleanActivity"] = manual_steps_df[activity_col].apply(
                extract_id
            )

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
        "Platzhalter für parallele Aktiv": "parallel",
        "Platzhalter für Aktivitäten nac": "parallel",
    }

    # Initialize a list to collect group DataFrames
    groups_list = []

    # Process each group sheet
    for sheet_name, group_type in group_sheets.items():
        if sheet_name not in xls.sheet_names:
            # print(f"Warning: Sheet '{sheet_name}' not found in the Excel file.")
            continue

        df = pd.read_excel(xls, sheet_name=sheet_name)

        # Map column patterns to actual column names in the dataframe
        required_columns = [
            "TransportID",
            "Name:de",
            "ParentActivity",
            "SequenceNumber",
        ]
        column_mapping = {
            pattern: get_column_name(df.columns, pattern)
            for pattern in required_columns
        }

        # Verify that all common columns exist in the sheet
        missing_cols = [
            pattern for pattern, col in column_mapping.items() if col is None
        ]
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
                        "condition": row[skip_expr_col],
                    }

            # Track how many matches we find
            matches_found = 0

            for idx, row in groups_df.iterrows():
                skip_id = row.get("Überspringen, falls")
                if pd.notna(skip_id):
                    if skip_id in skip_dict:
                        groups_df.at[idx, "skip_name"] = skip_dict[skip_id]["name"]
                        groups_df.at[idx, "skip_condition"] = skip_dict[skip_id][
                            "condition"
                        ]
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
                        "condition": row[repeat_expr_col],
                    }

            # Track how many matches we find
            matches_found = 0

            for idx, row in groups_df.iterrows():
                repeat_id = row.get("Wiederholen, falls")
                if pd.notna(repeat_id):
                    if repeat_id in repeat_dict:
                        groups_df.at[idx, "repeat_name"] = repeat_dict[repeat_id][
                            "name"
                        ]
                        groups_df.at[idx, "repeat_condition"] = repeat_dict[repeat_id][
                            "condition"
                        ]
                        matches_found += 1

    # Handle parallel group branch conditions
    # This handles both regular parallel conditions (from Zweiginformation) and UserChoice conditions (from Optionsinformation)
    def process_branch_conditions(info_sheet_name, activity_col_pattern):
        """Process branch conditions from either Zweiginformation or Optionsinformation"""
        if (
            info_sheet_name not in xls.sheet_names
            or "Bedingung für Zweig" not in xls.sheet_names
        ):
            return

        branch_info = pd.read_excel(xls, info_sheet_name)
        branch_conditions = pd.read_excel(xls, "Bedingung für Zweig")

        # Get column names using the pattern matching function
        activity_col = get_column_name(branch_info.columns, activity_col_pattern)
        condition_col = get_column_name(branch_info.columns, "Condition")

        if not all([activity_col, condition_col]):
            return

        # Clean IDs by applying extract_id
        branch_info[condition_col] = branch_info[condition_col].apply(extract_id)
        branch_info[activity_col] = branch_info[activity_col].apply(extract_id)

        bc_transport_col = get_column_name(branch_conditions.columns, "TransportID")
        bc_name_col = get_column_name(branch_conditions.columns, "Anzeigen als")
        bc_expr_col = get_column_name(branch_conditions.columns, "Ausdruck")

        if not all([bc_transport_col, bc_name_col, bc_expr_col]):
            return

        branch_conditions = branch_conditions.set_index(bc_transport_col)

        for idx, row in groups_df[groups_df["type"] == "parallel"].iterrows():
            group_id = row["id"]

            # Skip if this group already has conditions set (to avoid overwriting)
            if pd.notna(row.get("parallel_condition_name")) and pd.notna(
                row.get("parallel_condition_expression")
            ):
                continue

            branches = branch_info[branch_info[activity_col] == group_id]
            if not branches.empty:
                condition_names = []
                condition_expressions = []
                for _, branch in branches.iterrows():
                    condition_id = branch.get(condition_col)
                    if (
                        pd.notna(condition_id)
                        and condition_id in branch_conditions.index
                    ):
                        condition_names.append(
                            branch_conditions.at[condition_id, bc_name_col]
                        )
                        condition_expressions.append(
                            branch_conditions.at[condition_id, bc_expr_col]
                        )
                    else:
                        condition_names.append("")
                        condition_expressions.append("")

                # Filter out empty condition names before joining with semicolons
                non_empty_names = [name for name in condition_names if name]
                if non_empty_names:
                    groups_df.at[idx, "parallel_condition_name"] = ";".join(
                        map(str, non_empty_names)
                    )
                else:
                    groups_df.at[idx, "parallel_condition_name"] = None

                # Create formatted string with name: expression pairs
                formatted_expressions = []
                for i in range(len(condition_names)):
                    if condition_names[i]:  # Only include non-empty names
                        formatted_expressions.append(
                            f"{condition_names[i]}: {condition_expressions[i]}"
                        )
                if formatted_expressions:
                    groups_df.at[idx, "parallel_condition_expression"] = "\n".join(
                        formatted_expressions
                    )
                else:
                    groups_df.at[idx, "parallel_condition_expression"] = None

    # Process regular parallel conditions from Zweiginformation
    process_branch_conditions("Zweiginformation", "ParallelActivity")

    # Process UserChoice conditions from Optionsinformation
    process_branch_conditions("Optionsinformation", "UserChoiceActivity")

    # Handle UserChoice specific processing
    if "Platzhalter für Aktivitäten nac" in xls.sheet_names:
        userchoice_df = pd.read_excel(xls, "Platzhalter für Aktivitäten nac")
        fragetext_col = get_column_name(userchoice_df.columns, "Fragetext")
        auswahltitel_col = get_column_name(userchoice_df.columns, "Auswahltitel")
        name_col = get_column_name(userchoice_df.columns, "Name:de")

        for idx, row in groups_df[groups_df["type"] == "parallel"].iterrows():
            # Check if this is a UserChoice case (has parallel_condition_name set and Erledigungsmodus is not standard)
            erledigungsmodus = str(row.get("Erledigungsmodus", ""))
            has_conditions = pd.notna(row.get("parallel_condition_name"))

            # Identify UserChoice cases: has conditions and erledigungsmodus is not a standard type
            is_userchoice = (
                has_conditions
                and erledigungsmodus
                not in ["AnyBranch", "OnlyOneBranch", "AllBranches", ""]
                and erledigungsmodus != "None"
            ) or (
                # Also check if the name exists in the UserChoice sheet
                name_col
                and name_col in userchoice_df.columns
                and row["name"] in userchoice_df[name_col].values
            )

            if is_userchoice:
                # Hard code Erledigungsmodus to "Benutzerentscheid" for UserChoice cases
                groups_df.at[idx, "Erledigungsmodus"] = "Benutzerentscheid"

                # Look up Fragetext/Auswahltitel if available
                if name_col and name_col in userchoice_df.columns:
                    matching_rows = userchoice_df[
                        userchoice_df[name_col] == row["name"]
                    ]
                    if not matching_rows.empty:
                        # Try Fragetext first, then Auswahltitel if Fragetext is empty
                        question_text = ""
                        if (
                            fragetext_col
                            and pd.notna(matching_rows.iloc[0].get(fragetext_col))
                            and str(matching_rows.iloc[0].get(fragetext_col)).strip()
                        ):
                            question_text = str(
                                matching_rows.iloc[0][fragetext_col]
                            ).strip()
                        elif (
                            auswahltitel_col
                            and pd.notna(matching_rows.iloc[0].get(auswahltitel_col))
                            and str(matching_rows.iloc[0].get(auswahltitel_col)).strip()
                        ):
                            question_text = str(
                                matching_rows.iloc[0][auswahltitel_col]
                            ).strip()

                        # Prepend question text to parallel_condition_expression if found
                        if question_text:
                            existing_expression = row.get(
                                "parallel_condition_expression", ""
                            )
                            if pd.notna(existing_expression) and existing_expression:
                                new_expression = (
                                    f"{question_text}\n{existing_expression}"
                                )
                            else:
                                new_expression = question_text
                            groups_df.at[idx, "parallel_condition_expression"] = (
                                new_expression
                            )

    # Handle options for UserChoice from Optionsinformation sheet (fallback for cases without Condition column)
    if "Optionsinformation" in xls.sheet_names:
        options_info = pd.read_excel(xls, "Optionsinformation")
        user_choice_col = get_column_name(options_info.columns, "UserChoiceActivity")
        option_name_col = get_column_name(options_info.columns, "Name")
        condition_col = get_column_name(options_info.columns, "Condition")

        # Only use this fallback if there's no Condition column (otherwise the unified handler above will take care of it)
        if all([user_choice_col, option_name_col]) and not condition_col:
            options_info[user_choice_col] = options_info[user_choice_col].apply(
                extract_id
            )
            for idx, row in groups_df[groups_df["type"] == "parallel"].iterrows():
                # Check if Erledigungsmodus has a value and it's not one of the standard types
                erledigungsmodus = str(row.get("Erledigungsmodus", ""))
                if (
                    erledigungsmodus
                    and erledigungsmodus
                    not in ["AnyBranch", "OnlyOneBranch", "AllBranches"]
                    and erledigungsmodus != "None"
                    and pd.isna(
                        row.get("parallel_condition_name")
                    )  # Only if not already set
                ):
                    group_id = row["id"]
                    matching_options = options_info[
                        options_info[user_choice_col] == group_id
                    ]
                    if not matching_options.empty:
                        option_names = (
                            matching_options[option_name_col].dropna().tolist()
                        )
                        if option_names:
                            groups_df.at[idx, "parallel_condition_name"] = ";".join(
                                map(str, option_names)
                            )

    # Clean up temporary columns
    groups_df.drop(
        columns=["Überspringen, falls", "Wiederholen, falls"],
        errors="ignore",
        inplace=True,
    )

    # Validate group IDs
    if groups_df["id"].duplicated().any():
        print("Warning: Duplicate group IDs detected.")

    # Sort for readability
    groups_df.sort_values(by=["parent", "SequenceNumber"], inplace=True)

    return groups_df


def check_for_unknown_groups(xls, groups_df, activities_df):
    """
    Checks for unknown group types in the Excel file by verifying if parent IDs from activities and groups
    exist in the groups_df['id']. If not, it searches for the parent ID in all sheets of the Excel file.

    Args:
        xls: The Excel file object to search through.
        groups_df (pd.DataFrame): DataFrame containing group information.
        activities_df (pd.DataFrame): DataFrame containing activity information.

    Returns:
        None
    """

    # Get all parent IDs from activities and groups
    activity_parents = set(activities_df["parent"].dropna())
    group_parents = set(groups_df["parent"].dropna())
    all_parents = activity_parents.union(group_parents)

    # Get known group IDs
    known_group_ids = set(groups_df["id"])

    # Find unknown parent IDs
    unknown_parents = all_parents - known_group_ids

    if unknown_parents:
        for parent_id in unknown_parents:
            found = False
            for sheet_name in xls.sheet_names:
                if sheet_name in [
                    "Prozess",
                    "Platzhalter für sequentielle Ak",
                    "Platzhalter für parallele Aktiv",
                ]:
                    continue  # Skip sheets we already process
                df = pd.read_excel(xls, sheet_name=sheet_name)
                transport_col = get_column_name(df.columns, "TransportID")
                if transport_col is not None and parent_id in df[transport_col].values:
                    st.warning(
                        f'Unbekannter Platzhalter in Sheet: **"{sheet_name}"**. Aktivitäten innerhalb dieses Platzhalters könnten fehlerhaft dargestellt werden.'
                    )
                    found = True
                    break
            if not found:
                st.warning(
                    f"Unbekannter Platzhalter mit ID **{parent_id}** nicht in den Sheets gefunden. Aktivitäten könnten fehlerhaft dargestellt werden."
                )


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
    updated_nodes["node_type"] = "activity"  # Mark original activities

    # Create a copy of groups_table (no sequence number changes needed)
    updated_groups = groups_table.copy()

    # Track special connections for repeat conditions
    if "repeat_connections" not in updated_groups.columns:
        updated_groups["repeat_connections"] = None

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
            if base + "_counter" not in st.session_state:
                st.session_state[base + "_counter"] = 0
            st.session_state[base + "_counter"] += 1
            return f"{base}_{st.session_state[base + '_counter']}"

    # Track substep nodes with a counter to ensure uniqueness
    substep_nodes_list = []

    for activity_id, activity in activities_table.iterrows():
        if pd.notna(activity.get("substeps")):
            # Use properties for unique IDs
            substep_node_id = generate_node_id("substeps", {"activity_id": activity_id})

            # Create a substep node
            substep_node = pd.Series(
                {
                    "node_type": "substeps",
                    "parent": activity_id,
                    "SequenceNumber": -1,  # Not in main sequence
                    "label": activity["substeps"],
                    # Copy other relevant columns with None values
                    "Empfänger": None,
                    "name": None,
                    "TransportID": None,
                    "type": None,
                },
                name=substep_node_id,
            )

            substep_nodes_list.append(substep_node)

    # Add all substep nodes to the updated_nodes table
    if substep_nodes_list:
        substep_nodes_df = pd.DataFrame(substep_nodes_list)
        updated_nodes = pd.concat([updated_nodes, substep_nodes_df])

    # Process groups with Erledigungsmodus
    eligible_groups = groups_table[
        (groups_table["Erledigungsmodus"] == "AnyBranch")  # Mind. 1 Zweig
        | (groups_table["Erledigungsmodus"] == "OnlyOneBranch")  # Genau 1 Zweig
        | (groups_table["Erledigungsmodus"] == "AllBranches")  # Alle Zweige
        | (
            groups_table["Erledigungsmodus"].notna()
            & (groups_table["Erledigungsmodus"] != "")
            & (
                ~groups_table["Erledigungsmodus"].isin(
                    ["AnyBranch", "OnlyOneBranch", "AllBranches"]
                )
            )
        )  # Any other UserChoice
    ]

    for group_id in eligible_groups.index:
        # Get the erledigungsmodus for this group
        erledigungsmodus = groups_table.loc[group_id, "Erledigungsmodus"]

        # Identify child activities and subgroups of this group
        child_activities = activities_table[activities_table["parent"] == group_id]
        child_subgroups = groups_table[groups_table["parent"] == group_id]

        # Get existing sequence numbers of children
        existing_seq = pd.concat(
            [child_activities["SequenceNumber"], child_subgroups["SequenceNumber"]]
        ).sort_values()

        # Determine sequence numbers for new nodes
        min_seq = existing_seq.min() if not existing_seq.empty else 0
        max_seq = existing_seq.max() if not existing_seq.empty else 0

        # Handle different Erledigungsmodus types
        if erledigungsmodus == "AllBranches":
            # For AllBranches, we only need gateway nodes with + symbol by default
            gateway_split_id = generate_node_id(
                "gateway_split", {"group_id": group_id, "type": "split"}
            )
            gateway_join_id = generate_node_id(
                "gateway_join", {"group_id": group_id, "type": "join"}
            )

            # Place gateways at the beginning and end
            gateway_split_seq = min_seq - 1  # Just before first child
            gateway_join_seq = max_seq + 1  # Just after last child

            # Check if there's a valid parallel_condition_expression
            has_condition_expr = pd.notna(
                groups_table.loc[group_id, "parallel_condition_expression"]
            )

            if has_condition_expr:
                # If condition exists, treat like AnyBranch/OnlyOneBranch with decision node
                decision_node_id = generate_node_id(
                    "decision", {"group_id": group_id, "type": erledigungsmodus}
                )
                decision_seq = min_seq - 2  # Decision comes before gateway

                # Get condition name for label
                parallel_condition = groups_table.loc[
                    group_id, "parallel_condition_name"
                ]
                if pd.isna(parallel_condition) or str(parallel_condition) == "None":
                    decision_label = "Entscheid"
                else:
                    decision_label = "Entscheid\n" + str(parallel_condition).replace(
                        ";", "\n"
                    )

                # Optionally add rule node if expression exists
                rule_node_id = generate_node_id(
                    "rule", {"group_id": group_id, "type": erledigungsmodus}
                )
                rule_seq = -1  # Rule not in main sequence

                # Create nodes dataframe for AllBranches with condition (gateways + decision + rule)
                new_nodes = pd.DataFrame(
                    {
                        "node_id": [
                            decision_node_id,
                            gateway_split_id,
                            gateway_join_id,
                            rule_node_id,
                        ],
                        "node_type": ["decision", "gateway", "gateway", "rule"],
                        "parent": [group_id, group_id, group_id, decision_node_id],
                        "SequenceNumber": [
                            decision_seq,
                            gateway_split_seq,
                            gateway_join_seq,
                            rule_seq,
                        ],
                        "label": [
                            decision_label,
                            "+",
                            "+",
                            groups_table.loc[group_id, "parallel_condition_expression"],
                        ],  # Plus symbol for AllBranches gateways
                        "type": [
                            None,
                            None,
                            None,
                            None,
                        ],  # Standard decision, not UserChoice
                    }
                ).set_index("node_id")
            else:
                # Create nodes dataframe for AllBranches without condition (only gateways)
                new_nodes = pd.DataFrame(
                    {
                        "node_id": [gateway_split_id, gateway_join_id],
                        "node_type": ["gateway", "gateway"],
                        "parent": [group_id, group_id],
                        "SequenceNumber": [gateway_split_seq, gateway_join_seq],
                        "label": ["+", "+"],  # Plus symbol for AllBranches
                        "type": [None, None],  # Standard gateways
                    }
                ).set_index("node_id")

        elif erledigungsmodus not in ["AnyBranch", "OnlyOneBranch", "AllBranches"]:
            # Treat UserChoice like OnlyOneBranch with specific decision label
            decision_node_id = generate_node_id(
                "decision", {"group_id": group_id, "type": erledigungsmodus}
            )
            gateway_split_id = generate_node_id(
                "gateway_split", {"group_id": group_id, "type": erledigungsmodus}
            )
            gateway_join_id = generate_node_id(
                "gateway_join", {"group_id": group_id, "type": erledigungsmodus}
            )

            # Check if there's a valid parallel_condition_expression
            has_condition_expr = pd.notna(
                groups_table.loc[group_id, "parallel_condition_expression"]
            )

            # Only create rule node if there's a condition expression
            if has_condition_expr:
                rule_node_id = generate_node_id(
                    "rule", {"group_id": group_id, "type": erledigungsmodus}
                )
                rule_seq = -1  # Rule not in main sequence

            # Place nodes in sequence
            decision_seq = min_seq - 2  # Decision comes before gateway
            gateway_split_seq = (
                min_seq - 1
            )  # Gateway split comes just before the first child
            gateway_join_seq = (
                max_seq + 1
            )  # Gateway join comes just after the last child

            # Set gateway labels for UserChoice (like OnlyOneBranch)
            gateway_split_label = "X"  # Empty diamond for UserChoice
            gateway_join_label = "X"  # Empty diamond for UserChoice

            # Prepare node data for DataFrame
            node_ids = []
            node_types = []
            parent_activities = []
            sequence_numbers = []
            labels = []

            # Always add decision and gateway nodes
            node_ids.extend([decision_node_id, gateway_split_id, gateway_join_id])
            node_types.extend(["decision", "gateway", "gateway"])
            parent_activities.extend([group_id, group_id, group_id])
            sequence_numbers.extend([decision_seq, gateway_split_seq, gateway_join_seq])
            # Set decision label directly from Erledigungsmodus
            decision_label = groups_table.loc[group_id, "Erledigungsmodus"]
            labels.extend([decision_label, gateway_split_label, gateway_join_label])

            # Add rule node only if there's a condition expression
            if has_condition_expr:
                node_ids.append(rule_node_id)
                node_types.append("rule")
                parent_activities.append(decision_node_id)
                sequence_numbers.append(rule_seq)
                labels.append(
                    groups_table.loc[group_id, "parallel_condition_expression"]
                )

            # Create types list - mark decision as UserChoice
            types = []
            for i, node_type in enumerate(node_types):
                if node_type == "decision":
                    types.append("UserChoice")
                else:
                    types.append(None)

            # Create nodes dataframe for UserChoice
            new_nodes = pd.DataFrame(
                {
                    "node_id": node_ids,
                    "node_type": node_types,
                    "parent": parent_activities,
                    "SequenceNumber": sequence_numbers,
                    "label": labels,
                    "type": types,
                }
            ).set_index("node_id")
        else:
            # For AnyBranch and OnlyOneBranch, include decision and rule nodes
            # Check if there's a valid parallel_condition_expression
            has_condition_expr = pd.notna(
                groups_table.loc[group_id, "parallel_condition_expression"]
            )

            # For AnyBranch and OnlyOneBranch, always create decision and gateway nodes
            decision_node_id = generate_node_id(
                "decision", {"group_id": group_id, "type": erledigungsmodus}
            )
            gateway_split_id = generate_node_id(
                "gateway_split", {"group_id": group_id, "type": erledigungsmodus}
            )
            gateway_join_id = generate_node_id(
                "gateway_join", {"group_id": group_id, "type": erledigungsmodus}
            )

            # Only create rule node if there's a condition expression
            if has_condition_expr:
                rule_node_id = generate_node_id(
                    "rule", {"group_id": group_id, "type": erledigungsmodus}
                )
                rule_seq = -1  # Rule not in main sequence

            # Place nodes in sequence
            decision_seq = min_seq - 2  # Decision comes before gateway
            gateway_split_seq = (
                min_seq - 1
            )  # Gateway split comes just before the first child
            gateway_join_seq = (
                max_seq + 1
            )  # Gateway join comes just after the last child

            # Set gateway labels based on the erledigungsmodus
            if erledigungsmodus == "AnyBranch":
                gateway_split_label = "+"  # Gateway split symbol for AnyBranch
                gateway_join_label = "X"  # Gateway join symbol for AnyBranch
            else:  # OnlyOneBranch
                gateway_split_label = "X"  # Empty diamond for OnlyOneBranch
                gateway_join_label = "X"  # Empty diamond for OnlyOneBranch

            # Prepare node data for DataFrame
            node_ids = []
            node_types = []
            parent_activities = []
            sequence_numbers = []
            labels = []

            # Always add decision and gateway nodes
            node_ids.extend([decision_node_id, gateway_split_id, gateway_join_id])
            node_types.extend(["decision", "gateway", "gateway"])
            parent_activities.extend([group_id, group_id, group_id])
            sequence_numbers.extend([decision_seq, gateway_split_seq, gateway_join_seq])
            parallel_condition = groups_table.loc[group_id, "parallel_condition_name"]
            if pd.isna(parallel_condition) or str(parallel_condition) == "None":
                decision_label = "Entscheid"
            else:
                decision_label = "Entscheid\n" + str(parallel_condition).replace(
                    ";", "\n"
                )
            labels.extend([decision_label, gateway_split_label, gateway_join_label])

            # Add rule node only if there's a condition expression
            if has_condition_expr:
                node_ids.append(rule_node_id)
                node_types.append("rule")
                parent_activities.append(decision_node_id)
                sequence_numbers.append(rule_seq)
                labels.append(
                    groups_table.loc[group_id, "parallel_condition_expression"]
                )

            # Create types list - standard decisions for AnyBranch/OnlyOneBranch
            types = [None] * len(node_ids)  # All are standard, not UserChoice

            # Create nodes dataframe for AnyBranch or OnlyOneBranch
            new_nodes = pd.DataFrame(
                {
                    "node_id": node_ids,
                    "node_type": node_types,
                    "parent": parent_activities,
                    "SequenceNumber": sequence_numbers,
                    "label": labels,
                    "type": types,
                }
            ).set_index("node_id")

        # Append new nodes to the updated table
        updated_nodes = pd.concat([updated_nodes, new_nodes])

    # Next, process groups with skip conditions
    skip_condition_groups = groups_table[
        groups_table["skip_name"].notna() | groups_table["skip_condition"].notna()
    ]

    for group_id in skip_condition_groups.index:
        # Skip if this group was already processed for Erledigungsmodus
        if group_id in eligible_groups.index:
            continue

        # Identify child activities and subgroups of this group
        child_activities = activities_table[activities_table["parent"] == group_id]
        child_subgroups = groups_table[groups_table["parent"] == group_id]

        # Get existing sequence numbers of children
        existing_seq = pd.concat(
            [child_activities["SequenceNumber"], child_subgroups["SequenceNumber"]]
        ).sort_values()

        # Determine sequence numbers for new nodes
        min_seq = existing_seq.min() if not existing_seq.empty else 0
        max_seq = existing_seq.max() if not existing_seq.empty else 0

        # Generate node IDs
        rule_node_id = generate_node_id("skip_rule", {"group_id": group_id})
        decision_node_id = generate_node_id("skip_decision", {"group_id": group_id})
        gateway_split_id = generate_node_id(
            "skip_gateway_split", {"group_id": group_id}
        )
        gateway_join_id = generate_node_id("skip_gateway_join", {"group_id": group_id})

        # Place nodes in sequence
        decision_seq = min_seq - 2  # Decision comes before gateway
        gateway_split_seq = (
            min_seq - 1
        )  # Gateway split comes just before the first child
        gateway_join_seq = max_seq + 1  # Gateway join comes just after the last child
        rule_seq = -1  # Rule not in main sequence

        # Get skip condition labels
        skip_name = groups_table.loc[group_id, "skip_name"]
        skip_condition = groups_table.loc[group_id, "skip_condition"]

        # Create nodes dataframe for skip condition
        new_nodes = pd.DataFrame(
            {
                "node_id": [
                    rule_node_id,
                    decision_node_id,
                    gateway_split_id,
                    gateway_join_id,
                ],
                "node_type": ["rule", "decision", "gateway", "gateway"],
                "parent": [decision_node_id, group_id, group_id, group_id],
                "SequenceNumber": [
                    rule_seq,
                    decision_seq,
                    gateway_split_seq,
                    gateway_join_seq,
                ],
                "label": [
                    skip_condition if pd.notna(skip_condition) else "",
                    "Überspringen, falls\n"
                    + (skip_name if pd.notna(skip_name) else ""),
                    "X",  # X symbol for skip gateway split
                    "X",  # X symbol for skip gateway join
                ],
                "type": [None, None, None, None],  # Standard skip decision
            }
        ).set_index("node_id")

        # Append new nodes to the updated table
        updated_nodes = pd.concat([updated_nodes, new_nodes])

    # Finally, process groups with repeat conditions
    repeat_condition_groups = groups_table[
        groups_table["repeat_name"].notna() | groups_table["repeat_condition"].notna()
    ]

    for group_id in repeat_condition_groups.index:
        # Skip if this group was already processed for Erledigungsmodus
        if group_id in eligible_groups.index:
            continue

        # Identify child activities and subgroups of this group
        child_activities = activities_table[activities_table["parent"] == group_id]
        child_subgroups = groups_table[groups_table["parent"] == group_id]

        # Get existing sequence numbers of children
        existing_seq = pd.concat(
            [child_activities["SequenceNumber"], child_subgroups["SequenceNumber"]]
        ).sort_values()

        # Determine sequence numbers for new nodes
        min_seq = existing_seq.min() if not existing_seq.empty else 0
        max_seq = existing_seq.max() if not existing_seq.empty else 0

        # Generate node IDs
        rule_node_id = generate_node_id("repeat_rule", {"group_id": group_id})
        decision_node_id = generate_node_id("repeat_decision", {"group_id": group_id})
        gateway_split_node_id = generate_node_id(
            "repeat_gateway_split", {"group_id": group_id}
        )
        gateway_join_node_id = generate_node_id(
            "repeat_gateway_join", {"group_id": group_id}
        )

        # As a target for the repeat, we'll use a gateway node at the beginning
        # This will allow us to connect back to the start of the group
        gateway_join_seq = min_seq - 1
        # Decision and gateway split come at the end
        decision_seq = max_seq + 1  # Decision comes second-to-last
        gateway_split_seq = max_seq + 2  # Gateway split comes last
        rule_seq = -1  # Rule not in main sequence (it's connected to the decision)

        # Get repeat condition labels
        repeat_name = groups_table.loc[group_id, "repeat_name"]
        repeat_condition = groups_table.loc[group_id, "repeat_condition"]

        # Create nodes dataframe for repeat condition
        new_nodes = pd.DataFrame(
            {
                "node_id": [
                    rule_node_id,
                    decision_node_id,
                    gateway_split_node_id,
                    gateway_join_node_id,
                ],
                "node_type": ["rule", "decision", "gateway", "gateway"],
                "parent": [decision_node_id, group_id, group_id, group_id],
                "SequenceNumber": [
                    rule_seq,
                    decision_seq,
                    gateway_split_seq,
                    gateway_join_seq,
                ],
                "label": [
                    repeat_condition if pd.notna(repeat_condition) else "",
                    "Wiederholen, falls\n"
                    + (repeat_name if pd.notna(repeat_name) else ""),
                    "X",  # X symbol for gateway split
                    "X",  # X symbol for gateway join
                ],
                "type": [None, None, None, None],  # Standard repeat decision
            }
        ).set_index("node_id")

        # Store the gateway node IDs to refer back to in add_group function
        updated_groups.at[group_id, "repeat_connections"] = {
            "gateway_split": gateway_split_node_id,
            "gateway_join": gateway_join_node_id,
        }

        # Append new nodes to the updated table
        updated_nodes = pd.concat([updated_nodes, new_nodes])

    # Sort by parent and SequenceNumber for correct flow
    updated_nodes.sort_values(by=["parent", "SequenceNumber"], inplace=True)

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
    edge_labels = {}  # Store edge labels

    def process_group(group_id, prev_node=None):
        """
        Process a group based on its type, returning first and last nodes for connection.
        """
        group = updated_groups.loc[group_id]
        children = []

        # Collect nodes and subgroups
        nodes = updated_nodes[updated_nodes["parent"] == group_id]
        for node_id in nodes.index:
            children.append(("node", node_id, nodes.at[node_id, "SequenceNumber"]))

        subgroups = updated_groups[updated_groups["parent"] == group_id]
        for subgroup_id in subgroups.index:
            children.append(
                ("group", subgroup_id, subgroups.at[subgroup_id, "SequenceNumber"])
            )

        # Sort by SequenceNumber
        children.sort(key=lambda x: x[2])

        # Determine if there are subgroups with higher sequence numbers than activities for skip handling
        activity_seqs = [
            seq
            for c_type, child_id, seq in children
            if c_type == "node"
            and child_id in updated_nodes.index
            and get_safe_value_bpmn(updated_nodes.loc[child_id], "node_type")
            == "activity"
        ]
        subgroup_seqs = [seq for c_type, _, seq in children if c_type == "group"]
        has_subgroup_with_higher_seq = (
            any(
                sub_seq > act_seq
                for sub_seq in subgroup_seqs
                for act_seq in activity_seqs
            )
            if activity_seqs and subgroup_seqs
            else False
        )

        # Handle both 'sequential' and 'process' types similarly
        if get_safe_value_bpmn(group, "type") in ["sequential", "process"]:
            first_node = None
            last_node = None
            local_prev = prev_node

            for child_type, child_id, _ in children:
                if child_type == "node":
                    node_type = get_safe_value_bpmn(
                        updated_nodes.loc[child_id], "node_type"
                    )
                    # Skip special nodes in main flow
                    if node_type in ["substeps", "rule"]:
                        continue
                    if local_prev and (local_prev, child_id) not in edge_set:
                        edges.append((local_prev, child_id))
                        edge_set.add((local_prev, child_id))
                    local_prev = child_id
                    if first_node is None:
                        first_node = child_id
                    last_node = child_id
                elif child_type == "group":
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
            handle_skip(group, children, has_subgroup_with_higher_seq)
            handle_repeat(group, children)
            return first_node, last_node

        elif get_safe_value_bpmn(group, "type") == "parallel":
            erledigungsmodus = get_safe_value_bpmn(group, "Erledigungsmodus")
            decision = split = join = None
            for c_type, c_id, seq in children:
                if c_type == "node":
                    if "decision" in c_id:
                        decision = c_id
                    elif "gateway_split" in c_id and "skip" not in c_id:
                        split = c_id
                    elif "gateway_join" in c_id and "skip" not in c_id:
                        join = c_id

            # Check required nodes based on Erledigungsmodus
            if erledigungsmodus == "AllBranches":
                if not (split and join):
                    print(
                        f"Warning: Parallel group {group_id} missing split/join for AllBranches."
                    )
                    return None, None
            else:
                if not (decision and split and join):
                    print(
                        f"Warning: Parallel group {group_id} missing decision/split/join."
                    )
                    return None, None

            # Set the first node for connection
            first_node = decision if decision else split

            # Connect decision to split if decision exists
            if decision and (decision, split) not in edge_set:
                edges.append((decision, split))
                edge_set.add((decision, split))

            # Extract labels from decision node if present (for AnyBranch/OnlyOneBranch)
            decision_labels = []
            if decision and decision in updated_nodes.index:
                decision_label = get_safe_value_bpmn(
                    updated_nodes.loc[decision], "label", ""
                )
                if decision_label and "\n" in decision_label:
                    decision_labels = decision_label.split("\n")[1:]

            # Also extract labels from parallel_condition_name column if available
            parallel_labels = []
            if "parallel_condition_name" in group and pd.notna(
                group["parallel_condition_name"]
            ):
                parallel_labels = group["parallel_condition_name"].split(";")
                parallel_labels = [
                    label.strip() for label in parallel_labels if label.strip()
                ]

            # Identify branches between split and join
            split_seq = next(seq for _, c_id, seq in children if c_id == split)
            join_seq = next(seq for _, c_id, seq in children if c_id == join)
            branches = [c for c in children if split_seq < c[2] < join_seq]

            # Connect branches
            used_labels = set()  # Track used labels to avoid duplicates
            branch_index = 0
            for b_type, b_id, _ in branches:
                if b_type == "node":
                    node_type = get_safe_value_bpmn(
                        updated_nodes.loc[b_id], "node_type"
                    )
                    if node_type in ["substeps", "rule"]:
                        continue
                    if (split, b_id) not in edge_set:
                        edges.append((split, b_id))
                        edge_set.add((split, b_id))
                        if (
                            branch_index < len(parallel_labels)
                            and parallel_labels[branch_index] not in used_labels
                        ):
                            edge_labels[(split, b_id)] = parallel_labels[branch_index]
                            used_labels.add(parallel_labels[branch_index])
                            branch_index += 1
                        elif (
                            branch_index < len(decision_labels)
                            and decision_labels[branch_index] not in used_labels
                        ):
                            edge_labels[(split, b_id)] = decision_labels[branch_index]
                            used_labels.add(decision_labels[branch_index])
                            branch_index += 1
                    if (b_id, join) not in edge_set:
                        edges.append((b_id, join))
                        edge_set.add((b_id, join))
                elif b_type == "group":
                    # Check if the subgroup or any nested group contains activity nodes
                    def has_activity_in_group(group_id):
                        subgroup_nodes = updated_nodes[
                            updated_nodes["parent"] == group_id
                        ]
                        for node_id in subgroup_nodes.index:
                            if (
                                get_safe_value_bpmn(
                                    subgroup_nodes.loc[node_id], "node_type"
                                )
                                == "activity"
                            ):
                                return True
                        # Check nested groups
                        nested_groups = updated_groups[
                            updated_groups["parent"] == group_id
                        ]
                        for nested_group_id in nested_groups.index:
                            if has_activity_in_group(nested_group_id):
                                return True
                        return False

                    has_activity = has_activity_in_group(b_id)
                    if not has_activity:
                        # Empty subgroup, connect split directly to join
                        if (split, join) not in edge_set:
                            edges.append((split, join))
                            edge_set.add((split, join))
                            if (
                                branch_index < len(parallel_labels)
                                and parallel_labels[branch_index] not in used_labels
                            ):
                                edge_labels[(split, join)] = parallel_labels[
                                    branch_index
                                ]
                                used_labels.add(parallel_labels[branch_index])
                                branch_index += 1
                            elif (
                                branch_index < len(decision_labels)
                                and decision_labels[branch_index] not in used_labels
                            ):
                                edge_labels[(split, join)] = decision_labels[
                                    branch_index
                                ]
                                used_labels.add(decision_labels[branch_index])
                                branch_index += 1
                    else:
                        b_first, b_last = process_group(b_id)
                        if b_first and (split, b_first) not in edge_set:
                            edges.append((split, b_first))
                            edge_set.add((split, b_first))
                            if (
                                branch_index < len(parallel_labels)
                                and parallel_labels[branch_index] not in used_labels
                            ):
                                edge_labels[(split, b_first)] = parallel_labels[
                                    branch_index
                                ]
                                used_labels.add(parallel_labels[branch_index])
                                branch_index += 1
                            elif (
                                branch_index < len(decision_labels)
                                and decision_labels[branch_index] not in used_labels
                            ):
                                edge_labels[(split, b_first)] = decision_labels[
                                    branch_index
                                ]
                                used_labels.add(decision_labels[branch_index])
                                branch_index += 1
                        if b_last and (b_last, join) not in edge_set:
                            edges.append((b_last, join))
                            edge_set.add((b_last, join))

            return first_node, join

        else:
            print(f"Unknown group type: {get_safe_value_bpmn(group, 'type')}")
            return None, None

    def handle_skip(group, children, has_subgroup_with_higher_seq=False):
        """Handle skip constructs within a group.

        Args:
            group: The group being processed.
            children: List of child nodes and groups within the group.
            has_subgroup_with_higher_seq: Boolean indicating if a subgroup with a higher sequence number than the last activity exists.
        """
        decision = split = join = activity = None
        activities = []
        for c_type, c_id, seq in children:
            if c_type == "node":
                if "skip_decision" in c_id:
                    decision = c_id
                elif "skip_gateway_split" in c_id:
                    split = c_id
                elif "skip_gateway_join" in c_id:
                    join = c_id
                elif (
                    get_safe_value_bpmn(updated_nodes.loc[c_id], "node_type")
                    == "activity"
                ):
                    activity = c_id
                    activities.append((c_id, seq))

        if split and join:
            if (split, join) not in edge_set:
                edges.append((split, join))
                edge_set.add((split, join))

                # Extract skip condition label from decision node if available
                if decision in updated_nodes.index:
                    decision_label = get_safe_value_bpmn(
                        updated_nodes.loc[decision], "label", ""
                    )
                    if decision_label and "\n" in decision_label:
                        # Second line is the edge label for the skip path
                        skip_label = decision_label.split("\n")[1]
                        edge_labels[(split, join)] = skip_label

        if decision and split and join and activity:
            if (decision, split) not in edge_set:
                edges.append((decision, split))
                edge_set.add((decision, split))
            if (split, activity) not in edge_set:
                edges.append((split, activity))
                edge_set.add((split, activity))
            # Only connect the last activity to join if there is no subgroup with higher sequence number
            if not has_subgroup_with_higher_seq and activities:
                last_activity = activities[-1][0]
                if (last_activity, join) not in edge_set:
                    edges.append((last_activity, join))
                    edge_set.add((last_activity, join))

    def handle_repeat(group, children):
        """Handle repeat constructs within a group."""
        decision = gateway_split = gateway_join = activity = None
        for c_type, c_id, _ in children:
            if c_type == "node":
                if "repeat_decision" in c_id:
                    decision = c_id
                elif "repeat_gateway_split" in c_id:
                    gateway_split = c_id
                elif "repeat_gateway_join" in c_id:
                    gateway_join = c_id
                elif (
                    get_safe_value_bpmn(updated_nodes.loc[c_id], "node_type")
                    == "activity"
                ):
                    activity = c_id

        if gateway_split and gateway_join:
            if (gateway_split, gateway_join) not in edge_set:
                edges.append((gateway_split, gateway_join))
                edge_set.add((gateway_split, gateway_join))

        if decision and gateway_split and gateway_join and activity:
            if (gateway_join, activity) not in edge_set:
                edges.append((gateway_join, activity))
                edge_set.add((gateway_join, activity))
            if (activity, decision) not in edge_set:
                edges.append((activity, decision))
            if (decision, gateway_split) not in edge_set:
                edges.append((decision, gateway_split))

            # Extract repeat condition label from decision node
            if decision in updated_nodes.index:
                decision_label = get_safe_value_bpmn(
                    updated_nodes.loc[decision], "label", ""
                )
                if decision_label and "\n" in decision_label:
                    # Second line is the edge label for the repeat path
                    repeat_label = decision_label.split("\n")[1]
                    edge_labels[(gateway_split, gateway_join)] = repeat_label

    # Process top-level group
    top_group_id = updated_groups[updated_groups["parent"].isna()].index[0]
    first_node, last_node = process_group(top_group_id)

    # Add start and end connections
    if first_node and ("start", first_node) not in edge_set:
        edges.append(("start", first_node))
        edge_set.add(("start", first_node))
    if last_node and (last_node, "end") not in edge_set:
        edges.append((last_node, "end"))
        edge_set.add((last_node, "end"))

    # Add special node connections
    for node_id in updated_nodes.index:
        node_type = get_safe_value_bpmn(updated_nodes.loc[node_id], "node_type")
        parent_id = get_safe_value_bpmn(updated_nodes.loc[node_id], "parent")
        if (
            node_type == "substeps"
            and pd.notna(parent_id)
            and (parent_id, node_id) not in edge_set
        ):
            edges.append((parent_id, node_id))
            edge_set.add((parent_id, node_id))
        elif (
            node_type == "rule"
            and pd.notna(parent_id)
            and (node_id, parent_id) not in edge_set
        ):
            edges.append((node_id, parent_id))
            edge_set.add((node_id, parent_id))

    # Create edges DataFrame
    edges_df = pd.DataFrame(edges, columns=["source", "target"])

    # Assign labels to edges
    edges_df["label"] = None
    # Create a map from (source, target) to all matching edge tuples in edge_set
    edge_tuples_map = defaultdict(list)
    for edge_tuple in edge_set:
        if len(edge_tuple) == 3:  # It's a special edge with branch ID
            source, target, branch_id = edge_tuple
            edge_tuples_map[(source, target)].append(edge_tuple)

    # Apply labels to edges
    for i, (source, target) in enumerate(zip(edges_df["source"], edges_df["target"])):
        # Check if there are any special edges with this source-target pair
        if (source, target) in edge_tuples_map and edge_tuples_map[(source, target)]:
            # Get the label from the first matching edge tuple
            edge_tuple = edge_tuples_map[(source, target)][0]
            if edge_tuple in edge_labels:
                edges_df.loc[i, "label"] = edge_labels[edge_tuple]
                # Remove this tuple to prevent reuse for other edges with same source-target
                edge_tuples_map[(source, target)].remove(edge_tuple)
        # Fallback to standard (source, target) key if no special edge or no label found
        elif pd.isna(edges_df.loc[i, "label"]) and (source, target) in edge_labels:
            edges_df.loc[i, "label"] = edge_labels[(source, target)]

    edges_df["style"] = "solid_arrow"
    return edges_df


## -- Generate BPMN Diagram --

# Constants
ACTIVITY_TABLE_WIDTH = "180"
ACTIVITY_MAX_CHARS_PER_LINE = 20
ACTIVITY_FONT_SIZE = "14"
ACTIVITY_SMALL_FONT_SIZE = "12"
ACTIVITY_SMALL_MAX_CHARS_PER_LINE = 24
EDGE_MIN_LENGTH = "1.0"  # Define if not already present
EDGE_LABEL_DISTANCE = "2.0"  # Define if not already present
GRAPH_NODE_SEPARATION = "0.5"  # Define if not already present
GRAPH_RANK_SEPARATION = "0.5"  # Define if not already present


def wrap_text(text, max_chars_per_line):
    """Wrap text into lines not exceeding max_chars_per_line."""
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    for word in words:
        if current_length + len(word) + len(current_line) > max_chars_per_line:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = []
                current_length = 0
            else:
                lines.append(word)
                continue
        current_line.append(word)
        current_length += len(word)
    if current_line:
        lines.append(" ".join(current_line))
    return lines


def get_port(node_id, updated_nodes, direction):
    """Return the port for edge connections based on node type and direction."""
    if node_id in updated_nodes.index:
        try:
            # Handle Series objects safely
            node_type = updated_nodes.loc[node_id, "node_type"]
            if hasattr(node_type, "iloc"):
                node_type = node_type.iloc[0]

            if isinstance(node_type, str) and node_type == "activity":
                return ":w" if direction == "in" else ":e"
        except (IndexError, KeyError, AttributeError):
            # If any error occurs, return default empty string
            pass
    return ""


def add_node(dot, node_id, node, edge_set, updated_nodes):
    """Add a node to the Graphviz diagram based on its type."""
    # Get node_type and handle if it's a Series
    node_type = node["node_type"]
    if hasattr(node_type, "iloc"):
        node_type = node_type.iloc[0]

    label_value = get_safe_value_bpmn(node, "label", "")
    label = str(label_value)

    if is_node_type(node_type, "rule"):
        if node_id.startswith("repeat_rule") or node_id.startswith("skip_rule"):
            label = f"📄\n{label}"
        dot.node(node_id, label=label, shape="none")
        parent_activity = get_safe_value_bpmn(node, "parent", "")
        if parent_activity and (node_id, parent_activity) not in edge_set:
            dot.edge(node_id, parent_activity, style="dotted")
            edge_set.add((node_id, parent_activity))
        return False

    elif is_node_type(node_type, "substeps"):
        dot.node(
            node_id,
            label=label,
            shape="none",
            style="",
            fontsize="14",
            align="left",
            group=get_safe_value_bpmn(node, "parent", ""),
        )
        parent_activity = get_safe_value_bpmn(node, "parent", "")
        if parent_activity and (parent_activity, node_id) not in edge_set:
            dot.edge(
                parent_activity,
                node_id,
                style="dotted",
                dir="none",
                color="black",
                weight="3.0",
                len="0.8",
            )
            edge_set.add((parent_activity, node_id))
        return False
    else:
        if is_node_type(node_type, "activity"):
            empfanger = get_safe_value_bpmn(node, "Empfänger", "")
            name_de = get_safe_value_bpmn(node, "name", "")
            activity_type = get_safe_value_bpmn(node, "type", "")

            emoji = ""
            if activity_type == "manual":
                emoji = "👤 "
            elif activity_type == "system":
                emoji = "⚙️ "
            elif activity_type == "script":
                emoji = "📜 "

            formatted_empfanger = f"{emoji}{empfanger}" if empfanger else emoji

            wrapped_lines = wrap_text(name_de, ACTIVITY_MAX_CHARS_PER_LINE)
            if len(wrapped_lines) > 2:
                font_size = ACTIVITY_SMALL_FONT_SIZE
                wrapped_lines_small = wrap_text(
                    name_de, ACTIVITY_SMALL_MAX_CHARS_PER_LINE
                )
                if len(wrapped_lines_small) > 2:
                    wrapped_lines = wrapped_lines_small[:2]
                    wrapped_lines[-1] += " ..."
                else:
                    wrapped_lines = wrapped_lines_small
            else:
                font_size = ACTIVITY_FONT_SIZE

            formatted_name = "<BR/>".join(wrapped_lines)

            html_label = f"""<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="6" WIDTH="{ACTIVITY_TABLE_WIDTH}">
<TR><TD ALIGN="left" VALIGN="top"><FONT POINT-SIZE="{ACTIVITY_FONT_SIZE}">{formatted_empfanger}</FONT></TD></TR>
<TR><TD ALIGN="center"><FONT POINT-SIZE="{font_size}">{formatted_name}</FONT></TD></TR>
</TABLE>>"""
            label = html_label
        elif is_node_type(node_type, "helper"):
            label = ""
        attrs = {}
        if is_node_type(node_type, "gateway"):
            attrs["fontsize"] = "16"
            attrs["shape"] = "diamond"
        elif is_node_type(node_type, "activity"):
            attrs["shape"] = "box"
            attrs["style"] = "rounded"
            attrs["margin"] = "0"
            attrs["group"] = node_id
        else:
            attrs["shape"] = "box"
        dot.node(node_id, label=label, **attrs)
        return True


def is_node_type(value, type_to_check):
    """Safely check if a node type equals a specific value, handling Series."""
    if pd.isna(value):
        return False

    # If it's a Series, extract the first value
    if hasattr(value, "iloc"):
        try:
            value = value.iloc[0]
        except (IndexError, AttributeError):
            return False

    return value == type_to_check


def add_group(
    group_id, dot, updated_nodes, updated_groups, edge_set, processed_substeps=None
):
    """Build a group in the BPMN diagram recursively."""
    if processed_substeps is None:
        processed_substeps = set()

    group = updated_groups.loc[group_id]
    children = []
    group_name = get_safe_value_bpmn(group, "name")

    nodes = updated_nodes[updated_nodes["parent"] == group_id]
    for node_id in nodes.index:
        seq_num = get_safe_value_bpmn(nodes.loc[node_id], "SequenceNumber", 0)
        children.append(("node", node_id, seq_num))

    # Find decision node IDs safely
    decision_ids = []
    for node_id in nodes.index:
        node_type = get_safe_value_bpmn(nodes.loc[node_id], "node_type")
        if is_node_type(node_type, "decision"):
            decision_ids.append(node_id)

    for decision_id in decision_ids:
        # Find rule nodes connected to this decision
        rule_ids = []
        for node_id in updated_nodes[updated_nodes["parent"] == decision_id].index:
            node_type = get_safe_value_bpmn(updated_nodes.loc[node_id], "node_type")
            if is_node_type(node_type, "rule"):
                rule_ids.append(node_id)
        for rule_id in rule_ids:
            seq_num = get_safe_value_bpmn(
                updated_nodes.loc[rule_id], "SequenceNumber", 0
            )
            children.append(("node", rule_id, seq_num))

    # Find activity node IDs safely
    activity_ids = []
    for node_id in nodes.index:
        node_type = get_safe_value_bpmn(nodes.loc[node_id], "node_type")
        if is_node_type(node_type, "activity"):
            activity_ids.append(node_id)

    for activity_id in activity_ids:
        # Find substep nodes connected to this activity
        substep_ids = []
        for node_id in updated_nodes[updated_nodes["parent"] == activity_id].index:
            node_type = get_safe_value_bpmn(updated_nodes.loc[node_id], "node_type")
            if is_node_type(node_type, "substeps"):
                substep_ids.append(node_id)
        for substep_id in substep_ids:
            if substep_id not in processed_substeps:
                processed_substeps.add(substep_id)
                seq_num = get_safe_value_bpmn(
                    updated_nodes.loc[substep_id], "SequenceNumber", 0
                )
                children.append(("node", substep_id, seq_num))

    subgroups = updated_groups[updated_groups["parent"] == group_id]
    for subgroup_id in subgroups.index:
        seq_num = get_safe_value_bpmn(subgroups.loc[subgroup_id], "SequenceNumber", 0)
        children.append(("group", subgroup_id, seq_num))

    children.sort(key=lambda x: x[2])

    gateway_split = gateway_join = skip_gateway_split = skip_gateway_join = (
        repeat_gateway
    ) = repeat_helper = None
    parallel_branches = []
    gateway_connected_nodes = set()

    # Safely get group type
    group_type = get_safe_value_bpmn(group, "type")

    # Safely get parallel condition names and compute labels
    parallel_condition_name = get_safe_value_bpmn(group, "parallel_condition_name")
    labels = (
        parallel_condition_name.split(";")
        if group_type == "parallel" and parallel_condition_name
        else []
    )

    # Safely get repeat connections
    repeat_connections = get_safe_value_bpmn(group, "repeat_connections")
    if repeat_connections:
        if isinstance(repeat_connections, dict):
            repeat_gateway = repeat_connections.get("gateway")
            repeat_helper = repeat_connections.get("helper")
        elif isinstance(repeat_connections, str) and "gateway" in repeat_connections:
            import ast

            try:
                repeat_dict = ast.literal_eval(repeat_connections)
                repeat_gateway = repeat_dict.get("gateway")
                repeat_helper = repeat_dict.get("helper")
            except:
                repeat_gateway = repeat_helper = None

    for child_type, child_id, _ in children:
        if child_type == "node":
            # Safely get node_type for further checks
            node_type = get_safe_value_bpmn(updated_nodes.loc[child_id], "node_type")
            if is_node_type(node_type, "gateway"):
                if "gateway_split" in child_id and "skip" not in child_id:
                    gateway_split = child_id
                elif "gateway_join" in child_id and "skip" not in child_id:
                    gateway_join = child_id
                elif "skip_gateway_split" in child_id:
                    skip_gateway_split = child_id
                elif "skip_gateway_join" in child_id:
                    skip_gateway_join = child_id

    if group_type == "parallel" and gateway_split and gateway_join:
        split_seq = get_safe_value_bpmn(
            updated_nodes.loc[gateway_split], "SequenceNumber", 0
        )
        join_seq = get_safe_value_bpmn(
            updated_nodes.loc[gateway_join], "SequenceNumber", float("inf")
        )
        parallel_branches = [
            child for child in children if split_seq < child[2] < join_seq
        ]

    prev_node = first_node = last_node = first_real_node = None
    for child in children:
        child_type, child_id, _ = child
        if child_type == "node":
            node = updated_nodes.loc[child_id]
            in_flow = add_node(dot, child_id, node, edge_set, updated_nodes)
            if in_flow:
                if first_node is None:
                    first_node = child_id
                node_type = get_safe_value_bpmn(node, "node_type")
                if first_real_node is None and not is_node_type(node_type, "helper"):
                    first_real_node = child_id
                last_node = child_id
                if prev_node and (prev_node, child_id) not in edge_set:
                    if group_type != "parallel" or (
                        prev_node not in gateway_connected_nodes
                        and child_id not in gateway_connected_nodes
                    ):
                        from_port = get_port(prev_node, updated_nodes, "out")
                        to_port = get_port(child_id, updated_nodes, "in")
                        dot.edge(
                            prev_node + from_port,
                            child_id + to_port,
                            minlen=EDGE_MIN_LENGTH,
                            weight="2",
                            constraint="true",
                        )
                        edge_set.add((prev_node, child_id))
                prev_node = child_id
        elif child_type == "group":
            with dot.subgraph(name=f"cluster_{child_id}") as sub_dot:
                subgroup_name = get_safe_value_bpmn(
                    updated_groups.loc[child_id], "name", ""
                )
                sub_dot.attr(
                    label=f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="2"><TR><TD ALIGN="left"><B>{subgroup_name}</B></TD></TR></TABLE>>',
                    style="rounded,dashed",
                    penwidth="1.0",
                    labelloc="t",
                    labeljust="l",
                    margin="10",
                    fontname="sans-serif",
                )
                subgroup_first, subgroup_last = add_group(
                    child_id,
                    sub_dot,
                    updated_nodes,
                    updated_groups,
                    edge_set,
                    processed_substeps,
                )
            if subgroup_first and subgroup_last:
                if first_node is None:
                    first_node = subgroup_first
                if first_real_node is None:
                    first_real_node = subgroup_first
                last_node = subgroup_last
                if (
                    group_type == "parallel"
                    and (child, child_id, _) in parallel_branches
                ):
                    idx = parallel_branches.index((child, child_id, _))
                    label = labels[idx] if idx < len(labels) else None
                    if (
                        gateway_split
                        and (gateway_split, subgroup_first) not in edge_set
                    ):
                        from_port = ""
                        to_port = get_port(subgroup_first, updated_nodes, "in")
                        dot.edge(
                            gateway_split + from_port,
                            subgroup_first + to_port,
                            xlabel=label,
                            labelangle="0",
                            labeldistance=EDGE_LABEL_DISTANCE,
                            minlen=str(float(EDGE_MIN_LENGTH) + 0.2),
                            weight="2",
                            constraint="true",
                        )
                        edge_set.add((gateway_split, subgroup_first))
                        gateway_connected_nodes.add(subgroup_first)
                    if gateway_join and (subgroup_last, gateway_join) not in edge_set:
                        from_port = get_port(subgroup_last, updated_nodes, "out")
                        to_port = ""
                        dot.edge(
                            subgroup_last + from_port,
                            gateway_join + to_port,
                            minlen=EDGE_MIN_LENGTH,
                            weight="2",
                            constraint="true",
                        )
                        edge_set.add((subgroup_last, gateway_join))
                        gateway_connected_nodes.add(subgroup_last)
                elif prev_node and (prev_node, subgroup_first) not in edge_set:
                    if (
                        prev_node not in gateway_connected_nodes
                        and subgroup_first not in gateway_connected_nodes
                    ):
                        from_port = get_port(prev_node, updated_nodes, "out")
                        to_port = get_port(subgroup_first, updated_nodes, "in")
                        dot.edge(
                            prev_node + from_port,
                            subgroup_first + to_port,
                            minlen=EDGE_MIN_LENGTH,
                            weight="2",
                            constraint="true",
                        )
                        edge_set.add((prev_node, subgroup_first))
                prev_node = subgroup_last

    if group_type == "parallel" and gateway_split and gateway_join:
        for i, branch in enumerate(parallel_branches):
            if branch[0] == "node":
                node_id = branch[1]
                label = labels[i] if i < len(labels) else None
                if (gateway_split, node_id) not in edge_set:
                    from_port = ""
                    to_port = get_port(node_id, updated_nodes, "in")
                    dot.edge(
                        gateway_split + from_port,
                        node_id + to_port,
                        xlabel=label,
                        labelangle="0",
                        labeldistance=EDGE_LABEL_DISTANCE,
                        minlen=str(float(EDGE_MIN_LENGTH) + 0.2),
                        weight="2",
                        constraint="true",
                    )
                    edge_set.add((gateway_split, node_id))
                    gateway_connected_nodes.add(node_id)
                if (node_id, gateway_join) not in edge_set:
                    from_port = get_port(node_id, updated_nodes, "out")
                    to_port = ""
                    dot.edge(
                        node_id + from_port,
                        gateway_join + to_port,
                        minlen=EDGE_MIN_LENGTH,
                        weight="2",
                        constraint="true",
                    )
                    edge_set.add((node_id, gateway_join))
                    gateway_connected_nodes.add(node_id)

    if (
        skip_gateway_split
        and skip_gateway_join
        and (skip_gateway_split, skip_gateway_join) not in edge_set
    ):
        skip_name = get_safe_value_bpmn(group, "skip_name")
        label = skip_name if skip_name else None
        dot.edge(
            skip_gateway_split,
            skip_gateway_join,
            xlabel=label,
            labelangle="0",
            labeldistance=EDGE_LABEL_DISTANCE,
            constraint="false",
            minlen=str(float(EDGE_MIN_LENGTH) + 0.5),
            weight="1",
        )
        edge_set.add((skip_gateway_split, skip_gateway_join))

    if (
        repeat_gateway
        and repeat_helper
        and (repeat_gateway, repeat_helper) not in edge_set
    ):
        repeat_name = get_safe_value_bpmn(group, "repeat_name")
        label = repeat_name if repeat_name else None
        dot.edge(
            repeat_gateway,
            repeat_helper,
            xlabel=label,
            labelangle="0",
            labeldistance=EDGE_LABEL_DISTANCE,
            constraint="false",
            minlen=str(float(EDGE_MIN_LENGTH) + 0.5),
            weight="1",
        )
        edge_set.add((repeat_gateway, repeat_helper))
    if (
        repeat_helper
        and first_real_node
        and (repeat_helper, first_real_node) not in edge_set
    ):
        from_port = get_port(repeat_helper, updated_nodes, "out")
        to_port = get_port(first_real_node, updated_nodes, "in")
        dot.edge(
            repeat_helper + from_port,
            first_real_node + to_port,
            minlen=EDGE_MIN_LENGTH,
            weight="2",
            constraint="true",
        )
        edge_set.add((repeat_helper, first_real_node))

    return first_node, last_node


def build_workflow_diagram(updated_nodes, updated_groups):
    """Generate the complete BPMN diagram."""
    dot = Digraph(
        format="svg",
        graph_attr={
            "rankdir": "LR",
            "splines": "ortho",
            "fontname": "sans-serif",
            "nodesep": GRAPH_NODE_SEPARATION,
            "ranksep": GRAPH_RANK_SEPARATION,
            "overlap": "false",
            "sep": "+5",
            "margin": "0.1",
            "concentrate": "true",
            "ordering": "out",
            "newrank": "true",
        },
        node_attr={"fontname": "sans-serif", "margin": "0.1"},
        edge_attr={"fontname": "sans-serif", "weight": "2"},
    )

    with dot.subgraph(name="cluster_flow_control") as flow:
        flow.attr(style="invis")
        flow.node("rank_start", style="invis", shape="none", width="0")
        flow.node("rank_end", style="invis", shape="none", width="0")
        flow.edge("rank_start", "rank_end", style="invis")

    dot.node(
        "start", shape="circle", label="", width="0.5", height="0.5", rank="source"
    )
    dot.node("end", shape="circle", label="", width="0.5", height="0.5", rank="sink")

    dot.edge("rank_start", "start", style="invis", weight="100")
    dot.edge("rank_end", "end", style="invis", weight="100")

    edge_set = set()
    top_group_id = updated_groups[updated_groups["parent"].isna()].index[0]

    with dot.subgraph(name=f"cluster_{top_group_id}") as c:
        c.attr(
            label=f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="2"><TR><TD ALIGN="left"><B>{updated_groups.at[top_group_id, "name"]}</B></TD></TR></TABLE>>',
            style="rounded,dashed",
            penwidth="1.5",
            labelloc="t",
            labeljust="l",
            margin="10",
            fontname="sans-serif",
        )
        first_node, last_node = add_group(
            top_group_id, c, updated_nodes, updated_groups, edge_set, set()
        )

    from_port = ""
    to_port = get_port(first_node, updated_nodes, "in")
    dot.edge(
        "start" + from_port,
        first_node + to_port,
        minlen="0.8",
        weight="10",
        constraint="true",
    )

    from_port = get_port(last_node, updated_nodes, "out")
    to_port = ""
    dot.edge(
        last_node + from_port,
        "end" + to_port,
        minlen="0.8",
        weight="10",
        constraint="true",
    )

    return dot


# --- BPMN XML HELPER FUNCTIONS ---


def get_safe_value_bpmn(data, key, default="something"):
    """Safely get a value from a data row, handling Series or scalar."""
    value = data.get(key, default)
    if isinstance(value, pd.Series):
        return value.iloc[0] if not value.empty else default
    return value if pd.notna(value) else default


def is_node_type(node_type, target_type):
    """Check if node_type matches or contains target_type."""
    return (
        str(node_type).lower() == target_type.lower()
        or target_type.lower() in str(node_type).lower()
    )


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
        "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    }

    # Register namespaces
    for prefix, uri in namespaces.items():
        ET.register_namespace(prefix, uri)

    # Create root element
    root = ET.Element(
        "bpmn:definitions",
        {
            "id": "definitions_1",
            "targetNamespace": "http://bpmn.io/schema/bpmn",
            "xmlns:bpmn": namespaces["bpmn"],
            "xmlns:bpmndi": namespaces["bpmndi"],
            "xmlns:dc": namespaces["dc"],
            "xmlns:di": namespaces["di"],
            "xmlns:xsi": namespaces["xsi"],
        },
    )

    # Create process element
    process = ET.SubElement(
        root, "bpmn:process", {"id": "process_1", "isExecutable": "true"}
    )

    # Identify connected nodes (nodes with edges)
    connected_nodes = set(edges_df["source"]).union(set(edges_df["target"]))
    connected_nodes.discard("start")
    connected_nodes.discard("end")

    # Filter main flow nodes (exclude "rule" and "substeps")
    flow_nodes = [
        n
        for n in connected_nodes
        if get_safe_value_bpmn(node_df.loc[n], "node_type", "")
        not in ["rule", "substeps"]
    ]

    # Create ID mapping for flow nodes and start/end
    id_mapping = {}
    for node_id in flow_nodes + ["start", "end"]:
        cleaned_id = (
            "id_" + node_id.replace("-", "").replace("_", "")
            if node_id in connected_nodes
            else f"id_{node_id}"
        )
        id_mapping[node_id] = cleaned_id
    reverse_id_mapping = {v: k for k, v in id_mapping.items()}

    # Filter edges for sequence flows (only between flow nodes)
    flow_edges = edges_df[
        (edges_df["source"].isin(flow_nodes + ["start"]))
        & (edges_df["target"].isin(flow_nodes + ["end"]))
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
        sequence_flows.append(
            {"id": flow_id, "source": source, "target": target, "label": edge["label"]}
        )
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
        empfanger = get_safe_value_bpmn(node_data, "Empfänger", "")

        if is_node_type(node_type, "activity"):
            task_type = get_safe_value_bpmn(node_data, "type", "")
            # Format the name to include Empfänger if it exists
            formatted_name = f"({empfanger})\n{name}" if empfanger else name

            # Split long labels into multiple lines at word boundaries
            def split_label(label, max_chars=15):
                if len(label) <= max_chars:
                    return label
                words = label.split(" ")
                lines = []
                current_line = ""
                for word in words:
                    if len(current_line) + len(word) + 1 <= max_chars:
                        current_line += word + " "
                    else:
                        if current_line:
                            lines.append(current_line.strip())
                        current_line = word + " "
                if current_line:
                    lines.append(current_line.strip())
                return "\n".join(lines)

            formatted_name = split_label(formatted_name)
            # Truncate if longer than 50 chars after splitting, preserving word boundaries
            if len(formatted_name.replace("\n", " ")) > 50:
                truncated = formatted_name[:50]
                last_space = truncated.rfind(" ")
                last_newline = truncated.rfind("\n")
                cut_point = (
                    max(last_space, last_newline)
                    if last_space > 0 or last_newline > 0
                    else 47
                )
                formatted_name = truncated[:cut_point] + "..."
            # Add some spaces at the beginning of the label to prevent overlap
            formatted_name = "  " + formatted_name

            if task_type == "manual":
                element = ET.SubElement(
                    process, "bpmn:userTask", {"id": cleaned_id, "name": formatted_name}
                )
            elif task_type == "script":
                element = ET.SubElement(
                    process,
                    "bpmn:scriptTask",
                    {"id": cleaned_id, "name": formatted_name},
                )
            elif task_type == "system":
                element = ET.SubElement(
                    process,
                    "bpmn:serviceTask",
                    {"id": cleaned_id, "name": formatted_name},
                )
            else:
                element = ET.SubElement(
                    process, "bpmn:task", {"id": cleaned_id, "name": formatted_name}
                )
        elif is_node_type(node_type, "decision"):
            # Check if this is a UserChoice decision node (by checking the type column)
            decision_type = get_safe_value_bpmn(node_data, "type", "")
            if decision_type == "UserChoice":
                # UserChoice decision nodes - display as manual task with hand symbol
                decision_name = label if pd.notna(label) else name
                element = ET.SubElement(
                    process,
                    "bpmn:manualTask",
                    {"id": cleaned_id, "name": decision_name},
                )
            else:
                # For other decision nodes, use only the first line (truncated)
                decision_name = (
                    label.split("\n")[0] or name if pd.notna(label) else name
                )
                element = ET.SubElement(
                    process,
                    "bpmn:businessRuleTask",
                    {"id": cleaned_id, "name": decision_name},
                )
        elif is_node_type(node_type, "gateway"):
            gateway_label = label if pd.notna(label) else ""
            gateway_type = (
                "bpmn:exclusiveGateway"
                if gateway_label == "X"
                else "bpmn:parallelGateway"
            )
            element = ET.SubElement(process, gateway_type, {"id": cleaned_id})
        elif is_node_type(node_type, "helper"):
            element = ET.SubElement(
                process, "bpmn:intermediateThrowEvent", {"id": cleaned_id}
            )
        else:
            element = ET.SubElement(
                process, "bpmn:task", {"id": cleaned_id, "name": name}
            )
        for flow_id in incoming_flows.get(cleaned_id, []):
            ET.SubElement(element, "bpmn:incoming").text = flow_id
        for flow_id in outgoing_flows.get(cleaned_id, []):
            ET.SubElement(element, "bpmn:outgoing").text = flow_id
        element_mapping[cleaned_id] = element

    # Add start and end events
    start_element = ET.SubElement(
        process, "bpmn:startEvent", {"id": id_mapping["start"]}
    )
    for flow_id in outgoing_flows[id_mapping["start"]]:
        ET.SubElement(start_element, "bpmn:outgoing").text = flow_id

    end_element = ET.SubElement(process, "bpmn:endEvent", {"id": id_mapping["end"]})
    for flow_id in incoming_flows[id_mapping["end"]]:
        ET.SubElement(end_element, "bpmn:incoming").text = flow_id

    # Add sequence flows to process
    for flow in sequence_flows:
        # Create the base flow element
        flow_attrs = {
            "id": flow["id"],
            "sourceRef": flow["source"],
            "targetRef": flow["target"],
        }

        # Add name attribute if there's a label
        if pd.notna(flow["label"]):
            flow_attrs["name"] = str(flow["label"])

        flow_element = ET.SubElement(process, "bpmn:sequenceFlow", flow_attrs)

        # Add condition expression for flows from gateways
        if pd.notna(flow["label"]):
            source_orig = reverse_id_mapping[flow["source"]]
            if source_orig in node_df.index and is_node_type(
                node_df.loc[source_orig, "node_type"], "gateway"
            ):
                condition = ET.SubElement(
                    flow_element,
                    "bpmn:conditionExpression",
                    {"xsi:type": "bpmn:tFormalExpression"},
                )
                condition.text = str(flow["label"])

    # Create diagram
    diagram = ET.SubElement(root, "bpmndi:BPMNDiagram", {"id": "BPMNDiagram_1"})
    plane = ET.SubElement(
        diagram, "bpmndi:BPMNPlane", {"id": "BPMNPlane_1", "bpmnElement": "process_1"}
    )
    node_positions = {}

    # Position flow nodes minimally (horizontal line)
    x_pos = 50
    for node_id in ["start"] + flow_nodes + ["end"]:
        cleaned_id = id_mapping[node_id]
        if node_id in ["start", "end"] or is_node_type(
            node_df.loc[node_id, "node_type"], "helper"
        ):
            width, height = 36, 36
        elif is_node_type(node_df.loc[node_id, "node_type"], "gateway"):
            width, height = 50, 50
        else:
            width, height = 100, 80
        node_positions[cleaned_id] = {
            "x": x_pos,
            "y": 100,
            "width": width,
            "height": height,
        }
        x_pos += 150

    # Create shapes
    for element_id, pos in node_positions.items():
        shape = ET.SubElement(
            plane,
            "bpmndi:BPMNShape",
            {"id": f"{element_id}_di", "bpmnElement": element_id},
        )
        ET.SubElement(shape, "dc:Bounds", {k: str(v) for k, v in pos.items()})

    # Create sequence flow edges with labels for diagram
    for flow in sequence_flows:
        edge = ET.SubElement(
            plane,
            "bpmndi:BPMNEdge",
            {"id": f"{flow['id']}_di", "bpmnElement": flow["id"]},
        )

        # Add label element for the edge if there's a label
        if pd.notna(flow["label"]):
            # Add a BPMNLabel element with centered position
            label_element = ET.SubElement(edge, "bpmndi:BPMNLabel")
            # Position will be determined by the layout engine

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
    Process BPMN XML, provide a file download mechanism, and handle file upload for further processing.

    Args:
        basic_xml (str): The input BPMN XML string to process.
    """
    # Initialize session state variables
    if "bpmn_workflow_state" not in st.session_state:
        st.session_state["bpmn_workflow_state"] = "initial"
    if "basic_bpmn_xml" not in st.session_state:
        st.session_state["basic_bpmn_xml"] = basic_xml
    if "bpmn_layout_result" not in st.session_state:
        st.session_state["bpmn_layout_result"] = None

    # Load the JavaScript library
    js_path = os.path.join(
        st.session_state["cwd"], "assets/bpmn-auto-layout.js"
    )  # Adjust path as needed
    if not os.path.exists(js_path):
        st.error(f"Cannot find bpmn-auto-layout.js at {js_path}")
        return
    with open(js_path, "r") as f:
        bpmn_layout_js = f.read()

    # Escape the XML to safely embed it in JavaScript
    escaped_xml = basic_xml.replace('"', '\\"').replace("\n", "\\n")

    # HTML component with file download capability
    html_content = f"""
    <html>
      <body>
        <div id="status">Processing layout...</div>
        <div id="xml-preview" style="font-family: monospace; height: 100px; overflow: auto; border: 1px solid #ccc; padding: 5px;"></div>
        <button id="download-button" style="padding: 8px; background-color: #1E88E5; color: white; border: none; border-radius: 4px;" disabled>Download Layout XML</button>
        <div id="status-message" style="margin-top: 10px;"></div>
        <div id="error-output" style="color: red;"></div>

        <script>
        {bpmn_layout_js}
        </script>
        <script>
          document.addEventListener('DOMContentLoaded', async function() {{
            const status = document.getElementById("status");
            const preview = document.getElementById("xml-preview");
            const downloadButton = document.getElementById("download-button");
            const statusMessage = document.getElementById("status-message");
            const errorOutput = document.getElementById("error-output");
            
            let layoutedXML = null;

            try {{
              status.textContent = "Processing BPMN layout...";
              const inputXML = "{escaped_xml}";
              layoutedXML = await BpmnAutoLayout.layoutProcess(inputXML);
              
              preview.textContent = layoutedXML.substring(0, 500) + "...";
              status.textContent = "Layout completed!";
              downloadButton.disabled = false;

              downloadButton.addEventListener("click", function() {{
                try {{
                  const blob = new Blob([layoutedXML], {{type: 'application/xml'}});
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = 'bpmn_layout.xml';
                  document.body.appendChild(a);
                  a.click();
                  setTimeout(function() {{
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                  }}, 0);
                  statusMessage.textContent = "✅ Layout downloaded! Now upload the XML file in Step 2 below.";
                  statusMessage.style.color = "green";
                }} catch (e) {{
                  errorOutput.textContent = "Error creating download: " + e.message;
                  console.error("Download error:", e);
                }}
              }});
            }} catch (e) {{
              errorOutput.textContent = "Error: " + e.message;
              console.error("Layout error:", e);
            }}
          }});
        </script>
      </body>
    </html>
    """

    # Step 1: Process and Download
    st.write("### Step 1: Process and Download the Layout")
    st.write(
        "Wait for processing to finish, then click 'Download Layout XML' to save the file:"
    )
    st.components.v1.html(html_content, height=250)

    # Step 2: Upload the Layout XML
    st.write("### Step 2: Upload the Layout XML")
    st.write("Upload the XML file you just downloaded:")
    uploaded_file = st.file_uploader(
        "Upload BPMN layout XML", type=["xml", "bpmn"], key="bpmn_layout_uploader"
    )

    # Handle file upload
    if uploaded_file is not None:
        try:
            # Read and decode the uploaded file
            xml_data = uploaded_file.read().decode("utf-8")
            # Validate it's XML
            if xml_data.startswith("<?xml"):
                st.session_state["bpmn_layout_result"] = xml_data
                st.session_state["bpmn_workflow_state"] = "uploaded"
                st.success(
                    f"✅ Successfully loaded BPMN layout! Length: {len(xml_data)} characters"
                )
            else:
                st.error("❌ The uploaded file doesn't appear to be valid XML.")
                st.write("File starts with:", xml_data[:100])
        except Exception as e:
            st.error(f"❌ Error processing uploaded file: {str(e)}")


def split_diagram_for_page_fit(
    laid_out_xml, node_df, edges_df, namespaces, process, plane
):
    """
    Splits a BPMN diagram into two lines for page fit, ensuring proper arrow connections
    and splitting after parallel conditions are closed.

    Args:
        laid_out_xml (str): The input BPMN XML string.
        node_df, edges_df: DataFrames (not used here but kept for compatibility).
        namespaces (dict): XML namespaces.
        process: BPMN process element (passed for convenience).
        plane: BPMNPlane element (passed for convenience).

    Returns:
        tuple: (updated XML string, boolean indicating if splitting occurred)
    """
    import xml.etree.ElementTree as ET

    # Constants
    A4_WIDTH_GUIDELINE = 800  # A4 width guideline in pixels (relaxed for first line)
    SPACING_Y = 350  # Vertical spacing between lines
    MIN_NODES_PER_LINE = 8  # Minimum nodes per line to consider splitting

    # Parse XML and find elements
    root = ET.fromstring(laid_out_xml)
    process = root.find(".//bpmn:process", namespaces)
    plane = root.find(".//bpmndi:BPMNPlane", namespaces)
    shapes = plane.findall(".//bpmndi:BPMNShape", namespaces)
    if not shapes:
        return laid_out_xml, False

    # Extract node positions
    original_positions = {}
    positions = {}
    for shape in shapes:
        bpmn_element = shape.get("bpmnElement")
        bounds = shape.find("dc:Bounds", namespaces)
        if bounds is not None:
            x = float(bounds.get("x"))
            y = float(bounds.get("y"))
            width = float(bounds.get("width"))
            height = float(bounds.get("height"))
            original_positions[bpmn_element] = {
                "x": x,
                "y": y,
                "width": width,
                "height": height,
            }
            positions[bpmn_element] = {"x": x, "y": y, "width": width, "height": height}

    # Build flow dictionary
    sequence_flows = process.findall(".//bpmn:sequenceFlow", namespaces)
    flow_dict = {
        flow.get("id"): (flow.get("sourceRef"), flow.get("targetRef"))
        for flow in sequence_flows
    }

    # Sort nodes by x-position, then y-position
    node_sequence = sorted(
        positions.keys(), key=lambda nid: (positions[nid]["x"], positions[nid]["y"])
    )
    total_nodes = len(node_sequence)

    # Check if splitting is necessary
    if total_nodes < MIN_NODES_PER_LINE * 2:
        return laid_out_xml, False

    max_x = max(pos["x"] + pos["width"] for pos in positions.values())
    min_x = min(pos["x"] for pos in positions.values())
    diagram_width = max_x - min_x
    if diagram_width <= A4_WIDTH_GUIDELINE:
        return laid_out_xml, False

    # Helper functions to identify gateways
    def get_incoming_flows(node_id):
        return process.findall(
            f".//bpmn:sequenceFlow[@targetRef='{node_id}']", namespaces
        )

    def get_outgoing_flows(node_id):
        return process.findall(
            f".//bpmn:sequenceFlow[@sourceRef='{node_id}']", namespaces
        )

    def is_split_gateway(node_id):
        incoming = get_incoming_flows(node_id)
        outgoing = get_outgoing_flows(node_id)
        return len(incoming) == 1 and len(outgoing) > 1

    def is_join_gateway(node_id):
        incoming = get_incoming_flows(node_id)
        outgoing = get_outgoing_flows(node_id)
        return len(incoming) > 1 and len(outgoing) == 1

    # Find split point after parallel conditions are closed
    open_splits = 0
    split_candidates = []
    for idx, node in enumerate(node_sequence[:-1]):
        if is_split_gateway(node):
            open_splits += 1
        elif is_join_gateway(node):
            open_splits -= 1
        if open_splits == 0 and idx >= total_nodes // 4:
            split_candidates.append(idx)

    # Select split point
    if split_candidates:
        split_idx = min(split_candidates, key=lambda x: abs(x - total_nodes // 2))
    else:
        split_idx = total_nodes // 2  # Fallback, though rare with candidates present

    line_nodes = [node_sequence[: split_idx + 1], node_sequence[split_idx + 1 :]]

    # Calculate shifts for second line
    initial_x = min_x
    first_line_max_y = max(
        positions[n]["y"] + positions[n]["height"] for n in line_nodes[0]
    )
    current_line_y_offset = first_line_max_y + SPACING_Y
    delta_x = initial_x - positions[line_nodes[0][-1]]["x"]
    delta_y = current_line_y_offset

    # Shift nodes in second line
    for node in line_nodes[1]:
        if node in positions:
            shape = plane.find(
                f".//bpmndi:BPMNShape[@bpmnElement='{node}']", namespaces
            )
            bounds = shape.find("dc:Bounds", namespaces)
            old_x = float(bounds.get("x"))
            old_y = float(bounds.get("y"))
            new_x = old_x + delta_x
            new_y = old_y + delta_y
            bounds.set("x", str(new_x))
            bounds.set("y", str(new_y))
            positions[node]["x"] = new_x
            positions[node]["y"] = new_y

    # Add continuation indicators
    last_node_id = line_nodes[0][-1]
    first_node_id = line_nodes[1][0]

    throw_id = "ContinuationThrow"
    throw_event = ET.SubElement(
        process, "bpmn:intermediateThrowEvent", {"id": throw_id, "name": "A"}
    )
    ET.SubElement(
        throw_event, "bpmn:linkEventDefinition", {"id": "LinkDef_Throw", "name": "Link"}
    )
    throw_x = positions[last_node_id]["x"] + positions[last_node_id]["width"] + 50
    throw_y = (
        positions[last_node_id]["y"] + (positions[last_node_id]["height"] - 36) / 2
    )
    throw_shape = ET.SubElement(
        plane, "bpmndi:BPMNShape", {"id": f"{throw_id}_di", "bpmnElement": throw_id}
    )
    ET.SubElement(
        throw_shape,
        "dc:Bounds",
        {"x": str(throw_x), "y": str(throw_y), "width": "36", "height": "36"},
    )

    catch_id = "ContinuationCatch"
    catch_event = ET.SubElement(
        process, "bpmn:intermediateCatchEvent", {"id": catch_id, "name": "A"}
    )
    ET.SubElement(
        catch_event, "bpmn:linkEventDefinition", {"id": "LinkDef_Catch", "name": "Link"}
    )
    catch_x = positions[first_node_id]["x"] - 50 - 36
    catch_y = (
        positions[first_node_id]["y"] + (positions[first_node_id]["height"] - 36) / 2
    )
    catch_shape = ET.SubElement(
        plane, "bpmndi:BPMNShape", {"id": f"{catch_id}_di", "bpmnElement": catch_id}
    )
    ET.SubElement(
        catch_shape,
        "dc:Bounds",
        {"x": str(catch_x), "y": str(catch_y), "width": "36", "height": "36"},
    )

    flow_throw_id = "Flow_Throw"
    last_node = process.find(f".//*[@id='{last_node_id}']", namespaces)
    ET.SubElement(last_node, "bpmn:outgoing").text = flow_throw_id
    ET.SubElement(throw_event, "bpmn:incoming").text = flow_throw_id
    flow_throw = ET.SubElement(
        process,
        "bpmn:sequenceFlow",
        {"id": flow_throw_id, "sourceRef": last_node_id, "targetRef": throw_id},
    )
    flow_throw_edge = ET.SubElement(
        plane,
        "bpmndi:BPMNEdge",
        {"id": f"{flow_throw_id}_di", "bpmnElement": flow_throw_id},
    )
    ET.SubElement(
        flow_throw_edge,
        "di:waypoint",
        {
            "x": str(positions[last_node_id]["x"] + positions[last_node_id]["width"]),
            "y": str(
                positions[last_node_id]["y"] + positions[last_node_id]["height"] / 2
            ),
        },
    )
    ET.SubElement(
        flow_throw_edge, "di:waypoint", {"x": str(throw_x), "y": str(throw_y + 18)}
    )

    flow_catch_id = "Flow_Catch"
    ET.SubElement(catch_event, "bpmn:outgoing").text = flow_catch_id
    first_node = process.find(f".//*[@id='{first_node_id}']", namespaces)
    ET.SubElement(first_node, "bpmn:incoming").text = flow_catch_id
    flow_catch = ET.SubElement(
        process,
        "bpmn:sequenceFlow",
        {"id": flow_catch_id, "sourceRef": catch_id, "targetRef": first_node_id},
    )
    flow_catch_edge = ET.SubElement(
        plane,
        "bpmndi:BPMNEdge",
        {"id": f"{flow_catch_id}_di", "bpmnElement": flow_catch_id},
    )
    ET.SubElement(
        flow_catch_edge, "di:waypoint", {"x": str(catch_x + 36), "y": str(catch_y + 18)}
    )
    ET.SubElement(
        flow_catch_edge,
        "di:waypoint",
        {
            "x": str(positions[first_node_id]["x"]),
            "y": str(
                positions[first_node_id]["y"] + positions[first_node_id]["height"] / 2
            ),
        },
    )

    # Remove crossing edges
    edges_to_remove = []
    for edge in process.findall(".//bpmn:sequenceFlow", namespaces):
        source_ref = edge.get("sourceRef")
        target_ref = edge.get("targetRef")
        source_line = next(
            (i for i, line in enumerate(line_nodes) if source_ref in line), None
        )
        target_line = next(
            (i for i, line in enumerate(line_nodes) if target_ref in line), None
        )
        if (
            source_line != target_line
            and source_line is not None
            and target_line is not None
        ):
            edges_to_remove.append(edge.get("id"))

    for edge_id in edges_to_remove:
        edge_elem = process.find(f".//bpmn:sequenceFlow[@id='{edge_id}']", namespaces)
        if edge_elem is not None:
            process.remove(edge_elem)
        edge_di_elem = plane.find(
            f".//bpmndi:BPMNEdge[@bpmnElement='{edge_id}']", namespaces
        )
        if edge_di_elem is not None:
            plane.remove(edge_di_elem)

    # Shift edges within the second line
    for edge in plane.findall(".//bpmndi:BPMNEdge", namespaces):
        bpmn_element = edge.get("bpmnElement")
        if bpmn_element in flow_dict:
            source, target = flow_dict[bpmn_element]
            if source in line_nodes[1] and target in line_nodes[1]:
                waypoints = edge.findall("di:waypoint", namespaces)
                for wp in waypoints:
                    old_x = float(wp.get("x"))
                    old_y = float(wp.get("y"))
                    new_x = old_x + delta_x
                    new_y = old_y + delta_y
                    wp.set("x", str(new_x))
                    wp.set("y", str(new_y))

    # Serialize and return updated XML
    updated_xml = ET.tostring(root, encoding="utf-8").decode("utf-8")
    return updated_xml, True


def add_special_nodes_and_annotations(split_diagrams=False, include_legend=False):
    """
    Adds 'rule' and 'substep' nodes as DataObjectReference elements below their parents
    in the BPMN diagram, connects them with DataOutputAssociation edges, and optionally
    creates text annotations with full labels below the diagram.

    Args:
        split_diagrams (bool): Whether to split the diagram for page fit
        include_legend (bool): Whether to include text annotations/legend below the diagram

    Returns:
        tuple: (updated BPMN XML string, legend DataFrame) or (None, None) if processing fails
    """
    # Check if the laid-out BPMN XML is available
    if (
        "bpmn_layout_result" not in st.session_state
        or st.session_state["bpmn_layout_result"] is None
    ):
        st.error("No BPMN layout result is available. Please process the layout first.")
        return None, None

    # Load the laid-out BPMN XML from session state
    laid_out_xml = st.session_state["bpmn_layout_result"]
    try:
        root = ET.fromstring(laid_out_xml)

        # Access node_df and edges_df from session state (assumed to be set in Step 1)
        if "nodes_df" not in st.session_state:
            st.error("Node data is missing. Please generate the workflow first.")
            return None, None

        node_df = st.session_state["nodes_df"]
        edges_df = st.session_state["edges_df"]

        # Namespace definitions for BPMN XML
        namespaces = {
            "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
            "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
            "dc": "http://www.omg.org/spec/DD/20100524/DC",
            "di": "http://www.omg.org/spec/DD/20100524/DI",
        }

        # Find process and plane elements in the XML
        process = root.find(".//bpmn:process", namespaces)
        plane = root.find(".//bpmndi:BPMNPlane", namespaces)

        # Optional Step: Split diagram if too wide for A4 page
        if split_diagrams:
            laid_out_xml, was_split = split_diagram_for_page_fit(
                laid_out_xml, node_df, edges_df, namespaces, process, plane
            )
            root = ET.fromstring(laid_out_xml)  # Always update root from laid_out_xml
            process = root.find(".//bpmn:process", namespaces)
            plane = root.find(".//bpmndi:BPMNPlane", namespaces)
            # Ensure the updated XML is stored for consistent use
            st.session_state["bpmn_layout_result"] = laid_out_xml

        # Step 1: Identify "rule" and "substep" nodes
        special_nodes = node_df[node_df["node_type"].isin(["rule", "substeps"])]
        if special_nodes.empty:
            # Still need to collect user legend entries and create DataFrame
            legend_entries = []
            task_nodes = node_df[node_df["node_type"] == "activity"]
            if not task_nodes.empty and "user_legend" in st.session_state:
                user_legend_dict = st.session_state["user_legend"]
                used_abbreviations = set()
                for index, row in task_nodes.iterrows():
                    label = str(row["Empfänger"])
                    for abbr, full_name in user_legend_dict.items():
                        if abbr in label and abbr not in used_abbreviations:
                            used_abbreviations.add(abbr)
                            legend_entries.append(
                                {"#": abbr, "Typ": "Abkürzung", "Legende": full_name}
                            )
            legend_df = pd.DataFrame(legend_entries).reset_index(drop=True)
            return laid_out_xml, legend_df

        # Step 2: Extract parent positions from the laid-out diagram
        parent_positions = {}
        for shape in plane.findall(".//bpmndi:BPMNShape", namespaces):
            bpmn_element = shape.get("bpmnElement")
            bounds = shape.find("dc:Bounds", namespaces)
            if bounds is not None:
                x = float(bounds.get("x"))
                y = float(bounds.get("y"))
                width = float(bounds.get("width"))
                height = float(bounds.get("height"))
                parent_positions[bpmn_element] = {
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                }

        # Step 3: Sort special nodes by parent x-coordinate
        def get_parent_x(node_row):
            parent_id = node_row["parent"]
            parent_key = parent_id
            if parent_key not in parent_positions:
                parent_key = "id_" + str(parent_id).replace("-", "").replace("_", "")
            return parent_positions.get(parent_key, {}).get("x", 0)

        special_nodes = special_nodes.copy()
        special_nodes["parent_x"] = special_nodes.apply(get_parent_x, axis=1)
        special_nodes = special_nodes.sort_values("parent_x")

        # Step 4: Add DataObjectReference nodes and DataOutputAssociation edges
        legend_counter = 1
        annotations = []  # Store annotation data for later placement
        legend_entries = []  # Store legend entries for DataFrame
        for index, row in special_nodes.iterrows():
            parent_id = row["parent"]
            # Map parent id to the cleaned id used in the BPMN XML
            parent_key = parent_id
            if parent_key not in parent_positions:
                parent_key = "id_" + str(parent_id).replace("-", "").replace("_", "")
            if parent_key in parent_positions:
                parent_pos = parent_positions[parent_key]
            else:
                # If still not found, skip this special node
                continue

            data_ref_id = f"DataObjectRef_{index}"
            data_object_id = f"DataObject_{index}"
            association_id = f"Association_{index}"
            legend_label = f"({legend_counter})"

            # Create DataObject and DataObjectReference in the process
            ET.SubElement(process, "bpmn:dataObject", {"id": data_object_id})
            data_ref = ET.SubElement(
                process,
                "bpmn:dataObjectReference",
                {
                    "id": data_ref_id,
                    "dataObjectRef": data_object_id,
                    "name": legend_label,  # Use legend reference instead of full label
                },
            )

            # Connect with DataOutputAssociation for compatibility with BPMN viewers
            parent_element = process.find(f".//*[@id='{parent_key}']")
            if parent_element is not None:
                association = ET.SubElement(
                    parent_element, "bpmn:dataOutputAssociation", {"id": association_id}
                )
                ET.SubElement(association, "bpmn:targetRef").text = data_ref_id
                ET.SubElement(association, "bpmn:sourceRef").text = parent_key

            # Position DataObjectReference 35 pixels below parent (centered horizontally)
            data_ref_x = parent_pos["x"] + (parent_pos["width"] - 36) / 2
            data_ref_y = parent_pos["y"] + parent_pos["height"] + 30
            data_ref_shape = ET.SubElement(
                plane,
                "bpmndi:BPMNShape",
                {"id": f"{data_ref_id}_di", "bpmnElement": data_ref_id},
            )
            ET.SubElement(
                data_ref_shape,
                "dc:Bounds",
                {
                    "x": str(data_ref_x),
                    "y": str(data_ref_y),
                    "width": "36",
                    "height": "50",
                },
            )

            # Add DataOutputAssociation edge with waypoints and style as dotted line
            edge = ET.SubElement(
                plane,
                "bpmndi:BPMNEdge",
                {
                    "id": f"{association_id}_di",
                    "bpmnElement": association_id,
                    "isMarkerVisible": "true",
                },
            )
            ET.SubElement(
                edge,
                "di:waypoint",
                {
                    "x": str(
                        parent_pos["x"] + parent_pos["width"] / 2
                    ),  # Start at bottom center of parent
                    "y": str(parent_pos["y"] + parent_pos["height"]),
                },
            )
            ET.SubElement(
                edge,
                "di:waypoint",
                {
                    "x": str(
                        data_ref_x + 18
                    ),  # End at top center of DataObjectReference
                    "y": str(data_ref_y),
                },
            )
            # Add style for dotted line, ensuring correct namespace and structure
            style = ET.SubElement(edge, "bpmndi:style")
            ET.SubElement(
                style, "bpmndi:Stroke", {"dashArray": "5,5", "color": "#000000"}
            )

            # Store annotation info
            annotation_text = f"({legend_counter})\n{row['label']}"
            annotations.append((annotation_text, legend_counter))

            # Determine legend type based on node_type
            node_type = row["node_type"]
            if node_type == "rule":
                legend_type = "Regel"
            elif node_type == "substeps":
                legend_type = "Arbeitsschritte"
            else:
                legend_type = "Sonstiges"  # fallback

            # Store legend entry for DataFrame
            legend_entries.append(
                {"#": legend_counter, "Typ": legend_type, "Legende": row["label"]}
            )

            legend_counter += 1

        # Step 5: Collect user abbreviations for legend DataFrame (regardless of include_legend)
        user_legend_entries = []
        task_nodes = node_df[node_df["node_type"] == "activity"]
        if not task_nodes.empty and "user_legend" in st.session_state:
            user_legend_dict = st.session_state["user_legend"]
            used_abbreviations = set()
            for index, row in task_nodes.iterrows():
                label = str(row["Empfänger"])
                for abbr, full_name in user_legend_dict.items():
                    if abbr in label and abbr not in used_abbreviations:
                        user_legend_entries.append((abbr, full_name))
                        used_abbreviations.add(abbr)
                        # Store user abbreviation legend entry for DataFrame
                        legend_entries.append(
                            {"#": abbr, "Typ": "Abkürzung", "Legende": full_name}
                        )

        # Step 6: Generate text annotations only if include_legend is True
        if include_legend:
            # Step 5.1: Determine the bottom of the main diagram
            max_y = max(
                [pos["y"] + pos["height"] for pos in parent_positions.values()],
                default=0,
            )
            annotation_y = max_y + 150  # 100 pixels below the main diagram

            # Note: user_legend_entries already collected above

            # Step 6: Add text annotations horizontally
            annotation_x = 50  # Starting x position
            for annotation_text, counter in annotations:
                annotation_id = f"TextAnnotation_{counter}"
                annotation = ET.SubElement(
                    process, "bpmn:textAnnotation", {"id": annotation_id}
                )
                ET.SubElement(annotation, "bpmn:text").text = annotation_text

                # Position the annotation
                annotation_shape = ET.SubElement(
                    plane,
                    "bpmndi:BPMNShape",
                    {"id": f"{annotation_id}_di", "bpmnElement": annotation_id},
                )
                # Calculate height based on annotation_text length
                height = 50 + (len(annotation_text) // 100) * 50
                ET.SubElement(
                    annotation_shape,
                    "dc:Bounds",
                    {
                        "x": str(annotation_x),
                        "y": str(annotation_y),
                        "width": "300",
                        "height": str(height),
                    },
                )

                # Move to the next position (300 width + 50 space)
                annotation_x += 350

            # Step 6.5: Add user legend entries after numbered annotations
            for abbr, full_name in user_legend_entries:
                annotation_id = f"TextAnnotation_user_{abbr}"
                annotation_text = f"({abbr})\n{full_name}"
                annotation = ET.SubElement(
                    process, "bpmn:textAnnotation", {"id": annotation_id}
                )
                ET.SubElement(annotation, "bpmn:text").text = annotation_text

                # Position the annotation
                annotation_shape = ET.SubElement(
                    plane,
                    "bpmndi:BPMNShape",
                    {"id": f"{annotation_id}_di", "bpmnElement": annotation_id},
                )
                height = 50
                ET.SubElement(
                    annotation_shape,
                    "dc:Bounds",
                    {
                        "x": str(annotation_x),
                        "y": str(annotation_y),
                        "width": "300",
                        "height": str(height),
                    },
                )

                # Move to the next position (300 width + 50 space)
                annotation_x += 350

        # Step 7: Create legend DataFrame and return both XML and DataFrame
        legend_df = pd.DataFrame(legend_entries).reset_index(drop=True)
        updated_xml = ET.tostring(root, encoding="utf-8").decode("utf-8")
        return updated_xml, legend_df

    except Exception as e:
        st.error(f"Error adding annotations to BPMN: {str(e)}")
        return None, None


def bpmn_modeler_component(bpmn_xml):
    """Render BPMN diagram using bpmn-js with embedded resources and download buttons for BPMN and SVG."""
    # Paths
    BASE_DIR = st.session_state["cwd"]
    STATIC_DIR = os.path.join(BASE_DIR, "assets")

    # Get the filename from session state
    base_filename = st.session_state.get("dossier_filename", "diagram")
    bpmn_filename = f"{base_filename}.bpmn"
    svg_filename = f"{base_filename}.svg"

    # Read CSS and JS files as base64
    try:
        # Read CSS files
        with open(os.path.join(STATIC_DIR, "bpmn-js.css"), "rb") as f:
            bpmn_js_css = f.read().decode("utf-8")

        with open(os.path.join(STATIC_DIR, "diagram-js.css"), "rb") as f:
            diagram_js_css = f.read().decode("utf-8")

        # Read font files and encode them as base64
        font_files = {
            "eot": "application/vnd.ms-fontobject",
            "woff2": "font/woff2",
            "woff": "font/woff",
            "ttf": "font/ttf",
            "svg": "image/svg+xml",
        }

        font_data = {}
        for ext, mime_type in font_files.items():
            font_path = os.path.join(STATIC_DIR, f"bpmn-font/font/bpmn.{ext}")
            if os.path.exists(font_path):
                with open(font_path, "rb") as f:
                    font_base64 = base64.b64encode(f.read()).decode("utf-8")
                    font_data[ext] = f"data:{mime_type};base64,{font_base64}"

        # Read original font CSS
        with open(os.path.join(STATIC_DIR, "bpmn-font/css/bpmn.css"), "rb") as f:
            bpmn_font_css = f.read().decode("utf-8")

        # Replace font URLs with data URIs in the CSS
        for ext, data_uri in font_data.items():
            # Match patterns like: url('../font/bpmn.eot?21877404') or url('../font/bpmn.eot?21877404#iefix')
            pattern = (
                rf"url\(['\"](\.\.\/font\/bpmn\.{ext}(\?[^'\")]+)?)(#[^'\")]+)?['\"]\)"
            )
            replacement = f"url('{data_uri}')"
            bpmn_font_css = re.sub(pattern, replacement, bpmn_font_css)

        # HTML template with embedded resources and download buttons
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="UTF-8" />
        <style>
            {bpmn_js_css}
        </style>
        <style>
            {diagram_js_css}
        </style>
        <style>
            {bpmn_font_css}
        </style>
        <style>
            #canvas {{ 
                height: calc(100% - 40px); 
                width: 100%; 
                position: absolute; 
                left: 0;
                top: 40px;
            }}
            .download-btn {{
                position: absolute;
                top: 5px;
                z-index: 1000;
                padding: 8px 16px;
                background-color: #1E88E5;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }}
            #download-bpmn {{
                left: 5px;
            }}
            #download-svg {{
                left: 150px;
            }}
            #download-png {{
                left: 295px;
            }}
            html, body {{ 
                height: 100%; 
                width: 100%; 
                margin: 0;
                padding: 0;
            }}
        </style>
        </head>
        <body>
        <button id="download-bpmn" class="download-btn">Download BPMN</button>
        <button id="download-svg" class="download-btn">Download SVG</button>
        <button id="download-png" class="download-btn">Download PNG</button>
        <div id="canvas"></div>
        <script>
            {base64.b64decode(base64.b64encode(open(os.path.join(STATIC_DIR, 'bpmn-modeler.development.js'), 'rb').read())).decode('utf-8')}
        </script>
        <script>
            var diagramXML = `{bpmn_xml}`;
            var bpmnFilename = `{bpmn_filename}`;
            var svgFilename = `{svg_filename}`;
            var pngFilename = `{base_filename}.png`;
            var modeler = new BpmnJS({{ container: '#canvas' }});
            
            async function openDiagram(xml) {{
                try {{
                    await modeler.importXML(xml);
                    modeler.get('canvas').zoom('fit-viewport');
                }} catch (err) {{
                    console.error('Error importing XML:', err);
                }}
            }}
            
            async function saveBPMN() {{
                try {{
                    const {{ xml }} = await modeler.saveXML({{ format: true }});
                    console.log('Saved BPMN XML:', xml);
                    // Trigger a download (client-side)
                    const blob = new Blob([xml], {{ type: 'text/xml' }});
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = bpmnFilename;
                    a.click();
                    URL.revokeObjectURL(url);
                }} catch (err) {{
                    console.error('Error saving BPMN XML:', err);
                }}
            }}
            
            async function saveSVG() {{
                try {{
                    const result = await modeler.saveSVG();
                    const svgContent = result.svg;
                    // Add XML declaration and doctype only if not already present
                    let svgWithHeader = svgContent;
                    if (!svgContent.trim().startsWith('<?xml')) {{
                        svgWithHeader = '<?xml version="1.0" standalone="no"?>' + 
                                        '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">' + 
                                        svgContent;
                    }}
                    const blob = new Blob([svgWithHeader], {{ type: 'image/svg+xml' }});
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = svgFilename;
                    a.click();
                    URL.revokeObjectURL(url);
                }} catch (err) {{
                    console.error('Error saving SVG:', err);
                }}
            }}
            
            async function savePNG() {{
                try {{
                    const result = await modeler.saveSVG();
                    const svgContent = result.svg;
                    
                    // Scale factor for higher DPI (2x = 144 DPI, 3x = 216 DPI, 4x = 288 DPI)
                    const scaleFactor = 3;
                    
                    // Create a new Image element
                    const img = new Image();
                    
                    // Create a promise to handle the image loading
                    const imageLoaded = new Promise((resolve, reject) => {{
                        img.onload = resolve;
                        img.onerror = reject;
                    }});
                    
                    // Convert SVG to data URL
                    const svgBlob = new Blob([svgContent], {{ type: 'image/svg+xml;charset=utf-8' }});
                    const svgUrl = URL.createObjectURL(svgBlob);
                    img.src = svgUrl;
                    
                    // Wait for image to load
                    await imageLoaded;
                    
                    // Create canvas with scaled dimensions for higher resolution
                    const canvas = document.createElement('canvas');
                    const ctx = canvas.getContext('2d');
                    
                    // Get original dimensions
                    const originalWidth = img.naturalWidth || img.width;
                    const originalHeight = img.naturalHeight || img.height;
                    
                    // Set canvas size to scaled dimensions for higher DPI
                    canvas.width = originalWidth * scaleFactor;
                    canvas.height = originalHeight * scaleFactor;
                    
                    // Scale the drawing context to match
                    ctx.scale(scaleFactor, scaleFactor);
                    
                    // Enable image smoothing for better quality
                    ctx.imageSmoothingEnabled = true;
                    ctx.imageSmoothingQuality = 'high';
                    
                    // Fill with white background
                    ctx.fillStyle = 'white';
                    ctx.fillRect(0, 0, originalWidth, originalHeight);
                    
                    // Draw the SVG image onto the scaled canvas
                    ctx.drawImage(img, 0, 0, originalWidth, originalHeight);
                    
                    // Convert canvas to PNG blob with high quality
                    canvas.toBlob((blob) => {{
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = pngFilename;
                        a.click();
                        URL.revokeObjectURL(url);
                        URL.revokeObjectURL(svgUrl);
                    }}, 'image/png', 0.95);
                    
                }} catch (err) {{
                    console.error('Error saving PNG:', err);
                }}
            }}
            
            document.getElementById('download-bpmn').addEventListener('click', saveBPMN);
            document.getElementById('download-svg').addEventListener('click', saveSVG);
            document.getElementById('download-png').addEventListener('click', savePNG);
            openDiagram(diagramXML);
        </script>
        <script>
          modeler.on('element.changed', function(event) {{
            const element = event.element;
            if (element.waypoints) {{
                element.di.set('strokeWidth', 2); // Ensure consistent edge thickness
            }}
          }});
        </script>
        </body>
        </html>
        """

        # Render in Streamlit
        st.components.v1.html(html_template, height=700, scrolling=True)

    except Exception as e:
        st.error(f"Error loading BPMN viewer: {str(e)}")
        st.info(
            "Make sure all required files exist in the assets directory: bpmn-js.css, diagram-js.css, bpmn-font/css/bpmn.css, and bpmn-modeler.development.js"
        )


# --- Main Page Structure ---


def show():
    initialize_state()

    with st.expander("User Management", expanded=False):
        st.success(
            f"Currently {len(st.session_state['user_dict'])} user entries stored."
        )
        st.subheader("Upload Data")
        upload_user_list()
        modify_user_entries()  # All user management logic moved here

    st.subheader("Upload Prozess Export")
    xls = upload_dossier()

    if xls is not None:
        activities_table = build_activities_table(xls)
        groups_table = build_groups_table(xls)
        check_for_unknown_groups(xls, groups_table, activities_table)
        # Set the correct indices before calling generate_additional_nodes
        activities_index = activities_table.set_index("TransportID").copy()
        groups_index = groups_table.set_index("id").copy()

        # Now call the function with properly indexed dataframes
        try:
            updated_nodes, updated_groups = generate_additional_nodes(
                activities_index, groups_index
            )
            st.session_state["nodes_df"] = updated_nodes
            edges_table = build_edges_table(updated_nodes, updated_groups)
            st.session_state["edges_df"] = edges_table
            # Debugging
            # st.write(updated_nodes.to_dict())
            # st.write(updated_groups.to_dict())
            # st.write(edges_table.to_dict())
            with st.expander("Data Details", expanded=False):
                # st.write(st.session_state['user_dict'])
                # st.write("Aktivitäten")
                # st.dataframe(activities_table)
                # st.write("Platzhalter")
                # st.dataframe(groups_table)
                st.write("Nodes")
                st.dataframe(updated_nodes.reset_index())
                st.write("Groups")
                st.dataframe(updated_groups.reset_index())
                st.write("Edges")
                st.dataframe(edges_table)
            try:
                st.subheader("Workflow Diagram")

                # --- Deprecated Graphviz approach ---
                # diagram = build_workflow_diagram(updated_nodes, updated_groups)
                # # Save the DOT representation to a file (for debugging if needed)
                # diagram.save('bpmn_diagram.dot')
                # # Render the diagram with view=False to prevent it from opening automatically
                # svg_path = diagram.render('workflow_diagram', format='svg', cleanup=False, view=False)
                # # Display the diagram directly in Streamlit
                # st.graphviz_chart(diagram)

                # Create download buttons for the SVG and BPMN XML
                # col1, col2 = st.columns(2)
                # with col1:
                #     try:
                #         with open(svg_path, "rb") as file:
                #             btn = st.download_button(
                #                 label="Download as SVG",
                #                 data=file,
                #                 file_name="workflow_diagram.svg",
                #                 mime="image/svg+xml",
                #             )
                #     except Exception as e:
                #         st.warning(f"Could not create download button. Error: {str(e)}")

                basic_xml = create_main_flow_bpmn_xml(updated_nodes, edges_table)

                # if st.button("Generate BPMN XML"):
                #     # Create download button for basic XML
                #     st.download_button(
                #         label="Download Basic BPMN XML",
                #         data=basic_xml,
                #         file_name="basic_workflow.bpmn",
                #         mime="application/xml"
                #     )
                
                process_bpmn_layout(basic_xml)

                col1, col2, _, _ = st.columns(4)
                with col1:
                    split_diagrams = st.checkbox(
                        "Split long diagrams", value=False, key="split_diagrams"
                    )
                with col2:
                    include_legend = st.checkbox(
                        "Include legend", value=False, key="include_legend"
                    )
                if st.button("Generate Laid-Out BPMN XML"):
                    split_diagrams = st.session_state.get("split_diagrams", False)
                    include_legend = st.session_state.get("include_legend", False)
                    result_xml, legend_df = add_special_nodes_and_annotations(
                        split_diagrams, include_legend
                    )
                    if result_xml is not None:
                        bpmn_modeler_component(result_xml)

                        # Display legend DataFrame if it has entries
                        if not legend_df.empty:
                            st.subheader("Legende")
                            st.dataframe(
                                legend_df, use_container_width=True, hide_index=True
                            )
                    else:
                        st.info(
                            "Please wait for the layout processing to complete and then try again."
                        )
            except Exception as e:
                st.error(f"Error generating workflow diagram: {str(e)}")
                st.exception(e)
        except Exception as e:
            st.error(f"Error in generate_additional_nodes: {str(e)}")
            st.exception(e)
