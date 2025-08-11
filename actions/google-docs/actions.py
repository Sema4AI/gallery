from typing import Literal

from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError as GoogleApiHttpError
from pydantic import ValidationError
from sema4ai.actions import (
    ActionError,
    OAuth2Secret,
    Response,
    action,
)
from typing_extensions import Self

from models.documents import DocumentInfo, MarkdownDocument, RawDocument, TabInfo
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


@action
def get_document_by_name(
    name: str,
    oauth_access_token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/drive.readonly"]],
    ],
    tab_index: int = None,
    tab_title: str = None,
) -> Response[MarkdownDocument]:
    """Get a Google Document by its name.

    If multiple documents with the same name are found,
    you need to use the ID of the document to load it.
    Hint: Copy-pasting the URL of the document in the Agent will allow it to fetch the document by ID

    Apostrophes in the title need to be escaped with a backslash.
    The result is the Document formatted using the Extended Markdown Syntax.

    When no tab is specified, all tab contents are included in a structured format.

    Args:
        oauth_access_token: The OAuth2 Google access token
        name: The Google Document name
        tab_index: Optional tab index to get content from a specific tab
        tab_title: Optional tab title to get content from a specific tab
    Returns:
        The Google Document as a markdown formatted string.
    """

    # Validate that only one tab identifier is provided
    if tab_index is not None and tab_title:
        raise ActionError("Cannot specify both tab_index and tab_title. Please provide only one.")

    with Context(oauth_access_token) as ctx:
        document_id = _get_document_id(ctx, name)

        # If a tab is specified, find it by ID or title
        if tab_index is not None or tab_title:
            tab_identifier = tab_index if tab_index is not None else tab_title
            return Response(
                result=MarkdownDocument.from_raw_document(
                    _load_raw_document_tab_by_identifier(ctx, document_id, tab_identifier)
                )
            )
        else:
            # No specific tab requested - include all tab contents
            raw_doc = _load_raw_document(ctx, document_id)
            return Response(
                result=MarkdownDocument.from_raw_document(
                    raw_doc, include_all_tabs=True
                )
            )


@action
def get_document_by_id(
    document_id: str,
    oauth_access_token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/documents.readonly"]],
    ],
    tab_index: int = None,
    tab_title: str = None,
) -> Response[MarkdownDocument]:
    """Get a Google Document by its ID. The result is the Document formatted using the Extended Markdown Syntax.

    When no tab is specified, all tab contents are included in a structured format.

    Args:
        oauth_access_token: The OAuth2 Google access token
        document_id: The Google Document ID.
        tab_index: Optional tab index to get content from a specific tab
        tab_title: Optional tab title to get content from a specific tab
    Returns:
        The Google Document as a markdown formatted string.
    """

    # Validate that only one tab identifier is provided
    if tab_index is not None and tab_title:
        raise ActionError("Cannot specify both tab_index and tab_title. Please provide only one.")

    with Context(oauth_access_token) as ctx:
        # If a tab is specified, find it by ID or title
        if tab_index is not None or tab_title:
            tab_identifier = tab_index if tab_index is not None else tab_title
            return Response(
                result=MarkdownDocument.from_raw_document(
                    _load_raw_document_tab_by_identifier(ctx, document_id, tab_identifier)
                )
            )
        else:
            # No specific tab requested - include all tab contents
            raw_doc = _load_raw_document(ctx, document_id)
            return Response(
                result=MarkdownDocument.from_raw_document(
                    raw_doc, include_all_tabs=True
                )
            )


