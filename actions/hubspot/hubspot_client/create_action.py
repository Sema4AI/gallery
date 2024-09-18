import os
from typing import Literal

from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInputForCreate
from hubspot_client.models import (
    Company,
    CompanyInfo,
    Contact,
    ContactInfo,
    CreateDeal,
    CreateTask,
    CreateTicket,
    Deal,
    Task,
    Ticket,
)
from sema4ai.actions import OAuth2Secret, Response, action

DEV_OAUTH2_TOKEN = OAuth2Secret.model_validate(
    {"access_token": os.getenv("DEV_HUBSPOT_ACCESS_TOKEN", "not-set-but-required")}
)


@action(is_consequential=True)
def create_company(
    company_data: CompanyInfo,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["crm.objects.companies.write"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[Company]:
    """Create a new company.

    Args:
        company_data: JSON representation of the company to be created.
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        The newly created company.
    """
    api_client = HubSpot(access_token=token.access_token)

    response = api_client.crm.companies.basic_api.create(
        simple_public_object_input_for_create=SimplePublicObjectInputForCreate(
            properties=company_data.model_dump(mode="json")
        )
    )

    return Response(result=Company(id=response.id, **response.properties))


@action(is_consequential=True)
def create_contact(
    contact_data: ContactInfo,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["crm.objects.contacts.write"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[Contact]:
    """Create a new contact.

    Args:
        token: An OAuth2 Public App (client) token structure used to make API calls.
        contact_data: JSON representation of the contact to be created.

    Returns:
        The newly created contact.
    """
    api_client = HubSpot(access_token=token.access_token)

    response = api_client.crm.contacts.basic_api.create(
        simple_public_object_input_for_create=SimplePublicObjectInputForCreate(
            properties=contact_data.model_dump(mode="json")
        )
    )

    return Response(result=Contact(id=response.id, **response.properties))


@action(is_consequential=True)
def create_deal(
    deal_data: CreateDeal,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["crm.objects.deals.write"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[Deal]:
    """Create a new deal.

    The CreateDeal object requires a `dealstage` attribute which should be the ID of the deal stage and this can be
    found by listing all the deal pipelines beforehand.

    Args:
        deal_data: JSON representation of the deal to be created.
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        The newly created contact.
    """
    api_client = HubSpot(access_token=token.access_token)

    response = api_client.crm.deals.basic_api.create(
        simple_public_object_input_for_create=SimplePublicObjectInputForCreate(
            properties=deal_data.model_dump(mode="json")
        )
    )

    return Response(result=Deal(id=response.id, **response.properties))


@action(is_consequential=True)
def create_ticket(
    ticket_data: CreateTicket,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["tickets"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[Ticket]:
    """Create a new ticket.

    The CreateTicket object requires a `hs_pipeline_stage` attribute which should be the ID of the ticket stage and this
    can be found by listing all the ticket pipelines beforehand.

    Args:
        ticket_data: JSON representation of the ticket to be created.
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        The newly created ticket.
    """
    api_client = HubSpot(access_token=token.access_token)

    response = api_client.crm.tickets.basic_api.create(
        simple_public_object_input_for_create=SimplePublicObjectInputForCreate(
            properties=ticket_data.model_dump(mode="json")
        )
    )

    return Response(result=Ticket(id=response.id, **response.properties))


@action(is_consequential=True)
def create_tasks(
    task_data: CreateTask,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["crm.objects.contacts.write"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[Task]:
    """Create a new ticket.

    The CreateTicket object requires a `hs_pipeline_stage` attribute which should be the ID of the ticket stage and this
    can be found by listing all the ticket pipelines beforehand.

    Args:
        task_data: JSON representation of the ticket to be created.
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        The newly created ticket.
    """
    api_client = HubSpot(access_token=token.access_token)

    response = api_client.crm.objects.tasks.basic_api.create(
        simple_public_object_input_for_create=SimplePublicObjectInputForCreate(
            properties=task_data.model_dump(mode="json")
        )
    )

    return Response(result=Task(id=response.id, **response.properties))
