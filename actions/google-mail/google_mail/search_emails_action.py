from dotenv import load_dotenv
from pathlib import Path
from typing import Literal

from sema4ai.actions import action, OAuth2Secret, Response

from google_mail._models import Emails
from google_mail._support import (
    _get_google_service,
    _get_message_details,
    _list_messages_with_query,
)
from google_mail._variables import DEFAULT_EMAIL_QUERY_COUNT

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")


@action(is_consequential=False)
def search_emails(
    query: str,
    token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/gmail.readonly"]],
    ],
    max_results: int = DEFAULT_EMAIL_QUERY_COUNT,
    fetch_attachments: bool = False,
) -> Response[Emails]:
    """Search Google emails with a query filter.

    Please inform user if there are more than `max_results` emails.

    Args:
        query: the query filter to apply to the emails
        max_results: the maximum number of emails to return (default 100)
        fetch_attachments: if True, the attachments will be saved to Files API
        token: the OAuth2 token for the user

    Returns:
        The list of emails matching filter
    """
    service = _get_google_service(token)
    emails = Emails(items=[])
    messages = _list_messages_with_query(service, query=query, max_results=max_results)
    for message in messages:
        email = _get_message_details(service, message, fetch_attachments=fetch_attachments)
        emails.items.append(email)
    return Response(result=emails)
