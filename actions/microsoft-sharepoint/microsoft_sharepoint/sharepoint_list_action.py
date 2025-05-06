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
from microsoft_sharepoint.models import SharepointList, SharepointListItem, ListItem
from microsoft_sharepoint.support import (
    build_headers,
    send_request,
    NotFound,
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
        site_id = response.result["id"]
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


def _get_list_fields(site_id, list_id, headers):
    """Retrieve the fields (columns) of a SharePoint list.

    Args:
        site_id: ID of the SharePoint site.
        list_id: ID of the SharePoint list.
        headers: Auth headers.

    Returns:
        Dict mapping lower-case field names to their canonical names.
    """
    response = send_request(
        "get",
        f"/sites/{site_id}/lists/{list_id}/columns",
        "Get list columns",
        headers=headers,
    )
    # Map lower-case field names to canonical names for case-insensitive matching
    return {col["name"].lower(): col["name"] for col in response.get("value", [])}


def _map_fields_to_list_columns(incoming_fields, list_fields):
    """Map incoming fields to SharePoint list columns, handling case sensitivity and best-effort matching.

    Args:
        incoming_fields: List of dicts (as per new ListItem model) or a dict of incoming field names and values.
        list_fields: Dict mapping lower-case field names to canonical names.

    Returns:
        Dict of mapped fields suitable for SharePoint API.
    """
    # If incoming_fields is a list (as per new ListItem), merge all dicts into one
    if isinstance(incoming_fields, list):
        merged_fields = {}
        for d in incoming_fields:
            if isinstance(d, dict):
                merged_fields.update(d)
        incoming_fields = merged_fields
    mapped = {}
    for key, value in incoming_fields.items():
        canonical = list_fields.get(key.lower())
        if canonical:
            mapped[canonical] = value
        # else: skip fields not present in the list
    return mapped


@action
def create_sharepoint_list(
    sharepoint_list: SharepointList,
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Sites.Manage.All"]],
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
    print(f"GOT: {sharepoint_list}")
    if not site_id and not site_name:
        raise ActionError("Either site_id or site_name must be provided")
    headers = build_headers(token)
    if site_name:
        response = get_sharepoint_site(site_name=site_name, token=token)
        site_id = response.result["id"]
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


@action
def add_sharepoint_list_item(
    new_item: ListItem,
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Sites.Manage.All"]],
    ],
    site_id: str = "",
    site_name: str = "",
    list_id: str = "",
    list_name: str = "",
) -> Response[dict]:
    """
    Add a new item to a SharePoint list.

    Args:
        new_item: The item to add (fields as dict).
        site_id: ID of the SharePoint site.
        site_name: Name of the SharePoint site.
        list_id: ID of the SharePoint list.
        list_name: Name of the SharePoint list.
        token: OAuth2 token to use for the operation.

    Returns:
        Result of the operation
    """
    if not site_id and not site_name:
        raise ActionError("Either site_id or site_name must be provided")
    if not new_item.fields:
        raise ActionError("Cannot create an empty list item. At least one field must be provided.")
    headers = build_headers(token)
    if site_name and not site_id:
        response = get_sharepoint_site(site_name=site_name, token=token)
        site_id = response.result["id"]
    site_id = site_id if len(site_id.split(",")) == 1 else site_id.split(",")[1]
    if not list_id and list_name:
        found = _find_list_by_name(site_id, headers, list_name)
        if not found:
            raise ActionError(f"List '{list_name}' not found")
        list_id = found["id"]
    if not list_id:
        raise ActionError("Either list_id or list_name must be provided")
    columns = _get_list_fields(site_id, list_id, headers)
    data = {"fields": _map_fields_to_list_columns(new_item.fields, columns)}
    response_json = send_request(
        "post",
        f"/sites/{site_id}/lists/{list_id}/items",
        "Add list item",
        headers=headers,
        data=data,
    )
    return Response(result=response_json)


@action
def update_sharepoint_list_item(
    update_item: SharepointListItem,
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Sites.Manage.All"]],
    ],
    site_id: str = "",
    site_name: str = "",
    list_id: str = "",
    list_name: str = "",
) -> Response[dict]:
    """
    Update an existing item in a SharePoint list.

    Args:
        update_item: The item to update (must include item_id and fields).
        site_id: ID of the SharePoint site.
        site_name: Name of the SharePoint site.
        list_id: ID of the SharePoint list.
        list_name: Name of the SharePoint list.
        token: OAuth2 token to use for the operation.

    Returns:
        Result of the operation
    """
    if not update_item.item_id:
        raise ActionError("item_id must be provided in the item")
    if not site_id and not site_name:
        raise ActionError("Either site_id or site_name must be provided")
    headers = build_headers(token)
    if site_name and not site_id:
        response = get_sharepoint_site(site_name=site_name, token=token)
        site_id = response.result["id"]
    site_id = site_id if len(site_id.split(",")) == 1 else site_id.split(",")[1]
    if not list_id and list_name:
        found = _find_list_by_name(site_id, headers, list_name)
        if not found:
            raise ActionError(f"List '{list_name}' not found")
        list_id = found["id"]
    if not list_id:
        raise ActionError("Either list_id or list_name must be provided")

    columns = _get_list_fields(site_id, list_id, headers)
    data = {"fields": _map_fields_to_list_columns(update_item.fields.fields, columns)}
    response_json = send_request(
        "patch",
        f"/sites/{site_id}/lists/{list_id}/items/{update_item.item_id}",
        "Update list item",
        headers=headers,
        data=data,
    )
    return Response(result=response_json)


