import json

from sema4ai.actions import action, Response, ActionError
from agent_api_client import AgentAPIClient

# Create a single client instance
client = AgentAPIClient()


@action
def get_all_agents() -> Response[str]:
    """Fetches a list of all available agents with their IDs and names.

    Returns:
        Response containing either a JSON string of agents or an error message
    """
    response = client.request("agents/")
    agents = response.json()
    result = [{"agent_id": agent["id"], "name": agent["name"]} for agent in agents]
    return Response(result=json.dumps(result))


@action
def get_agent_by_name(name: str) -> Response[str]:
    """Fetches an agent by name.

    Args:
        name: The name of the agent

    Returns:
        Response containing either the agent ID or an error message
    """
    response = client.request("agents/")
    agents = response.json()
    for agent in agents:
        if agent["name"] == name:
            return Response(result=agent["id"])
    raise ActionError(f"No agent found with name '{name}'")


@action
def get_threads(agent_id: str) -> Response[str]:
    """Fetches all threads for an agent.

    Args:
        agent_id: The ID of the agent

    Returns:
        Response containing either a JSON string of threads or an error message
    """
    response = client.request("threads/")
    threads = response.json()
    result = []
    for thread in threads:
        if thread["agent_id"] == agent_id:
            result.append({"thread_id": thread["thread_id"], "name": thread["name"]})
    return Response(result=json.dumps(result))


@action
def get_thread(agent_name: str, thread_name: str) -> Response[str]:
    """Fetches a thread for an agent.

    Args:
        agent_name: The name of the agent
        thread_name: The name of the thread

    Returns:
        Response containing either the thread ID or an error message
    """
    agent_result = get_agent_by_name(agent_name)
    if agent_result.error:
        raise ActionError(agent_result.error)

    response = client.request("threads/")
    threads = response.json()
    for thread in threads:
        if thread["agent_id"] == agent_result.result and thread["name"] == thread_name:
            return Response(result=thread["thread_id"])
    raise ActionError(
        f"No thread found for agent '{agent_name}' with name '{thread_name}'"
    )


@action
def create_thread(agent_id: str, thread_name: str) -> Response[str]:
    """Creates a new thread for communication with an agent.

    Args:
        agent_id: The id of the agent to create thread in
        thread_name: The name of the thread to be created

    Returns:
        Response containing either the thread ID or an error message
    """
    response = client.request(
        "threads",
        method="POST",
        json_data={"name": thread_name, "agent_id": agent_id},
    )
    result = response.json()
    return Response(result=result["thread_id"])


@action
def send_message(thread_id: str, message: str) -> Response[str]:
    """Sends a message within a thread and retrieves the agent's response.

    Args:
        thread_id: The thread ID obtained from create_thread
        message: The message content

    Returns:
        Response containing either the agent's response or an error message
    """
    response = client.request(
        "runs/stream",
        method="POST",
        json_data={
            "thread_id": thread_id,
            "input": [
                {
                    "content": message,
                    "type": "human",
                    "example": False,
                },
            ],
        },
    )

    collected_data = []
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode("utf-8")
            if decoded_line.startswith("data: "):
                collected_data.append(decoded_line[6:])

    if not collected_data:
        raise ActionError("No response data received")

    last_response = json.loads(collected_data[-1])
    return Response(result=last_response[-1]["content"])
