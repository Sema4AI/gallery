---
# Robocorp Control Room

Action Package for managing Robocorp automations in Control Room via API.

Possible actions with this package are:

- listing available processes
- starting process runs
- checking process run status

## Prompts

```
List all available processes in my Robocorp Control Room workspace.
```

> Here are the available processes in your workspace:
> - Process 1 (ID: abc-123)
> - Process 2 (ID: def-456)
> - Process 3 (ID: ghi-789)

```
Start a process run for process ID abc-123 and then check its status.
```

> The process run has been started successfully. Run ID: xyz-789
> Current status: Running

## Authorization

This action package uses API key authentication to access the Robocorp Control Room API.

Credentials needed are:

    - API key (RC-WSKEY)
    - Workspace ID

These can be provided either through:
- Secret objects in the action calls from AI Agent
- Environment variables (`API_KEY` and `WORKSPACE_ID`) for local testing
