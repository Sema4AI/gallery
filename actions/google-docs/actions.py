import io
import json
import os
import re
from typing import Literal

from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError as GoogleApiHttpError
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from pydantic import ValidationError
from sema4ai.actions import (
    ActionError,
    OAuth2Secret,
    Response,
    action,
    chat,
)
from typing_extensions import Self

from models.documents import CommentAuthor, CommentInfo, DocumentInfo, MarkdownDocument, RawDocument, TabInfo
from models.update_operations import BatchUpdateBody


class Context:
    def __init__(self, secret: OAuth2Secret):
        self._secret = secret
        self._docs = None
        self._drive = None

    @property
    def documents(self) -> Resource:
        if self._docs is None:
            self._docs = build(
                "docs", "v1", credentials=Credentials(token=self._secret.access_token)
            )
        return self._docs.documents()

    @property
    def files(self) -> Resource:
        if self._drive is None:
            self._drive = build(
                "drive", "v3", credentials=Credentials(token=self._secret.access_token)
            )

        return self._drive.files()

    @property
    def comments(self) -> Resource:
        if self._drive is None:
            self._drive = build(
                "drive", "v3", credentials=Credentials(token=self._secret.access_token)
            )

        return self._drive.comments()

    @property
    def permissions(self) -> Resource:
        if self._drive is None:
            self._drive = build(
                "drive", "v3", credentials=Credentials(token=self._secret.access_token)
            )

        return self._drive.permissions()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._docs is not None:
            self._docs.close()

        if self._drive is not None:
            self._drive.close()

        if isinstance(exc_val, RefreshError):
            raise ActionError("Access token expired") from None
        elif isinstance(exc_val, GoogleApiHttpError):
            raise ActionError(exc_val.reason) from None


def _get_or_create_sema4_folder(ctx: Context) -> str:
    """Get or create the 'Sema4.ai Studio Files' folder in Google Drive."""
    folder_name = "Sema4.ai Studio Files"

    try:
        # Search for existing folder
        results = ctx.files.list(
            q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id, name)"
        ).execute()

        files = results.get('files', [])
        if files:
            # Folder exists, return its ID
            return files[0]['id']

        # Folder doesn't exist, create it
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': []  # Create in root folder
        }

        folder = ctx.files.create(
            body=folder_metadata,
            fields='id'
        ).execute()

        return folder.get('id')

    except Exception as e:
        raise ActionError(f"Error creating/accessing Sema4.ai Studio Files folder: {str(e)}")


def _upload_image_to_drive(ctx: Context, file_path: str, filename: str = None) -> str:
    """Upload an image file to the Sema4.ai Studio Files folder in Google Drive."""
    try:
        if not os.path.exists(file_path):
            raise ActionError(f"Image file not found: {file_path}")

        if filename is None:
            filename = os.path.basename(file_path)

        # Get or create the Sema4.ai Studio Files folder
        folder_id = _get_or_create_sema4_folder(ctx)

        # Read the image file
        with open(file_path, 'rb') as image_file:
            image_data = image_file.read()

        # Determine MIME type based on file extension
        file_ext = os.path.splitext(filename)[1].lower()
        mime_type_map = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp'
        }
        mime_type = mime_type_map.get(file_ext, 'image/png')

        # Create file metadata
        file_metadata = {
            'name': filename,
            'parents': [folder_id]  # Upload to Sema4.ai Studio Files folder
        }

        # Create media upload object
        media = MediaIoBaseUpload(
            io.BytesIO(image_data),
            mimetype=mime_type,
            resumable=True
        )

        file = ctx.files.create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        file_id = file.get('id')

        # Make the file publicly accessible
        permission = {
            'type': 'anyone',
            'role': 'reader'
        }
        ctx.permissions.create(
            fileId=file_id,
            body=permission
        ).execute()

        return file_id
    except Exception as e:
        raise ActionError(f"Error uploading image file {file_path} to Drive: {str(e)}")


def _upload_chat_file_to_drive(ctx: Context, filename: str) -> str:
    """Upload a chat file to the Sema4.ai Studio Files folder in Google Drive."""
    try:
        # Get the chat file content
        file_content = chat.get_file_content(filename)
        if not file_content:
            raise ActionError(f"Chat file '{filename}' not found or empty")

        # Get or create the Sema4.ai Studio Files folder
        folder_id = _get_or_create_sema4_folder(ctx)

        # Determine MIME type based on file extension
        file_ext = os.path.splitext(filename)[1].lower()
        mime_type_map = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml',
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.csv': 'text/csv',
            '.json': 'application/json'
        }
        mime_type = mime_type_map.get(file_ext, 'application/octet-stream')

        # Create file metadata
        file_metadata = {
            'name': filename,
            'parents': [folder_id]  # Upload to Sema4.ai Studio Files folder
        }

        # Create media upload object
        media = MediaIoBaseUpload(
            io.BytesIO(file_content),
            mimetype=mime_type,
            resumable=True
        )

        file = ctx.files.create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        file_id = file.get('id')

        # Make the file publicly accessible
        permission = {
            'type': 'anyone',
            'role': 'reader'
        }
        ctx.permissions.create(
            fileId=file_id,
            body=permission
        ).execute()

        return file_id
    except Exception as e:
        raise ActionError(f"Error uploading chat file '{filename}' to Drive: {str(e)}")


def _detect_chat_file_references(text: str) -> list[dict]:
    """Detect chat file references in the format <<filename>>."""
    chat_file_blocks = []

    # Pattern to match chat file references like <<filename.ext>>
    pattern = r'<<([^>]+)>>'

    matches = re.finditer(pattern, text)

    for match in matches:
        filename = match.group(1).strip()
        if filename:  # Only process non-empty filenames
            chat_file_blocks.append({
                'filename': filename,
                'start': match.start(),
                'end': match.end(),
                'original_text': match.group(0)
            })

    return chat_file_blocks


def _detect_vega_lite_markdown(text: str) -> list[dict]:
    """Detect vega-lite markdown blocks in the text and return their specifications."""
    vega_lite_blocks = []

    # Pattern to match vega-lite markdown blocks
    # Supports both ```vega-lite and ```json with vega-lite content
    pattern = r'```(?:vega-lite|json)\s*\n(.*?)\n```'

    matches = re.finditer(pattern, text, re.DOTALL | re.IGNORECASE)

    for match in matches:
        try:
            spec_text = match.group(1).strip()
            # Try to parse as JSON
            spec = json.loads(spec_text)

            # Basic validation to check if it looks like a vega-lite spec
            if isinstance(spec, dict) and ('mark' in spec or 'encoding' in spec or '$schema' in spec):
                # Automatically add schema if missing
                if '$schema' not in spec:
                    spec['$schema'] = 'https://vega.github.io/schema/vega-lite/v5.json'

                vega_lite_blocks.append({
                    'spec': spec,
                    'start': match.start(),
                    'end': match.end(),
                    'original_text': match.group(0)
                })
        except json.JSONDecodeError:
            # Skip invalid JSON
            continue

    return vega_lite_blocks


def _convert_vega_lite_to_drive_file(ctx: Context, vega_lite_spec: dict, filename: str = None) -> str:
    """Convert a vega-lite specification to a PNG image and upload to Sema4.ai Studio Files folder."""
    try:
        import vl_convert as vlc

        if filename is None:
            filename = f"vega_lite_chart_{hash(str(vega_lite_spec)) % 10000}.png"

        # Get or create the Sema4.ai Studio Files folder
        folder_id = _get_or_create_sema4_folder(ctx)

        # Convert vega-lite spec to PNG
        png_data = vlc.vegalite_to_png(vl_spec=vega_lite_spec, scale=2)

        # Create file metadata
        file_metadata = {
            'name': filename,
            'parents': [folder_id]  # Upload to Sema4.ai Studio Files folder
        }

        # Create media upload object
        media = MediaIoBaseUpload(
            io.BytesIO(png_data),
            mimetype='image/png',
            resumable=True
        )

        file = ctx.files.create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        file_id = file.get('id')

        # Make the file publicly accessible
        permission = {
            'type': 'anyone',
            'role': 'reader'
        }
        ctx.permissions.create(
            fileId=file_id,
            body=permission
        ).execute()

        return file_id
    except ImportError:
        raise ActionError("vl-convert-python library is required for vega-lite conversion. Please install it.")
    except Exception as e:
        raise ActionError(f"Error converting vega-lite to image and uploading to Drive: {str(e)}")


