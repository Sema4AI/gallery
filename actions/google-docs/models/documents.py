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
    text: Annotated[str, Field(validation_alias=AliasPath("textRun", "content"))]
    link: Annotated[
        str, Field(validation_alias=AliasPath("link", "textStyle", "link"))
    ] = None
    text_style: Annotated[
        TextStyle,
        Field(validation_alias="textStyle", default_factory=lambda: TextStyle()),
    ]

    def to_markdown(self, ctx: _MarkdownContext) -> str:
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
        if (inline_objects := info.context.get("inline_objects")) is None:
            raise RuntimeError("`inline_objects` was not passed as context")

        match inline_objects.get(value):
            case {
                "inlineObjectProperties": {
                    "embeddedObject": {"imageProperties": {"contentUri": content_uri}}
                    | {"embeddedDrawingProperties": {"contentUri": content_uri}}
                }
            }:
                return content_uri
            case _:
                raise ValueError("Invalid image element")

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
        _UnorderedListId | _OrderedListId,
        Field(validation_alias=AliasPath("bullet", "listId")),
    ] = None

    @field_validator("list_id", mode="before")
    def populate_list_id(cls, value: str, info: ValidationInfo) -> str | None:
        if (inline_objects := info.context.get("lists")) is None:
            raise RuntimeError("`lists` was not passed as context")

        if (list_properties := inline_objects.get(value)) is None:
            raise ValueError("Invalid list id")

        nesting_level_info = list_properties["listProperties"]["nestingLevels"][
            info.data["nesting_level"]
        ]

        match nesting_level_info:
            case {"glyphSymbol": _}:
                return _UnorderedListId(value)
            case {"glyphType": _}:
                return _OrderedListId(value)
            case _:
                # Can't determine list type, so we treat it as a normal text.
                return None

    def to_markdown(self, ctx: _MarkdownContext) -> str:
        body = "".join(e.to_markdown(ctx) for e in self.elements)

        if self.list_id:
            spacing = " " * (self.nesting_level * 2)
            match self.list_id:
                case _OrderedListId(list_id):
                    i = ctx.get_next_list_index(str(list_id), self.nesting_level)
                    return f"{spacing}{i}. {body}"
                case _UnorderedListId():
                    return f"{spacing}* {body}"
                case _:
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
    data: list[list["_Content"]]

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
        rows = iter(self.data)

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


class DocumentInfo(BaseModel, extra="ignore", populate_by_name=True):
    # Model used to structure the action response.
    title: Annotated[str, Field(description="The title of the document.")]
    documentId: Annotated[
        str,
        Field(
            description="The ID of the document.",
        ),
    ]


class RawDocument(DocumentInfo):
    # Model used to parse the Google API response..
    body: _Content

    @classmethod
    def from_google_response(cls, data: dict) -> Self:
        return cls.model_validate(
            data,
            context={
                "inline_objects": data.get("inlineObjects"),
                "lists": data.get("lists"),
            },
        )

    def to_markdown(self) -> str:
        return self.body.to_markdown(_MarkdownContext()).strip()


class MarkdownDocument(DocumentInfo):
    body: Annotated[
        str | None,
        Field(description="The body of the document written in Extended Markdown."),
    ] = None

    @classmethod
    def from_raw_document(cls, document: RawDocument) -> Self:
        return MarkdownDocument(
            title=document.title,
            documentId=document.documentId,
            body=document.to_markdown(),
        )
