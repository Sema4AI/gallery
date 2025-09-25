from datetime import datetime, timedelta, timezone
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

from models.documents import CommentAuthor, CommentInfo, DocumentInfo, MarkdownDocument, RawDocument, SearchResult, TabInfo
from models.update_operations import BatchUpdateBody


class Context:
    def __init__(self, secret: OAuth2Secret):
        self._secret = secret
        self._docs = None
        self._drive = None

    @property
    def documents(self) -> Resource:
        self._docs = build(
            "docs", "v1", credentials=Credentials(token=self._secret.access_token)
        )
        return self._docs.documents()

    @property
    def files(self) -> Resource:
        self._drive = build(
            "drive", "v3", credentials=Credentials(token=self._secret.access_token)
        )
        return self._drive.files()

    @property
    def comments(self) -> Resource:
        self._drive = build(
            "drive", "v3", credentials=Credentials(token=self._secret.access_token)
        )

        return self._drive.comments()

    @property
    def permissions(self) -> Resource:
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
    """Get or create the '.sema4ai-document-assets' folder in Google Drive."""
    folder_name = ".sema4ai-document-assets"

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
        raise ActionError(f"Error creating/accessing .sema4ai-document-assets folder: {str(e)}")


def _upload_image_to_drive(ctx: Context, file_path: str, filename: str = None) -> str:
    """Upload an image file to the .sema4ai-document-assets folder in Google Drive."""
    try:
        if not os.path.exists(file_path):
            raise ActionError(f"Image file not found: {file_path}")

        if filename is None:
            filename = os.path.basename(file_path)

        # Get or create the .sema4ai-document-assets folder
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
            'parents': [folder_id]  # Upload to .sema4ai-document-assets folder
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
    """Upload a chat file to the .sema4ai-document-assets folder in Google Drive."""
    try:
        # Get the chat file content
        file_content = chat.get_file_content(filename)
        if not file_content:
            raise ActionError(f"Chat file '{filename}' not found or empty")

        # Get or create the .sema4ai-document-assets folder
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
            'parents': [folder_id]  # Upload to .sema4ai-document-assets folder
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
    """Convert a vega-lite specification to a PNG image and upload to .sema4ai-document-assets folder."""
    try:
        import vl_convert as vlc

        if filename is None:
            filename = f"vega_lite_chart_{hash(str(vega_lite_spec)) % 10000}.png"

        # Get or create the .sema4ai-document-assets folder
        folder_id = _get_or_create_sema4_folder(ctx)

        # Convert vega-lite spec to PNG
        png_data = vlc.vegalite_to_png(vl_spec=vega_lite_spec, scale=2)

        # Create file metadata
        file_metadata = {
            'name': filename,
            'parents': [folder_id]  # Upload to .sema4ai-document-assets folder
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
    """List all files in the .sema4ai-document-assets folder."""
    try:
        folder_id = _get_or_create_sema4_folder(ctx)

        results = ctx.files.list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name, createdTime, size, mimeType)"
        ).execute()

        return results.get('files', [])
    except Exception as e:
        raise ActionError(f"Error listing .sema4ai-document-assets: {str(e)}")


def _cleanup_old_sema4_files(ctx: Context, days_old: int = 30) -> int:
    """Clean up old files in the .sema4ai-document-assets folder (older than specified days)."""
    try:
        from datetime import datetime, timedelta, timezone

        folder_id = _get_or_create_sema4_folder(ctx)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

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
        raise ActionError(f"Error cleaning up old .sema4ai-document-assets: {str(e)}")


def _delete_drive_files(ctx: Context, file_ids: list[str]) -> int:
    """Delete specific files from Google Drive by their IDs.

    Args:
        ctx: The context object with Google Drive API access
        file_ids: List of file IDs to delete

    Returns:
        Number of files successfully deleted
    """
    deleted_count = 0
    for file_id in file_ids:
        try:
            ctx.files.delete(fileId=file_id).execute()
            deleted_count += 1
        except Exception as e:
            print(f"Warning: Could not delete file {file_id}: {str(e)}")
            continue
    return deleted_count


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
        If download=True, the file is also attached to chat.
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
        If download=True, the file is also attached to chat.
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

            # Clean up uploaded images after successful embedding
            if image_data_dict:
                file_ids_to_delete = list(image_data_dict.values())
                deleted_count = _delete_drive_files(ctx, file_ids_to_delete)
                print(f"Cleaned up {deleted_count} uploaded image files after embedding")

        except Exception:
            # Clean-up in case of error.
            ctx.files.delete(fileId=doc.document_id).execute()
            raise

        return Response(result=doc)


