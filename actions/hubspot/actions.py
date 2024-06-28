"""Set of actions operating on HubSpot resources.

Currently supporting:
- Searching CRM: companies, contacts, deals, tickets, tasks
"""


import os
from enum import Enum
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from hubspot import HubSpot
from hubspot.crm.companies import PublicObjectSearchRequest as CompanySearchRequest
from hubspot.crm.contacts import PublicObjectSearchRequest as ContactSearchRequest
from hubspot.crm.deals import PublicObjectSearchRequest as DealSearchRequest
from hubspot.crm.objects import PublicObjectSearchRequest as ObjectSearchRequest
from hubspot.crm.tickets import PublicObjectSearchRequest as TicketSearchRequest
from sema4ai.actions import OAuth2Secret, Response, action

from models import (
    Company,
    Contact,
    Deal,
    Task,
    Ticket,
)


load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")

DEV_OAUTH2_TOKEN = OAuth2Secret.model_validate(
    {"access_token": os.getenv("DEV_HUBSPOT_ACCESS_TOKEN", "not-set-but-required")}
)


class ObjectEnum(Enum):
    """Types of objects we accept under the `search_objects` function."""

    TASKS = "tasks"


OBJECT_MODEL_MAP = {
    ObjectEnum.TASKS: Task,
}


@action(is_consequential=False)
def search_companies(
    query: str,
    limit: int = 10,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["crm.objects.companies.read"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[list[Company]]:
    """Search for HubSpot companies based on the provided string query.

    This is a basic search returning a list of companies that are matching the
    `query` among any of their properties. The search will be limited to at most
    `limit` results, therefore you have to increase this parameter if you want to
    obtain more.

    Args:
        query: String that is searched for in all the company properties for a match.
        limit: The maximum number of results the search can return.
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        A structure with a list of companies matching the query.
    """
    api_client = HubSpot(access_token=token.access_token)
    search_request = CompanySearchRequest(query=query, limit=limit)
    response = api_client.crm.companies.search_api.do_search(
        public_object_search_request=search_request
    )
    companies = [
        Company(id=result.id, **result.properties) for result in response.results
    ]
    names = [company.name for company in companies]
    print(f"Companies matching query: {', '.join(names)}")
    return Response(result=companies)


@action(is_consequential=False)
def search_contacts(
    query: str,
    limit: int = 10,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["crm.objects.contacts.read"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[list[Contact]]:
    """Search for HubSpot contacts based on the provided string query.

    This is a basic search returning a list of contacts that are matching the
    `query` among any of their properties. The search will be limited to at most
    `limit` results, therefore you have to increase this parameter if you want to
    obtain more.

    Args:
        query: String that is searched for in all the contact properties for a match.
        limit: The maximum number of results the search can return.
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        A structure with a list of contacts matching the query.
    """
    api_client = HubSpot(access_token=token.access_token)
    search_request = ContactSearchRequest(query=query, limit=limit)
    response = api_client.crm.contacts.search_api.do_search(
        public_object_search_request=search_request
    )
    contacts = [
        Contact(id=result.id, **result.properties) for result in response.results
    ]
    emails = [contact.email for contact in contacts]
    print(f"Contacts matching query: {', '.join(emails)}")
    return Response(result=contacts)


@action(is_consequential=False)
def search_deals(
    query: str,
    limit: int = 10,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["crm.objects.deals.read"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[list[Deal]]:
    """Search for HubSpot deals based on the provided string query.

    This is a basic search returning a list of deals that are matching the
    `query` among any of their properties. The search will be limited to at most
    `limit` results, therefore you have to increase this parameter if you want to
    obtain more.

    Args:
        query: String that is searched for in all the deals properties for a match.
        limit: The maximum number of results the search can return.
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        A structure with a list of deals matching the query.
    """
    api_client = HubSpot(access_token=token.access_token)
    search_request = DealSearchRequest(query=query, limit=limit)
    response = api_client.crm.deals.search_api.do_search(
        public_object_search_request=search_request
    )
    deals = [Deal(id=result.id, **result.properties) for result in response.results]
    names = [deal.dealname for deal in deals]
    print(f"Deals matching query: {', '.join(names)}")
    return Response(result=deals)


@action(is_consequential=False)
def search_tickets(
    query: str,
    limit: int = 10,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["tickets"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[list[Ticket]]:
    """Search for HubSpot deals based on the provided string query.

    This is a basic search returning a list of deals that are matching the
    `query` among any of their properties. The search will be limited to at most
    `limit` results, therefore you have to increase this parameter if you want to
    obtain more.
    Tickets are best for managing customer interactions, track progress and reporting
    to them.

    Args:
        query: String that is searched for in all the deals properties for a match.
        limit: The maximum number of results the search can return.
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        A structure with a list of deals matching the query.
    """
    api_client = HubSpot(access_token=token.access_token)
    search_request = TicketSearchRequest(query=query, limit=limit)
    response = api_client.crm.tickets.search_api.do_search(
        public_object_search_request=search_request
    )
    tickets = [Ticket(id=result.id, **result.properties) for result in response.results]
    subjects = [ticket.subject for ticket in tickets]
    print(f"Tickets matching query: {', '.join(subjects)}")
    return Response(result=tickets)


@action(is_consequential=False)
def search_objects(
    object_type: str,
    query: str,
    limit: int = 10,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["crm.objects.custom.read"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[list[Task]]:
    """Search for HubSpot objects based on the provided string query.

    This is a basic search returning a list of objects that are matching the
    `query` among any of their properties. The search will be limited to at most
    `limit` results, therefore you have to increase this parameter if you want to
    obtain more.
    Tasks are better for managing internal workflows, the stepping stones to get
    tickets done.

    Args:
        object_type: The kind of object you are searching, currently supporting: tasks.
        query: String that is searched for in all the object properties for a match.
        limit: The maximum number of results the search can return.
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        A structure with a list of objects matching the query.
    """
    api_client = HubSpot(access_token=token.access_token)
    object_type = ObjectEnum(object_type)  # normalizes string value to enumeration
    search_api = getattr(api_client.crm.objects, object_type.value).search_api
    ObjectResult = OBJECT_MODEL_MAP[object_type]
    search_request = ObjectSearchRequest(
        query=query, limit=limit, properties=ObjectResult.get_properties()
    )
    response = search_api.do_search(public_object_search_request=search_request)
    objects = [
        ObjectResult(id=result.id, **result.properties) for result in response.results
    ]
    EOL = "\n"
    print(
        f"{object_type.value.capitalize()} matching query:"
        f" {EOL.join(map(str, objects))}"
    )
    return Response(result=objects)
