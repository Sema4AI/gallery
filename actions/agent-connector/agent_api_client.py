import os
import json
import platform
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse

import sema4ai_http
from urllib3.exceptions import ConnectionError, HTTPError


class AgentAPIClient:
    def __init__(self, api_key=None):
        """Initialize the AgentAPIClient.
        
        Args:
            api_key: Optional API key to use for authentication in cloud environments
        """
        self.api_url = self._get_api_url()
        self.api_key = api_key
        print(f"API URL: {self.api_url}")
        
        # Determine if we're running in cloud based on https protocol using proper URL parsing
        if self.api_url:
            parsed_url = urlparse(self.api_url)
            self.is_cloud = parsed_url.scheme == "https"
            if self.is_cloud:
                print("Running in cloud environment (HTTPS) - will use Bearer authentication")
            else:
                print(f"Running in local environment ({parsed_url.scheme}) - no authentication required")
        else:
            self.is_cloud = False
            print("No API URL detected - cannot determine environment")

    def _get_api_url(self) -> str:
        """Determine the correct API URL by checking environment variable and testing API availability.

        Returns:
            str: The working API URL

        Raises:
            ConnectionError: If no API server is responding
        """
        def test_url(url: str) -> bool:
            try:
                parsed = urlparse(url)
                if parsed.scheme not in ("http", "https"):
                    return False
                response = sema4ai_http.get(f"{url}", timeout=1)
                return True
            except (HTTPError, ValueError) as e:
                return False
            except Exception as e:
                return False

        # First check environment variable
        if api_url := os.getenv("SEMA4AI_API_V1_URL"):
            if test_url(api_url):
                return api_url

        # Try reading from agent-server.pid file - use OS-specific paths
        pid_file_path = self._get_pid_file_path()
        print(f"Looking for PID file at: {pid_file_path}")
        
        try:
            if os.path.exists(pid_file_path):
                with open(pid_file_path, "r") as f:
                    content = f.read()
                    server_info = json.loads(content)
                    if base_url := server_info.get("base_url"):
                        api_url = f"{base_url}/api/public/v1"
                        if test_url(api_url):
                            return api_url
        except (json.JSONDecodeError, IOError) as e:
            pass

        # Could not connect to API server or find the PID file
        return None
        
    def _get_pid_file_path(self) -> str:
        """Get the path to the agent-server.pid file based on the operating system.
        
        Returns:
            str: Path to the PID file
        """
        home_dir = os.path.expanduser("~")
        
        # Determine OS-specific path
        if platform.system() == "Windows":
            # Windows path: C:\Users\<username>\AppData\Local\sema4ai\sema4ai-studio\agent-server.pid
            return os.path.join(home_dir, "AppData", "Local", "sema4ai", "sema4ai-studio", "agent-server.pid")
        else:
            # macOS/Linux path: ~/.sema4ai/sema4ai-studio/agent-server.pid
            return os.path.join(home_dir, ".sema4ai", "sema4ai-studio", "agent-server.pid")

    def request(self, path: str, method="GET", json_data=None, headers=None):
        """Make an API request with common error handling.

        Args:
            path: API endpoint path
            method: HTTP method (GET or POST)
            json_data: Optional JSON payload for POST requests
            headers: Optional additional headers

        Returns:
            Response object

        Raises:
           urllib3.exceptions.ConnectionError: If the request fails or returns an error status
        """
        if self.api_url is None:
            raise ConnectionError("Agent Server not running")

        url = urljoin(self.api_url + "/", quote(path))
        
        # Initialize headers
        request_headers = headers.copy() if headers else {}
        
        # Add Bearer token for cloud environments if API key is provided
        if self.is_cloud and self.api_key:
            request_headers["Authorization"] = f"Bearer {self.api_key}"
            print("Adding Bearer token authentication")

        if method == "GET":
            response = sema4ai_http.get(url, json=json_data, headers=request_headers)
        elif method == "POST":
            response = sema4ai_http.post(url, json=json_data, headers=request_headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()

        return response