@action(is_consequential=True)
def insert_content_to_document_by_id(
    document_id: str,
    body: str,
    oauth_access_token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/documents"]],
    ],
    position: Literal["prepend", "append"] = "append",
    tab_index: int = None,
    tab_title: str = None,
) -> Response[DocumentInfo]:
    """Inserts text formatted using Extended Markdown syntax into an existing Google Document by its ID.

    Args:
        document_id: The Google Document ID
        body: The Google Document body as an Extended Markdown string
        oauth_access_token: The OAuth2 Google access token
        position: Whether to prepend (insert at beginning) or append (insert at end) content
        tab_index: Optional tab index to insert content into a specific tab
        tab_title: Optional tab title to insert content into a specific tab

    Returns:
        A structure containing the Document.
    """

    # Validate that only one tab identifier is provided
    if tab_index is not None and tab_title:
        raise ActionError("Cannot specify both tab_index and tab_title. Please provide only one.")

    with Context(oauth_access_token) as ctx:
        # If a tab is specified, insert into that tab
        if tab_index is not None or tab_title:
            tab_identifier = tab_index if tab_index is not None else tab_title
            document = _insert_content_to_document_tab(ctx, document_id, body, tab_identifier, position)
        else:
            # No tab specified: if the document has tabs, default to first tab (index 0).
            try:
                raw_doc = ctx.documents.get(
                    documentId=document_id,
                    includeTabsContent=True
                ).execute()
                if raw_doc.get("tabs"):
                    document = _insert_content_to_document_tab(ctx, document_id, body, 0, position)
                else:
                    document = _insert_content_to_document(ctx, document_id, body, position)
            except Exception:
                # Fallback to inserting into whole document if fetching tabs fails
                document = _insert_content_to_document(ctx, document_id, body, position)

        return Response(result=document)


@action(is_consequential=True)
def insert_content_to_document_by_name(
    name: str,
    body: str,
    oauth_access_token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/documents"]],
    ],
    position: Literal["prepend", "append"] = "append",
    tab_index: int = None,
    tab_title: str = None,
) -> Response[DocumentInfo]:
    """Inserts text formatted using Extended Markdown syntax into an existing Google Document by its name.

    Args:
        name: The Google Document name
        body: The Google Document body as an Extended Markdown string
        oauth_access_token: The OAuth2 Google access token
        position: Whether to prepend (insert at beginning) or append (insert at end) content
        tab_index: Optional tab index to insert content into a specific tab
        tab_title: Optional tab title to insert content into a specific tab

    Returns:
        A structure containing the Document.
    """

    # Validate that only one tab identifier is provided
    if tab_index is not None and tab_title:
        raise ActionError("Cannot specify both tab_index and tab_title. Please provide only one.")

    with Context(oauth_access_token) as ctx:
        document_id = _get_document_id(ctx, name)

        # If a tab is specified, insert into that tab
        if tab_index is not None or tab_title:
            tab_identifier = tab_index if tab_index is not None else tab_title
            document = _insert_content_to_document_tab(ctx, document_id, body, tab_identifier, position)
        else:
            # No tab specified: if the document has tabs, default to first tab (index 0).
            try:
                raw_doc = ctx.documents.get(
                    documentId=document_id,
                    includeTabsContent=True
                ).execute()
                if raw_doc.get("tabs"):
                    document = _insert_content_to_document_tab(ctx, document_id, body, 0, position)
                else:
                    document = _insert_content_to_document(ctx, document_id, body, position)
            except Exception:
                # Fallback to inserting into whole document if fetching tabs fails
                document = _insert_content_to_document(ctx, document_id, body, position)

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


