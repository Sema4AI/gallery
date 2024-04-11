"""Set of actions operating on HubSpot resources.

Currently supporting:
- Searching: companies, contacts, deals, tasks
"""


import json
import os
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from hubspot import HubSpot
from hubspot.crm.companies import PublicObjectSearchRequest as CompanySearchRequest
from pydantic import BaseModel, Field
from robocorp.actions import Request, action


ACCESS_TOKEN_FIELD = "HUBSPOT_ACCESS_TOKEN"

load_dotenv(Path("devdata") / ".env")


class CompanyResult(BaseModel):
    """Company search result object holding the queried information."""

    names: Annotated[list[str], Field(description="Company names.")]


def _get_api_client(request: Request) -> HubSpot:
    # Sets the access token from the incoming request object if present, otherwise it
    #  defaults to an environment variable.
    access_token = os.getenv(ACCESS_TOKEN_FIELD)
    context_data = request.headers.get("X-Action-Context")
    if context_data:
        action_context = json.loads(context_data)
        access_token = action_context.get(ACCESS_TOKEN_FIELD, access_token)

    return HubSpot(access_token=access_token)


@action
def search_companies(request: Request, query: str, limit: int = 10) -> CompanyResult:
    """Search for companies based on the provided string query.

    Args:
        query: String that is searched for in all the properties for a match.
        limit: The maximum number of results the search can return.

    Returns:
        A list of company names matching the query.
    """
    api_client = _get_api_client(request)
    search_request = CompanySearchRequest(query=query, limit=limit)
    response = api_client.crm.companies.search_api.do_search(
        public_object_search_request=search_request
    )
    names = [result.to_dict()["properties"]["name"] for result in response.results]
    print(f"Companies matching query: {', '.join(names)}")
    return CompanyResult(names=names)
