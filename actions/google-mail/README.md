# Google Mail

Action Package interacting with Google Mail (GMail) resources.

Possible actions with this package are:

- send email (to, subject and body fields)

## Prompts

```
Send email to mika.hanninen@gmail.com and robocorp.tester.2@gmail.com, subject "process these files" and
body "message content sent from the Sema4Desktop v0.0.26"
```

> The email has been successfully sent to mika.hanninen@gmail.com and robocorp.tester.2@gmail.com with the
> subject "process these files" and the specified body content. If there's anything else you need, let me know!

## Authorization

This action package uses Google OAuth2 flow to authenticate user.

Scopes in use:

    - https://www.googleapis.com/auth/gmail.send
