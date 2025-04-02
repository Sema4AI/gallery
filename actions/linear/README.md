# Linear

Action package for interacting with Linear issues.

Actions available:

- create an issue
- search for issues
- add comment to an issue
- search for projects

## Prompts

```
Give me all open issues for Mika Hänninen
```

> 1. Linear action package
>
> Project: Gallery Action Packages
> Team: DevTools
> State: In Progress
> Description: Enable interaction with Linear issues.
>
> ...

```
For DevTools team create an issue "add more features to Linear action package" for "Gallery Action packages" project. Assign issue for Mika and add label "Feature" to the issue.
```

> Title: add more features to Linear action package
> Team: DevTools
> Assignee: Mika
> Project: Gallery Action packages
> Label: Feature
> Issue ID: DEV-1228
> URL: View Issue in Linear
> Let me know if there's anything else you need!

```
Show me all projects for DevTools team that were updated recently
```

> Searching for projects...
> 
> 1. Action Package Gallery
>    Team: DevTools
>    Updated: 2 days ago
>    Description: Collection of reusable action packages
>
> 2. Linear Integration
>    Team: DevTools
>    Updated: 5 days ago
>    Description: Linear API integration package
>
> Showing 2 most recently updated projects for DevTools team.

## Authentication

Supports at the moment personal API keys, which can be acquired from https://linear.app/sema4ai/settings/api.