@action(is_consequential=True)
def create_document(
    title: str,
    body: str,
    oauth_access_token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/documents"]],
    ],
    tab_index: int = None,
    tab_title: str = None,
) -> Response[DocumentInfo]:
    """Create a new Google Document from an Extended Markdown string.

    Args:
        title: The Google Document title
        body: The Google Document body as an Extended Markdown string.
        oauth_access_token: The OAuth2 Google access token
        tab_index: Optional tab index to add content to a specific tab (for existing documents)
        tab_title: Optional tab title to add content to a specific tab (for existing documents)

    Returns:
        A structure containing the Document
    """

    # Validate that only one tab identifier is provided
    if tab_index is not None and tab_title:
        raise ActionError("Cannot specify both tab_index and tab_title. Please provide only one.")

    # Note: Google Docs API doesn't currently support creating documents with multiple tabs
    # Tab parameters are included for future compatibility but will be ignored for now
    if tab_index is not None or tab_title:
        raise ActionError("Creating documents with specific tabs is not currently supported by the Google Docs API. Create the document first, then append to specific tabs.")

    with Context(oauth_access_token) as ctx:
        doc = _create_document(ctx, title)
        try:
            ctx.documents.batchUpdate(
                documentId=doc.document_id,
                body=BatchUpdateBody.from_markdown(body).get_body(),
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
            document = _append_to_document(ctx, document_id, body)

        return Response(result=document)


@action(is_consequential=True)
def append_to_document_by_name(
    name: str,
    body: str,
    oauth_access_token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/documents"]],
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
            document = _append_to_document(ctx, document_id, body)

        return Response(result=document)


@action
def list_document_tabs(
    oauth_access_token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/documents.readonly"]],
    ],
    document_id: str = None,
    document_name: str = None,
) -> Response[list[TabInfo]]:
    """List all tabs in a Google Document.

    Args:
        oauth_access_token: The OAuth2 Google access token
        document_id: Optional Google Document ID
        document_name: Optional Google Document name

    Returns:
        List of tabs in the document with their IDs, titles, and positions
    """

    # Validate that exactly one document identifier is provided
    if not (document_id or document_name):
        raise ActionError("Must specify either document_id or document_name.")
    if document_id and document_name:
        raise ActionError("Cannot specify both document_id and document_name. Please provide only one.")

    with Context(oauth_access_token) as ctx:
        # Get document ID if name was provided
        if document_name:
            doc_id = _get_document_id(ctx, document_name)
        else:
            doc_id = document_id.strip()

        # Get document with tabs content included
        raw_doc = ctx.documents.get(
            documentId=doc_id,
            includeTabsContent=True  # Need tab content to get proper structure
        ).execute()

        tabs = []
        if "tabs" in raw_doc:
            # Use the same extraction logic as other tab functions
            def extract_all_tabs(tabs_list, parent_index=""):
                tab_infos = []
                for index, tab in enumerate(tabs_list):
                    tab_id = tab.get("tabId")
                    if not tab_id and "tabProperties" in tab:
                        tab_id = tab["tabProperties"].get("tabId")

                    if tab_id:
                        # Get tab title
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

                        # Handle nested child tabs recursively
                        if "childTabs" in tab:
                            child_tabs = extract_all_tabs(tab["childTabs"], f"{tab_index}.")
                            tab_infos.extend(child_tabs)

                return tab_infos

            tabs = extract_all_tabs(raw_doc["tabs"])

        return Response(result=tabs)


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


def _load_raw_document_tab_by_identifier(ctx: Context, document_id: str, tab_identifier: str) -> RawDocument:
    """Load a specific tab from a document by ID or title."""
    document_id = document_id.strip()
    tab_identifier = tab_identifier.strip()

    # Get document with tabs content
    raw_doc = ctx.documents.get(
        documentId=document_id,
        includeTabsContent=True
    ).execute()

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


def _load_raw_document(ctx: Context, document_id: str) -> RawDocument:
    document_id = document_id.strip()
    raw_doc = ctx.documents.get(
        documentId=document_id,
        includeTabsContent=True
    ).execute()

    try:
        return RawDocument.from_google_response(raw_doc)
    except ValidationError:
        raise ActionError("Could not parse document")


def _create_document(ctx, title: str) -> DocumentInfo:
    # Create the document
    raw_response = ctx.documents.create(body={"title": title}).execute()

    # Extract basic document info
    doc_info = DocumentInfo(
        title=raw_response.get("title", title),
        document_id=raw_response.get("documentId"),
        current_tab=None,
        tabs=[]
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
    content = f"\n{content}"
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
        current_tab=raw_document.current_tab,
        tabs=raw_document.tabs
    )

    return doc_info


def _append_to_document_tab(ctx: Context, document_id: str, content: str, tab_identifier: str) -> DocumentInfo:
    """Append content to a specific tab in a document."""
    content = f"\n{content}"

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

    # Create a temporary RawDocument from the tab to get the end index
    mock_doc = {
        "documentId": document_id,
        "title": raw_doc.get("title", "Untitled"),
        "body": tab_content["documentTab"]["body"],
        "inlineObjects": raw_doc.get("inlineObjects"),
        "lists": raw_doc.get("lists"),
    }

    try:
        temp_raw_document = RawDocument.from_google_response(mock_doc)
        end_index = temp_raw_document.end_index
    except ValidationError:
        raise ActionError("Could not parse tab content for appending")

    # Create batch update body with tab-specific location
    batch_body = BatchUpdateBody.from_markdown(
        content, start_index=end_index - 1, is_append=True
    ).get_body()

    # Add tab ID to all requests in the batch update
    for request in batch_body.get("requests", []):
        if "insertText" in request:
            location = request["insertText"].get("location", {})
            location["tabId"] = target_tab_id
            request["insertText"]["location"] = location
        elif "insertInlineImage" in request:
            location = request["insertInlineImage"].get("location", {})
            location["tabId"] = target_tab_id
            request["insertInlineImage"]["location"] = location
        # Add other request types as needed

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
        current_tab=current_tab_info,
        tabs=all_tabs
    )

    return doc_info
