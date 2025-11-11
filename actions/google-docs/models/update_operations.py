from __future__ import annotations

import emoji
import re
from enum import Enum
from typing import Generator, Iterable

from pydantic import AliasGenerator, BaseModel, model_validator
from pydantic.alias_generators import to_camel
from typing_extensions import Literal, Self, assert_never

from models.documents import TextStyle


class _ListType(Enum):
    numbered = "NUMBERED_DECIMAL_ALPHA_ROMAN"
    bulleted = "BULLET_DISC_CIRCLE_SQUARE"


class _ListContext:
    def __init__(self):
        self._start_index: int | None = None
        self._end_index: int | None = None
        self._list_type: _ListType | None = None

    def is_within_list(self) -> bool:
        return self._list_type is not None

    def _build_update_operation(
        self,
    ) -> "CreateParagraphBulletsRequest":
        return CreateParagraphBulletsRequest.new(
            self._list_type, start_index=self._start_index, end_index=self._end_index
        )

    def parse_line(
        self, list_type: _ListType | None, *, start_index: int, end_index: int
    ) -> "CreateParagraphBulletsRequest" | None:
        value = None

        if list_type:
            # We get a new list type, and we are already on a list
            if self._start_index and (list_type != self._list_type):
                value = self._build_update_operation()
            # We got a list type, but we don't have a start index.
            elif not self._start_index:
                self._list_type = list_type
                self._start_index = start_index
                self._end_index = end_index
            # We are still within the same list.
            elif list_type == self._list_type:
                self._end_index = end_index
            else:
                if list_type != self._list_type:
                    assert_never("list_type != self._list_type")
        elif self._list_type and self._start_index:
            # We are not in a list anymore
            value = self._build_update_operation()

        if value:
            self._reset()
            return value

        return None

    def check_on_end(self):
        pass

    def _reset(self):
        self._start_index = None
        self._end_index = None
        self._list_type = None


class _TableContext:
    def __init__(self):
        self._text = ""

    def add_line(self, text: str) -> bool:
        text = text.strip()
        if text.startswith("|"):
            if self._text:
                self._text += "||" + text  # Use || as row separator for table parsing
            else:
                self._text = text
            return True

        return False

    def get_line(self) -> _TableLine | None:
        if self._text:
            value = self._text
            self._text = ""
            return _TableLine(value)

        return None


class _BaseUpdateRequest(
    BaseModel, alias_generator=AliasGenerator(serialization_alias=to_camel)
):
    pass


class _Location(_BaseUpdateRequest):
    segment_id: str | None = None
    tab_id: str | None = None
    index: int | None = None
    end_of_segment_location: dict | None = None


class Range(_BaseUpdateRequest):
    segment_id: str | None = None
    tab_id: str | None = None
    start_index: int
    end_index: int


class _InsertPageBreak(_BaseUpdateRequest):
    location: _Location


class InsertPageBreakRequest(_BaseUpdateRequest):
    insert_page_break: _InsertPageBreak

    @classmethod
    def new(cls, index: int) -> Self:
        return cls(insert_page_break=_InsertPageBreak(location=_Location(index=index)))


class _InsertInlineImage(_BaseUpdateRequest):
    uri: str
    location: _Location


class InsertInlineImageRequest(_BaseUpdateRequest):
    insert_inline_image: _InsertInlineImage

    @classmethod
    def new(cls, uri: str, *, index: int) -> Self:
        return cls(
            insert_inline_image=_InsertInlineImage(
                uri=uri, location=_Location(index=index)
            )
        )


class _UpdateTextStyle(_BaseUpdateRequest):
    text_style: TextStyle
    range: Range
    fields: str = "*"

    @model_validator(mode="after")
    def set_fields(self):
        fields = []
        style_dict = self.text_style.model_dump(by_alias=True)
        for style_field, style_value in style_dict.items():
            # Only include fields that are explicitly set to True (for booleans) or have a value
            if style_value is True or (style_value is not False and style_value is not None):
                fields.append(style_field)

        if fields:
            self.fields = ",".join(fields)
        else:
            # Fallback to all fields if none detected
            self.fields = "*"

        return self


