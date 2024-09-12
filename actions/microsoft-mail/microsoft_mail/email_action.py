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
from microsoft_mail.models import Message, MessageAttachment
from microsoft_mail.support import (
    _base64_attachment,
    _set_message_data,
    _get_folder_id,
)
from typing import Literal

from microsoft_mail.support import build_headers, send_request


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

    For email address search use:
        - from/emailAddress/address eq 'sender@example.com

    For any date comparison use:
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
    message: Message,
    html_content: bool = False,
) -> Response:
    """
    Create a draft message in the user's mailbox.

    Args:
        token: OAuth2 token to use for the operation.
        message: The message content to create a draft.
        html_content: Whether the body content is HTML.

    Returns:
        The created draft message.
    """
    if all(
        not param
        for param in [
            message.subject,
            message.body,
            message.to,
            message.cc,
            message.bcc,
            message.attachments,
        ]
    ):
        raise ActionError(
            "At least one of the parameters must be provided to create a draft."
        )
    headers = build_headers(token)
    data = _set_message_data(message, html_content)
    draft = send_request(
        "post",
        "/me/messages",
        "create draft message",
        data=data,
        headers=headers,
    )
    if message.attachments and len(message.attachments.attachments) > 0:
        for attachment in message.attachments.attachments:
            add_attachment(token, draft["id"], attachment)
    return Response(result=draft)


@action(is_consequential=True)
def update_draft_message(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.ReadWrite"]],
    ],
    message_id: str,
    message: Message,
    html_content: bool = False,
) -> Response:
    """
    Update a draft message in the user's mailbox.

    Args:
        token: OAuth2 token to use for the operation.
        message_id: The ID of the draft message to update.
        message: The message content to update a draft.
        html_content: Whether the body content is HTML.

    Returns:
        The created draft message.
    """
    if all(
        not param
        for param in [
            message.subject,
            message.body,
            message.to,
            message.cc,
            message.bcc,
            message.attachments,
        ]
    ):
        raise ActionError(
            "At least one of the parameters must be provided to create a draft."
        )
    headers = build_headers(token)
    data = _set_message_data(message, html_content)
    if message.attachments and len(message.attachments.attachments) > 0:
        data["attachments"] = []
        for attachment in message.attachments.attachments:
            file_attachment = _base64_attachment(attachment)
            data["attachments"].append(file_attachment)
    draft = send_request(
        "patch",
        f"/me/messages/{message_id}",
        "create draft message",
        data=data,
        headers=headers,
    )
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
    html_content: bool = False,
) -> Response:
    """
    Send a new message.

    Args:
        token: OAuth2 token to use for the operation.
        message: The message content to send.
        save_to_sent_items: Whether to save the message to the sent items.
        html_content: Whether the body content is HTML.

    Returns:
        Response indicating the result of the send operation.
    """
    if all(
        not param
        for param in [
            message.subject,
            message.body,
            message.to,
            message.cc,
            message.bcc,
            message.attachments,
        ]
    ):
        raise ActionError(
            "At least one of the parameters must be provided to create a draft."
        )
    headers = build_headers(token)
    print(f"Received message: {message}")
    data = _set_message_data(message, html_content)
    if message.attachments and len(message.attachments.attachments) > 0:
        data["attachments"] = []
        for attachment in message.attachments.attachments:
            file_attachment = _base64_attachment(attachment)
            data["attachments"].append(file_attachment)
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
        data={"saveToSentItems": save_to_sent_items},
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
    html_content: bool = False,
) -> Response:
    """
    Reply to an existing message.

    Args:
        token: OAuth2 token to use for the operation.
        message_id: The ID of the message to reply to.
        reply: The reply message properties that needs to be appended, set or deleted. Do not modify the body of the message.
        html_content: Whether the body content is HTML.

    Returns:
        Response indicating the result of the reply operation.
    """
    headers = build_headers(token)
    existing_message = get_message(token, message_id).result
    print(f"existing_message: {existing_message}")
    message_data = _set_message_data(reply, html_content, existing_message)
    data = {}
    data["message"] = message_data
    if reply.body:
        data["comment"] = reply.body
    reply_response = send_request(
        "post",
        f"/me/messages/{message_id}/reply",
        "reply to message",
        data=data,
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


@action
def subscribe_notifications(
    token: OAuth2Secret[Literal["microsoft"], list[Literal["Mail.ReadWrite"]]],
    message_folder: str,
    webhook_url: str,
    expiration_date: str,
    account: str,
) -> Response:
    """
    Subscribe to notifications for new messages in a specific folder.

    Args:
        token: The OAuth2 token for authentication.
        message_folder: The folder to subscribe to.
        webhook_url: The URL to receive notifications.
        expiration_date: The expiration date of the subscription. This needs to be in UTC format.
        account: The email account.

    Returns:
        Response: Confirmation of successful subscription.
    """
    headers = build_headers(token)
    account = "me" if account.lower() == "me" or len(account) == 0 else account
    if message_folder.lower() == "inbox":
        target_folder = "Inbox"
    else:
        target_folder = _get_folder_id(token, account, message_folder)
    # subscription_resource = (
    #     f"users/mika@beissi.onmicrosoft.com/mailFolders('Inbox')/messages"
    # )
    subscription_resource = f"me/mailFolders('{target_folder}')/messages"
    data = {
        "changeType": "created",
        "notificationUrl": webhook_url,
        "resource": subscription_resource,
        "expirationDateTime": "2024-09-13T08:00:00.9356913",  # expiration_date,
        "clientState": "secretClientValue",
        "latestSupportedTlsVersion": "v1_2",
    }
    message = send_request(
        "post",
        "/subscriptions",
        "subscribe for notifications",
        headers=headers,
        data=data,
    )
    return Response(result=message)


@action
def delete_all_subscriptions(
    token: OAuth2Secret[Literal["microsoft"], list[Literal["Mail.ReadWrite"]]]
) -> Response:
    """
    Delete all existing subscriptions.

    Args:
        token: The OAuth2 token for authentication.

    Returns:
        Response: Confirmation of successful deletion of all subscriptions.
    """
    headers = build_headers(token)
    message = send_request(
        "get",
        "/subscriptions",
        "get subscriptions",
        headers=headers,
    )
    for subscription in message["value"]:
        send_request(
            "delete",
            f"/subscriptions/{subscription['id']}",
            "delete subscription",
            headers=headers,
        )
    return Response(result="All subscriptions deleted")


@action
def get_subscriptions(
    token: OAuth2Secret[Literal["microsoft"], list[Literal["Mail.Read"]]]
) -> Response:
    """
    Get a list of all active subscriptions.

    Args:
        token (OAuth2Secret): The OAuth2 token for authentication.

    Returns:
        Response: A list of all active subscriptions.
    """
    headers = build_headers(token)
    message = send_request(
        "get",
        "/subscriptions",
        "get subscriptions",
        headers=headers,
    )
    return Response(result=message)
