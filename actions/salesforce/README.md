# Salesforce

Action Package interacting with Salesforce resources.

Possible actions with this package are:

- query the Salesforce resources in an SQL like manner

## Prompts

```
What are the latest 3 contacts created?
```

> Here are the last 3 contacts created:
>
> 1. Rose Gonzalez - Created on 2024-10-24
> 2. Sean Forbes - Created on 2024-10-24
> 3. Jack Rogers - Created on 2024-10-24


```
What are the biggest 3 deals closed this month?
```

> Here are the biggest deals closed this month:
>
> 1. Grand Hotels Generator Installations - Amount: $350,000, Closed on 2024-10-03
> 2. Grand Hotels Emergency Generators - Amount: $210,000, Closed on 2024-10-01
> 3. United Oil SLA - Amount: $120,000, Closed on 2024-10-12

## Authorization

This action package uses OAuth2 client credentials flow to authenticate with Salesforce.

To authenticate with Salesforce, you need to create an external connected app in Salesforce and provide the following information:

- client_id (Consumer Key)
- client_secret (Consumer Secret)
- domain_url (e.g.  `https://robocorp-dev-ed.develop.my.salesforce.com`)

To create an external connected app in Salesforce, follow these steps:

1. Go to Apps -> App Manager and click on the `New Connected App` button.
2. Select `Create an External Client App`
3. Fill in the required fields and enable Oauth Settings.

Configure Oauth Settings:

1. Callback URL can be your domain salesforce domain url (e.g. `https://robocorp-dev-ed.develop.my.salesforce.com`).
2. Add `Manage user data via APIs (api)` scope.
3. Click on the `Flow Enablement` -> `Enable Client Credentials Flow` checkbox.
4. Uncheck the box `Require Proof Key for Code Exchange (PKCE) extension for Supported Authorization Flows`.
5. Click `Create`.
6. After creating the connected app, click on `Policies` -> `Edit` button, enable the `Enable Client Credentials Flow`, set the username you want to use and click `Save`.

To find the `client_id` and `client_secret` click on `Settings` tab -> `OAuth Settings` -> `Consumer Key and Secret`.

