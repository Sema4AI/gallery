import json
import urllib.parse
from urllib.parse import urlparse

from agent_api_client import AgentAPIClient
from sema4ai.actions import ActionError, Response, Secret, action

# Create a client instance for each function call with the API key


@action
def get_all_agents(sema4_api_key: Secret) -> Response[str]:
    """Fetches a list of all available agents with their IDs and names.

    Args:
        sema4_api_key: The API key for the Sema4 API if running in cloud. Use LOCAL if in Studio or SDK!

    Returns:
        Response containing either a JSON string of agents or an error message
    """
    # Initialize client with API key if provided
    client = AgentAPIClient(api_key=sema4_api_key.value if sema4_api_key.value != "LOCAL" else None)
    
    # Handle environment-specific behavior - properly distinguish HTTP vs HTTPS
    endpoint = "agents"
    if client.api_url:
        parsed_url = urlparse(client.api_url)
        # Check if scheme is exactly "http" (not "https")
        if parsed_url.scheme == "http":
            endpoint = "agents/"
            print("Using local endpoint format (with trailing slash)")
        else:
            print("Using cloud endpoint format (no trailing slash)")
    
    full_url = f"{client.api_url}/{endpoint}"
    print(f"API Call URL (get_all_agents): {full_url}")
    
    try:
        # Handle pagination to get all agents
        all_agents = []
        next_token = None
        
        while True:
            # Construct endpoint with pagination token if available
            paginated_endpoint = endpoint
            if next_token:
                paginated_endpoint = f"{endpoint}?next={next_token}"
                print(f"API Call URL (get_all_agents pagination): {client.api_url}/{paginated_endpoint}")
            
            response = client.request(paginated_endpoint)
            response_json = response.json()
            
            # Extract agents - handle both direct list and dictionary with 'data' field
            if isinstance(response_json, dict) and 'data' in response_json:
                # Response is in the format described in the docs
                agents = response_json['data']
                next_token = response_json.get('next')
                has_more = response_json.get('has_more', False)
            else:
                # Response is a direct list of agents
                agents = response_json
                next_token = None
                has_more = False
                
            all_agents.extend(agents)
            
            # Check if there are more pages
            if not next_token or not has_more:
                break
        
        result = [{"agent_id": agent["id"], "name": agent["name"]} for agent in all_agents]
        return Response(result=json.dumps(result))
    except Exception as e:
        # Try to extract error message from response if possible
        error_message = "Error fetching agents"
        
        # Check if there's a response with error details
        if hasattr(e, 'response') and e.response:
            try:
                error_data = e.response.json()
                if isinstance(error_data, dict) and 'error' in error_data:
                    if isinstance(error_data['error'], dict) and 'message' in error_data['error']:
                        error_message = error_data['error']['message']
                    else:
                        error_message = str(error_data['error'])
            except:
                # If we can't parse JSON, use the status code
                if hasattr(e.response, 'status_code'):
                    error_message = f"HTTP {e.response.status_code}: {e.response.reason}"

        print(f"Error in get_all_agents: {str(e)}")
        print(f"Final error message: {error_message}")
        raise ActionError(error_message)


