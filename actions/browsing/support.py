from models import (
    Links,
    Link,
    Form,
    FormElement,
    Option,
)
from urllib.parse import unquote, urlparse


def _get_form_elements(page, url) -> Form:
    page_form = Form(url=url, elements=[])
    _get_elements_by_type(page, "input", page_form)
    _get_elements_by_type(page, "button", page_form)
    _get_elements_by_type(page, "select", page_form)
    _get_elements_by_type(page, "textarea", page_form)
    _get_elements_by_type(page, "table", page_form)
    return page_form


def _get_page_links(page, url) -> Links:
    link_elements = page.locator("//a").all()
    links = []
    for element in link_elements:
        if not element.is_visible():
            continue
        href = element.get_attribute("href")
        text = element.text_content().strip()
        if href and "http" not in href:
            parsed_url = urlparse(url)
            href = f"{parsed_url.scheme}://{parsed_url.netloc}{href}"
        links.append(Link(href=href or "", text=text or ""))
    return Links(links=links)


def _get_elements_by_type(page, element_type, page_form):
    elements = page.locator(f"//{element_type}").all()
    print(f"len {element_type}: {len(elements)}")
    form_elements = {}
    for element in elements:
        options = []
        if element_type == "select":
            select_options = element.locator("option").all()
            options = [
                Option(
                    value=option.get_attribute("value"),
                    text=option.text_content().strip(),
                )
                for option in select_options
            ]

        fe = FormElement(
            type=element_type,
            text=element.text_content(),
            placeholder=element.get_attribute("placeholder") or "",
            aria_label=element.get_attribute("aria-label") or "",
            value_type=element.get_attribute("type") or "",
            class_=element.get_attribute("class") or "",
            id=element.get_attribute("id") or "",
            name=element.get_attribute("name") or "",
            options=options,
        )
        if fe in form_elements:
            existing_element = form_elements[fe]
            existing_element.count += 1
        else:
            fe.count = 1
            form_elements[fe] = fe
    page_form.elements.extend(form_elements.values())
    return page_form


def _ensure_https(url):
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _locator_action(locator, element):
    if element.type == "button":
        locator.click()
    elif element.type == "select":
        locator.select_option(element.value_to_fill)
    else:
        locator.fill(element.value_to_fill)


def _get_filename_from_cd(cd):
    """
    Get filename from content-disposition header if available.
    """
    if not cd:
        return None
    fname = cd.split("filename=")[1] if "filename=" in cd else None
    return unquote(fname.strip('"')) if fname else None


def _configure_browser(browser, headless_mode, user_agent):
    extras = {}
    if user_agent and user_agent.name != "":
        extras["user_agent"] = user_agent.name
    browser.configure(browser_engine="chromium", headless=headless_mode)
    if extras:
        browser.configure_context(**extras)
