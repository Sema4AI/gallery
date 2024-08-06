# Microsoft Calendar

Action Package interacting with Microsoft Calendar resources.

Possible actions with this package are:

- list the calendars on which the user is subscribed to
- query events from the user's calendar
- create a new event
- update an existing event

## Prompts

```
What is my schedule for tomorrow?
```

> Here is your schedule for tomorrow, August 7, 2024:
>  
> 1. DevTools Weekly
>    * Time: 08:00 - 08:30 (Local Time)
>    * Location: Microsoft Teams Meeting
>    * Details: Gather the main targets, blockers, and notes for the week. This is to keep the whole team in touch and working together.
>    * Join the Meeting: Join the meeting now
>    * Meeting ID: 345 708 543 419
>    * Passcode: mtKeLZ
>
> 2. CodeReview Reminder
>    * Time: 10:30 - 11:30 (Local Time)
>    * Details: Take time to do code reviews for all pending PRs.
> 
>If you need any further assistance or details, feel free to ask!

```
Create a new event for tomorrow at 12 PM with robert@company.com to have a catch-up discussion.
```

> The "Catch-up Discussion" event with Robert has been successfully created for tomorrow at 12 PM. If you need any further adjustments or have more tasks, feel free to let me know!

```
Update the Catch-up Discussion one hour later and invite albert@company.com as well.
```

> The "Catch-up Discussion" event has been successfully updated to start at 1 PM tomorrow and now includes an additional attendee, Albert from company.com. If there's anything else you need, just let me know!


## Authorization

This action package uses the OAuth2 flow to authenticate user.

Scopes in use:

    - Calendars.Read
    - Calendars.ReadWrite