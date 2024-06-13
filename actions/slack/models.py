from datetime import datetime
from typing import Annotated, TypeVar

from pydantic import BaseModel, Field, ValidationInfo, model_validator

from conversations import map_user_ids_to_display_name

DataT = TypeVar("DataT")


class Message(BaseModel, extra="allow"):
    type: Annotated[str, Field(description="Type of the message")]
    user: Annotated[str, Field(description="Human friendly username")]
    text: Annotated[str, Field(description="Message body")]
    ts: Annotated[datetime, Field(description="The timestamp when the message was posted")]
    thread_ts: Annotated[
        datetime | None, Field(None, description="The timestamp when the thread was posted")
    ]
    user_id: Annotated[
        str, Field(description="The ID of the user", validation_alias="user")
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


class BaseMessages(BaseModel, extra="ignore"):
    @model_validator(mode="before")
    @classmethod
    def strip_extra_data(cls, data: dict, info: ValidationInfo) -> dict:
        for message in data["messages"]:
            for key in ("channel_id", "channel_name"):
                message[key] = info.context[key]

        return data

    @model_validator(mode="after")
    def update_user_names(self, info: ValidationInfo):
        user_ids = [msg.user_id for msg in self.messages if not msg.bot_name]
        if user_ids:
            users_display_name = map_user_ids_to_display_name(
                *user_ids, access_token=info.context["access_token"]
            )
        else:
            users_display_name = {}

        for message in self.messages:
            if message.bot_name:
                message.user = message.bot_name
            else:
                message.user = users_display_name[message.user_id]

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
