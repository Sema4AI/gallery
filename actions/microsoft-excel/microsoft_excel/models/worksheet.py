from functools import cached_property
from typing import Any

from pydantic import BaseModel, Field, computed_field
from typing_extensions import Annotated


class Range(BaseModel):
    """A Range represents a collection of cells from the Excel worksheet."""

    values: list[list[Any]]
    address: Annotated[
        str,
        Field(
            description="The address of the range within the Excel file. "
            "It has the following format: {worksheet name}!{top_left_cell}:{bottom_right_cell}"
        ),
    ]

    @computed_field
    @cached_property
    def start_cell(self) -> str:
        return self.address.split("!")[-1].split(":")[0]

    @computed_field
    @cached_property
    def end_cell(self) -> str:
        return self.address.split("!", 1)[-1].split(":", 1)[-1]

    @computed_field
    @cached_property
    def worksheet_name(self) -> str:
        return self.address.split("!", 1)[0]


class WorksheetInfo(BaseModel, extra="ignore"):
    id: Annotated[str, Field(description="Worksheet ID")]
    name: str
    position: Annotated[
        int,
        Field(
            description="The zero-based position of the worksheet within the workbook."
        ),
    ]
    visibility: Annotated[
        str,
        Field(
            description="The Visibility of the worksheet. The possible values are: Visible, Hidden, VeryHidden."
        ),
    ]


class Worksheet(WorksheetInfo):
    range: Range
