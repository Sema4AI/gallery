"""
A bare-bone AI Action template

Please check out the base guidance on AI Actions in our main repository readme:
https://github.com/sema4ai/actions/blob/master/README.md

"""

from contextlib import contextmanager
from datetime import datetime
from typing import Annotated

from httpx import Client, HTTPStatusError
from httpx import Response as HttpxResponse
from pydantic import BaseModel, Field, PlainSerializer, ValidationInfo, model_validator
from sema4ai.actions import ActionError, Response, Secret, action
from sema4ai_http import build_ssl_context
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
    def from_http_response(cls, response: HttpxResponse) -> Self:
        return cls.model_validate_json(
            response.read(), context={"links": response.links}
        )

    @model_validator(mode="before")
    def set_links(cls, values: dict, info: ValidationInfo):
        try:
            next_page = info.context["links"]["next"]["url"]
        except (KeyError, TypeError):
            next_page = None

        values["next_page"] = next_page

        return values


@contextmanager
def get_client(instance_url: Secret, username: Secret, password: Secret) -> Client:
    with Client(
        base_url=instance_url.value.rstrip("/"),
        auth=(username.value, password.value),
        verify=build_ssl_context(),
        params={
            "sysparm_exclude_reference_link": "true",
            "sysparm_display_value": "true",
        },
    ) as client:
        try:
            yield client
        except HTTPStatusError as exc:
            raise ActionError(
                f"[HTTP Error] status: {exc.response.status_code}, error: {exc.response.text}"
            ) from None


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

    with get_client(instance_url, username, password) as client:
        incidents = _get_incidents(
            client,
            {
                "active": "true",
                "assigned_to": username.value,
            },
            pagination=pagination,
        )

    return incidents


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

    with get_client(instance_url, username, password) as client:
        incidents = _get_incidents(
            client,
            {
                "sysparm_query": f"sys_created_on>={today}",
            },
            pagination=pagination,
        )

    return incidents


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
        pagination: An object for pagination containing `limit` which denotes the number of items per page.
        and `next_page` the url to load the next page.
    Returns:
        A structure representing the incidents.
    """

    with get_client(instance_url, username, password) as client:
        incidents = _get_incidents(
            client,
            {
                "sysparm_query": sysparm_query,
            },
            pagination=pagination,
        )

    return incidents


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
    with get_client(instance_url, username, password) as client:
        if pagination.next_page:
            raw_response = client.get(pagination.next_page)
        else:
            raw_response = client.get(
                "/api/now/table/sys_user",
                params=pagination.as_params(),
            )

        return ServiceNowResponse.from_http_response(raw_response.raise_for_status())


def _get_incidents(
    client: Client, params: dict[str, str], *, pagination: Pagination
) -> ServiceNowResponse:
    if pagination.next_page:
        raw_response = client.get(pagination.next_page)
    else:
        raw_response = client.get(
            "/api/now/table/incident", params={**pagination.as_params(), **params}
        ).raise_for_status()

    return ServiceNowResponse.from_http_response(raw_response)
