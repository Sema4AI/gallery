from pydantic import BaseModel, Field
from typing import Annotated


class SearchResult(BaseModel):
    title: str = Field(description="The title of the search result", default="")
    link: str = Field(description="The link of the search result", default="")
    desc: str = Field(description="The description of the search result", default="")


class SearchResultList(BaseModel):
    results: Annotated[
        list[SearchResult], Field(description="A list of google search results")
    ]
