"""Set of actions searching using DuckDuckGo.

Currently supporting:
- search places in a map location
- search news
- search images
- search videos
- search text

"""

from sema4ai.actions import action, ActionError


import asyncio
import sys
from duckduckgo_search import DDGS


from models import (
    PlaceSearchResult,
    PlaceSearchResultList,
    SearchResultList,
    SearchResult,
    GenericSearchResultList,
)


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


@action(is_consequential=False)
def web_search_places(
    place: str,
    city: str = "",
    country: str = "",
    radius: int = 10,
    max_results: int = 5,
) -> PlaceSearchResultList:
    """Find places in a map location.

    Returned link can be used to check opening hours for the place if hours
    are not already included in the results.

    Args:
        place: place to search for
        city: city to search on
        country: country to search on
        radius: radius to search on (in kilometers)
        max_results: how many results to retrieve

    Returns:
        Details on the place search results.
    """
    parameters = {"max_results": max_results}
    if city:
        parameters["city"] = city
        parameters["radius"] = radius
    if country:
        parameters["country"] = country
        parameters["radius"] = radius
    try:
        results = DDGS().maps(place, **parameters)
        items = []
        for r in results:
            place_result = PlaceSearchResult()
            print(r)
            if "title" in r.keys():
                place_result.title = r["title"]
            if "address" in r.keys():
                place_result.address = r["address"]
            if "phone" in r.keys():
                place_result.phone = r["phone"]
            if "desc" in r.keys():
                place_result.desc = r["desc"]
            if "source" in r.keys():
                place_result.source = r["source"]
            if "latitude" in r.keys():
                place_result.latitude = str(r["latitude"])
            if "longitude" in r.keys():
                place_result.longitude = str(r["longitude"])
            if "url" in r.keys():
                place_result.url = r["url"]
            if "category" in r.keys():
                place_result.category = r["category"]
            items.append(place_result)
        return PlaceSearchResultList(results=items)
    except Exception as err:
        raise ActionError(f"Error in searching places: {err}")


@action(is_consequential=False)
def web_search_news(topic: str, max_results: int = 5) -> SearchResultList:
    """Performs DuckDuckGo Search to find news about a topic.

    Args:
        topic: topic to search on
        max_results: how many results to retrieve

    Returns:
        Titles and links of the results.
    """
    results = DDGS().news(topic, max_results=max_results)
    items = []
    for r in results:
        print(r)
        items.append(SearchResult(title=r["title"], link=r["url"]))
    return SearchResultList(results=items)


@action(is_consequential=False)
def web_search_images(
    keywords: str, type_image: str = "", max_results: int = 10
) -> GenericSearchResultList:
    """Performs DuckDuckGo Search to find images about a topic.

    Args:
        keywords: keywords to search images on
        max_results: count on how many results to retrieve
        type_image: type of image to search on ('photo', 'clipart', 'gif', 'transparent', 'line')

    Returns:
        Image search results.
    """
    try:
        type_image = type_image if type_image != "" else None
        results = DDGS().images(
            keywords=keywords, type_image=type_image, max_results=max_results
        )
        items = []
        for r in results:
            print(r)
            items.append(r)
        return GenericSearchResultList(results=items)
    except Exception as err:
        raise ActionError(f"Error in searching images: {err}")


@action(is_consequential=False)
def web_search_videos(keywords: str, max_results: int = 10) -> GenericSearchResultList:
    """Performs DuckDuckGo Search to find videos about a topic.

    Args:
        keywords: keywords to search videos on
        max_results: count on how many results to retrieve

    Returns:
        Video search results.
    """
    try:
        results = DDGS().videos(
            keywords=keywords, timelimit="y", max_results=max_results
        )
        items = []
        for r in results:
            print(r)
            items.append(r)
        return GenericSearchResultList(results=items)
    except Exception as err:
        raise ActionError(f"Error in searching videos: {err}")


@action(is_consequential=False)
def web_search_text(keywords: str, max_results: int = 10) -> GenericSearchResultList:
    """Performs DuckDuckGo Search to about a topic.

    Args:
        keywords: keywords to search videos on
        max_results: count on how many results to retrieve

    Returns:
        Video search results.
    """
    try:
        results = DDGS().text(keywords=keywords, max_results=max_results)
        items = []
        for r in results:
            print(r)
            items.append(r)
        return GenericSearchResultList(results=items)
    except Exception as err:
        raise ActionError(f"Error in searching text: {err}")
