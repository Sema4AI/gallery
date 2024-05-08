from datetime import datetime
from typing import Annotated, TypeVar, Generic

from pydantic import BaseModel, Extra, model_validator, ValidationInfo, Field

from utils import get_users_id_to_display_name

DataT = TypeVar("DataT")


class Messages(BaseModel, extra=Extra.allow):
    type: str
    user: str = Field(description="Human friendly username")
    text: str = Field(description="Message body")
    ts: Annotated[
        datetime, Field(description="The timestamp when the message was posted")
    ]
    user_id: Annotated[
        str, Field(description="The ID of the user", validation_alias="user")
    ]
    bot_id: Annotated[str | None, Field(description="The ID of the bot")] = None
    bot_name: Annotated[str | None, Field(description="The name of the bot")] = None

    @model_validator(mode="before")
    @classmethod
    def strip_extra_data(cls, data: dict) -> dict:
        """Strips down some extra data from the payload to reduce model input"""

        data.pop("blocks", None)

        if bot_profile := data.pop("bot_profile", None):  # type: dict | None
            data["bot_name"] = bot_profile.get("name")

        return data


class MessageList(BaseModel, extra=Extra.ignore):
    messages: list[Messages]

    @model_validator(mode="after")
    def update_user_names(self, info: ValidationInfo):
        users_display_name = get_users_id_to_display_name(
            *(m.user_id for m in self.messages if not m.bot_name),
            access_token=info.context["access_token"],
        )

        for message in self.messages:
            if message.bot_name:
                message.user = message.bot_name
            else:
                message.user = users_display_name[message.user_id]

        return self


class Response(BaseModel, Generic[DataT]):
    result: DataT | None = None
    error: str | None = None
