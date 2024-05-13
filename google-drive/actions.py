import json
import os
from io import BytesIO
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from sema4ai.actions import Secret, action

from models import CommentList, File, FileList, Response

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")

DEV_GOOGLE_CREDENTIALS = Secret.model_validate(os.getenv("DEV_GOOGLE_CREDENTIALS", ""))
SCOPES = ["https://www.googleapis.com/auth/drive"]
FILE_FIELDS = [
    "id",
    "name",
    "mimeType",
    "createdTime",
    "modifiedTime",
    "owners",
    "size",
    "version",
    "webViewLink",
    "permissions",
]

EXPORT_MIMETYPE_MAP = {
    "application/vnd.google-apps.spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.google-apps.document": "text/plain",
}


def _build_service(credentials: Secret) -> Resource:
    # Create the Google Drive V3 service interface
    creds = service_account.Credentials.from_service_account_info(
        json.loads(credentials.value), scopes=SCOPES
    )

    return build("drive", "v3", credentials=creds)


def _get_file_by_name(service: Resource, name: str) -> Optional[File]:
    response = (
        service.files()
        .list(q=f"name = '{name}'", fields=f'files({",".join(FILE_FIELDS)})')
        .execute()
    )

    if not response.get("files"):
        return

    return File(**response["files"][0])


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


@action(is_consequential=False)
def get_file_by_id(
    file_id: str, google_credentials: Secret = DEV_GOOGLE_CREDENTIALS
) -> Response[File]:
    """Get a file from Google Drive by id.

    Args:
        file_id: Unique id of the file.
        google_credentials: Json containing Google service account credentials.

    Returns:
        Message containing the details of the file or error message.
    """

    service = _build_service(google_credentials)
    try:
        return Response(
            result=File(
                **service.files()
                .get(fileId=file_id, fields=",".join(FILE_FIELDS))
                .execute()
            )
        )
    except HttpError:
        return Response(error=f"No files were found with the id: {file_id}")
    finally:
        service.close()


@action(is_consequential=False)
def get_files_by_query(
    query: str, google_credentials: Secret = DEV_GOOGLE_CREDENTIALS
) -> Response[FileList]:
    """Get all files from Google Drive that match the given query.

    Args:
        query: Google Drive API V3 query string for search files in the format query_term operator values.
        google_credentials: Json containing Google service account credentials.

    Returns:
        A list of files or an error message if no files were found.
    """
    service = _build_service(google_credentials)

    response = (
        service.files()
        .list(q=query, fields=f'files({",".join(FILE_FIELDS)})')
        .execute()
    )
    service.close()

    files = FileList(files=response.get("files", []))
    if not files:
        return Response(error=f"No files were found for the query: {query}")

    return Response(result=files)


@action(is_consequential=False)
def get_file_contents(
    name: str, worksheet: str = "", google_credentials: Secret = DEV_GOOGLE_CREDENTIALS
) -> Response:
    """
    Get the file contents.

    Args:
        name: Name of the file.
        worksheet: Name of the worksheet in case of Excel files, default is the first sheet.
        google_credentials: Json containing Google service account credentials.

    Return:
        The file contents or an error message.
    """
    service = _build_service(google_credentials)

    file = _get_file_by_name(service, name)
    if not file:
        return Response(error=f"The file named '{name}' could not be found")

    if not EXPORT_MIMETYPE_MAP.get(file.mimeType):
        return Response(
            error=f"Type document {file.mimeType} is not supported for this operation"
        )

    file_content = _export_file_content(
        service, file.id, EXPORT_MIMETYPE_MAP[file.mimeType]
    )

    service.close()

    if file.is_excel():
        return Response(result=_get_excel_content(file_content, worksheet))

    return Response(result=file_content.getvalue().decode("utf-8", errors="replace"))


@action(is_consequential=True)
def share_document(
    name: str,
    role: str,
    email_address: str,
    google_credentials: Secret = DEV_GOOGLE_CREDENTIALS,
) -> Response:
    """
    Share a document with a specific email address.

    Args:
        name: Name of the file to be shared.
        role: Assign a specific role. Possible options are: reader, writer, commenter, organizer, fileOrganizer.
        email_address: The email address of the user or group to share the file with.
        google_credentials: Json containing Google service account credentials.

    Return:
        Message indicating the success or failure of the operation.
    """
    service = _build_service(google_credentials)

    permission = {"type": "user", "role": role, "emailAddress": email_address}

    file = _get_file_by_name(service, name)
    if not file:
        return Response(error=f"The file named '{name}' could not be found")

    try:
        service.permissions().create(
            fileId=file.id, body=permission, fields="id"
        ).execute()
    except HttpError as e:
        return Response(error=f"Failed to share the document. Reason: {e.reason}")
    finally:
        service.close()

    return Response(
        result=f"Permission {role} was granted. File link: {file.webViewLink}"
    )


@action(is_consequential=False)
def list_file_comments(
    name: str, google_credentials: Secret = DEV_GOOGLE_CREDENTIALS
) -> Response[CommentList]:
    """
    List the comments on a specific file.

    Args:
        name: Name of the file to read its associated comments.
        google_credentials: Json containing Google service account credentials.

    Return:
        List of comments associated with the file.
    """
    service = _build_service(google_credentials)

    file = _get_file_by_name(service, name)
    if not file:
        return []

    comments_list = (
        service.comments()
        .list(fileId=file.id, fields="*")
        .execute()
        .get("comments", [])
    )

    return Response(result=CommentList(comments=comments_list))
