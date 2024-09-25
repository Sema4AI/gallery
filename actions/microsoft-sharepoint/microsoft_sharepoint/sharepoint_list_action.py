"""Set of actions operating on Sharepoint lists,

Currently supporting:
- Getting all lists related to a Sharepoint site
- Creating a list in a Sharepoint site
"""

from sema4ai.actions import action, OAuth2Secret, Response, ActionError
from typing import Literal
from microsoft_sharepoint.sharepoint_site_action import (
    get_sharepoint_site,
    _get_my_site,
)
from microsoft_sharepoint.models import SharepointList
from microsoft_sharepoint.support import (
    build_headers,
    send_request,
)


@action
def get_sharepoint_lists(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Sites.Read.All"]],
    ],
    site_id: str = "",
    site_name: str = "",
) -> Response[dict]:
    """
    Get lists of the Sharepoint site by site id or site name.

    Use terms 'me', 'my lists', 'mylists', 'my site', 'mysite' to get lists of the user's site.

    Use 'site_id' every time it is available.

    Args:
        site_id: id of the Sharepoint site.
        site_name: name of the Sharepoint site.
        token: OAuth2 token to use for the operation.

    Returns:
        Lists of the Sharepoint site
    """
    if not site_id and not site_name:
        raise ActionError("Either site_id or site_name must be provided")
    headers = build_headers(token)
    mysite = _get_my_site(token)
    if len(site_id) > 0:
        if site_id == mysite["id"]:
            site_name = "My Site"
        else:
            site = get_sharepoint_site(site_id=site_id, token=token)
            site_name = site.result["name"]
        lists = _get_lists(site_id, headers)
    elif site_name.lower() in ["me", "my lists", "mylists", "my site", "mysite"]:
        site_name = "My Site"
        lists = _get_lists(mysite["id"], headers)
    else:
        response = get_sharepoint_site(site_name=site_name, token=token)
        if len(response.result["value"]) == 0:
            raise ActionError(f"Site '{site_name}' not found")
        elif len(response.result["value"]) > 1:
            raise ActionError("Multiple sites with the same name found.")
        site_id = response.result["value"][0]["id"]
        lists = _get_lists(site_id, headers)
    return Response(
        result={"value": {"list_name": f"Lists for {site_name}", "lists": lists}}
    )


def _get_lists(site_id, headers):
    site_id = site_id if len(site_id.split(",")) == 1 else site_id.split(",")[1]
    list_response = send_request(
        "get", f"/sites/{site_id}/lists", "Get site lists", headers=headers
    )
    lists = [
        thelist for thelist in list_response["value"] if not thelist["list"]["hidden"]
    ]
    return lists


@action
def create_sharepoint_list(
    sharepoint_list: SharepointList,
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Sites.ReadWrite.All"]],
    ],
    site_name: str = "",
    site_id: str = "",
) -> Response[dict]:
    """
    Create list in the Sharepoint site by site id or site name.

    Unless specified the column type is by default 'text'.

    Args:
        sharepoint_list: name of the list and columns to create.
        site_name: name of the Sharepoint site.
        site_id: id of the Sharepoint site.
        token: OAuth2 token to use for the operation.

    Returns:
        Result of the operation
    """
    if not site_id and not site_name:
        raise ActionError("Either site_id or site_name must be provided")
    headers = build_headers(token)
    if site_name:
        response = get_sharepoint_site(site_name=site_name, token=token)
        if len(response.result["value"]) == 0:
            raise ActionError(f"Site '{site_name}' not found")
        elif len(response.result["value"]) > 1:
            raise ActionError(
                "Multiple sites with the same name found. Need to have a specific site to add list to."
            )
        site_id = response.result["value"][0]["id"]
    site_id = site_id if len(site_id.split(",")) == 1 else site_id.split(",")[1]
    data = {
        "displayName": sharepoint_list.list_name,
        "description": sharepoint_list.description,
        "columns": [],
        "list": {"template": "genericList"},
    }
    for column in sharepoint_list.columns:
        data["columns"].append({"name": column.column_name, column.column_type: {}})
    response_json = send_request(
        "post", f"/sites/{site_id}/lists", "Create list", headers=headers, data=data
    )
    return Response(result=response_json)
