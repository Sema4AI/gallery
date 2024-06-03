from dotenv import load_dotenv
from pathlib import Path
from typing import Literal

from sema4ai.actions import action, OAuth2Secret, Response

from google_mail._support import (
    _create_message,
    _get_google_service,
    _send_message,
)

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")


@action(is_consequential=True)
def send_email(
    subject: str,
    body: str,
    to: str,
    token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/gmail.send"]],
    ],
    cc: str = "",
    bcc: str = "",
) -> Response[str]:
    """Send the email to the recipient(s) using the Gmail API.

    The recipients can be given with `to`, `cc` and `bcc` parameters as a comma separated list.

    Args:
        subject: the subject of the email
        body: the message of the email
        to: the email address(es) of the recipient(s), comma separated
        cc: the email address(es) of the recipient(s) to be cc'd, comma separated
        bcc: the email address(es) of the recipient(s) to be bcc'd, comma separated
        token: the OAuth2 token for the user

    Returns:
        Result of the email sending, "email sent" if successful
    """
    service = _get_google_service(token)
    result = _send_message(
        service,
        "me",
        _create_message(
            "me",
            subject=subject,
            body=body,
            to=to,
            cc=cc,
            bcc=bcc,
            attachments=None,
        ),
    )
    return Response(result="email sent" if result is None else result)
