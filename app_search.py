import streamlit as st
import pickle
import time
import pandas as pd
# import pyperclip
import os

# def success_temporary(text):
#     # Placeholder for the success message
#     placeholder = st.empty()
#     # Show the success message
#     placeholder.success(text, icon="✅")
#     # Wait for a few seconds
#     time.sleep(5)  # Adjust the number of seconds here
#     # Clear the message
#     placeholder.empty()
    
    
def success_temporary(text):
    # Previous version with sleep might interfere with st run-cycle. this checks time after next re-run (user interaction.)
    # Initialize a key in the session state to track the display time if it doesn't already exist
    if 'display_time' not in st.session_state or st.session_state.display_time is None:
        # Placeholder for the success message
        placeholder = st.empty()
        # Show the success message
        placeholder.success(text, icon="✅")
        # Record the current time as the start time for the message display
        st.session_state.display_time = time.time()
    else:
        # Check if 5 seconds have passed since the message was displayed
        if time.time() - st.session_state.display_time > 5:
            # Clear the message
            st.session_state.display_time = None  # Reset the display time
            # This line is only necessary if you are reusing the same placeholder for other content
            st.empty()


@st.cache_data
def load_data():
    try:
        file_path = os.path.join(st.session_state["cwd"], "data/calculated/personen_organisationen_dfs_processed.pickle")
        print("opening: ", file_path)
        with open(
            file_path, "rb"
        ) as file:
            data_dfs = pickle.load(file)
        return data_dfs
    except Exception as e:
        st.error(f"No data found or error in loading data: {e}", icon="🚨")


def search_names(search_name, data_dfs):
    if not search_name.strip():
        # with empty input return two empty dataframes.
        return pd.DataFrame(columns=["Name", "ReferenceID"]), pd.DataFrame(
            columns=["Name", "ReferenceID"]
        )

    df_personen = data_dfs["personen"]
    df_organisationen = data_dfs["organisationen"]

    search_words = set(search_name.lower().split())

    def match(row):
        name_words = set(row.lower().split())
        return search_words.issubset(name_words)

    match_personen = df_personen["Name"].apply(match)
    match_organisationen = df_organisationen["Name"].apply(match)

    personen_matches = df_personen[match_personen][["Name", "Objekt_link", "ReferenceID"]]
    # personen_matches["Copy"] = False
    organisationen_matches = df_organisationen[match_organisationen][
        ["Name", "Objekt_link", "ReferenceID"]
    ]
    # organisationen_matches["Copy"] = False
    
    # st.write(df_personen.columns)
    # st.write(st.session_state)

    return personen_matches, organisationen_matches


def show():
    data_dfs = load_data()

    search_name = st.text_input("Name of Person or Organisation")

    # global personen_matches
    personen_matches, organisationen_matches = search_names(search_name, data_dfs)

    col1, col2 = st.columns(2)
    
    with col1:
        if not personen_matches.empty:
            st.subheader("Personen matches")
            # personen_matches = st.data_editor(personen_matches.reset_index(drop=True))
            st.write(personen_matches.to_dict('records'))
        # for index, row in personen_matches.iterrows():
        #     if row['Copy']:
        #         # Copy ReferenceID to clipboard
        #         pyperclip.copy(row['ReferenceID'])
        #         st.write(f"Copied {row['ReferenceID']} to clipboard")
        #         # Reset the flag to False after copying
        #         personen_matches.at[index, 'Copy'] = False

    with col2:
        if not organisationen_matches.empty:
            st.subheader("Organisationen matches")
            # organisationen_matches = st.data_editor(organisationen_matches.reset_index(drop=True))
            st.write(organisationen_matches.to_dict('records'))
        # for index, row in organisationen_matches.iterrows():
        #     if row['Copy']:
        #         # Copy ReferenceID to clipboard
        #         pyperclip.copy(row['ReferenceID'])
        #         # Reset the flag to False after copying
        #         personen_matches.at[index, 'Copy'] = False
