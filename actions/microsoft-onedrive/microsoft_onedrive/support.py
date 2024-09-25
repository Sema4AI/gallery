from typing import Dict, List

import requests

from microsoft_onedrive.models import ItemType

BASE_GRAPH_URL = "https://graph.microsoft.com/v1.0"


def build_headers(token):
    return {
        "Authorization": f"Bearer {token.access_token}",
        "Content-Type": "application/json",
    }


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
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        data = response.json()
        for item in data.get("value", []):
            if item.get("folder"):
                folder_path = (
                    item["parentReference"].get("path", "") + "/" + item["name"]
                )
                folder_info = {"path": folder_path, "id": item["id"]}
                folders.append(folder_info)
                child_url = f"{BASE_GRAPH_URL}/me/drive/items/{item['id']}/children"
                folders.extend(get_folders_recursively(child_url, headers))

        url = data.get("@odata.nextLink")
    return folders
