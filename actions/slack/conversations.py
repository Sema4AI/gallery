from dataclasses import dataclass
from functools import lru_cache

from rapidfuzz.distance.Levenshtein import distance as levenshtein_distance
from rapidfuzz.process import extract as rapidfuzz_extract
from robocorp import log
from slack_sdk import WebClient as SlackWebClient
from typing_extensions import Self


class ConversationNotFoundError(Exception):
    def __init__(self, conversation_name: str):
        self.conversation_name = conversation_name
        super().__init__(f"{conversation_name!r} was not found")


@log.suppress
def map_user_ids_to_display_names(
    *user_ids: str, client: SlackWebClient, strict: bool = True
) -> dict[str, str]:
    cursor = None
    result = {}
    updates = 0

    while True:
        response = client.users_list(limit=1000, cursor=cursor).validate()
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
            if not strict:
                # When populating the user names for conversation history, we accept
                #  the user IDs to be used as labels as well if the real user name was
                #  not found at all.
                result = {**{user_id: user_id for user_id in user_ids}, **result}

            return result


class UserConversationId(str):
    pass


class ChannelConversationId(str):
    pass


@dataclass
class ConversationsInfo:
    _client: SlackWebClient
    _conversation_name_to_id: dict[str, UserConversationId | ChannelConversationId]
    _user_id_to_conversation_id: dict[str, str]
    _updated: bool = False

    @classmethod
    @lru_cache(maxsize=1)
    def new(cls, *, client: SlackWebClient) -> Self:
        user_ids = {}
        conversations = {}
        cursor = None

        while True:
            response = client.conversations_list(
                cursor=cursor,
                limit=999,
                types="public_channel,private_channel,mpim,im",
            ).validate()
            for channel in response["channels"]:
                if channel.get("is_channel", False):
                    # We only add channels in the init, we will lazy-load the user info
                    #  if it gets requested.
                    conversations[channel["name"].lower()] = ChannelConversationId(
                        channel["id"]
                    )
                else:
                    user_ids[channel["user"]] = channel["id"]

            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        return cls(
            _conversation_name_to_id=conversations,
            _user_id_to_conversation_id=user_ids,
            _client=client,
        )

    def _fetch_usernames(self):
        # Since we don't always need the user names, we lazy load them on demand.
        if not self._updated:
            for user_id, user_name in map_user_ids_to_display_names(
                *self._user_id_to_conversation_id.keys(),
                client=self._client,
                strict=False,
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


def get_conversation_id(name: str, *, client: SlackWebClient) -> str:
    conversations = ConversationsInfo.new(client=client)

    if channel_id := conversations.get_channel_id(name):
        return channel_id
    elif user_id := conversations.get_user_id(name):
        return user_id

    raise ConversationNotFoundError(name)
