from typing import List

from pydantic import (
    BaseModel,
    Field,
    field_serializer,
    field_validator,
)
from typing_extensions import Annotated


class QueryParams(BaseModel):
    filter: Annotated[
        str | None,
        Field(
            serialization_alias="$filter",
            description="Optional OData filter parameter for customizing the query",
        ),
    ] = None
    search: Annotated[
        str | None,
        Field(
            serialization_alias="$search", description="Optional OData search parameter"
        ),
    ] = None


class Calendar(BaseModel):
    id: Annotated[str, Field(description="Calendar ID")]
    name: Annotated[str | None, Field(description="Calendar name")]


class EmailAddress(BaseModel):
    name: Annotated[str | None, Field(description="The name of the email owner")] = None
    address: Annotated[str, Field(description="The email address")]


class ResponseStatus(BaseModel):
    response: Annotated[
        str | None,
        Field(
            description="The response type. Possible values are: none, organizer, tentativelyAccepted, "
            "accepted, declined, notResponded."
        ),
    ] = None
    time: Annotated[
        str | None,
        Field(description="The date and time when the response was returned"),
    ] = None


class Attendee(BaseModel):
    type: Annotated[
        str, Field(description="The attendee type: required, optional, resource")
    ]
    emailAddress: Annotated[
        EmailAddress, Field(description="The email address object of the attendee")
    ]
    status: Annotated[
        ResponseStatus | None,
        Field(description="The status of the attendee's response"),
    ] = None


class AddAttendee(BaseModel):
    type: Annotated[
        str, Field(description="The attendee type: required, optional, resource")
    ]
    email: Annotated[str, Field(description="The email address of the attendee")]
    name: Annotated[str | None, Field(description="The name of the attendee")] = None

    def to_attendee(self) -> "Attendee":
        email_address = EmailAddress(name=self.name, address=self.email)

        return Attendee(type=self.type, emailAddress=email_address)


class Location(BaseModel):
    displayName: Annotated[str, Field(description="The display name of the location")]


class EventDateTime(BaseModel):
    dateTime: Annotated[
        str | None,
        Field(description="The start or end time of the event"),
    ] = None
    timeZone: Annotated[
        str | None,
        Field(description="The time zone in which the time is specified"),
    ] = None


class Pattern(BaseModel):
    type: Annotated[
        str,
        Field(
            description="The recurrence pattern type: daily, weekly, absoluteMonthly, relativeMonthly,"
            " absoluteYearly, relativeYearly"
        ),
    ]
    interval: Annotated[
        int,
        Field(
            description="The number of units between occurrences, where units can be in days, weeks, months, or years, "
            "depending on the type"
        ),
    ]
    daysOfWeek: Annotated[
        List[str],
        Field(
            description="A collection of the days of the week on which the event occurs."
            "If type is relativeMonthly or relativeYearly, and daysOfWeek specifies more than one day, the event falls "
            "on the first day that satisfies the pattern."
            "Required if type is weekly, relativeMonthly, or relativeYearly"
        ),
    ]
    dayOfMonth: Annotated[
        int | None,
        Field(
            description="The day of the month on which the event occurs. "
            "Required if type is absoluteMonthly or absoluteYearly"
        ),
    ] = None
    firstDayOfWeek: Annotated[
        str | None,
        Field(
            description="The first day of the week on which the event occurs."
            "Default is sunday. Required if type is weekly"
        ),
    ] = None
    index: Annotated[
        str | None,
        Field(
            description="Specifies on which instance of the allowed days specified in daysOfWeek the event occurs, "
            "counted from the first instance in the month. The possible values are: first, second, third, fourth, last."
            "Default is first. Optional and used if type is relativeMonthly or relativeYearly"
        ),
    ] = None
    month: Annotated[
        int | None,
        Field(
            description="The month in which the event occurs. This is a number from 1 to 12"
        ),
    ] = None


