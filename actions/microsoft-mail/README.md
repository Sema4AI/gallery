# Microsoft Mail

Action package for interaction with Microsoft Mail.

Currently supporting:

- Listing emails in the user's mailbox matching a search query.
- Filtering emails by recipient information.
- Creating a draft email in the user's mailbox.
- Updating an existing draft email.
- Adding an attachment to an email.
- Sending a new email.
- Sending an existing draft email.
- Replying to an existing email.
- Forwarding an existing email.
- Moving an email to a different folder.
- Retrieving details of a specific email by ID.
- Listing all folders in the user's mailbox.
- Subscribing to notifications for new emails or other mailbox changes.
- Deleting all active subscriptions for notifications.
- Deleting a specific subscription by ID.
- Getting a list of active subscriptions.
- Retrieving details of a specific folder in the user's mailbox.
- Flagging emails in the user's mailbox.

## Prompt Examples

```
List emails I have received having mika@sema4.ai in cc list
```

> You have received the following email with "mika@sema4.ai" in the CC list:

> Subject: Microsoft Mail action package out soon
> From: Mika Hänninen (mika.hanninen@gmail.com)
> To: Mika Hänninen (mika@beissi.onmicrosoft.com)
> Received: 2024-09-18 at 09:49:46 UTC
> Body Preview: Hei Mikas check this one
> View Email (LINK)
>
> Let me know if you need anything else!

```
Create draft email for mika@sema4.ai, subject "Testing Microsoft Mail action package close to completion"
```

> The draft email has been created with the subject "Testing Microsoft Mail action package close to completion" for Mika at mika@sema4.ai.
>
> View Draft (LINK)

```
Change draft content to html and list all actions available in to the body of the and show me what that draft looks like
```

> The draft email has been updated with the complete list of 17 actions:
>
> Subject: Testing Microsoft Mail action package close to completion
>
> To: Mika (mika@sema4.ai)
>
> Body:
>
> <h2>Available Microsoft Mail Actions</h2>
> <ul>
>     <li>Create a draft message</li>
>     <li>Create and send a message</li>
>     <li>Add an attachment</li>
>     <li>Download an attachment</li>
>     <li>Send a draft</li>
>   .....
> </ul>

```
Send that draft
```

> The email has been sent successfully! If you need anything else, feel free to ask.

## Authorization

This package uses OAuth for user authenticaion. In Sema4.ai Studio you can either use the Sema4.ai provided public OAuth app credentials, or create your own client. In Control Room, you are expected to create the private client regardless.

### Creating a Microsoft Entra Enterprise app for authentication

In order to use the action package you need to go into https://portal.azure.com and register new Azure Entra ID (formerly Azure AD) application. Follow the detailed instructions [here](https://sema4.ai/docs/build-agents/prebuilt-actions/authentication/microsoft).

Scopes in use:

    - Mail.Read
    - Mail.ReadWrite
    - Mail.Send
    - User.Read
