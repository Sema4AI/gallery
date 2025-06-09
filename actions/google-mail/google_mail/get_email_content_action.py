from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from sema4ai.actions import ActionError, OAuth2Secret, Response, action

from google_mail._models import Emails
from google_mail._support import (
    _get_google_service,
    _get_message_by_id,
    _get_message_details,
    _list_messages_with_query,
)
from google_mail._variables import MAX_RESPONSE_SIZE

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")


@action(is_consequential=False)
def get_email_content(
    token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/gmail.readonly"]],
    ],
    email_id: str = "",
    query: str = "",
    fetch_attachments: bool = False,
    max_results: int = 10,
) -> Response[Emails]:
    """Get Google email content with specific email id or with
    a query filter.

    Args:
        email_id: the email id to get the content from
        query: the query filter to apply to the emails
        fetch_attachments: if True, the attachments will be saved to Files API
        max_results: the maximum number of emails to return (default 10)
        token: the OAuth2 token for the user

    Returns:
        The list of emails matching filter
    """
    if not email_id and not query:
        raise ActionError("Either email_id or query must be provided")
    service = _get_google_service(token)
    emails = Emails(items=[])
    if email_id:
        message = _get_message_by_id(service, "me", email_id)
        email = _get_message_details(service, message, return_content=True, fetch_attachments=fetch_attachments)
        print(f"Appending to result email of size {email.get_size_in_bytes()}")
        emails.items.append(email)
    else:
        messages = _list_messages_with_query(
            service, query=query, max_results=max_results
        )
        total_response_size = 0
        for message in messages:
            email = _get_message_details(service, message, return_content=True, fetch_attachments=fetch_attachments)
            print(f"Appending to result email of size {email.get_size_in_bytes()}")
            email_size = email.get_size_in_bytes()
            total_response_size += email_size
            if total_response_size > MAX_RESPONSE_SIZE:
                break
            emails.items.append(email)
        print(f"Total email response size: {total_response_size}")
    return Response(result=emails)
