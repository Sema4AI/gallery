import json
import os
import time
from pathlib import Path
from typing import List, Optional

import sema4ai_http
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from sema4ai.actions import ActionError, Response, Secret, action
from urllib3.exceptions import HTTPError

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")

def retry_with_exponential_backoff(func, max_retries=3, base_delay=1.0, max_delay=5.0):
    """
    Retry a function with exponential backoff for connection-related exceptions.
    
    Args:
        func: The function to retry
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds for exponential backoff (default: 1.0)
        max_delay: Maximum delay in seconds (default: 5.0)
    
    Returns:
        The result of the function call
        
    Raises:
        ActionError: If all retries are exhausted
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except (HTTPError, Exception) as e:
            last_exception = e
            
            # Check if it's a connection-related error that should be retried
            error_str = str(e).lower()
            is_connection_error = (
                "remote end closed connection" in error_str or
                "connection aborted" in error_str or
                "remotedisconnected" in error_str or
                "connection reset" in error_str or
                "broken pipe" in error_str
            )
            
            if not is_connection_error and not isinstance(e, HTTPError):
                # Not a retryable error, raise immediately
                raise ActionError(f"Non-retryable error occurred: {str(e)}")
            
            if attempt == max_retries:
                # Last attempt failed, raise the exception
                if is_connection_error:
                    raise ActionError(f"Remote connection failed after {max_retries} retries: {str(e)}")
                else:
                    raise ActionError(f"HTTP error occurred: {str(e)}")
            
            # Calculate delay with exponential backoff
            delay = min(base_delay * (2 ** attempt), max_delay)
            time.sleep(delay)
    
    # This should never be reached, but just in case
    raise ActionError(f"Unexpected error: {str(last_exception)}")


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
def search_google(q: str, num: int, api_key: Secret) -> Response[SearchResult]:
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
    api_key = api_key.value or os.getenv("SERPER_API_KEY")
    if not api_key:
        raise ActionError("API key is required but not provided")

    def make_request():
        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
        payload = json.dumps({"q": q, "num": num})

        response = sema4ai_http.post(
            "https://google.serper.dev/search",
            body=payload,
            headers=headers,
        )

        response.raise_for_status()
        return response

    try:
        # Use retry logic with exponential backoff
        response = retry_with_exponential_backoff(make_request)
        search_result = SearchResult(**response.json())
        return Response(result=search_result)
    except Exception as e:
        raise ActionError(f"An unexpected error occurred: {str(e)}")