class UpdateTextStyleRequest(_BaseUpdateRequest):
    update_text_style: _UpdateTextStyle

    @classmethod
    def new(cls, text_style: TextStyle, *, start_index: int, end_index: int, fields: str | None = None) -> Self:
        update_style = _UpdateTextStyle(
            text_style=text_style,
            range=Range(start_index=start_index, end_index=end_index),
        )
        if fields:
            update_style.fields = fields
        return cls(update_text_style=update_style)


_NAME_STYLE_TYPE = Literal[
    "HEADING_1", "HEADING_2", "HEADING_3", "HEADING_4", "HEADING_5", "HEADING_6", "NORMAL_TEXT"
]


class _ParagraphStyle(_BaseUpdateRequest):
    named_style_type: _NAME_STYLE_TYPE | None = None
    border_bottom: _ParagraphBorder | None = None


class _UpdateParagraphStyle(_BaseUpdateRequest):
    paragraph_style: _ParagraphStyle
    range: Range
    fields: str = "namedStyleType"  # required field by API, can be "borderBottom" for horizontal rules


class UpdateParagraphStyleRequest(_BaseUpdateRequest):
    update_paragraph_style: _UpdateParagraphStyle

    @classmethod
    def new(cls, style: str, *, start_index: int, end_index: int) -> Self:
        return cls.model_validate(
            {
                "update_paragraph_style": {
                    "paragraph_style": {"named_style_type": style},
                    "range": Range(start_index=start_index, end_index=end_index),
                    "fields": "namedStyleType",
                }
            }
        )

    @classmethod
    def new_horizontal_rule(cls, start_index: int, end_index: int, *, tab_id: str | None = None) -> Self:
        """Create a horizontal rule using paragraph bottom border."""
        return cls(
            update_paragraph_style=_UpdateParagraphStyle(
                paragraph_style=_ParagraphStyle(
                    border_bottom=_ParagraphBorder()
                ),
                range=Range(
                    start_index=start_index,
                    end_index=end_index,
                    tab_id=tab_id
                ),
                fields="borderBottom"
            )
        )




class _CreateParagraphBullets(_BaseUpdateRequest):
    range: Range
    bullet_preset: _ListType


class CreateParagraphBulletsRequest(_BaseUpdateRequest):
    create_paragraph_bullets: _CreateParagraphBullets

    @classmethod
    def new(cls, bullet_preset: _ListType, *, start_index: int, end_index: int) -> Self:
        return cls(
            create_paragraph_bullets=_CreateParagraphBullets(
                bullet_preset=bullet_preset,
                range=Range(start_index=start_index, end_index=end_index),
            )
        )


class _SubstringMatchCriteria(_BaseUpdateRequest):
    text: str
    match_case: bool


class ReplaceAllTextRequest(_BaseUpdateRequest):
    replace_text: str
    contains_text: _SubstringMatchCriteria

    @classmethod
    def new(cls, old_text: str, new_text: str, *, case_sensitive: bool = False) -> Self:
        return cls(
            replace_text=new_text,
            contains_text=_SubstringMatchCriteria(
                text=old_text, match_case=case_sensitive
            ),
        )

    def __hash__(self):
        return hash(self.replace_text)


class _InsertTable(_BaseUpdateRequest):
    rows: int
    columns: int
    location: _Location


class InsertTableRequest(_BaseUpdateRequest):
    insert_table: _InsertTable

    @classmethod
    def new(cls, rows: int, columns: int, *, index: int) -> Self:
        return cls(
            insert_table=_InsertTable(
                rows=rows, columns=columns, location=_Location(index=index)
            )
        )

    @classmethod
    def new_end_of_segment(cls, rows: int, columns: int, *, tab_id: str | None = None, segment_id: str | None = None) -> Self:
        location = _Location(
            end_of_segment_location={},
            tab_id=tab_id,
            segment_id=segment_id
        )
        return cls(
            insert_table=_InsertTable(
                rows=rows, columns=columns, location=location
            )
        )


class _InsertText(_BaseUpdateRequest):
    text: str
    location: _Location


class InsertTextRequest(_BaseUpdateRequest):
    insert_text: _InsertText

    @classmethod
    def new(cls, text: str, *, index: int) -> Self:
        return cls(insert_text=_InsertText(text=text, location=_Location(index=index)))

    @classmethod
    def new_end_of_segment(cls, text: str, *, tab_id: str | None = None, segment_id: str | None = None) -> Self:
        location = _Location(
            end_of_segment_location={},
            tab_id=tab_id,
            segment_id=segment_id
        )
        return cls(insert_text=_InsertText(text=text, location=location))


