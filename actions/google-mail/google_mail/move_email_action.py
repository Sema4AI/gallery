from dotenv import load_dotenv
from pathlib import Path
from typing import Literal

from sema4ai.actions import action, OAuth2Secret, Response, ActionError

from google_mail._models import EmailIdList
from google_mail._support import (
    _get_google_service,
    _get_label_id,
    _move_email_to_label,
    _move_email_to_trash,
    _list_messages_with_query,
)

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")


@action(is_consequential=True)
def move_email(
    token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/gmail.modify"]],
    ],
    query: str = "",
    email_ids: EmailIdList = "",
    label: str = "",
    max_results: int = 1,
) -> Response[str]:
    """Moves emails using Google Email labels with a specific email id
    or with a query filter.

    Maximum of 500 emails can be moved at a time (set that on "all")
    Email can be moved to a label or to the trash (label="TRASH").

    Args:
        email_ids: the email id(s) to move
        query: the query filter to find emails to move
        label: the label name to apply to the emails
        token: the OAuth2 token for the user
        max_results: the maximum number of emails to move

    Returns:
        The result of the operation
    """
    if not email_ids and not query:
        raise ActionError("Either email_ids or query must be provided")
    service = _get_google_service(token)
    email_id_list = []
    if label != "":
        if email_ids:
            email_id_list = email_ids.id_list
        else:
            messages = _list_messages_with_query(
                service, query=query, max_results=max_results
            )
            if len(messages) == 0:
                raise ActionError(f"No messages found matching query '{query}'")
            email_id_list = [message["id"] for message in messages]
        if label.upper() == "TRASH":
            _move_email_to_trash(service, email_id_list)
        else:
            new_label_id = _get_label_id(service, label)
            _move_email_to_label(service, email_id_list, new_label_id)
    else:
        raise ActionError("Label must be provided to move emails.")
    return Response(result="action done")
