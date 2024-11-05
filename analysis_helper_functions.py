import pandas as pd


def find_name_adresse_doubletten(df, organisationen=True, abbreviated_first_name=False, only_with_Geschaeftspartner=False):
    """
    A cluster here is just any group of organizations with exact match in Name and Adresse (email irrelevant). Used for Doubletten analyses.
    """
    # Group by 'Name' and 'address_full', and assign cluster_id
    if organisationen:
        df['cluster_id'] = df.groupby(['Name_Zeile2', 'address_full']).ngroup()
    else:
        if abbreviated_first_name:
            df["Name_abbrev"] = df["Name"].apply(abbreviate_first_name)
            df['cluster_id'] = df.groupby(['Name_abbrev', 'address_full']).ngroup()
        else:
            df['cluster_id'] = df.groupby(['Name', 'address_full']).ngroup()

    # Keep only groups with at least 2 identical rows
    df = df[df.groupby('cluster_id')['cluster_id'].transform('size') > 1]
    
    # If only_with_Geschaeftspartner is True, filter clusters
    if only_with_Geschaeftspartner:
        df = df[df.groupby('cluster_id')['Geschaeftspartner_list'].transform(lambda x: x.str.len().max() > 0)]

    if organisationen:
        df.sort_values(by='Name_Zeile2', inplace=True)
    else:
        df.sort_values(by='Name', inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df


def filter_clusters_with_mixed_produkt_roles(
    df, no_Geschaeftspartner=True, no_Servicerole=True
):
    """
    Für DB cleanup step 2, nachdem alle Produktrollen auf einen Master übertragen wurden.
    Findet Doubletten, bei denen eine Inhaber+Adressant ist (sollte nur noch eine  =Master sein), die anderen Doubletten habe keinerlei Rollen mehr.
    Achtung: Cluster kann weitere Doubletten enthalten, die noch Rollen haben (z.B. nur Rechnungsempfänger), diese werden nicht angezeigt.
    """
    # Apply initial filters to remove entries based on no_Geschaeftspartner and no_Servicerole
    if no_Geschaeftspartner:
        df = df[~df["Geschaeftspartner_list"].apply(lambda gp: len(gp) != 0)]
    if no_Servicerole:
        df = df[df["Servicerole_count"] == 0]

    def filter_relevant_members(group):
        # Identify members with both roles > 0
        has_both_roles = group[
            (group["Produkt_Inhaber"] > 0) & (group["Produkt_Adressant"] > 0)
        ]
        # Identify members with both roles == 0
        has_zero_roles = group[
            (group["Produkt_Inhaber"] == 0) & (group["Produkt_Adressant"] == 0)
        ]
        # Return relevant members if criteria are met
        if len(has_both_roles) == 1 and len(has_zero_roles) >= 1:
            return pd.concat([has_both_roles, has_zero_roles])
        return pd.DataFrame()

    # Apply the group filter and ensure each group has at least two members
    filtered_df = df.groupby("cluster_id").apply(filter_relevant_members).reset_index(drop=True)
    filtered_df = filtered_df[filtered_df.groupby("cluster_id")["cluster_id"].transform("size") >= 2]

    return filtered_df



## CLEANUP / STYLING FUNCTIONS

from openpyxl import load_workbook
from openpyxl.styles import PatternFill
def apply_excel_styling_organisationen_nur_master_hat_produkte(file_path, sheet_name='Sheet1'):
    # Load the workbook and select the sheet
    wb = load_workbook(file_path)
    ws = wb[sheet_name]

    # Define the tomato fill using the RGB part of the color code
    tomato_fill = PatternFill(start_color="FF6347", end_color="FF6347", fill_type="solid")

    # Find the column indices for 'master', 'Produkt_Inhaber', and 'Produkt_Adressant'
    header = {cell.value: idx for idx, cell in enumerate(ws[1])}
    master_col = header.get('master')
    produkt_inhaber_col = header.get('Produkt_Inhaber')
    produkt_adressant_col = header.get('Produkt_Adressant')

    if master_col is None or produkt_inhaber_col is None or produkt_adressant_col is None:
        print("Header values:", [cell.value for cell in ws[1]])
        raise ValueError("One or more required columns are missing in the Excel file.")

    # Iterate over the rows and apply the tomato fill where necessary
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        if (row[master_col].value == 'X' and 
            row[produkt_inhaber_col].value == 0 and 
            row[produkt_adressant_col].value == 0):
            for cell in row:
                cell.fill = tomato_fill

    # Save the workbook
    wb.save(file_path)


def set_master_flag(df):
    if "cluster_id" not in df.columns:
        raise ValueError("DataFrame does not contain 'cluster_id' column.")

    # Create a copy to avoid modifying the original DataFrame
    result_df = df.copy()

    # Sort by 'score' and 'CreatedAt' in descending order for processing
    sorted_df = result_df.sort_values(by=["score", "CreatedAt"], ascending=[False, False])

    # Group by 'cluster_id' and mark the first row in each group as 'X' and others as ''
    sorted_df["master"] = sorted_df.groupby("cluster_id").cumcount().map({0: "X"}).fillna("")

    # Handle the case where all rows have the same 'cluster_id'
    if sorted_df["master"].eq("").all():
        sorted_df["master"].iloc[0] = "X"  # Mark the first row as 'master'

    # Assign the 'master' column directly to the original DataFrame
    result_df["master"] = sorted_df["master"]
    
    # Create the 'master_ID' column
    master_ids = sorted_df[sorted_df["master"] == "X"].set_index("cluster_id")["ReferenceID"]
    result_df["masterID"] = result_df["cluster_id"].map(master_ids)

    return result_df

def renumber_and_sort_alphanumeric(df, column='cluster_id'):    # Split the column into two
    # Split the column into two
    df['num'] = df[column].str.split('_').str[0]
    df['alpha'] = df[column].str.split('_').str[1]
    df['num'] = df['num'].astype(int)

    # Sort the dataframe
    df.sort_values(['num', 'alpha'], inplace=True)

    # Create a new column with rank
    df['rank'] = df['num'].rank(method='dense').astype(int)

    # Combine 'rank' and 'alpha' to get the desired format
    df[column] = df['rank'].astype(str) + '_' + df['alpha']

    # Drop the temporary columns
    df.drop(['num', 'alpha', 'rank'], axis=1, inplace=True)

    return df

def renumber_pairs(column):
    # To recognize clusters I have a continous cluster-id, e.g. 1,1,2,2,3,3, but due to filtering there are some gaps, 1,1,3,3, ...
    # this will just renumber it to 1,1,2,2
    # numbers dont even have to be in ascending order, e.g. if i sorted dataframe by name before and cluster_ids become 3,3,1,1,2,2
    # will just respect the order of appearance and re-number starting with 1.
    mapping = {}
    new_id = 1

    for val in column:
        if val not in mapping:
            mapping[val] = new_id
            new_id += 1

    new_values = [mapping[val] for val in column]
    return new_values

def filter_verknuepfungen(row):
    """
    For Organisations-analyses we only want to show Verknüpfungen to Personen. 
    This filters out anything from the list that is not 'Mitarbeiter' or 'Administrator'
    """
    filtered_indices = [i for i, x in enumerate(row['Verknuepfungsart_list']) if x in ['Mitarbeiter', 'Administrator']]
    row['Verknuepfungsart_list'] = [row['Verknuepfungsart_list'][i] for i in filtered_indices]
    row['VerknuepftesObjektID_list'] = [row['VerknuepftesObjektID_list'][i] for i in filtered_indices]
    row['VerknuepftesObjekt_list'] = [row['VerknuepftesObjekt_list'][i] for i in filtered_indices]
    return row
    
def final_touch(df, cols_to_keep, two_roles=False, alphanumeric=False):
    """
    For a single dataframe. 
    newer analyses have alphanumeric cluster_ids (1_a, 1_b, 2_a, etc.), so we need to sort them differently.
    """
    if "cluster_id" not in df.columns:
        raise ValueError("DataFrame does not contain 'cluster_id' column.")
    
    df = df.apply(filter_verknuepfungen, axis=1)
    df = set_master_flag(df)
    df = df[cols_to_keep]
    df["score"] = df["score"].astype(int)
    
    if two_roles or alphanumeric:
        df = renumber_and_sort_alphanumeric(df.copy(), column='cluster_id')
    else:
        df["cluster_id"] = df["cluster_id"].astype(int)
        df["cluster_id"] = renumber_pairs(df["cluster_id"])
        df.sort_values(by="cluster_id", inplace=True)
        
    df.reset_index(drop=True, inplace=True)
    return df