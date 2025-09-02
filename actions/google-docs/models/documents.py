import itertools
from abc import ABC, abstractmethod
from typing import Annotated, Any, Iterable, Union
from uuid import uuid4

from pydantic import AliasPath, BaseModel, Field, Tag, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo
from typing_extensions import Self


class _MarkdownContext:
    def __init__(self):
        self._lists_counter = {}

    def get_next_list_index(self, list_id: str, nesting_level: int) -> int:
        key = (list_id, nesting_level)
        try:
            counter = self._lists_counter[key]
        except KeyError:
            counter = self._lists_counter[key] = itertools.count(1)

        return next(counter)


class _OrderedListId(str):
    pass


class _UnorderedListId(str):
    pass


class _DocumentOperationsMixin(ABC):
    @abstractmethod
    def to_markdown(self, ctx: _MarkdownContext) -> str:
        raise NotImplementedError(f"{self.__class__}.to_markdown()")


class _BaseStructuralElement(BaseModel, extra="ignore"):
    start_index: Annotated[int | None, Field(validation_alias="startIndex")] = None
    end_index: Annotated[int | None, Field(validation_alias="endIndex")] = None


class _TextStyleLink(BaseModel):
    url: str


class TextStyle(BaseModel, extra="ignore"):
    bold: bool = False
    italic: bool = False
    strikethrough: bool = False
    link: _TextStyleLink | None = None

    @classmethod
    def new_link(cls, url: str):
        return TextStyle(link=_TextStyleLink(url=url))


class _TextElementBase(_BaseStructuralElement, extra="ignore"):
    text: Annotated[str, Field(validation_alias=AliasPath("textRun", "content"))] = None
    link: Annotated[
        str, Field(validation_alias=AliasPath("link", "textStyle", "link"))
    ] = None
    text_style: Annotated[
        TextStyle,
        Field(
            validation_alias=AliasPath("textRun", "textStyle"),
            default_factory=lambda: TextStyle(),
        ),
    ]

    def to_markdown(self, ctx: _MarkdownContext) -> str:
        if self.text is None:
            return ""

        if self.link:
            text = f"[{self.text}]({self.link})"
        else:
            text = self.text

        if self.text_style.bold:
            return f"**{text}**"

        if self.text_style.italic:
            return f"*{text}*"

        if self.text_style.strikethrough:
            return f"~~{text}~~"

        return self.text


class _ImageElementBase(_BaseStructuralElement, extra="ignore"):
    image_url: Annotated[
        str, Field(validation_alias=AliasPath("inlineObjectElement", "inlineObjectId"))
    ]
    title: str = None

    @field_validator("image_url", mode="after")
    def get_image_url(cls, value: str, info: ValidationInfo) -> str:
        context = info.context or {}
        inline_objects = context.get("inline_objects") or {}

        obj = inline_objects.get(value)
        if not obj:
            # No inline object metadata; return the raw id to avoid failing parse
            return value

        props = obj.get("inlineObjectProperties", {})
        embedded = props.get("embeddedObject", {})
        content_uri = None
        if isinstance(embedded, dict):
            content_uri = (
                embedded.get("imageProperties", {}).get("contentUri")
                or embedded.get("embeddedDrawingProperties", {}).get("contentUri")
            )
        return content_uri or value

    def to_markdown(self, ctx: _MarkdownContext) -> str:
        return f"![{self.title or f'Image {uuid4()}'}]({self.image_url})"


class _ParagraphData(
    _BaseStructuralElement, extra="ignore", arbitrary_types_allowed=True
):
    elements: list[_TextElementBase | _ImageElementBase]
    style: Annotated[
        str, Field(validation_alias=AliasPath("paragraphStyle", "namedStyleType"))
    ] = None

    nesting_level: Annotated[
        int, Field(validation_alias=AliasPath("bullet", "nestingLevel"))
    ] = 0
    list_id: Annotated[
        _UnorderedListId | _OrderedListId | None,
        Field(validation_alias=AliasPath("bullet", "listId")),
    ] = None

    @field_validator("list_id", mode="before")
    def populate_list_id(cls, value: str, info: ValidationInfo) -> str | None:
        # Be resilient: missing lists context or unknown list ids should not fail parsing
        context = info.context or {}
        lists_ctx = context.get("lists") or {}

        list_properties = lists_ctx.get(value)
        if not list_properties:
            # Treat as normal text when list metadata is unavailable
            return None

        try:
            nesting_level = info.data.get("nesting_level", 0)
            nesting_levels = list_properties.get("listProperties", {}).get("nestingLevels", [])
            nesting_level_info = nesting_levels[nesting_level]
        except Exception:
            # Incomplete list metadata; treat as normal text
            return None

        # Determine list id type without pattern matching for broader compatibility
        if isinstance(nesting_level_info, dict):
            if "glyphSymbol" in nesting_level_info:
                return _UnorderedListId(value)
            if "glyphType" in nesting_level_info:
                return _OrderedListId(value)
        # Can't determine list type; treat as normal text
        return None

    def to_markdown(self, ctx: _MarkdownContext) -> str:
        body = "".join(e.to_markdown(ctx) for e in self.elements)

        if self.list_id:
            spacing = " " * (self.nesting_level * 2)
            if isinstance(self.list_id, _OrderedListId):
                i = ctx.get_next_list_index(str(self.list_id), self.nesting_level)
                return f"{spacing}{i}. {body}"
            elif isinstance(self.list_id, _UnorderedListId):
                return f"{spacing}* {body}"
            else:
                raise ValueError(f"Invalid list id type: {self.list_id:r}")

        elif self.style and self.style.startswith("HEADING_"):
            if not body.strip():
                # Don't add an empty header"
                return ""

            header_number = int(self.style.split("_", 1)[-1])
            return f"{'#' * header_number} {body}"

        return body


