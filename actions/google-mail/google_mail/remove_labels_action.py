from dotenv import load_dotenv
from pathlib import Path
from typing import Literal

from sema4ai.actions import action, OAuth2Secret, Response, ActionError

from google_mail._models import EmailIdList
from google_mail._support import (
    _get_google_service,
    _get_label_id,
    _remove_labels_from_emails,
    _list_messages_with_query,
)
from google_mail._variables import DEFAULT_EMAIL_QUERY_COUNT

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")


@action(is_consequential=True)
def remove_labels(
    token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/gmail.modify"]],
    ],
    query: str = "",
    email_ids: EmailIdList = "",
    labels: str = "",
    max_results: int = DEFAULT_EMAIL_QUERY_COUNT,
) -> Response[str]:
    """Removes label(s) from emails using Google Email labels with a specific email id or with a query filter.

    Args:
        query: the query filter to find emails to remove labels
        email_ids: the email id(s) to move
        labels: the label names to remove from the emails (comma separated)
        max_results: the maximum number of emails to remove labels
        token: the OAuth2 token for the user

    Returns:
        The result of the operation
    """
    if not email_ids and not query:
        raise ActionError("Either email_ids or query must be provided")
    service = _get_google_service(token)
    email_id_list = []
    labels = labels.split(",")
    label_id_list = []
    for label in labels:
        try:
            label_id = _get_label_id(service, label)
            label_id_list.append(label_id)
        except ActionError:
            pass
    if len(label_id_list) == 0:
        raise ActionError(f"No labels found matching '{labels}'")
    if email_ids:
        email_id_list = email_ids.id_list
    else:
        messages = _list_messages_with_query(
            service, query=query, max_results=max_results
        )
        if len(messages) == 0:
            raise ActionError(f"No messages found matching query '{query}'")
        email_id_list = [message["id"] for message in messages]

    _remove_labels_from_emails(service, email_id_list, label_id_list)
    return Response(result="Label(s) removed successfully.")
