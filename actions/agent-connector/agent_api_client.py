import json
import mimetypes
import os
import platform
from copy import copy
from urllib.parse import urljoin, urlparse

import sema4ai_http
from sema4ai.actions import chat
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

    def _request_with_base_url(
        self,
        base_url: str,
        path: str,
        method="GET",
        json_data: dict | None = None,
        headers: dict | None = None,
        success_codes: tuple[int, ...] = (200, 201, 204),
    ) -> sema4ai_http.ResponseWrapper:
        """Make a request to an explicit base URL (used for Work Item API)."""
        if not base_url.endswith("/"):
            base_url += "/"
        url = urljoin(base_url, path)

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

        if response.status_code not in success_codes:
            error_msg = f"HTTP {response.status_code}"
            if response.text:
                error_msg += f": {response.text}"
            else:
                error_msg += f": {response.reason or 'Unknown error'}"

            raise AgentApiClientException(error_msg)

        return response

    def _get_work_item_fallback_url(self, work_item_api_url: str) -> str | None:
        if "/api/v2/" in work_item_api_url:
            return work_item_api_url.replace("/api/v2/", "/api/v1/", 1)
        return None

    def _request_work_item_api(
        self,
        base_url: str,
        path: str,
        method="GET",
        json_data: dict | None = None,
        headers: dict | None = None,
        success_codes: tuple[int, ...] = (200, 201, 204),
    ) -> tuple[sema4ai_http.ResponseWrapper, str]:
        fallback_url = self._get_work_item_fallback_url(base_url)
        try:
            return (
                self._request_with_base_url(
                    base_url,
                    path,
                    method=method,
                    json_data=json_data,
                    headers=headers,
                    success_codes=success_codes,
                ),
                base_url,
            )
        except AgentApiClientException as exc:
            if fallback_url and "HTTP 404" in str(exc):
                response = self._request_with_base_url(
                    fallback_url,
                    path,
                    method=method,
                    json_data=json_data,
                    headers=headers,
                    success_codes=success_codes,
                )
                print(f"Work Item API URL fallback to: {fallback_url}")
                return response, fallback_url
            raise

    def _post_work_item_upload(
        self, base_url: str, fields: dict, headers: dict | None
    ) -> tuple[sema4ai_http.ResponseWrapper, str]:
        fallback_url = self._get_work_item_fallback_url(base_url)
        upload_url = urljoin(base_url.rstrip("/") + "/", "upload-file")
        response = sema4ai_http.post(upload_url, headers=headers, fields=fields)
        if response.status_code == 404 and fallback_url:
            fallback_upload_url = urljoin(
                fallback_url.rstrip("/") + "/", "upload-file"
            )
            response = sema4ai_http.post(
                fallback_upload_url, headers=headers, fields=fields
            )
            print(f"Work Item API URL fallback to: {fallback_url}")
            return response, fallback_url
        return response, base_url

    def _get_work_item_api_url(self) -> str:
        """Resolve the Work Item API base URL.

        Priority:
        1) SEMA4AI_WORK_ITEM_API_URL (supports endpoint URL or /api/v1[/work-items])
        2) Derive from the Agent API URL (replace /api/public/v1 -> /api/v1)
        """
        env_url = os.getenv("SEMA4AI_WORK_ITEM_API_URL")
        if env_url:
            return self._normalize_work_item_url(env_url)

        derived_url = self._derive_work_item_url_from_agent_api(self.api_url)
        if derived_url:
            return derived_url

        raise AgentApiClientException(
            "Work Item API URL not configured. Set SEMA4AI_WORK_ITEM_API_URL."
        )

    def _normalize_work_item_url(self, url: str) -> str:
        normalized = url.rstrip("/")
        if "/work-items" in normalized:
            return normalized
        if normalized.endswith("/api/v1") or normalized.endswith("/api/v2"):
            return f"{normalized}/work-items"
        if "/api/v1/" in normalized or "/api/v2/" in normalized:
            if "/api/v2/" in normalized:
                base = normalized.split("/api/v2")[0] + "/api/v2"
            else:
                base = normalized.split("/api/v1")[0] + "/api/v1"
            return f"{base}/work-items"
        return f"{normalized}/api/v2/work-items"

    def _derive_work_item_url_from_agent_api(self, agent_api_url: str) -> str | None:
        normalized = agent_api_url.rstrip("/")
        if "/api/public/" in normalized:
            normalized = normalized.replace("/api/public/", "/api/")
        if normalized.endswith("/v2"):
            return f"{normalized}/work-items"
        if normalized.endswith("/work-items"):
            return normalized
        if normalized.endswith("/api/v1"):
            base = normalized.rsplit("/api/v1", 1)[0]
            return f"{base}/api/v2/work-items"
        if normalized.endswith("/api/v2"):
            return f"{normalized}/work-items"
        if "/api/v2/" in normalized:
            base = normalized.split("/api/v2")[0] + "/api/v2"
            return f"{base}/work-items"
        if "/api/v1/" in normalized:
            base = normalized.split("/api/v1")[0] + "/api/v2"
            return f"{base}/work-items"
        if "/api/" not in normalized:
            return f"{normalized}/api/v2/work-items"
        return None

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

    def _upload_work_item_file(
        self,
        file_path: str,
        work_item_api_url: str,
        work_item_id: str | None = None,
    ) -> tuple[str, str]:
        filename = os.path.basename(file_path)
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        request_headers = (
            {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None
        )

        if os.path.exists(file_path):
            with open(file_path, "rb") as file_handle:
                file_bytes = file_handle.read()
        else:
            try:
                # Try resolving relative/basename from chat file store.
                file_bytes = chat.get_file_content(filename)
            except Exception as exc:
                raise AgentApiClientException(
                    f"Attachment not found locally or in chat files: {file_path}"
                ) from exc

        fields = {"file": (filename, file_bytes, content_type)}
        if work_item_id:
            fields["work_item_id"] = work_item_id
        upload_response, effective_base_url = self._post_work_item_upload(
            work_item_api_url, fields, request_headers
        )

        if upload_response.status_code not in (200, 201):
            error_msg = f"HTTP {upload_response.status_code}"
            if upload_response.text:
                error_msg += f": {upload_response.text}"
            else:
                error_msg += f": {upload_response.reason or 'Unknown error'}"
            raise AgentApiClientException(error_msg)

        upload_info = upload_response.json()
        work_item_id = upload_info.get("work_item_id") or upload_info.get("id")
        if not work_item_id:
            raise AgentApiClientException(
                f"Work item ID missing from upload response: {upload_info}"
            )

        upload_url = upload_info.get("upload_url")
        upload_form_data = upload_info.get("upload_form_data") or {}
        file_id = upload_info.get("file_id")
        file_ref = upload_info.get("file_ref") or filename

        if upload_url:
            fields = dict(upload_form_data)
            fields["file"] = (filename, file_bytes, content_type)
            remote_upload = sema4ai_http.post(upload_url, fields=fields)

            if remote_upload.status_code not in (200, 201, 204):
                error_msg = f"HTTP {remote_upload.status_code}"
                if remote_upload.text:
                    error_msg += f": {remote_upload.text}"
                else:
                    error_msg += f": {remote_upload.reason or 'Unknown error'}"
                raise AgentApiClientException(error_msg)

            if file_id:
                self._request_work_item_api(
                    effective_base_url,
                    f"{work_item_id}/confirm-file",
                    method="POST",
                    json_data={"file_ref": file_ref, "file_id": file_id},
                    success_codes=(200, 201, 204),
                )

        return work_item_id, effective_base_url

    def create_work_item(
        self,
        agent_id: str,
        payload: dict,
        attachments: list[str] | None = None,
        work_item_api_url: str | None = None,
    ) -> dict:
        if work_item_api_url:
            work_item_api_url = self._normalize_work_item_url(work_item_api_url)
        else:
            work_item_api_url = self._get_work_item_api_url()
        print(f"Work Item API URL: {work_item_api_url}")
        if attachments:
            work_item_id = None
            effective_base_url = work_item_api_url
            for file_path in attachments:
                work_item_id, effective_base_url = self._upload_work_item_file(
                    file_path=file_path,
                    work_item_api_url=effective_base_url,
                    work_item_id=work_item_id,
                )

            create_payload = {
                "work_item_id": work_item_id,
                "agent_id": agent_id,
                "payload": payload,
            }
        else:
            create_payload = {"agent_id": agent_id, "payload": payload}

        response, effective_base_url = self._request_work_item_api(
            effective_base_url if attachments else work_item_api_url,
            "",
            method="POST",
            json_data=create_payload,
        )
        work_item = response.json()

        if attachments:
            work_item_id = work_item.get("work_item_id") or work_item.get("id")
            if work_item_id:
                details_response, _ = self._request_work_item_api(
                    effective_base_url,
                    f"{work_item_id}?results=true",
                    method="GET",
                )
                work_item = details_response.json()

        return work_item