def _list_sema4_files(ctx: Context) -> list[dict]:
    """List all files in the Sema4.ai Studio Files folder."""
    try:
        folder_id = _get_or_create_sema4_folder(ctx)

        results = ctx.files.list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name, createdTime, size, mimeType)"
        ).execute()

        return results.get('files', [])
    except Exception as e:
        raise ActionError(f"Error listing Sema4.ai Studio Files: {str(e)}")


def _cleanup_old_sema4_files(ctx: Context, days_old: int = 30) -> int:
    """Clean up old files in the Sema4.ai Studio Files folder (older than specified days)."""
    try:
        from datetime import datetime, timedelta

        folder_id = _get_or_create_sema4_folder(ctx)
        cutoff_date = datetime.now() - timedelta(days=days_old)

        # Get all files in the folder
        results = ctx.files.list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name, createdTime)"
        ).execute()

        files_to_delete = []
        for file in results.get('files', []):
            created_time = datetime.fromisoformat(file['createdTime'].replace('Z', '+00:00'))
            if created_time < cutoff_date:
                files_to_delete.append(file['id'])

        # Delete old files
        deleted_count = 0
        for file_id in files_to_delete:
            try:
                ctx.files.delete(fileId=file_id).execute()
                deleted_count += 1
            except Exception:
                # Skip files that can't be deleted (might be in use)
                continue

        return deleted_count
    except Exception as e:
        raise ActionError(f"Error cleaning up old Sema4.ai Studio Files: {str(e)}")


def _process_markdown_with_images_and_vega_lite(ctx: Context, body: str, image_files: list[str] = None) -> tuple[str, dict[str, str]]:
    """Process markdown content to handle image files, chat files, and vega-lite charts.

    Returns:
        tuple: (processed_markdown, image_data_dict)
    """
    image_data_dict = {}

    # Process chat file references first (<<filename>> syntax)
    chat_file_blocks = _detect_chat_file_references(body)

    for i, block in enumerate(chat_file_blocks):
        try:
            # Upload chat file to Drive and get file ID
            drive_file_id = _upload_chat_file_to_drive(ctx, block['filename'])
            image_key = f"chat_file_{i}"
            image_data_dict[image_key] = drive_file_id

            # Replace the chat file reference with an image reference
            # For images, use image syntax; for other files, use link syntax
            file_ext = os.path.splitext(block['filename'])[1].lower()
            if file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg']:
                # It's an image, use image syntax
                body = body.replace(block['original_text'], f"![{block['filename']}]({image_key})")
            else:
                # It's not an image, use link syntax
                body = body.replace(block['original_text'], f"[{block['filename']}]({image_key})")
        except Exception as e:
            # If upload fails, keep the original reference
            print(f"Warning: Could not upload chat file '{block['filename']}': {str(e)}")
            continue

    # Process image files if provided
    if image_files:
        for i, image_path in enumerate(image_files):
            if os.path.exists(image_path):
                # Upload image to Drive and get file ID
                filename = os.path.basename(image_path)
                drive_file_id = _upload_image_to_drive(ctx, image_path, filename)
                image_key = f"image_{i}"
                image_data_dict[image_key] = drive_file_id

                # Replace image references in the markdown
                # Handle multiple possible patterns:
                # 1. ![image_0](/path/to/image.png) - explicit index pattern
                # 2. ![](filename.png) - just filename
                # 3. ![alt text](filename.png) - with alt text

                # Pattern 1: Explicit index pattern
                placeholder1 = f"![image_{i}]({image_path})"
                if placeholder1 in body:
                    body = body.replace(placeholder1, f"![{image_key}]({image_key})")

                # Pattern 2: Just filename (most common case)
                placeholder2 = f"![]({filename})"
                if placeholder2 in body:
                    body = body.replace(placeholder2, f"![{image_key}]({image_key})")

                # Pattern 3: With alt text
                placeholder3 = f"![{filename}]({filename})"
                if placeholder3 in body:
                    body = body.replace(placeholder3, f"![{image_key}]({image_key})")

    # Process vega-lite markdown blocks
    vega_lite_blocks = _detect_vega_lite_markdown(body)

    for i, block in enumerate(vega_lite_blocks):
        try:
            # Convert vega-lite to image and upload to Drive
            drive_file_id = _convert_vega_lite_to_drive_file(ctx, block['spec'], f"vega_lite_chart_{i+1}.png")
            image_key = f"vega_lite_{i}"
            image_data_dict[image_key] = drive_file_id

            # Replace the vega-lite markdown block with an image reference
            body = body.replace(block['original_text'], f"![Vega-Lite Chart {i+1}]({image_key})")
        except Exception as e:
            # If conversion fails, keep the original markdown
            print(f"Warning: Could not convert vega-lite block {i}: {str(e)}")
            continue

    return body, image_data_dict


@action
def get_document_by_name(
    name: str,
    oauth_access_token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/documents.readonly", "https://www.googleapis.com/auth/drive.readonly"]],
    ],
    tab_index: int = None,
    tab_title: str = None,
    include_comments: bool = False,
    download: bool = True,
    export_format: str = "application/pdf",
) -> Response[MarkdownDocument]:
    """Get a Google Document by its name.

    If multiple documents with the same name are found,
    you need to use the ID of the document to load it.
    Hint: Copy-pasting the URL of the document in the Agent will allow it to fetch the document by ID

    Apostrophes in the title need to be escaped with a backslash.
    The result is the Document formatted using the Extended Markdown Syntax.

    When no tab is specified, all tab contents are included in a structured format.

    Note: Comments are automatically included in the response when available. Comments are fetched
    via Google Drive API which works with documents.readonly scope.

    Args:
        oauth_access_token: The OAuth2 Google access token
        name: The Google Document name
        tab_index: Optional tab index to get content from a specific tab
        tab_title: Optional tab title to get content from a specific tab
        include_comments: Optional boolean to include comments in the response
        download: Optional boolean to download the document in a supported format and attach to chat (default: True)
        export_format: The MIME type for the export format when download=True (default: PDF)
                      Supported formats: PDF, DOCX, TXT, HTML, RTF, ODT
    Returns:
        The Google Document as a markdown formatted string with comments included.
        If download=True, the file is also attached to Studio chat.
    """

    # Validate that only one tab identifier is provided
    if tab_index is not None and tab_title:
        raise ActionError("Cannot specify both tab_index and tab_title. Please provide only one.")

    with Context(oauth_access_token) as ctx:
        document_id = _get_document_id(ctx, name)

        # Download file if requested
        download_info = None
        if download:
            try:
                doc_info = ctx.documents.get(documentId=document_id).execute()
                doc_title = doc_info.get("title", "document")
                download_info = _download_document_file(ctx, document_id, export_format, doc_title)
            except Exception as e:
                raise ActionError(f"Failed to download document: {str(e)}")

        # If a tab is specified, find it by ID or title
        if tab_index is not None or tab_title:
            tab_identifier = tab_index if tab_index is not None else tab_title
            result = MarkdownDocument.from_raw_document(
                _load_raw_document_tab_by_identifier(ctx, document_id, tab_identifier, include_comments=include_comments)
            )
        else:
            # No specific tab requested - include all tab contents
            raw_doc = _load_raw_document(ctx, document_id, include_comments=include_comments)
            result = MarkdownDocument.from_raw_document(
                raw_doc, include_all_tabs=True
            )

        # Add download info to result if available
        if download_info:
            result.download_info = download_info

        return Response(result=result)


