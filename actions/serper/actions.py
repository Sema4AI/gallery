
import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Union

import sema4ai_http
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from sema4ai.actions import ActionError, Response, Secret, action
from urllib3.exceptions import HTTPError

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")


# Input validation functions
def _validate_url(url: str) -> None:
    """Validate URL format for lens search."""
    if not url or not isinstance(url, str):
        raise ActionError("URL is required and must be a string")
    if not url.startswith(('http://', 'https://')):
        raise ActionError("URL must start with http:// or https://")


def _validate_query(q: str) -> None:
    """Validate search query is not empty."""
    if not q or not isinstance(q, str) or not q.strip():
        raise ActionError("Search query is required and cannot be empty")


def _validate_coordinates(ll: str) -> None:
    """Validate GPS coordinates format."""
    if not ll.startswith('@'):
        raise ActionError("GPS coordinates must start with '@' (format: @latitude,longitude,zoom)")
    parts = ll[1:].split(',')
    if len(parts) < 2:
        raise ActionError("GPS coordinates must include latitude and longitude (format: @latitude,longitude,zoom)")


def _validate_positive_integer(value: int, param_name: str) -> None:
    """Validate that a parameter is a positive integer."""
    if not isinstance(value, int) or value <= 0:
        raise ActionError(f"{param_name} must be a positive integer")


# Helper functions for common operations
def _get_api_key(api_key: Secret) -> str:
    """Extract and validate API key."""
    key = api_key.value or os.getenv("SERPER_API_KEY")
    if not key:
        raise ActionError("API key is required but not provided")
    return key


def _build_payload(base_params: dict, optional_params: dict = None) -> dict:
    """Build API payload, only including non-None optional parameters."""
    payload = base_params.copy()
    if optional_params:
        for key, value in optional_params.items():
            if value is not None:
                payload[key] = value
    return payload


def _make_serper_request(endpoint: str, payload: dict, api_key_str: str, result_class):
    """Make request to Serper API and return parsed result."""
    try:
        headers = {"X-API-KEY": api_key_str, "Content-Type": "application/json"}
        response = sema4ai_http.post(
            f"https://google.serper.dev/{endpoint}",
            body=json.dumps(payload),
            headers=headers,
        )
        response.raise_for_status()
        search_result = result_class(**response.json())
        return Response(result=search_result)
    except HTTPError as e:
        raise ActionError(f"HTTP error occurred: {str(e)}")
    except Exception as e:
        raise ActionError(f"An unexpected error occurred: {str(e)}")


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


# New models for additional search endpoints
class NewsResult(BaseModel):
    title: str = Field(description="Article headline", default="")
    link: str = Field(description="Article URL", default="")
    snippet: str = Field(description="Article summary", default="")
    date: str = Field(description="Publication date", default="")
    source: str = Field(description="News source", default="")
    imageUrl: Optional[str] = Field(description="Article image", default=None)
    position: int = Field(description="Result position", default=0)


class NewsSearchResult(BaseModel):
    searchParameters: dict = Field(description="The search parameters used", default={})
    news: List[NewsResult] = Field(description="A list of news results", default=[])
    credits: int = Field(description="The number of credits used", default=0)


class ShoppingResult(BaseModel):
    title: str = Field(description="Product name", default="")
    source: str = Field(description="Vendor/retailer", default="")
    link: str = Field(description="Product page URL", default="")
    price: str = Field(description="Product price", default="")
    imageUrl: str = Field(description="Product image", default="")
    rating: float = Field(description="Product rating", default=0.0)
    ratingCount: int = Field(description="Number of ratings", default=0)
    productId: str = Field(description="Unique product identifier", default="")
    position: int = Field(description="Result position", default=0)


class ShoppingSearchResult(BaseModel):
    searchParameters: dict = Field(description="The search parameters used", default={})
    shopping: List[ShoppingResult] = Field(description="A list of shopping results", default=[])
    credits: int = Field(description="The number of credits used", default=0)


class ScholarResult(BaseModel):
    title: str = Field(description="Paper title", default="")
    link: str = Field(description="Paper URL", default="")
    publicationInfo: str = Field(description="Author and publication details", default="")
    snippet: str = Field(description="Paper abstract/summary", default="")
    year: int = Field(description="Publication year", default=0)
    citedBy: int = Field(description="Citation count", default=0)
    pdfUrl: Optional[str] = Field(description="Direct PDF link", default=None)
    id: str = Field(description="Unique paper identifier", default="")
    position: int = Field(description="Result position", default=0)


class ScholarSearchResult(BaseModel):
    searchParameters: dict = Field(description="The search parameters used", default={})
    organic: List[ScholarResult] = Field(description="A list of scholarly results", default=[])
    credits: int = Field(description="The number of credits used", default=0)


