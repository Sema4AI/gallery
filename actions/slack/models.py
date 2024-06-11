from datetime import datetime
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, Extra, Field, ValidationInfo, model_validator

from conversations import map_users_id_to_display_name

DataT = TypeVar("DataT")


class Messages(BaseModel, extra=Extra.allow):
    type: Annotated[str, Field(description="Message type")]
    # FIXME(cmin764): Add back the `alias="user"` param once the AS will support it.
    user: Annotated[str, Field(description="The raw user ID as received")]
    user_id: Annotated[str | None, Field(None, description="The ID of the user")]
    user_name: Annotated[str | None, Field(None, description="Human friendly username")]
    text: Annotated[str, Field(description="Message body")]
    ts: Annotated[
        datetime, Field(description="The timestamp when the message was posted")
    ]
    bot_id: Annotated[str | None, Field(None, description="The ID of the bot")]
    bot_name: Annotated[str | None, Field(None, description="The name of the bot")]

    @model_validator(mode="before")
    @classmethod
    def strip_extra_data(cls, data: dict) -> dict:
        """Strips down some extra data from the payload to reduce model input."""

        data.pop("blocks", None)
        # The API is a very inconsistent, but if we do get this data,
        # we trim it down since we already need to fetch all usernames for the cases where we don't have it.
        data.pop("user_profile", None)

        if bot_profile := data.pop("bot_profile", None):  # type: dict | None
            data["bot_name"] = bot_profile.get("name")

        return data


class MessageList(BaseModel, extra=Extra.ignore):
    messages: list[Messages]

    @model_validator(mode="after")
    def update_user_names(self, info: ValidationInfo):
        users_display_name = map_users_id_to_display_name(
            *(m.user for m in self.messages if not m.bot_name),
            access_token=info.context["access_token"],
        )

        for message in self.messages:
            message.user_id = message.user
            if message.bot_name:
                message.user_name = message.bot_name
            else:
                message.user_name = users_display_name[message.user]

        return self


class Response(BaseModel, Generic[DataT]):
    result: DataT | None = None
    error: str | None = None
