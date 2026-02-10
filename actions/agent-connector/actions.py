from pydantic import BaseModel, ConfigDict
from sema4ai.actions import (
    ActionError,
    Response,
    Secret,
    action,
)

from agent_api_client import _AgentAPIClient, Agent

class AgentResult(BaseModel):
    found: bool
    agent: Agent | None = None
    requested_name: str | None = None
    available_agent_names: list[str] | None = None
    suggested_name: str | None = None
    message: str | None = None

def find_closest_match(target: str, candidates: list[str], threshold: float = 0.6) -> str | None:
    """Find the closest matching string from a list of candidates.
    
    Args:
        target: The string to find a match for
        candidates: List of candidate strings
        threshold: Minimum similarity score (0-1) to consider a match
        
    Returns:
        The closest matching string or None if no match above threshold
    """
    if not candidates:
        return None
    
    target_lower = target.lower()
    best_match = None
    best_score = 0
    
    for candidate in candidates:
        candidate_lower = candidate.lower()
        
        # Exact match
        if target_lower == candidate_lower:
            return candidate
        
        # Check if target is contained in candidate or vice versa
        if target_lower in candidate_lower or candidate_lower in target_lower:
            score = min(len(target_lower), len(candidate_lower)) / max(len(target_lower), len(candidate_lower))
            if score > best_score:
                best_score = score
                best_match = candidate
        
        # Check for common prefix/suffix
        common_prefix = 0
        for i in range(min(len(target_lower), len(candidate_lower))):
            if target_lower[i] == candidate_lower[i]:
                common_prefix += 1
            else:
                break
        
        if common_prefix > 0:
            score = common_prefix / max(len(target_lower), len(candidate_lower))
            if score > best_score:
                best_score = score
                best_match = candidate
    
    return best_match if best_score >= threshold else None


def resolve_agent_by_name(client: _AgentAPIClient, agent_name: str) -> AgentResult:
    """Centralized function to resolve an agent by name and provide suggestions if not found.
    
    Args:
        client: The agent API client instance
        agent_name: The name of the agent to find
        
    Returns:
        AgentResult with found=True and agent populated if found, or found=False with suggestions if not found
    """
    # First, try to find the agent
    agent = client.get_agent_by_name(agent_name)
    if agent:
        return AgentResult(
            found=True,
            agent=agent
        )
    
    # Agent not found, get all agents to provide suggestions
    all_agents = client.get_all_agents()
    available_names = [agent.name for agent in all_agents]
    
    # Find the closest matching name
    suggested_name = find_closest_match(agent_name, available_names, threshold=0.6)
    
    return AgentResult(
        found=False,
        requested_name=agent_name,
        available_agent_names=available_names,
        suggested_name=suggested_name,
        message=f"Agent '{agent_name}' not found. Available agents: {', '.join(available_names)}"
    )

class Conversation(BaseModel):
    id: str
    name: str
    agent_id: str


class MessageResponse(BaseModel):
    conversation_id: str
    response: str
    agent_name: str


class WorkItemResponse(BaseModel):
    work_item: dict
    agent_name: str
    agent_id: str


class WorkItemPayload(BaseModel):
    """Payload for creating a work item. Accepts any additional properties."""

    model_config = ConfigDict(extra="allow")

@action
def ask_agent(
    agent_name: str, 
    message: str, 
    sema4_api_key: Secret,
    conversation_id: str | None = None,
    conversation_name: str | None = None
) -> Response[MessageResponse]:
    """The simplest way to ask an agent a question, by name. Creates a new conversation if conversation_id is not provided.

    Args:
        agent_name: The name of the agent to send message to
        message: The message content to send
        conversation_id: Optional conversation ID. If not provided, a new conversation will be created. Provide a conversation ID to send a message to an existing conversation for follow-up and to maintain context.
        conversation_name: Optional name for the new conversation (only used if conversation_id is not provided)
        sema4_api_key: The API key for the Sema4 API if running in cloud. Use LOCAL if in Studio or SDK!

    Returns:
        Response containing the conversation ID and agent's response
    """
    client = _AgentAPIClient(api_key=sema4_api_key.value)
    
    # First, find the agent by name
    agent_result = resolve_agent_by_name(client, agent_name)
    if not agent_result.found:
        raise ActionError(agent_result.message)
    
    agent = agent_result.agent
    
    # If no conversation_id provided, create a new conversation
    if not conversation_id:
        if not conversation_name:
            conversation_name = f"Conversation with {agent_name}"
        
        conversation = client.create_conversation(
            agent_id=agent.id,
            conversation_name=conversation_name
        )
        conversation_id = conversation.id
    
    # Send the message
    response = client.send_message(
        conversation_id=conversation_id,
        agent_id=agent.id,
        message=message,
    )
    
    return Response(result=MessageResponse(
        conversation_id=conversation_id,
        response=response,
        agent_name=agent_name
    ))

@action
def get_all_agents(sema4_api_key: Secret) -> Response[list[Agent]]:
    """Only use this to get a list of all available agents. If you're asking an agent by name, use ask_agent instead. Fetches a list of all available agents with their IDs and names.

    Args:
        sema4_api_key: The API key for the Sema4 API if running in cloud. Use LOCAL if in Studio or SDK!

    Returns:
        Response containing either a JSON string of agents or an error message
    """
    client = _AgentAPIClient(api_key=sema4_api_key.value)
    return Response(result=client.get_all_agents())


@action
def get_agent_by_name(name: str, sema4_api_key: Secret) -> Response[AgentResult]:
    """Only use this to resolve an agent by name. If you're asking an agent by name, use ask_agent instead. If the agent is not found, returns a result with available agent names and suggestions. 

    Args:
        name: The name of the agent
        sema4_api_key: The API key for the Sema4 API if running in cloud. Use LOCAL if in Studio or SDK!

    Returns:
        Response containing an AgentResult with either the found agent or suggestions for available agents
    """
    client = _AgentAPIClient(api_key=sema4_api_key.value)
    return Response(result=resolve_agent_by_name(client, name))


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


@action
def create_work_item_for_agent(
    agent_name: str,
    payload: WorkItemPayload,
    sema4_api_key: Secret,
    attachments: list[str] | None = None,
    work_item_api_url: str | None = None,
) -> Response[WorkItemResponse]:
    """Creates a Work Item for a specific agent by name.

    Args:
        agent_name: The name of the agent to run the Work Item
        payload: JSON payload to send as the Work Item payload (any properties allowed)
        sema4_api_key: The API key for the Sema4 API if running in cloud. Use LOCAL if in Studio or SDK!
        attachments: Optional list of file paths to attach to the Work Item
        work_item_api_url: Optional Work Item API URL override

    Returns:
        Response containing the created Work Item details
    """
    client = _AgentAPIClient(api_key=sema4_api_key.value)
    agent_result = resolve_agent_by_name(client, agent_name)
    if not agent_result.found:
        raise ActionError(agent_result.message)

    agent = agent_result.agent
    work_item = client.create_work_item(
        agent_id=agent.id,
        payload=payload.model_dump(exclude_none=True),
        attachments=attachments,
        work_item_api_url=work_item_api_url,
    )
    return Response(
        result=WorkItemResponse(
            work_item=work_item,
            agent_name=agent.name,
            agent_id=agent.id,
        )
    )