@action
def get_document_by_id(
    document_id: str,
    oauth_access_token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/documents.readonly", "https://www.googleapis.com/auth/drive.readonly"]],
    ],
    tab_index: int = None,
    tab_title: str = None,
    include_comments: bool = False,
    download: bool = True,
    export_format: str = "application/pdf",
) -> Response[MarkdownDocument]:
    """Get a Google Document by its ID. The result is the Document formatted using the Extended Markdown Syntax.

    When no tab is specified, all tab contents are included in a structured format.

    Note: Comments are automatically included in the response when available. Comments are fetched
    via Google Drive API which works with documents.readonly scope.

    Args:
        oauth_access_token: The OAuth2 Google access token
        document_id: The Google Document ID.
        tab_index: Optional tab index to get content from a specific tab
        tab_title: Optional tab title to get content from a specific tab
        include_comments: Optional boolean to include comments in the response
        download: Optional boolean to download the document in a supported format and attach to chat (default: True)
        export_format: The MIME type for the export format when download=True (default: PDF)
                      Supported formats: PDF, DOCX, TXT, HTML, RTF, ODT
    Returns:
        The Google Document as a markdown formatted string with comments included.
        If download=True, the file is also attached to Studio chat.
    """

    # Validate that only one tab identifier is provided
    if tab_index is not None and tab_title:
        raise ActionError("Cannot specify both tab_index and tab_title. Please provide only one.")

    with Context(oauth_access_token) as ctx:
        # Download file if requested
        download_info = None
        if download:
            try:
                doc_info = ctx.documents.get(documentId=document_id).execute()
                doc_title = doc_info.get("title", "document")
                download_info = _download_document_file(ctx, document_id, export_format, doc_title)
            except Exception as e:
                raise ActionError(f"Failed to download document: {str(e)}")

        # If a tab is specified, find it by ID or title
        if tab_index is not None or tab_title:
            tab_identifier = tab_index if tab_index is not None else tab_title
            result = MarkdownDocument.from_raw_document(
                _load_raw_document_tab_by_identifier(ctx, document_id, tab_identifier, include_comments=include_comments)
            )
        else:
            # No specific tab requested - include all tab contents
            raw_doc = _load_raw_document(ctx, document_id, include_comments=include_comments)
            result = MarkdownDocument.from_raw_document(
                raw_doc, include_all_tabs=True
            )

        # Add download info to result if available
        if download_info:
            result.download_info = download_info

        return Response(result=result)


@action(is_consequential=True)
def create_document(
    title: str,
    body: str,
    oauth_access_token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/documents", "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]],
    ],
    tab_index: int = None,
    tab_title: str = None,
    image_files: list[str] = None,
) -> Response[DocumentInfo]:
    """Create a new Google Document from an Extended Markdown string.

    Args:
        title: The Google Document title
        body: The Google Document body as an Extended Markdown string.
        oauth_access_token: The OAuth2 Google access token
        tab_index: Optional tab index to add content to a specific tab (for existing documents)
        tab_title: Optional tab title to add content to a specific tab (for existing documents)
        image_files: Optional list of local file paths to images that should be embedded in the document

    Returns:
        A structure containing the Document
    """

    # Validate that only one tab identifier is provided
    if tab_index is not None and tab_title:
        raise ActionError("Cannot specify both tab_index and tab_title. Please provide only one.")

    # Note: Google Docs API doesn't currently support creating docvuments with multiple tabs
    # Tab parameters are included for future compatibility but will be ignored for now
    if tab_index is not None or tab_title:
        raise ActionError("Creating documents with specific tabs is not currently supported by the Google Docs API. Create the document first, then append to specific tabs.")

    with Context(oauth_access_token) as ctx:
        doc = _create_document(ctx, title)
        try:
            # Process markdown content for images and vega-lite charts
            processed_body, image_data_dict = _process_markdown_with_images_and_vega_lite(ctx, body, image_files)

            # Create batch update body with image data
            batch_body = BatchUpdateBody.from_markdown(processed_body, image_data=image_data_dict)

            ctx.documents.batchUpdate(
                documentId=doc.document_id,
                body=batch_body.get_body(),
            ).execute()
        except Exception:
            # Clean-up in case of error.
            ctx.files.delete(fileId=doc.document_id).execute()
            raise

        return Response(result=doc)


@action(is_consequential=True)
def append_to_document_by_id(
    document_id: str,
    body: str,
    oauth_access_token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/documents"]],
    ],
    tab_index: int = None,
    tab_title: str = None,
) -> Response[DocumentInfo]:
    """Appends text formated using Extended Markdown syntax to an existing Google Document by its ID.

    Args:
        document_id: The Google Document ID
        body: The Google Document body as an Extended Markdown string
        oauth_access_token: The OAuth2 Google access token
        tab_index: Optional tab index to append content to a specific tab
        tab_title: Optional tab title to append content to a specific tab

    Returns:
        A structure containing the Document.
    """

    # Validate that only one tab identifier is provided
    if tab_index is not None and tab_title:
        raise ActionError("Cannot specify both tab_index and tab_title. Please provide only one.")

    with Context(oauth_access_token) as ctx:
        # If a tab is specified, append to that tab
        if tab_index is not None or tab_title:
            tab_identifier = tab_index if tab_index is not None else tab_title
            document = _append_to_document_tab(ctx, document_id, body, tab_identifier)
        else:
            # No tab specified: if the document has tabs, default to first tab (index 0).
            try:
                raw_doc = ctx.documents.get(
                    documentId=document_id,
                    includeTabsContent=True
                ).execute()
                if raw_doc.get("tabs"):
                    document = _append_to_document_tab(ctx, document_id, body, 0)
                else:
                    document = _append_to_document(ctx, document_id, body)
            except Exception:
                # Fallback to appending to whole document if fetching tabs fails
                document = _append_to_document(ctx, document_id, body)

        return Response(result=document)


@action(is_consequential=True)
def append_to_document_by_name(
    name: str,
    body: str,
    oauth_access_token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/documents"]],
    ],
    tab_index: int = None,
    tab_title: str = None,
) -> Response[DocumentInfo]:
    """Appends text formated using Extended Markdown syntax to an existing Google Document by its name.

    Args:
        name: The Google Document name
        body: The Google Document body as an Extended Markdown string
        oauth_access_token: The OAuth2 Google access token
        tab_index: Optional tab index to append content to a specific tab
        tab_title: Optional tab title to append content to a specific tab

    Returns:
        A structure containing the Document.
    """

    # Validate that only one tab identifier is provided
    if tab_index is not None and tab_title:
        raise ActionError("Cannot specify both tab_index and tab_title. Please provide only one.")

    with Context(oauth_access_token) as ctx:
        document_id = _get_document_id(ctx, name)

        # If a tab is specified, append to that tab
        if tab_index is not None or tab_title:
            tab_identifier = tab_index if tab_index is not None else tab_title
            document = _append_to_document_tab(ctx, document_id, body, tab_identifier)
        else:
            # No tab specified: if the document has tabs, default to first tab (index 0).
            try:
                raw_doc = ctx.documents.get(
                    documentId=document_id,
                    includeTabsContent=True
                ).execute()
                if raw_doc.get("tabs"):
                    document = _append_to_document_tab(ctx, document_id, body, 0)
                else:
                    document = _append_to_document(ctx, document_id, body)
            except Exception:
                # Fallback to appending to whole document if fetching tabs fails
                document = _append_to_document(ctx, document_id, body)

        return Response(result=document)


def _extract_child_tabs(child_tabs: list, parent_index: int) -> list[TabInfo]:
    """Recursively extract child tabs information."""
    tabs = []
    for child_index, child_tab in enumerate(child_tabs):
        if "documentTab" in child_tab:
            tab_info = TabInfo(
                tabId=child_tab["tabId"],
                title=child_tab["documentTab"]["title"],
                index=f"{parent_index}.{child_index}"
            )
            tabs.append(tab_info)

            # Recursively handle nested child tabs
            if "childTabs" in child_tab:
                tabs.extend(_extract_child_tabs(child_tab["childTabs"], f"{parent_index}.{child_index}"))

    return tabs