def _insert_content_to_document(ctx: Context, document_id: str, content: str, position: str) -> DocumentInfo:
    raw_document = _load_raw_document(ctx, document_id)

    # Process markdown content for images and vega-lite charts
    processed_content, image_data_dict = _process_markdown_with_images_and_vega_lite(ctx, content)

    # Use different approaches for prepend vs append
    if position == "prepend":
        # For prepend, insert at the very beginning
        body = BatchUpdateBody.from_markdown(
            processed_content, start_index=1, is_append=False, image_data=image_data_dict
        ).get_body()
    else:  # position == "append"
        # For append, use the document end with proper spacing
        body = BatchUpdateBody.from_markdown(
            processed_content, start_index=raw_document.end_index - 1, is_append=True, image_data=image_data_dict
        ).get_body()

    ctx.documents.batchUpdate(
        documentId=raw_document.document_id,
        body=body,
    ).execute()

    # Clean up uploaded images after successful embedding
    if image_data_dict:
        file_ids_to_delete = list(image_data_dict.values())
        deleted_count = _delete_drive_files(ctx, file_ids_to_delete)
        print(f"Cleaned up {deleted_count} uploaded image files after embedding")

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


def _insert_content_to_document_tab(ctx: Context, document_id: str, content: str, tab_identifier: str, position: str) -> DocumentInfo:
    """Insert content into a specific tab in a document."""

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

    # Process markdown content for images and vega-lite charts
    processed_content, image_data_dict = _process_markdown_with_images_and_vega_lite(ctx, content)

    # Use the proper document loading approach to get the accurate end index
    actual_end_index = None
    try:
        # Load the complete document using the same method as other functions
        raw_document = _load_raw_document(ctx, document_id)
        actual_end_index = raw_document.end_index
    except Exception as e:
        # Fallback to estimated positioning if document loading fails
        tab_body = tab_content["documentTab"]["body"]
        tab_content_length = 1  # Default for empty tab

        if tab_body and "content" in tab_body:
            content_elements = tab_body.get("content", [])
            if content_elements:
                # Find the maximum endIndex across all elements
                max_end_index = 0
                for element in content_elements:
                    if "endIndex" in element:
                        max_end_index = max(max_end_index, element["endIndex"])

                if max_end_index > 0:
                    tab_content_length = max_end_index
                else:
                    # Fallback to last element analysis
                    last_element = content_elements[-1]
                    if "startIndex" in last_element:
                        tab_content_length = last_element["startIndex"] + 1

        actual_end_index = tab_content_length

    # For tab operations, use proper positioning logic
    if position == "prepend":
        # For prepend, insert at the very beginning of the tab
        batch_body = BatchUpdateBody.from_markdown(
            processed_content, start_index=1, is_append=False, image_data=image_data_dict
        ).get_body()
    else:  # position == "append"
        # For append, we need to insert before the last character (usually a newline)
        # Google Docs API requires insertion index to be strictly less than end index
        append_index = max(1, actual_end_index - 1)
        batch_body = BatchUpdateBody.from_markdown(
            processed_content, start_index=append_index, is_append=True, image_data=image_data_dict
        ).get_body()

    # Add tab IDs to all requests
    for i, request in enumerate(batch_body.get("requests", [])):
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

    # Clean up uploaded images after successful embedding
    if image_data_dict:
        file_ids_to_delete = list(image_data_dict.values())
        deleted_count = _delete_drive_files(ctx, file_ids_to_delete)
        print(f"Cleaned up {deleted_count} uploaded image files after embedding")

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
def list_sema4_files(
    oauth_access_token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/drive.readonly"]],
    ],
) -> Response[list[dict]]:
    """List all files in the .sema4ai-document-assets Google Drive folder.

    Args:
        oauth_access_token: The OAuth2 Google access token

    Returns:
        List of files in the .sema4ai-document-assets folder with metadata
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
    """Clean up old files in the .sema4ai-document-assets Google Drive folder.

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
        chat.attach_file_content(name=filename, data=file_data)

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


