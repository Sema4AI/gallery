from __future__ import annotations

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
            self._text += text
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
    index: int


class Range(_BaseUpdateRequest):
    segment_id: str | None = None
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
        for style_field, style_value in self.text_style.model_dump(
            by_alias=True
        ).items():
            if style_value:
                fields.append(style_field)

        self.fields = ",".join(fields)

        return self


class UpdateTextStyleRequest(_BaseUpdateRequest):
    update_text_style: _UpdateTextStyle

    @classmethod
    def new(cls, text_style: TextStyle, *, start_index: int, end_index: int) -> Self:
        return cls(
            update_text_style=_UpdateTextStyle(
                text_style=text_style,
                range=Range(start_index=start_index, end_index=end_index),
            )
        )


_NAME_STYLE_TYPE = Literal[
    "HEADING_1", "HEADING_2", "HEADING_3", "HEADING_4", "HEADING_5", "HEADING_6"
]


class _ParagraphStyle(_BaseUpdateRequest):
    named_style_type: _NAME_STYLE_TYPE


class _UpdateParagraphStyle(_BaseUpdateRequest):
    paragraph_style: _ParagraphStyle
    range: Range
    fields: Literal["namedStyleType"] = "namedStyleType"  # required field by API


class UpdateParagraphStyleRequest(_BaseUpdateRequest):
    update_paragraph_style: _UpdateParagraphStyle

    @classmethod
    def new(cls, style: str, *, start_index: int, end_index: int) -> Self:
        return cls.model_validate(
            {
                "update_paragraph_style": {
                    "paragraph_style": {"named_style_type": style},
                    "range": Range(start_index=start_index, end_index=end_index),
                }
            }
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


class _InsertText(_BaseUpdateRequest):
    text: str
    location: _Location


class InsertTextRequest(_BaseUpdateRequest):
    insert_text: _InsertText

    @classmethod
    def new(cls, text: str, *, index: int) -> Self:
        return cls(insert_text=_InsertText(text=text, location={"index": index}))


UpdateRequest = (
    InsertPageBreakRequest
    | InsertInlineImageRequest
    | UpdateTextStyleRequest
    | UpdateParagraphStyleRequest
    | CreateParagraphBulletsRequest
    | ReplaceAllTextRequest
    | InsertTextRequest
    | InsertTableRequest
)


class _Line:
    __slots__ = ("data", "_list_context")

    MARKDOWN_BOLD_PATTERN = re.compile(r"^\*\*(.*?)\*\*")
    MARKDOWN_ITALIC_PATTERN = re.compile(r"^(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)")
    MARKDOWN_STRIKETHROUGH_PATTERN = re.compile(r"^~~(.*?)~~")

    IMAGE_PATTERN = re.compile(r"^!\[([^]]+)]\(([^)]+)\)")
    LINK_PATTERN = re.compile(r"^\[([^]]+)]\(([^)]+)\)")

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

        return (
            heading_number,
            self.data.removeprefix("#" * heading_number).lstrip(),
        )

    def _parse_list(self) -> tuple[_ListType | None, str]:
        if self.data.startswith("-"):
            return _ListType.bulleted, self.data.removeprefix("-").lstrip()

        if list_match := next(self.NUMBERED_LIST_PATTERN.finditer(self.data), None):
            # list_match.group(1) strips the ending new-line
            return _ListType.numbered, list_match.group(1) + "\n"

        return None, self.data

    def get_update_operations(
        self, start_index: int
    ) -> Generator[UpdateRequest, None, int]:
        """Helper method to generate Google Update Operations.
        It will yield all the operations for this specific line.
        Returns the end index.
        """

        list_type = None

        if self.data.startswith("---"):
            end_index = start_index + 1
            yield InsertPageBreakRequest.new(start_index)
            # Short circuit in case of page break
            return end_index

        heading_number, parsed_text = self._parse_header()
        if not heading_number:
            list_type, parsed_text = self._parse_list()

        update_requests, parsed_text = self._parse_line(
            parsed_text, start_index=start_index
        )

        end_index = start_index + len(parsed_text)

        yield InsertTextRequest.new(parsed_text, index=start_index)
        yield from update_requests

        if heading_number:
            yield UpdateParagraphStyleRequest.new(
                f"HEADING_{heading_number}",
                start_index=start_index,
                end_index=end_index,
            )
        elif self._list_context:
            if list_update_operation := self._list_context.parse_line(
                list_type, start_index=start_index, end_index=end_index
            ):
                yield list_update_operation

        return end_index

    def _parse_line(
        self, data: str, *, start_index: int
    ) -> tuple[list["UpdateRequest"], str]:
        parser = self._parse_string(data, current_index=start_index)

        requests = []

        while True:
            try:
                requests.append(next(parser))
            except StopIteration as exc:
                return requests, exc.value

    def _parse_string(
        self, text: str, *, current_index=1
    ) -> Generator[_BaseUpdateRequest, None, str]:
        parsed_text = ""
        while len(text):
            for pattern in (
                self.MARKDOWN_BOLD_PATTERN,
                self.MARKDOWN_ITALIC_PATTERN,
                self.MARKDOWN_STRIKETHROUGH_PATTERN,
                self.IMAGE_PATTERN,
                self.LINK_PATTERN,
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
                            )

                        case self.MARKDOWN_ITALIC_PATTERN:
                            yield UpdateTextStyleRequest.new(
                                TextStyle(italic=True),
                                start_index=token_start_index,
                                end_index=token_end_index,
                            )

                        case self.MARKDOWN_STRIKETHROUGH_PATTERN:
                            yield UpdateTextStyleRequest.new(
                                TextStyle(strikethrough=True),
                                start_index=token_start_index,
                                end_index=token_end_index,
                            )

                        case self.LINK_PATTERN:
                            yield UpdateTextStyleRequest.new(
                                TextStyle.new_link(item_match.group(2)),
                                start_index=token_start_index,
                                end_index=token_end_index,
                            )

                        case self.IMAGE_PATTERN:
                            token_end_index = token_start_index
                            parsed_text = parsed_text[: -len(value)]

                            yield InsertInlineImageRequest.new(
                                item_match.group(2), index=token_start_index
                            )

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
        self, start_index: int
    ) -> Generator[UpdateRequest, None, int]:
        rows = []
        row_count = 0
        column_count = 0

        for row_data in self.data.split("||"):
            cells = []
            row_count += 1
            for column_data in row_data.split("|"):
                # since we split by | and Markdown tables start and end with |,
                # we get 2 extra lines we don't need
                if not column_data or column_data.startswith("---"):
                    continue

                if data := column_data.strip():
                    cells.append(_Line(data))
                else:
                    # We might get an empty cell, but the strip will remove that.
                    cells.append(_Line(""))

                column_count += 1

            if cells:
                rows.append(cells)

        if row_count:
            # Markdown requires the header row to be present, so we remove that extra row
            row_count -= 1

        # Reshape table
        column_count = column_count // row_count
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
                operations = cell.get_update_operations(current_index)
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
    def from_markdown(cls, text: str) -> Self:
        text = text.strip()
        current_index = 1
        requests = []
        images = []
        for line in cls._get_lines(text):
            operations = line.get_update_operations(start_index=current_index)
            while True:
                try:
                    op = next(operations)
                    if isinstance(op, InsertInlineImageRequest):
                        # Adding an image breaks the calculated offsets, so we add them last.
                        images.append(op)
                    else:
                        requests.append(op)
                except StopIteration as exc:
                    current_index = exc.value
                    break

        requests += images

        for i, request in enumerate(requests):
            print(f"([{i}]", request)

        return cls(requests=requests)

    def get_body(self):
        return self.model_dump(
            mode="json",
            by_alias=True,
            exclude_none=True,
        )

    @staticmethod
    def _get_lines(text: str) -> Iterable[_Line | _TableLine]:
        list_context = _ListContext()
        table_context = _TableContext()

        # Split by new lines
        for new_line in text.split("\n"):
            # Split by double spaces (new lines in Markdown)

            for markdown_line in new_line.split("  "):
                # Make sure it's not an empty line
                if line := markdown_line:
                    # Obligatory "hack" for handling tables.
                    if table_context.add_line(line):
                        continue

                    if table_line := table_context.get_line():
                        yield table_line

                    yield _Line(line, list_context=list_context)

        # The document might end in a table or a list,
        # so we need to make sure we don't have anything left in the contexts
        if list_context.is_within_list():
            # yield an empty line so the context can properly apply the style
            yield _Line("", list_context=list_context)

        if table_line := table_context.get_line():
            yield table_line
