import os
from pathlib import Path
from typing import List, Literal

from sema4ai.actions import OAuth2Secret, Response, action

from microsoft_onedrive.models import (
    DeleteOneDriveItemParams,
    OneDriveFolderCreationParams,
    OneDriveUploadRequest,
    RenameOneDriveItemParams,
)
from microsoft_onedrive.support import build_headers, send_request


@action
def create_onedrive_folder(
    token: OAuth2Secret[
        Literal["microsoft"],
        List[Literal["Files.ReadWrite"]],
    ],
    params: OneDriveFolderCreationParams,
) -> Response[dict]:
    """Create a new folder in OneDrive.

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
        create_url = f"/me/drive/root:/{params.parent_folder_path}:/children"
    else:
        create_url = "/me/drive/root/children"
    folder_data = {
        "name": params.folder_name,
        "folder": {},
        "@microsoft.graph.conflictBehavior": "rename",
    }

    folder_info = send_request(
        "post", create_url, "create folder", headers=headers, json=folder_data
    )
    return Response(
        result={
            "message": "Folder created successfully",
            "folder_id": folder_info.get("id"),
            "folder_name": folder_info.get("name"),
            "web_url": folder_info.get("webUrl"),
        }
    )


@action
def delete_onedrive_item(
    token: OAuth2Secret[
        Literal["microsoft"],
        List[Literal["Files.ReadWrite"]],
    ],
    params: DeleteOneDriveItemParams,
) -> Response[dict]:
    """Delete a file or folder from OneDrive using its ID.

    Args:
        token: OAuth2 token with Files.ReadWrite permission.
        params: Pydantic model containing the item_id parameter.

    Returns:
        Dictionary with a 'success' key indicating whether the deletion was successful.
    """
    headers = build_headers(token)
    url = f"/me/drive/items/{params.item_id}"

    send_request("delete", url, "delete item", headers=headers)
    return Response(result={"success": True, "message": "Item deleted successfully"})


@action
def rename_onedrive_item(
    token: OAuth2Secret[
        Literal["microsoft"],
        List[Literal["Files.ReadWrite"]],
    ],
    params: RenameOneDriveItemParams,
) -> Response[dict]:
    """Rename a file or folder in OneDrive using its ID.

    Args:
        token: OAuth2 token with Files.ReadWrite permission.
        params: Pydantic model containing the item_id and new_name parameters.

    Returns:
        Dictionary with information about the renamed item.
    """
    headers = build_headers(token)
    url = f"/me/drive/items/{params.item_id}"
    body = {"name": params.new_name}

    renamed_item = send_request("patch", url, "rename item", headers=headers, json=body)
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


@action
def upload_file_to_onedrive(
    token: OAuth2Secret[
        Literal["microsoft"],
        List[Literal["Files.ReadWrite"]],
    ],
    upload_request: OneDriveUploadRequest,
) -> Response[dict]:
    """Upload a file to OneDrive.

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
        upload_url = (
            f"/me/drive/root:/{upload_request.folder_path}/{upload_file.name}:/content"
        )
        upload_session_url = f"/me/drive/root:/{upload_request.folder_path}/{upload_file.name}:/createUploadSession"
    else:
        upload_url = f"/me/drive/root:/{upload_file.name}:/content"
        upload_session_url = f"/me/drive/root:/{upload_file.name}:/createUploadSession"

    headers.update({"Content-Type": "application/octet-stream"})

    if filesize <= 4000000:  # 4MB
        with open(upload_request.filepath, "rb") as file:
            file_content = file.read()
        upload_response = send_request(
            "put", upload_url, "upload file", headers=headers, data=file_content
        )
        return Response(
            result={
                "message": f"File uploaded successfully and can be found at {upload_response['webUrl']}"
            }
        )
    else:
        # upload bigger file in session
        upload_session_response = send_request(
            "post", upload_session_url, "create upload session", headers=headers
        )
        upload_url = upload_session_response["uploadUrl"]
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
                send_request(
                    "put", upload_url, "upload chunk", headers=headers, data=chunk_data
                )
                i += 1
        return Response(result={"message": "File uploaded successfully"})