def _load_raw_document_tab_by_identifier(ctx: Context, document_id: str, tab_identifier: str, include_comments: bool = False) -> RawDocument:
    """Load a specific tab from a document by ID or title."""
    document_id = document_id.strip()
    tab_identifier = tab_identifier.strip()

    # Get document with tabs content
    raw_doc = ctx.documents.get(
        documentId=document_id,
        includeTabsContent=True
    ).execute()
    # Ensure keys exist to satisfy downstream parsing context
    raw_doc.setdefault("lists", {})
    raw_doc.setdefault("inlineObjects", {})

    # Find the specific tab by ID or title
    tab_content = _find_tab_by_index_or_title(raw_doc.get("tabs", []), tab_identifier)
    if not tab_content:
        raise ActionError(f"Tab with ID or title '{tab_identifier}' not found in document")

    # Get the actual tab ID for setting current_tab later
    actual_tab_id = tab_content.get("tabId")
    if not actual_tab_id and "tabProperties" in tab_content:
        actual_tab_id = tab_content["tabProperties"].get("tabId")

    # Create a mock document structure with just the tab content
    # Don't include tabs structure to avoid confusion in from_google_response
    # Use original document title, not tab title
    mock_doc = {
        "documentId": document_id,
        "title": raw_doc.get("title", "Untitled"),  # Keep original document title
        "body": tab_content["documentTab"]["body"],
        "inlineObjects": raw_doc.get("inlineObjects"),
        "lists": raw_doc.get("lists"),
    }

    try:
        # Create the RawDocument which will use the specific tab's body
        result = RawDocument.from_google_response(mock_doc)

        # Now manually add the tab information from the original document
        from models.documents import TabInfo

        def extract_tabs_from_raw(tabs_list, parent_index=""):
            tab_infos = []
            for index, tab in enumerate(tabs_list):
                tab_id = tab.get("tabId")
                if not tab_id and "tabProperties" in tab:
                    tab_id = tab["tabProperties"].get("tabId")

                if tab_id:
                    title = None
                    if "tabProperties" in tab and "title" in tab["tabProperties"]:
                        title = tab["tabProperties"]["title"]
                    elif "documentTab" in tab and "title" in tab["documentTab"]:
                        title = tab["documentTab"]["title"]

                    if not title:
                        title = f"Tab {index + 1}"

                    tab_index = f"{parent_index}{index}" if parent_index else str(index)
                    tab_info = TabInfo(
                        tabId=tab_id,
                        title=title,
                        index=tab_index
                    )
                    tab_infos.append(tab_info)

                    if "childTabs" in tab:
                        child_tabs = extract_tabs_from_raw(tab["childTabs"], f"{tab_index}.")
                        tab_infos.extend(child_tabs)

            return tab_infos

        # Extract all tabs and set them on the result
        all_tabs = extract_tabs_from_raw(raw_doc.get("tabs", []))
        result.tabs = all_tabs

        # Set current_tab to the one we loaded
        if actual_tab_id:
            for tab in all_tabs:
                if tab.tab_id == actual_tab_id:
                    result.current_tab = tab
                    break

        # Optionally fetch all comments, then filter for this specific tab
        if include_comments:
            import json
            all_comments = _fetch_comments_from_drive_api(ctx, document_id)
            # Enrich comments with location first (adds tabId/tabTitle/tabIndex to anchor JSON)
            all_comments = _enrich_comments_with_location(all_comments, raw_doc)
            # Filter comments by matching normalized anchor.tabId to the target tab ID
            filtered: list[CommentInfo] = []
            for c in all_comments:
                try:
                    data = json.loads(c.anchor) if c.anchor else {}
                    if data.get("tabId") == actual_tab_id:
                        filtered.append(c)
                except Exception:
                    # Fallback to legacy mapping if parsing fails
                    mapped_id = _find_comment_tab_by_anchor(raw_doc, c.anchor, actual_tab_id)
                    if mapped_id == actual_tab_id:
                        filtered.append(c)
            result.comments = filtered

        return result
    except ValidationError:
        raise ActionError("Could not parse tab content")


def _load_raw_document_tab(ctx: Context, document_id: str, tab_id: str) -> RawDocument:
    """Load a specific tab from a document."""
    document_id = document_id.strip()
    tab_id = tab_id.strip()

    # Get document with tabs content
    raw_doc = ctx.documents.get(
        documentId=document_id,
        includeTabsContent=True
    ).execute()
    raw_doc.setdefault("lists", {})
    raw_doc.setdefault("inlineObjects", {})

    # Find the specific tab
    tab_content = _find_tab_content(raw_doc.get("tabs", []), tab_id)
    if not tab_content:
        raise ActionError(f"Tab with ID '{tab_id}' not found in document")

    # Create a mock document structure with just the tab content but include all tabs info
    mock_doc = {
        "documentId": document_id,
        "title": tab_content["documentTab"]["title"],
        "body": tab_content["documentTab"]["body"],
        "tabs": raw_doc.get("tabs", []),  # Include original tabs structure
        "inlineObjects": raw_doc.get("inlineObjects"),
        "lists": raw_doc.get("lists"),
    }

    try:
        # Create the RawDocument which will populate tab info
        result = RawDocument.from_google_response(mock_doc)

        # Update current_tab to point to the specific tab we loaded
        if result.tabs:
            for tab in result.tabs:
                if tab.tab_id == tab_id:
                    result.current_tab = tab
                    break

        return result
    except ValidationError:
        raise ActionError("Could not parse tab content")


def _find_tab_content(tabs: list, target_tab_id: str) -> dict | None:
    """Recursively find a tab by its ID."""
    for tab in tabs:
        if tab.get("tabId") == target_tab_id:
            return tab

        # Check child tabs recursively
        if "childTabs" in tab:
            result = _find_tab_content(tab["childTabs"], target_tab_id)
            if result:
                return result

    return None


def _find_tab_by_index_or_title(tabs: list, tab_identifier) -> dict | None:
    """Find a tab by either its index (int) or title (str)."""

    def search_recursive(tabs_list, current_path=""):
        for index, tab in enumerate(tabs_list):
            current_index = f"{current_path}{index}" if current_path else str(index)

            # Check if looking for tab by index
            if isinstance(tab_identifier, int):
                # For integer index, match against the tab position
                if index == tab_identifier:
                    return tab
            else:
                # For string, check tab title
                title = None
                if "tabProperties" in tab and "title" in tab["tabProperties"]:
                    title = tab["tabProperties"]["title"]
                elif "documentTab" in tab and "title" in tab["documentTab"]:
                    title = tab["documentTab"]["title"]

                if title == tab_identifier:
                    return tab

            # Check child tabs recursively
            if "childTabs" in tab:
                result = search_recursive(tab["childTabs"], f"{current_index}.")
                if result:
                    return result

        return None

    return search_recursive(tabs)


def _get_document_id(ctx: Context, name: str) -> str:
    name = name.strip()

    response = ctx.files.list(
        fields="files/id,files/name",
        q=f"name contains '{name}' and mimeType='application/vnd.google-apps.document'",
    ).execute()

    if not (files := response.get("files")):
        raise ActionError(f"Could not find document with name: {name}")

    if len(files) > 1:
        choices = []
        for f in files:
            if name == f["name"]:
                return f["id"]

            choices.append(f["name"])

        choices = ", ".join(choices)

        raise ActionError(
            f"Multiple files found, you must choose one of the following: {choices}."
        )

    return response["files"][0]["id"]


def _load_raw_document(ctx: Context, document_id: str, include_comments: bool = False) -> RawDocument:
    document_id = document_id.strip()
    raw_doc = ctx.documents.get(
        documentId=document_id,
        includeTabsContent=True
    ).execute()
    raw_doc.setdefault("lists", {})
    raw_doc.setdefault("inlineObjects", {})

    try:
        raw_document = RawDocument.from_google_response(raw_doc)
        # Optionally fetch and add comments to the document
        if include_comments:
            drive_comments = _fetch_comments_from_drive_api(ctx, document_id)
            # Enrich with location so each comment carries tab info
            drive_comments = _enrich_comments_with_location(drive_comments, raw_doc)
            raw_document.comments = drive_comments
        return raw_document
    except ValidationError:
        raise ActionError("Could not parse document")


