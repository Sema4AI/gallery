import os
from typing import Literal

from hubspot import HubSpot
from sema4ai.actions import OAuth2Secret, Response, action

DEV_OAUTH2_TOKEN = OAuth2Secret.model_validate(
    {"access_token": os.getenv("DEV_HUBSPOT_ACCESS_TOKEN", "not-set-but-required")}
)


@action(is_consequential=True)
def delete_company(
    company_id: str,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["crm.objects.companies.write"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[str]:
    """Delete an existing company.

    Args:
        company_id: The id of the company to delete.
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        Success or error message.
    """
    api_client = HubSpot(access_token=token.access_token)
    api_client.crm.companies.basic_api.archive(company_id=company_id)

    return Response(result="The company was successfully deleted.")


@action(is_consequential=True)
def delete_contact(
    contact_id: str,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["crm.objects.contacts.write"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[str]:
    """Delete an existing contact.

    Args:
        contact_id: The id of the contact to delete.
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        Success or error message.
    """
    api_client = HubSpot(access_token=token.access_token)
    api_client.crm.contacts.basic_api.archive(contact_id=contact_id)

    return Response(result="The contact was successfully deleted.")


@action(is_consequential=True)
def delete_deal(
    deal_id: str,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["crm.objects.deals.write"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[str]:
    """Delete an existing deal.

    Args:
        deal_id: The id of the deal to delete.
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        Success or error message.
    """
    api_client = HubSpot(access_token=token.access_token)
    api_client.crm.deals.basic_api.archive(deal_id=deal_id)

    return Response(result="The deal was successfully deleted.")


@action(is_consequential=True)
def delete_ticket(
    ticket_id: str,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["tickets"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[str]:
    """Delete an existing ticket.

    Args:
        ticket_id: The id of the ticket to delete.
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        Success or error message.
    """
    api_client = HubSpot(access_token=token.access_token)
    api_client.crm.tickets.basic_api.archive(ticket_id=ticket_id)

    return Response(result="The ticket was successfully deleted.")


@action(is_consequential=True)
def delete_task(
    task_id: str,
    token: OAuth2Secret[
        Literal["hubspot"], list[Literal["crm.objects.contacts.write"]]
    ] = DEV_OAUTH2_TOKEN,
) -> Response[str]:
    """Delete an existing ticket.

    Args:
        task_id: The id of the task to delete.
        token: An OAuth2 Public App (client) token structure used to make API calls.

    Returns:
        Success or error message.
    """
    api_client = HubSpot(access_token=token.access_token)
    api_client.crm.objects.tasks.basic_api.archive(task_id=task_id)

    return Response(result="The task was successfully deleted.")