class _Dimension(_BaseUpdateRequest):
    magnitude: float = 1.0
    unit: str = "PT"


class _Color(_BaseUpdateRequest):
    red: float = 0.0
    green: float = 0.0
    blue: float = 0.0


class _ColorWrapper(_BaseUpdateRequest):
    rgb_color: _Color = _Color()


class _BorderColor(_BaseUpdateRequest):
    color: _ColorWrapper = _ColorWrapper()


class _ParagraphBorder(_BaseUpdateRequest):
    color: _BorderColor = _BorderColor()
    width: _Dimension = _Dimension()
    dash_style: str = "SOLID"


class _TableCellBorder(_BaseUpdateRequest):
    color: dict = {"color": {"rgbColor": {"red": 0.0, "green": 0.0, "blue": 0.0}}}
    width: dict = {"magnitude": 1, "unit": "PT"}
    dash_style: str = "SOLID"

    @classmethod
    def no_border(cls) -> Self:
        """Create an invisible border (zero width)."""
        return cls(width={"magnitude": 0, "unit": "PT"})


class _TableCellStyle(_BaseUpdateRequest):
    border_top: _TableCellBorder | None = None
    border_bottom: _TableCellBorder | None = None
    border_left: _TableCellBorder | None = None
    border_right: _TableCellBorder | None = None


class _TableCellLocation(_BaseUpdateRequest):
    column_index: int = 0
    row_index: int = 0
    table_start_location: _Location


class _TableRange(_BaseUpdateRequest):
    column_span: int = 1
    row_span: int = 1
    table_cell_location: _TableCellLocation


class _UpdateTableCellStyle(_BaseUpdateRequest):
    table_cell_style: _TableCellStyle
    table_range: _TableRange
    fields: str = "borderTop"


class UpdateTableCellStyleRequest(_BaseUpdateRequest):
    update_table_cell_style: _UpdateTableCellStyle

    @classmethod
    def new_horizontal_rule(cls, table_location: _Location) -> Self:
        """Create a horizontal rule using table cell border."""
        return cls(
                        update_table_cell_style=_UpdateTableCellStyle(
                table_cell_style=_TableCellStyle(
                    border_top=_TableCellBorder(),                # Visible top border
                    border_bottom=_TableCellBorder.no_border(),   # Invisible bottom border
                    border_left=_TableCellBorder.no_border(),     # Invisible left border
                    border_right=_TableCellBorder.no_border(),    # Invisible right border
                ),
                table_range=_TableRange(
                    table_cell_location=_TableCellLocation(
                        table_start_location=table_location
                    )
                ),
                fields="borderTop,borderBottom,borderLeft,borderRight"
            )
        )


UpdateRequest = (
    InsertPageBreakRequest
    | InsertInlineImageRequest
    | UpdateTextStyleRequest
    | UpdateParagraphStyleRequest
    | CreateParagraphBulletsRequest
    | ReplaceAllTextRequest
    | InsertTextRequest
    | InsertTableRequest
    | UpdateTableCellStyleRequest
)