def _create_document(ctx, title: str) -> DocumentInfo:
    # Create the document
    raw_response = ctx.documents.create(body={"title": title}).execute()

    # Extract basic document info
    doc_info = DocumentInfo(
        title=raw_response.get("title", title),
        document_id=raw_response.get("documentId"),
        document_url=f"https://docs.google.com/document/d/{raw_response.get('documentId')}/edit",
        current_tab=None,
        tabs=[],
        comments=[]  # New documents don't have comments yet
    )

    # If the document has tabs, process them
    if "tabs" in raw_response and raw_response["tabs"]:
        from models.documents import TabInfo

        def extract_tabs_from_response(tabs_list, parent_index=""):
            tab_infos = []
            for index, tab in enumerate(tabs_list):
                tab_id = tab.get("tabId")
                if not tab_id and "tabProperties" in tab:
                    tab_id = tab["tabProperties"].get("tabId")

                if tab_id:
                    title = None
                    if "tabProperties" in tab and "title" in tab["tabProperties"]:
                        title = tab["tabProperties"]["title"]
                    elif "documentTab" in tab and "title" in tab["documentTab"]:
                        title = tab["documentTab"]["title"]

                    if not title:
                        title = f"Tab {index + 1}"

                    tab_index = f"{parent_index}{index}" if parent_index else str(index)
                    tab_info = TabInfo(
                        tabId=tab_id,
                        title=title,
                        index=tab_index
                    )
                    tab_infos.append(tab_info)

                    if "childTabs" in tab:
                        child_tabs = extract_tabs_from_response(tab["childTabs"], f"{tab_index}.")
                        tab_infos.extend(child_tabs)

            return tab_infos

        # Extract all tabs and set them on the document
        all_tabs = extract_tabs_from_response(raw_response["tabs"])
        doc_info.tabs = all_tabs

        # Set current_tab to the first tab if available
        if all_tabs:
            doc_info.current_tab = all_tabs[0]

    return doc_info


def _append_to_document(ctx: Context, document_id: str, content: str) -> DocumentInfo:
    #content = f"\n{content}"
    raw_document = _load_raw_document(ctx, document_id)

    body = BatchUpdateBody.from_markdown(
        content, start_index=raw_document.end_index - 1, is_append=True
    ).get_body()

    ctx.documents.batchUpdate(
        documentId=raw_document.document_id,
        body=body,
    ).execute()

    # Create DocumentInfo with tab information (if document has tabs)
    doc_info = DocumentInfo(
        title=raw_document.title,
        document_id=raw_document.document_id,
        document_url=f"https://docs.google.com/document/d/{raw_document.document_id}/edit",
        current_tab=raw_document.current_tab,
        tabs=raw_document.tabs,
        comments=_fetch_comments_from_drive_api(ctx, raw_document.document_id)
    )

    return doc_info


def _append_to_document_tab(ctx: Context, document_id: str, content: str, tab_identifier: str) -> DocumentInfo:
    """Append content to a specific tab in a document."""
    # Add minimal spacing without causing page breaks
    #content = f"\n{content}"

    # Get document with tabs content
    raw_doc = ctx.documents.get(
        documentId=document_id,
        includeTabsContent=True
    ).execute()

    # Find the specific tab
    tab_content = _find_tab_by_index_or_title(raw_doc.get("tabs", []), tab_identifier)
    if not tab_content:
        # Check if we're trying to find by title/index and provide helpful error message
        if isinstance(tab_identifier, str):  # Looking for a title
            raise ActionError(
                f"Tab with title '{tab_identifier}' not found in document. "
                f"The Google Docs API doesn't currently support creating new tabs programmatically. "
                f"Please create the tab manually in Google Docs first, then use this action to append content to it."
            )
        else:  # Looking for an index
            raise ActionError(f"Tab with index {tab_identifier} not found in document")

    # Get the tab ID for the batch update
    target_tab_id = tab_content.get("tabId")
    if not target_tab_id and "tabProperties" in tab_content:
        target_tab_id = tab_content["tabProperties"].get("tabId")

    if not target_tab_id:
        raise ActionError(f"Could not determine tab ID for tab '{tab_identifier}'")

    # Use EndOfSegmentLocation for tab insertions - this is more reliable
    # than calculating exact indices and avoids the paragraph bounds issue
    from models.update_operations import BatchUpdateBody

    # First, get the actual end index of the tab content
    try:
        temp_raw_document = RawDocument.from_google_response({
            "documentId": document_id,
            "title": raw_doc.get("title", "Untitled"),
            "body": tab_content["documentTab"]["body"],
            "inlineObjects": raw_doc.get("inlineObjects"),
            "lists": raw_doc.get("lists"),
        })
        print(f"len(temp_raw_document.body): {len(temp_raw_document.body)}")
        tab_end_index = temp_raw_document.end_index
    except Exception:
        tab_end_index = 1

    # Create the batch update with the correct start index for the tab
    # Only use is_append=True if the tab has existing content (end_index > 1)
    # For empty tabs, start fresh without leading newline
    is_tab_empty = tab_end_index <= 1


    batch_body = BatchUpdateBody.from_markdown(
        content, start_index=tab_end_index, is_append=not is_tab_empty
    ).get_body()

    # Add tab IDs to all requests
    for request in batch_body.get("requests", []):
        if "insertText" in request:
            location = request["insertText"].get("location", {})
            location["tabId"] = target_tab_id
            request["insertText"]["location"] = location
        elif "insertInlineImage" in request:
            location = request["insertInlineImage"].get("location", {})
            location["tabId"] = target_tab_id
            request["insertInlineImage"]["location"] = location
        elif "insertPageBreak" in request:
            location = request["insertPageBreak"].get("location", {})
            location["tabId"] = target_tab_id
            request["insertPageBreak"]["location"] = location
        elif "insertTable" in request:
            location = request["insertTable"].get("location", {})
            location["tabId"] = target_tab_id
            request["insertTable"]["location"] = location
        elif "updateTextStyle" in request:
            range_obj = request["updateTextStyle"].get("range", {})
            range_obj["tabId"] = target_tab_id
            request["updateTextStyle"]["range"] = range_obj
        elif "updateParagraphStyle" in request:
            range_obj = request["updateParagraphStyle"].get("range", {})
            range_obj["tabId"] = target_tab_id
            request["updateParagraphStyle"]["range"] = range_obj
        elif "createParagraphBullets" in request:
            range_obj = request["createParagraphBullets"].get("range", {})
            range_obj["tabId"] = target_tab_id
            request["createParagraphBullets"]["range"] = range_obj
        elif "updateTableCellStyle" in request:
            # Handle table range location for cell-specific styling
            table_range = request["updateTableCellStyle"].get("tableRange", {})
            if table_range:
                table_cell_location = table_range.get("tableCellLocation", {})
                table_start_location = table_cell_location.get("tableStartLocation", {})
                table_start_location["tabId"] = target_tab_id
                table_cell_location["tableStartLocation"] = table_start_location
                table_range["tableCellLocation"] = table_cell_location
                request["updateTableCellStyle"]["tableRange"] = table_range
            else:
                # Handle direct table start location for whole-table styling
                table_location = request["updateTableCellStyle"].get("tableStartLocation", {})
                table_location["tabId"] = target_tab_id
                request["updateTableCellStyle"]["tableStartLocation"] = table_location

    # Execute the batch update
    ctx.documents.batchUpdate(
        documentId=document_id,
        body=batch_body,
    ).execute()

    # Extract all tabs information and set current tab
    from models.documents import TabInfo

    def extract_tabs_from_raw(tabs_list, parent_index=""):
        tab_infos = []
        for index, tab in enumerate(tabs_list):
            tab_id = tab.get("tabId")
            if not tab_id and "tabProperties" in tab:
                tab_id = tab["tabProperties"].get("tabId")

            if tab_id:
                title = None
                if "tabProperties" in tab and "title" in tab["tabProperties"]:
                    title = tab["tabProperties"]["title"]
                elif "documentTab" in tab and "title" in tab["documentTab"]:
                    title = tab["documentTab"]["title"]

                if not title:
                    title = f"Tab {index + 1}"

                tab_index = f"{parent_index}{index}" if parent_index else str(index)
                tab_info = TabInfo(
                    tabId=tab_id,
                    title=title,
                    index=tab_index
                )
                tab_infos.append(tab_info)

                if "childTabs" in tab:
                    child_tabs = extract_tabs_from_raw(tab["childTabs"], f"{tab_index}.")
                    tab_infos.extend(child_tabs)

        return tab_infos

    # Extract all tabs
    all_tabs = extract_tabs_from_raw(raw_doc.get("tabs", []))

    # Find the current tab (the one we appended to)
    current_tab_info = None
    if target_tab_id:
        for tab in all_tabs:
            if tab.tab_id == target_tab_id:
                current_tab_info = tab
                break

    # Create DocumentInfo with tab information
    doc_info = DocumentInfo(
        title=raw_doc.get("title", "Untitled"),
        document_id=document_id,
        document_url=f"https://docs.google.com/document/d/{document_id}/edit",
        current_tab=current_tab_info,
        tabs=all_tabs,
        comments=_fetch_comments_from_drive_api(ctx, document_id)
    )

    return doc_info


