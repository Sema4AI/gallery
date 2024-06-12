from typing import Annotated

from pydantic import BaseModel, Field


class Row(BaseModel):
    cells: Annotated[list[str], Field(description="Row cells")]

    def as_list(self) -> list[str]:
        return [str(cell) for cell in self.cells]


class Table(BaseModel):
    # NOTE(cmin764): The `header` would be enough to be just a `Row`, but in Sema4.ai
    #  Desktop the LLM will always send the header as a plain list, while ReMark will
    #  understand the expected type.
    header: Annotated[Row | list[str], Field(description="Table header")]
    rows: Annotated[list[Row], Field(description="Table rows")]

    def get_header(self) -> list[str]:
        return (
            [str(cell) for cell in self.header]
            if isinstance(self.header, list)
            else self.header.as_list()
        )

    def as_list(self) -> list[list[str]]:
        return [row.as_list() for row in self.rows]


class Sheet(BaseModel):
    name: Annotated[str, Field(description="Sheet name")]
    top_row: Annotated[Row, Field(description="First row")]


class Schema(BaseModel):
    sheets: Annotated[list[Sheet], Field(description="Workbook sheets")]
