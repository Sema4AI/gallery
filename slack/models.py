from datetime import datetime
from typing import List, Annotated, Dict, Optional, TypeVar, Generic

from pydantic import BaseModel, Extra, model_validator, ValidationInfo, Field

from utils import get_users_id_to_display_name

DataT = TypeVar("DataT")


class Messages(BaseModel, extra=Extra.allow):
    type: str
    user: str = Field(description="Human friendly username")
    text: str = Field(description="Message body")
    ts: datetime = Field(description="The timestamp when the messaage was posted")
    user_id: Annotated[str, Field(validation_alias="user")]
    bot_profile: Optional[Dict] = Field(
        None, description="Mapping containing bot profile information"
    )


class MessageList(BaseModel, extra=Extra.ignore):
    messages: List[Messages]

    @model_validator(mode="after")
    def update_user_names(self, info: ValidationInfo):
        users_display_name = get_users_id_to_display_name(
            *(m.user_id for m in self.messages if not m.bot_profile),
            access_token=info.context["access_token"],
        )

        for message in self.messages:
            if message.bot_profile and (bot_name := message.bot_profile.get("name")):
                message.user = bot_name
            else:
                message.user = users_display_name[message.user_id]

        return self


class Response(BaseModel, Generic[DataT]):
    result: Optional[DataT] = None
    error: Optional[str] = None
