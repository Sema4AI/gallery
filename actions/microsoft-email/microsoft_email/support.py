import base64
import requests
from sema4ai.actions import ActionError

BASE_GRAPH_URL = "https://graph.microsoft.com/v1.0"


def build_headers(token):
    return {
        "Authorization": f"Bearer {token.access_token}",
        "Content-Type": "application/json",
    }


def send_request(
    method,
    url,
    req_name,
    headers=None,
    data=None,
    params=None,
):
    """
    Generalized request handler.

    :param method: HTTP method (e.g., 'get', 'post').
    :param url: URL for the request.
    :param headers: Optional headers for the request.
    :param data: Optional JSON data for 'post' requests.
    :param params: Optional query parameters for 'get' requests.
    :return: JSON response data if available.
    :raises: RequestException for any request failures.
    """
    try:
        response = requests.request(
            method, f"{BASE_GRAPH_URL}{url}", headers=headers, json=data, params=params
        )
        response.raise_for_status()  # Raises a HTTPError for bad responses
        if response.status_code not in [200, 201, 202, 204]:
            raise ActionError(f"Error on '{req_name}': {response.text}")
        # Check if the response has JSON content
        if "application/json" in response.headers.get("Content-Type", ""):
            return response.json()
        return None
    except Exception as e:
        raise ActionError(f"Error on '{req_name}': {str(e)}")


def _read_file(attachment):
    file_content = ""
    with open(attachment.filepath, "rb") as file:
        file_content = file.read()
    return base64.b64encode(file_content).decode("utf-8")


def _base64_attachment(attachment):
    c_bytes = (
        attachment.content_bytes
        if attachment.filepath == ""
        else _read_file(attachment)
    )
    data = {
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": attachment.name if len(attachment.name) > 0 else "SOMETHING",
        "contentBytes": c_bytes,
    }
    return data
