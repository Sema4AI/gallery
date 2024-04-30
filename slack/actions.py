"""
A simple AI Action template for comparing timezones

Please check out the base guidance on AI Actions in our main repository readme:
https://github.com/robocorp/robocorp/blob/master/README.md

"""

import os
from functools import lru_cache
from pathlib import Path

import slack_sdk
from dotenv import load_dotenv
from sema4ai.actions import action, Secret

from models import MessageList

load_dotenv(Path("devdata") / ".env")


ACCESS_TOKEN = Secret.model_validate(os.getenv("SLACK_TOKEN", ""))


def _parse_token(token: Secret) -> str:
    return token.value or ACCESS_TOKEN.value


@lru_cache(maxsize=1000)
def _get_channel_id(channel_name: str, access_token: str) -> str:
    cursor = None
    channel_name = channel_name.lower()

    while True:
        response = (
            slack_sdk.WebClient(token=access_token)
            .conversations_list(
                exclude_archived=True,
                limit=1000,
                cursor=cursor,
                types="public_channel,private_channel",
            )
            .validate()
        )

        for channel in response["channels"]:
            if (
                channel_name == channel["name"].lower()
                and channel["is_channel"] is True
            ):
                return channel["id"]

        try:
            cursor = response["response_metadata"]["next_cursor"]
        except KeyError:
            pass

        if not cursor:
            raise ValueError(f"Channel '{channel_name}' not found")


@action(is_consequential=True)
def send_message_to_channel(
    channel_name: str, message: str, access_token: Secret = ACCESS_TOKEN
) -> bool:
    """Sends a message to the specified Slack channel.
    Args:
        channel_name: Slack channel to send the message to.
        message: Message to send on the Slack channel.
        access_token: The Slack application access token.

    Returns:
        Boolean value indicating success or failure.
    """
    access_token = _parse_token(access_token)

    response = (
        slack_sdk.WebClient(token=access_token)
        .chat_postMessage(channel=channel_name, text=message)
        .validate()
    )

    return bool(response.data.get("ok", False))


@action(is_consequential=False)
def read_messages_from_channel(
    channel_name: str, limit: int = 20, access_token: Secret = ACCESS_TOKEN
) -> MessageList:
    """Sends a message to the specified Slack channel.
    Args:
        channel_name: The name of the Slack channel to read the messages from.
        limit: The number of messages to read from the channel. Limited to a maximum of 1000.
        access_token: The Slack application access token.

    Returns:
        A structure  containing the messages and associated metadata from the specified Slack channel.
    """
    limit = min(limit, 1000)
    access_token = _parse_token(access_token)
    # When reading from a channel, the API label doesn't contain the `#` in the beginning of the channel name
    channel_name = channel_name.lstrip("#")

    response = (
        slack_sdk.WebClient(token=access_token)
        .conversations_history(
            channel=_get_channel_id(channel_name, access_token), limit=limit
        )
        .validate()
    )

    return MessageList.model_validate(response.data, from_attributes=True)
