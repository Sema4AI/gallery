from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from sema4ai.actions import OAuth2Secret, Response, action

from models import CalendarList, CreateEvent, Event, EventList, UpdateEvent

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")


def _build_service(credentials: OAuth2Secret) -> Resource:
    creds = Credentials(token=credentials.access_token)

    return build("calendar", "v3", credentials=creds)


@action(is_consequential=True)
def create_event(
    google_credentials: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/calendar.events"]],
    ],
    event: CreateEvent,
    calendar_id: str = "primary",
) -> Response[Event]:
    """Creates a new event in the specified calendar.

    Args:
        google_credentials: JSON containing Google OAuth2 credentials.
        event: JSON representation of the Google Calendar V3 event.
        calendar_id: Calendar identifier which can be found by listing all calendars action.
            Default value is "primary" which indicates the calendar where the user is currently logged in.

    Returns:
        The newly created event.
    """
    service = _build_service(google_credentials)

    event_dict = event.model_dump(mode="json", exclude={"id"}, exclude_none=True)

    event_dict["start"] = {"dateTime": event_dict["start"]}
    event_dict["end"] = {"dateTime": event_dict["end"]}
    if event_dict.get("attendees"):
        for attendee in event_dict["attendees"]:
            attendee["responseStatus"] = "needsAction"

    event = service.events().insert(calendarId=calendar_id, body=event_dict).execute()

    return Response(result=Event(**event))


@action(is_consequential=False)
def list_events(
    google_credentials: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/calendar.readonly"]],
    ],
    calendar_id: str = "primary",
    query: str = "",
    start_date: str = "",
    end_date: str = "",
) -> Response[EventList]:
    """List all events in the user's primary calendar between the given dates.

    To aggregate all events across calendars, call this method for each calendar returned by list_calendars endpoint.
    Ideally a start and end date should always be provided, otherwise we will look in the whole future or past.

    Args:
        google_credentials: JSON containing Google OAuth2 credentials.
        calendar_id: Calendar identifier which can be found by listing all calendars action.
            Default value is "primary" which indicates the calendar where the user is currently logged in.
        query: Free text search terms to find events that match these terms in summary, description, location,
            attendee's name / email or working location information.
        start_date: Upper bound (exclusive) for an event's start time to filter by.
            Must be an RFC3339 timestamp with mandatory time zone offset.
        end_date: Lower bound (exclusive) for an event's end time to filter by.
            Must be an RFC3339 timestamp with mandatory time zone offset.

    Returns:
        A list of calendar events that match the query, if defined.

    """
    service = _build_service(google_credentials)

    events = (
        service.events()
        .list(
            calendarId=calendar_id,
            q=query if query else None,
            timeMin=start_date if start_date else None,
            timeMax=end_date if end_date else None,
            singleEvents=True,
        )
        .execute()
        .get("items", [])
    )

    filtered_events = [event for event in events if event.get("status") != "cancelled"]

    return Response(result=EventList(events=filtered_events))


@action(is_consequential=False)
def list_calendars(
    google_credentials: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/calendar.readonly"]],
    ],
) -> Response[CalendarList]:
    """List all calendars that the user is subscribed to.

    Args:
        google_credentials: JSON containing Google OAuth2 credentials.

    Returns:
        A list of calendars.

    """
    service = _build_service(google_credentials)

    calendars = service.calendarList().list().execute().get("items", [])

    return Response(result=CalendarList(calendars=calendars))


@action(is_consequential=True)
def update_event(
    google_credentials: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/calendar.events"]],
    ],
    event_id: str,
    updates: UpdateEvent,
    calendar_id: str = "primary",
) -> Response[Event]:
    """Update an existing Google Calendar event with dynamic arguments.

    Args:
        google_credentials: JSON containing Google OAuth2 credentials.
        calendar_id: Identifier of the calendar where the event is.
            Default value is "primary" which indicates the calendar where the user is currently logged in.
        event_id: Identifier of the event to update. Can be found by listing events in all calendars.
        updates: A dictionary containing the event attributes to update.
            Possible keys include 'summary', 'description', 'start', 'end', and 'attendees'.

    Returns:
        Updated event details.
    """
    service = _build_service(google_credentials)
    event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

    updates_dump = updates.model_dump(mode="json", exclude_none=True)

    if updates.start:
        updates_dump["start"] = {"dateTime": updates_dump["start"]}
    if updates.end:
        updates_dump["end"] = {"dateTime": updates_dump["end"]}

    event.update(updates_dump)

    updated_event = (
        service.events()
        .update(calendarId=calendar_id, eventId=event_id, body=event)
        .execute()
    )

    return Response(result=Event(**updated_event))
