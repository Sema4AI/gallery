from typing import List, Literal
from pathlib import Path

from sema4ai.actions import ActionError, OAuth2Secret, Response, action

from microsoft_onedrive.models import (
    GetOneDriveItemByIdParams,
    OneDriveListingParams,
    OneDriveSearchItemsRequest,
    DownloadRequest,
)
from microsoft_onedrive.support import (
    build_headers,
    get_folders_recursively,
    parse_onedrive_items,
    send_request,
)


@action
def get_onedrive_item_by_id(
    token: OAuth2Secret[
        Literal["microsoft"],
        List[Literal["Files.Read"]],
    ],
    params: GetOneDriveItemByIdParams,
) -> Response[dict]:
    """Retrieve detailed information about a file or folder in OneDrive using its ID.
    Useful also to find parent folders.

    Args:
        token: OAuth2 token with Files.Read permission.
        params: Pydantic model containing the item_id parameter.

    Returns:
        Dictionary with detailed information about the requested item.
    """
    headers = build_headers(token)
    url = f"/me/drive/items/{params.item_id}"

    item_data = send_request("get", url, "retrieve item", headers=headers)

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


@action
def list_all_onedrive_folders_recursively(
    token: OAuth2Secret[
        Literal["microsoft"],
        List[Literal["Files.Read"]],
    ],
    root_folder: str = "/",
) -> Response[dict]:
    """Recursively list all folders in OneDrive starting from a specified root folder.

    Args:
        token: OAuth2 token.
        root_folder: The root folder to start listing folders from. Use "/" for the root of OneDrive.

    Returns:
        Dictionary with a 'folders' key mapping to a list of dictionaries,
        each containing 'path' and 'id' for a folder.
    """
    headers = build_headers(token)

    if root_folder in ["/", "root", "home"]:
        url = "/me/drive/root/children"
    else:
        folder_path = root_folder.strip("/")
        url = f"/me/drive/root:/{folder_path}:/children"

    all_folders = get_folders_recursively(url, headers)
    return Response(result={"folders": all_folders})


@action
def list_items_from_onedrive_folder(
    token: OAuth2Secret[
        Literal["microsoft"],
        List[Literal["Files.Read"]],
    ],
    params: OneDriveListingParams,
) -> Response[dict]:
    """List items in a specified OneDrive folder. Use "/" for the root folder, "/Documents", etc.
    Returns also download urls (note that it's slow to print).

    Args:
        token: OAuth2 token.
        params: Pydantic model containing folder_path and item_type.

    Returns:
        Dictionary with an 'items' key mapping to a list of item details.
    """
    headers = build_headers(token)

    if params.folder_path in ["/", "root", "home"]:
        url = "/me/drive/root/children"
    else:
        folder_path = params.folder_path.lstrip("/")
        url = f"/me/drive/root:/{folder_path}:/children"

    items = send_request("get", url, "list items", headers=headers)
    parsed_items = parse_onedrive_items(items, params.item_type)
    return Response(result={"items": parsed_items})


@action
def list_onedrive_items_shared_with_me(
    token: OAuth2Secret[
        Literal["microsoft"],
        List[Literal["Files.Read.All"]],
    ],
) -> Response[dict]:
    """List items shared with me in OneDrive.

    Args:
        token: OAuth2 token to use for the operation.

    Returns:
        Response containing a dictionary with an 'items' key mapping to a list of shared item details.
    """
    headers = build_headers(token)
    url = "/me/drive/sharedWithMe"
    items = send_request("get", url, "list shared items", headers=headers)
    return Response(result={"items": items.get("value", [])})


@action
def search_for_onedrive_items(
    token: OAuth2Secret[
        Literal["microsoft"],
        List[Literal["Files.Read.All"]],
    ],
    search_request: OneDriveSearchItemsRequest,
) -> Response[dict]:
    """Search for items ("all" ,"files" or "folders") in OneDrive by name or content.

    Args:
        token: OAuth2 token to use for the operation.
        search_request: OneDriveSearchItemsRequest containing the search query and item type.

    Returns:
        Response containing a list of items matching the search query and type, including download URLs for files.
    """
    headers = build_headers(token)
    url = f"/me/drive/root/search(q='{search_request.query}')"

    response_json = send_request("get", url, "search items", headers=headers)
    all_items = response_json.get("value", [])

    if search_request.item_type == "file":
        filtered_items = [item for item in all_items if "file" in item]
    elif search_request.item_type == "folder":
        filtered_items = [item for item in all_items if "folder" in item]
    else:
        filtered_items = all_items

    for item in filtered_items:
        if "file" in item:
            item_id = item["id"]
            download_url = f"/me/drive/items/{item_id}"
            download_info = send_request(
                "get", download_url, "get download URL", headers=headers
            )
            item["download_url"] = download_info.get(
                "@microsoft.graph.downloadUrl", None
            )
        else:
            item["download_url"] = None

    return Response(result={"items": filtered_items})


@action
def download_onedrive_file(
    token: OAuth2Secret[
        Literal["microsoft"],
        List[Literal["Files.Read.All"]],
    ],
    download_request: DownloadRequest,
    download_location: str = "",
    download_all: bool = False,
) -> Response[str]:
    """Download file or files from OneDrive to local storage.

    Do not give 'download_location' unless user specifies a path.
    By default downloads to the user's Downloads folder.

    Args:
        token: OAuth2 token to use for the operation.
        download_request: The download request containing the search query or download URL.
        download_location:  The path (folder) to save the downloaded file.
        download_all: Whether to download all files found or not.

    Returns:
        Response with a message indicating the number of files downloaded.
    """
    headers = build_headers(token)
    download_location = (
        Path.home() / "Downloads"
        if download_location == ""
        else Path(download_location)
    )
    if download_request.download_url and download_request.name:
        matching_files = [
            {
                "name": download_request.name,
                "download_url": download_request.download_url,
            }
        ]
    elif download_request.search_items_request:
        response = search_for_onedrive_items(
            token,
            download_request.search_items_request,
        )
        matching_files = response.result.get("items", [])
        if len(matching_files) == 0:
            raise ActionError("No files found matching the search query.")
        elif not download_all and len(matching_files) > 1:
            raise ActionError(
                "Multiple files found matching the search query. Set download_all to True to download all files."
            )
    else:
        raise ActionError("Either query or download_url, name must be provided.")
    download_count = 0
    for file in matching_files:
        download_url = file.get("download_url")
        if download_url:
            file_name = file.get("name")
            download_content = send_request(
                "get", download_url, "download file", headers=headers
            )
            if download_content:
                with open(f"{download_location}/{file_name}", "wb") as f:
                    f.write(download_content)
                download_count += 1
            else:
                raise ActionError("Failed to download file")
        else:
            raise ActionError(f"No download URL available for file: {file.get('name')}")
    return Response(
        result=f"{download_count} file(s) downloaded successfully to {download_location}."
    )


@action
def get_my_drive(
    token: OAuth2Secret[
        Literal["microsoft"],
        List[Literal["Files.Read"]],
    ]
) -> Response[dict]:
    """Get my drive details.

    Args:
        token: OAuth2 token to use for the operation.
    Returns:
        Response with the result of the operation.
    """
    result = send_request(
        "get", "/me/drive", "get my drive", headers=build_headers(token)
    )
    return Response(result=result)
