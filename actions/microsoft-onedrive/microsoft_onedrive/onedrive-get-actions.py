from typing import List, Literal

import requests
from sema4ai.actions import ActionError, OAuth2Secret, Response, action

from microsoft_onedrive.models import (
    GetOneDriveItemByIdParams,
    OneDriveListingParams,
    OneDriveSearchItemsRequest,
    RecursiveOneDriveFoldersParams,
)
from microsoft_onedrive.support import (
    BASE_GRAPH_URL,
    build_headers,
    get_folders_recursively,
    parse_onedrive_items,
)


@action
def get_onedrive_item_by_id(
    token: OAuth2Secret[
        Literal["microsoft"],
        List[Literal["Files.Read"]],
    ],
    params: GetOneDriveItemByIdParams,
) -> Response[dict]:
    """
    Retrieve detailed information about a file or folder in OneDrive using its ID. Useful also to find parent folders.

    Args:
        token: OAuth2 token with Files.Read permission.
        params: Pydantic model containing the item_id parameter.

    Returns:
        Dictionary with detailed information about the requested item.
    """
    headers = build_headers(token)
    url = f"{BASE_GRAPH_URL}/me/drive/items/{params.item_id}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        item_data = response.json()

        result = {
            "id": item_data.get("id"),
            "name": item_data.get("name"),
            "type": "folder" if "folder" in item_data else "file",
            "size": item_data.get("size"),
            "created_datetime": item_data.get("createdDateTime"),
            "last_modified_datetime": item_data.get("lastModifiedDateTime"),
            "web_url": item_data.get("webUrl"),
        }

        if "folder" in item_data:
            result["child_count"] = item_data["folder"].get("childCount")
        elif "file" in item_data:
            result["mime_type"] = item_data["file"].get("mimeType")

        if "parentReference" in item_data:
            result["parent_folder"] = {
                "id": item_data["parentReference"].get("id"),
                "path": item_data["parentReference"].get("path"),
            }

        return Response(result=result)

    except requests.HTTPError as e:
        status_code = e.response.status_code
        if status_code == 400:
            raise ActionError(
                f"Bad request. The item ID '{params.item_id}' might be invalid."
            )
        elif status_code == 401:
            raise ActionError("Unauthorized. Please check your authentication token.")
        elif status_code == 403:
            raise ActionError(
                "Access forbidden. You may not have permission to access this item."
            )
        elif status_code == 404:
            raise ActionError(f"Item not found: {params.item_id}")
        else:
            raise ActionError(f"Failed to retrieve OneDrive item: HTTP {status_code}")
    except requests.RequestException as e:
        raise ActionError(f"Network error while retrieving OneDrive item: {str(e)}")
    except Exception as e:
        raise ActionError(f"Unexpected error while retrieving OneDrive item: {str(e)}")


@action
def list_all_onedrive_folders_recursively(
    token: OAuth2Secret[
        Literal["microsoft"],
        List[Literal["Files.Read"]],
    ],
    params: RecursiveOneDriveFoldersParams,
) -> Response[dict]:
    """
    Recursively list all folders in OneDrive starting from a specified root folder.

    Args:
        token: OAuth2 token.
        params: Pydantic model containing the root_folder parameter.

    Returns:
        Dictionary with a 'folders' key mapping to a list of dictionaries,
        each containing 'path' and 'id' for a folder.
    """
    headers = build_headers(token)

    if params.root_folder in ["/", "root", "home"]:
        url = f"{BASE_GRAPH_URL}/me/drive/root/children"
    else:
        folder_path = params.root_folder.strip("/")
        url = f"{BASE_GRAPH_URL}/me/drive/root:/{folder_path}:/children"

    try:
        all_folders = get_folders_recursively(url, headers)
        return Response(result={"folders": all_folders})
    except requests.HTTPError as e:
        status_code = e.response.status_code
        if status_code == 400:
            raise ActionError(
                f"Bad request. The folder path '{params.root_folder}' might be invalid."
            )
        elif status_code == 401:
            raise ActionError("Unauthorized. Please check your authentication token.")
        elif status_code == 403:
            raise ActionError(
                "Access forbidden. You may not have permission to access this folder."
            )
        elif status_code == 404:
            raise ActionError(f"Folder not found: {params.root_folder}")
        else:
            raise ActionError(f"Failed to list OneDrive folders: HTTP {status_code}")
    except requests.RequestException as e:
        raise ActionError(f"Network error while listing OneDrive folders: {str(e)}")
    except Exception as e:
        raise ActionError(f"Unexpected error while listing OneDrive folders: {str(e)}")