class PatentResult(BaseModel):
    title: str = Field(description="Patent title", default="")
    link: str = Field(description="Patent URL", default="")
    snippet: str = Field(description="Patent description/abstract", default="")
    position: int = Field(description="Result position", default=0)
    priorityDate: Optional[str] = Field(description="Priority date", default=None)
    filingDate: Optional[str] = Field(description="Filing date", default=None)
    grantDate: Optional[str] = Field(description="Grant date", default=None)
    publicationDate: Optional[str] = Field(description="Publication date", default=None)
    inventor: Optional[str] = Field(description="Inventor name(s)", default=None)
    assignee: Optional[str] = Field(description="Patent assignee/owner", default=None)
    publicationNumber: Optional[str] = Field(description="Publication number", default=None)
    language: Optional[str] = Field(description="Patent language", default=None)
    pdfUrl: Optional[str] = Field(description="Direct PDF link", default=None)
    figures: Optional[List[str]] = Field(description="Patent figures/images", default=None)


class PatentSearchResult(BaseModel):
    searchParameters: dict = Field(description="The search parameters used", default={})
    organic: List[PatentResult] = Field(description="A list of patent results", default=[])
    credits: int = Field(description="The number of credits used", default=0)


class EnhancedPlace(BaseModel):
    position: int = Field(description="Result position", default=0)
    title: str = Field(description="Place name", default="")
    address: Optional[str] = Field(description="Full address", default=None)
    latitude: float = Field(description="GPS latitude", default=0.0)
    longitude: float = Field(description="GPS longitude", default=0.0)
    rating: float = Field(description="Average rating", default=0.0)
    ratingCount: int = Field(description="Number of reviews", default=0)
    priceLevel: Optional[str] = Field(description="Price range indicator (e.g., '$$$')", default=None)
    type: Optional[str] = Field(description="Primary business type", default=None)
    types: Optional[List[str]] = Field(description="All business type categories", default=None)
    website: Optional[str] = Field(description="Business website", default=None)
    phoneNumber: Optional[str] = Field(description="Contact phone number", default=None)
    description: Optional[str] = Field(description="Business description", default=None)
    openingHours: Optional[Dict[str, str]] = Field(description="Operating hours by day", default=None)
    thumbnailUrl: Optional[str] = Field(description="Place thumbnail image", default=None)
    cid: Optional[str] = Field(description="Customer/place ID (numeric)", default=None)
    fid: Optional[str] = Field(description="Feature ID (hex format)", default=None)
    placeId: Optional[str] = Field(description="Google Place ID", default=None)
    # Keep legacy field for backward compatibility
    category: str = Field(description="Business category (legacy field)", default="")
    placeid: Optional[str] = Field(description="Google Place ID (legacy field)", default=None)


class MapSearchResult(BaseModel):
    searchParameters: dict = Field(description="The search parameters used", default={})
    ll: Optional[str] = Field(description="GPS coordinates if provided", default=None)
    places: List[EnhancedPlace] = Field(description="A list of places", default=[])
    credits: int = Field(description="The number of credits used", default=0)


class PlaceSearchResult(BaseModel):
    searchParameters: dict = Field(description="The search parameters used", default={})
    places: List[EnhancedPlace] = Field(description="A list of places", default=[])
    credits: int = Field(description="The number of credits used", default=0)


class ReviewResult(BaseModel):
    title: Optional[str] = Field(description="Review title", default=None)
    rating: Optional[float] = Field(description="Review rating", default=None)
    text: Optional[str] = Field(description="Review text", default=None)
    author: Optional[str] = Field(description="Review author", default=None)
    date: Optional[str] = Field(description="Review date", default=None)
    position: Optional[int] = Field(description="Result position", default=None)


class ReviewSearchResult(BaseModel):
    searchParameters: dict = Field(description="The search parameters used", default={})
    reviews: List[ReviewResult] = Field(description="A list of review results", default=[])
    credits: int = Field(description="The number of credits used", default=0)



@action
def search_google(q: str, num: int, api_key: Secret) -> Response[SearchResult]:
    """
    Perform a comprehensive Google search using the Serper API. Returns organic results, knowledge graphs, related questions, and more.
    
    You can specify the number of results to return (num, default: 10, max: 100).
    
    Args:
        q: Search query string
        num: Number of search results to return (1-100)
        api_key: Serper API key for authentication
    """
    # Validate inputs
    _validate_query(q)
    _validate_positive_integer(num, "num")
    
    # Build payload and make request
    payload = _build_payload({"q": q, "num": num})
    api_key_str = _get_api_key(api_key)
    return _make_serper_request("search", payload, api_key_str, SearchResult)