@action
def search_documents(
    search_query: str,
    oauth_access_token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/drive.readonly", "https://www.googleapis.com/auth/documents.readonly"]],
    ],
    max_results: int = 10,
    search_content: bool = False,
    search_metadata: bool = True,
) -> Response[list[SearchResult]]:
    """Search Google Documents using fuzzy matching on names, content, and metadata.

    This action performs an enhanced search across Google Documents in your Drive with multiple search strategies:

    SEARCH STRATEGIES:
    1. Document names (always enabled) - Uses fuzzy matching for approximate name searches
    2. Document content (optional) - Searches within document text content
    3. Metadata (optional) - Searches owner names and document descriptions
    4. Native Google Drive search - Uses Google's built-in fullText search for exact matches

    PARAMETER USAGE GUIDE:

    search_query examples:
    - "project report" - Finds docs with similar names like "Project Status Report", "Final Project Report"
    - "meeting notes" - Matches "Meeting Notes", "Team Meeting Minutes", etc.
    - "analytics dashboard" - Finds documents containing these terms in name or content
    - "john" - Finds documents owned by users named John (when search_metadata=True)
    - "quarterly revenue" - Searches for this phrase in content (when search_content=True)

    search_content parameter:
    - False (default, faster): Only searches names, metadata, and uses Google's native search
    - True (slower): Also searches within document content for comprehensive results
    - Use True when looking for specific content/phrases inside documents

    search_metadata parameter:
    - True (default): Searches document owners, descriptions, and other metadata
    - False: Skip metadata search for faster results
    - Useful for finding documents by author ("docs by sarah") or description keywords

    TIME-BASED SEARCHES:
    Note: This action does NOT filter by dates. For recent documents, use broad search terms
    and check the returned 'modified_time' field. Google Drive API doesn't support
    date range queries in this action.

    PERFORMANCE TIPS:
    - Start with search_content=False for faster results
    - Use search_content=True when you need to find specific phrases inside documents
    - Increase max_results if you need more comprehensive results
    - Use specific keywords rather than full sentences for better matches

    Args:
        search_query: Search terms to match against documents (supports fuzzy matching)
        oauth_access_token: The OAuth2 Google access token
        max_results: Maximum number of results to return (default: 10, max: 50)
        search_content: Whether to search within document content (slower but more comprehensive)
        search_metadata: Whether to search in metadata like owner names and descriptions

    Returns:
        List of SearchResult objects with document info, similarity scores, and match reasons, sorted by relevance
    """

    if max_results > 50:
        max_results = 50

    with Context(oauth_access_token) as ctx:
        try:
            # Start with Google Drive API native search for better initial filtering
            base_query = "mimeType='application/vnd.google-apps.document' and trashed=false"

            # Try to use Google Drive's native text search first (if query looks searchable)
            if len(search_query.strip()) > 2 and not search_content:
                # Google Drive can search in names and some content natively
                drive_query = f"{base_query} and (name contains '{search_query}' or fullText contains '{search_query}')"
                try:
                    results = ctx.files.list(
                        q=drive_query,
                        fields="files(id,name,createdTime,modifiedTime,owners,webViewLink,description,size)",
                        pageSize=min(100, max_results * 5)
                    ).execute()

                    # If native search returns results, prioritize them
                    native_files = results.get('files', [])
                except:
                    # Fallback to basic query if native search fails
                    native_files = []
            else:
                native_files = []

            # Always do a broader search for fuzzy matching
            results = ctx.files.list(
                q=base_query,
                fields="files(id,name,createdTime,modifiedTime,owners,webViewLink,description,size)",
                pageSize=min(1000, max_results * 10)
            ).execute()

            files = results.get('files', [])

            # Combine native search results with broader results, avoiding duplicates
            native_ids = {f['id'] for f in native_files}
            all_files = native_files + [f for f in files if f['id'] not in native_ids]

            if not all_files:
                return Response(result=[])

            # Perform enhanced matching
            search_results = []
            search_query_lower = search_query.lower()

            for file in all_files:
                file_name = file.get('name', '')
                file_name_lower = file_name.lower()
                owners = file.get('owners', [])
                description = file.get('description', '') or ''

                # Calculate base similarity score from name
                name_score = _calculate_fuzzy_score(search_query_lower, file_name_lower)

                # Boost score if found via native search
                if file['id'] in native_ids:
                    name_score = max(name_score, 0.7)  # Ensure native matches get good scores

                total_score = name_score
                match_reasons = []

                if name_score > 0:
                    match_reasons.append(f"name ({name_score:.2f})")

                # Search metadata if enabled
                if search_metadata:
                    metadata_score = 0

                    # Search in owner names
                    for owner in owners:
                        owner_name = owner.get('displayName', owner.get('emailAddress', '')).lower()
                        owner_score = _calculate_fuzzy_score(search_query_lower, owner_name)
                        if owner_score > metadata_score:
                            metadata_score = owner_score
                            if owner_score > 0.3:
                                match_reasons.append(f"owner ({owner_score:.2f})")

                    # Search in description
                    if description:
                        desc_score = _calculate_fuzzy_score(search_query_lower, description.lower())
                        if desc_score > metadata_score:
                            metadata_score = desc_score
                            if desc_score > 0.3:
                                match_reasons.append(f"description ({desc_score:.2f})")

                    # Add metadata score to total (weighted lower than name)
                    total_score = max(total_score, metadata_score * 0.6)

                content_preview = ""

                # Search content if enabled (expensive operation)
                if search_content and total_score < 0.8:  # Only search content if not already high scoring
                    try:
                        # Get document content for searching
                        doc_data = ctx.documents.get(documentId=file['id']).execute()
                        content = _extract_text_from_document(doc_data)
                        content_lower = content.lower()

                        # Search in content
                        content_score = _calculate_content_score(search_query_lower, content_lower)
                        if content_score > 0:
                            total_score = max(total_score, content_score * 0.8)
                            match_reasons.append(f"content ({content_score:.2f})")

                            # Extract a preview snippet around the match
                            content_preview = _extract_content_preview(content, search_query, max_length=200)

                    except Exception as e:
                        # Content search failed, continue with other matches
                        print(f"Warning: Could not search content in document {file['id']}: {str(e)}")

                # Only include if there's some similarity
                if total_score > 0:
                    result_item = SearchResult(
                        document_id=file['id'],
                        name=file_name,
                        similarity_score=round(total_score, 3),
                        match_reasons=match_reasons,
                        created_time=file.get('createdTime'),
                        modified_time=file.get('modifiedTime'),
                        owners=[owner.get('displayName', owner.get('emailAddress', '')) for owner in owners],
                        web_view_link=file.get('webViewLink'),
                        document_url=f"https://docs.google.com/document/d/{file['id']}/edit",
                        description=description,
                        content_preview=content_preview
                    )

                    search_results.append(result_item)

            # Sort by similarity score (descending) and limit results
            search_results.sort(key=lambda x: x.similarity_score, reverse=True)
            search_results = search_results[:max_results]

            return Response(result=search_results)

        except Exception as e:
            raise ActionError(f"Error searching documents: {str(e)}")


