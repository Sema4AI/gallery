"""Set of actions operating on HubSpot resources.

Currently supporting:
- Searching CRM: companies, contacts, deals, tickets, tasks
"""

import os
from enum import Enum
from typing import Literal

import requests
from hubspot import HubSpot
from hubspot.crm.companies import PublicObjectSearchRequest as CompanySearchRequest
from hubspot.crm.contacts import PublicObjectSearchRequest as ContactSearchRequest
from hubspot.crm.deals import PublicObjectSearchRequest as DealSearchRequest
from hubspot.crm.objects import PublicObjectSearchRequest as ObjectSearchRequest
from hubspot.crm.tickets import PublicObjectSearchRequest as TicketSearchRequest
from hubspot_client.models import (
    Company,
    Contact,
    Deal,
    EmailStatisticsResponse,
    MarketingEmailQueryParams,
    Owner,
    Pipeline,
    SearchParams,
    Task,
    Ticket,
)
from sema4ai.actions import OAuth2Secret, Response, action

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
    search_params: SearchParams,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["crm.objects.companies.read"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[list[Company]]:
    """Search for HubSpot companies based on the provided string query.

    This is a basic search returning a list of companies that are matching the
    `query` among any of their properties. The search will be limited to at most
    `limit` results, therefore you have to increase this parameter if you want to
    obtain more.

    If you want to filter the results, you can provide a list of filters to apply.
    Filters correspond exactly to the Hubspot filter search results documentation which can be
    found here: https://developers.hubspot.com/beta-docs/guides/api/crm/search#filter-search-results.

    Args:
        search_params: JSON containing the following search parameters:
            - query: String that is searched for in all the contact properties for a match.
            - filter_groups: A list of filters to apply to the search.
            - limit: The maximum number of results the search can return.
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        A structure with a list of companies matching the query.
    """
    api_client = HubSpot(access_token=token.access_token)
    search_request = CompanySearchRequest(**search_params.model_dump(exclude_none=True))
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
    search_params: SearchParams,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["crm.objects.contacts.read"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[list[Contact]]:
    """Search for HubSpot contacts based on the provided string query.

    This is a basic search returning a list of contacts that are matching the
    `query` among any of their properties. The search will be limited to at most
    `limit` results, therefore you have to increase this parameter if you want to
    obtain more.

    If you want to filter the results, you can provide a list of filters to apply.
    Filters correspond exactly to the Hubspot filter search results documentation which can be
    found here: https://developers.hubspot.com/beta-docs/guides/api/crm/search#filter-search-results.

    Args:
        search_params: JSON containing the following search parameters:
            - query: String that is searched for in all the contact properties for a match.
            - filter_groups: A list of filters to apply to the search.
            - limit: The maximum number of results the search can return.
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        A structure with a list of contacts matching the query.
    """
    api_client = HubSpot(access_token=token.access_token)
    search_request = ContactSearchRequest(**search_params.model_dump(exclude_none=True))
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
    search_params: SearchParams,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["crm.objects.deals.read"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[list[Deal]]:
    """Search for HubSpot deals based on the provided string query.

    This is a basic search returning a list of deals that are matching the
    `query` string among any of their properties. The search will be limited to at most
    `limit` results, therefore you have to increase this parameter if you want to
    obtain more.

    If you want to filter the results, you can provide a list of filters to apply.
    Filters correspond exactly to the Hubspot filter search results documentation which can be
    found here: https://developers.hubspot.com/beta-docs/guides/api/crm/search#filter-search-results.


    Args:
        search_params: JSON containing the following search parameters:
            - query: String that is searched for in all the contact properties for a match.
            - filter_groups: A list of filters to apply to the search.
            - limit: The maximum number of results the search can return.
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        A structure with a list of deals matching the query.
    """
    api_client = HubSpot(access_token=token.access_token)
    search_request = DealSearchRequest(**search_params.model_dump(exclude_none=True))
    response = api_client.crm.deals.search_api.do_search(
        public_object_search_request=search_request
    )
    deals = [Deal(id=result.id, **result.properties) for result in response.results]
    names = [deal.dealname for deal in deals]
    print(f"Deals matching query: {', '.join(names)}")
    return Response(result=deals)


@action(is_consequential=False)
def search_tickets(
    search_params: SearchParams,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["tickets"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[list[Ticket]]:
    """Search for HubSpot deals based on the provided string query.

    This is a basic search returning a list of deals that are matching the
    `query` among any of their properties. The search will be limited to at most
    `limit` results, therefore you have to increase this parameter if you want to
    obtain more.

    If you want to filter the results, you can provide a list of filters to apply.
    Filters correspond exactly to the Hubspot filter search results documentation which can be
    found here: https://developers.hubspot.com/beta-docs/guides/api/crm/search#filter-search-results.

    Tickets are best for managing customer interactions, track progress and reporting
    to them.

    Args:
        search_params: JSON containing the following search parameters:
            - query: String that is searched for in all the contact properties for a match.
            - filter_groups: A list of filters to apply to the search.
            - limit: The maximum number of results the search can return.
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        A structure with a list of deals matching the query.
    """
    api_client = HubSpot(access_token=token.access_token)
    search_request = TicketSearchRequest(**search_params.model_dump(exclude_none=True))
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
    search_params: SearchParams,
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
        search_params: JSON containing the following search parameters:
            - query: String that is searched for in all the contact properties for a match
            - filter_groups: A list of filters to apply to the search
            - limit: The maximum number of results the search can return
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        A structure with a list of objects matching the query.
    """
    api_client = HubSpot(access_token=token.access_token)
    object_type = ObjectEnum(object_type)  # normalizes string value to enumeration
    search_api = getattr(api_client.crm.objects, object_type.value).search_api
    ObjectResult = OBJECT_MODEL_MAP[object_type]
    search_request = ObjectSearchRequest(
        **search_params.model_dump(exclude_none=True),
        properties=ObjectResult.get_properties(),
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


@action(is_consequential=False)
def list_pipelines(
    object_type: str,
    token: OAuth2Secret[
        Literal["hubspot"],
        list[Literal["crm.objects.custom.read", "crm.objects.deals.read"]],
    ] = DEV_OAUTH2_TOKEN,
) -> Response[list[Pipeline]]:
    """Get all deal pipelines and its stages.

    This is necessary to pull the ID of the stage when you need to create a new Deal.

    Args:
         object_type: The kind of object you are searching, currently supporting: deals and tickets.
         token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        The deal pipelines and its stages.
    """
    api_client = HubSpot(access_token=token.access_token)
    response = api_client.crm.pipelines.pipelines_api.get_all(object_type=object_type)

    pipelines = [
        Pipeline.model_validate(pipeline.to_dict()) for pipeline in response.results
    ]

    return Response(result=pipelines)


@action(is_consequential=False)
def list_owners(
    token: OAuth2Secret[
        Literal["hubspot"],
        list[Literal["crm.objects.owners.read"]],
    ] = DEV_OAUTH2_TOKEN,
) -> Response[list[Owner]]:
    """Get all owners.

    Args:
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        A list of owners.
    """
    api_client = HubSpot(access_token=token.access_token)

    has_more = True
    next_page_token = None
    owners = []

    while has_more:
        response = api_client.crm.owners.owners_api.get_page(
            limit=200, after=next_page_token
        )

        if response.paging:
            next_page_token = response.paging.next.after
        else:
            has_more = False

        owners.extend(response.results)

    owners_dict = [Owner.model_validate(owner.to_dict()) for owner in owners]

    return Response(result=owners_dict)


@action(is_consequential=False)
def get_marketing_email_analytics(
    query: MarketingEmailQueryParams,
    token: OAuth2Secret[
        Literal["hubspot"],
        list[Literal["content"]],
    ] = DEV_OAUTH2_TOKEN,
) -> Response[EmailStatisticsResponse]:
    """Retrieve marketing email analytics within a specified time interval.

    Args:
        query: JSON containing the following search parameters:
            - startTimestamp: Start timestamp
            - endTimestamp: End timestamp
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        A list of marketing email analytics.
    """

    url = "https://api.hubapi.com/marketing/v3/emails/statistics/list"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {token.access_token}",
    }

    response = requests.request("GET", url, headers=headers, params=query.model_dump())

    response_json = response.json()
    if response.status_code != 200:
        return Response(error=response_json)

    return Response(result=EmailStatisticsResponse.model_validate(response_json))
