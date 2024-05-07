"""
A simple AI Action template for comparing timezones

Please check out the base guidance on AI Actions in our main repository readme:
https://github.com/robocorp/robocorp/blob/master/README.md

"""

import os
from dotenv import load_dotenv
from models import MessageList, Response
from pathlib import Path
from sema4ai.actions import action, Secret
from slack_sdk import WebClient as SlackWebClient
from slack_sdk.errors import SlackApiError
from typing_extensions import Self
from utils import get_channel_id, ChannelNotFoundError

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")


DEV_SLACK_ACCESS_TOKEN = Secret.model_validate(os.getenv("SLACK_TOKEN", ""))


class CaptureError:
    def __init__(self):
        self._error = "Unknown error"

    def get_response(self) -> Response:
        return Response(error=self._error)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):

        if not exc_type:
            return

        if issubclass(exc_type, SlackApiError):
            err = exc_val.response["error"]
            if err == "no_in_channel":
                self._error = "Slack bot was not added to the channel"
            else:
                self._error = err
        elif issubclass(exc_type, ChannelNotFoundError):
            self._error = str(exc_val)
        else:
            # return None to raise other exceptions as usual
            return

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
        A structure containing a boolean if the message was successfully sent or an error if it occurred
    """

    with CaptureError() as error:
        access_token = _parse_token(access_token)
        response = SlackWebClient(token=access_token).chat_postMessage(channel=channel_name, text=message).validate()

        return Response(result=bool(response.data.get("ok", False)))

    return error.get_response()


@action(is_consequential=False)
def read_messages_from_channel(
    channel_name: str, limit: int = 20, access_token: Secret = DEV_SLACK_ACCESS_TOKEN
) -> Response[MessageList]:
    """Sends a message to the specified Slack channel.

    Args:
        channel_name: The name of the Slack channel to read the messages from.
        limit: The number of messages to read from the channel. Limited to a maximum of 200.
        access_token: The Slack application access token.

    Returns:
        A structure containing the messages and associated metadata from the specified Slack channel
        or an error if it occurred
    """
    with CaptureError() as error:
        access_token = _parse_token(access_token)
        # When reading from a channel, the API label doesn't contain the `#` in the beginning of the channel name
        channel_name = channel_name.lstrip("#")

        response = (
            SlackWebClient(token=access_token)
            .conversations_history(
                channel=get_channel_id(channel_name, access_token=access_token),
                limit=limit,
            )
            .validate()
        )

        return Response(
            result=MessageList.model_validate(
                response.data,
                from_attributes=True,
                context={"access_token": access_token},
            )
        )

    return error.get_response()
