import os
import glob


def get_most_recent_file(directory, pattern):
    """
    Helper function to get the most recent file matching a specific pattern.
    Returns a tuple of the file path and an error message.
    """
    files = glob.glob(os.path.join(directory, pattern))
    files = [f for f in files if "hyperlinks" not in f and not f.endswith("Zone.Identifier")]
    files.sort(key=os.path.getmtime, reverse=True)

    if files:
        return files[0], False
    else:
        return None, f"File missing: {pattern}"


def detect_raw_files():
    """
    For app_processing.py
    Expects query excel outputs in data/
    Returns the most recent files of different types as specified.
    Concatenates error messages if multiple files are missing.
    """
    directory = "data/"

    # Dictionary to hold file patterns
    file_patterns = {
        "organisationen": "_EGov_Organisationen_Analyse*",
        "organisationsrollen": "_EGov_Organisationsrollenanalyse_MDG*",
        "organisationsrollenFDA": "_EGov_OrganisationsrollenanalyseFDA_MDG*",
        "organisationservicerolle": "_EGov_Organisationen_Servicerolle*",
        "personen": "_EGov_Personen_Analyse*",
        "personenservicerolle": "_EGov_Personen_Servicerolle*",
        "personenrollen": "_EGov_Personenrollenanalyse_MDG*"
    }

    # Initialize a list to collect error messages and a dict for the results
    error_messages = []
    result_files = {}

    # Loop through the dictionary to get the most recent files and collect errors
    for key, pattern in file_patterns.items():
        result, error = get_most_recent_file(directory, pattern=pattern)
        result_files[key] = result
        if error:
            error_messages.append(error)

    # Concatenate all error messages if any
    error_message = "; ".join(error_messages) if error_messages else False

    return result_files, error_message
