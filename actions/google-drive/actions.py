from io import BytesIO
from pathlib import Path
from typing import Literal, Optional, Union
import csv
import io

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from models import CommentList, File, FileList, Response, BasicFile
from sema4ai.actions import OAuth2Secret, action, chat, ActionError

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")

EXPORT_MIMETYPE_MAP = {
    "application/vnd.google-apps.spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.google-apps.document": "text/plain",
}


def _build_service(credentials: OAuth2Secret) -> Resource:
    # Create the Google Drive V3 service interface
    creds = Credentials(token=credentials.access_token)

    return build("drive", "v3", credentials=creds)


def _get_file_by_name(service: Resource, name: str) -> Optional[File]:
    response = (
        service.files()
        .list(
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            q=f"name = '{name}'",
            fields="*",
        )
        .execute()
    )

    if not response.get("files"):
        return

    return File(**response["files"][0])


def _get_file_by_id(service: Resource, file_id: str) -> Optional[File]:
    try:
        return File(
            **service.files()
            .get(supportsAllDrives=True, fileId=file_id, fields="*")
            .execute()
        )
    except HttpError:
        return None


def _export_file_content(service: Resource, file_id: str, mime_type: str) -> BytesIO:
    # Export the file content to the desired format
    request = service.files().export_media(fileId=file_id, mimeType=mime_type)
    fh = BytesIO()
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while done is False:
        status, done = downloader.next_chunk()

    return fh


def _get_excel_content(file_content: BytesIO, worksheet: Optional[str] = None) -> str:
    import pandas as pd

    if worksheet:
        df = pd.read_excel(file_content, sheet_name=worksheet)
    else:
        df = pd.read_excel(file_content)

    df_cleaned = df.rename(columns=lambda x: "" if x.startswith("Unnamed") else x)
    df_cleaned = df_cleaned.fillna("")

    return df_cleaned.to_string(index=False)


def _resolve_full_path(service: Resource, file: dict, id_to_file: dict) -> str:
    path_parts = []
    parents = file.get("parents", [])
    drive_type = None
    found_drive_root = False
    while parents:
        parent_id = parents[0]
        parent = id_to_file.get(parent_id)
        if not parent:
            try:
                parent = service.files().get(
                    fileId=parent_id,
                    fields="id, name, parents, driveId, mimeType",
                    supportsAllDrives=True
                ).execute()
                id_to_file[parent_id] = parent
            except Exception:
                # Try as shared drive root
                try:
                    drive = service.drives().get(driveId=parent_id, fields="id, name").execute()
                    path_parts.append(drive.get("name", "?"))
                    drive_type = "shared"
                    found_drive_root = True
                    break
                except Exception:
                    path_parts.append("?")
                    break
        # If parent is the root of a shared drive (no parents, has driveId), use the drive's name
        if parent.get("driveId") and not parent.get("parents"):
            try:
                drive = service.drives().get(driveId=parent.get("driveId"), fields="id, name").execute()
                path_parts.append(drive.get("name", "?"))
                drive_type = "shared"
                found_drive_root = True
            except Exception:
                path_parts.append("?")
            break
        # If parent is the My Drive root, stop and mark
        if parent.get("mimeType") == "application/vnd.google-apps.folder" and not parent.get("parents"):
            path_parts.append(parent.get("name", "?"))
            drive_type = "mydrive"
            found_drive_root = True
            break
        path_parts.append(parent.get("name", "?"))
        parents = parent.get("parents", [])
    path_parts = list(reversed([p for p in path_parts if p]))
    if drive_type == "shared" and found_drive_root:
        path_parts = ["Shared Drives"] + path_parts
    elif drive_type == "mydrive" and found_drive_root:
        path_parts = ["My Drive"] + path_parts


    return "/".join(path_parts) if path_parts else "/"


def to_csv_for_filelist(file_list: FileList) -> str:
    # Convert FileList (with File or BasicFile objects) to CSV string
    if not file_list.files:
        return ""
    # Use the union of all keys in all file dicts as columns
    all_keys = set()
    dicts = []
    for f in file_list.files:
        d = f.model_dump() if hasattr(f, 'model_dump') else dict(f)
        dicts.append(d)
        all_keys.update(d.keys())
    fieldnames = sorted(all_keys)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for d in dicts:
        writer.writerow({k: d.get(k, "") for k in fieldnames})
    return output.getvalue()


