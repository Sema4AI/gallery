from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, model_validator


class TeamSearchRequest(BaseModel):
    team_name: str = Field(
        ..., description="The name of the Microsoft Team to search for."
    )


class ChannelMessageRequest(BaseModel):
    team_id: str = Field(..., description="The ID of the Microsoft Team.")
    channel_id: str = Field(..., description="The ID of the channel within the team.")
    message: str = Field(..., description="The message to post.")


class TeamDetails(BaseModel):
    display_name: str = Field(description="Display name of the team")
    description: str = Field(description="Description of the team")
    visibility: str = Field(
        description="Visibility of the team (public/private)", default="private"
    )


class UserSearch(BaseModel):
    email: Optional[EmailStr] = Field(None, description="Email address of the user")
    first_name: Optional[str] = Field(None, description="First name of the user")
    last_name: Optional[str] = Field(None, description="Last name of the user")

    @model_validator(mode="before")
    def check_at_least_one_field(cls, values):
        if not any(values.values()):
            raise ValueError(
                "At least one of email, first_name, or last_name must be provided"
            )
        return values


class SendMessageRequest(BaseModel):
    chat_id: str = Field(..., description="The ID of the chat to send the message to.")
    message: str = Field(..., description="The message content to send.")


class ChatCreationRequest(BaseModel):
    recipient_ids: List[str] = Field(
        ..., description="List of recipient user IDs for the chat."
    )


class AddUsersToTeamRequest(BaseModel):
    team_id: str = Field(..., description="The ID of the Microsoft Team.")
    user_ids: List[str] = Field(..., description="List of user IDs to add to the team.")


class GetChannelMessagesRequest(BaseModel):
    team_id: str = Field(..., description="The ID of the Microsoft Team.")
    channel_id: str = Field(..., description="The ID of the channel within the team.")
    limit: Optional[int] = Field(
        10, description="The number of messages to retrieve. Defaults to 10."
    )


class GetMessageRepliesRequest(BaseModel):
    team_id: str = Field(..., description="The ID of the Microsoft Team.")
    channel_id: str = Field(..., description="The ID of the channel within the team.")
    message_id: str = Field(
        ..., description="The ID of the message to get replies for."
    )


class ReplyMessageRequest(BaseModel):
    team_id: str = Field(..., description="The ID of the Microsoft Team.")
    channel_id: str = Field(..., description="The ID of the channel within the team.")
    message_id: str = Field(..., description="The ID of the message to reply to.")
    reply: str = Field(..., description="The content of the reply message.")
