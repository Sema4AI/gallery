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
from microsoft_email.models import Message, MessageAttachment, MessageAttachmentList
from microsoft_email.support import _base64_attachment
from typing import Literal

from microsoft_email.support import build_headers, send_request


@action
def list_messages(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.Read"]],
    ],
    search_query: str,
    exclude_sent_items: bool = True,
) -> Response[list]:
    """
    List messages in the user's mailbox matching search query.

    For any date comparison use the following format:
        - consider Monday as beginning of the week
        - date in ISO 8601 format (e.g., '2024-08-24')
        - use boolean operators (e.g., 'AND', 'OR', 'NOT'). These operators must be in uppercase.
        - comparison operators 'ge', 'le', 'eq', 'ne' (e.g., 'receivedDateTime ge 2024-08-24')

    Args:
        token: OAuth2 token to use for the operation.
        search_query: query to search for messages.
        exclude_sent_items: Whether to exclude sent items from the search.

    Returns:
        Lists of the messages.
    """
    headers = build_headers(token)
    if exclude_sent_items:
        folders = list_folders(token)
        sent_items = next(
            folder for folder in folders.result if folder["displayName"] == "Sent Items"
        )
        send_items_folder_id = sent_items["id"]
        search_query = f"{search_query} AND parentFolderId ne '{send_items_folder_id}'"
    messages = send_request(
        "get",
        f"/me/messages?$filter={search_query}",
        "list messages",
        headers=headers,
    )
    messages = [message for message in messages["value"]]
    for message in messages:
        message.pop("body", None)
    return Response(result=messages)


@action(is_consequential=True)
def create_draft_message(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.ReadWrite"]],
    ],
    subject: str = "",
    body: str = "",
    to: str = "",
    cc: str = "",
    bcc: str = "",
    attachments: MessageAttachmentList = [],
) -> Response:
    """
    Create a draft message in the user's mailbox.

    Args:
        token: OAuth2 token to use for the operation.
        subject: Subject of the message.
        body: Body of the message.
        to: Comma separated list of email addresses of the recipients.
        cc: Comma separated list of email addresses of the CC recipients.
        bcc: Comma separated list of email addresses of the BCC recipients.
        attachments: Attachments to include with the message.

    Returns:
        The created draft message.
    """
    if all(not param for param in [subject, body, to, cc, bcc, attachments]):
        raise ActionError(
            "At least one of the parameters must be provided to create a draft."
        )
    headers = build_headers(token)
    data = {}
    if subject:
        data["subject"] = subject
    if body:
        data["body"] = {"contentType": "Text", "content": body}
    if to:
        data["toRecipients"] = [
            {"emailAddress": {"address": recipient.address, "name": recipient.name}}
            for recipient in to.split(",")
        ]
    if cc:
        data["ccRecipients"] = [
            {"emailAddress": {"address": recipient.address, "name": recipient.name}}
            for recipient in cc.split(",")
        ]
    if bcc:
        data["bccRecipients"] = [
            {"emailAddress": {"address": recipient.address, "name": recipient.name}}
            for recipient in bcc.split(",")
        ]
    draft = send_request(
        "post",
        "/me/messages",
        "create draft message",
        data=data,
        headers=headers,
    )
    print(f"type of attachments: {type(attachments)}")
    print(f"dir of attachments: {dir(attachments)}")
    if attachments and len(attachments.attachments) > 0:
        for attachment in attachments.attachments:
            add_attachment(token, draft["id"], attachment)
    return Response(result=draft)


@action(is_consequential=True)
def add_attachment(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.ReadWrite"]],
    ],
    message_id: str,
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
        f"/me/messages/{message_id}/attachments",
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
) -> Response:
    """
    Send a draft message.

    Args:
        token: OAuth2 token to use for the operation.
        message_id: The ID of the draft message to send.

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
        data=reply,
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
    to_recipients: str,
    comment: str = "",
) -> Response:
    """
    Forward an existing message.

    Args:
        token: OAuth2 token to use for the operation.
        message_id: The ID of the message to forward.
        to_recipients: Comma separated list of email addresses of the recipients to forward the message to.
        comment: A comment to include.

    Returns:
        Response indicating the result of the forward operation.
    """
    headers = build_headers(token)
    data = {
        "comment": comment,
        "toRecipients": [
            {"emailAddress": {"address": recipient.strip(), "name": recipient.strip()}}
            for recipient in to_recipients.split(",")
        ],
    }

    forward_response = send_request(
        "post",
        f"/me/messages/{message_id}/forward",
        "forward message",
        data=data,
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
        data={"destinationId": destination_folder_id},
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


@action
def list_folders(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.Read"]],
    ],
) -> Response:
    """
    List folders in the user's mailbox.

    Args:
        token: OAuth2 token to use for the operation.

    Returns:
        Lists of the folders.
    """
    headers = build_headers(token)
    folders = send_request(
        "get",
        "/me/mailFolders",
        "list folders",
        headers=headers,
    )
    folders = [folder for folder in folders["value"]]
    return Response(result=folders)
