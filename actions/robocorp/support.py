import os
from typing import Any, Dict, Tuple
from dotenv import load_dotenv
from pathlib import Path

import requests
from sema4ai.actions import Response, Secret, ActionError


load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")

def get_credentials(api_key: Secret, workspace_id: Secret) -> Tuple[str, str]:
    """
    Get API key and workspace ID from Secrets or environment variables.

    Args:
        api_key: The API key Secret object.
        workspace_id: The workspace ID Secret object.

    Returns:
        Tuple[str, str]: A tuple containing (api_key_value, workspace_id_value)

    Raises:
        ActionError: If either the API key or workspace ID is missing or empty.
    """
    api_key_value = api_key.value or os.getenv("API_KEY", "")
    ws_id = workspace_id.value or os.getenv("WORKSPACE_ID", "")

    if not api_key_value:
        raise ActionError("API key is required. Please provide it either through the Secret object or set the API_KEY environment variable.")
    
    if not ws_id:
        raise ActionError("Workspace ID is required. Please provide it either through the Secret object or set the WORKSPACE_ID environment variable.")

    return api_key_value, ws_id


def make_get_request(url: str, headers: dict) -> Response[Dict[str, Any]]:
    """
    Make a GET request and return the response as a dictionary.

    Args:
        url (str): The URL to send the GET request to.
        headers (dict): The headers to include in the request.

    Returns:
        Response[Dict[str, Any]]: The response wrapped in a Response object.

    Raises:
        ActionError: If the request fails.
    """
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return Response(result=response.json())


def make_post_request(url: str, headers: dict) -> Response[Dict[str, Any]]:
    """
    Make a POST request and return the response as a dictionary.

    Args:
        url (str): The URL to send the POST request to.
        headers (dict): The headers to include in the request.

    Returns:
        Response[Dict[str, Any]]: The response wrapped in a Response object.

    Raises:
        ActionError: If the request fails.
    """
    response = requests.post(url, headers=headers)
    response.raise_for_status()
    return Response(result=response.json())
