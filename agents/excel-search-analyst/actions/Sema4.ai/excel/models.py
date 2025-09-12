from datetime import datetime
from typing import Annotated, List, Union

from pydantic import BaseModel, Field


class Header(BaseModel):
    value: Union[str, list]


class CrossReferenceResult(BaseModel):
    """Model for the result of cross-reference intersections"""

    intersections: List[str]


class Row(BaseModel):
    cells: Annotated[list[str], Field(description="Row cells")]

    def __init__(self, cells: list[str]):
        super().__init__(cells=[str(cell) for cell in cells])

    def as_list(self) -> list[str]:
        return [str(cell) for cell in self.cells]


class Table(BaseModel):
    rows: Annotated[list[Row], Field(description="The rows that need to be added")]

    def as_list(self) -> list[list[str]]:
        return [row.as_list() for row in self.rows]


class Sheet(BaseModel):
    name: Annotated[str, Field(description="Sheet name")]
    data_range: Annotated[str, Field(description="Data range")]
    # top_row: Annotated[Row, Field(description="First row which may be a header")]


class UserAndTime(BaseModel):
    user: Annotated[str, Field(description="User name")]
    time: Annotated[datetime, Field(description="Creation time")]


class Schema(BaseModel):
    created: UserAndTime = Field(description="Created by and time")
    last_modified: UserAndTime = Field(description="Last modified by and time")
    sheets: Annotated[list[Sheet], Field(description="Workbook sheets")]
