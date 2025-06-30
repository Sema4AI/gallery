"""Set of actions operating on Sharepoint sites,

Currently supporting:
- Getting all sites known to the user
- Getting site id by site name
- Getting site by site id
"""

from sema4ai.actions import action, OAuth2Secret, Response, ActionError
from typing import Literal
from microsoft_sharepoint.support import (
    build_headers,
    send_request,
)
import re


@action
def search_for_site(
    search_string: str,
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Sites.Read.All"]],
    ],
) -> Response[dict]:
    """
    Search for a Sharepoint site by name or by domain/hostname.

    Args:
        search_string: name of the Sharepoint site or hostname (e.g. 'beissi-my.sharepoint.com').
        token: OAuth2 token to use for the operation.

    Returns:
        Site details including the site id or error message
    """
    headers = build_headers(token)
    # If the input looks like a domain, use the /sites/{hostname}:/ endpoint
    if re.match(r"^[a-zA-Z0-9.-]+\.sharepoint\.com$", search_string.strip()):
        hostname = search_string.strip()
        try:
            site = send_request(
                "get",
                f"/sites/{hostname}:/",
                f"Get site by hostname: {hostname}",
                headers=headers,
            )
            # Return in the same format as the search endpoint
            return Response(result={"value": [site]})
        except Exception as e:
            return Response(result={"value": []})
    # Otherwise, use the search endpoint
    response_json = send_request(
        "get", f"/sites?search={search_string}", "Search for site", headers=headers
    )
    return Response(result=response_json)


@action
def get_sharepoint_site(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Sites.Read.All"]],
    ],
    site_id: str = "",
    site_name: str = "",
) -> Response[dict]:
    """
    Get the Sharepoint site either by id or by name.

    Args:
        site_id: id of the Sharepoint site.
        site_name: name of the Sharepoint site.
        token: OAuth2 token to use for the operation.

    Returns:
        Site details or error message
    """
    if not site_id and not site_name:
        raise ActionError("Either site_id or site_name must be provided")
    if site_id != "":
        pass
    elif site_name.lower() in ["me", "my site", "mysite"]:
        mysite = _get_my_site(token)
        site_id = mysite["id"]
    else:
        response = search_for_site(search_string=site_name, token=token)
        # Filter results case-insensitively
        matches = [site for site in response.result["value"] if site["displayName"].lower() == site_name.lower()]
        if len(matches) > 1:
            raise ActionError(f"Multiple sites with the same name '{site_name}' found.")
        elif len(matches) == 0:
            raise ActionError(f"No site found with the given name '{site_name}'.")
        else:
            site_id = matches[0]["id"]
    site_id = site_id if len(site_id.split(",")) == 1 else site_id.split(",")[1]
    headers = build_headers(token)
    response_json = send_request(
        "get", f"/sites/{site_id}", "Get site", headers=headers
    )
    return Response(result=response_json)


@action
def get_all_sharepoint_sites(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Sites.Read.All"]],
    ],
) -> Response[dict]:
    """
    Get all Sharepoint sites known to the user.

    Args:
        token: OAuth2 token to use for the operation.

    Returns:
        Result of the operation
    """
    headers = build_headers(token)
    response_json = send_request(
        "get", "/sites?search=*", "Get all sites", headers=headers
    )
    mysite = _get_my_site(token)
    response_json["value"].append(mysite)
    return Response(result=response_json)


def _get_my_site(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Sites.Read.All"]],
    ]
) -> dict:
    """
    Get the site details of the current user's personal site.

    Args:
        token: OAuth2 token to use for the operation.

    Returns:
        Result of the operation
    """
    headers = build_headers(token)
    user_data = send_request(
        "get",
        "/me?$select=mySite",
        req_name="Get the current user's information",
        headers=headers,
    )
    my_site_url = user_data["mySite"]
    # Extract hostname and personal site path from the mySite URL
    my_site_url_parts = my_site_url.split("/")
    hostname = my_site_url_parts[2]
    personal_site_path = "/".join(my_site_url_parts[3:-1])

    site_data = send_request(
        "get",
        f"/sites/{hostname}:/{personal_site_path}",
        "Get the site details",
        headers=headers,
    )
    return site_data
