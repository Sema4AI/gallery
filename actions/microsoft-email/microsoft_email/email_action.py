"""Set of actions operating on Microsoft Email using Microsoft Graph API.

Currently supporting:
- listing messages in the user's mailbox matching a search query.
- creating a draft message in the user's mailbox.
- adding an attachment to a message.
- sending a new message.
- sending a draft message.
- replying to an existing message.
- forwarding an existing message.
- moving a message to a different folder.
- getting the details of a specific message.
"""

from sema4ai.actions import action, OAuth2Secret, Response, ActionError
from microsoft_email.models import Message, MessageAttachment
from microsoft_email.support import _base64_attachment
from typing import Literal

from microsoft_email.support import build_headers, send_request


@action
def list_messages(
    search_query: str,
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.Read"]],
    ],
) -> Response[list]:
    """
    List messages in the user's mailbox matching search query.

    Args:
        search_query: query to search for messages.
        token: OAuth2 token to use for the operation.

    Returns:
        Lists of the messages
    """
    headers = build_headers(token)
    print(f"search_query: {search_query}")
    messages = send_request(
        "get",
        f'/me/messages?$searc="{search_query}"',
        "list messages",
        headers=headers,
    )
    messages = [message for message in messages["value"]]
    for message in messages:
        if "body" in message and "content" in message["body"]:
            message["body"]["content"] = ""
    return Response(result=messages)


@action(is_consequential=True)
def create_draft_message(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.ReadWrite"]],
    ],
    message: Message,
) -> Response:
    """
    Create a draft message in the user's mailbox.

    Args:
        token: OAuth2 token to use for the operation.
        message: The message content to save as a draft.

    Returns:
        The created draft message.
    """
    headers = build_headers(token)
    data = {
        "subject": message.subject,
        "body": {"contentType": "Text", "content": message.body},
        "toRecipients": [
            {"emailAddress": {"address": recipient.address, "name": recipient.name}}
            for recipient in message.to
        ],
    }
    draft = send_request(
        "post",
        "/me/messages",
        "create draft message",
        data=data,
        headers=headers,
    )
    if message.attachments and len(message.attachments) > 0:
        for attachment in message.attachments:
            attachment.message_id = draft["id"]
            add_attachment(token, attachment)
    return Response(result=draft)


@action(is_consequential=True)
def add_attachment(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.ReadWrite"]],
    ],
    attachment: MessageAttachment,
) -> Response:
    """
    Add an attachment to a message.

    If possible pass attachment as local file absolute filepath, or
    pass the content_bytes directly.

    The attachment
    Args:
        token: OAuth2 token to use for the operation.
        message_id: The ID of the message to add the attachment to.
        attachment: The attachment to add.

    Returns:
        The added attachment details.
    """
    headers = build_headers(token)
    data = _base64_attachment(attachment)
    attachment_response = send_request(
        "post",
        f"/me/messages/{attachment.message_id}/attachments",
        "add attachment",
        data=data,
        headers=headers,
    )
    if "id" in attachment_response.keys():
        return Response(result="Attachment added successfully")
    else:
        raise ActionError(f"Error on 'add attachment': {attachment_response.text}")


@action(is_consequential=True)
def send_message(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.Send"]],
    ],
    message: Message,
    save_to_sent_items: bool = True,
) -> Response:
    """
    Send a new message.

    Args:
        token: OAuth2 token to use for the operation.
        message: The message content to send.
        save_to_sent_items: Whether to save the message to the sent items.

    Returns:
        Response indicating the result of the send operation.
    """
    headers = build_headers(token)
    print(f"Received message: {message}")
    data = {
        "subject": message.subject,
        "body": {"contentType": "Text", "content": message.body},
        "toRecipients": [
            {"emailAddress": {"address": recipient.address, "name": recipient.name}}
            for recipient in message.to
        ],
        "importance": message.importance,
    }
    if message.cc and len(message.cc) > 0:
        data["ccRecipients"] = [
            {"emailAddress": {"address": recipient.address, "name": recipient.name}}
            for recipient in message.cc
        ]
    if message.bcc and len(message.bcc) > 0:
        data["bccRecipients"] = [
            {"emailAddress": {"address": recipient.address, "name": recipient.name}}
            for recipient in message.bcc
        ]
    if message.attachments and len(message.attachments) > 0:
        data["attachments"] = []
        for attachment in message.attachments:
            file_attachment = _base64_attachment(attachment)
            data["attachments"].append(file_attachment)
    if message.reply_to:
        data["replyTo"] = {
            "emailAddress": {
                "address": message.reply_to.address,
                "name": message.reply_to.name,
            }
        }
    send_request(
        "post",
        "/me/sendMail",
        "send message",
        data={"message": data, "saveToSentItems": save_to_sent_items},
        headers=headers,
    )
    return Response(result="Email sent successfully")


@action(is_consequential=True)
def send_draft(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.Send"]],
    ],
    message_id: str,
    save_to_sent_items: bool = True,
) -> Response:
    """
    Send a draft message.

    Args:
        token: OAuth2 token to use for the operation.
        message_id: The ID of the draft message to send.
        save_to_sent_items: Whether to save the message to the sent items.

    Returns:
        Response indicating the result of the send operation.
    """
    headers = build_headers(token)
    send_request(
        "post",
        f"/me/messages/{message_id}/send",
        "send draft",
        headers=headers,
    )
    return Response(result="Draft email sent successfully")


@action(is_consequential=True)
def reply_to_message(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.Send"]],
    ],
    message_id: str,
    reply: Message,
) -> Response:
    """
    Reply to an existing message.

    Args:
        token: OAuth2 token to use for the operation.
        message_id: The ID of the message to reply to.
        reply: The reply message content.

    Returns:
        Response indicating the result of the reply operation.
    """
    headers = build_headers(token)
    reply_response = send_request(
        "post",
        f"/me/messages/{message_id}/reply",
        "reply to message",
        json=reply,
        headers=headers,
    )
    return Response(result=reply_response)


@action(is_consequential=True)
def forward_message(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.Send"]],
    ],
    message_id: str,
    forward: Message,
) -> Response:
    """
    Forward an existing message.

    Args:
        token: OAuth2 token to use for the operation.
        message_id: The ID of the message to forward.
        forward: The forward message content.

    Returns:
        Response indicating the result of the forward operation.
    """
    headers = build_headers(token)
    forward_response = send_request(
        "post",
        f"/me/messages/{message_id}/forward",
        "forward message",
        json=forward,
        headers=headers,
    )
    return Response(result=forward_response)


@action(is_consequential=True)
def move_message(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.ReadWrite"]],
    ],
    message_id: str,
    destination_folder_id: str,
) -> Response:
    """
    Move a message to a different folder.

    Args:
        token: OAuth2 token to use for the operation.
        message_id: The ID of the message to move.
        destination_folder_id: The ID of the destination folder.

    Returns:
        The moved message details.
    """
    headers = build_headers(token)
    move_response = send_request(
        "post",
        f"/me/messages/{message_id}/move",
        "move message",
        json={"destinationId": destination_folder_id},
        headers=headers,
    )
    return Response(result=move_response)


@action
def get_message(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.Read"]],
    ],
    message_id: str,
) -> Response:
    """
    Get the details of a specific message.

    Args:
        token: OAuth2 token to use for the operation.
        message_id: The ID of the message to retrieve.

    Returns:
        The message details.
    """
    headers = build_headers(token)
    message = send_request(
        "get",
        f"/me/messages/{message_id}",
        "get message",
        headers=headers,
    )
    return Response(result=message)