@action
def get_agent_by_name(name: str, sema4_api_key: Secret) -> Response[str]:
    """Fetches an agent by name.

    Args:
        name: The name of the agent
        sema4_api_key: The API key for the Sema4 API if running in cloud. Use LOCAL if in Studio or SDK!

    Returns:
        Response containing either the agent ID or an error message
    """
    # Initialize client with API key if provided
    client = AgentAPIClient(api_key=sema4_api_key.value if sema4_api_key.value != "LOCAL" else None)
    
    # Handle environment-specific behavior - properly distinguish HTTP vs HTTPS
    endpoint = "agents"
    if client.api_url:
        parsed_url = urlparse(client.api_url)
        # Check if scheme is exactly "http" (not "https")
        if parsed_url.scheme == "http":
            endpoint = "agents/"
            print("Using local endpoint format (with trailing slash)")
        else:
            print("Using cloud endpoint format (no trailing slash)")
    
    full_url = f"{client.api_url}/{endpoint}"
    print(f"API Call URL (get_agent_by_name): {full_url}")
    
    try:
        # Handle pagination to get all agents
        next_token = None
        
        while True:
            # Construct endpoint with pagination token if available
            paginated_endpoint = endpoint
            if next_token:
                paginated_endpoint = f"{endpoint}?next={next_token}"
                print(f"API Call URL (get_agent_by_name pagination): {client.api_url}/{paginated_endpoint}")
            
            response = client.request(paginated_endpoint)
            response_json = response.json()
            
            # Extract agents - handle both direct list and dictionary with 'data' field
            if isinstance(response_json, dict) and 'data' in response_json:
                # Response is in the format described in the docs
                agents = response_json['data']
                next_token = response_json.get('next')
                has_more = response_json.get('has_more', False)
            else:
                # Response is a direct list of agents
                agents = response_json
                next_token = None
                has_more = False
            
            # Look for the agent with the matching name
            for agent in agents:
                if agent["name"] == name:
                    return Response(result=agent["id"])
            
            # Check if there are more pages
            if not next_token or not has_more:
                break
        
        # If we get here, we didn't find the agent in any page
        raise ActionError(f"No agent found with name '{name}'")
    except ActionError as e:
        raise e
    except Exception as e:
        # Try to extract error message from response if possible
        error_message = "Error fetching agents"
        
        # Check if there's a response with error details
        if hasattr(e, 'response') and e.response:
            try:
                error_data = e.response.json()
                if isinstance(error_data, dict) and 'error' in error_data:
                    if isinstance(error_data['error'], dict) and 'message' in error_data['error']:
                        error_message = error_data['error']['message']
                    else:
                        error_message = str(error_data['error'])
            except:
                # If we can't parse JSON, use the status code
                if hasattr(e.response, 'status_code'):
                    error_message = f"HTTP {e.response.status_code}: {e.response.reason}"

        print(f"Error in get_agent_by_name: {str(e)}")
        print(f"Final error message: {error_message}")
        raise ActionError(error_message)


@action
def get_conversations(agent_id: str, sema4_api_key: Secret) -> Response[str]:
    """Fetches all conversations for an agent.

    Args:
        agent_id: The ID of the agent
        sema4_api_key: The API key for the Sema4 API if running in cloud. Use LOCAL if in Studio or SDK!

    Returns:
        Response containing either a JSON string of conversations or an error message
    """
    # Initialize client with API key if provided
    client = AgentAPIClient(api_key=sema4_api_key.value if sema4_api_key.value != "LOCAL" else None)
    
    endpoint = f"agents/{agent_id}/conversations"
    
    full_url = f"{client.api_url}/{endpoint}"
    print(f"API Call URL (get_conversations): {full_url}")
    
    try:
        # Handle pagination to get all conversations
        all_conversations = []
        next_token = None
        
        while True:
            # Construct endpoint with pagination token if available
            paginated_endpoint = endpoint
            if next_token:
                paginated_endpoint = f"{endpoint}?next={next_token}"
                print(f"API Call URL (get_conversations pagination): {client.api_url}/{paginated_endpoint}")
            
            response = client.request(paginated_endpoint)
            response_json = response.json()
            
            # Extract conversations - handle both direct list and dictionary with 'data' field
            if isinstance(response_json, dict) and 'data' in response_json:
                # Response is in the format described in the docs
                conversations = response_json['data']
                next_token = response_json.get('next')
                has_more = response_json.get('has_more', False)
            else:
                # Response is a direct list of conversations
                conversations = response_json
                next_token = None
                has_more = False
                
            all_conversations.extend(conversations)
            
            # Check if there are more pages
            if not next_token or not has_more:
                break
            
        result = []
        for conversation in all_conversations:
            result.append({
                "conversation_id": conversation["id"], 
                "name": conversation["name"]
            })
        return Response(result=json.dumps(result))
    except Exception as e:
        # Try to extract error message from response if possible
        error_message = f"Error fetching conversations for agent '{agent_id}'"
        
        # Check if there's a response with error details
        if hasattr(e, 'response') and e.response:
            try:
                error_data = e.response.json()
                if isinstance(error_data, dict) and 'error' in error_data:
                    if isinstance(error_data['error'], dict) and 'message' in error_data['error']:
                        error_message = error_data['error']['message']
                    else:
                        error_message = str(error_data['error'])
            except:
                # If we can't parse JSON, use the status code
                if hasattr(e.response, 'status_code'):
                    status_code = e.response.status_code
                    if status_code == 404:
                        error_message = f"Agent with ID '{agent_id}' not found"
                    else:
                        error_message = f"HTTP {status_code}: {e.response.reason if hasattr(e.response, 'reason') else 'Unknown'}"

        print(f"Error in get_conversations: {str(e)}")
        print(f"Final error message: {error_message}")
        raise ActionError(error_message)


