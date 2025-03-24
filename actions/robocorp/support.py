import os
from typing import Any, Dict, Tuple

import requests
from sema4ai.actions import ActionError, Response, Secret


def get_credentials(api_key: Secret, workspace_id: Secret) -> Tuple[str, str]:
    """
    Get API key and workspace ID from Secrets or environment variables.

    Args:
        api_key: The API key Secret object.
        workspace_id: The workspace ID Secret object.

    Returns:
        Tuple[str, str]: A tuple containing (api_key_value, workspace_id_value)
    """
    api_key_value = api_key.value or os.getenv("API_KEY", "")
    ws_id = workspace_id.value or os.getenv("WORKSPACE_ID", "")
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

    if response.status_code in [200, 201]:
        return Response(result=response.json())
    else:
        raise ActionError(f"Failed to retrieve data: {response.text}")


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

    if response.status_code in [200, 201]:
        return Response(result=response.json())
    else:
        raise ActionError(f"Failed to make POST request: {response.text}")
