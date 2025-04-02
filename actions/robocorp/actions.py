
from sema4ai.actions import Response, Secret, action

from support import make_get_request, make_post_request, get_credentials

BASE_URL = "https://cloud.robocorp.com/api/v1/workspaces"


@action
def list_processes(api_key: Secret, workspace_id: Secret) -> Response[dict]:
    """
    List the Control Room processes including names and ID's.

    Args:
        api_key: The API key for authentication.
        workspace_id: The workspace ID to query.

    Returns:
        Result of the operation
    """
    api_key_value, ws_id = get_credentials(api_key, workspace_id)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"RC-WSKEY {api_key_value}",
    }

    url = f"{BASE_URL}/{ws_id}/processes"
    return make_get_request(url, headers)


@action
def start_process_run(
    api_key: Secret, workspace_id: Secret, process_id: str
) -> Response[dict]:
    """
    Start a process run based on the process ID which you can get from list_processes.

    Args:
        api_key: The API key for authentication.
        workspace_id: The workspace ID to query.
        process_id: The ID of the process to run.

    Returns:
        Response[dict]: Result of the operation including the ID that you can check the status with get_process_run
    """
    api_key_value, ws_id = get_credentials(api_key, workspace_id)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"RC-WSKEY {api_key_value}",
    }

    url = f"{BASE_URL}/{ws_id}/processes/{process_id}/process-runs"
    return make_post_request(url, headers)


@action
def get_process_run(
    api_key: Secret, workspace_id: Secret, process_run_id: str
) -> Response[dict]:
    """
    Get details for a specific process run.

    Args:
        api_key: The API key for authentication.
        workspace_id: The workspace ID to query.
        process_run_id: The ID of the process run to retrieve, can be found e.g. from the start_process_run action

    Returns:
        Response[dict]: The details of the specified process run.
    """
    api_key_value, ws_id = get_credentials(api_key, workspace_id)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"RC-WSKEY {api_key_value}",
    }

    url = f"{BASE_URL}/{ws_id}/process-runs/{process_run_id}"

    return make_get_request(url, headers)