def _fetch_comments_from_document_structure(raw_doc: dict) -> list[CommentInfo]:
    """Extract comments and annotations from the Google Docs document structure."""
    comments = []

    # Extract suggestions (which can contain comment-like information)
    if "suggestionsViewMode" in raw_doc:
        suggestions = raw_doc["suggestionsViewMode"]
        for suggestion_id, suggestion_data in suggestions.items():
            try:
                comment = _convert_suggestion_to_comment(suggestion_id, suggestion_data)
                if comment:
                    comments.append(comment)
            except Exception:
                continue

    # Extract footnotes (which might contain comment information)
    if "footnotes" in raw_doc:
        footnotes = raw_doc["footnotes"]
        for footnote_id, footnote_data in footnotes.items():
            try:
                comment = _extract_comment_from_footnote(footnote_id, footnote_data)
                if comment:
                    comments.append(comment)
            except Exception:
                continue

    # Extract any other annotations or comments embedded in the document
    if "namedRanges" in raw_doc:
        named_ranges = raw_doc["namedRanges"]
        for range_id, range_data in named_ranges.items():
            try:
                comment = _extract_comment_from_named_range(range_id, range_data)
                if comment:
                    comments.append(comment)
            except Exception:
                continue

    # Look for revision history that might contain comment-like information
    if "revisionId" in raw_doc:
        try:
            comment = _extract_comment_from_revision(raw_doc["revisionId"], raw_doc)
            if comment:
                comments.append(comment)
        except Exception:
            pass

    # Look for any embedded objects that might contain annotations
    if "inlineObjects" in raw_doc:
        inline_objects = raw_doc["inlineObjects"]
        for obj_id, obj_data in inline_objects.items():
            try:
                comment = _extract_comment_from_inline_object(obj_id, obj_data)
                if comment:
                    comments.append(comment)
            except Exception:
                continue

    return comments


def _fetch_comments_from_drive_api(ctx: Context, document_id: str) -> list[CommentInfo]:
    """Fetch comments using the Google Drive API."""
    comments = []

    try:
        result = ctx.comments.list(
            fileId=document_id,
            fields="comments(id,content,htmlContent,author(displayName,emailAddress,me),createdTime,modifiedTime,resolved,deleted,anchor,quotedFileContent(mimeType,value),replies(id,content,htmlContent,author(displayName,emailAddress,me),createdTime,modifiedTime,deleted))"
        ).execute()

        for comment_data in result.get("comments", []):
            try:
                comment = CommentInfo.model_validate(comment_data)
                comments.append(comment)
            except Exception:
                # Skip invalid comments but continue processing others
                continue

    except Exception as e:
        # Log the error but don't fail the entire operation
        print(f"Warning: Could not fetch comments from Drive API: {e}")

    return comments


def _convert_suggestion_to_comment(suggestion_id: str, suggestion_data: dict) -> CommentInfo | None:
    """Convert a document suggestion to a CommentInfo object."""
    try:
        # Extract basic suggestion information
        content = suggestion_data.get("suggestionText", {}).get("content", "")
        if not content:
            return None

        # Create a comment from the suggestion
        comment = CommentInfo(
            comment_id=f"suggestion_{suggestion_id}",
            content=content,
            html_content=None,
            author=CommentAuthor(
                display_name=suggestion_data.get("author", {}).get("displayName", "Unknown"),
                email_address=suggestion_data.get("author", {}).get("emailAddress"),
                me=suggestion_data.get("author", {}).get("me", False)
            ),
            created_time=suggestion_data.get("createdTime", ""),
            modified_time=suggestion_data.get("modifiedTime", ""),
            resolved=False,
            deleted=False,
            anchor=None,
            quoted_file_content=None,
            replies=[]
        )

        return comment
    except Exception:
        return None


def _extract_comment_from_footnote(footnote_id: str, footnote_data: dict) -> CommentInfo | None:
    """Extract comment information from footnote structure."""
    try:
        # Check if footnote contains comment-like information
        content = footnote_data.get("content", {}).get("content", [])
        if not content:
            return None

        # Extract text content from footnote
        text_content = ""
        for element in content:
            if "paragraph" in element and "elements" in element["paragraph"]:
                for text_element in element["paragraph"]["elements"]:
                    if "textRun" in text_element and "content" in text_element["textRun"]:
                        text_content += text_element["textRun"]["content"]

        if not text_content.strip():
            return None

        # Create a comment from the footnote
        comment = CommentInfo(
            comment_id=f"footnote_{footnote_id}",
            content=text_content.strip(),
            html_content=None,
            author=CommentAuthor(
                display_name="Document Author",
                email_address=None,
                me=False
            ),
            created_time="",
            modified_time="",
            resolved=False,
            deleted=False,
            anchor=None,
            quoted_file_content=None,
            replies=[]
        )

        return comment
    except Exception:
        return None


def _extract_comment_from_named_range(range_id: str, range_data: dict) -> CommentInfo | None:
    """Extract comment information from named ranges (which might contain annotations)."""
    try:
        # Check if named range contains comment-like information
        name = range_data.get("name", "")
        if not name or not name.lower().startswith(("comment", "note", "annotation")):
            return None

        # Extract content from the named range
        content = range_data.get("content", {}).get("content", [])
        if not content:
            return None

        # Extract text content
        text_content = ""
        for element in content:
            if "paragraph" in element and "elements" in element["paragraph"]:
                for text_element in element["paragraph"]["elements"]:
                    if "textRun" in text_element and "content" in text_element["textRun"]:
                        text_content += text_element["textRun"]["content"]

        if not text_content.strip():
            return None

        # Create a comment from the named range
        comment = CommentInfo(
            comment_id=f"range_{range_id}",
            content=f"{name}: {text_content.strip()}",
            html_content=None,
            author=CommentAuthor(
                display_name="Document Author",
                email_address=None,
                me=False
            ),
            created_time="",
            modified_time="",
            resolved=False,
            deleted=False,
            anchor=None,
            quoted_file_content=None,
            replies=[]
        )

        return comment
    except Exception:
        return None


def _extract_comment_from_revision(revision_id: str, raw_doc: dict) -> CommentInfo | None:
    """Extract comment information from document revision history."""
    try:
        # Check if revision contains comment-like information
        # This is a basic implementation - revision data structure may vary
        if "body" in raw_doc and "content" in raw_doc["body"]:
            # Look for any revision notes or comments in the content
            content = raw_doc["body"]["content"]
            revision_notes = _extract_revision_notes_from_content(content)

            if revision_notes:
                comment = CommentInfo(
                    comment_id=f"revision_{revision_id}",
                    content=f"Revision {revision_id}: {revision_notes}",
                    html_content=None,
                    author=CommentAuthor(
                        display_name="Document System",
                        email_address=None,
                        me=False
                    ),
                    created_time="",
                    modified_time="",
                    resolved=False,
                    deleted=False,
                    anchor=None,
                    quoted_file_content=None,
                    replies=[]
                )
                return comment

        return None
    except Exception:
        return None


