from typing import Literal

import requests
from sema4ai.actions import ActionError, OAuth2Secret, Response, action

from microsoft_teams.models import (
    AddUsersToTeamRequest,
    ChannelMessageRequest,
    ChatCreationRequest,
    SendMessageRequest,
    TeamDetails,
    ReplyMessageRequest,
)
from microsoft_teams.support import (
    BASE_GRAPH_URL,
    build_headers,
)


@action
def post_channel_message(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["ChannelMessage.Send"]],
    ],
    message_request: ChannelMessageRequest,
) -> Response[dict]:
    """
    Post a message to a specific channel in a Microsoft Team. If multiple channels ask user which to use.

    Args:
        token: OAuth2 token to use for the operation.
        message_request: Pydantic model containing team_id, channel_id, and message.

    Returns:
        Result of the operation
    """
    headers = build_headers(token)
    payload = {"body": {"content": message_request.message}}
    response = requests.post(
        f"{BASE_GRAPH_URL}/teams/{message_request.team_id}/channels/{message_request.channel_id}/messages",
        headers=headers,
        json=payload,
    )
    if response.status_code in [200, 201]:
        return Response(result=response.json())
    else:
        raise ActionError(f"Failed to post channel message: {response.text}")


@action
def create_team(
    team_details: TeamDetails,
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Team.Create", "Group.Read.All"]],
    ],
) -> Response[dict]:
    """
    Create a new Microsoft Team using the standard template. If details are not returned search the Team by it's name after a moment.

    Args:
        team_details: Details of the team to be created.
        token: OAuth2 token to use for the operation.

    Returns:
        Result of the operation, including the details of the newly created team.
    """
    headers = build_headers(token)

    data = {
        "template@odata.bind": "https://graph.microsoft.com/v1.0/teamsTemplates('standard')",
        "displayName": team_details.display_name,
        "description": team_details.description,
        "visibility": team_details.visibility,
    }

    response = requests.post(f"{BASE_GRAPH_URL}/teams", headers=headers, json=data)

    if response.status_code in [200, 201, 202]:
        search_response = requests.get(
            f"{BASE_GRAPH_URL}/groups?$filter=displayName eq '{team_details.display_name}' and resourceProvisioningOptions/Any(x:x eq 'Team')",
            headers=headers,
        )

        if search_response.status_code in [200, 201]:
            search_results = search_response.json().get("value", [])
            if search_results:
                return Response(result=search_results[0])
            else:
                return Response(
                    result={
                        "message": "Team created, but could not yet find the details, search after a moment."
                    }
                )
        else:
            raise ActionError(
                f"Team created, but failed to search for team: {search_response.text}"
            )
    else:
        error_details = response.text
        raise ActionError(f"Failed to create team: {error_details}")


@action
def create_chat(
    chat_request: ChatCreationRequest,
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Chat.Create"]],
    ],
) -> Response[dict]:
    """
    Create a new chat (one-on-one or group) based on the number of recipients.

    Args:
        chat_request: Pydantic model containing a list of recipient IDs.
        token: OAuth2 token to use for the operation.

    Returns:
        Result of the operation, including chat details if successful.
    """
    headers = build_headers(token)

    me_response = requests.get(f"{BASE_GRAPH_URL}/me", headers=headers)
    if me_response.status_code in [200, 201]:
        my_details = me_response.json()
        user_id_1 = my_details["id"]
    else:
        raise ActionError(
            f"Failed to retrieve current user details: {me_response.text}"
        )

    members = [
        {
            "@odata.type": "#microsoft.graph.aadUserConversationMember",
            "roles": ["owner"],
            "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{user_id_1}')",
        }
    ]

    for user_id in chat_request.recipient_ids:
        members.append(
            {
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": ["owner"],
                "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{user_id}')",
            }
        )

    chat_type = "oneOnOne" if len(chat_request.recipient_ids) == 1 else "group"

    data = {"chatType": chat_type, "members": members}

    response = requests.post(f"{BASE_GRAPH_URL}/chats", headers=headers, json=data)

    if response.status_code in [200, 201]:
        return Response(result=response.json())
    else:
        raise ActionError(f"Failed to create chat: {response.text}")


@action
def send_message_to_chat(
    message_request: SendMessageRequest,
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["ChatMessage.Send"]],
    ],
) -> Response[dict]:
    """
    Send a message to a specific chat which needs to be created first.

    Args:
        message_request: Pydantic model containing the chat ID and message content.
        token: OAuth2 token to use for the operation.

    Returns:
        Result of the operation, including message details if successful.
    """
    headers = build_headers(token)

    data = {"body": {"content": message_request.message}}

    response = requests.post(
        f"{BASE_GRAPH_URL}/chats/{message_request.chat_id}/messages",
        headers=headers,
        json=data,
    )

    if response.status_code in [200, 201]:
        return Response(result=response.json())
    else:
        raise ActionError(f"Failed to send chat message: {response.text}")


@action
def add_users_to_team(
    add_users_request: AddUsersToTeamRequest,
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["GroupMember.ReadWrite.All"]],
    ],
) -> Response[dict]:
    """
    Add one or more users to a Microsoft Team.

    Args:
        add_users_request: Pydantic model containing the team ID and list of user IDs.
        token: OAuth2 token to use for the operation.

    Returns:
        Result of the operation, including details if successful.
    """
    headers = build_headers(token)
    team_id = add_users_request.team_id
    user_ids = add_users_request.user_ids

    results = []

    for user_id in user_ids:
        response = requests.post(
            f"{BASE_GRAPH_URL}/groups/{team_id}/members/$ref",
            headers=headers,
            json={"@odata.id": f"https://graph.microsoft.com/v1.0/users/{user_id}"},
        )

        if response.status_code in [200, 201, 204]:
            results.append({"user_id": user_id, "status": "Added successfully"})
        else:
            results.append(
                {"user_id": user_id, "status": f"Failed to add: {response.text}"}
            )

    return Response(result={"results": results})


@action
def reply_to_message(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["ChannelMessage.Send"]],
    ],
    reply_request: ReplyMessageRequest,
) -> Response[dict]:
    """
    Reply to a specific message in a Microsoft Team channel.

    Args:
        token: OAuth2 token to use for the operation.
        reply_request: Pydantic model containing team_id, channel_id, message_id, and the reply content.

    Returns:
        Result of the operation.
    """
    headers = build_headers(token)
    payload = {"body": {"content": reply_request.reply}}
    response = requests.post(
        f"{BASE_GRAPH_URL}/teams/{reply_request.team_id}/channels/{reply_request.channel_id}/messages/{reply_request.message_id}/replies",
        headers=headers,
        json=payload,
    )
    if response.status_code in [200, 201]:
        return Response(result=response.json())
    else:
        raise ActionError(f"Failed to reply to the message: {response.text}")
