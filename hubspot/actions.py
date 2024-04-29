"""Set of actions operating on HubSpot resources.

Currently supporting:
- Searching CRM: companies, contacts, deals, tickets, tasks
"""


import os
from pathlib import Path

from dotenv import load_dotenv
from hubspot import HubSpot
from hubspot.crm.companies import PublicObjectSearchRequest as CompanySearchRequest
from hubspot.crm.contacts import PublicObjectSearchRequest as ContactSearchRequest
from hubspot.crm.deals import PublicObjectSearchRequest as DealSearchRequest
from hubspot.crm.tickets import PublicObjectSearchRequest as TicketSearchRequest
from sema4ai.actions import Secret, action

from models import (
    CompaniesResult,
    CompanyResult,
    ContactResult,
    ContactsResult,
    DealResult,
    DealsResult,
    TicketResult,
    TicketsResult,
)


load_dotenv(Path("devdata") / ".env")

DEV_ACCESS_TOKEN = Secret.model_validate(os.getenv("HUBSPOT_ACCESS_TOKEN", ""))


@action(is_consequential=False)
def hubspot_search_companies(
    query: str,
    limit: int = 10,
    access_token: Secret = DEV_ACCESS_TOKEN,
) -> CompaniesResult:
    """Search for HubSpot companies based on the provided string query.

    This is a basic search returning a list of companies that are matching the
    `query` among any of their properties. The search will be limited to at most
    `limit` results, therefore you have to increase this parameter if you want to
    obtain more.

    Args:
        query: String that is searched for in all the company properties for a match.
        limit: The maximum number of results the search can return.
        access_token: Your Private App generated access token used to make API calls.

    Returns:
        A structure with a list of companies matching the query.
    """
    api_client = HubSpot(access_token=access_token.value)
    search_request = CompanySearchRequest(query=query, limit=limit)
    response = api_client.crm.companies.search_api.do_search(
        public_object_search_request=search_request
    )
    companies = [
        CompanyResult(id=result.id, **result.properties) for result in response.results
    ]
    names = [company.name for company in companies]
    print(f"Companies matching query: {', '.join(names)}")
    return CompaniesResult(companies=companies)


@action(is_consequential=False)
def hubspot_search_contacts(
    query: str,
    limit: int = 10,
    access_token: Secret = DEV_ACCESS_TOKEN,
) -> ContactsResult:
    """Search for HubSpot contacts based on the provided string query.

    This is a basic search returning a list of contacts that are matching the
    `query` among any of their properties. The search will be limited to at most
    `limit` results, therefore you have to increase this parameter if you want to
    obtain more.

    Args:
        query: String that is searched for in all the contact properties for a match.
        limit: The maximum number of results the search can return.
        access_token: Your Private App generated access token used to make API calls.

    Returns:
        A structure with a list of contacts matching the query.
    """
    api_client = HubSpot(access_token=access_token.value)
    search_request = ContactSearchRequest(query=query, limit=limit)
    response = api_client.crm.contacts.search_api.do_search(
        public_object_search_request=search_request
    )
    contacts = [
        ContactResult(id=result.id, **result.properties) for result in response.results
    ]
    emails = [contact.email for contact in contacts]
    print(f"Contacts matching query: {', '.join(emails)}")
    return ContactsResult(contacts=contacts)


@action(is_consequential=False)
def hubspot_search_deals(
    query: str,
    limit: int = 10,
    access_token: Secret = DEV_ACCESS_TOKEN,
) -> DealsResult:
    """Search for HubSpot deals based on the provided string query.

    This is a basic search returning a list of deals that are matching the
    `query` among any of their properties. The search will be limited to at most
    `limit` results, therefore you have to increase this parameter if you want to
    obtain more.

    Args:
        query: String that is searched for in all the deals properties for a match.
        limit: The maximum number of results the search can return.
        access_token: Your Private App generated access token used to make API calls.

    Returns:
        A structure with a list of deals matching the query.
    """
    api_client = HubSpot(access_token=access_token.value)
    search_request = DealSearchRequest(query=query, limit=limit)
    response = api_client.crm.deals.search_api.do_search(
        public_object_search_request=search_request
    )
    deals = [
        DealResult(id=result.id, **result.properties) for result in response.results
    ]
    names = [deal.dealname for deal in deals]
    print(f"Deals matching query: {', '.join(names)}")
    return DealsResult(deals=deals)


@action(is_consequential=False)
def hubspot_search_tickets(
    query: str,
    limit: int = 10,
    access_token: Secret = DEV_ACCESS_TOKEN,
) -> TicketsResult:
    """Search for HubSpot deals based on the provided string query.

    This is a basic search returning a list of deals that are matching the
    `query` among any of their properties. The search will be limited to at most
    `limit` results, therefore you have to increase this parameter if you want to
    obtain more.

    Args:
        query: String that is searched for in all the deals properties for a match.
        limit: The maximum number of results the search can return.
        access_token: Your Private App generated access token used to make API calls.

    Returns:
        A structure with a list of deals matching the query.
    """
    api_client = HubSpot(access_token=access_token.value)
    search_request = TicketSearchRequest(query=query, limit=limit)
    response = api_client.crm.tickets.search_api.do_search(
        public_object_search_request=search_request
    )
    tickets = [
        TicketResult(id=result.id, **result.properties) for result in response.results
    ]
    subjects = [ticket.subject for ticket in tickets]
    print(f"Tickets matching query: {', '.join(subjects)}")
    return TicketsResult(tickets=tickets)
