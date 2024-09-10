import glob
import os
import numpy as np


def generate_dataframe_html(df):
    # wrap table with a div to add a horizontal scrollbar
    table_html = df.to_html(header=True, classes=["no_style_div"], render_links=False)
    html_string = f"""
    <div style="overflow-x: auto; border: 1px solid #e6e9ef; margin-bottom: 2em; padding: 1em;">
        {table_html}
    
    """
    # warning: I removed the closing </div> above, since it was shown in plain text. it works now, but could cause future problems.
    return html_string


import pandas as pd
import sys
import io


def identify_groups_and_master(df):
    """
    Input: df where all users have the same name.
    Assigns each entry a duplicate_group number (finding unions by checking addres, email, phone, VerknupftesObjektID).
    """
    df.reset_index(inplace=True, drop=True)
    # if 'index' in df.columns:
    #     df.reset_index(inplace=True, drop=True)
    # else:
    #     print("Index column not found in DataFrame.")

    # Create a buffer to capture the printed output
    output_buffer = io.StringIO()

    # Keep the original stdout reference for restoration later
    original_stdout = sys.stdout

    # Redirect stdout to the buffer
    sys.stdout = output_buffer

    # Union-find utility functions
    def find(x, parent):
        # Find the root of x
        if parent[x] != x:
            parent[x] = find(parent[x], parent)
        return parent[x]

    def union(x, y, parent):
        # Union sets containing x and y
        rootX = find(x, parent)
        rootY = find(y, parent)
        if rootX != rootY:
            parent[rootY] = rootX

    # Apply the function to the 'UID_CHID' column
    df.replace("NotRegisteredCHID", pd.NA, inplace=True)

    # Initialize each row as its own group
    n = len(df)
    parent = [i for i in range(n)]

    columns_to_check = [
        "address_gmaps",
        "EMailAdresse",
        "Telefonnummer",
        "VerknuepftesObjektID",
    ]

    # Union rows that have matching values in ANY of the columns
    for column in ["address_gmaps", "EMailAdresse", "Telefonnummer"]:
        unique_vals = df[column].dropna().unique()  # Drop NaN values
        for val in unique_vals:
            indices = df[df[column] == val].index.tolist()
            for i in range(1, len(indices)):
                # Print statement to explain the merge
                print(
                    f"Rows {indices[0]} and {indices[i]} are being merged due to shared {column} value: {val}\n"
                )
                union(indices[0], indices[i], parent)

    # Special handling for 'VerknuepftesObjektID' column
    df["VerknuepftesObjektID"] = df["VerknuepftesObjektID"].apply(
        lambda x: [x] if isinstance(x, str) else x
    )
    all_object_ids = set(
        [
            item
            for sublist in df["VerknuepftesObjektID"].dropna()
            if isinstance(sublist, list)
            for item in sublist
        ]
    )
    for object_id in all_object_ids:
        indices = df[
            df["VerknuepftesObjektID"].apply(
                lambda x: object_id in x if isinstance(x, list) else False
            )
        ].index.tolist()
        for i in range(1, len(indices)):
            # Print statement to explain the merge
            print(
                f"Rows {indices[0]} and {indices[i]} are being merged due to shared objectID value: {object_id}\n"
            )
            union(indices[0], indices[i], parent)

    # Assign a unique group ID for each unique parent
    group_map = {}
    for i in range(n):
        root = find(i, parent)
        if root not in group_map:
            group_map[root] = len(group_map)
        df.at[i, "duplicate_group"] = group_map[root]

    # Assign scores and determine master
    df["Aktiv"] = (
        df["Aktiv"].fillna(0).astype(int)
    )  # TODO: should already be done in notebook
    # df['Aktiv'] = df['Aktiv'].astype(bool).astype(int)
    df["AnzahlGeschaeftsobjekte"] = df["AnzahlGeschaeftsobjekte"].fillna(0)
    df["Verknuepfungsart"] = df["Verknuepfungsart"].fillna(0)
    df["Versandart"] = df["Versandart"].fillna(0)
    df["AnzahlObjektZeiger"] = df["AnzahlObjektZeiger"].fillna(0)

    df["UID_CHID_check"] = df["UID_CHID"].apply(lambda x: x if not pd.isna(x) else 0)

    df["score"] = (
        df["Aktiv"].astype(int) * 1000
        + df["AnzahlGeschaeftsobjekte"].astype(int) * 100
        + df["UID_CHID_check"].astype(int) * 50
        + df["Verknuepfungsart"].isin(["Administrator", "Mitarbeiter"]).astype(int) * 50
        + df["Versandart"].isin(["Portal"]).astype(int) * 100
        + df["AnzahlObjektZeiger"].astype(int) * 10
    )
    master_indices = df.groupby("duplicate_group")["score"].idxmax()
    df["master"] = -1
    df.loc[master_indices, "master"] = df.loc[master_indices, "duplicate_group"]

    # Restore the original stdout
    sys.stdout = original_stdout

    # Get the captured output as a string
    captured_output = output_buffer.getvalue()

    return df, captured_output


