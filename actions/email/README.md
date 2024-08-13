# Email sending

Action Package for sending email using any SMTP service.

Possible actions with this package are:

- sending email

## Prompts

```
Send email from sema4.tester@gmail.com to johndoe@domain.com. Body of the email should contain list of Sharepoint sites
and subject would be "testing email action".
```

> The email has been sent successfully with the list of your SharePoint sites. If you need any further assistance, feel free to ask!

## Authorization

This action package uses SMTP authentication to login into SMTP server.

Credentials needed are:

    - the hostname of the SMTP server
    - the port number of the SMTP server (commonly 587)
    - the user account name
    - the password for the account (could be a app password if possible)
