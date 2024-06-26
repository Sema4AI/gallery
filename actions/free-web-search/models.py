from pydantic import BaseModel, Field
from typing import Annotated, Dict


class SearchResult(BaseModel):
    title: str = Field(description="The title of the search result", default="")
    link: str = Field(description="The link of the search result", default="")
    desc: str = Field(description="The description of the search result", default="")


class SearchResultList(BaseModel):
    results: Annotated[
        list[SearchResult], Field(description="A list of google search results")
    ]


class PlaceSearchResult(BaseModel):
    title: str = Field(description="The title of the search result", default="")
    address: str = Field(description="The address of the search result", default="")
    phone: str = Field(description="The phone number of the search result", default="")
    desc: str = Field(description="The description of the search result", default="")
    source: str = Field(description="The source of the search result", default="")
    latitude: str = Field(description="The latitude of the search result", default="")
    longitude: str = Field(description="The longitude of the search result", default="")
    url: str = Field(description="The link of the search result", default="")
    hours: str = Field(description="The opening hours of the search result", default="")
    category: str = Field(description="The category of the search result", default="")


class PlaceSearchResultList(BaseModel):
    results: Annotated[
        list[PlaceSearchResult], Field(description="A list of place search results")
    ]


class GenericSearchResultList(BaseModel):
    results: list[Dict] = Field(description="The search result", default={})