class _Paragraph(_BaseStructuralElement):
    paragraph: _ParagraphData

    def to_markdown(self, ctx: _MarkdownContext) -> str:
        return self.paragraph.to_markdown(ctx)


class _SectionBreak(_BaseStructuralElement):
    section_break: Annotated[bool, Field(validation_alias="sectionBreak")]

    @model_validator(mode="before")
    @classmethod
    def populate_section_break(cls, v):
        if "sectionBreak" in v:
            v["sectionBreak"] = True

        return v

    def to_markdown(self, _ctx: _MarkdownContext) -> str:
        return "\n---\n"


class _TableData(_BaseStructuralElement):
    rows: int = 0
    columns: int = 0
    cells: list[list["_Content"]]

    @model_validator(mode="before")
    @classmethod
    def populate_cells(cls, data: Any) -> Any:
        cells = []
        for table_row in data["tableRows"]:
            rows = []
            cells.append(rows)
            for table_cell in table_row["tableCells"]:
                rows.append(table_cell)

        data["cells"] = cells
        return data

    def to_markdown(self, ctx: _MarkdownContext) -> str:
        rows = iter(self.cells)

        if (table_header := next(rows, None)) is None:
            return ""

        # We assume first rows are table header as per markdown specification.
        body = self._build_row(t.to_markdown(ctx).strip() for t in table_header)
        # Header separator
        body += self._build_row("---" for _ in range(self.columns))

        for row in rows:
            body += self._build_row(cell.to_markdown(ctx).strip() for cell in row)

        return body

    @staticmethod
    def _build_row(items: Iterable[str]) -> str:
        row = "|".join(items)
        return f"|{row}|\n"


class _Table(_BaseStructuralElement):
    table: _TableData

    def to_markdown(self, ctx: _MarkdownContext) -> str:
        return self.table.to_markdown(ctx)


class _TableOfContents(_BaseStructuralElement):
    table_of_contents: Annotated["_Content", Field(validation_alias="tableOfContents")]

    def to_markdown(self, ctx: _MarkdownContext) -> str:
        return self.table_of_contents.to_markdown(ctx)


_StructuralElement = Union[
    Annotated[_Paragraph, Tag("paragraph")],
    Annotated[_Table, Tag("table")],
    Annotated[_TableOfContents, Tag("table_of_contents")],
    Annotated[_SectionBreak, Tag("section_break")],
]


class _Content(BaseModel, extra="ignore"):
    content: Annotated[
        list[_StructuralElement],
        Field(
            description="Content is a list of structural elements of the document. ",
            # discriminator=Discriminator(_resolve_structural_elements),
        ),
    ]

    def to_markdown(self, ctx: _MarkdownContext) -> str:
        return "\n".join(c.to_markdown(ctx) for c in self.content)


class TabInfo(BaseModel, extra="ignore", populate_by_name=True):
    """Information about a document tab."""
    tab_id: Annotated[str, Field(description="The ID of the tab.", validation_alias="tabId")]
    title: Annotated[str, Field(description="The title of the tab.")]
    index: Annotated[int, Field(description="The position of the tab.")]


class CommentAuthor(BaseModel, extra="ignore", populate_by_name=True):
    """Information about a comment author."""
    display_name: Annotated[str, Field(description="The display name of the author.", validation_alias="displayName")]
    email_address: Annotated[str | None, Field(description="The email address of the author.", validation_alias="emailAddress", default=None)]
    me: Annotated[bool, Field(description="Whether this user is the requesting user.", default=False)]


