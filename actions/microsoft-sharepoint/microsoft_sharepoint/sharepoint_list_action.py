"""Set of actions operating on Sharepoint lists,

Currently supporting:
- Getting all lists related to a Sharepoint site
- Creating a list in a Sharepoint site
"""

import requests
from sema4ai.actions import action, OAuth2Secret, Response, ActionError
from typing import Literal
from microsoft_sharepoint.sharepoint_site_action import get_sharepoint_site_id
from microsoft_sharepoint.models import SharepointList
from microsoft_sharepoint.support import (
    BASE_GRAPH_URL,
    build_headers,
)


@action
def get_sharepoint_lists(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Sites.Read.All"]],
    ],
    site_name: str = "",
    site_id: str = "",
) -> Response[dict]:
    """
    Get lists of the Sharepoint site by site id or site name.

    Args:
        site_name: name of the Sharepoint site.
        site_id: id of the Sharepoint site.
        token: OAuth2 token to use for the operation.

    Returns:
        Lists of the Sharepoint site
    """
    if not site_id and not site_name:
        raise ActionError("Either site_id or site_name must be provided")
    if site_name:
        response = get_sharepoint_site_id(site_name=site_name, token=token)
        if len(response.result["value"]) > 1:
            raise ActionError(
                "Multiple sites with the same name found. Need to have a specific site to add list to."
            )
        site_id = response.result["value"][0]["id"]
    headers = build_headers(token)
    response = requests.get(f"{BASE_GRAPH_URL}/sites/{site_id}/lists", headers=headers)
    if response.status_code in [200, 201]:
        return Response(result=response.json())
    else:
        raise ActionError(f"Failed to get site lists: {response.text}")


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
    if site_name:
        response = get_sharepoint_site_id(site_name=site_name, token=token)
        if len(response.result["value"]) > 1:
            raise ActionError(
                "Multiple sites with the same name found. Need to have a specific site to add list to."
            )
        site_id = response.result["value"][0]["id"]
    headers = build_headers(token)
    data = {
        "displayName": sharepoint_list.list_name,
        "columns": [],
        "list": {"template": "genericList"},
    }
    for column in sharepoint_list.columns:
        data["columns"].append({"name": column.column_name, column.column_type: {}})
    response = requests.post(
        f"{BASE_GRAPH_URL}/sites/{site_id}/lists", headers=headers, json=data
    )
    if response.status_code in [200, 201]:
        return Response(result=response.json())
    else:
        raise ActionError(f"Failed to create site list: {response.text}")
