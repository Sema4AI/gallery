import os
import requests
from urllib.parse import urlparse, quote, urljoin


class AgentAPIClient:
    def __init__(self):
        self.api_url = self._get_api_url()

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
                requests.get(f"{url}", timeout=1)
                return True
            except (requests.RequestException, ValueError):
                return False

        # First check environment variable
        if url := os.getenv("SEMA4AI_AGENT_SERVER_API_URL"):
            if test_url(url):
                return url

        # Try default ports
        for port in [8990, 8000]:
            url = f"http://localhost:{port}/api/v1"
            if test_url(url):
                return url

        # Could not connect to API server on ports 8990 or 8000, or the given environment variable
        return None

    def request(self, path: str, method="GET", json_data=None):
        """Make an API request with common error handling.

        Args:
            path: API endpoint path
            method: HTTP method (GET or POST)
            json_data: Optional JSON payload for POST requests

        Returns:
            Response object

        Raises:
            requests.exceptions.RequestException: If the request fails or returns an error status
        """
        if self.api_url is None:
            raise requests.exceptions.ConnectionError("Agent Server not running")

        url = urljoin(self.api_url + "/", quote(path))
        response = requests.request(method, url, json=json_data)
        response.raise_for_status()
        return response