class Range(BaseModel):
    type: Annotated[
        str,
        Field(
            description="The recurrence range. The possible values are: endDate, noEnd, numbered."
            "endDate -> Range with end date and requires: type, startDate, endDate"
            "noEnd -> Range without an end date and requires: type, startDate"
            "numbered -> Range with specific number of occurrences and requires: type, startDate, numberOfOccurrences"
        ),
    ]
    startDate: Annotated[
        str,
        Field(
            description="The date to start applying the recurrence pattern. "
            "The first occurrence of the meeting may be this date or later, depending on the recurrence pattern of "
            "the event. Must be the same value as the start property of the recurring event."
        ),
    ]
    endDate: Annotated[
        str | None,
        Field(
            description="The date to stop applying the recurrence pattern. "
            "Depending on the recurrence pattern of the event, the last occurrence of the meeting may not be this date."
            "Required if type is endDate."
        ),
    ] = None
    numberOfOccurrences: Annotated[
        int | None,
        Field(
            description="The number of times to repeat the event. Required and must be positive if type is numbered."
        ),
    ] = None


class Recurrence(BaseModel):
    pattern: Annotated[Pattern, Field(description="The frequency of an event")]
    range: Annotated[Range, Field(description="The duration of an event")]


class EventBody(BaseModel):
    contentType: Annotated[
        str,
        Field(
            description="The content type of the event; possible values: text and html."
        ),
    ]
    content: Annotated[str, Field(description="The body of the event")]


class BaseEvent(BaseModel):
    start: Annotated[
        EventDateTime, Field(description="The start date and time of the event")
    ]
    end: Annotated[
        EventDateTime, Field(description="The end date and time of the event")
    ]
    subject: Annotated[str | None, Field(description="The subject of the event")] = None
    body: Annotated[EventBody | None, Field(description="The body of the event")] = None
    attendees: Annotated[
        List[Attendee] | None, Field(description="The list of attendees")
    ] = None
    location: Annotated[
        Location | None, Field(description="The location of the event")
    ] = None
    onlineMeetingProvider: Annotated[
        str | None, Field(description="The online meeting provider")
    ] = None
    isOnlineMeeting: Annotated[
        bool | None, Field(description="Whether the event is an online meeting")
    ] = None
    recurrence: Annotated[
        Recurrence | None, Field(description="The recurrence of the event")
    ] = None


class Event(BaseEvent):
    id: Annotated[str, Field(description="The id of the event")]
    bodyPreview: Annotated[str | None, Field(description="The body of the event")] = (
        None
    )
    organizer: Annotated[
        EmailAddress | None,
        Field(description="The organizer of the event"),
    ] = None
    importance: Annotated[
        str | None, Field(description="The importance of the event")
    ] = None
    isDraft: Annotated[bool | None, Field(description="Whether the event is draft")] = (
        None
    )

    @field_validator("organizer", mode="before")
    def set_organizer(cls, value: dict) -> EmailAddress | None:
        if value.get("emailAddress"):
            return EmailAddress.model_validate(value["emailAddress"])

        return None


class CreateEvent(BaseEvent):
    start: Annotated[str, Field(description="The start date and time of the event")]
    end: Annotated[str, Field(description="The end date and time of the event")]
    timeZone: Annotated[
        str,
        Field(
            description="Specifies the timezone for the start or end date. "
            "This field is required when defining a start or end date. By default, it should match the value "
            "returned by the get_mailbox_timezone action unless specified otherwise by the user."
        ),
    ]
    attendees: Annotated[
        List[AddAttendee] | None, Field(description="The list of attendees")
    ] = None

    @field_serializer("attendees")
    def serialize_attendees(
        self, attendees: list[AddAttendee], _info
    ) -> list[dict] | None:
        if not attendees:
            return None

        return [
            add_attendee.to_attendee().model_dump(mode="json", exclude_none=True)
            for add_attendee in attendees
        ]

    @field_serializer("start")
    def serialize_start(self, start: str, _info) -> dict | None:
        if not start:
            return None

        return {"dateTime": start, "timeZone": self.timeZone or "UTC"}

    @field_serializer("end")
    def serialize_end(self, end: str, _info) -> dict | None:
        if not end:
            return None

        return {"dateTime": end, "timeZone": self.timeZone or "UTC"}


class UpdateEvent(CreateEvent):
    start: Annotated[
        str | None, Field(description="The start date and time of the event")
    ] = None
    end: Annotated[
        str | None, Field(description="The end date and time of the event")
    ] = None
    timeZone: Annotated[
        str | None,
        Field(
            description="Specifies the timezone for the start or end date. "
            "This field is required when defining a start or end date. By default, it should match the value "
            "returned by the get_mailbox_timezone action unless specified otherwise by the user."
        ),
    ] = None
