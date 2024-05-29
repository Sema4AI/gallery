from typing import Annotated

from pydantic import BaseModel, Field


class Row(BaseModel):
    cells: Annotated[list[str], Field(description="Row cells")]


class Table(BaseModel):
    header: Annotated[Row | None, Field(None, description="Table header")]
    rows: Annotated[list[Row], Field(description="Table rows")]

    def as_list(self) -> list[list[str]]:
        return [row.cells for row in self.rows]


class Sheet(BaseModel):
    name: Annotated[str, Field(description="Sheet name")]
    top_row: Annotated[Row, Field(description="First row")]


class Schema(BaseModel):
    sheets: Annotated[list[Sheet], Field(description="Workbook sheets")]
