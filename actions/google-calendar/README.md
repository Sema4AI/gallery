# Google Calendar

Action Package interacting with Google Calendar resources.

Possible actions with this package are:

- list the calendars on which the user is subscribed to
- query events from the user's calendar
- create a new event
- update an existing event

## Prompts

```
Give me all the events from this friday.
```

> Here are the events from friday:
> 
> 1. Home
>    * Start: June 19, 2024
>    * End: June 20, 2024
> 2. #coffee-time Donut
>    * Start: June 19, 2024, 12:00 PM
>    * End: June 19, 2024, 12:30 PM
>    * Attendees:
>        * Kari (kari@robocorp.com) - Organizer
>        * Ovidiu (ovidiu@robocorp.com)
> 3. DevTools Sync
>    * Location: Zoom Meeting
>    * Start: June 19, 2024, 1:30 PM
>    * End: June 19, 2024, 2:00 PM
>    * Description: Sync meeting for DevTools. Topics are raised in #dev-tools-team channel.
>    * Attendees:
>      * Kari, Matti, Mika, Jippo, Cosmin, Cpopa, Fabio, Ovidiu, Vlad, Michal
>      
> Let me know if you need more details or any other assistance!

```
Create a new event for tomorrow at 12 PM with vlad@sema4.ai to have a catch-up discussion.
```

> The "Catch-up Discussion" event with Vlad has been successfully created for tomorrow at 12 PM. If you need any further adjustments or have more tasks, feel free to let me know!

```
Update the Catch-up Discussion one hour later and invite cosmin@robocorp.com as well.
```

> The "Catch-up Discussion" event has been successfully updated to start at 1 PM tomorrow and now includes an additional attendee, Cosmin from robocorp.com. If there's anything else you need, just let me know!


## Authorization

This action package uses Google OAuth2 flow to authenticate user.

Scopes in use:

    - https://www.googleapis.com/auth/calendar.events
    - https://www.googleapis.com/auth/calendar.readonly