import re
import urllib.parse
from dataclasses import dataclass
from time import sleep
from typing import Any, Optional

import requests
from sema4ai.actions import ActionError

from models import CommentsResponse, Ticket, TicketResponse, User


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

        response = http_method(url, headers=headers, params=params)

        if response.status_code == 429:
            sleep(int(response.headers.get("Retry-After", 1)))

            return self._call_api(http_method, endpoint, params)

        if response.status_code != 200:
            raise ActionError(response.text)

        return response


class TicketApi(BaseApi):
    QUERY_OPTIONS = {
        "sort_by": "created_at",
        "sort_order": "asc",
        "include": "tickets(users)",
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

    def search(self, query: str) -> TicketResponse:
        query = self._add_ticket_type(query)
        params = {"query": query, **self.QUERY_OPTIONS}

        response = self._call_api(requests.get, "/api/v2/search.json", params).json()

        return TicketResponse.from_response(response)


class CommentsApi(BaseApi):
    QUERY_OPTIONS = {
        "sort_by": "created_at",
        "sort_order": "asc",
        "include": "users",
    }

    def get_comments(self, ticket_id: str):
        response = self._call_api(
            requests.get,
            f"/api/v2/tickets/{ticket_id}/comments",
            params=self.QUERY_OPTIONS,
        ).json()

        return CommentsResponse.from_response(response)
