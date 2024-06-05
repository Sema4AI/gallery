from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class EventDateTime(BaseModel):
    dateTime: datetime = Field(description="The start or end time of the event.")
    timeZone: Optional[str] = Field(
        None,
        description="The time zone in which the time is specified, formatted as IANA Time Zone Database. "
        "For single events this field is optional.",
    )


class Attendee(BaseModel):
    email: str = Field(description="The email address of the attendee.")
    displayName: Optional[str] = Field(
        None, description="The display name of the attendee."
    )
    optional: Optional[bool] = Field(
        None, description="Whether this is an optional attendee."
    )
    responseStatus: Optional[str] = Field(
        None, description="The response status of the attendee."
    )
    organizer: Optional[bool] = Field(
        None, description="Whether the attendee is the organizer of the event."
    )


class ReminderOverride(BaseModel):
    method: str = Field(description="The method of the reminder (email or popup).")
    minutes: int = Field(
        description="The number of minutes before the event when the reminder should occur.",
    )


class Reminder(BaseModel):
    useDefault: bool = Field(
        ..., description="Indicates whether to use the default reminders."
    )
    overrides: Optional[List[ReminderOverride]] = Field(
        None, description="A list of overrides for the reminders."
    )


class Event(BaseModel):
    id: str = Field(description="The id of the event.")
    summary: str = Field(description="A short summary of the event's purpose.")
    location: Optional[str] = Field(
        None, description="The physical location of the event."
    )
    description: Optional[str] = Field(
        None, description="A more detailed description of the event."
    )
    start: EventDateTime = Field(description="The (inclusive) start time of the event.")
    end: EventDateTime = Field(description="The (exclusive) end time of the event.")
    recurrence: Optional[List[str]] = Field(
        None,
        description="A list of RRULE, EXRULE, RDATE, and EXDATE lines for a recurring event.",
    )
    attendees: Optional[List[Attendee]] = Field(
        None, description="A list of attendees."
    )
    # reminders: Reminder = Field(description="Reminders settings for the event.")


class UpdateEvent(BaseModel):
    summary: Optional[str] = Field(
        None, description="A short summary of the event's purpose."
    )
    location: Optional[str] = Field(
        None, description="The physical location of the event."
    )
    description: Optional[str] = Field(
        None, description="A more detailed description of the event."
    )
    start: Optional[EventDateTime] = Field(
        None, description="The (inclusive) start time of the event."
    )
    end: Optional[EventDateTime] = Field(
        None, description="The (exclusive) end time of the event."
    )
    attendees: Optional[List[Attendee]] = Field(
        None,
        description="A list of attendees consisting in email and whether they are mandatory to participate or not.",
    )


class EventList(BaseModel):
    events: List[Event]


class Calendar(BaseModel):
    id: str = Field(description="The id of the calendar.")
    summary: str = Field(description="The name or summary of the calendar.")
    timeZone: str = Field(
        description="The timezone the calendar is set to, such as 'Europe/Bucharest'."
    )
    selected: bool = Field(
        description="A boolean indicating if the calendar is selected by the user in their UI."
    )
    accessRole: str = Field(
        description="The access role of the user with respect to the calendar, e.g., 'owner'."
    )


class CalendarList(BaseModel):
    calendars: List[Calendar]
