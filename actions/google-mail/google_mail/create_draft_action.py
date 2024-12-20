from typing import Literal

from sema4ai.actions import ActionError, OAuth2Secret, Response, action

from google_mail._support import _create_draft, _create_message, _get_google_service


@action(is_consequential=True)
def create_draft(
    token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/gmail.modify"]],
    ],
    subject: str = "",
    body: str = "",
    to: str = "",
    cc: str = "",
    bcc: str = "",
) -> Response[str]:
    """Create a draft of an email.

    The recipients can be given with `to`, `cc` and `bcc` parameters as a comma separated list.

    Args:
        subject: the subject of the email
        body: the message of the email
        to: the email address(es) of the recipient(s), comma separated
        cc: the email address(es) of the recipient(s) to be cc'd, comma separated
        bcc: the email address(es) of the recipient(s) to be bcc'd, comma separated
        token: the OAuth2 token for the user

    Returns:
        The id of the drafted email
    """
    if all(not param for param in [subject, body, to, cc, bcc]):
        raise ActionError(
            "At least one of the parameters must be provided to create a draft."
        )

    service = _get_google_service(token)
    result = _create_draft(
        service,
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
    return Response(result=f"Draft created with id '{result}'")
