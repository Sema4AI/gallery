import json
import os
from pathlib import Path
from typing import List, Optional
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import sema4ai_http
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from sema4ai.actions import ActionError, Response, Secret, action
from urllib3.exceptions import HTTPError

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")


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
    Perform a search using the Serper API and return a structured summary. The number of results can be specified.

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

    max_attempts = 3
    initial_delay = 0.5
    max_delay = 8.0
    attempt = 0

    while True:
        try:
            headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
            payload = json.dumps({"q": q, "num": num})

            response = sema4ai_http.post(
                "https://google.serper.dev/search",
                body=payload,
                headers=headers,
            )

            status_code = getattr(response, "status_code", None)
            if status_code is not None and (status_code == 429 or 500 <= status_code <= 599) and attempt < max_attempts:
                retry_after = None
                try:
                    retry_after = response.headers.get("Retry-After")
                except Exception:
                    retry_after = None
                delay = initial_delay * (2 ** attempt)
                if retry_after:
                    try:
                        if retry_after.isdigit():
                            delay = float(retry_after)
                        else:
                            dt = parsedate_to_datetime(retry_after)
                            if dt is not None:
                                if dt.tzinfo is None:
                                    dt = dt.replace(tzinfo=timezone.utc)
                                seconds = (dt - datetime.now(timezone.utc)).total_seconds()
                                if seconds > 0:
                                    delay = seconds
                    except Exception:
                        pass
                if delay > max_delay:
                    delay = max_delay
                time.sleep(delay)
                attempt += 1
                continue

            response.raise_for_status()

            search_result = SearchResult(**response.json())
            return Response(result=search_result)
        except HTTPError as e:
            status_code = None
            resp = getattr(e, "response", None)
            if resp is not None:
                try:
                    status_code = resp.status_code
                except Exception:
                    status_code = None
            if (status_code == 429 or (status_code is not None and status_code >= 500)) and attempt < max_attempts:
                retry_after = None
                try:
                    retry_after = resp.headers.get("Retry-After") if resp is not None else None
                except Exception:
                    retry_after = None
                delay = initial_delay * (2 ** attempt)
                if retry_after:
                    try:
                        if retry_after.isdigit():
                            delay = float(retry_after)
                        else:
                            dt = parsedate_to_datetime(retry_after)
                            if dt is not None:
                                if dt.tzinfo is None:
                                    dt = dt.replace(tzinfo=timezone.utc)
                                seconds = (dt - datetime.now(timezone.utc)).total_seconds()
                                if seconds > 0:
                                    delay = seconds
                    except Exception:
                        pass
                if delay > max_delay:
                    delay = max_delay
                time.sleep(delay)
                attempt += 1
                continue
            raise ActionError(f"HTTP error occurred: {str(e)}")
        except Exception as e:
            if attempt < max_attempts:
                delay = initial_delay * (2 ** attempt)
                if delay > max_delay:
                    delay = max_delay
                time.sleep(delay)
                attempt += 1
                continue
            raise ActionError(f"An unexpected error occurred: {str(e)}")