@action
def get_conversation(agent_name: str, conversation_name: str, sema4_api_key: Secret) -> Response[str]:
    """Fetches a conversation for an agent.

    Args:
        agent_name: The name of the agent
        conversation_name: The name of the conversation
        sema4_api_key: The API key for the Sema4 API if running in cloud. Use LOCAL if in Studio or SDK!

    Returns:
        Response containing either the conversation ID or an error message
    """
    try:
        # Initialize client with API key if provided
        client = AgentAPIClient(api_key=sema4_api_key.value if sema4_api_key.value != "LOCAL" else None)
        
        agent_result = get_agent_by_name(agent_name, sema4_api_key)
        if agent_result.error:
            raise ActionError(agent_result.error)
        
        agent_id = agent_result.result
        endpoint = f"agents/{agent_id}/conversations"
        
        full_url = f"{client.api_url}/{endpoint}"
        print(f"API Call URL (get_conversation): {full_url}")
        
        try:
            # Handle pagination to find the conversation
            next_token = None
            
            while True:
                # Construct endpoint with pagination token if available
                paginated_endpoint = endpoint
                if next_token:
                    paginated_endpoint = f"{endpoint}?next={next_token}"
                    print(f"API Call URL (get_conversation pagination): {client.api_url}/{paginated_endpoint}")
                
                response = client.request(paginated_endpoint)
                response_json = response.json()
                
                # Extract conversations - handle both direct list and dictionary with 'data' field
                if isinstance(response_json, dict) and 'data' in response_json:
                    # Response is in the format described in the docs
                    conversations = response_json['data']
                    next_token = response_json.get('next')
                    has_more = response_json.get('has_more', False)
                else:
                    # Response is a direct list of conversations
                    conversations = response_json
                    next_token = None
                    has_more = False
                
                # Look for the conversation with the matching name
                for conversation in conversations:
                    if conversation["name"] == conversation_name:
                        return Response(result=conversation["id"])
                
                # Check if there are more pages
                if not next_token or not has_more:
                    break
            
            # If we get here, we didn't find the conversation in any page
            raise ActionError(
                f"No conversation found for agent '{agent_name}' with name '{conversation_name}'"
            )
        except ActionError as e:
            raise e
        except Exception as e:
            # Try to extract error message from response if possible
            error_message = f"Error fetching conversations for agent '{agent_name}'"
            
            # Check if there's a response with error details
            if hasattr(e, 'response') and e.response:
                try:
                    error_data = e.response.json()
                    if isinstance(error_data, dict) and 'error' in error_data:
                        if isinstance(error_data['error'], dict) and 'message' in error_data['error']:
                            error_message = error_data['error']['message']
                        else:
                            error_message = str(error_data['error'])
                except:
                    # If we can't parse JSON, use the status code
                    if hasattr(e.response, 'status_code'):
                        status_code = e.response.status_code
                        if status_code == 404:
                            error_message = f"Agent with ID '{agent_id}' not found"
                        else:
                            error_message = f"HTTP {status_code}: {e.response.reason if hasattr(e.response, 'reason') else 'Unknown'}"

            print(f"Error in get_conversation: {str(e)}")
            print(f"Final error message: {error_message}")
            raise ActionError(error_message)
    except ActionError as e:
        raise e
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(error_msg)
        raise ActionError(error_msg)


