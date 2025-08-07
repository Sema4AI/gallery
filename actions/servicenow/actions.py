from datetime import datetime
from typing import Annotated

import sema4ai_http
import urllib3
from pydantic import BaseModel, Field, PlainSerializer, ValidationInfo, model_validator
from sema4ai.actions import Response, Secret, action
from typing_extensions import Self

_Dict = Annotated[dict, PlainSerializer(lambda x: {k: v for k, v in x.items() if v})]


class Pagination(BaseModel):
    limit: int = 20
    next_page: str | None = None

    @classmethod
    def default(cls) -> Self:
        return cls()

    def as_params(self) -> dict:
        return {"sysparm_limit": self.limit}


class ServiceNowResponse(BaseModel):
    items: Annotated[list[_Dict], Field(validation_alias="result")]
    next_page: str | None

    @classmethod
    def from_http_response(cls, response: urllib3.HTTPResponse) -> Self:
        content = response.data.decode("utf-8")
        links = response.headers.get("Link")
        context = {"links": {}}
        if links and 'rel="next"' in links:
            for part in links.split(","):
                if 'rel="next"' in part:
                    url_part = part.split(";")[0].strip().strip("<>")
                    context["links"]["next"] = {"url": url_part}
                    break

        return cls.model_validate_json(content, context=context)

    @model_validator(mode="before")
    def set_links(cls, values: dict, info: ValidationInfo):
        try:
            next_page = info.context["links"]["next"]["url"]
        except (KeyError, TypeError):
            next_page = None

        values["next_page"] = next_page

        return values


@action(is_consequential=False)
def get_my_open_incidents(
    instance_url: Secret,
    username: Secret,
    password: Secret,
    pagination: Pagination = Pagination.default(),
) -> Response[ServiceNowResponse]:
    """Retrieves all open incidents assigned to the user.

    Args:
        instance_url: The ServiceNow instance URL.
        username: The username of the user to authenticate.
        password: The password of the user to authenticate.
        pagination: An object for pagination containing `limit` which denotes the number of items per page
            and `next_page` the url to load the next page.
    Returns:
        A structure representing the incidents.
    """

    incidents = _get_incidents(
        instance_url,
        username,
        password,
        {
            "active": "true",
            "assigned_to": username.value,
        },
        pagination=pagination,
    )

    return Response(result=incidents)


@action(is_consequential=False)
def get_recent_incidents(
    instance_url: Secret,
    username: Secret,
    password: Secret,
    pagination: Pagination = Pagination.default(),
) -> Response[ServiceNowResponse]:
    """Retrieves the incident created today

    Args:
        instance_url: The ServiceNow instance URL.
        username: The username of the user to authenticate.
        password: The password of the user to authenticate.
        pagination: An object for pagination containing `limit` which denotes the number of items per page
            and `next_page` the url to load the next page.
    Returns:
        A structure representing the incidents.
    """
    today = datetime.today().strftime("%Y-%m-%d")

    incidents = _get_incidents(
        instance_url,
        username,
        password,
        {
            "sysparm_query": f"sys_created_on>={today}",
        },
        pagination=pagination,
    )

    return Response(result=incidents)


@action(is_consequential=False)
def search_incidents(
    instance_url: Secret,
    username: Secret,
    password: Secret,
    sysparm_query: str,
    pagination: Pagination = Pagination.default(),
) -> Response[ServiceNowResponse]:
    """Retrieves all open incidents assigned to the user.

    Args:
        instance_url: The ServiceNow instance URL.
        username: The username of the user to authenticate.
        password: The password of the user to authenticate.
        sysparm_query: The query param to use for searching the incidents.
            You should build this yourself based on what the user asks of you and using your current knowledge of ServiceNow API
        pagination: An object for pagination containing `limit` which denotes the number of items per page
            and `next_page` the url to load the next page.
    Returns:
        A structure representing the incidents.
    """

    incidents = _get_incidents(
        instance_url,
        username,
        password,
        {
            "sysparm_query": sysparm_query,
        },
        pagination=pagination,
    )

    return Response(result=incidents)


@action(is_consequential=False)
def get_users(
    instance_url: Secret,
    username: Secret,
    password: Secret,
    pagination: Pagination = Pagination.default(),
) -> Response[ServiceNowResponse]:
    """Retrieves all the users registered on the ServiceNow instance.

    Args:
        instance_url: The ServiceNow instance URL.
        username: The username of the user to authenticate.
        password: The password of the user to authenticate.
        pagination: An object for pagination containing `limit` which denotes the number of items per page
            and `next_page` the url to load the next page.
    Returns:
        A structure representing the users.
    """
    headers = urllib3.make_headers(basic_auth=f"{username.value}:{password.value}")
    fields = {
        "sysparm_exclude_reference_link": "true",
        "sysparm_display_value": "true",
    }

    if pagination.next_page:
        raw_response = sema4ai_http.get(
            pagination.next_page, headers=headers, fields=fields
        )
    else:
        raw_response = sema4ai_http.get(
            f"{instance_url.value.rstrip('/')}/api/now/table/sys_user",
            headers=headers,
            fields={**pagination.as_params(), **fields},
        )

    raw_response.raise_for_status()

    return Response(result=ServiceNowResponse.from_http_response(raw_response))


def _get_incidents(
    instance_url: str,
    username: str,
    password: str,
    params: dict[str, str],
    *,
    pagination: Pagination,
) -> ServiceNowResponse:
    headers = urllib3.make_headers(basic_auth=f"{username.value}:{password.value}")
    common_params = {
        **pagination.as_params(),
        **params,
        "sysparm_exclude_reference_link": "true",
        "sysparm_display_value": "true",
    }
    if pagination.next_page:
        raw_response = sema4ai_http.get(
            pagination.next_page, headers=headers, fields=common_params
        )
    else:
        raw_response = sema4ai_http.get(
            f"{instance_url.value.rstrip('/')}/api/now/table/incident",
            headers=headers,
            fields={**pagination.as_params(), **params, **common_params},
        )

    raw_response.raise_for_status()

    return ServiceNowResponse.from_http_response(raw_response)
