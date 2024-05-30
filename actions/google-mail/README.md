# Google Mail

Action Package interacting with Google Mail (GMail) resources.

Details on GMail query syntax: https://support.google.com/mail/answer/7190?hl=en

Possible actions with this package are:

- send email (to, subject, body, cc and bcc fields)
- search for emails
- get email content
- move email (identifying an e-mail and moving it into a folder, including trash (delete))
- create draft
- update draft
- list drafts
- send draft

If the email contains attachment "invite.ics" then don't show that attachment (and don't list attachments at all if that was the only one), and lastly tag email to be about "MEETING" (and that into end of subject line with bold letters).

## Prompts

```
Send email to x@y.com and y@x.com, subject "process these files" and
body "message content sent from the Sema4Desktop v0.0.26"
```

> The email has been successfully sent to x@y.com and y@x.com with the
> subject "process these files" and the specified body content. If there's anything else you
> need, let me know!

```
How many emails I have from ReleaseNotes ?
```

> You have received 7 emails from "ReleaseNotes." If you need more details about these emails or any
> other assistance, feel free to ask!

```
Move all of them to trash.
```

> All emails from "ReleaseNotes" have been moved to the trash. If there's anything else you need, just let me know!

```
Send email to recipient@domain.com, I finally got rid of those pesky ReleaseNotes emails. Add into the email body
the subject and dates of those emails. Include also the count of how many emails were moved.
```

> The email has been sent to recipient@domain.com, summarizing the details of the ReleaseNotes emails that
> were moved to the trash, including their subjects, dates, and the total count. If you need further assistance,
> feel free to ask!

## Authorization

This action package uses Google OAuth2 flow to authenticate user.

Scopes in use:

    - https://www.googleapis.com/auth/gmail.send
    - https://www.googleapis.com/auth/gmail.readonly
    - https://www.googleapis.com/auth/gmail.modify
