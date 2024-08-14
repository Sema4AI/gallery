from typing import Annotated

from pydantic import BaseModel, Field


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
    top_row: Annotated[Row, Field(description="First row which may be a header")]


class Schema(BaseModel):
    sheets: Annotated[list[Sheet], Field(description="Workbook sheets")]