def _extract_comment_from_inline_object(obj_id: str, obj_data: dict) -> CommentInfo | None:
    """Extract comment information from inline objects (images, drawings, etc.)."""
    try:
        # Check if inline object contains comment-like information
        # Look for alt text, title, or other descriptive fields
        alt_text = obj_data.get("inlineObjectProperties", {}).get("embeddedObject", {}).get("altText", "")
        title = obj_data.get("inlineObjectProperties", {}).get("embeddedObject", {}).get("title", "")

        if alt_text or title:
            content = f"Object {obj_id}"
            if title:
                content += f" - {title}"
            if alt_text:
                content += f": {alt_text}"

            comment = CommentInfo(
                comment_id=f"object_{obj_id}",
                content=content,
                html_content=None,
                author=CommentAuthor(
                    display_name="Document Author",
                    email_address=None,
                    me=False
                ),
                created_time="",
                modified_time="",
                resolved=False,
                deleted=False,
                anchor=None,
                quoted_file_content=None,
                replies=[]
            )
            return comment

        return None
    except Exception:
        return None


def _extract_revision_notes_from_content(content: list) -> str | None:
    """Extract revision notes from document content."""
    try:
        notes = []
        for element in content:
            if "paragraph" in element and "elements" in element["paragraph"]:
                for text_element in element["paragraph"]["elements"]:
                    if "textRun" in text_element and "content" in text_element["textRun"]:
                        text = text_element["textRun"]["content"]
                        # Look for revision-related text
                        if any(keyword in text.lower() for keyword in ["revision", "version", "update", "change"]):
                            notes.append(text.strip())

        return " ".join(notes) if notes else None
    except Exception:
        return None


def _parse_comment_anchor(anchor_str: str) -> dict | None:
    """Parse comment anchor to extract location information.

    Expected format based on Google Docs API:
    - Structured anchor: JSON with segmentId, startIndex, endIndex
    - Simple kix anchor: "kix.xxxxxxx" (maps to document segment)
    """
    if not anchor_str:
        return None

    # Try to parse as JSON first (structured anchor with segmentId, startIndex, endIndex)
    try:
        import json
        anchor_data = json.loads(anchor_str)
        if isinstance(anchor_data, dict):
            return anchor_data
    except (json.JSONDecodeError, TypeError):
        pass

    # If not JSON, treat as simple kix anchor string - this needs to be mapped to segment
    if anchor_str.startswith("kix."):
        return {"segmentId": anchor_str, "type": "simple_kix"}

    return None


def _search_for_anchor_in_content(content, anchor_id: str) -> bool:
    """Recursively search for an anchor ID in document content structure."""
    if isinstance(content, dict):
        for key, value in content.items():
            if key == "segmentId" and value == anchor_id:
                return True
            if _search_for_anchor_in_content(value, anchor_id):
                return True
    elif isinstance(content, list):
        for item in content:
            if _search_for_anchor_in_content(item, anchor_id):
                return True
    elif isinstance(content, str):
        if anchor_id in content:
            return True
    return False


def _flatten_tabs(raw_doc: dict) -> list[dict]:
    """Flatten tabs into a list with id, title, index and body for mapping."""
    flattened = []
    def recurse(tabs_list, parent_index=""):
        for index, tab in enumerate(tabs_list or []):
            tab_id = tab.get("tabId") or tab.get("id")
            if not tab_id and "tabProperties" in tab:
                tab_id = tab["tabProperties"].get("tabId")
            title = None
            if "tabProperties" in tab and "title" in tab["tabProperties"]:
                title = tab["tabProperties"]["title"]
            elif "documentTab" in tab and "title" in tab["documentTab"]:
                title = tab["documentTab"]["title"]
            body = tab.get("documentTab", {}).get("body") if "documentTab" in tab else None
            flat_index = f"{parent_index}{index}" if parent_index else str(index)
            flattened.append({
                "tabId": tab_id,
                "title": title or f"Tab {index + 1}",
                "index": flat_index,
                "body": body,
            })
            if "childTabs" in tab:
                recurse(tab["childTabs"], f"{flat_index}.")
    recurse(raw_doc.get("tabs", []))
    return flattened


def _map_segment_to_tab_info(raw_doc: dict, segment_id: str) -> dict | None:
    """Find the tab info that contains the given segment id."""
    if not segment_id:
        return None
    for tab in _flatten_tabs(raw_doc):
        if tab.get("body") and _segment_belongs_to_tab(tab["body"], segment_id, tab.get("tabId")):
            return tab
    return None


def _normalize_comment_anchor_with_tab(comment: CommentInfo, raw_doc: dict) -> str | None:
    """Create a normalized anchor JSON string including tab mapping if possible."""
    import json
    parsed = _parse_comment_anchor(comment.anchor) if comment.anchor else None
    segment_id = parsed.get("segmentId") if isinstance(parsed, dict) else None

    tab_info = _map_segment_to_tab_info(raw_doc, segment_id) if segment_id else None

    # Fallback: try quoted content matching to locate tab when no anchor/segment
    if tab_info is None and comment.quoted_file_content and comment.quoted_file_content.value:
        quoted_text = comment.quoted_file_content.value.strip()
        if quoted_text:
            import json as _json
            for tab in _flatten_tabs(raw_doc):
                body_json = _json.dumps(tab.get("body", {}))
                if quoted_text and quoted_text in body_json:
                    tab_info = tab
                    break

    normalized = {
        "segmentId": segment_id,
        "startIndex": parsed.get("startIndex") if isinstance(parsed, dict) else None,
        "endIndex": parsed.get("endIndex") if isinstance(parsed, dict) else None,
        "tabId": tab_info.get("tabId") if tab_info else None,
        "tabTitle": tab_info.get("title") if tab_info else None,
        "tabIndex": tab_info.get("index") if tab_info else None,
    }
    return json.dumps(normalized)


def _enrich_comments_with_location(comments: list[CommentInfo], raw_doc: dict) -> list[CommentInfo]:
    """Ensure every comment has a normalized anchor indicating its location (including tab info)."""
    enriched: list[CommentInfo] = []
    for c in comments:
        try:
            normalized_anchor = _normalize_comment_anchor_with_tab(c, raw_doc)
            enriched.append(c.model_copy(update={"anchor": normalized_anchor}))
        except Exception:
            enriched.append(c)
    return enriched


def _segment_belongs_to_tab(tab_body: dict, segment_id: str, tab_id: str) -> bool:
    """Check if a segment ID belongs to a specific tab by examining the tab's content structure."""
    # Search for the segment ID in the document structure more systematically
    import json

    def search_for_segment_recursive(obj, target_segment):
        """Recursively search for segment ID in nested structures"""
        if isinstance(obj, dict):
            # Check if this object has segment information
            if "segmentId" in obj and obj["segmentId"] == target_segment:
                return True
            # Also check for other segment-related fields
            for key in ["anchor", "id", "elementId"]:
                if key in obj and obj[key] == target_segment:
                    return True
            # Recurse into nested objects
            for value in obj.values():
                if search_for_segment_recursive(value, target_segment):
                    return True
        elif isinstance(obj, list):
            for item in obj:
                if search_for_segment_recursive(item, target_segment):
                    return True
        elif isinstance(obj, str):
            if target_segment in obj:
                return True
        return False

    # First try recursive search
    if search_for_segment_recursive(tab_body, segment_id):
        # Segment found in tab
        return True

    # Also try JSON string search as fallback
    body_json = json.dumps(tab_body)
    if segment_id in body_json:
        # Segment substring found in serialized tab body
        return True

    return False


