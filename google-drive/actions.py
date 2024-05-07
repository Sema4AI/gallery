import os
import json

import pandas as pd
from io import BytesIO
from pathlib import Path
from typing import List, Optional, TypeVar, Generic

from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload
from pydantic import BaseModel

from sema4ai.actions import Secret, action

load_dotenv(Path("devdata") / ".env")

DEFAULT_CREDENTIALS = Secret.model_validate(os.getenv("GOOGLE_CREDENTIALS", ""))
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


class Owner(BaseModel):
    displayName: str
    emailAddress: Optional[str] = None


class Permission(BaseModel):
    emailAddress: str
    role: str
    deleted: bool
    pendingOwner: bool


class File(BaseModel):
    id: str
    name: str
    mimeType: str
    createdTime: str
    modifiedTime: str
    owners: List[Owner]
    size: str
    version: str
    webViewLink: str
    permissions: List[Permission]

    def size_in_megabytes(self):
        size_in_bytes = int(self.size)
        size_in_mb = size_in_bytes / (1024 * 1024)
        return round(size_in_mb, 2)

    def is_excel(self):
        return self.mimeType == "application/vnd.google-apps.spreadsheet"

    def is_doc(self):
        return self.mimeType == "application/vnd.google-apps.document"


class FileList(BaseModel):
    files: List[File]


class BaseComment(BaseModel):
    id: str
    kind: str
    createdTime: str
    modifiedTime: str
    htmlContent: str
    content: str
    author: Owner
    deleted: bool


class Reply(BaseComment):
    action: Optional[str] = None


class Comment(BaseComment):
    resolved: Optional[bool] = None
    replies: List[Reply]


class CommentList(BaseModel):
    comments: List[Comment]


DataT = TypeVar("DataT")


class Response(BaseModel, Generic[DataT]):
    result: Optional[DataT] = None
    error: Optional[str] = None


def _build_service(credentials: Secret):
    creds = service_account.Credentials.from_service_account_info(
        json.loads(credentials.value), scopes=SCOPES
    )

    return build("drive", "v3", credentials=creds)


def _get_file_by_name(service, name: str) -> Optional[File]:
    response = (
        service.files()
        .list(q=f"name = '{name}'", fields=f'files({",".join(FILE_FIELDS)})')
        .execute()
    )

    if not response.get("files"):
        return

    return File(**response["files"][0])


def _export_file_content(service, file_id: str, mime_type: str) -> BytesIO:
    # Export the file content
    request = service.files().export_media(fileId=file_id, mimeType=mime_type)
    fh = BytesIO()
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while done is False:
        status, done = downloader.next_chunk()

    return fh


def _get_excel_content(file_content: BytesIO, worksheet: Optional[str] = None):
    if worksheet:
        df = pd.read_excel(file_content, sheet_name=worksheet)
    else:
        df = pd.read_excel(file_content)

    df_cleaned = df.rename(columns=lambda x: "" if x.startswith("Unnamed") else x)
    df_cleaned = df_cleaned.fillna("")

    return df_cleaned.to_string(index=False)


@action(is_consequential=False)
def get_file_by_id(
    file_id: str, credentials: Secret = DEFAULT_CREDENTIALS
) -> Response[File]:
    """Get a file from Google Drive by id.

    Args:
        file_id: unique id of the file

    Returns:
        Message containing the details of the file or error message.
    """

    service = _build_service(credentials)
    try:
        return Response(
            result=File(
                **service.files()
                .get(fileId=file_id, fields=",".join(FILE_FIELDS))
                .execute()
            )
        )
    except Exception:
        return Response(error=f"No files were found with the id: {file_id}")
    finally:
        service.close()


@action(is_consequential=False)
def get_files_by_query(
    query: str, credentials: Secret = DEFAULT_CREDENTIALS
) -> Response[FileList]:
    """Get all files from Google Drive that match the given query.

    Args:
        query: Google Drive API V3 query string for search files in the format query_term operator values

    Returns:
        A list of files or an error message if no files were found.
    """
    service = _build_service(credentials)

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
    name: str, worksheet: str = "", credentials: Secret = DEFAULT_CREDENTIALS
) -> str:
    """
    Get the file contents.

    Args:
        name: name of the file
        worksheet: name of the worksheet in case of Excel files, default is the first sheet

    Return:
        The file contents or an error message.
    """
    service = _build_service(credentials)

    file = _get_file_by_name(service, name)
    if not file:
        return "File was not found"

    if not EXPORT_MIMETYPE_MAP.get(file.mimeType):
        return f"Type document {file.mimeType} is not supported for this operation"

    file_content = _export_file_content(
        service, file.id, EXPORT_MIMETYPE_MAP[file.mimeType]
    )

    service.close()

    if file.is_excel():
        return _get_excel_content(file_content, worksheet)

    return file_content.getvalue().decode("utf-8")


@action(is_consequential=True)
def share_document(
    name: str, role: str, email_address: str, credentials: Secret = DEFAULT_CREDENTIALS
) -> str:
    """
    Share a document with a specific email address.

    Args:
        name: name of the file to be shared
        role: assign a specific role; options: reader, writer, commenter, organizer, fileOrganizer
        email_address: the email address of the user or group to share the file with.

    Return:
        Message indicating the success or failure of the operation.
    """
    service = _build_service(credentials)

    permission = {"type": "user", "role": role, "emailAddress": email_address}

    file = _get_file_by_name(service, name)
    if not file:
        return "File was not found"

    try:
        service.permissions().create(
            fileId=file.id, body=permission, fields="id"
        ).execute()
    except Exception as e:
        return f"An error occurred: {e}"
    finally:
        service.close()

    return f"Permission {role} was granted. File link: {file.webViewLink}"


@action(is_consequential=False)
def list_file_comments(
    name: str, credentials: Secret = DEFAULT_CREDENTIALS
) -> Response[CommentList]:
    """
    List the comments on a specific file.

    Args:
        name: name of the file to read its associated comments

    Return:
        The comments associated with the file.
    """
    service = _build_service(credentials)

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
