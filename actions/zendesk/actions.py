from typing import Literal

from sema4ai.actions import OAuth2Secret, Response, action

from client import CommentsApi, GroupsApi, TicketsApi, UsersApi
from models import (
    AddComment,
    CommentsResponse,
    Group,
    Ticket,
    TicketsResponse,
    UpdateTicket,
    UsersResponse,
)


@action(is_consequential=False)
def search_tickets(
    zendesk_credentials: OAuth2Secret[Literal["zendesk"], list[Literal["read"]]],
    query: str,
) -> Response[TicketsResponse]:
    """List tickets that meet the search criteria.

    You can narrow your search results according to resource dates, and object properties, such as ticket status or tag.

    Args:
        zendesk_credentials: Zendesk OAuth2 credentials
        query: The query string following Zendesk's query syntax rules.
            Details at: https://support.zendesk.com/hc/en-us/articles/4408886879258-Zendesk-Support-search-reference.

    Returns:
        A list of tickets matching the query.
    """
    client = TicketsApi(
        zendesk_credentials.access_token, zendesk_credentials.metadata["server"]
    )

    response = client.search(query)
    return Response(result=response)


@action(is_consequential=True)
def update_ticket(
    zendesk_credentials: OAuth2Secret[Literal["zendesk"], list[Literal["read"]]],
    ticket_id: str,
    updates: UpdateTicket,
) -> Response[Ticket]:
    """Update an existing ticket.

    Args:
        zendesk_credentials: Zendesk OAuth2 credentials
        ticket_id (str): Ticket id to update
        updates: json containing the new properties of the ticket

    Returns:

    """
    client = TicketsApi(
        zendesk_credentials.access_token, zendesk_credentials.metadata["server"]
    )

    response = client.update(ticket_id, updates)
    return Response(result=response)


@action(is_consequential=False)
def get_ticket_comments(
    zendesk_credentials: OAuth2Secret[Literal["zendesk"], list[Literal["read"]]],
    ticket_id: str,
) -> Response[CommentsResponse]:
    """Get the comments for a ticket.

    Ticket comments represent the conversation between requesters, collaborators, and agents.
    Comments can be public or private.

    Args:
        zendesk_credentials: Zendesk OAuth2 credentials
        ticket_id (str): The ticket ID to pull comments for

    Returns:
        The ticket comments.
    """
    client = CommentsApi(
        zendesk_credentials.access_token, zendesk_credentials.metadata["server"]
    )

    response = client.get(ticket_id)
    return Response(result=response)


@action(is_consequential=False)
def search_users(
    zendesk_credentials: OAuth2Secret[Literal["zendesk"], list[Literal["read"]]],
    query: str,
) -> Response[UsersResponse]:
    """List the users that meet the search criteria.

    Args:
        zendesk_credentials: Zendesk OAuth2 credentials
        query: The query parameter supports the Zendesk search syntax for more advanced user searches.
            It can specify a partial or full value of any user property, including name, email address, notes, or phone.

    Returns:
        The ticket comments.
    """
    client = UsersApi(
        zendesk_credentials.access_token, zendesk_credentials.metadata["server"]
    )

    response = client.search(query)
    return Response(result=response)


@action(is_consequential=True)
def add_comment(
    zendesk_credentials: OAuth2Secret[
        Literal["zendesk"], list[Literal["tickets:write"]]
    ],
    ticket_id: str,
    comment: AddComment,
) -> Response[str]:
    """Creates a comment on a Zendesk ticket, with the author being the logged-in user.

    Args:
        zendesk_credentials: Zendesk OAuth2 credentials
        ticket_id (str): The unique identifier of the ticket to add the comment to
        comment (str): JSON representation of the comment to be added.

    Returns:
        Success message if the comment was added or an error message.
    """
    client = CommentsApi(
        zendesk_credentials.access_token, zendesk_credentials.metadata["server"]
    )

    response = client.create(ticket_id, comment)
    return Response(result=response)


@action(is_consequential=False)
def list_groups(
    zendesk_credentials: OAuth2Secret[Literal["zendesk"], list[Literal["read"]]],
) -> Response[list[Group]]:
    """List all the available groups.

    Groups serve as the core element of ticket workflow; support agents are organized into groups and tickets can be
    assigned to a group only, or to an assigned agent within a group.

    Args:
        zendesk_credentials: Zendesk OAuth2 credentials

    Returns:
        List of groups.
    """
    client = GroupsApi(
        zendesk_credentials.access_token, zendesk_credentials.metadata["server"]
    )

    response = client.list()
    return Response(result=response)

@action(is_consequential=True)
def create_ticket(
    zendesk_credentials: OAuth2Secret[
    Literal["zendesk"], list[Literal["tickets:write"]]],
    comment: str,
    priority: str,
    subject: str
) -> Response[str]:
    """
    Create a ticket in Zendesk

    Args:
        zendesk_credentials: Zendesk OAuth2 credentials
        comment (str): Comment to be added to the ticket
        priority (str): Priority of the ticket
        subject (str): Subject of the ticket

    Returns:
        Success message if the ticket was created or an error message.
    """
    client = TicketsApi(
        zendesk_credentials.access_token, zendesk_credentials.metadata["server"]
    )

    response = client.create(comment, priority, subject)
    return Response(result=response)