def display_subset_of_df(df, columns_at_start=[], columns_at_end=[]):
    desired_order = [
        "Name",
        "score",
        "Aktiv",
        "CreatedAt",
        "Versandart",
        "UID_CHID",
        "ReferenceID",
        "address_full",
        "address_gmaps",
        "EMailAdresse",
        "Telefonnummer",
        "AnzahlObjektZeiger",
        "AnzahlVerknuepfungen",
        "VerknuepftesObjekt",
        "VerknuepftesObjektID",
        "Verknuepfungsart",
    ]
    desired_order = columns_at_start + desired_order + columns_at_end
    output_df = df[desired_order]

    # Use last 3 digits of ReferenceID as index
    output_df["index_column"] = df["ReferenceID"].str[-3:]
    output_df.set_index("index_column", inplace=True)

    # Remove duplicates based on ReferenceID
    output_df = output_df.drop_duplicates(subset="ReferenceID", keep="first")

    # Remove columns with all NaN values
    output_df = output_df.dropna(axis=1, how="all")

    # Remove columns with all empty lists
    columns_to_remove = []
    for col in output_df.columns:
        if all(pd.isnull(output_df[col])):
            columns_to_remove.append(col)
        elif all(isinstance(item, list) and len(item) == 0 for item in output_df[col]):
            columns_to_remove.append(col)
    output_df = output_df.drop(columns=columns_to_remove)

    return output_df




def calculate_scores_personen(df, physisch=False):
    # For Doubletten physisch, UID is not really important. We still consider it here but divided by 10.

    # Fill missing values for non-list columns
    df.fillna(
        {
            "AnzahlGeschaeftsobjekte": 0,
            "Versandart": 0,
            "AnzahlObjektZeiger": 0,
            "AnzahlVerknuepfungen": 0,
            "Servicerole_string": "",
        },
        inplace=True,
    )

    # UID_CHID_check calculation
    df["UID_CHID_check"] = df["UID_CHID"].apply(
        lambda x: 0
        if pd.isna(x) or x == ""
        else 1
        if str(x).lower() == "notregisteredchid"
        else 2
    )

    # Function to calculate score and score details
    def score_and_details(row):
        score_components = {
            "Geschaeftsobjekte": row["AnzahlGeschaeftsobjekte"] * 30,
            "UID": int(row["UID_CHID_check"] * 50 / (10 if physisch else 1)),
            "Verknuepfungsart": sum(
                100 if val == "Administrator" else 50 if val == "Mitarbeiter" else 0
                for val in (row["Verknuepfungsart_list"] or [])
            ),
            "Versandart": 100 if row["Versandart"] == "Portal" else 0,
            "ObjektZeiger": np.minimum(row["AnzahlObjektZeiger"] * 10, 100),
            "Geschaeftspartner": sum(
                100 for _ in (row["Geschaeftspartner_list"] or [])
            ),
            "Servicerole_string": 100 if "Ausweis" in row["Servicerole_string"] else 0,
            "Produktrolle": len(row["Produkt_rolle"]) * 100
            if row["Produkt_rolle"]
            else 0,
        }

        if row["EMailAdresse"] and not pd.isna(row["EMailAdresse"]):
            score_components["Email"] = 20

        if row["Telefonnummer"] and not pd.isna(row["Telefonnummer"]):
            score_components["Email"] = 10

        score_details = ", ".join(
            [f"{name} {score}" for name, score in score_components.items() if score > 0]
        )

        total_score = sum(score_components.values())

        return total_score, score_details

    # Apply the function to each row
    df[["score", "score_details"]] = df.apply(
        lambda row: score_and_details(row), axis=1, result_type="expand"
    )

    return df


