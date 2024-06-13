"""Prebuilt AI Actions package that integrates with Slack SDK.

Please check out the base guidance on AI Actions in our main repository readme:
https://github.com/sema4ai/actions/blob/master/README.md
"""

import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sema4ai.actions import Response, Secret, action
from slack_sdk import WebClient as SlackWebClient
from slack_sdk.errors import SlackApiError
from typing_extensions import Self

from conversations import ConversationNotFoundError, get_conversation_id
from models import Messages, ThreadMessage, ThreadMessages

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

        # return True to suppress the exception
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
        A structure containing a boolean if the message was successfully sent or an
        error if it occurred.
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


def _get_message_replies(
    message: ThreadMessage, *, client: SlackWebClient
) -> list[dict]:
    response = client.conversations_replies(
        channel=message.channel_id, ts=message.thread_ts
    ).validate()
    return list(
        filter(
            lambda msg: msg["client_msg_id"] != message.client_msg_id,
            response.get("messages"),
        )
    )


@action(is_consequential=False)
def read_messages_from_channel(
    channel_name: str,
    messages_limit: int = 20,
    newer_than: str = "",
    saved_only: bool = False,
    with_replies: bool = False,
    access_token: Secret = DEV_SLACK_ACCESS_TOKEN,
) -> Response[ThreadMessages]:
    """Read a message from a given Slack channel.

    Newer messages than the `newer_than` will be retrieved when this is set, then these
    are filtered based on their saved status when `saved_only` is enabled. Enabling
    `with_replies` will additionally provide the reply messages if the original message
    is part of a thread. Increase the `messages_limit` to a higher number if you want
    more results.

    Args:
        channel_name: The name of the Slack channel to read the messages from.
        messages_limit: The number of messages to read from the channel. Defaults to 20
            messages and has a maximum limit of 200 messages.
        access_token: The Slack application access token.
        newer_than: Get messages newer than the specified date in YYYY-MM-DD format.
        saved_only: Set this to `True` to return only the saved messages.
        with_replies: Set this to `True` to retrieve message thread replies as well.

    Returns:
        A structure containing the messages and associated metadata from the specified
        Slack channel or an error if it occurred.
    """

    if newer_than:
        newer_than_date = datetime.strptime(newer_than, "%Y-%m-%d")
        newer_than_timestamp = newer_than_date.timestamp()
    else:
        newer_than_timestamp = None

    with CaptureError() as error:
        access_token = _parse_token(access_token)
        client = SlackWebClient(token=access_token)

        channel_id = get_conversation_id(channel_name, access_token=access_token)
        response = client.conversations_history(
            channel=channel_id,
            limit=messages_limit,
            oldest=newer_than_timestamp,
        ).validate()

        context = {
            "access_token": access_token,
            "channel_name": channel_name,
            "channel_id": channel_id,
        }
        messages_result = ThreadMessages.model_validate(
            response.data, from_attributes=True, context=context
        )
        messages = messages_result.messages

        if saved_only:
            for idx in range(len(messages) - 1, -1, -1):
                message = messages[idx]
                is_message = message.type == "message"
                saved = getattr(message, "saved", {})
                in_progress = saved.get("state") == "in_progress"
                if not (is_message and in_progress):
                    messages.pop(idx)

        if with_replies:
            for message in messages:
                if not message.thread_ts:
                    continue  # not a thread

                replies = _get_message_replies(message, client=client)
                message.replies = Messages.model_validate(
                    {"messages": replies}, from_attributes=True, context=context
                )

        return Response(result=messages_result)

    return error.get_response()


@action(is_consequential=False)
def get_all_channels(
    channels_limit: int = 100, access_token: Secret = DEV_SLACK_ACCESS_TOKEN
) -> Response[list[str]]:
    """Return all the available public or private Slack channels.

    Args:
        channels_limit: The maximum number of channels that can be returned.

    Returns:
        A list with all the channel names which can be used with other actions.
    """
    with CaptureError() as error:
        access_token = _parse_token(access_token)

        response = (
            SlackWebClient(token=access_token)
            .conversations_list(
                exclude_archived=True,
                limit=channels_limit,
                types=["public_channel", "private_channel"],
            )
            .validate()
        )
        channel_names = [channel["name"] for channel in response.data["channels"]]
        return Response(result=channel_names)

    return error.get_response()