class CommentQuotedContent(BaseModel, extra="ignore", populate_by_name=True):
    """Quoted file content in a comment."""
    mime_type: Annotated[str, Field(description="The MIME type of the quoted content.", validation_alias="mimeType")]
    value: Annotated[str, Field(description="The quoted content value.")]


class CommentReply(BaseModel, extra="ignore", populate_by_name=True):
    """A reply to a comment."""
    reply_id: Annotated[str, Field(description="The ID of the reply.", validation_alias="id")]
    content: Annotated[str, Field(description="The plain text content of the reply.")]
    html_content: Annotated[str | None, Field(description="The HTML content of the reply.", validation_alias="htmlContent", default=None)]
    author: Annotated[CommentAuthor, Field(description="The author of the reply.")]
    created_time: Annotated[str, Field(description="The time when the reply was created.", validation_alias="createdTime")]
    modified_time: Annotated[str, Field(description="The time when the reply was last modified.", validation_alias="modifiedTime")]
    deleted: Annotated[bool, Field(description="Whether the reply has been deleted.", default=False)]


class CommentInfo(BaseModel, extra="ignore", populate_by_name=True):
    """Information about a document comment."""
    comment_id: Annotated[str, Field(description="The ID of the comment.", validation_alias="id")]
    content: Annotated[str, Field(description="The plain text content of the comment.")]
    html_content: Annotated[str | None, Field(description="The HTML content of the comment.", validation_alias="htmlContent", default=None)]
    author: Annotated[CommentAuthor, Field(description="The author of the comment.")]
    created_time: Annotated[str, Field(description="The time when the comment was created.", validation_alias="createdTime")]
    modified_time: Annotated[str, Field(description="The time when the comment was last modified.", validation_alias="modifiedTime")]
    resolved: Annotated[bool, Field(description="Whether the comment has been resolved.", default=False)]
    deleted: Annotated[bool, Field(description="Whether the comment has been deleted.", default=False)]
    anchor: Annotated[str | None, Field(description="The document region as JSON string.", default=None)]
    quoted_file_content: Annotated[CommentQuotedContent | None, Field(description="The quoted file content.", validation_alias="quotedFileContent", default=None)]
    replies: Annotated[list[CommentReply], Field(description="List of replies to the comment.", default_factory=list)]


class DocumentInfo(BaseModel, extra="ignore", populate_by_name=True):
    # Model used to structure the action response.
    title: Annotated[str, Field(description="The title of the document.")]
    document_id: Annotated[
        str,
        Field(
            description="The ID of the document.",
            validation_alias="documentId",
        ),
    ]
    document_url: Annotated[str, Field(description="The direct link to the Google Document.")]
    current_tab: Annotated[TabInfo | None, Field(description="Information about the current tab being displayed.", default=None)]
    tabs: Annotated[list[TabInfo], Field(description="List of all tabs in the document.", default_factory=list)]
    comments: Annotated[list[CommentInfo], Field(description="List of comments on the document.", default_factory=list)]