def calculate_scores_organisationen(df):
    # new: requires serviceroles and produkte to be integrated.
    df["Debitornummer"] = df["Debitornummer"].fillna(0)
    df["Versandart"] = df["Versandart"].fillna(0)
    df["AnzahlGeschaeftsobjekte"] = df["AnzahlGeschaeftsobjekte"].fillna(0)
    df["AnzahlObjektZeiger"] = df["AnzahlObjektZeiger"].fillna(0)
    df["Debitornummer_check"] = df["Debitornummer"].apply(lambda x: 1 if x > 0 else 0)
    df["UID_CHID_check"] = df["UID_CHID"].apply(
        lambda x: 1 if isinstance(x, str) else 0
    )

    def calculate_score_and_details(row):
        score_components = {
            "Debitornummer": row["Debitornummer_check"] * 100,
            "UID_CHID": row["UID_CHID_check"] * 200,
            "Versandart": 100 if row["Versandart"] == "Portal" else 0,
            "Geschaeftsobjekte": row["AnzahlGeschaeftsobjekte"] * 30,
            "ObjektZeiger": min(row["AnzahlObjektZeiger"] * 10, 100),
            "Verknuepfungsart": sum(
                100 if val == "Administrator" else 50 if val == "Mitarbeiter" else 0
                for val in row["Verknuepfungsart_list"]
            ),
            "Geschaeftspartner": sum(100 for _ in row["Geschaeftspartner_list"]),
            "Produkt_Inhaber": min(row["Produkt_Inhaber"] * 80, 200),
            "Produkt_Adressant": min(row["Produkt_Adressant"] * 30, 100),
            "Servicerole": row["Servicerole_count"] * 50,
            "UID_MASTER": 1000 if row["UID_MASTER"] == True else 0
        }
        
        total_score = sum(score_components.values())
        score_details = ", ".join([f"{k}: {v}" for k, v in score_components.items() if v > 0])
        
        return total_score, score_details

    df["score"], df["score_details"] = zip(*df.apply(calculate_score_and_details, axis=1))
    
    return df


def get_geschaeftspartner(input_df, folder_path):
    """
    Check if input df has matching ReferenceID with any of the other dfs.
    df gets a new column "Geschaeftspartner" which contains a list of all matching partners.
    """
    # Create the "Geschaeftspartner" column in the input_df
    input_df["Geschaeftspartner"] = [[] for _ in range(len(input_df))]

    # List all xlsx files in the specified directory
    xlsx_files = glob.glob(f"{folder_path}/*.xlsx")

    # Helper function to check if a ReferenceID exists in any of the dfs and return its name(s)
    def check_reference(reference, df, partner_name):
        if reference in df["ReferenceID"].values:
            return [partner_name]
        return []

    # Load each xlsx file and check for a match with the ReferenceID in input_df
    for xlsx_file in xlsx_files:
        # Extract the partner name from the file name
        partner_name = (
            os.path.basename(xlsx_file)
            .rsplit("-", 1)[-1]
            .rsplit("_", 1)[-1]
            .split(".")[0]
        )

        # Load the dataframe
        df = pd.read_excel(xlsx_file)

        # Loop through each row in input_df and populate the "Geschaeftspartner" column
        for index, row in input_df.iterrows():
            partners = check_reference(row["ReferenceID"], df, partner_name)
            input_df.at[index, "Geschaeftspartner"].extend(partners)

    return input_df


