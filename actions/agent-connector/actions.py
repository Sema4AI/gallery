import json
from sema4ai.actions import action
import requests

API_URL = "http://localhost:8100"


def _get_all_agents():
    """Fetches a list of all available agents with their IDs and names.

    Returns:
        list or str: A list of dictionaries with assistant IDs and names,
                     or an error message if the request fails.
    """
    url = f"{API_URL}/assistants/"
    response = requests.get(url)
    if response.status_code == 200:
        assistants = response.json()
        return [{"assistant_id": assistant["assistant_id"], "name": assistant["name"]} for assistant in assistants]
    else:
        return f"Error fetching agents: {response.status_code} {response.text}"


@action
def create_test_agent(agent_name: str, action_server_url: str) -> str:
    """Creates a test agent with the given parameters.

    Args:
        agent_name (str): The name of the agent.
        action_server_url (str): The URL of the action server.

    Returns:
        str: The created agent ID, or error message if the call fails.
    """
    system_message = f"You are an assistant with the following name: {agent_name}.\nThe current date and time is: {{CURRENT_DATETIME}}.\nYour instructions are to follow users instructions."
    url = f"{API_URL}/assistants"
    payload = {
        "name": agent_name,
        "config": {
            "configurable": {
                "type": "agent",
                "type==agent/agent_type": "GPT 4o",
                "type==agent/interrupt_before_action": False,
                "type==agent/retrieval_description": "Can be used to look up information that was uploaded to this assistant.\nIf the user is referencing particular files, that is often a good hint that information may be here.\nIf the user asks a vague question, they are likely meaning to look up info from this retriever, and you should call it!",
                "type==agent/system_message": system_message,
                "type==agent/description": "Default description for the agent",
                "type==agent/tools": [
                    {
                        "type": "action_server_by_sema4ai",
                        "name": "Action Server by Sema4.ai",
                        "description": "Run AI actions with [Sema4.ai Action Server](https://github.com/Sema4AI/actions).",
                        "config": {
                            "url": action_server_url,
                            "api_key": "APIKEY",
                            "isBundled": "false",
                        }
                    }
                ]
            }
        }
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json()["assistant_id"]
    else:
        return f"Error creating agent: {response.status_code} {response.text}"


@action
def create_thread(agent_name: str, thread_name: str) -> str:
    """Creates a new thread for communication with an agent.

    Note: Agent names are pre-defined and must match existing agent names.

    Args:
        agent_name (str): The name of the pre-defined agent.
        thread_name (str): The name of the thread (user-defined).

    Returns:
        str: The thread ID, or error message if the call fails.
    """
    agents = _get_all_agents()
    if isinstance(agents, str):
        return agents

    assistant = next((agent for agent in agents if agent["name"] == agent_name), None)
    if assistant is None:
        available_agents = ", ".join(agent["name"] for agent in agents)
        return f"No agent found with name '{agent_name}'. Available agents: {available_agents}"

    assistant_id = assistant["assistant_id"]
    url = f"{API_URL}/threads"
    payload = {
        "name": thread_name,
        "assistant_id": assistant_id
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json()["thread_id"]
    else:
        return f"Error creating thread: {response.status_code} {response.text}"


@action
def send_message(thread_id: str, message: str) -> str:
    """Sends a message within a thread and retrieves the agent's response.

    Note: The thread ID must be obtained from a successful call to `create_thread`.

    Args:
        thread_id (str): The thread ID obtained from `create_thread`.
        message (str): The message content.

    Returns:
        str: The agent's response, or error message if the call fails.
    """
    url = f"{API_URL}/runs/stream"
    payload = {
        "thread_id": thread_id,
        "input": [
            {
                "content": message,
                "type": 'human',
                "example": False,
            },
        ]
    }
    response = requests.post(url, json=payload, stream=True)

    if response.status_code != 200:
        return f"Error sending message: {response.status_code} {response.text}"

    collected_data = []

    for line in response.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            if decoded_line.startswith("data: "):
                collected_data.append(decoded_line[6:])

    last_response = json.loads(collected_data[-1])
    return last_response[-1]["content"]
