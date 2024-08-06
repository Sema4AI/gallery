from typing import Literal

import requests
from sema4ai.actions import OAuth2Secret, Response, action

from models import Calendar, CreateEvent, Event, QueryParams, UpdateEvent


def _build_headers(token):
    return {
        "Authorization": f"Bearer {token.access_token}",
        "Content-Type": "application/json",
    }


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
    headers = _build_headers(credentials)

    url = "https://graph.microsoft.com/v1.0/me/calendar/events"
    if calendar_id:
        url = "https://graph.microsoft.com/v1.0/me/calendars/{id}/events"

    response = requests.post(
        url,
        headers=_build_headers(credentials),
        json=event.model_dump(mode="json", exclude_none=True, exclude={"timeZone"}),
    )

    if response.status_code != 201:
        return Response(error=response.text)

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
    response = requests.patch(
        f"https://graph.microsoft.com/v1.0/me/events/{event_id}",
        headers=_build_headers(credentials),
        json=updates.model_dump(mode="json", exclude_none=True, exclude={"timeZone"}),
    )

    if response.status_code != 200:
        return Response(error=response.text)

    return Response(result=Event.model_validate(response.json()))


@action(is_consequential=False)
def list_events(
    credentials: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Calendars.Read"]],
    ],
    query_params: QueryParams,
    calendar_id: str = "",
) -> Response[list[Event]]:
    """List all events in the user's calendar.

    To aggregate all events across calendars, call this method for each calendar returned by list_calendars endpoint.
    Ideally a start and end date should always be provided, otherwise we will look in the whole future or past.

    Args:
        credentials: JSON containing Microsoft OAuth2 credentials.
        query_params: JSON containing the following query parameters:
            - filter -> used to filter results based on different properties; details available at: https://learn.microsoft.com/en-us/graph/filter-query-parameter?tabs=http
            - search -> used to search after a particular string
        calendar_id: Calendar identifier which can be found by listing calendars action.
            Default value is using the user's default calendar.

    Returns:
        A list of calendar events that match the query, if defined.

    """
    url = "https://graph.microsoft.com/v1.0/me/calendar/events"
    if calendar_id:
        url = f"https://graph.microsoft.com/v1.0/me/calendars/{calendar_id}/events"

    response = requests.get(
        url,
        headers=_build_headers(credentials),
        params=query_params.model_dump(by_alias=True, exclude_none=True),
    )

    if response.status_code != 200:
        return Response(error=response.text)

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
        "https://graph.microsoft.com/v1.0/me/calendars",
        headers=_build_headers(credentials),
    )

    if response.status_code != 200:
        return Response(error=response.text)

    calendars = [
        Calendar.model_validate(calendar) for calendar in response.json()["value"]
    ]

    return Response(result=calendars)
