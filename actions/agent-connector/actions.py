from pydantic import BaseModel
from sema4ai.actions import (
    ActionError,
    Response,
    Secret,
    action,
)

from agent_api_client import _AgentAPIClient


class Agent(BaseModel):
    id: str
    name: str
    description: str | None = None
    mode: str | None = None


class Conversation(BaseModel):
    id: str
    name: str
    agent_id: str


# Create a client instance for each function call with the API key


@action
def get_all_agents(sema4_api_key: Secret) -> Response[list[Agent]]:
    """Fetches a list of all available agents with their IDs and names.

    Args:
        sema4_api_key: The API key for the Sema4 API if running in cloud. Use LOCAL if in Studio or SDK!

    Returns:
        Response containing either a JSON string of agents or an error message
    """
    client = _AgentAPIClient(api_key=sema4_api_key.value)
    return Response(result=client.get_all_agents())


@action
def get_agent_by_name(name: str, sema4_api_key: Secret) -> Response[Agent]:
    """Fetches an agent by name.

    Args:
        name: The name of the agent
        sema4_api_key: The API key for the Sema4 API if running in cloud. Use LOCAL if in Studio or SDK!

    Returns:
        Response containing either the agent ID or an error message
    """
    client = _AgentAPIClient(api_key=sema4_api_key.value)
    return Response(result=client.get_agent_by_name(name))


@action
def get_conversations(
    agent_id: str, sema4_api_key: Secret
) -> Response[list[Conversation]]:
    """Fetches all conversations for an agent.

    Args:
        agent_id: The ID of the agent
        sema4_api_key: The API key for the Sema4 API if running in cloud. Use LOCAL if in Studio or SDK!

    Returns:
        Response containing either a JSON string of conversations or an error message
    """
    client = _AgentAPIClient(api_key=sema4_api_key.value)
    return Response(result=client.get_conversations(agent_id))


@action
def get_conversation(
    agent_name: str, conversation_name: str, sema4_api_key: Secret
) -> Response[Conversation]:
    """Fetches a conversation for an agent.

    Args:
        agent_name: The name of the agent
        conversation_name: The name of the conversation
        sema4_api_key: The API key for the Sema4 API if running in cloud. Use LOCAL if in Studio or SDK!

    Returns:
        Response containing either the conversation ID or an error message
    """
    client = _AgentAPIClient(api_key=sema4_api_key.value)
    conversation = client.get_conversation(
        agent_name=agent_name, conversation_name=conversation_name
    )
    if not conversation:
        raise ActionError(
            f"Conversation '{conversation_name}' for agent '{agent_name}' not found"
        )

    return Response(result=conversation)


@action
def get_conversation_messages(
    agent_id: str, conversation_id: str, sema4_api_key: Secret
) -> Response[list]:
    """Fetches all messages from a specific conversation.

    Args:
        agent_id: The ID of the agent
        conversation_id: The ID of the conversation
        sema4_api_key: The API key for the Sema4 API if running in cloud. Use LOCAL if in Studio or SDK!

    Returns:
        Response containing either a JSON string of the conversation with messages or an error message
    """
    client = _AgentAPIClient(api_key=sema4_api_key.value)
    messages = client.get_conversation_messages(
        agent_id=agent_id, conversation_id=conversation_id
    )

    return Response(result=messages)


@action
def create_conversation(
    agent_id: str, conversation_name: str, sema4_api_key: Secret
) -> Response[Conversation]:
    """Creates a new conversation for communication with an agent.

    Args:
        agent_id: The id of the agent to create conversation with
        conversation_name: The name of the conversation to be created
        sema4_api_key: The API key for the Sema4 API if running in cloud. Use LOCAL if in Studio or SDK!

    Returns:
        The created conversation object.
    """
    client = _AgentAPIClient(api_key=sema4_api_key.value)
    return Response(
        result=client.create_conversation(
            agent_id=agent_id, conversation_name=conversation_name
        )
    )


@action
def send_message(
    conversation_id: str, agent_id: str, message: str, sema4_api_key: Secret
) -> Response[str]:
    """Sends a message within a conversation and retrieves the agent's response.

    Args:
        conversation_id: The ID of the conversation
        agent_id: The ID of the agent to send message to
        message: The message content to send
        sema4_api_key: The API key for the Sema4 API if running in cloud. Use LOCAL if in Studio or SDK!

    Returns:
        Response containing either the agent's response or an error message
    """
    client = _AgentAPIClient(api_key=sema4_api_key.value)
    response = client.send_message(
        conversation_id=conversation_id,
        agent_id=agent_id,
        message=message,
    )

    return Response(result=response)
