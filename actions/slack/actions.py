"""Prebuilt AI Actions package that integrates with Slack SDK.

The package currently supports channels retrieval, reading and sending messages.
"""

import contextlib
import os
from datetime import datetime
from pathlib import Path
from typing import Generator

from conversations import ConversationNotFoundError, get_conversation_id
from dotenv import load_dotenv
from models import Messages, ThreadMessage, ThreadMessageList
from sema4ai.actions import ActionError, Response, Secret, action
from slack_sdk import WebClient as SlackWebClient
from slack_sdk.errors import SlackApiError

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")

DEV_SLACK_ACCESS_TOKEN = Secret.model_validate(os.getenv("DEV_SLACK_ACCESS_TOKEN", ""))


@contextlib.contextmanager
def _build_api_client(access_token: Secret) -> Generator[SlackWebClient, None, None]:
    # Offers a Slack API client and treats known errors during its operation.
    token: str = access_token.value or DEV_SLACK_ACCESS_TOKEN.value
    try:
        yield SlackWebClient(token=token)
    except ConversationNotFoundError as exc:
        raise ActionError(exc) from exc
    except SlackApiError as exc:
        message = str(exc)
        if exc.response["error"] == "not_in_channel":
            message = "slack bot isn't added to the channel"
        raise ActionError(message) from exc


@action(is_consequential=True)
def send_message_to_channel(
    channel_name: str, message: str, access_token: Secret = DEV_SLACK_ACCESS_TOKEN
) -> Response[bool]:
    """Sends a message to the specified Slack channel.

    Based on how the Slack access token was generated, the message can be sent straight
    from the bot or on behalf of the user which obtained the token. You can detect a
    message sent by a bot by observing the values of the `bot_id` and `bot_name` fields
    under the retrieved message content.

    Args:
        channel_name: Slack channel to send the message to.
        message: Message to send on the Slack channel.
        access_token: The Slack application access token.

    Returns:
        A structure containing a boolean if the message was successfully sent or an
        error if such occurred.
    """
    with _build_api_client(access_token) as client:
        response = client.chat_postMessage(
            channel=get_conversation_id(channel_name, client=client), text=message
        ).validate()

    return Response(result=bool(response.data.get("ok", False)))


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
) -> Response[ThreadMessageList]:
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
        newer_than: Get messages newer than the specified date in YYYY-MM-DD format.
        saved_only: Enable this to return only the saved messages.
        with_replies: Enable this to retrieve message thread replies as well.
        access_token: The Slack application access token.

    Returns:
        A structure containing the messages and associated metadata from the specified
        Slack channel or an error if such occurred.
    """
    if newer_than:
        newer_than_date = datetime.strptime(newer_than, "%Y-%m-%d")
        newer_than_timestamp = newer_than_date.timestamp()
    else:
        newer_than_timestamp = None

    with _build_api_client(access_token) as client:
        channel_id = get_conversation_id(channel_name, client=client)
        response = client.conversations_history(
            channel=channel_id,
            limit=messages_limit,
            oldest=newer_than_timestamp,
        ).validate()

        context = {
            "client": client,
            "channel_name": channel_name,
            "channel_id": channel_id,
        }
        messages_result = ThreadMessageList.model_validate(
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


@action(is_consequential=False)
def get_all_channels(
    channels_limit: int = 100, access_token: Secret = DEV_SLACK_ACCESS_TOKEN
) -> Response[list[str]]:
    """Return all the available public or private Slack channels.

    Args:
        channels_limit: The maximum number of channels that can be returned.
        access_token: The Slack application access token.

    Returns:
        A list with all the channel names which can be used with other actions.
    """
    with _build_api_client(access_token) as client:
        response = client.conversations_list(
            exclude_archived=True,
            limit=channels_limit,
            types=["public_channel", "private_channel"],
        ).validate()

    channel_names = [channel["name"] for channel in response.data["channels"]]
    return Response(result=channel_names)
