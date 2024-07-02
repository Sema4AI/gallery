from pydantic import BaseModel, Field, ValidationInfo, field_validator
from typing_extensions import Annotated, Self


class User(BaseModel):
    id: Annotated[int, Field(description="The unique identifier for the user")]
    name: Annotated[str, Field(description="The name of the user")]
    email: Annotated[str, Field(description="The email address of the user")]


class Rating(BaseModel):
    comment: Annotated[str, Field(description="Comment for rating")]
    score: Annotated[int, Field(description="Score for rating")]


class Ticket(BaseModel):
    id: Annotated[int, Field(description="The unique identifier of the ticket")]
    subject: Annotated[str | None, Field(description="The subject of the ticket")] = (
        None
    )
    description: Annotated[
        str | None,
        Field(description="The detailed description of the ticket"),
    ] = None
    status: Annotated[str, Field(description="The current status of the ticket")]
    created_at: Annotated[
        str, Field(description="The datetime when the ticket was created")
    ]
    updated_at: Annotated[
        str, Field(description="The datetime when the ticket was updated")
    ]
    priority: Annotated[str | None, Field(description="The priority of the ticket")] = (
        None
    )
    type: Annotated[
        str | None,
        Field(
            description="The type of the ticket. Allowed values are 'problem', 'incident', 'question', or 'task'."
        ),
    ] = None
    requester: Annotated[
        User | str | None,
        Field(
            description="The user who requested the ticket",
            validation_alias="requester_id",
        ),
    ] = None
    assignee: Annotated[
        User | str | None,
        Field(
            description="The user assigned to the ticket",
            validation_alias="assignee_id",
        ),
    ] = None
    due_at: Annotated[
        str | None,
        Field(description="If this is a ticket of type 'task' it has a due date"),
    ] = None
    tags: Annotated[list | None, Field(description="List of tags for the ticket")] = (
        None
    )
    satisfaction_rating: Annotated[
        Rating | None, Field(description="Rating of the ticket")
    ] = None

    @field_validator("assignee", "requester", mode="before")
    def set_users_data(cls, value: str, info: ValidationInfo) -> User | str | None:
        if not info.context:
            return value

        if user := info.context.get("users", {}).get(value):
            return User.model_validate(user)

        return value


class Comment(BaseModel):
    id: Annotated[int, Field(description="The unique identifier of the comment")]
    author_id: Annotated[
        User | str | None, Field(description="The ID of the author of the comment")
    ]
    body: Annotated[str, Field(description="The body of the comment in plain text")]
    html_body: Annotated[
        str, Field(description="The body of the comment in HTML format")
    ]
    public: Annotated[bool, Field(description="Indicates if the comment is public")]
    created_at: Annotated[
        str,
        Field(
            description="The timestamp when the comment was created in ISO 8601 format"
        ),
    ]

    @field_validator("author_id", mode="before")
    def set_users_data(cls, value: str, info: ValidationInfo) -> User | str | None:
        if not info.context:
            return value

        if user := info.context.get("users", {}).get(value):
            return User.model_validate(user)

        return value


class BaseResponse(BaseModel):
    users: Annotated[
        list[User] | None, Field(description="List of users", exclude=True)
    ] = None

    @classmethod
    def from_response(cls, data: dict) -> Self:
        user_dict = {user["id"]: user for user in data.get("users") or []}

        return cls.model_validate(data, context={"users": user_dict})


class TicketResponse(BaseResponse):
    results: Annotated[list[Ticket], Field(description="List of tickets")]


class CommentsResponse(BaseResponse):
    comments: Annotated[list[Comment], Field(description="List of ticket comments")]
