from dotenv import load_dotenv
from pathlib import Path
from typing import Literal

from sema4ai.actions import action, OAuth2Secret, Response

from google_mail._support import _get_google_service, _send_draft

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")


@action(is_consequential=True)
def send_draft(
    draft_id: str,
    token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/gmail.send"]],
    ],
) -> Response[str]:
    """Send draft email by its draft id.

    Args:
        draft_id: the id of the draft to send
        token: the OAuth2 token for the user

    Returns:
        The result of the email sending
    """
    service = _get_google_service(token)
    _send_draft(service, draft_id)
    return Response(result="Draft email sent")