@action
def get_conversation_messages(agent_id: str, conversation_id: str, sema4_api_key: Secret) -> Response[str]:
    """Fetches all messages from a specific conversation.

    Args:
        agent_id: The ID of the agent
        conversation_id: The ID of the conversation
        sema4_api_key: The API key for the Sema4 API if running in cloud. Use LOCAL if in Studio or SDK!

    Returns:
        Response containing either a JSON string of the conversation with messages or an error message
    """
    # Initialize client with API key if provided
    client = AgentAPIClient(api_key=sema4_api_key.value if sema4_api_key.value != "LOCAL" else None)
    
    endpoint = f"agents/{agent_id}/conversations/{conversation_id}/messages"
    
    full_url = f"{client.api_url}/{endpoint}"
    print(f"API Call URL (get_conversation_messages): {full_url}")
    
    try:
        # Handle pagination to get all messages
        all_messages = []
        next_token = None
        
        while True:
            # Construct endpoint with pagination token if available
            paginated_endpoint = endpoint
            if next_token:
                paginated_endpoint = f"{endpoint}?next={next_token}"
                print(f"API Call URL (get_conversation_messages pagination): {client.api_url}/{paginated_endpoint}")
            
            response = client.request(paginated_endpoint)
            response_json = response.json()
            
            # Extract messages - handle both direct list and dictionary with 'data' field
            if isinstance(response_json, dict) and 'data' in response_json:
                # Response is in the format described in the docs
                messages = response_json['data']
                next_token = response_json.get('next')
                has_more = response_json.get('has_more', False)
            else:
                # Response is a direct list or conversation object with messages
                if 'messages' in response_json:
                    # The API returned a conversation object with messages included
                    return Response(result=json.dumps(response_json))
                else:
                    messages = response_json
                    next_token = None
                    has_more = False
                
            all_messages.extend(messages)
            
            # Check if there are more pages
            if not next_token or not has_more:
                break
        
        # If we collected messages separately, construct a conversation object
        result = {
            "id": conversation_id,
            "agent_id": agent_id,
            "messages": all_messages
        }
        
        return Response(result=json.dumps(result))
    except Exception as e:
        # Try to extract error message from response if possible
        error_message = f"Error fetching messages for conversation '{conversation_id}'"
        
        # Check if there's a response with error details
        if hasattr(e, 'response') and e.response:
            try:
                error_data = e.response.json()
                if isinstance(error_data, dict) and 'error' in error_data:
                    if isinstance(error_data['error'], dict) and 'message' in error_data['error']:
                        error_message = error_data['error']['message']
                    else:
                        error_message = str(error_data['error'])
            except:
                # If we can't parse JSON, use the status code
                if hasattr(e.response, 'status_code'):
                    status_code = e.response.status_code
                    if status_code == 404:
                        error_message = f"Conversation with ID '{conversation_id}' not found"
                    else:
                        error_message = f"HTTP {status_code}: {e.response.reason if hasattr(e.response, 'reason') else 'Unknown'}"

        print(f"Error in get_conversation_messages: {str(e)}")
        print(f"Final error message: {error_message}")
        raise ActionError(error_message)


@action
def create_conversation(agent_id: str, conversation_name: str, sema4_api_key: Secret) -> Response[str]:
    """Creates a new conversation for communication with an agent.

    Args:
        agent_id: The id of the agent to create conversation with
        conversation_name: The name of the conversation to be created
        sema4_api_key: The API key for the Sema4 API if running in cloud. Use LOCAL if in Studio or SDK!

    Returns:
        Response containing either the conversation ID or an error message
    """
    # Initialize client with API key if provided
    client = AgentAPIClient(api_key=sema4_api_key.value if sema4_api_key.value != "LOCAL" else None)
    
    endpoint = f"agents/{agent_id}/conversations"
    
    full_url = f"{client.api_url}/{endpoint}"
    print(f"API Call URL (create_conversation): {full_url}")
    
    try:
        response = client.request(
            endpoint,
            method="POST",
            json_data={"name": conversation_name},
        )
        response_json = response.json()
        
        print(f"Create conversation response: {response_json}")
        
        # Extract conversation ID directly from the response
        # The response is a direct conversation object, not wrapped in a 'data' field
        conversation_id = response_json["id"]
        
        # Return just the ID to maintain backward compatibility
        return Response(result=conversation_id)
    except Exception as e:
        # Try to extract error message from response if possible
        error_message = f"Error creating conversation for agent '{agent_id}'"
        
        # Check if there's a response with error details
        if hasattr(e, 'response') and e.response:
            try:
                error_data = e.response.json()
                if isinstance(error_data, dict) and 'error' in error_data:
                    if isinstance(error_data['error'], dict) and 'message' in error_data['error']:
                        error_message = error_data['error']['message']
                    else:
                        error_message = str(error_data['error'])
            except:
                # If we can't parse JSON, use the status code
                if hasattr(e.response, 'status_code'):
                    status_code = e.response.status_code
                    if status_code == 404:
                        error_message = f"Agent with ID '{agent_id}' not found"
                    else:
                        error_message = f"HTTP {status_code}: {e.response.reason if hasattr(e.response, 'reason') else 'Unknown'}"

        print(f"Error in create_conversation: {str(e)}")
        print(f"Final error message: {error_message}")
        raise ActionError(error_message)


