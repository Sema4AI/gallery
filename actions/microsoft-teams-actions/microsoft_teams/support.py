BASE_GRAPH_URL = "https://graph.microsoft.com/v1.0"


def build_headers(token):
    return {
        "Authorization": f"Bearer {token.access_token}",
        "Content-Type": "application/json",
    }


def parse_channel_messages(response_data: dict) -> list:
    """
    Parse the channel messages response to extract relevant details.

    Args:
        response_data: The full JSON response from the Microsoft Graph API.

    Returns:
        A list of parsed messages with key details.
    """
    parsed_messages = []

    for message in response_data.get("value", []):
        parsed_message = {
            "id": message.get("id"),
            "createdDateTime": message.get("createdDateTime"),
            "from": message.get("from", {}).get("user", {}).get("displayName"),
            "sender_id": message.get("from", {}).get("user", {}).get("id"),
            "content": message.get("body", {}).get("content"),
        }
        parsed_messages.append(parsed_message)

    return parsed_messages


def parse_message_replies(response_data: dict) -> list:
    """
    Parse the message replies response to extract relevant details.

    Args:
        response_data: The full JSON response from the Microsoft Graph API.

    Returns:
        A list of parsed replies with key details.
    """
    parsed_replies = []

    for reply in response_data.get("value", []):
        parsed_reply = {
            "id": reply.get("id"),
            "createdDateTime": reply.get("createdDateTime"),
            "from": reply.get("from", {}).get("user", {}).get("displayName"),
            "sender_id": reply.get("from", {}).get("user", {}).get("id"),
            "content": reply.get("body", {}).get("content"),
        }
        parsed_replies.append(parsed_reply)

    return parsed_replies