def _calculate_fuzzy_score(query: str, text: str) -> float:
    """Calculate fuzzy matching score between query and text.

    Returns a score between 0 and 1, where 1 is a perfect match.
    Uses multiple scoring methods and returns the highest score.
    """
    if not query or not text:
        return 0.0

    # Exact match gets highest score
    if query == text:
        return 1.0

    # Substring match
    if query in text:
        return 0.8 + (0.2 * (len(query) / len(text)))

    # Word boundary matches
    words_in_text = text.split()
    words_in_query = query.split()

    # Check if all query words appear in text
    query_words_found = sum(1 for qw in words_in_query if any(qw in tw for tw in words_in_text))
    if query_words_found == len(words_in_query):
        return 0.6 + (0.2 * (query_words_found / len(words_in_text)))

    # Character-based similarity using simple edit distance approximation
    char_score = _simple_similarity(query, text)
    if char_score > 0.3:  # Only return if reasonably similar
        return char_score * 0.5  # Scale down character-based matches

    return 0.0


def _simple_similarity(s1: str, s2: str) -> float:
    """Simple character-based similarity scoring."""
    if not s1 or not s2:
        return 0.0

    # Calculate Jaccard similarity using character bigrams
    def get_bigrams(s):
        return set(s[i:i+2] for i in range(len(s)-1))

    bigrams1 = get_bigrams(s1)
    bigrams2 = get_bigrams(s2)

    if not bigrams1 and not bigrams2:
        return 1.0
    if not bigrams1 or not bigrams2:
        return 0.0

    intersection = len(bigrams1.intersection(bigrams2))
    union = len(bigrams1.union(bigrams2))

    return intersection / union if union > 0 else 0.0


def _extract_text_from_document(doc_data: dict) -> str:
    """Extract plain text content from Google Docs document data."""
    try:
        content = doc_data.get('body', {}).get('content', [])
        text_parts = []

        def extract_text_from_element(element):
            if 'paragraph' in element:
                paragraph = element['paragraph']
                for elem in paragraph.get('elements', []):
                    if 'textRun' in elem:
                        text_parts.append(elem['textRun'].get('content', ''))
            elif 'table' in element:
                table = element['table']
                for row in table.get('tableRows', []):
                    for cell in row.get('tableCells', []):
                        for cell_elem in cell.get('content', []):
                            extract_text_from_element(cell_elem)

        for element in content:
            extract_text_from_element(element)

        return ''.join(text_parts)
    except Exception:
        return ""


