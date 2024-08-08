import os
from typing import Literal

from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInput
from hubspot_client.models import (
    Company,
    Contact,
    Deal,
    Task,
    TaskInfo,
    Ticket,
    UpdateCompany,
    UpdateContact,
    UpdateDeal,
    UpdateTicket,
)
from sema4ai.actions import OAuth2Secret, Response, action

DEV_OAUTH2_TOKEN = OAuth2Secret.model_validate(
    {"access_token": os.getenv("DEV_HUBSPOT_ACCESS_TOKEN", "not-set-but-required")}
)


@action(is_consequential=True)
def update_company(
    company_id: str,
    company_data: UpdateCompany,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["crm.objects.companies.write"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[UpdateCompany]:
    """Update an existing company.

    Args:
        company_id: The id of the company to update.
        company_data: JSON including the properties to be updated.
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        The updated fields.
    """
    api_client = HubSpot(access_token=token.access_token)

    response = api_client.crm.companies.basic_api.update(
        company_id=company_id,
        simple_public_object_input=SimplePublicObjectInput(
            properties=company_data.model_dump(mode="json", exclude_none=True),
        ),
    )

    return Response(result=UpdateCompany(**response.properties))


@action(is_consequential=True)
def update_contact(
    contact_id: str,
    contact_data: UpdateContact,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["crm.objects.contacts.write"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[UpdateContact]:
    """Update an existing contact.

    Args:
        contact_id: The id of the contact to update.
        contact_data: JSON including the properties to be updated.
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        The updated fields.
    """
    api_client = HubSpot(access_token=token.access_token)

    response = api_client.crm.contacts.basic_api.update(
        contact_id=contact_id,
        simple_public_object_input=SimplePublicObjectInput(
            properties=contact_data.model_dump(mode="json", exclude_none=True)
        ),
    )

    return Response(result=UpdateContact(**response.properties))


@action(is_consequential=True)
def update_deal(
    deal_id: str,
    deal_data: UpdateDeal,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["crm.objects.deals.write"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[UpdateDeal]:
    """Update an existing deal.

    Args:
        deal_id: The id of the deal to update.
        deal_data: JSON including the properties to be updated.
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        The updated fields.
    """
    api_client = HubSpot(access_token=token.access_token)

    response = api_client.crm.deals.basic_api.update(
        deal_id=deal_id,
        simple_public_object_input=SimplePublicObjectInput(
            properties=deal_data.model_dump(mode="json", exclude_none=True)
        ),
    )

    return Response(result=UpdateDeal(**response.properties))


@action(is_consequential=True)
def update_ticket(
    ticket_id: str,
    ticket_data: UpdateTicket,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["tickets"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[UpdateTicket]:
    """Update an existing ticket.

    Args:
        ticket_id: The id of the ticket to update.
        ticket_data: JSON including the properties to be updated.
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        The updated fields.
    """
    api_client = HubSpot(access_token=token.access_token)

    response = api_client.crm.tickets.basic_api.update(
        ticket_id=ticket_id,
        simple_public_object_input=SimplePublicObjectInput(
            properties=ticket_data.model_dump(mode="json", exclude_none=True)
        ),
    )

    return Response(result=UpdateTicket(**response.properties))


@action(is_consequential=True)
def update_task(
    task_id: str,
    task_data: TaskInfo,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["crm.objects.contacts.write"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[TaskInfo]:
    """Update an existing ticket.

    Args:
        task_id: The id of the task to update.
        task_data: JSON including the properties to be updated.
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        The updated fields.
    """
    api_client = HubSpot(access_token=token.access_token)

    response = api_client.crm.objects.tasks.basic_api.update(
        task_id=task_id,
        simple_public_object_input=SimplePublicObjectInput(
            properties=task_data.model_dump(mode="json", exclude_none=True)
        ),
    )

    return Response(result=TaskInfo(**response.properties))