@action
def search_news(
    q: str,
    api_key: Secret,
    gl: Optional[str] = None,
    location: Optional[str] = None,
    hl: Optional[str] = None,
    tbs: Optional[str] = None,
    autocorrect: Optional[bool] = None,
    num: int = 10,
    page: int = 1
) -> Response[NewsSearchResult]:
    """
    Search for recent news articles with publication dates, sources, and images. Perfect for staying updated on current events.
    
    You can specify the number of articles (num, default: 10), page number (page, default: 1), country (gl), and time filter (tbs: "qdr:h" for hour, "qdr:d" for day, "qdr:w" for week, "qdr:m" for month).
    
    Args:
        q: News search query
        api_key: Serper API key for authentication
        gl: Country code for localized results
        location: Location filter for regional news
        hl: Language code for results
        tbs: Time filter for news recency
        autocorrect: Enable automatic spelling correction
        num: Number of articles to return
        page: Page number for pagination
    """
    # Validate inputs
    _validate_query(q)
    _validate_positive_integer(num, "num")
    _validate_positive_integer(page, "page")
    
    # Build payload and make request
    base_params = {"q": q, "num": num, "page": page}
    optional_params = {"gl": gl, "location": location, "hl": hl, "tbs": tbs, "autocorrect": autocorrect}
    payload = _build_payload(base_params, optional_params)
    api_key_str = _get_api_key(api_key)
    return _make_serper_request("news", payload, api_key_str, NewsSearchResult)


@action
def search_shopping(
    q: str,
    api_key: Secret,
    gl: Optional[str] = None,
    location: Optional[str] = None,
    hl: Optional[str] = None,
    autocorrect: Optional[bool] = None,
    num: int = 10,
    page: int = 1
) -> Response[ShoppingSearchResult]:
    """
    Search for products with prices, ratings, and vendor information. Perfect for price comparison and product research.
    
    You can specify the number of products (num, default: 10), page number (page, default: 1), and country for localized pricing (gl).
    
    Args:
        q: Product search query
        api_key: Serper API key for authentication
        gl: Country code for localized pricing
        location: Location for regional availability
        hl: Language code for product descriptions
        autocorrect: Enable automatic spelling correction
        num: Number of products to return
        page: Page number for pagination
    """
    # Validate inputs
    _validate_query(q)
    _validate_positive_integer(num, "num")
    _validate_positive_integer(page, "page")
    
    # Build payload and make request
    base_params = {"q": q, "num": num, "page": page}
    optional_params = {"gl": gl, "location": location, "hl": hl, "autocorrect": autocorrect}
    payload = _build_payload(base_params, optional_params)
    api_key_str = _get_api_key(api_key)
    return _make_serper_request("shopping", payload, api_key_str, ShoppingSearchResult)


@action
def search_scholar(
    q: str,
    api_key: Secret,
    gl: Optional[str] = None,
    location: Optional[str] = None,
    hl: Optional[str] = None,
    autocorrect: Optional[bool] = None,
    page: int = 1
) -> Response[ScholarSearchResult]:
    """
    Search for academic papers and scholarly articles with citations, publication info, and PDF links. Perfect for research and literature reviews.
    
    You can specify the page number (page, default: 1) and country for regional academic sources (gl).
    
    Args:
        q: Academic search query
        api_key: Serper API key for authentication
        gl: Country code for regional academic sources
        location: Location filter for institutional research
        hl: Language code for papers
        autocorrect: Enable automatic spelling correction
        page: Page number for pagination
    """
    # Validate inputs
    _validate_query(q)
    _validate_positive_integer(page, "page")
    
    # Build payload and make request
    base_params = {"q": q, "page": page}
    optional_params = {"gl": gl, "location": location, "hl": hl, "autocorrect": autocorrect}
    payload = _build_payload(base_params, optional_params)
    api_key_str = _get_api_key(api_key)
    return _make_serper_request("scholar", payload, api_key_str, ScholarSearchResult)


@action
def search_patents(
    q: str,
    api_key: Secret,
    num: int = 10,
    page: int = 1
) -> Response[PatentSearchResult]:
    """
    Search for patents with detailed metadata including inventors, filing dates, and PDF documents. Perfect for IP research and prior art searches.
    
    You can specify the number of patents (num, default: 10) and page number (page, default: 1).
    
    Args:
        q: Patent search query
        api_key: Serper API key for authentication
        num: Number of patents to return
        page: Page number for pagination
    """
    # Validate inputs
    _validate_query(q)
    _validate_positive_integer(num, "num")
    _validate_positive_integer(page, "page")
    
    # Build payload and make request
    payload = _build_payload({"q": q, "num": num, "page": page})
    api_key_str = _get_api_key(api_key)
    return _make_serper_request("patents", payload, api_key_str, PatentSearchResult)


