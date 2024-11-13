import os



# Ensure these constants are defined
ACTIONS_DIR = "actions"
GALLERY = "gallery"
MY_ACTIONS_DIR = "MyActions"
WORKSPACE_HOME_DIR = "payment-remittance-reconcile-action"

def get_full_path(relative_path):
    """
    Constructs the full path for a given relative path based on the current environment.

    If the current directory contains 'actions' or 'gallery', it assumes the environment is an action package.
    Otherwise, it constructs the path assuming a production environment.

    Args:
        relative_path (str): The relative path to be converted to a full path.

    Returns:
        str: The full path as a string.

    Examples:
        >>> get_full_path("reconciliation_ledger_db/ddl/reconciliation_ledger.ddl")
        '/current/working/directory/actions/MyActions/payment-reconciliation-action/reconciliation_ledger_db/ddl/reconciliation_ledger.ddl'

        >>> get_full_path("reconciliation_ledger_db/invoice_data/1_FirstRate.sql")
        '/current/working/directory/actions/MyActions/payment-reconciliation-action/reconciliation_ledger_db/invoice_data/1_FirstRate.sql'
    """
    current_dir = os.getcwd()

    if ACTIONS_DIR in current_dir or GALLERY in current_dir:
        # Opened as action package
        complete_path = relative_path
    else:
        # Opened as a different environment, perhaps production
        complete_path = os.path.join(current_dir, ACTIONS_DIR, MY_ACTIONS_DIR, WORKSPACE_HOME_DIR, relative_path)
    
    return complete_path