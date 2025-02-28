from sema4ai.actions import action, Secret, ActionError
import http.client
import json
import os
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "devdata", ".env"))


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
def search_google(q: str, num: int, api_key: Secret) -> SearchResult:
    """
    Perform a search using the Serper API and return a structured summary.

    Args:
        q: The search query.
        num: The number of results to return.
        api_key: The API key for authentication.

    Returns:
        SearchResult: A structured summary of the search results.
    """
    # Check if API key is provided
    if not api_key or not api_key.value or not os.getenv("SERPER_API_KEY"):
        raise ActionError("API key is required but not provided")

    try:
        conn = http.client.HTTPSConnection("google.serper.dev")
        payload = json.dumps({"q": q, "num": num})
        headers = {"X-API-KEY": api_key.value, "Content-Type": "application/json"}
        conn.request("POST", "/search", payload, headers)
        res = conn.getresponse()

        # Check if the response status is not successful
        if res.status != 200:
            error_data = res.read().decode("utf-8")
            raise ActionError(
                f"API request failed with status {res.status}: {error_data}"
            )

        data = res.read()
        response = json.loads(data.decode("utf-8"))

        # Parse the response using the Pydantic model
        search_result = SearchResult(**response)

        return search_result

    except json.JSONDecodeError:
        raise ActionError("Failed to parse API response as JSON")
    except http.client.HTTPException as e:
        raise ActionError(f"HTTP error occurred: {str(e)}")
    except Exception as e:
        raise ActionError(f"An unexpected error occurred: {str(e)}")
