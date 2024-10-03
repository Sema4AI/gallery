import os
from pathlib import Path
from typing import List, Literal

import requests
from sema4ai.actions import ActionError, OAuth2Secret, Response, action

from microsoft_onedrive.models import (
    DeleteOneDriveItemParams,
    OneDriveFolderCreationParams,
    OneDriveUploadRequest,
    RenameOneDriveItemParams,
)
from microsoft_onedrive.support import (
    BASE_GRAPH_URL,
    build_headers,
)


@action
def create_onedrive_folder(
    token: OAuth2Secret[
        Literal["microsoft"],
        List[Literal["Files.ReadWrite"]],
    ],
    params: OneDriveFolderCreationParams,
) -> Response[dict]:
    """
    Create a new folder in OneDrive.

    Args:
        token: OAuth2 token to use for the operation.
        params: OneDriveFolderCreationParams object containing:
            folder_name: name of the folder to create.
            parent_folder_path: path of the parent folder in OneDrive (optional).

    Returns:
        Response with the result of the operation
    """
    headers = build_headers(token)

    if params.parent_folder_path:
        create_url = (
            f"{BASE_GRAPH_URL}/me/drive/root:/{params.parent_folder_path}:/children"
        )
    else:
        create_url = f"{BASE_GRAPH_URL}/me/drive/root/children"

    folder_data = {
        "name": params.folder_name,
        "folder": {},
        "@microsoft.graph.conflictBehavior": "rename",
    }

    create_response = requests.post(create_url, headers=headers, json=folder_data)

    if create_response.status_code in [200, 201]:
        folder_info = create_response.json()
        return Response(
            result={
                "message": "Folder created successfully",
                "folder_id": folder_info.get("id"),
                "folder_name": folder_info.get("name"),
                "web_url": folder_info.get("webUrl"),
            }
        )
    else:
        raise ActionError(f"Failed to create folder: {create_response.text}")


@action
def delete_onedrive_item(
    token: OAuth2Secret[
        Literal["microsoft"],
        List[Literal["Files.ReadWrite"]],
    ],
    params: DeleteOneDriveItemParams,
) -> Response[dict]:
    """
    Delete a file or folder from OneDrive using its ID.

    Args:
        token: OAuth2 token with Files.ReadWrite permission.
        params: Pydantic model containing the item_id parameter.

    Returns:
        Dictionary with a 'success' key indicating whether the deletion was successful.
    """
    headers = build_headers(token)
    url = f"{BASE_GRAPH_URL}/me/drive/items/{params.item_id}"

    try:
        response = requests.delete(url, headers=headers)
        response.raise_for_status()

        return Response(
            result={"success": True, "message": "Item deleted successfully"}
        )

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
                "Access forbidden. You may not have permission to delete this item."
            )
        elif status_code == 404:
            raise ActionError(f"Item not found: {params.item_id}")
        elif status_code == 409:
            raise ActionError("Conflict error. The item might be locked or in use.")
        else:
            raise ActionError(f"Failed to delete OneDrive item: HTTP {status_code}")
    except requests.RequestException as e:
        raise ActionError(f"Network error while deleting OneDrive item: {str(e)}")
    except Exception as e:
        raise ActionError(f"Unexpected error while deleting OneDrive item: {str(e)}")


