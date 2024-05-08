"""Set of actions for searching and web browsing.

Currently supporting:
- google search
- scrape web page content and elements
- fill form elements
- search places in a map location
- search news
- download file
"""

from sema4ai.actions import action, Secret
from robocorp import browser

from dotenv import load_dotenv

import asyncio
import sys
from duckduckgo_search import DDGS
import os
import requests
from urllib.parse import urlparse

from models import (
    DownloadedFile,
    WebPage,
    PlaceSearchResult,
    PlaceSearchResultList,
    SearchResultList,
    SearchResult,
)
from support import (
    _ensure_https,
    _get_form_elements,
    _get_page_links,
    _locator_action,
    _get_filename_from_cd,
)

load_dotenv()

HEADLESS_BROWSER = not os.getenv("HEADLESS_BROWSER")
API_KEY_FIELD = "GOOGLE_SEARCH_API_KEY"
CONTEXT_FIELD = "GOOGLE_SEARCH_CONTEXT"

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


@action(is_consequential=False)
def get_website_content(url: str) -> WebPage:
    """Gets the text content, form elements, links and other elements of a website.

    If url ends with .csv then use 'download_file' action.

    Args:
        url: the URL of the website

    Returns:
        Text content, form elements and elements of the website.
    """
    url = _ensure_https(url)
    browser.configure(browser_engine="chromium", headless=HEADLESS_BROWSER)
    page = browser.goto(url)
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_load_state("networkidle")
    text_contents = page.locator("//body").inner_text()
    form = _get_form_elements(page, url)
    links = _get_page_links(page, url)
    wb = WebPage(url=url, text_content=text_contents, form=form, links=links)
    print(text_contents)
    print(f"len text_contents: {len(text_contents)}")
    return wb


@action(is_consequential=False)
def download_file(
    file_url: str, max_filesize_in_megabytes: int = 100, target_folder: str = ""
) -> DownloadedFile:
    """Download a file from the given URL.

    Args:
        file_url: the URL of the file to download
        max_filesize_in_megabytes: maximum file size in MB to download
        target_folder: folder to download the file

    Returns:
        Content of the file (if text), the filepath where file is download and
        status of the download.
    """
    df = DownloadedFile(
        content="",
        filepath="",
        status="",
        request_status=200,
        content_type="",
        content_length=0,
    )
    try:
        with requests.get(file_url, stream=True) as response:
            df.request_status = response.status_code
            response.raise_for_status()  # Check for HTTP errors

            # Attempt to fetch the filename from the Content-Disposition header
            content_disposition = response.headers.get("Content-Disposition", "")
            filename = _get_filename_from_cd(content_disposition)

            # If no filename in the header, extract from URL
            if not filename:
                filename = os.path.basename(urlparse(file_url).path)

            # Check file type and size from headers
            df.content_type = response.headers.get("Content-Type", "")
            df.content_length = int(response.headers.get("Content-Length", 0))
            print(f"Content-Type: {df.content_type}")
            print(f"Content-Length: {df.content_length} bytes")

            if df.content_length > max_filesize_in_megabytes * 1000000:
                df.status = f"File is too large to download - limit is {max_filesize_in_megabytes} MB"
                return df

            # Check if content is text-based or binary
            if "text" in df.content_type:
                df.content = response.text

            if target_folder == "":
                target_folder = os.getcwd()
            file_path = os.path.join(target_folder, filename)
            with open(file_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            df.status = f"File downloaded successfully at: {os.path.abspath(file_path)}"
            df.filepath = os.path.abspath(file_path)  # Return the full path of the file
    except Exception as e:
        df.filepath = ""
        df.status = f"Download failed: {str(e)}"
    print(df.status)
    return df


@action(is_consequential=False)
def web_search_places(
    place: str, city: str = "", country: str = "", radius: int = 10, count: int = 3
) -> PlaceSearchResultList:
    """Find places in a map location.

    Returned link can be used to check opening hours for the place if hours
    are not already included in the results.

    Args:
        place: place to search for
        city: city to search on
        country: country to search on
        radius: radius to search on (in kilometers)
        count: count on how many results to retrieve

    Returns:
        Details on the place search results.
    """
    ddgs = DDGS()
    parameters = {"max_results": count}
    if city:
        parameters["city"] = city
        parameters["radius"] = radius
    if country:
        parameters["country"] = country
        parameters["radius"] = radius
    results = ddgs.maps(place, **parameters)
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


@action(is_consequential=False)
def google_search(
    topic: str,
    count: int = 3,
    api_key: Secret = Secret.model_validate(os.getenv(API_KEY_FIELD, "")),
    context: Secret = Secret.model_validate(os.getenv(CONTEXT_FIELD, "")),
) -> SearchResultList:
    """Performs Google Search to find information about a topic.

    Secrets are required. Do not call if they are given.

    To list all possible results use count=0.

    Args:
        topic: topic to search on
        count: count on how many results to retrieve

    Returns:
        Titles and links of the results.
    """
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key.value or os.getenv(API_KEY_FIELD, ""),
        "cx": context.value or os.getenv(CONTEXT_FIELD, ""),
        "q": topic,
    }
    response = requests.get(url, params=params)
    result = response.json()
    items = []
    if "items" in result.keys():
        for item in result["items"]:
            items.append(
                SearchResult(
                    title=item["title"], link=item["link"], desc=item["snippet"]
                )
            )

    message = f"Found {len(items)} results for '{topic}'"
    if count > 0:
        message += f" and returning {count} of those."
    print(message)
    return (
        SearchResultList(results=items[:count])
        if count > 0
        else SearchResultList(results=items)
    )


