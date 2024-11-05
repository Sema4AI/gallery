import os


def get_full_path(relative_path):
    """
    For Action executions the workingdir should always point to the action package root so this method just joins the cwd and the relative dir and returns the absolute path.
    Args:
        relative_path (str): The relative path to be converted to a full path.

    Returns:
        str: The full path as a string.
    """
    return os.path.abspath(os.path.join(os.getcwd(), relative_path))
