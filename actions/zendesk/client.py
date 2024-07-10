import re
import urllib.parse
from dataclasses import dataclass
from time import sleep
from typing import Any, Optional

import requests
from sema4ai.actions import ActionError

from models import (
    AddComment,
    CommentsResponse,
    Group,
    Ticket,
    TicketsResponse,
    UpdateTicket,
    User,
    UsersResponse,
)


@dataclass
class BaseApi:
    bearer_token: str
    subdomain: str

    def _call_api(
        self, http_method: Any, endpoint: str, params: Optional[dict[str, Any]] = None
    ) -> requests.Response:
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
        }
        url = urllib.parse.urljoin(self.subdomain, endpoint)

        if http_method == requests.get:
            response = http_method(url, headers=headers, params=params)
        else:
            response = http_method(url, headers=headers, json=params)

        if response.status_code == 429:
            sleep(int(response.headers.get("Retry-After", 1)))

            return self._call_api(http_method, endpoint, params)

        if response.status_code != 200:
            raise ActionError(response.text)

        return response


class TicketsApi(BaseApi):
    QUERY_OPTIONS = {
        "sort_by": "created_at",
        "sort_order": "asc",
        "include": "tickets(users,groups)",
    }

    @staticmethod
    def _add_ticket_type(query: str):
        # Add or replace query type to value 'ticket'
        match = re.search(r"type:(\w+)", query)
        if match:
            type_value = match.group(1)
            if type_value != "ticket":
                query = re.sub(r"type:\w+", "type:ticket", query)
        else:
            # If type is not found, add 'type:ticket' at the end
            query += " type:ticket"

        return query

    def search(self, query: str) -> TicketsResponse:
        query = self._add_ticket_type(query)
        params = {"query": query, **self.QUERY_OPTIONS}

        response = self._call_api(requests.get, "/api/v2/search.json", params).json()

        return TicketsResponse.from_response(response)

    def update(self, ticket_id: str, updates: UpdateTicket) -> Ticket:
        response = self._call_api(
            requests.put,
            f"/api/v2/tickets/{ticket_id}.json",
            updates.to_ticket(),
        ).json()

        return Ticket.model_validate(response["ticket"])


class CommentsApi(BaseApi):
    QUERY_OPTIONS = {
        "sort_by": "created_at",
        "sort_order": "asc",
        "include": "users",
    }

    def get(self, ticket_id: str):
        response = self._call_api(
            requests.get,
            f"/api/v2/tickets/{ticket_id}/comments",
            params=self.QUERY_OPTIONS,
        ).json()

        return CommentsResponse.from_response(response)

    def create(self, ticket_id: str, comment: AddComment) -> str:
        response = self._call_api(
            requests.put,
            f"/api/v2/tickets/{ticket_id}.json",
            comment.to_ticket_comment(),
        )

        return "Successfully created the comment"


class UsersApi(BaseApi):
    def search(self, query: str) -> UsersResponse:
        response = self._call_api(
            requests.get, "/api/v2/users/search.json", {"query": query}
        ).json()

        return UsersResponse.from_response(response)


class GroupsApi(BaseApi):
    def list(self) -> list[Group]:
        response = self._call_api(requests.get, "/api/v2/groups.json").json()

        return [Group.model_validate(group) for group in response["groups"]]