@action
def send_message(conversation_id: str, agent_id: str, message: str, sema4_api_key: Secret) -> Response[str]:
    """Sends a message within a conversation and retrieves the agent's response.

    Args:
        conversation_id: The ID of the conversation
        agent_id: The ID of the agent to send message to
        message: The message content to send
        sema4_api_key: The API key for the Sema4 API if running in cloud. Use LOCAL if in Studio or SDK!

    Returns:
        Response containing either the agent's response or an error message
    """
    # Initialize client with API key if provided
    client = AgentAPIClient(api_key=sema4_api_key.value if sema4_api_key.value != "LOCAL" else None)
    
    try:
        # Handle case where conversation_id contains full path information
        conversation_id_only = conversation_id
        if '/' in conversation_id:
            parts = conversation_id.split('/')
            # Check if this is in the format agents/{agent_id}/conversations/{conversation_id}
            if len(parts) >= 4 and "conversations" in parts:
                conv_index = parts.index("conversations") + 1
                if conv_index < len(parts):
                    conversation_id_only = parts[conv_index]
                    print(f"Extracted conversation_id: {conversation_id_only} from path")
                else:
                    # Invalid path format
                    raise ActionError(f"Invalid path format in conversation ID: {conversation_id}")
            else:
                # Simple format like "abc/def"
                conversation_id_only = parts[-1]  # Just take the last part
                print(f"Using last path segment as conversation_id: {conversation_id_only}")
        
        # Construct the endpoint with the provided agent_id and extracted conversation_id
        endpoint = f"agents/{agent_id}/conversations/{conversation_id_only}/messages"
        
        full_url = f"{client.api_url}/{endpoint}"
        print(f"API Call URL (send_message): {full_url}")
        
        try:
            response = client.request(
                endpoint,
                method="POST",
                json_data={"content": message},
            )

            # Parse the response from the synchronous endpoint
            response_json = response.json()
            print(f"Response from send_message: {response_json}")
            
            # Handle different response formats:
            # 1. Wrapped in 'data' field: {"data": [...messages...]}
            # 2. Direct list of messages: [...messages...]
            # 3. Single message response: {"id": "...", "content": "..."}
            # 4. Full conversation object: {"id": "...", "messages": [...messages...]}
            
            messages = []
            
            if isinstance(response_json, dict):
                if 'data' in response_json:
                    messages = response_json['data']
                elif 'messages' in response_json:
                    # This is a full conversation object with messages
                    messages = response_json['messages']
                elif 'content' in response_json:
                    # Single message response
                    return Response(result=response_json.get("content", ""))
            elif isinstance(response_json, list):
                messages = response_json
            
            print(f"Extracted messages: {messages}")
            
            # The response should contain the messages, with the last one being the agent's response
            if messages:
                # Find the last message from the agent
                for msg in reversed(messages):
                    if msg.get("role") == "agent":
                        agent_response = msg.get("content", "")
                        print(f"Found agent response: {agent_response}")
                        return Response(result=json.dumps(agent_response))
                
                # If no agent message found, return the last message content
                if isinstance(messages[-1], dict) and "content" in messages[-1]:
                    last_message = messages[-1]["content"]
                    print(f"No agent response found, returning last message: {last_message}")
                    return Response(result=json.dumps(last_message))
                
                raise ActionError("No agent response found in conversation messages")
            else:
                print("No messages found in API response")
                if isinstance(response_json, dict):
                    # If it's a different format than expected, return the raw response
                    return Response(result=json.dumps(response_json))
                raise ActionError("No messages returned from the API")
        except Exception as e:
            # Handle errors when sending messages
            error_message = f"Error sending message to conversation {conversation_id_only}"
            if hasattr(e, 'response') and e.response:
                try:
                    error_data = e.response.json()
                    print(f"Error response when sending message: {error_data}")
                    if isinstance(error_data, dict) and 'error' in error_data:
                        if isinstance(error_data['error'], dict) and 'message' in error_data['error']:
                            error_message = error_data['error']['message']
                        else:
                            error_message = str(error_data['error'])
                except:
                    # If we can't parse JSON, use the status code
                    if hasattr(e.response, 'status_code'):
                        status_code = e.response.status_code
                        print(f"HTTP Status Code: {status_code}")
                        if status_code == 404:
                            error_message = f"Conversation {conversation_id_only} or agent {agent_id} not found"
                        else:
                            error_message = f"HTTP {status_code}: {e.response.reason if hasattr(e.response, 'reason') else 'Unknown'}"
            
            print(f"Error in send_message: {str(e)}")
            print(f"Final error message: {error_message}")
            raise ActionError(f"{error_message}: {str(e)}")
    except ActionError as e:
        raise e
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(error_msg)
        raise ActionError(error_msg)
