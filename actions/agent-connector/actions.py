from pydantic import BaseModel
from sema4ai.actions import (
    ActionError,
    Response,
    Secret,
    action,
)
import difflib

from agent_api_client import _AgentAPIClient, Agent

class AgentResult(BaseModel):
    found: bool
    agent: Agent | None = None
    requested_name: str | None = None
    available_agent_names: list[str] | None = None
    suggested_name: str | None = None
    message: str | None = None

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
def get_agent_by_name(name: str, sema4_api_key: Secret) -> Response[AgentResult]:
    """Fetches an agent by name. If the agent is not found, returns a result with available agent names and suggestions.

    Args:
        name: The name of the agent
        sema4_api_key: The API key for the Sema4 API if running in cloud. Use LOCAL if in Studio or SDK!

    Returns:
        Response containing an AgentResult with either the found agent or suggestions for available agents
    """
    client = _AgentAPIClient(api_key=sema4_api_key.value)
    agent = client.get_agent_by_name(name)
    
    if agent:
        return Response(result=AgentResult(
            found=True,
            agent=agent
        ))
    
    # Agent not found, get all agents to provide suggestions
    all_agents = client.get_all_agents()
    available_names = [agent.name for agent in all_agents]
    
    # Find the closest matching name
    suggested_name = None
    if available_names:
        # Use difflib to find the closest match
        matches = difflib.get_close_matches(name, available_names, n=1, cutoff=0.6)
        suggested_name = matches[0] if matches else None
    
    result = AgentResult(
        found=False,
        requested_name=name,
        available_agent_names=available_names,
        suggested_name=suggested_name,
        message=f"Agent '{name}' not found. Available agents: {', '.join(available_names)}"
    )
    
    return Response(result=result)


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
