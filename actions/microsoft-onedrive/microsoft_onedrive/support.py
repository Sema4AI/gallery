from typing import Dict, List

import sema4ai_http
from microsoft_onedrive.models import ItemType
from sema4ai.actions import ActionError

BASE_GRAPH_URL = "https://graph.microsoft.com/v1.0"


def build_headers(token):
    return {
        "Authorization": f"Bearer {token.access_token}",
        "Content-Type": "application/json",
    }


def send_request(
    method, url, req_name, headers=None, json=None, params=None, data=None
):
    """
    Generalized request handler.

    :param method: HTTP method (e.g., 'get', 'post').
    :param url: URL for the request.
    :param headers: Optional headers for the request.
    :param json: Optional JSON data for 'post' requests.
    :param data: Optional data for 'post' requests.
    :param params: Optional query parameters for 'get' requests.
    :return: JSON response data if available.
    :raises: RequestException for any request failures.
    """
    try:
        query_url = url if url.startswith("http") else f"{BASE_GRAPH_URL}{url}"
        response = getattr(sema4ai_http, method.lower())(
            query_url, headers=headers, json=json, fields=params, body=data
        )
        response.raise_for_status()  # Raises a HTTPError for bad responses
        if response.status_code not in [200, 201, 202, 204]:
            raise ActionError(f"Error on '{req_name}': {response.text}")
        # Check if the response has JSON content
        if "application/json" in response.headers.get("Content-Type", ""):
            return response.json()
        else:
            return response.data
    except Exception as e:
        raise ActionError(f"Error on '{req_name}': {str(e)}")


def parse_onedrive_items(response_data: dict, item_type: ItemType) -> List[dict]:
    """
    Parse the OneDrive items response to extract relevant details based on the specified item type.

    Args:
        response_data: The full JSON response from the Microsoft Graph API.
        item_type: The type of items to include in the result.

    Returns:
        A list of parsed item information with key details.
    """
    parsed_items = []

    for item in response_data.get("value", []):
        is_folder = "folder" in item

        if (
            (item_type == ItemType.files and not is_folder)
            or (item_type == ItemType.folders and is_folder)
            or (item_type == ItemType.all)
        ):
            parsed_item = {
                "id": item.get("id"),
                "name": item.get("name"),
                "size": item.get("size"),
                "webUrl": item.get("webUrl"),
                "downloadUrl": item.get("@microsoft.graph.downloadUrl"),
                "createdDateTime": item.get("createdDateTime"),
                "lastModifiedDateTime": item.get("lastModifiedDateTime"),
                "createdBy": item.get("createdBy", {})
                .get("user", {})
                .get("displayName"),
                "lastModifiedBy": item.get("lastModifiedBy", {})
                .get("user", {})
                .get("displayName"),
                "mimeType": item.get("file", {}).get("mimeType"),
                "isFolder": is_folder,
            }
            parsed_items.append(parsed_item)

    return parsed_items


def get_folders_recursively(url: str, headers: dict) -> List[Dict[str, str]]:
    folders = []
    while url:
        data = send_request("get", url, "get folders", headers=headers)
        for item in data.get("value", []):
            if item.get("folder"):
                folder_path = (
                    item["parentReference"].get("path", "") + "/" + item["name"]
                )
                folder_info = {"path": folder_path, "id": item["id"]}
                folders.append(folder_info)
                child_url = f"/me/drive/items/{item['id']}/children"
                folders.extend(get_folders_recursively(child_url, headers))

        url = data.get("@odata.nextLink")
    return folders
