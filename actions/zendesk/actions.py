from typing import Literal

from sema4ai.actions import OAuth2Secret, Response, action

from client import CommentsApi, TicketApi
from models import CommentsResponse, TicketResponse


@action(is_consequential=False)
def search_ticket(
    zendesk_credentials: OAuth2Secret[Literal["zendesk"], list[Literal["read"]]],
    query: str,
) -> Response[TicketResponse]:
    """List tickets that match the query.

    You can narrow your search results according to resource dates, and object properties, such as ticket status or tag.

    Args:
        zendesk_credentials: Zendesk OAuth2 credentials
        query: The query string following Zendesk's query syntax rules.
            Details at: https://support.zendesk.com/hc/en-us/articles/4408886879258-Zendesk-Support-search-reference.

    Returns:
        A list of tickets matching the query.
    """
    client = TicketApi(
        zendesk_credentials.access_token, zendesk_credentials.metadata["server"]
    )

    return Response(result=client.search(query))


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
        ticket_id: The ticket ID to pull comments for

    Returns:
        The ticket comments.
    """
    client = CommentsApi(
        zendesk_credentials.access_token, zendesk_credentials.metadata["server"]
    )

    return Response(result=client.get_comments(ticket_id))
