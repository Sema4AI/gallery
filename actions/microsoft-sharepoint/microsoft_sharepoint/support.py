import sema4ai_http
from sema4ai.actions import ActionError

BASE_GRAPH_URL = "https://graph.microsoft.com/v1.0"


class NotFound(Exception):
    """Raised when a requested resource is not found (HTTP 404)."""
    pass


def build_headers(token):
    return {
        "Authorization": f"Bearer {token.access_token}",
        "Content-Type": "application/json",
    }


def send_request(
    method,
    url,
    req_name,
    headers=None,
    data=None,
    params=None,
):
    """
    Generalized request handler.

    :param method: HTTP method (e.g., 'get', 'post').
    :param url: URL for the request.
    :param headers: Optional headers for the request.
    :param data: Optional JSON data for 'post' requests.
    :param params: Optional query parameters for 'get' requests.
    :return: JSON response data.
    :raises: RequestException for any request failures.
    """
    print(f"Sending request: {method} {url}")
    response = getattr(sema4ai_http, method.lower())(
        f"{BASE_GRAPH_URL}{url}", headers=headers, json=data, fields=params
    )
    if response.status_code in [200, 201]:
        return response.json()
    elif response.status_code == 204:
        # No Content (e.g., successful DELETE)
        return {}
    elif response.status_code == 404:
        # Not found (e.g., item does not exist)
        raise NotFound(f"Not found on '{req_name}': {response.text}")

    response.raise_for_status()  # Raises a HTTPError for bad responses