def _extract_parent_name_from_query(query: str) -> Optional[str]:
    """Extract parent folder name from a query containing 'in parents'."""
    import re

    # Match either 'name' or "name" followed by "in parents"
    pattern = r"['\"]([^'\"]+)['\"] in parents"
    match = re.search(pattern, query)
    if match:
        return match.group(1)
    return None


def _resolve_parent_folder_name(service: Resource, parent_name: str, search_all_drives: bool = False) -> Optional[str]:
    """Helper function to get folder ID from folder name.

    When search_all_drives is True, searches in all shared drives as well.
    Handles both folder names and shared drive names.
    """
    try:
        # First list all shared drives to search in them specifically
        shared_drives = []
        if search_all_drives:
            try:
                drives_response = service.drives().list(
                    fields="drives(id,name)",
                    pageSize=50
                ).execute()
                shared_drives = drives_response.get('drives', [])
                print(f"Found {len(shared_drives)} shared drives to search in")

                # Check if the parent name is actually a shared drive name
                for drive in shared_drives:
                    if drive.get('name') == parent_name:
                        print(f"Found exact match for shared drive: {parent_name} (ID: {drive.get('id')})")
                        return drive.get('id')
                    elif drive.get('name').lower() == parent_name.lower():
                        print(f"Found case-insensitive match for shared drive: {drive.get('name')} (ID: {drive.get('id')})")
                        return drive.get('id')

            except Exception as e:
                print(f"Warning: Could not list shared drives: {str(e)}")

        # If not a shared drive name, try exact match for folders
        query = f"name = '{parent_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"

        # Try in each shared drive first
        for drive in shared_drives:
            list_args = {
                "q": query,
                "spaces": "drive",
                "fields": "files(id,name,driveId,parents)",
                "supportsAllDrives": True,
                "includeItemsFromAllDrives": True,
                "corpora": "drive",
                "driveId": drive['id']
            }

            print(f"Searching for folder '{parent_name}' in shared drive '{drive.get('name')}' ({drive.get('id')})")
            try:
                response = service.files().list(**list_args).execute()
                files = response.get('files', [])
                if files:
                    selected = files[0]
                    print(f"Found in shared drive '{drive.get('name')}': {selected.get('name')} ({selected.get('id')})")
                    return selected['id']
            except Exception as e:
                print(f"Warning: Error searching in drive '{drive.get('name')}': {str(e)}")
                continue

        # If not found in specific shared drives, try general search
        list_args = {
            "q": query,
            "spaces": "drive",
            "fields": "files(id,name,driveId,parents)",
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
        }

        if search_all_drives:
            list_args["corpora"] = "allDrives"

        print(f"Searching for folder '{parent_name}' across all accessible locations")
        response = service.files().list(**list_args).execute()
        files = response.get('files', [])

        print(f"Found {len(files)} potential folders:")
        for f in files:
            print(f"  - Name: {f.get('name')}, ID: {f.get('id')}, DriveId: {f.get('driveId')}, Parents: {f.get('parents')}")

        if not files and search_all_drives:
            # Try without exact name match in case of case sensitivity issues
            query = f"name contains '{parent_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            list_args["q"] = query
            print("Retrying with case-insensitive search")
            response = service.files().list(**list_args).execute()
            files = response.get('files', [])
            print(f"Found {len(files)} folders with case-insensitive search")
            for f in files:
                if f.get('name').lower() == parent_name.lower():  # Case-insensitive exact match
                    files = [f]
                    break

        if not files:
            print(f"No folders found matching name '{parent_name}'")
            return None

        # If searching all drives, prefer folders from shared drives
        if search_all_drives and any(f.get('driveId') for f in files):
            shared_folders = [f for f in files if f.get('driveId')]
            selected = shared_folders[0]
            print(f"Selected shared drive folder: Name: {selected.get('name')}, ID: {selected.get('id')}, DriveId: {selected.get('driveId')}")
            return selected['id']

        selected = files[0]
        print(f"Selected folder: Name: {selected.get('name')}, ID: {selected.get('id')}, DriveId: {selected.get('driveId')}")
        return selected['id']
    except Exception as e:
        print(f"Error resolving parent folder name '{parent_name}': {str(e)}")
        return None


def _preprocess_query(service: Resource, query: str, search_all_drives: bool = False) -> str:
    """Preprocess query to handle parent folder names."""
    import re

    parent_name = _extract_parent_name_from_query(query)
    if not parent_name:
        return query

    parent_id = _resolve_parent_folder_name(service, parent_name, search_all_drives)
    if parent_id:
        # Replace the folder name with its ID in the original query
        return re.sub(f"['\"]({re.escape(parent_name)})['\"] in parents", f"'{parent_id}' in parents", query)

    print(f"Warning: Could not resolve parent folder name '{parent_name}'")
    return query


