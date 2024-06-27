"""Set of actions operating on Sharepoint sites,

Currently supporting:
- Getting all sites known to the user
- Getting site id by site name
- Getting site by site id
"""

import requests
from sema4ai.actions import action, OAuth2Secret, Response, ActionError
from typing import Literal
from microsoft_sharepoint.support import (
    BASE_GRAPH_URL,
    build_headers,
)


@action
def get_sharepoint_site_id(
    site_name: str,
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Sites.Read.All"]],
    ],
) -> Response[dict]:
    """
    Get the site id of the Sharepoint site by its name

    Args:
        site_name: name of the Sharepoint site.
        token: OAuth2 token to use for the operation.

    Returns:
        Site details including the site id or error message
    """
    headers = build_headers(token)
    response = requests.get(
        f"{BASE_GRAPH_URL}/sites?search={site_name}",
        headers=headers,
    )
    if response.status_code in [200, 201]:
        return Response(result=response.json())
    else:
        raise ActionError(f"Failed to get site id: {response.text}")


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
        filename: name of the file.
        token: OAuth2 token to use for the operation.

    Returns:
        Result of the operation
    """
    if not site_id and not site_name:
        raise ActionError("Either site_id or site_name must be provided")
    if site_name:
        response = get_sharepoint_site_id(site_name=site_name, token=token)
        if len(response.result["value"]) > 1:
            raise ActionError("Multiple sites with the same name found.")
        site_id = response.result["value"][0]["id"]
    headers = build_headers(token)
    response = requests.get(
        f"{BASE_GRAPH_URL}/sites/{site_id}",
        headers=headers,
    )
    if response.status_code in [200, 201]:
        return Response(result=response.json())
    else:
        raise ActionError(f"Failed to get a site: {response.text}")


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
    response = requests.get(
        f"{BASE_GRAPH_URL}/sites?search=*",
        headers=headers,
    )
    if response.status_code in [200, 201]:
        return Response(result=response.json())
    else:
        raise ActionError(f"Failed to sites: {response.text}")
