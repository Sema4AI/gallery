import json
from sema4ai.actions import action
from agent_api_client import AgentAPIClient

# Create a single client instance
client = AgentAPIClient()


@action
def get_all_agents() -> str:
    """Fetches a list of all available agents with their IDs and names.

    Returns:
        A json of the list of dictionaries with agent IDs and names, or an error message if the request fails.
    """
    response = client.request("agents/")
    if isinstance(response, str):  # Error message
        return response

    agents = response.json()
    result = [{"agent_id": agent["id"], "name": agent["name"]} for agent in agents]
    return json.dumps(result)


@action
def get_agent_by_name(name: str) -> str:
    """Fetches an agent by name.

    Args:
        name: The name of the agent

    Returns:
        A string with the agent ID and name or error message.
    """
    response = client.request("agents/")  # Get all agents instead of trying direct path
    if isinstance(response, str):  # Error message
        return response

    agents = response.json()
    for agent in agents:
        if agent["name"] == name:
            return agent["id"]
    return f"Error fetching agent: No agent with name '{name}'"


@action
def get_threads(agent_id: str) -> str:
    """Fetches all threads for an agent.

    Args:
        agent_id: The ID of the agent

    Returns:
        A json string with the List of threads or error message.
    """
    response = client.request("threads/")  # Get all threads and filter
    if isinstance(response, str):  # Error message
        return response

    threads = response.json()
    result = []
    for thread in threads:
        if thread["agent_id"] == agent_id:
            result.append({"thread_id": thread["thread_id"], "name": thread["name"]})
    return json.dumps(result)


@action
def get_thread(agent_name: str, thread_name: str) -> str:
    """Fetches a thread for an agent.

    Args:
        agent_name: The name of the agent
        thread_name: The name of the thread

    Returns:
        The thread ID or error message.
    """
    # First get the agent_id
    agent_id = get_agent_by_name(agent_name)
    if agent_id.startswith("Error"):  # Error message
        return agent_id

    # Then get all threads and filter
    response = client.request("threads/")
    if isinstance(response, str):  # Error message
        return response

    threads = response.json()
    for thread in threads:
        if thread["agent_id"] == agent_id and thread["name"] == thread_name:
            return thread["thread_id"]
    return f"Error: No thread found for agent '{agent_name}' with name '{thread_name}'"


@action
def create_thread(agent_id: str, thread_name: str) -> str:
    """Creates a new thread for communication with an agent.

    Note: Agent names are pre-defined and must match existing agent names.

    Args:
        agent_id: The id of the agent to create thread in. Use tools get_all_agents or get_agent_by_name to get the id of an agent based on it's name.
        thread_name: The name of the thread  to be created (user-defined).

    Returns:
        The thread ID, or error message if the call fails.
    """
    response = client.request(
        "threads",  # Ensure trailing slash in the path
        method="POST",
        json_data={"name": thread_name, "agent_id": agent_id},
    )
    if isinstance(response, str):  # Error message
        return response

    return response.json()["thread_id"]


@action
def send_message(thread_id: str, message: str) -> str:
    """Sends a message within a thread and retrieves the agent's response.

    Note: The thread ID must be obtained from a successful call to `create_thread`.

    Args:
        thread_id: The thread ID obtained from `create_thread`.
        message: The message content.

    Returns:
        The agent's response, or error message if the call fails.
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

    if isinstance(response, str):  # Error message
        return response

    collected_data = []

    for line in response.iter_lines():
        if line:
            decoded_line = line.decode("utf-8")
            if decoded_line.startswith("data: "):
                collected_data.append(decoded_line[6:])

    last_response = json.loads(collected_data[-1])
    return last_response[-1]["content"]