@action
def rename_onedrive_item(
    token: OAuth2Secret[
        Literal["microsoft"],
        List[Literal["Files.ReadWrite"]],
    ],
    params: RenameOneDriveItemParams,
) -> Response[dict]:
    """
    Rename a file or folder in OneDrive using its ID.

    Args:
        token: OAuth2 token with Files.ReadWrite permission.
        params: Pydantic model containing the item_id and new_name parameters.

    Returns:
        Dictionary with information about the renamed item.
    """
    headers = build_headers(token)
    url = f"{BASE_GRAPH_URL}/me/drive/items/{params.item_id}"

    body = {"name": params.new_name}

    try:
        response = requests.patch(url, headers=headers, json=body)
        response.raise_for_status()

        renamed_item = response.json()
        return Response(
            result={
                "success": True,
                "message": "Item renamed successfully",
                "item": {
                    "id": renamed_item.get("id"),
                    "name": renamed_item.get("name"),
                    "type": "folder" if "folder" in renamed_item else "file",
                },
            }
        )

    except requests.HTTPError as e:
        status_code = e.response.status_code
        if status_code == 400:
            raise ActionError(
                f"Bad request. The item ID '{params.item_id}' might be invalid or the new name '{params.new_name}' is not allowed."
            )
        elif status_code == 401:
            raise ActionError("Unauthorized. Please check your authentication token.")
        elif status_code == 403:
            raise ActionError(
                "Access forbidden. You may not have permission to rename this item."
            )
        elif status_code == 404:
            raise ActionError(f"Item not found: {params.item_id}")
        elif status_code == 409:
            raise ActionError(
                "Conflict error. An item with the new name might already exist in the same location."
            )
        else:
            raise ActionError(f"Failed to rename OneDrive item: HTTP {status_code}")
    except requests.RequestException as e:
        raise ActionError(f"Network error while renaming OneDrive item: {str(e)}")
    except Exception as e:
        raise ActionError(f"Unexpected error while renaming OneDrive item: {str(e)}")


@action
def upload_file_to_onedrive(
    token: OAuth2Secret[
        Literal["microsoft"],
        List[Literal["Files.ReadWrite"]],
    ],
    upload_request: OneDriveUploadRequest,
) -> Response[dict]:
    """
    Upload a file to OneDrive.

    Args:
        token: OAuth2 token to use for the operation.
        upload_request: OneDriveUploadRequest object containing:
            filename: name of the file to upload.
            folder_path: path of the folder in OneDrive to upload the file to.

    Returns:
        Response with the result of the operation
    """
    headers = build_headers(token)
    upload_file = Path(upload_request.filepath).resolve()
    filesize = os.path.getsize(upload_file)

    if upload_request.folder_path:
        upload_url = f"{BASE_GRAPH_URL}/me/drive/root:/{upload_request.folder_path}/{upload_file.name}:/content"
        upload_session_url = f"{BASE_GRAPH_URL}/me/drive/root:/{upload_request.folder_path}/{upload_file.name}:/createUploadSession"
    else:
        upload_url = f"{BASE_GRAPH_URL}/me/drive/root:/{upload_file.name}:/content"
        upload_session_url = (
            f"{BASE_GRAPH_URL}/me/drive/root:/{upload_file.name}:/createUploadSession"
        )

    headers.update({"Content-Type": "application/octet-stream"})

    if filesize <= 4000000:  # 4MB
        with open(upload_request.filepath, "rb") as file:
            file_content = file.read()
        upload_response = requests.put(upload_url, headers=headers, data=file_content)
        if upload_response.status_code in [200, 201]:
            web_url = upload_response.json()["webUrl"]
            return Response(
                result={
                    "message": f"File uploaded successfully and can be found at {web_url}"
                }
            )
        else:
            raise ActionError(f"Failed to upload file: {upload_response.text}")
    else:
        # upload bigger file in session
        upload_session_response = requests.post(upload_session_url, headers=headers)
        upload_url = upload_session_response.json()["uploadUrl"]
        chunk_size = 327680  # 320KB
        with open(upload_request.filepath, "rb") as file:
            i = 0
            while True:
                chunk_data = file.read(chunk_size)
                if not chunk_data:
                    break
                start = i * chunk_size
                end = start + len(chunk_data) - 1
                headers.update({"Content-Range": f"bytes {start}-{end}/{filesize}"})
                chunk_response = requests.put(
                    upload_url, headers=headers, data=chunk_data
                )
                if not chunk_response.ok:
                    raise ActionError(f"Failed to upload file: {chunk_response.text}")
                i += 1
        return Response(result={"message": "File uploaded successfully"})
