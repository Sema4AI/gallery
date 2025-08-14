from typing import List, Literal

from pydantic import BaseModel, Field
from pydantic.functional_validators import BeforeValidator
from typing_extensions import Annotated


class EventDateTime(BaseModel):
    dateTime: Annotated[
        str | None,
        Field(description="The start or end time of the event"),
    ] = None
    timeZone: Annotated[
        str | None,
        Field(
            description="The time zone in which the time is specified, formatted as IANA Time Zone Database. "
            "For single events this field is optional."
        ),
    ] = None


class Attendee(BaseModel):
    email: Annotated[str, Field(description="The email address of the attendee")]
    displayName: Annotated[
        str | None, Field(description="The display name of the attendee")
    ] = None
    optional: Annotated[
        bool | None, Field(description="Whether this is an optional attendee")
    ] = None
    responseStatus: Annotated[
        str | None,
        Field(
            description="The response status of the attendee. "
            "Possible values: 'needsAction', 'declined', 'tentative', 'accepted'."
        ),
    ] = None
    organizer: Annotated[
        bool | None,
        Field(description="Whether the attendee is the organizer of the event"),
    ] = None


class ReminderOverride(BaseModel):
    method: Annotated[
        str, Field(description="The method of the reminder (email or popup)")
    ]
    minutes: Annotated[
        int,
        Field(
            description="The number of minutes before the event when the reminder should occur."
        ),
    ]


class Reminder(BaseModel):
    useDefault: Annotated[
        bool, Field(..., description="Indicates whether to use the default reminders.")
    ]
    overrides: Annotated[
        List[ReminderOverride] | None,
        Field(description="A list of overrides for the reminders."),
    ] = None


class Event(BaseModel):
    @staticmethod
    def set_datetime(values: dict):
        if values.get("date"):
            values["dateTime"] = values["date"]

        return values

    id: Annotated[str | None, Field(description="The id of the event")] = None
    summary: Annotated[str, Field(description="A short summary of the event's purpose")]
    location: Annotated[
        str | None, Field(description="The physical location of the event")
    ] = None
    description: Annotated[
        str | None, Field(description="A more detailed description of the event")
    ] = None
    start: Annotated[
        EventDateTime,
        BeforeValidator(set_datetime),
        Field(description="The (inclusive) start time of the event"),
    ]
    end: Annotated[
        EventDateTime,
        BeforeValidator(set_datetime),
        Field(description="The (exclusive) end time of the event"),
    ]
    recurrence: Annotated[
        List[str] | None,
        Field(
            description="A list of RRULE, EXRULE, RDATE, and EXDATE lines for a recurring event.",
        ),
    ] = None
    attendees: Annotated[
        List[Attendee] | None, Field(description="A list of attendees")
    ] = None
    reminders: Annotated[
        Reminder | None, Field(description="Reminders settings for the event")
    ] = None
    transparency: Annotated[
        Literal["opaque", "transparent"] | None,
        Field(
            description=(
                "Whether the event blocks time on the calendar. "
                "'opaque' means busy (default), 'transparent' means free."
            )
        ),
    ] = None


class CreateEvent(Event):
    start: Annotated[str, Field(description="The (inclusive) start time of the event")]
    end: Annotated[str, Field(description="The (exclusive) end time of the event")]


class UpdateEvent(BaseModel):
    summary: Annotated[
        str | None, Field(description="A short summary of the event's purpose")
    ] = None
    location: Annotated[
        str | None, Field(description="The physical location of the event")
    ] = None
    description: Annotated[
        str | None, Field(description="A more detailed description of the event")
    ] = None
    start: Annotated[
        str | None,
        Field(description="The (inclusive) start time of the event"),
    ] = None
    end: Annotated[
        str | None, Field(description="The (exclusive) end time of the event")
    ] = None
    attendees: Annotated[
        List[Attendee] | None,
        Field(
            description="A list of attendees consisting in email and whether they are mandatory to participate or not"
        ),
    ] = None
    reminders: Annotated[
        Reminder | None, Field(description="Reminders settings for the event")
    ] = None
    transparency: Annotated[
        Literal["opaque", "transparent"] | None,
        Field(
            description=(
                "Whether the event blocks time on the calendar. "
                "Use 'opaque' for busy or 'transparent' for free."
            )
        ),
    ] = None


class EventList(BaseModel):
    events: Annotated[List[Event], Field(description="A list of events")]


class Calendar(BaseModel):
    id: Annotated[str, Field(description="The id of the calendar")]
    summary: Annotated[str, Field(description="The name or summary of the calendar")]
    timeZone: Annotated[
        str,
        Field(
            description="The timezone the calendar is set to, such as 'Europe/Bucharest'"
        ),
    ]
    selected: Annotated[
        bool,
        Field(
            description="A boolean indicating if the calendar is selected by the user in their UI"
        ),
    ]
    accessRole: Annotated[
        str,
        Field(
            description="The access role of the user with respect to the calendar, e.g., 'owner'"
        ),
    ]


class CalendarList(BaseModel):
    calendars: Annotated[List[Calendar], Field(description="A list of calendars")]
