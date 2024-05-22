from io import BytesIO
from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from models import CommentList, File, FileList, Response
from sema4ai.actions import OAuth2Secret, action

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
    response = service.files().list(q=f"name = '{name}'", fields="*").execute()

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
    google_credentials: OAuth2Secret[
        Literal["google"],
        list[
            Literal[
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/drive.metadata.readonly",
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
    try:
        return Response(
            result=File(**service.files().get(fileId=file_id, fields="*").execute())
        )
    except HttpError:
        return Response(error=f"No files were found with the id: {file_id}")
    finally:
        service.close()


@action(is_consequential=False)
def get_files_by_query(
    google_credentials: OAuth2Secret[
        Literal["google"],
        list[
            Literal[
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/drive.metadata.readonly",
            ]
        ],
    ],
    query: str,
) -> Response[FileList]:
    """Get all files from Google Drive that match the given query.

    Args:
        google_credentials: JSON containing Google OAuth2 credentials.
        query: Google Drive API V3 query string for search files in the format query_term operator values.

    Returns:
        A list of files or an error message if no files were found.
    """
    service = _build_service(google_credentials)

    response = service.files().list(q=query, fields="*").execute()
    service.close()

    print(response.get("files", []))
    files = FileList(files=response.get("files", []))
    if not files:
        return Response(error=f"No files were found for the query: {query}")

    return Response(result=files)


@action(is_consequential=False)
def get_file_contents(
    google_credentials: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/drive.readonly"]],
    ],
    name: str,
    worksheet: str = "",
) -> Response:
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
    google_credentials: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/drive.file"]],
    ],
    name: str,
    role: str,
    email_address: str,
) -> Response:
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
        return Response(error=f"Failed to share the document. Reason: {e.reason}")
    finally:
        service.close()

    return Response(
        result=f"Permission {role} was granted. File link: {file.webViewLink}"
    )


@action(is_consequential=False)
def list_file_comments(
    google_credentials: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/drive.readonly"]],
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

    file = _get_file_by_name(service, name)
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