@action(is_consequential=True)
def fill_elements(
    web_page: WebPage,
) -> str:
    """Fill form elements according to input values given in the Form object.

    Args:
        web_page:  details on the web page and its form elements

    Returns:
        Resulting page content after page load.
    """
    browser.configure(browser_engine="chromium", headless=HEADLESS_BROWSER)
    page = browser.goto(web_page.url)
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_load_state("networkidle")
    locator = None
    submit_locator = None
    for element in web_page.form.elements:
        if element.value_type == "submit":
            submit_locator = page.locator(f"xpath=//{element.type}[@type='submit']")
        if element.value_to_fill == "":
            continue
        if element.id:
            locator = page.locator(f"css=#{element.id}")
            print(f"selected element with id: {element.id}")
            _locator_action(locator, element)
        elif element.class_:
            locator = page.locator(f"css=.{element.class_}")
            print(f"selected element with class: {element.class_}")
            _locator_action(locator, element)
        elif element.placeholder:
            locator = page.get_by_placeholder(element.placeholder)
            print(f"selected element with placeholder: {element.placeholder}")
            _locator_action(locator, element)
        elif element.aria_label:
            locator = page.locator(
                f"//{element.type}[@aria-label='{element.aria_label}']"
            )
            print(f"selected element with aria_label: {element.aria_label}")
            _locator_action(locator, element)

    if locator:
        print("Enter the locator")
        locator.press("Enter")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_load_state("networkidle")
    elif submit_locator:
        print("Click the submit locator")
        submit_locator.click()
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_load_state("networkidle")
    return page.locator("//body").inner_text()


@action(is_consequential=False)
def web_search_news(topic: str, count: int = 3) -> SearchResultList:
    """Performs DuckDuckGo Search to find news about a topic.

    Args:
        topic: topic to search on
        count: count on how many results to retrieve

    Returns:
        Titles and links of the results.
    """
    ddgs = DDGS()
    results = ddgs.news(topic, max_results=count)
    items = []
    for r in results:
        print(r)
        items.append(SearchResult(title=r["title"], link=r["url"]))
    return SearchResultList(results=items)
