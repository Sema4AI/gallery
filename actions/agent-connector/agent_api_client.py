import json
import os
import platform
from copy import copy
from urllib.parse import urljoin, urlparse

import sema4ai_http
from pydantic import BaseModel


class Agent(BaseModel):
    id: str
    name: str
    description: str | None = None
    mode: str | None = None


class Conversation(BaseModel):
    id: str
    name: str
    agent_id: str


class AgentApiClientException(Exception):
    """Exception raised when the Agent API client encounters an error."""


class _AgentAPIClient:
    PID_FILE_NAME = "agent-server.pid"

    def __init__(self, api_key: str | None = None):
        """Initialize the AgentServerClient."""
        self.api_key = api_key if api_key != "LOCAL" else None
        self.api_url = self._get_api_url()
        self.is_v2 = "v2" in self.api_url

        print(f"API URL: {self.api_url}")

    def _get_api_url(self) -> str:
        """Determine the correct API URL by checking environment variable or agent-server.pid file
        and testing API availability.

        Returns:
            str: The working API URL

        Raises:
            AgentApiClientException: If no API server is responding
        """
        # Try to get URL from environment variable first
        api_url = self._try_get_url_from_environment()
        if api_url:
            return api_url

        # Try to get URL from PID file as fallback
        api_url = self._try_get_url_from_pid_file()
        if api_url:
            return api_url

        # No working API server found
        raise AgentApiClientException("Could not connect to agent server")

    def _try_get_url_from_environment(self) -> str | None:
        env_url = os.getenv("SEMA4AI_API_V1_URL")
        if not env_url:
            return None

        return self._test_api_endpoints(env_url)

    def _try_get_url_from_pid_file(self) -> str | None:
        pid_file_path = self._get_pid_file_path()
        print(f"Looking for agent server in PID file: {pid_file_path}")

        try:
            if not os.path.exists(pid_file_path):
                return None

            with open(pid_file_path, "r") as f:
                server_info = json.loads(f.read())
                base_url = server_info.get("base_url")
                if base_url:
                    for version in ["v1", "v2"]:
                        endpoint_url = f"{base_url}/api/public/{version}"
                        return self._test_api_endpoints(endpoint_url)
                else:
                    return None
        except Exception as e:
            print(f"Failed to read PID file: {e}")
            return None

    def _test_api_endpoints(self, base_url: str) -> str | None:
        """Test different API endpoint versions to find a working one.

        Args:
            base_url: Base URL to test

        Returns:
            str | None: Working API URL if found, None otherwise
        """
        test_endpoint = f"{base_url}/agents"
        if "v2" in base_url:
            test_endpoint += "/"

        if self._is_url_accessible(test_endpoint):
            return base_url
        return None

    def _is_url_accessible(self, url: str) -> bool:
        try:
            parsed_url = urlparse(url)
            if parsed_url.scheme not in ("http", "https"):
                return False

            headers = (
                {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None
            )
            print(f"Testing URL: {url}")
            sema4ai_http.get(url, headers=headers, timeout=1).raise_for_status()
            return True
        except Exception as e:
            print(f"Error testing URL: {e}")
            return False

    def _get_pid_file_path(self) -> str:
        """Get the path to the agent-server.pid file based on the operating system.

        Returns:
            str: Path to the PID file
        """
        # Determine OS-specific path
        if platform.system() == "Windows":
            # Windows path: C:\Users\<username>\AppData\Local\sema4ai\sema4ai-studio\agent-server.pid
            local_app_data = os.environ.get("LOCALAPPDATA")
            if not local_app_data:
                # Fallback to default Windows AppData path
                local_app_data = os.path.join(
                    os.path.expanduser("~"), "AppData", "Local"
                )

            return os.path.join(
                local_app_data,
                "sema4ai",
                "sema4ai-studio",
                self.PID_FILE_NAME,
            )
        else:
            # macOS/Linux path: ~/.sema4ai/sema4ai-studio/agent-server.pid
            return os.path.join(
                os.path.expanduser("~"),
                ".sema4ai",
                "sema4ai-studio",
                self.PID_FILE_NAME,
            )

    def request(
        self,
        path: str,
        method="GET",
        json_data: dict | None = None,
        headers: dict | None = None,
    ) -> sema4ai_http.ResponseWrapper:
        """Make an API request with common error handling.

        Args:
            path: API endpoint path
            method: HTTP method (GET, POST, or DELETE)
            json_data: Optional JSON payload for POST requests
            headers: Optional additional headers

        Returns:
            sema4ai_http.ResponseWrapper object

        Raises:
           ValueError: for unsupported HTTP methods
           AgentApiClientException: for HTTP errors
           ConnectionError: If the request fails
        """
        url = self.api_url
        if not url.endswith("/"):
            url += "/"
        url = urljoin(url, path)

        # NOTE: We only do this for backwards compatibility with the old API (only for local endpoint).
        # The new endpoint is actually V1.
        parsed_url = urlparse(self.api_url)
        if self.is_v2 and parsed_url.scheme == "http" and not url.endswith("/"):
            url += "/"

        request_headers = copy(headers) if headers else {}

        if self.api_key:
            request_headers["Authorization"] = f"Bearer {self.api_key}"

        if method == "GET":
            response = sema4ai_http.get(url, json=json_data, headers=request_headers)
        elif method == "POST":
            response = sema4ai_http.post(url, json=json_data, headers=request_headers)
        elif method == "DELETE":
            response = sema4ai_http.delete(url, headers=request_headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        if response.status_code not in (200, 201):
            error_msg = f"HTTP {response.status_code}"
            if response.text:
                error_msg += f": {response.text}"
            else:
                error_msg += f": {response.reason or 'Unknown error'}"

            raise AgentApiClientException(error_msg)

        return response

    def _get_all_pages(self, endpoint: str) -> list:
        all_data = []
        next_token = None

        while True:
            paginated_endpoint = endpoint
            if next_token:
                paginated_endpoint = f"{endpoint}?next={next_token}"

            response = self.request(paginated_endpoint)
            response_json = response.json()

            all_data.extend(
                response_json.get("data", response_json.get("messages", []))
            )
            if not response_json.get("next"):
                break

            next_token = response_json.get("next")

        return all_data

    def _get_conversations(self, endpoint: str) -> list[Conversation]:
        full_url = urljoin(self.api_url, endpoint)
        print(f"Agent Server API Call URL: {full_url}")

        return [
            Conversation.model_validate(conversation)
            for conversation in self._get_all_pages(endpoint)
        ]

    def _get_agents(self, endpoint: str) -> list[Agent]:
        full_url = urljoin(self.api_url, endpoint)
        print(f"Agent Server API Call URL: {full_url}")

        all_agents = self._get_all_pages(endpoint)
        return [Agent.model_validate(agent) for agent in all_agents]

    def get_all_agents(self) -> list[Agent]:
        return self._get_agents("agents")

    def get_agent_by_name(self, name: str) -> Agent | None:
        agents = self._get_agents("agents")
        return next((agent for agent in agents if agent.name == name), None)

    def get_conversations(self, agent_id: str) -> list[Conversation]:
        return self._get_conversations(f"agents/{agent_id}/conversations")

    def get_conversation(
        self, agent_name: str, conversation_name: str
    ) -> Conversation | None:
        agent_result = self.get_agent_by_name(agent_name)
        if not agent_result:
            raise AgentApiClientException(f"No agent found with name '{agent_name}'")

        agent_id = agent_result.id
        conversations = self.get_conversations(agent_id)

        return next(
            (
                conversation
                for conversation in conversations
                if conversation_name == conversation.name
            ),
            None,
        )

    def get_conversation_messages(
        self, agent_id: str, conversation_id: str
    ) -> list[dict]:
        endpoint = f"agents/{agent_id}/conversations/{conversation_id}/messages"
        full_url = urljoin(self.api_url, endpoint)
        print(f"Agent Server API Call URL: {full_url}")

        return self._get_all_pages(endpoint)

    def create_conversation(
        self, agent_id: str, conversation_name: str
    ) -> Conversation:
        endpoint = f"agents/{agent_id}/conversations"
        full_url = urljoin(self.api_url, endpoint)
        print(f"Agent Server API Call URL: {full_url}")

        response = self.request(
            endpoint,
            method="POST",
            json_data={"name": conversation_name},
        )

        return Conversation.model_validate(response.json())

    def send_message(self, conversation_id: str, agent_id: str, message: str) -> str:
        # Handle case where conversation_id contains full path information
        conversation_id_only = conversation_id
        if "/" in conversation_id:
            parts = conversation_id.split("/")
            # Check if this is in the format agents/{agent_id}/conversations/{conversation_id}
            if len(parts) >= 4 and "conversations" in parts:
                conv_index = parts.index("conversations") + 1
                if conv_index < len(parts):
                    conversation_id_only = parts[conv_index]
                    print(
                        f"Extracted conversation_id: {conversation_id_only} from path"
                    )
                else:
                    # Invalid path format
                    raise AgentApiClientException(
                        f"Invalid path format in conversation ID: {conversation_id}"
                    )
            else:
                # Simple format like "abc/def"
                conversation_id_only = parts[-1]  # Just take the last part
                print(
                    f"Using last path segment as conversation_id: {conversation_id_only}"
                )

        # Construct the endpoint with the provided agent_id and extracted conversation_id
        endpoint = f"agents/{agent_id}/conversations/{conversation_id_only}/messages"

        full_url = urljoin(self.api_url, endpoint)
        print(f"Agent Server API Call URL: {full_url}")
        response = self.request(
            endpoint,
            method="POST",
            json_data={"content": message},
        )

        response_json = response.json()
        print(f"Response from send_message: {response_json}")

        # Handle different response formats:
        # 1. Wrapped in 'data' field: {"data": [...messages...]}
        # 2. Direct list of messages: [...messages...]
        # 3. Single message response: {"id": "...", "content": "..."}
        # 4. Full conversation object: {"id": "...", "messages": [...messages...]}
        messages = []
        if isinstance(response_json, dict):
            if "data" in response_json:
                messages = response_json["data"]
            elif "messages" in response_json:
                # This is a full conversation object with messages
                messages = response_json["messages"]
            elif "content" in response_json:
                # Single message response
                return json.dumps(response_json.get("content", ""))
        elif isinstance(response_json, list):
            messages = response_json

        if messages:
            for msg in reversed(messages):
                if msg.get("role") == "agent":
                    agent_response = msg.get("content", "")
                    print(f"Found agent response: {agent_response}")
                    return json.dumps(agent_response)

            # If no agent message found, return the last message content
            if isinstance(messages[-1], dict) and "content" in messages[-1]:
                last_message = messages[-1]["content"]
                print(
                    f"No agent response found, returning last message: {last_message}"
                )
                return json.dumps(last_message)

            raise AgentApiClientException(
                "No agent response found in conversation messages"
            )

        return json.dumps(response_json)
