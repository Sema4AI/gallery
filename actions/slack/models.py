import re
from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, Field, ValidationInfo, model_validator

from conversations import map_user_ids_to_display_name


RE_USER_ID = re.compile(r"<@U\w+>")  # user ID in text
USER_ID_NAME_MAP = {}  # cache resolved user IDs into names


class Message(BaseModel, extra="allow"):
    type: Annotated[str, Field(description="Type of the message")]
    user: Annotated[str, Field(description="The raw user ID as received")]
    # FIXME(cmin764): Add back the `alias="user"` param once the AS will support it,
    #  then remove the `user` field.
    user_id: Annotated[str | None, Field(None, description="The ID of the user")]
    user_name: Annotated[str | None, Field(None, description="Human friendly username")]
    text: Annotated[str, Field(description="Message body")]
    # NOTE(cmin764): Keeping these timestamps as originally received to query for
    #  thread replies accurately using their value as it is.
    ts: Annotated[str, Field(description="The timestamp when the message was posted")]
    thread_ts: Annotated[
        str | None,
        Field(None, description="The timestamp when the thread was started"),
    ]
    date: Annotated[
        str | None,
        Field(None, description="The date and time of the posted message in UTC"),
    ]
    channel_id: Annotated[
        str, Field(description="Channel ID where the message belongs")
    ]
    channel_name: Annotated[
        str, Field(description="Channel name where the message belongs")
    ]
    bot_id: Annotated[str | None, Field(None, description="The ID of the bot")]
    bot_name: Annotated[str | None, Field(None, description="The name of the bot")]

    @model_validator(mode="before")
    @classmethod
    def strip_extra_data(cls, data: dict) -> dict:
        """Strips down some extra data from the payload to reduce model input."""

        data.pop("blocks", None)
        # The API is a very inconsistent, but if we do get this data, we trim it down
        #  since we already need to fetch all usernames for the cases where we don't
        #  have it.
        data.pop("user_profile", None)

        if bot_profile := data.pop("bot_profile", None):  # type: dict | None
            data["bot_name"] = bot_profile.get("name")

        return data

    @model_validator(mode="after")
    def refine_user_data(self):
        self.user_id = self.user
        self.date = datetime.fromtimestamp(float(self.ts), tz=timezone.utc).isoformat()
        return self


class BaseMessages(BaseModel, extra="ignore"):
    @model_validator(mode="before")
    @classmethod
    def augment_input_data(cls, data: dict, info: ValidationInfo) -> dict:
        for message in data["messages"]:
            for key in ("channel_id", "channel_name"):
                message[key] = info.context[key]

        return data

    @model_validator(mode="after")
    def update_user_names(self, info: ValidationInfo):
        # Map user IDs to names for every such reference encountered.
        user_ids = set()
        for message in self.messages:
            user_ids.add(message.user_id)
            for match in RE_USER_ID.finditer(message.text):
                user_ids.add(match.group().strip("<@>"))
        user_ids -= set(USER_ID_NAME_MAP)
        if user_ids:  # retrieve for new IDs only
            users_display_name = map_user_ids_to_display_name(
                *user_ids, access_token=info.context["access_token"]
            )
            USER_ID_NAME_MAP.update(users_display_name)

        for message in self.messages:
            if message.bot_name:
                message.user_name = message.bot_name
            else:
                message.user_name = USER_ID_NAME_MAP[message.user_id]
            message.text = RE_USER_ID.sub(
                lambda match: f"@{USER_ID_NAME_MAP[match.group().strip('<@>')]}",
                message.text,
            )

        return self


class Messages(BaseMessages):
    messages: Annotated[list[Message], Field(description="List of final messages")]


class ThreadMessage(Message):
    replies: Annotated[
        Messages,
        Field(
            default_factory=lambda: Messages(messages=[]), description="Thread replies"
        ),
    ]


class ThreadMessages(BaseMessages):
    messages: Annotated[
        list[ThreadMessage], Field(description="List of thread messages")
    ]
