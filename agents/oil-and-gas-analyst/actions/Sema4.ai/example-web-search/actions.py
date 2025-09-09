import json
from typing import List, Optional

import sema4ai_http
from pydantic import BaseModel, Field
from sema4ai.actions import ActionError, Response, action
from urllib3.exceptions import HTTPError


# Define Pydantic models for the response
class KnowledgeGraph(BaseModel):
    title: str = Field(description="The title of the knowledge graph", default="")
    type: str = Field(description="The type of the entity", default="")
    website: str = Field(description="The website of the entity", default="")
    imageUrl: str = Field(description="The image URL of the entity", default="")
    attributes: dict = Field(description="Attributes of the entity", default={})


class OrganicResult(BaseModel):
    title: str = Field(description="The title of the search result", default="")
    link: str = Field(description="The link of the search result", default="")
    snippet: str = Field(description="The snippet of the search result", default="")
    position: int = Field(description="The position of the search result", default=0)


class Place(BaseModel):
    title: str = Field(description="The title of the place", default="")
    address: str = Field(description="The address of the place", default="")
    cid: str = Field(description="The CID of the place", default="")


class PeopleAlsoAsk(BaseModel):
    question: str = Field(description="The question people also ask", default="")
    snippet: str = Field(description="The snippet of the answer", default="")
    title: str = Field(description="The title of the source", default="")
    link: str = Field(description="The link to the source", default="")


class RelatedSearch(BaseModel):
    query: str = Field(description="The related search query", default="")


class SearchResult(BaseModel):
    searchParameters: dict = Field(description="The search parameters used", default={})
    knowledgeGraph: Optional[KnowledgeGraph] = Field(
        description="The knowledge graph result", default=None
    )
    organic: List[OrganicResult] = Field(
        description="A list of organic search results", default=[]
    )
    places: List[Place] = Field(description="A list of places", default=[])
    peopleAlsoAsk: List[PeopleAlsoAsk] = Field(
        description="A list of people also ask questions", default=[]
    )
    relatedSearches: List[RelatedSearch] = Field(
        description="A list of related searches", default=[]
    )
    credits: int = Field(description="The number of credits used", default=0)


@action
def search(q: str, num: int) -> Response[SearchResult]:
    """
    Perform a search using the an API to Google Search and return a structured summary.

    Args:
        q: The search query.
        num: The number of results to return.

    Returns:
        SearchResult: A structured summary of the search results.
    """

    try:
        headers = {"Content-Type": "application/json"}
        payload = json.dumps({"q": q, "num": num})

        response = sema4ai_http.post(
            "https://demo-services.sema4ai.dev/search",
            body=payload,
            headers=headers,
        )

        response.raise_for_status()

        search_result = SearchResult(**response.json())
        return Response(result=search_result)
    except HTTPError as e:
        raise ActionError(f"HTTP error occurred: {str(e)}")
    except Exception as e:
        raise ActionError(f"An unexpected error occurred: {str(e)}")