class _Line:
    __slots__ = ("data", "_list_context")

    MARKDOWN_BOLD_PATTERN = re.compile(r"^\*\*(.*?)\*\*")
    MARKDOWN_ITALIC_PATTERN = re.compile(r"^(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)")
    MARKDOWN_STRIKETHROUGH_PATTERN = re.compile(r"^~~(.*?)~~")

    IMAGE_PATTERN = re.compile(r"^!\[([^]]+)]\(([^)]+)\)")
    LINK_PATTERN = re.compile(r"^\[([^]]+)]\(([^)]+)\)")
    EMOJI_PATTERN = re.compile(r"^:([a-zA-Z0-9_+-]+):")

    NUMBERED_LIST_PATTERN = re.compile(r"^\d+\.\s*(.*)")



    def __init__(
        self,
        line: str,
        *,
        # this is optional since lines in a table can't have lists
        list_context: _ListContext = None,
        append_new_line: bool = True,
    ):
        line = line.strip()
        if append_new_line:
            line += "\n"

        self.data = line
        self._list_context = list_context

    def _parse_header(self) -> tuple[int, str]:
        heading_number = 0
        for i in range(6, 0, -1):
            if self.data.startswith("#" * i):
                heading_number = i
                break

        parsed_text = self.data.removeprefix("#" * heading_number).lstrip()

        return (
            heading_number,
            parsed_text,
        )

    def _parse_list(self) -> tuple[_ListType | None, str]:
        if self.data.startswith("-"):
            return _ListType.bulleted, self.data.removeprefix("-").lstrip()

        if list_match := next(self.NUMBERED_LIST_PATTERN.finditer(self.data), None):
            # list_match.group(1) strips the ending new-line
            return _ListType.numbered, list_match.group(1) + "\n"

        return None, self.data

    def get_update_operations(
        self, start_index: int, image_data: dict = None
    ) -> Generator[UpdateRequest, None, int]:
        """Helper method to generate Google Update Operations.
        It will yield all the operations for this specific line.
        Returns the end index.
        """

        list_type = None

                                # Handle horizontal rules (standalone --- lines)
        stripped_data = self.data.strip()
        if stripped_data == "---":
            # Create a horizontal rule using Google Docs API recommended approach:
            # Insert a single-cell table with top border styling (known working method)

            # 1. Insert a 1x1 table (empty content)
            yield InsertTableRequest.new(1, 1, index=start_index)

            # 2. Style the table cell with a top border to create horizontal line effect
            # Note: Reference the table location AFTER insertion (as per Google's examples)
            table_location = _Location(index=start_index + 1)
            yield UpdateTableCellStyleRequest.new_horizontal_rule(table_location)

            # Table index calculation (from _TableLine implementation):
            # +1 for table start, +1 for row start, +2 for cell start, +0 for empty cell, +2 for table end
            # Total: +6 for a 1x1 empty table
            end_index = start_index + 6
            return end_index

        heading_number, parsed_text = self._parse_header()
        if not heading_number:
            list_type, parsed_text = self._parse_list()

        # For empty lines, insert a newline to create proper spacing
        if not parsed_text:
            parsed_text = "\n"

        # Process emojis and other markdown
        update_requests, processed_text = self._parse_line(
            parsed_text, start_index=start_index, image_data=image_data
        )

        # Use the processed text for insertion
        text_to_insert = processed_text

        yield InsertTextRequest.new(text_to_insert, index=start_index)

        # Google Docs API uses UTF-16 code units for indexing, not Python character count
        # Emojis are 2 UTF-16 code units but 1 Python character, causing index misalignment
        def get_utf16_length(text: str) -> int:
            return len(text.encode('utf-16le')) // 2

        # Calculate end_index using UTF-16 length (Google Docs API standard)
        utf16_length = get_utf16_length(text_to_insert)
        end_index = start_index + utf16_length

        # For paragraph-level styles (headings), use UTF-16 length for correct indices
        text_without_newline = text_to_insert.rstrip("\n")
        if text_without_newline:
            style_end_index = start_index + get_utf16_length(text_without_newline)
        else:
            # For empty lines (just newline), apply style to just the newline character
            style_end_index = start_index + 1

        if heading_number and style_end_index is not None:
            request = UpdateParagraphStyleRequest.new(
                f"HEADING_{heading_number}",
                start_index=start_index,
                end_index=style_end_index,
            )
            yield request

        yield from update_requests

        if not heading_number and style_end_index is not None:
            # For all non-heading text (empty or not), explicitly set NORMAL_TEXT style
            # to prevent heading style inheritance.
            yield UpdateParagraphStyleRequest.new(
                "NORMAL_TEXT",
                start_index=start_index,
                end_index=style_end_index,
            )
        elif self._list_context:
            if list_update_operation := self._list_context.parse_line(
                list_type, start_index=start_index, end_index=end_index
            ):
                yield list_update_operation

        return end_index

    def _parse_line(
        self, data: str, *, start_index: int, image_data: dict = None
    ) -> tuple[list["UpdateRequest"], str]:
        parser = self._parse_string(data, current_index=start_index, image_data=image_data)

        requests = []

        while True:
            try:
                requests.append(next(parser))
            except StopIteration as exc:
                return requests, exc.value

    def _parse_string(
        self, text: str, *, current_index=1, image_data: dict = None
    ) -> Generator[_BaseUpdateRequest, None, str]:
        parsed_text = ""
        while len(text):
            for pattern in (
                self.MARKDOWN_BOLD_PATTERN,
                self.MARKDOWN_ITALIC_PATTERN,
                self.MARKDOWN_STRIKETHROUGH_PATTERN,
                self.IMAGE_PATTERN,
                self.LINK_PATTERN,
                self.EMOJI_PATTERN,
            ):
                if item_match := re.match(pattern, text):
                    end_index = item_match.end()
                    value = item_match.group(1)

                    # parse nested tags.
                    update_requests, value = self._parse_line(
                        value, start_index=current_index
                    )

                    yield from update_requests

                    parsed_text += value

                    token_start_index = current_index
                    token_end_index = current_index + len(value)

                    match item_match.re:
                        case self.MARKDOWN_BOLD_PATTERN:
                            yield UpdateTextStyleRequest.new(
                                TextStyle(bold=True),
                                start_index=token_start_index,
                                end_index=token_end_index,
                                fields='bold'
                            )

                        case self.MARKDOWN_ITALIC_PATTERN:
                            yield UpdateTextStyleRequest.new(
                                TextStyle(italic=True),
                                start_index=token_start_index,
                                end_index=token_end_index,
                                fields='italic'
                            )

                        case self.MARKDOWN_STRIKETHROUGH_PATTERN:
                            yield UpdateTextStyleRequest.new(
                                TextStyle(strikethrough=True),
                                start_index=token_start_index,
                                end_index=token_end_index,
                                fields='strikethrough'
                            )

                        case self.LINK_PATTERN:
                            yield UpdateTextStyleRequest.new(
                                TextStyle.new_link(item_match.group(2)),
                                start_index=token_start_index,
                                end_index=token_end_index,
                                fields='link'
                            )

                        case self.IMAGE_PATTERN:
                            token_end_index = token_start_index
                            parsed_text = parsed_text[: -len(value)]

                            # Check if this is a local image reference
                            image_url = item_match.group(2)
                            if image_data and image_url in image_data:
                                # Use Google Drive file ID for uploaded images
                                image_url = f"https://drive.google.com/uc?id={image_data[image_url]}"

                            yield InsertInlineImageRequest.new(
                                image_url, index=token_start_index
                            )

                        case self.EMOJI_PATTERN:
                            # Convert emoji shortcode to actual emoji using emoji package
                            emoji_code = item_match.group(1)
                            emoji_text = f":{emoji_code}:"
                            emoji_char = emoji.emojize(emoji_text)
                            # If emoji wasn't found, emojize returns the original text
                            if emoji_char == emoji_text:
                                # Keep original shortcode if not found
                                emoji_char = emoji_text
                            parsed_text = parsed_text[: -len(value)] + emoji_char
                            token_end_index = current_index + len(emoji_char)

                        case _:
                            assert_never(item_match.re)

                    current_index = token_end_index
                    text = text[end_index:]

                    break

            else:
                current_index += 1
                parsed_text += text[:1]
                text = text[1:]

        return parsed_text

    def __repr__(self):
        return f"<Line {self.data!r}>"


