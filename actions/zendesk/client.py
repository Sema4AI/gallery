import re
import urllib.parse
from dataclasses import dataclass
from time import sleep
from typing import Any, Optional

import sema4ai_http
from sema4ai.actions import ActionError

from models import (
    AddComment,
    CommentsResponse,
    Group,
    Tag,
    Ticket,
    TicketsResponse,
    UpdateTicket,
    UsersResponse,
)


@dataclass
class BaseApi:
    bearer_token: str
    subdomain: str

    def _call_api(
        self,
        http_method: Any,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
    ) -> sema4ai_http.ResponseWrapper:
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
        }
        url = urllib.parse.urljoin(self.subdomain, endpoint)

        if http_method == sema4ai_http.get:
            response = http_method(url, headers=headers, fields=params)
        else:
            response = http_method(url, headers=headers, json=params)

        if response.status_code == 429:
            sleep(int(response.headers.get("Retry-After", 1)))

            return self._call_api(http_method, endpoint, params)

        if response.status_code not in [200, 204]:
            raise ActionError(response.text)

        return response


class TicketsApi(BaseApi):
    QUERY_OPTIONS = {
        "sort_by": "created_at",
        "sort_order": "asc",
        "include": "tickets(users,groups,organizations)",
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

        response = self._call_api(
            sema4ai_http.get, "/api/v2/search.json", params
        ).json()

        return TicketsResponse.from_response(response)

    def update(self, ticket_id: str, updates: UpdateTicket) -> Ticket:
        response = self._call_api(
            sema4ai_http.put,
            f"/api/v2/tickets/{ticket_id}.json",
            updates.to_ticket(),
        ).json()

        return Ticket.model_validate(response["ticket"])

    def create(
        self, comment: str, priority: str, subject: str, tags: str
    ) -> Ticket:
        response = self._call_api(
            sema4ai_http.post,
            "/api/v2/tickets.json",
            {
                "ticket": {
                    "comment": {"body": comment},
                    "priority": priority,
                    "subject": subject,
                    "tags": [tags],
                }
            },
        ).json()

        return Ticket.model_validate(response["ticket"])

    def delete(self, ticket_id: str) -> bool:
        self._call_api(
            sema4ai_http.delete,
            f"/api/v2/tickets/{ticket_id}.json",
        )
        return True


class CommentsApi(BaseApi):
    QUERY_OPTIONS = {
        "sort_by": "created_at",
        "sort_order": "asc",
        "include": "users",
    }

    def get(self, ticket_id: str):
        response = self._call_api(
            sema4ai_http.get,
            f"/api/v2/tickets/{ticket_id}/comments",
            params=self.QUERY_OPTIONS,
        ).json()

        return CommentsResponse.from_response(response)

    def create(self, ticket_id: str, comment: AddComment) -> str:
        self._call_api(
            sema4ai_http.put,
            f"/api/v2/tickets/{ticket_id}.json",
            comment.to_ticket_comment(),
        )

        return "Successfully created the comment"


class UsersApi(BaseApi):
    def search(self, query: str) -> UsersResponse:
        response = self._call_api(
            sema4ai_http.get, "/api/v2/users/search.json", {"query": query}
        ).json()

        return UsersResponse.from_response(response)


class GroupsApi(BaseApi):
    def list(self) -> list[Group]:
        response = self._call_api(
            sema4ai_http.get, "/api/v2/groups.json"
        ).json()

        return [Group.model_validate(group) for group in response["groups"]]


class TagsApi(BaseApi):
    def list(self) -> list[Tag]:
        response = self._call_api(sema4ai_http.get, "/api/v2/tags.json").json()

        return [Tag.model_validate(tag) for tag in response["tags"]]
