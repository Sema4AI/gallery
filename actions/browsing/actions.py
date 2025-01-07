"""Set of actions for web browsing.

Currently supporting:
- scrape web page content and elements
- fill form elements
- download file
"""

from sema4ai.actions import action, Response
from robocorp import browser
from playwright.sync_api import TimeoutError
from dotenv import load_dotenv


import os
from pathlib import Path
import requests
from urllib.parse import urlparse


from models import DownloadedFile, Form, Links, WebPage, UserAgent
from support import (
    _configure_browser,
    _ensure_https,
    _get_form_elements,
    _get_page_links,
    _locator_action,
    _get_filename_from_cd,
    _clean_text,
)

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")

HEADLESS_BROWSER = not os.getenv("HEADLESS_BROWSER")
MAX_WAIT_FOR_NETWORK_IDLE = 5000


@action
def get_website_content(url: str, user_agent: UserAgent = {}) -> Response[WebPage]:
    """
    Gets the text content, form elements, links and other elements of a website.
    If content-type is not "text/html" then just URL content is returned.

    Args:
        url: the URL of the website
        user_agent: the user agent to use for browsing

    Returns:
        Text content, form elements and elements of the website.
    """
    url = _ensure_https(url)
    _configure_browser(browser, HEADLESS_BROWSER, user_agent)
    page = browser.page()
    response = page.goto(url)
    page.wait_for_load_state("domcontentloaded")
    try:
        # Wait for network to be idle for 5 seconds, but continue even if not idle
        page.wait_for_load_state("networkidle", timeout=MAX_WAIT_FOR_NETWORK_IDLE)
    except TimeoutError as _:
        pass
    content_type = response.headers.get("content-type", "").lower()
    print(f"content type: {content_type}")
    if "text/html" in content_type:
        text_contents = page.locator("//body").inner_text()
        text_contents = _clean_text(text_contents)
        form = _get_form_elements(page, url)
        links = _get_page_links(page, url)
        wb = WebPage(url=url, text_content=text_contents, form=form, links=links)
    else:
        content = response.body()
        wb = WebPage(
            url=url,
            text_content=_clean_text(content),
            links=Links(links=[]),
            form=Form(url=url, elements=[]),
        )
    print(f"len text_contents: {len(wb.text_content)}")
    print(f"total size: {wb.calculate_total_size()}")
    return wb


@action
def download_file(
    file_url: str, max_filesize_in_megabytes: int = 100, target_folder: str = ""
) -> Response[DownloadedFile]:
    """
    Download a file from the given URL.

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


@action(is_consequential=True)
def fill_elements(
    web_page: WebPage,
) -> str:
    """
    Fill form elements according to input values given in the Form object.

    Args:
        web_page:  details on the web page and its form elements

    Returns:
        Resulting page content after page load.
    """
    browser.configure(browser_engine="chromium", headless=HEADLESS_BROWSER)
    page = browser.goto(web_page.url)
    page.wait_for_load_state("domcontentloaded")
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
        try:
            # Wait for network to be idle for 5 seconds, but continue even if not idle
            page.wait_for_load_state("networkidle", timeout=MAX_WAIT_FOR_NETWORK_IDLE)
        except TimeoutError as _:
            pass
    elif submit_locator:
        print("Click the submit locator")
        submit_locator.click()
        page.wait_for_load_state("domcontentloaded")
        try:
            # Wait for network to be idle for 5 seconds, but continue even if not idle
            page.wait_for_load_state("networkidle", timeout=MAX_WAIT_FOR_NETWORK_IDLE)
        except TimeoutError as _:
            pass
    return page.locator("//body").inner_text()
