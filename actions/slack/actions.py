"""
Prebuild AI Action package that integrates with Slack SDK.

Please check out the base guidance on AI Actions in our main repository readme:
https://github.com/sema4ai/actions/blob/master/README.md
"""

import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sema4ai.actions import Secret, action
from slack_sdk import WebClient as SlackWebClient
from slack_sdk.errors import SlackApiError
from typing_extensions import Self

from conversations import ConversationNotFoundError, get_conversation_id
from models import MessageList
from sema4ai.actions import Response

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")


DEV_SLACK_ACCESS_TOKEN = Secret.model_validate(os.getenv("DEV_SLACK_ACCESS_TOKEN", ""))


class CaptureError:
    def __init__(self):
        self._error = "Unknown error"

    def get_response(self) -> Response:
        return Response(error=self._error)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool | None:
        if not exc_type:
            return None

        match exc_val:
            case ConversationNotFoundError() as e:
                self._error = str(e)
            case SlackApiError() as e:
                err = e.response["error"]
                if err == "not_in_channel":
                    self._error = "Slack bot was not added to the channel"
                else:
                    self._error = err
            case _:
                # return None to raise the exception
                return None

        # return True to supress the exception
        return True


def _parse_token(token: Secret) -> str:
    return token.value or DEV_SLACK_ACCESS_TOKEN.value


@action(is_consequential=True)
def send_message_to_channel(
    channel_name: str, message: str, access_token: Secret = DEV_SLACK_ACCESS_TOKEN
) -> Response[bool]:
    """Sends a message to the specified Slack channel.

    Args:
        channel_name: Slack channel to send the message to.
        message: Message to send on the Slack channel.
        access_token: The Slack application access token.

    Returns:
        A structure containing a boolean if the message was successfully sent or an error if it occurred.
    """

    with CaptureError() as error:
        access_token = _parse_token(access_token)

        response = (
            SlackWebClient(token=access_token)
            .chat_postMessage(
                channel=get_conversation_id(channel_name, access_token=access_token),
                text=message,
            )
            .validate()
        )

        return Response(result=bool(response.data.get("ok", False)))

    return error.get_response()


@action(is_consequential=False)
def read_messages_from_channel(
    channel_name: str,
    message_limit: int = 20,
    newer_than: str = "",
    saved_only: bool = False,
    access_token: Secret = DEV_SLACK_ACCESS_TOKEN,
) -> Response[MessageList]:
    """Sends a message to the specified Slack channel.

    Args:
        channel_name: The name of the Slack channel to read the messages from.
        message_limit: The number of messages to read from the channel. Defaults to 20 messages and has a maximum limit of 200 messages.
        access_token: The Slack application access token.
        newer_than: Get messages newer than the specified date in YYYY-MM-DD format.
        saved_only: Only the messages you saved would be returned when this is on.

    Returns:
        A structure containing the messages and associated metadata from the specified Slack channel
        or an error if it occurred.
    """

    if newer_than:
        newer_than_date = datetime.strptime(newer_than, "%Y-%m-%d")
        newer_than_timestamp = newer_than_date.timestamp()
    else:
        newer_than_timestamp = None

    with CaptureError() as error:
        access_token = _parse_token(access_token)

        response = (
            SlackWebClient(token=access_token)
            .conversations_history(
                channel=get_conversation_id(channel_name, access_token=access_token),
                limit=message_limit,
                oldest=newer_than_timestamp,
            )
            .validate()
        )

        messages_result = MessageList.model_validate(
            response.data,
            from_attributes=True,
            context={"access_token": access_token},
        )
        if saved_only:
            messages = messages_result.messages
            for idx in range(len(messages) - 1, -1, -1):
                saved = getattr(messages[idx], "saved", {})
                if not saved.get("state") == "in_progress":
                    messages.pop(idx)

        return Response(result=messages_result)

    return error.get_response()
