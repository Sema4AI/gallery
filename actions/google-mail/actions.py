import base64
from dotenv import load_dotenv
from pathlib import Path
from typing import Literal


from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sema4ai.actions import action, OAuth2Secret

from email.mime.text import MIMEText


load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")


def create_message(sender, to, subject, message_text):
    message = MIMEText(message_text)
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}


def send_message(service, user_id, message):
    try:
        message = (
            service.users().messages().send(userId=user_id, body=message).execute()
        )
        return None
    except Exception as error:
        error_msg = f"An error occurred: {error}"
        print(error_msg)
        return error_msg


@action
def send_email(
    subject: str,
    message: str,
    to: str,
    token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/gmail.send"]],
    ],
) -> str:
    """Send the email to the provided email address.

    The recipients can be given with `to` parameter as a comma separated list.

    Args:
        subject: the subject of the email
        message: the message of the email
        to: the email address(es) of the recipient(s), comma separated
        token: the OAuth2 token for the user

    Returns:
        Result of the email send action.
    """
    creds = Credentials(token=token.access_token)
    service = build("gmail", "v1", credentials=creds)
    result = send_message(service, "me", create_message("me", to, subject, message))

    return "email sent" if result is None else result