class _TableLine:
    __slots__ = ("data",)

    def __init__(self, text: str):
        self.data = text

    def get_update_operations(
        self, start_index: int, image_data: dict = None
    ) -> Generator[UpdateRequest, None, int]:
        rows = []
        row_count = 0
        column_count = 0

        for row_data in self.data.split("||"):
            cells = []
            row_count += 1
            current_row_columns = 0
            for column_data in row_data.split("|"):
                # since we split by | and Markdown tables start and end with |,
                # we get 2 extra lines we don't need
                if not column_data or column_data.strip().startswith("---"):
                    continue

                if data := column_data.strip():
                    cells.append(_Line(data))
                else:
                    # We might get an empty cell, but the strip will remove that.
                    cells.append(_Line(""))

                current_row_columns += 1

            if cells:
                rows.append(cells)
                # Track the maximum number of columns across all rows
                column_count = max(column_count, current_row_columns)

        # Use the actual number of rows we collected
        # No need to subtract 1 since separator rows are already filtered out
        row_count = len(rows)

        # Ensure all rows have the same number of columns by padding with empty cells
        for row in rows:
            while len(row) < column_count:
                row.append(_Line(""))

        yield InsertTableRequest.new(row_count, column_count, index=start_index)

        # For some obscure reason the index calculation of tables is not well documented.
        # Bellow is the index calculation:
        #   * index +=1 for the start of the table
        #   * index +=1 for the start of each row
        #   * index +=2 for the start of each cell
        #   * index +=text.length in each cell
        #   * index +=2 for the end of the table

        # Reference on index calculation for tables:
        # https://gist.github.com/tanaikech/3b5ac06747c8771f70afd3496278b04b?permalink_comment_id=4397902#gistcomment-4397902

        # We added the table so the index shifted by one
        current_index = start_index + 1

        requests = []
        style_requests = []

        for row in rows:
            current_index += 1
            for cell in row:
                current_index += 2
                operations = cell.get_update_operations(current_index, image_data=image_data)
                try:
                    while True:
                        op = next(operations)
                        if isinstance(op, InsertTextRequest):
                            requests.append(op)
                        else:
                            style_requests.append(op)
                except StopIteration as exc:
                    current_index = exc.value
                    pass

        # We first insert the text and then we apply the style of the text
        yield from requests
        yield from style_requests

        current_index += 2

        return current_index