@action(is_consequential=False)
def get_file_by_id(
    google_credentials: OAuth2Secret[
        Literal["google"],
        list[
            Literal[
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/drive.metadata.readonly"
            ]
        ],
    ],
    file_id: str,
) -> Response[File]:
    """Get a file from Google Drive by id.

    Args:
        google_credentials: JSON containing Google OAuth2 credentials.
        file_id: Unique id of the file.

    Returns:
        Message containing the details of the file or error message.
    """

    service = _build_service(google_credentials)

    file = _get_file_by_id(service, file_id)
    service.close()

    if file:
        return Response(result=file)

    return Response(error=f"No files were found with the id: {file_id}")


@action(is_consequential=False)
def get_files_by_query(
    google_credentials: OAuth2Secret[
        Literal["google"],
        list[
            Literal[
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/drive.metadata.readonly"
            ]
        ],
    ],
    query: str,
    search_all_drives: bool = False,
    basic_info_only: bool = False,
    save_result_as_csv: Union[bool, str] = False,
) -> Response[FileList]:
    """Get all files from Google Drive that match the given query.

    Args:
        google_credentials: JSON containing Google OAuth2 credentials.
        query: Google Drive API V3 query string for search files in the format query_term operator values.
            When using 'in parents' operator, you can use either the parent folder's ID or name.
            Example: "name = 'Report' and 'My Folder' in parents"
            When search_all_drives is True, parent folder names will be searched in shared drives first.
        search_all_drives: Whether to search both My Drives and all shared drives.
            Default is set to false for better performance and will include both owned files and those that have been
            shared with the user.
        basic_info_only: Whether to return only the basic information of the files
        save_result_as_csv: If True, saves results to 'query_result.csv'. If a string is provided,
            uses that as the filename to save the CSV results.

    Returns:
        A list of files or an error message if no files were found.
    """
    service = _build_service(google_credentials)

    try:
        # First try to resolve any parent folder names
        processed_query = _preprocess_query(service, query, search_all_drives)

        list_args = {
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
            "q": processed_query,
            "fields": "*",
        }

        if search_all_drives:
            list_args["corpora"] = "allDrives"
            list_args["spaces"] = "drive"

        print(f"Executing final query with args: {list_args}")
        response = service.files().list(**list_args).execute()
        files_data = response.get("files", [])

        # Build a map of id to file for quick lookup
        id_to_file = {f["id"]: f for f in files_data}

        # Resolve location for each file
        files = []
        for f in files_data:
            location = _resolve_full_path(service, f, id_to_file)
            if basic_info_only:
                basic_file = BasicFile(
                    id=f.get("id"),
                    name=f.get("name"),
                    location=location,
                    webViewLink=f.get("webViewLink"),
                )
                files.append(basic_file)
            else:
                file_obj = File(**f)
                file_obj.location = location
                files.append(file_obj)

        file_list = FileList(files=files)
        if not files:
            if "in parents" in query and "in parents" in processed_query:
                raise ActionError(error="No files found. Parent folder could not be found or you may not have access to it.")
            return Response(error=f"No files were found for the query: {query}")

        if save_result_as_csv:
            csv_filename = "query_result.csv" if isinstance(save_result_as_csv, bool) else save_result_as_csv
            chat.attach_file_content(name=csv_filename, data=to_csv_for_filelist(file_list).encode("utf-8"))

        return Response(result=file_list)
    except HttpError as e:
        error_reason = str(e)
        if "File not found" in error_reason:
            raise ActionError("The specified folder could not be found or you may not have sufficient permissions to access it.")
        raise ActionError(f"Failed to execute query: {error_reason}")
    except Exception as e:
        raise ActionError(f"An error occurred: {str(e)}")
    finally:
        service.close()


@action(is_consequential=False)
def get_file_contents(
    google_credentials: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/drive.readonly"]]
    ],
    name: str,
    worksheet: str = "",
) -> Response[str]:
    """Get the file contents.

    Args:
        google_credentials: JSON containing Google OAuth2 credentials.
        name: Name of the file.
        worksheet: Name of the worksheet in case of Excel files, default is the first sheet.

    Returns:
        The file contents or an error message.
    """
    service = _build_service(google_credentials)

    file = _get_file_by_name(service, name)
    if not file:
        return Response(error=f"The file named '{name}' could not be found")

    if not EXPORT_MIMETYPE_MAP.get(file.mimeType):
        raise ActionError(f"Type document {file.mimeType} is not supported for this operation")

    file_content = _export_file_content(
        service, file.id, EXPORT_MIMETYPE_MAP[file.mimeType]
    )

    service.close()

    if file.is_excel():
        return Response(result=_get_excel_content(file_content, worksheet))

    return Response(result=file_content.getvalue().decode("utf-8", errors="replace"))