class RawDocument(DocumentInfo):
    # Model used to parse the Google API response..
    body: _Content
    tab_contents: Annotated[list[tuple[TabInfo, _Content]], Field(default_factory=list)]

    @classmethod
    def from_google_response(cls, data: dict) -> Self:
        # Handle documents with tabs structure
        if "tabs" in data and data["tabs"]:
            # Extract all tabs information and their content
            all_tabs = []
            tab_contents = []
            current_tab_info = None

            def extract_tabs_recursive(tabs_list, parent_path="", global_index=[0]):
                tab_infos = []
                for local_index, tab in enumerate(tabs_list):
                    # Check different possible tab structures
                    tab_id = tab.get("tabId")

                    # Look for tab ID and title in tabProperties
                    if not tab_id and "tabProperties" in tab:
                        tab_props = tab["tabProperties"]
                        tab_id = tab_props.get("tabId")

                    # Try different ways to get tab title
                    title = None
                    if "tabProperties" in tab and "title" in tab["tabProperties"]:
                        title = tab["tabProperties"]["title"]
                    elif "documentTab" in tab and "title" in tab["documentTab"]:
                        title = tab["documentTab"]["title"]

                    # Fallback title if none found
                    if not title:
                        title = f"Tab {local_index + 1}"

                    # Create tab info even without tabId (use index as fallback)
                    if not tab_id:
                        tab_id = f"tab_{global_index[0]}"

                    # Use global index for TabInfo (sequential numbering)
                    tab_info = TabInfo(
                        tabId=tab_id,
                        title=title,
                        index=global_index[0]
                    )
                    tab_infos.append(tab_info)
                    global_index[0] += 1

                    # Extract tab content if available
                    if "documentTab" in tab and "body" in tab["documentTab"]:
                        tab_content = _Content.model_validate(
                            tab["documentTab"]["body"],
                            context={
                                "inline_objects": data.get("inlineObjects"),
                                "lists": data.get("lists"),
                            }
                        )
                        tab_contents.append((tab_info, tab_content))

                    # Handle child tabs recursively
                    if "childTabs" in tab:
                        current_path = f"{parent_path}{local_index}." if parent_path else f"{local_index}."
                        child_tabs = extract_tabs_recursive(tab["childTabs"], current_path, global_index)
                        tab_infos.extend(child_tabs)

                return tab_infos

            all_tabs = extract_tabs_recursive(data["tabs"])

            # For documents with tabs, body should be empty - content is in tab_contents
            if data["tabs"] and len(data["tabs"]) > 0:
                # Set current tab to the first tab if tabs exist
                if all_tabs:
                    current_tab_info = all_tabs[0]

                # Create a new data dict with empty body since content is in tabs
                processed_data = {
                    "documentId": data.get("documentId"),
                    "title": data.get("title", "Untitled"),
                    "document_url": f"https://docs.google.com/document/d/{data.get('documentId')}/edit",
                    "body": {"content": []},  # Empty body for documents with tabs
                    "current_tab": current_tab_info,
                    "tabs": all_tabs,
                    "tab_contents": tab_contents,
                    "inlineObjects": data.get("inlineObjects"),
                    "lists": data.get("lists"),
                }
            else:
                # No tabs found, create empty body
                processed_data = {
                    "documentId": data.get("documentId"),
                    "title": data.get("title", "Untitled"),
                    "document_url": f"https://docs.google.com/document/d/{data.get('documentId')}/edit",
                    "body": {"content": []},
                    "current_tab": None,
                    "tabs": [],
                    "tab_contents": [],
                    "inlineObjects": data.get("inlineObjects"),
                    "lists": data.get("lists"),
                }
        else:
            # Legacy document without tabs - use original data with empty tab info
            processed_data = {
                **data,
                "current_tab": None,
                "tabs": [],
                "tab_contents": []
            }

        return cls.model_validate(
            processed_data,
            context={
                "inline_objects": processed_data.get("inlineObjects") or {},
                "lists": processed_data.get("lists") or {},
            },
        )

    def to_markdown(self) -> str:
        # If document has tabs, body should be empty - don't use it
        if self.tab_contents:
            return ""  # Body is empty for documents with tabs
        return self.body.to_markdown(_MarkdownContext()).strip()

    def to_markdown_all_tabs(self) -> str:
        """Generate markdown with all tab contents concatenated."""
        if not self.tab_contents:
            # No tabs, return regular body content
            return self.to_markdown()

        ctx = _MarkdownContext()
        parts = []

        for tab_info, tab_content in self.tab_contents:
            # Add tab header using integer index
            parts.append(f"## Tab {tab_info.index}: {tab_info.title}")
            parts.append("")  # Empty line after header

            # Add tab content
            tab_markdown = tab_content.to_markdown(ctx).strip()
            if tab_markdown:
                parts.append(tab_markdown)
            else:
                parts.append("*[This tab is empty]*")

            # Add separator between tabs (except for the last one)
            parts.append("")
            parts.append("---")
            parts.append("")

        # Remove the last separator
        if parts and parts[-3:] == ["", "---", ""]:
            parts = parts[:-3]

        return "\n".join(parts)

    @property
    def end_index(self) -> int:
        if last_element := self.body.content[-1]:
            return last_element.end_index

        return 1


class MarkdownDocument(DocumentInfo):
    body: Annotated[
        str | None,
        Field(description="The body of the document written in Extended Markdown."),
    ] = None
    tab_contents: Annotated[
        list[dict] | None,
        Field(description="All tab contents with their metadata.", default=None)
    ] = None

    @classmethod
    def from_raw_document(cls, document: RawDocument, include_all_tabs: bool = False) -> Self:
        # Process tab_contents into serializable format
        serialized_tab_contents = None
        if document.tab_contents:
            serialized_tab_contents = []
            ctx = _MarkdownContext()
            for tab_info, tab_content in document.tab_contents:
                serialized_tab_contents.append({
                    "tab_info": {
                        "tab_id": tab_info.tab_id,
                        "title": tab_info.title,
                        "index": tab_info.index
                    },
                    "markdown_content": tab_content.to_markdown(ctx).strip()
                })

        # Set body based on document structure
        if document.tab_contents:
            # Document has tabs - keep body empty to show clear structure
            body = ""
        else:
            # Legacy document without tabs - use body content
            body = document.to_markdown()

        return MarkdownDocument(
            title=document.title,
            document_id=document.document_id,
            document_url=document.document_url,
            body=body,
            current_tab=document.current_tab,
            tabs=document.tabs,
            tab_contents=serialized_tab_contents,
            comments=document.comments,
        )
