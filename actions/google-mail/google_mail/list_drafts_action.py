from dotenv import load_dotenv
from pathlib import Path
from typing import Literal

from sema4ai.actions import action, OAuth2Secret, Response, ActionError

from google_mail._models import Drafts
from google_mail._support import _get_google_service, _list_drafts


load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")


@action(is_consequential=True)
def list_drafts(
    token: OAuth2Secret[
        Literal["google"],
        list[
            Literal[
                "https://www.googleapis.com/auth/gmail.modify",
                "https://www.googleapis.com/auth/gmail.readonly",
            ]
        ],
    ],
    query: str = "",
) -> Response[Drafts]:
    """Get list of drafts or filter drafts with a query.

    Args:
        query: query to filter drafts or list all drafts

    Returns:
        The list of draft emails
    """
    service = _get_google_service(token)
    drafts = _list_drafts(service, query=query)
    if drafts:
        return Response(result=drafts)
    else:
        raise ActionError("No drafts found")