@action
def list_items_from_onedrive_folder(
    token: OAuth2Secret[
        Literal["microsoft"],
        List[Literal["Files.Read"]],
    ],
    params: OneDriveListingParams,
) -> Response[dict]:
    """
    List items in a specified OneDrive folder. Use "/" for the root folder, "/Documents", etc. Returns also download urls (note that it's slow to print).

    Args:
        token: OAuth2 token.
        params: Pydantic model containing folder_path and item_type.

    Returns:
        Dictionary with an 'items' key mapping to a list of item details.
    """
    headers = build_headers(token)

    if params.folder_path in ["/", "root", "home"]:
        url = f"{BASE_GRAPH_URL}/me/drive/root/children"
    else:
        folder_path = params.folder_path.lstrip("/")
        url = f"{BASE_GRAPH_URL}/me/drive/root:/{folder_path}:/children"

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        parsed_items = parse_onedrive_items(response.json(), params.item_type)
        return Response(result={"items": parsed_items})
    else:
        raise ActionError(f"Failed to list OneDrive items: {response.text}")


@action
def list_onedrive_items_shared_with_me(
    token: OAuth2Secret[
        Literal["microsoft"],
        List[Literal["Files.Read.All"]],
    ],
) -> Response[dict]:
    """
    List items shared with me in OneDrive.

    Args:
        token: OAuth2 token to use for the operation.

    Returns:
        Response containing a dictionary with an 'items' key mapping to a list of shared item details.
    """
    headers = build_headers(token)
    url = f"{BASE_GRAPH_URL}/me/drive/sharedWithMe"

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        items = response.json().get("value", [])
        return Response(result={"items": items})
    else:
        raise ActionError(f"Failed to list shared OneDrive items: {response.text}")


@action
def search_for_onedrive_items(
    token: OAuth2Secret[
        Literal["microsoft"],
        List[Literal["Files.Read.All"]],
    ],
    search_request: OneDriveSearchItemsRequest,
) -> Response[dict]:
    """
    Search for items ("all" ,"files" or "folders") in OneDrive by name or content.

    Args:
        token: OAuth2 token to use for the operation.
        search_request: OneDriveSearchItemsRequest containing the search query and item type.

    Returns:
        Response containing a list of items matching the search query and type, including download URLs for files.
    """
    headers = build_headers(token)
    url = f"{BASE_GRAPH_URL}/me/drive/root/search(q='{search_request.query}')"

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        all_items = response.json().get("value", [])

        if search_request.item_type == "file":
            filtered_items = [item for item in all_items if "file" in item]
        elif search_request.item_type == "folder":
            filtered_items = [item for item in all_items if "folder" in item]
        else:
            filtered_items = all_items

        for item in filtered_items:
            if "file" in item:
                item_id = item["id"]
                download_url = f"{BASE_GRAPH_URL}/me/drive/items/{item_id}"
                download_response = requests.get(download_url, headers=headers)

                if download_response.status_code == 200:
                    download_info = download_response.json()
                    item["download_url"] = download_info.get(
                        "@microsoft.graph.downloadUrl"
                    )
                else:
                    item["download_url"] = None
            else:
                item["download_url"] = None

        return Response(result={"items": filtered_items})
    else:
        raise ActionError(f"Failed to search items: {response.text}")
