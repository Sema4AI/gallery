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
    response_json = send_request(
        "get", f"/sites?search={site_name}", "Get site id", headers=headers
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
    return Response(result=response_json)
