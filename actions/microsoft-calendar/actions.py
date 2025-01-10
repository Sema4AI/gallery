from typing import Literal

import requests
from sema4ai.actions import OAuth2Secret, Response, action

from models import Calendar, CreateEvent, Event, QueryParams, UpdateEvent

BASE_URL = "https://graph.microsoft.com/v1.0/me"
EVENTS_ENDPOINT = f"{BASE_URL}/calendar/events"
CALENDARS_ENDPOINT = f"{BASE_URL}/calendars"
MAILBOX_ENDPOINT = f"{BASE_URL}/mailboxSettings/timeZone"


def _build_headers(token, timezone=None):
    headers = {
        "Authorization": f"Bearer {token.access_token}",
        "Content-Type": "application/json",
    }

    if timezone:
        headers["Prefer"] = f'outlook.timezone="{timezone}"'

    return headers


@action(is_consequential=True)
def create_event(
    credentials: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Calendars.ReadWrite"]],
    ],
    event: CreateEvent,
    calendar_id: str = "",
) -> Response[Event]:
    """Creates a new event in the user's calendar.

    Args:
        credentials: JSON containing Microsoft OAuth2 credentials.
        event: JSON representation of the Microsoft Calendar event.
        calendar_id: Calendar identifier where to add the event which can be found by listing calendars action.
            Default value is using the user's default calendar.

    Returns:
        The newly created event.
    """
    url = EVENTS_ENDPOINT
    if calendar_id:
        url = f"{CALENDARS_ENDPOINT}/{calendar_id}/events"

    response = requests.post(
        url,
        headers=_build_headers(credentials),
        json=event.model_dump(mode="json", exclude_none=True, exclude={"timeZone"}),
    )

    response.raise_for_status()

    return Response(result=Event.model_validate(response.json()))


@action(is_consequential=True)
def update_event(
    credentials: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Calendars.ReadWrite"]],
    ],
    event_id: str,
    updates: UpdateEvent,
) -> Response[Event]:
    """Update an existing Microsoft Calendar event.

    Args:
        credentials: JSON containing Microsoft OAuth2 credentials.
        event_id: Identifier of the event to update. Can be found by listing events in all calendars.
        updates: A dictionary containing the event attributes to update.

    Returns:
        Updated event details.
    """
    headers = _build_headers(credentials)
    updates_json = updates.model_dump(
        mode="json", exclude_none=True, exclude={"timeZone"}
    )

    # We add the new attendees to the existing ones, so we don't override them
    if "attendees" in updates_json:
        response = requests.get(f"{BASE_URL}/events/{event_id}", headers=headers)
        response.raise_for_status()

        current_event = Event.model_validate(response.json())
        attendees = [
            attendee.model_dump(mode="json") for attendee in current_event.attendees
        ]

        updates_json["attendees"] = updates_json["attendees"] + attendees

    response = requests.patch(
        f"{BASE_URL}/events/{event_id}",
        headers=headers,
        json=updates_json,
    )

    response.raise_for_status()

    return Response(result=Event.model_validate(response.json()))


@action(is_consequential=False)
def list_events(
    credentials: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Calendars.Read"]],
    ],
    query_params: QueryParams,
    timezone: str,
    calendar_id: str = "",
) -> Response[list[Event]]:
    """List all events in the user's calendar.

    To aggregate all events across calendars, call this method for each calendar returned by list_calendars endpoint.
    Ideally a start and end date should always be provided, otherwise we will look in the whole future or past.

    Args:
        credentials: JSON containing Microsoft OAuth2 credentials.
        query_params: JSON containing the following query parameters:
            - filter -> used to filter results based on different properties
                Details available at: https://learn.microsoft.com/en-us/graph/filter-query-parameter?tabs=http.
                Usage example: "start/dateTime ge '2024-08-07T00:00:00Z' and start/dateTime lt '2024-08-07T23:59:59Z'".
            - search -> used to search after a particular string
        timezone: By default, it should match the value returned by the get_mailbox_timezone action unless specified
            otherwise by the user. Queries and event dates will use the timezone specified.
        calendar_id: Calendar identifier which can be found by listing calendars action.
            Default value is using the user's default calendar.

    Returns:
        A list of calendar events that match the query, if defined.

    """
    url = EVENTS_ENDPOINT
    if calendar_id:
        url = f"{CALENDARS_ENDPOINT}/{calendar_id}/events"

    response = requests.get(
        url,
        headers=_build_headers(credentials, timezone=timezone),
        params=query_params.model_dump(by_alias=True, exclude_none=True),
    )

    response.raise_for_status()

    events = [Event.model_validate(event) for event in response.json()["value"]]

    return Response(result=events)


@action(is_consequential=False)
def list_calendars(
    credentials: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Calendars.Read"]],
    ],
) -> Response[list[Calendar]]:
    """List all calendars that the user is subscribed to.

    Args:
        credentials: JSON containing Microsoft OAuth2 credentials.

    Returns:
        A list of calendars.

    """
    response = requests.get(
        CALENDARS_ENDPOINT,
        headers=_build_headers(credentials),
    )

    response.raise_for_status()

    calendars = [
        Calendar.model_validate(calendar) for calendar in response.json()["value"]
    ]

    return Response(result=calendars)


@action(is_consequential=False)
def get_mailbox_timezone(
    credentials: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["MailboxSettings.Read"]],
    ],
) -> Response[str]:
    """Returns the user's mailbox timezone.

    This timezone should be used in all subsequent actions where a timezone is required.

    Args:
        credentials: JSON containing Microsoft OAuth2 credentials.

    Returns:
        User's mailbox timezone.
    """
    response = requests.get(
        MAILBOX_ENDPOINT,
        headers=_build_headers(credentials),
    )

    response.raise_for_status()

    return Response(result=response.json()["value"])
