BASE_GRAPH_URL = "https://graph.microsoft.com/v1.0"


def build_headers(token):
    return {
        "Authorization": f"Bearer {token.access_token}",
        "Content-Type": "application/json",
    }
