from dataclasses import dataclass
from functools import lru_cache

from rapidfuzz.distance.Levenshtein import distance as levenshtein_distance
from rapidfuzz.process import extract as rapidfuzz_extract
from robocorp import log
from sema4ai.actions import Secret
from slack_sdk import WebClient as SlackWebClient
from typing_extensions import Self


class ConversationNotFoundError(Exception):
    def __init__(self, conversation_name: str):
        self.conversation_name = conversation_name
        super().__init__(f"'{conversation_name}' was not found")


@log.suppress
def map_users_id_to_display_name(
    *user_ids: str, access_token: str, return_only_found: bool = False
) -> dict[str, str]:
    cursor = None
    updates = 0

    result = {}

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
            if (member_id := member["id"]) in user_ids:
                result[member_id] = member["profile"]["real_name"]
                updates += 1

        if updates >= len(user_ids):
            return result

        try:
            cursor = response["response_metadata"]["next_cursor"]
        except KeyError:
            cursor = None

        if not cursor:
            if not return_only_found:
                # When populating username for conversation history,
                # we need the user ids to use as labels if the username was not found.
                result = {**{user_id: user_id for user_id in user_ids}, **result}

            return result


class UserConversationId(str):
    pass


class ChannelConversationId(str):
    pass


@dataclass
class ConversationsInfo:
    _access_token: Secret
    _conversation_name_to_id: dict[str, UserConversationId | ChannelConversationId]
    _user_id_to_conversation_id: dict[str, str]

    _updated: bool = False

    @classmethod
    @lru_cache(maxsize=1)
    def new(cls, *, access_token: str) -> Self:
        user_ids = {}
        conversations = {}

        while True:
            cursor = None

            response = (
                SlackWebClient(token=access_token)
                .conversations_list(
                    cursor=cursor,
                    types="public_channel,private_channel,mpim,im",
                )
                .validate()
            )

            for channel in response["channels"]:
                if channel.get("is_channel", False):
                    # We only add channels in the init, we will lazy-load the user info if it gets requested.
                    conversations[channel["name"].lower()] = ChannelConversationId(
                        channel["id"]
                    )
                else:
                    user_ids[channel["user"]] = channel["id"]

            try:
                cursor = response["response_metadata"]["next_cursor"]
            except KeyError:
                cursor = None

            if not cursor:
                break

        return cls(
            _conversation_name_to_id=conversations,
            _user_id_to_conversation_id=user_ids,
            _access_token=Secret.model_validate(access_token),
        )

    def _fetch_usernames(self):
        # Since we don't always need the usernames, we lazy load them on demand.
        if not self._updated:
            for user_id, user_name in map_users_id_to_display_name(
                *self._user_id_to_conversation_id.keys(),
                access_token=self._access_token.value,
                return_only_found=True,
            ).items():
                self._conversation_name_to_id[user_name.lower()] = UserConversationId(
                    self._user_id_to_conversation_id[user_id]
                )

            self._updated = True

        return self

    def _get_info(self, name: str) -> UserConversationId | ChannelConversationId | None:
        name = name.strip().lstrip("#").lower()

        if result := rapidfuzz_extract(
            name,
            list(self._conversation_name_to_id.keys()),
            scorer=levenshtein_distance,
            limit=1,
            score_cutoff=2,
        ):
            return self._conversation_name_to_id[result[0][0]]

        return None

    def get_channel_id(self, name: str) -> str | None:
        info = self._get_info(name)
        return str(info) if isinstance(info, ChannelConversationId) else None

    def get_user_id(self, name: str) -> str | None:
        self._fetch_usernames()

        info = self._get_info(name)
        return str(info) if isinstance(info, UserConversationId) else None


def get_conversation_id(name: str, *, access_token: str) -> str:
    conversations = ConversationsInfo.new(access_token=access_token)

    if channel_id := conversations.get_channel_id(name):
        return channel_id
    elif user_id := conversations.get_user_id(name):
        return user_id

    raise ConversationNotFoundError(name)
