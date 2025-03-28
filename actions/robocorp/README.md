# Robocorp Control Room Actions

Actions for interacting with Robocorp autoamtions in Control Room via API.

## Available Actions

### list_processes
Lists all available processes in your Control Room workspace.

### start_process_run
Starts a process run using the process ID (which you can get from list_processes).

### get_process_run
Gets the details of a specific process run (use the run ID returned by start_process_run).

## Authentication
All actions require API key and workspace ID which can be provided either through:
- Secret objects in the action calls from AI Agent
- Environment variables (`API_KEY` and `WORKSPACE_ID`) for local testing. 
