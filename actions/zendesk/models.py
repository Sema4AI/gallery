from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_serializer
from typing_extensions import Annotated, Self


class User(BaseModel):
    id: Annotated[int, Field(description="Unique identifier of the user")]
    name: Annotated[str, Field(description="Name of the user")]
    created_at: Annotated[str, Field(description="Timestamp when the user was created")]
    updated_at: Annotated[
        str, Field(description="Timestamp when the user was last updated")
    ]
    email: Annotated[str, Field(description="Email address of the user")]
    role: Annotated[
        str, Field(description="Role of the user (end-user, agent or admin)")
    ]
    verified: Annotated[
        bool, Field(description="Indicates if any of the user's identities is verified")
    ]
    # Properties below are only available for an Agent or Admin
    role_type: Annotated[
        int | None,
        Field(
            description="The user's role id:"
            "0 for a custom agent,"
            "1 for a light agent, "
            "2 for a chat agent, "
            "3 for a chat agent added to the Support account as a contributor,"
            "4 for an admin,"
            "5 for a billing admin"
        ),
    ] = None
    suspended: Annotated[
        bool | None, Field(description="Indicates if the agent is suspended")
    ] = None
    active: Annotated[
        bool | None, Field(description="False if the user has been deleted")
    ] = None
    tags: Annotated[
        list[str] | None, Field(description="Tags associated with agent")
    ] = None
    ticket_restriction: Annotated[
        str | None,
        Field(
            default=None, description="Specifies which tickets the user has access to"
        ),
    ] = None


class Group(BaseModel):
    id: Annotated[int, Field(description="The unique identifier of the group")]
    name: Annotated[str, Field(description="The name of the group")]
    description: Annotated[
        str | None,
        Field(description="A brief description of the group"),
    ] = None
    default: Annotated[
        bool | None, Field(description="Indicates if this is the default group")
    ] = None


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
        User | int | None,
        Field(
            description="The user who requested the ticket",
            validation_alias="requester_id",
        ),
    ] = None
    assignee: Annotated[
        User | int | None,
        Field(
            description="The user assigned to the ticket",
            validation_alias="assignee_id",
        ),
    ] = None
    group: Annotated[
        Group | int | None,
        Field(
            description="The user assigned to the ticket",
            validation_alias="group_id",
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

    @field_validator("group", mode="before")
    def set_groups_data(cls, value: str, info: ValidationInfo) -> Group | str | None:
        if not info.context:
            return value

        if group := info.context.get("groups", {}).get(value):
            return Group.model_validate(group)

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


class UpdateTicket(BaseModel):
    assignee_id: Annotated[
        str | None, Field(description="The ID of the assigned user")
    ] = None
    group_id: Annotated[
        str | None, Field(description="The ID of the assigned group")
    ] = None

    def to_ticket(self):
        return {"ticket": self.model_dump(mode="json", exclude_none=True)}


class AddComment(BaseModel):
    body: Annotated[str, Field(description="The body of the comment in plain text")]
    public: Annotated[bool, Field(description="Indicates if the comment is public")]

    def to_ticket_comment(self):
        return {"ticket": {"comment": self.model_dump(mode="json")}}


class BaseResponse(BaseModel):
    @classmethod
    def from_response(cls, data: dict) -> Self:
        users_dict = {user["id"]: user for user in data.get("users") or []}
        groups_dict = {group["id"]: group for group in data.get("groups") or []}

        return cls.model_validate(
            data, context={"users": users_dict, "groups": groups_dict}
        )


class TicketsResponse(BaseResponse):
    results: Annotated[list[Ticket], Field(description="List of tickets")]


class CommentsResponse(BaseResponse):
    comments: Annotated[list[Comment], Field(description="List of ticket comments")]


class UsersResponse(BaseModel):
    users: Annotated[list[User], Field(description="List of users")]

    @classmethod
    def from_response(cls, data: dict) -> Self:
        return cls.model_validate(data)