@action
def delete_sharepoint_list_item(
    item_id: str,
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Sites.Manage.All"]],
    ],
    site_id: str = "",
    site_name: str = "",
    list_id: str = "",
    list_name: str = "",
) -> Response[dict]:
    """
    Delete an item from a SharePoint list.

    Args:
        item_id: ID of the item to delete.
        site_id: ID of the SharePoint site.
        site_name: Name of the SharePoint site.
        list_id: ID of the SharePoint list.
        list_name: Name of the SharePoint list.
        token: OAuth2 token to use for the operation.

    Returns:
        Result of the operation
    """
    if not item_id:
        raise ActionError("item_id must be provided")
    if not site_id and not site_name:
        raise ActionError("Either site_id or site_name must be provided")
    headers = build_headers(token)
    if site_name and not site_id:
        response = get_sharepoint_site(site_name=site_name, token=token)
        site_id = response.result["id"]
    site_id = site_id if len(site_id.split(",")) == 1 else site_id.split(",")[1]
    if not list_id and list_name:
        found = _find_list_by_name(site_id, headers, list_name)
        if not found:
            raise ActionError(f"List '{list_name}' not found")
        list_id = found["id"]
    if not list_id:
        raise ActionError("Either list_id or list_name must be provided")

    try:
        response_json = send_request(
            "delete",
            f"/sites/{site_id}/lists/{list_id}/items/{item_id}",
            "Delete list item",
            headers=headers,
        )
    except NotFound:
        raise ActionError(f"Item '{item_id}' not found")
    return Response(result=response_json)


@action
def get_sharepoint_list_items(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Sites.Read.All"]],
    ],
    site_id: str = "",
    site_name: str = "",
    list_id: str = "",
    list_name: str = "",
    top: int = 100,
) -> Response[dict]:
    """
    Get items from a SharePoint list by site and list id or name.

    Args:
        site_id: ID of the SharePoint site.
        site_name: Name of the SharePoint site.
        list_id: ID of the SharePoint list.
        list_name: Name of the SharePoint list.
        token: OAuth2 token to use for the operation.
        top: Maximum number of items to return (default 100).

    Returns:
        List of items in the SharePoint list
    """
    if not site_id and not site_name:
        raise ActionError("Either site_id or site_name must be provided")
    headers = build_headers(token)
    if site_name and not site_id:
        response = get_sharepoint_site(site_name=site_name, token=token)
        site_id = response.result["id"]
    site_id = site_id if len(site_id.split(",")) == 1 else site_id.split(",")[1]
    if not list_id and list_name:
        found = _find_list_by_name(site_id, headers, list_name)
        if not found:
            raise ActionError(f"List '{list_name}' not found")
        list_id = found["id"]
    if not list_id:
        raise ActionError("Either list_id or list_name must be provided")
    params = {"$top": top, "$expand": "fields"}
    response_json = send_request(
        "get",
        f"/sites/{site_id}/lists/{list_id}/items",
        "Get list items",
        headers=headers,
        params=params,
    )
    items = response_json.get("value", [])
    fields_list = [item.get("fields", {}) for item in items]
    return Response(result={"items": fields_list})


def _find_list_by_name(site_id, headers, list_name):
    """Find a list by name (case-insensitive) for a site.
    If site_id is a comma-separated string, extract the actual site id (second part).
    """
    # Handle site_id like 'host,siteid,webid' by extracting the second part
    if "," in site_id:
        parts = site_id.split(",")
        if len(parts) > 1:
            site_id = parts[1]
    lists = _get_lists(site_id, headers)
    return next((l for l in lists if l["name"].lower() == list_name.lower()), None)
