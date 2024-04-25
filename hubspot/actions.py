"""Set of actions operating on HubSpot resources.

Currently supporting:
- Searching: companies, contacts, deals, tasks
"""


import os
from pathlib import Path

from dotenv import load_dotenv
from hubspot import HubSpot
from hubspot.crm.companies import PublicObjectSearchRequest as CompanySearchRequest
from hubspot.crm.contacts import PublicObjectSearchRequest as ContactSearchRequest
from sema4ai.actions import Secret, action

from models import CompaniesResult, CompanyResult, ContactResult, ContactsResult


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
