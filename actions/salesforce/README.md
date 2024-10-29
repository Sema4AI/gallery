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

This action package uses OAuth2 flow to authenticate user.

Scopes in use:

    - api
    - refresh_token