@action(is_consequential=True)
def share_document(
    google_credentials: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/drive.file"]]
    ],
    name: str,
    role: str,
    email_address: str,
) -> Response[str]:
    """Share a document with a specific email address.

    Args:
        google_credentials: JSON containing Google OAuth2 credentials.
        name: Name of the file to be shared.
        role: Assign a specific role. Possible options are: reader, writer, commenter, organizer, fileOrganizer.
        email_address: The email address of the user or group to share the file with.

    Returns:
        Message indicating the success or failure of the operation.
    """
    service = _build_service(google_credentials)

    permission = {"type": "user", "role": role, "emailAddress": email_address}

    file = _get_file_by_name(service, name)
    if not file:
        return Response(error=f"The file named '{name}' could not be found")

    try:
        service.permissions().create(fileId=file.id, body=permission).execute()
    except HttpError as e:
        raise ActionError(f"Failed to share the document. Reason: {e.reason}")
    finally:
        service.close()

    return Response(
        result=f"Permission {role} was granted. File link: {file.webViewLink}"
    )


@action(is_consequential=False)
def list_file_comments(
    google_credentials: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/drive.readonly"]]
    ],
    name: str,
) -> Response[CommentList]:
    """List the comments on a specific file.

    Args:
        google_credentials: JSON containing Google OAuth2 credentials.
        name: Name of the file to read its associated comments.

    Returns:
        List of comments associated with the file.
    """
    service = _build_service(google_credentials)

    file = _get_file_by_name(service, name) or _get_file_by_id(service, name)
    if not file:
        return Response(error=f"The file named '{name}' could not be found")

    comments_list = (
        service.comments()
        .list(fileId=file.id, fields="*")
        .execute()
        .get("comments", [])
    )
    service.close()

    return Response(result=CommentList(comments=comments_list))


@action(is_consequential=True)
def upload_file(
    google_credentials: OAuth2Secret[
        Literal["google"],
        list[
            Literal[
                "https://www.googleapis.com/auth/drive.file"
            ]
        ],
    ],
    filename: str,
    drive_file_name: str,
    parent_folder_id: Optional[str] = None,
    share_with_email: Optional[str] = None,
    share_role: str = "reader",
) -> Response[File]:
    """Upload a file to Google Drive, and optionally share it with a user.

    The `parent_folder_id` can be either a folder ID or a shared drive ID, if not then use
    `get_files_by_query` to find the ID of the parent folder.

    Args:
        google_credentials: JSON containing Google OAuth2 credentials.
        filename: The name of the file to prompt the user to select or upload.
        drive_file_name: Desired name for the file in Google Drive.
        parent_folder_id: Optional ID of the parent folder in Drive.
        share_with_email: Optional email address to share the file with after upload.
        share_role: Role to grant to the shared user (reader, writer, commenter, organizer, fileOrganizer). Default is 'reader'.

    Returns:
        The uploaded file's metadata or an error message.
    """
    service = _build_service(google_credentials)
    file_metadata = {"name": drive_file_name}
    if parent_folder_id:
        file_metadata["parents"] = [parent_folder_id]
    try:
        local_file_path = chat.get_file(filename)
        media = MediaFileUpload(local_file_path, resumable=True)
        uploaded = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="*",
            supportsAllDrives=True
        ).execute()
        file_obj = File(**uploaded)
        # Optionally share the file
        if share_with_email:
            permission = {"type": "user", "role": share_role, "emailAddress": share_with_email}
            try:
                service.permissions().create(
                    fileId=file_obj.id,
                    body=permission,
                    supportsAllDrives=True,
                    sendNotificationEmail=True
                ).execute()
            except HttpError as e:
                if "File not found" in str(e):
                    raise ActionError(f"File uploaded but sharing failed: The file is in a shared drive and you may not have permission to share it. File ID: {file_obj.id}")
                raise ActionError(f"File uploaded but sharing failed: {str(e)}")
            except Exception as e:
                raise ActionError(f"File uploaded but sharing failed: {str(e)}")
        return Response(result=file_obj)
    except Exception as e:
        raise ActionError(f"Failed to upload file: {str(e)}")
    finally:
        service.close()
