from typing import Annotated

from pydantic import BaseModel, Field


class Row(BaseModel):
    cells: Annotated[list[str], Field(description="Row cells")]

    def as_list(self) -> list[str]:
        return [str(cell) for cell in self.cells]


class Table(BaseModel):
    header: Annotated[Row, Field(description="Table header")]
    rows: Annotated[list[Row], Field(description="Table rows")]

    def get_header(self) -> list[str]:
        return self.header.as_list()

    def as_list(self) -> list[list[str]]:
        return [row.as_list() for row in self.rows]


class Sheet(BaseModel):
    name: Annotated[str, Field(description="Sheet name")]
    top_row: Annotated[Row, Field(description="First row")]


class Schema(BaseModel):
    sheets: Annotated[list[Sheet], Field(description="Workbook sheets")]