#  ----- Functions related to app file upload ----
# -------------------------------
import streamlit as st
import fnmatch


def upload_files():
    uploaded_files = st.file_uploader(
        "Upload File", accept_multiple_files=True, type=["xlsx"]
    )

    if uploaded_files is not None and not st.session_state["clear_data"]:
        for uploaded_file in uploaded_files:
            # For backwards compatibility, put Geschaeftspartner files into appropriate subfolders.
            if fnmatch.fnmatch(
                uploaded_file.name, "*Geschaeftspartner*_Organisationen*.xlsx"
            ):
                relative_dir = "data/mandanten/organisationen"
            elif fnmatch.fnmatch(
                uploaded_file.name, "*Geschaeftspartner*_Personen*.xlsx"
            ):
                relative_dir = "data/mandanten/personen"
            else:
                relative_dir = "data"

            # Combine the stored cwd with the relative directory
            data_dir = os.path.join(st.session_state["cwd"], relative_dir)

            # Ensure the directory exists
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)

            # Define the full file path
            file_path = os.path.join(data_dir, uploaded_file.name)

            # Write the file to the specified location
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

        if len(uploaded_files) > 0:
            st.success(f"{len(uploaded_files)} files saved")


import shutil


def clear_data_directory(directory="data"):
    # Combine the stored cwd with the relative directory
    full_directory_path = os.path.join(st.session_state["cwd"], directory)

    # Check if the directory exists
    if os.path.exists(full_directory_path):
        # Remove all files in the directory
        for filename in os.listdir(full_directory_path):
            file_path = os.path.join(full_directory_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                st.error(f"Failed to delete {file_path}. Reason: {e}")
        st.success("Data directory cleared.")
        st.session_state["clear_data"] = True
    else:
        st.warning("Data directory does not exist.")


# ----------------- other app only related function -----
import re
from datetime import datetime


def get_data_version():
    """
    find_all_data() must have been executed somewhere before this.
    """
    
    # Check if 'file_paths' exists in the session state and is not empty
    if "file_paths" not in st.session_state or not st.session_state["file_paths"]:
        # Handle the empty or missing case
        return "No data", "No data", []

    filenames = st.session_state["file_paths"]
    date_pattern = r"\d{4}-\d{2}-\d{2}"

    dates = set()
    filenames_with_dates = []

    for key, value in filenames.items():
        match = re.search(date_pattern, value)
        filename_with_extension = os.path.basename(value)
        filename_without_extension = os.path.splitext(filename_with_extension)[0]

        if match:
            date_str = match.group()
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            dates.add(date_obj)
            # Add a tuple of (date_obj, filename_without_extension) to the list
            filenames_with_dates.append((date_obj, filename_without_extension))

    # Sort the list by dates
    filenames_with_dates.sort(key=lambda x: x[0])

    # Extract just the filenames in order
    ordered_filenames = [filename for date, filename in filenames_with_dates]

    # Find the earliest and latest date
    earliest_date = min(dates).strftime("%Y-%m-%d")
    latest_date = max(dates).strftime("%Y-%m-%d")

    # Store it in session state for later use
    st.session_state["file_versions"] = {}
    st.session_state["file_versions"]["earliest_date"] = earliest_date
    st.session_state["file_versions"]["latest_date"] = latest_date
    st.session_state["file_versions"]["ordered_filenames"] = ordered_filenames

    return earliest_date, latest_date, ordered_filenames
