from dotenv import load_dotenv
from pathlib import Path
from typing import Literal

from sema4ai.actions import action, OAuth2Secret, Response, ActionError

from google_mail._support import (
    _get_google_service,
    _update_draft,
    _create_message,
    _get_draft_by_id,
    _extract_body,
    _list_messages_with_query,
    _get_message_headers,
)
from google_mail.get_email_content_action import get_email_content

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")


@action(is_consequential=True)
def update_draft(
    draft_id: str,
    token: OAuth2Secret[
        Literal["google"],
        list[
            Literal[
                "https://www.googleapis.com/auth/gmail.modify",
                "https://www.googleapis.com/auth/gmail.readonly",
            ]
        ],
    ],
    subject: str = "",
    body: str = "",
    to: str = "",
    cc: str = "",
    bcc: str = "",
) -> Response[str]:
    """Update existing draft email by its id.

    If draft_id is unknown then use action "get_email_content" to get the draft_id.

    The recipients can be given with `to` parameter as a comma separated list.

    Args:
        draft_id: identify the draft by its id
        query: identify the draft by querying
        subject: the subject of the email
        body: the message of the email
        to: the email address(es) of the recipient(s), comma separated
        token: the OAuth2 token for the user
        cc: the email address(es) of the recipient(s) to be cc'd, comma separated
        bcc: the email address(es) of the recipient(s) to be bcc'd, comma separated

    Returns:
        The id of the drafted email
    """
    if all(not param for param in [subject, body, to, cc, bcc]):
        raise ActionError(
            "At least one of the parameters must be provided to update a draft."
        )
    service = _get_google_service(token)
    # get previous draft AND update only parts of it

    draft = _get_draft_by_id(service, draft_id)
    print(draft)
    original_body = _extract_body(draft["message"])
    headers = _get_message_headers(draft)
    subject = subject or headers.get("Subject", "")
    body = body or original_body
    to = to or headers.get("To", "")
    cc = cc or headers.get("Cc", "")
    bcc = bcc or headers.get("Bcc", "")
    print(draft)
    # result = _update_draft(
    #     service,
    #     draft_id,
    #     _create_message(
    #         "me",
    #         subject=subject,
    #         body=body,
    #         to=to,
    #         cc=cc,
    #         bcc=bcc,
    #         attachments=None,
    #     ),
    # )
    return Response(result=f"Draft with id '{subject}' updated")
