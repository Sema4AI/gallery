import sema4ai_http
from sema4ai.actions import ActionError

BASE_GRAPH_URL = "https://graph.microsoft.com/v1.0"


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
    try:
        response = getattr(sema4ai_http, method.lower())(
            f"{BASE_GRAPH_URL}{url}", headers=headers, json=data, fields=params
        )
        response.raise_for_status()  # Raises a HTTPError for bad responses

        if response.status_code not in [200, 201]:
            raise ActionError(f"Error on '{req_name}': {response.text}")
        return response.json()

    except Exception as e:
        raise ActionError(f"Error on '{req_name}': {str(e)}")