@action
def search_maps(
    q: str,
    api_key: Secret,
    ll: Optional[str] = None,
    placeid: Optional[str] = None,
    cid: Optional[str] = None,
    hl: Optional[str] = None,
    page: int = 1
) -> Response[MapSearchResult]:
    """
    Enhanced geographic search with detailed place information, opening hours, and ratings. Perfect for finding local businesses and locations.
    
    You can specify GPS coordinates (ll: '@latitude,longitude,zoom'), Google Place ID (placeid), or business ID (cid). Page number defaults to 1.
    
    Args:
        q: Location search query
        api_key: Serper API key for authentication
        ll: GPS coordinates in format '@latitude,longitude,zoom'
        placeid: Google Place ID for specific location lookup
        cid: Customer/location ID for business lookup
        hl: Language code for results
        page: Page number for pagination
    """
    # Validate inputs
    _validate_query(q)
    _validate_positive_integer(page, "page")
    if ll:
        _validate_coordinates(ll)
    
    # Build payload and make request
    base_params = {"q": q, "page": page}
    optional_params = {"ll": ll, "placeid": placeid, "cid": cid, "hl": hl}
    payload = _build_payload(base_params, optional_params)
    api_key_str = _get_api_key(api_key)
    return _make_serper_request("maps", payload, api_key_str, MapSearchResult)


@action
def search_places(
    q: str,
    api_key: Secret,
    gl: Optional[str] = None,
    location: Optional[str] = None,
    hl: Optional[str] = None,
    tbs: Optional[str] = None,
    autocorrect: Optional[bool] = None,
    num: int = 10,
    page: int = 1
) -> Response[PlaceSearchResult]:
    """
    Search for local businesses and places with contact information, ratings, and categories. Perfect for finding services and establishments.
    
    You can specify the number of places (num, default: 10), page number (page, default: 1), country (gl), and location filter.
    
    Args:
        q: Place search query
        api_key: Serper API key for authentication
        gl: Country code for localized results
        location: Location filter for regional search
        hl: Language code for results
        tbs: Time-based filter for business hours or recency
        autocorrect: Enable automatic spelling correction
        num: Number of places to return
        page: Page number for pagination
    """
    # Validate inputs
    _validate_query(q)
    _validate_positive_integer(num, "num")
    _validate_positive_integer(page, "page")
    
    # Build payload and make request
    base_params = {"q": q, "num": num, "page": page}
    optional_params = {"gl": gl, "location": location, "hl": hl, "tbs": tbs, "autocorrect": autocorrect}
    payload = _build_payload(base_params, optional_params)
    api_key_str = _get_api_key(api_key)
    return _make_serper_request("places", payload, api_key_str, PlaceSearchResult)


@action
def search_reviews(
    api_key: Secret,
    fid: Optional[str] = None,
    cid: Optional[str] = None,
    placeid: Optional[str] = None,
    sortBy: Optional[str] = None,
    topicId: Optional[str] = None,
    nextPageToken: Optional[str] = None,
    gl: Optional[str] = None,
    hl: Optional[str] = None
) -> Response[ReviewSearchResult]:
    """
    Search for customer reviews of specific businesses or places with ratings, dates, and detailed feedback. Perfect for reputation analysis.
    
    Requires at least one ID: business ID (fid), customer ID (cid), or Google Place ID (placeid). You can sort by "Most relevant", "Newest", "Highest rating", or "Lowest rating".
    
    Args:
        api_key: Serper API key for authentication
        fid: Feature/business ID from Google Maps
        cid: Customer/client ID for the business
        placeid: Google Place ID for the location
        sortBy: Sort method for reviews
        topicId: Topic identifier for filtered reviews
        nextPageToken: Pagination token for additional results
        gl: Country code for localized reviews
        hl: Language code for review text
    """
    # Validate inputs
    if not any([fid, cid, placeid]):
        raise ActionError("At least one of fid, cid, or placeid must be provided")
    
    # Build payload and make request
    base_params = {}
    optional_params = {"fid": fid, "cid": cid, "placeid": placeid, "sortBy": sortBy, 
                      "topicId": topicId, "nextPageToken": nextPageToken, "gl": gl, "hl": hl}
    payload = _build_payload(base_params, optional_params)
    api_key_str = _get_api_key(api_key)
    return _make_serper_request("reviews", payload, api_key_str, ReviewSearchResult)