class BatchUpdateBody(_BaseUpdateRequest):
    requests: list[UpdateRequest]

    @classmethod
    def from_raw_string(cls, text: str):
        """Used to generate the body for a new document"""
        return cls(requests=[InsertTextRequest.new(text, index=1)])

    @classmethod
    def from_markdown(
        cls, text: str, *, start_index: int = 1, is_append: bool = False, image_data: dict = None
    ) -> Self:
        # Normalize the text by removing trailing spaces before newlines
        # This ensures consistent parsing regardless of input formatting
        text = text.rstrip()  # Only strip trailing whitespace, preserve leading empty lines
        # Remove trailing spaces before each newline to prevent inconsistent line breaks
        text = re.sub(r' +\n', '\n', text)

        # Fix missing empty lines between headings and "Use case:" lines
        # Pattern: heading followed directly by **Use case:** should have empty line between
        text = re.sub(r'(### \d+\. [^\n]+)\n(\*\*Use case:\*\*)', r'\1\n\n\2', text)

        current_index = start_index
        requests = []

        for line in cls._get_lines(text, is_append=is_append):
            line_text_requests = []
            line_text_style_requests = []
            line_paragraph_style_requests = []
            line_images = []

            operations = line.get_update_operations(start_index=current_index, image_data=image_data)
            while True:
                try:
                    op = next(operations)
                    if isinstance(op, InsertInlineImageRequest):
                        line_images.append(op)
                    elif isinstance(op, InsertTextRequest) or isinstance(op, InsertTableRequest):
                        line_text_requests.append(op)
                    elif isinstance(op, UpdateTextStyleRequest):
                        line_text_style_requests.append(op)
                    else:
                        line_paragraph_style_requests.append(op)
                except StopIteration as exc:
                    current_index = exc.value
                    break

            # Add line requests in optimal order: text first, then character styles, then paragraph styles, then images
            requests.extend(line_text_requests)
            requests.extend(line_text_style_requests)
            requests.extend(line_paragraph_style_requests)
            requests.extend(line_images)

        return cls(requests=requests)

    def get_body(self):
        return self.model_dump(
            mode="json",
            by_alias=True,
            exclude_none=True,
        )

    @staticmethod
    def _get_lines(text: str, *, is_append=False) -> Iterable[_Line | _TableLine]:
        list_context = _ListContext()
        table_context = _TableContext()

        if is_append:
            # For append we add a new line
            yield _Line("")

        # Split by new lines
        for new_line in text.split("\n"):
            # Split by double spaces (new lines in Markdown)

            for markdown_line in new_line.split("  "):
                # Process all lines, including empty ones (for proper spacing)
                line = markdown_line

                # Only check for table processing if line has content
                if line:
                    # Obligatory "hack" for handling tables.
                    if table_context.add_line(line):
                        continue

                    if table_line := table_context.get_line():
                        yield table_line

                # Always yield the line (empty or not) to preserve spacing
                yield _Line(line, list_context=list_context)

        # The document might end in a table or a list,
        # so we need to make sure we don't have anything left in the contexts
        if list_context.is_within_list():
            # yield an empty line so the context can properly apply the style
            yield _Line("", list_context=list_context)

        if table_line := table_context.get_line():
            yield table_line