def _calculate_content_score(query: str, content: str) -> float:
    """Calculate similarity score for content search."""
    if not query or not content:
        return 0.0

    # Look for exact phrase matches in content
    if query in content:
        # Higher score for shorter content (more relevant)
        relevance_factor = min(1.0, 1000 / len(content)) if len(content) > 0 else 0
        return 0.9 * (0.5 + 0.5 * relevance_factor)

    # Look for individual words
    query_words = query.split()
    if len(query_words) > 1:
        words_found = sum(1 for word in query_words if word in content)
        if words_found > 0:
            word_score = words_found / len(query_words)
            relevance_factor = min(1.0, 1000 / len(content)) if len(content) > 0 else 0
            return word_score * 0.7 * (0.3 + 0.7 * relevance_factor)

    return 0.0


def _extract_content_preview(content: str, search_query: str, max_length: int = 200) -> str:
    """Extract a preview snippet around the search match."""
    if not content or not search_query:
        return ""

    content_lower = content.lower()
    query_lower = search_query.lower()

    # Find the first occurrence of the search term
    match_pos = content_lower.find(query_lower)
    if match_pos == -1:
        # Try to find individual words
        words = search_query.split()
        for word in words:
            match_pos = content_lower.find(word.lower())
            if match_pos != -1:
                break

    if match_pos == -1:
        # No match found, return beginning of content
        return content[:max_length].strip() + ("..." if len(content) > max_length else "")

    # Extract context around the match
    start = max(0, match_pos - max_length // 3)
    end = min(len(content), match_pos + max_length * 2 // 3)

    preview = content[start:end].strip()

    # Add ellipsis if we're not at the beginning/end
    if start > 0:
        preview = "..." + preview
    if end < len(content):
        preview = preview + "..."

    return preview


@action
def list_recent_documents(
    oauth_access_token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/drive.readonly"]],
    ],
    days: int = 7,
    max_results: int = 20,
) -> Response[list[SearchResult]]:
    """List recently modified Google Documents.

    This action finds Google Documents that have been modified within the specified time period.
    Use this when you need to find documents you've worked on recently, rather than searching by content.

    USAGE EXAMPLES:
    - "documents I updated today" -> days=1
    - "docs modified this week" -> days=7
    - "recent work documents" -> days=7 or days=14
    - "files I changed yesterday" -> days=2

    Args:
        oauth_access_token: The OAuth2 Google access token
        days: Number of days to look back for modifications (default: 7)
        max_results: Maximum number of results to return (default: 20, max: 100)

    Returns:
        List of SearchResult objects for recently modified documents, sorted by modification time (newest first)
    """

    if max_results > 100:
        max_results = 100

    with Context(oauth_access_token) as ctx:
        try:
            # Calculate the date threshold
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            cutoff_str = cutoff_date.isoformat().replace('+00:00', 'Z')

            # Query for recently modified Google Docs
            query = f"mimeType='application/vnd.google-apps.document' and trashed=false and modifiedTime > '{cutoff_str}'"

            results = ctx.files.list(
                q=query,
                fields="files(id,name,createdTime,modifiedTime,owners,webViewLink,description,size)",
                pageSize=min(1000, max_results * 2),  # Get extra in case some fail
                orderBy='modifiedTime desc'  # Sort by modification time, newest first
            ).execute()

            files = results.get('files', [])

            if not files:
                return Response(result=[])

            # Convert to SearchResult objects
            search_results = []

            for file in files[:max_results]:
                owners = file.get('owners', [])

                result_item = SearchResult(
                    document_id=file['id'],
                    name=file.get('name', ''),
                    similarity_score=1.0,  # All results are equally "relevant" for time-based search
                    match_reasons=[f"modified within {days} days"],
                    created_time=file.get('createdTime'),
                    modified_time=file.get('modifiedTime'),
                    owners=[owner.get('displayName', owner.get('emailAddress', '')) for owner in owners],
                    web_view_link=file.get('webViewLink'),
                    document_url=f"https://docs.google.com/document/d/{file['id']}/edit",
                    description=file.get('description'),
                    content_preview=None
                )

                search_results.append(result_item)

            return Response(result=search_results)

        except Exception as e:
            raise ActionError(f"Error listing recent documents: {str(e)}")