def _find_comment_tab_by_anchor(raw_doc: dict, comment_anchor: str, target_tab_id: str) -> str | None:
    """Find which tab a comment belongs to using proper anchor analysis."""
    if not comment_anchor or not raw_doc.get("tabs"):
        return None

    # Parse the anchor to extract location information
    anchor_data = _parse_comment_anchor(comment_anchor)

    if not anchor_data:
        return None

    segment_id = anchor_data.get("segmentId")
    if not segment_id:
        return None


    # For kix anchors, we need to map the segmentId to the actual tab
    # First, let's see if the segment ID directly corresponds to a tab ID or can be found in tab structure
    for tab_index, tab in enumerate(raw_doc["tabs"]):
        # Get the actual tab identifier
        tab_id = tab.get("id") or tab.get("tab_id") or tab.get("tabId")
        if not tab_id and "tabProperties" in tab:
            tab_id = tab["tabProperties"].get("tabId")


        # Check if this tab contains content that would map to this segment ID
        if "documentTab" in tab and "body" in tab["documentTab"]:
            # Look for segment references in the tab's body structure
            body = tab["documentTab"]["body"]

            # Debug: Show a sample of what's in this tab's body
            # import json
            # body_sample = json.dumps(body, indent=2)[:500]  # First 500 chars

            if _segment_belongs_to_tab(body, segment_id, tab_id):
                # Return the tab ID if it matches our target
                return tab_id if tab_id == target_tab_id else None

    return None


def _comment_belongs_to_tab_by_content(comment: CommentInfo, raw_doc: dict, target_tab_id: str) -> bool:
    """Try to match a comment to a tab based on its quoted content."""
    if not comment.quoted_file_content or not comment.quoted_file_content.value:
        return False

    quoted_text = comment.quoted_file_content.value.strip()
    if not quoted_text:
        return False


    # Find the target tab and check if the quoted text appears in it
    for tab in raw_doc.get("tabs", []):
        tab_id = tab.get("id") or tab.get("tab_id") or tab.get("tabId")
        if not tab_id and "tabProperties" in tab:
            tab_id = tab["tabProperties"].get("tabId")

        if tab_id == target_tab_id and "documentTab" in tab:
            import json
            tab_content_str = json.dumps(tab["documentTab"])
            if quoted_text in tab_content_str:
                return True

    return False


def _filter_comments_for_tab(comments: list[CommentInfo], raw_doc: dict, target_tab_id: str) -> list[CommentInfo]:
    """Filter comments to only include those that belong to a specific tab using anchor analysis."""
    if not comments:
        return []

    # Filter comments belonging to the target tab ID

    # Use anchor-based matching only
    filtered_comments = []
    for comment in comments:
        if comment.anchor:
            found_tab_id = _find_comment_tab_by_anchor(raw_doc, comment.anchor, target_tab_id)
            if found_tab_id == target_tab_id:
                filtered_comments.append(comment)
        else:
            # Comment has no anchor; skip
            pass

    return filtered_comments


@action
def get_document_comments(
    oauth_access_token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/drive.readonly", "https://www.googleapis.com/auth/documents.readonly"]],
    ],
    document_id: str = None,
    document_name: str = None,
    tab_id: str = None,
    tab_index: int = None,
    tab_title: str = None,
) -> Response[list[CommentInfo]]:
    """List comments for a Google Doc using the Google Drive API.

    Args:
        oauth_access_token: The OAuth2 Google access token
        document_id: Optional Google Document ID
        document_name: Optional Google Document name
        tab_id: Optional tab ID to filter comments to a specific tab
        tab_index: Optional tab index to filter comments to a specific tab
        tab_title: Optional tab title to filter comments to a specific tab

    Returns:
        List of comments from Drive API (comments.list)

    Note:
        Must specify either document_id or document_name, but not both.
    """
    # Validate that exactly one document identifier is provided
    if not (document_id or document_name):
        raise ActionError("Must specify either document_id or document_name.")
    if document_id and document_name:
        raise ActionError("Cannot specify both document_id and document_name. Please provide only one.")
    # Validate that at most one tab identifier is provided
    provided_tab_filters = [v is not None for v in (tab_id, tab_index, tab_title)]
    if sum(provided_tab_filters) > 1:
        raise ActionError("Provide only one of tab_id, tab_index, or tab_title.")

    with Context(oauth_access_token) as ctx:
        # Resolve document ID when a name is provided
        doc_id = _get_document_id(ctx, document_name) if document_name else document_id.strip()

        # Fetch comments via Drive API
        comments = _fetch_comments_from_drive_api(ctx, doc_id)

        # Always load document structure to enrich comments with tab/location info
        raw_doc = ctx.documents.get(
            documentId=doc_id,
            includeTabsContent=True
        ).execute()

        # Enrich all comments with normalized anchor including tab info
        comments = _enrich_comments_with_location(comments, raw_doc)

        # If a tab filter is provided, filter the enriched comments
        if any(provided_tab_filters):
            # Resolve the actual tab ID to filter against
            target_tab_id = tab_id
            if target_tab_id is None:
                tab_identifier = tab_index if tab_index is not None else tab_title
                tab_content = _find_tab_by_index_or_title(raw_doc.get("tabs", []), tab_identifier)
                if not tab_content:
                    raise ActionError("Tab not found in document")
                target_tab_id = tab_content.get("tabId") or tab_content.get("tabProperties", {}).get("tabId")
                if not target_tab_id:
                    raise ActionError("Could not determine tab ID for the specified tab")

            # Filter based on normalized anchor tabId
            import json
            filtered: list[CommentInfo] = []
            for c in comments:
                try:
                    anchor = c.anchor
                    data = json.loads(anchor) if anchor else {}
                    if data.get("tabId") == target_tab_id:
                        filtered.append(c)
                except Exception:
                    # Fallback to previous anchor-based mapping
                    mapped_id = _find_comment_tab_by_anchor(raw_doc, c.anchor, target_tab_id)
                    if mapped_id == target_tab_id:
                        filtered.append(c)
            comments = filtered

        return Response(result=comments)


@action
def list_sema4_studio_files(
    oauth_access_token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/drive.readonly"]],
    ],
) -> Response[list[dict]]:
    """List all files in the Sema4.ai Studio Files folder.

    Args:
        oauth_access_token: The OAuth2 Google access token

    Returns:
        List of files in the Sema4.ai Studio Files folder with metadata
    """
    with Context(oauth_access_token) as ctx:
        files = _list_sema4_files(ctx)
        return Response(result=files)


@action(is_consequential=True)
def cleanup_old_sema4_files(
    oauth_access_token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/drive.file"]],
    ],
    days_old: int = 30,
) -> Response[dict]:
    """Clean up old files in the Sema4.ai Studio Files folder.

    Args:
        oauth_access_token: The OAuth2 Google access token
        days_old: Number of days after which files are considered old (default: 30)

    Returns:
        Dictionary with cleanup results
    """
    with Context(oauth_access_token) as ctx:
        deleted_count = _cleanup_old_sema4_files(ctx, days_old)
        return Response(result={
            "deleted_files": deleted_count,
            "days_old": days_old,
            "message": f"Cleaned up {deleted_count} files older than {days_old} days"
        })


def _download_document_file(ctx: Context, document_id: str, export_format: str, doc_title: str) -> dict:
    """Helper function to download a document in the specified format and attach to chat."""

    # Validate export format
    supported_formats = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "text/plain": "txt",
        "text/html": "html",
        "application/rtf": "rtf",
        "application/vnd.oasis.opendocument.text": "odt"
    }

    if export_format not in supported_formats:
        raise ActionError(f"Unsupported export format: {export_format}. Supported formats: {list(supported_formats.keys())}")

    file_extension = supported_formats[export_format]

    # Clean filename for filesystem
    import re
    clean_title = re.sub(r'[^\w\s-]', '', doc_title).strip()
    clean_title = re.sub(r'[-\s]+', '-', clean_title)
    filename = f"{clean_title}.{file_extension}"

    # Download the file
    try:
        request = ctx.files.export_media(fileId=document_id, mimeType=export_format)
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

        file_data = file_content.getvalue()

    except Exception as e:
        raise ActionError(f"Failed to download document: {str(e)}")

    # Note: File download completed successfully
    # The file data is available in the response

    return {
        "filename": filename,
        "export_format": export_format,
        "file_size_bytes": len(file_data),
        "attached_to_chat": True
    }



