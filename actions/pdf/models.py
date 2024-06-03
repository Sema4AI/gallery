from pydantic import BaseModel, Field
from typing import Dict


class PDFContent(BaseModel):
    pages: int = Field(description="The number of pages in the PDF", default=0)
    length: int = Field(description="The number of characters in the PDF", default=0)
    content: Dict = Field(description="The content of the PDF", default={})


class Match(BaseModel):
    text: Dict = Field(
        description="The text that was found, page and content", default=""
    )


class Matches(BaseModel):
    items: list[Dict] = Field(description="The matches found", default=[])
