from functools import lru_cache
from slack_sdk import WebClient as SlackWebClient
from typing import Dict, TypeVar, Callable

T = TypeVar("T", bound=Callable)


class ChannelNotFoundError(Exception):
    def __init__(self, channel_name: str):
        self.channel_name = channel_name
        super().__init__(f"Channel '{channel_name}' not found")


def get_users_display_name(*user_ids: str, access_token: str) -> Dict[str, str]:
    cursor = None
    updates = 0
    result = {uid: uid for uid in user_ids}

    while True:
        response = (
            SlackWebClient(token=access_token)
            .users_list(
                limit=1000,
                cursor=cursor,
            )
            .validate()
        )

        for member in response.get("members", []):
            if member["id"] in result:
                result[member["id"]] = member["name"]
                updates += 1

        if updates >= len(user_ids):
            return result

        try:
            cursor = response["response_metadata"]["next_cursor"]
        except KeyError:
            pass

        if not cursor:
            return result


@lru_cache(maxsize=1000)
def get_channel_id(channel_name: str, *, access_token: str) -> str:
    cursor = None
    channel_name = channel_name.lower()

    while True:
        response = (
            SlackWebClient(token=access_token)
            .conversations_list(
                exclude_archived=True,
                limit=1000,
                cursor=cursor,
                types="public_channel,private_channel",
            )
            .validate()
        )

        for channel in response.get("channels", []):
            if channel_name == channel["name"].lower() and channel["is_channel"] is True:
                return channel["id"]

        try:
            cursor = response["response_metadata"]["next_cursor"]
        except KeyError:
            pass

        if not cursor:
            raise ChannelNotFoundError(channel_name)


# @contextmanager
# def handle_error() -> Callable:
#
#     ctx = {"error": None}
#
#     try:
#         yield ctx
#     except SlackApiError as e:
#         ctx["error"] = e.response["error"]
#     except ChannelNotFoundError as e:
#         ctx["error"] = str(e)
