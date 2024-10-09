"""Set of actions operating on Microsoft Email using Microsoft Graph API.

Currently supporting:
- Listing emails in the user's mailbox matching a search query.
- Filtering emails by recipient information.
- Creating a draft email in the user's mailbox.
- Updating an existing draft email.
- Adding an attachment to an email.
- Sending a new email.
- Sending an existing draft email.
- Replying to an existing email.
- Forwarding an existing email.
- Moving an email to a different folder.
- Retrieving details of a specific email by ID.
- Listing all folders in the user's mailbox.
- Subscribing to notifications for new emails or other mailbox changes.
- Deleting all active subscriptions for notifications.
- Deleting a specific subscription by ID.
- Getting a list of active subscriptions.
- Retrieving details of a specific folder in the user's mailbox.
"""

from sema4ai.actions import action, OAuth2Secret, Response, ActionError
from microsoft_mail.models import Email, EmailAttachment, Emails
from microsoft_mail.support import (
    _find_folder,
    _get_inbox_folder_id,
    _base64_attachment,
    _set_message_data,
    _delete_subscription,
    _get_folder_structure,
    _get_me,
)
from typing import Literal

from microsoft_mail.support import build_headers, send_request


@action
def list_emails(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.Read", "User.Read"]],
    ],
    search_query: str,
    folder_to_search: str = "inbox",
    properties_to_return: str = "",
    return_only_count: bool = False,
) -> Response[Emails]:
    """
    List emails in the user's mailbox matching search query.

    When searching emails in a specific folder, the folder name should be provided in the 'folder_to_search' parameter and NOT in the 'search_query'.

    Use action 'filter_by_recipients' if there are any conditions related to recipients ('to', 'cc', 'bcc' or 'from').

    For any date comparison use:
        - consider Monday as beginning of the week
        - date in ISO 8601 format (e.g., '2024-08-24')
        - use boolean operators (e.g., 'AND', 'OR', 'NOT'). These operators must be in uppercase.
        - comparison operators 'ge', 'le', 'eq', 'ne' (e.g., 'receivedDateTime ge 2024-08-24')

    Args:
        token: OAuth2 token to use for the operation.
        search_query: query to search for emails. Keep spaces in folder names if user gives spaces.
        folder_to_search: The folder to search for emails. Default is 'inbox'.
        properties_to_return: The properties to return in the response. Default is all properties. Comma separated list of properties, like 'subject,body,toRecipients'.
        return_only_count: Limit response size, but still return the count matching the query.

    Returns:
        List of the emails matching the search query.
    """
    items_per_query = "$top=50"
    count_param = "&count=true"
    keys_to_pop = ["body", "changeKey", "internetMessageId", "inferenceClassification"]
    keys_to_return = (
        [p.lower() for p in properties_to_return.split(",")]
        if properties_to_return
        else []
    )
    # Make sure that 'id' is always returned when keys are limited
    if len(keys_to_return) > 0 and "id" not in keys_to_return:
        keys_to_return.append("id")
    headers = build_headers(token)
    headers["ConsistencyLevel"] = "eventual"
    folders = []
    search_query = "" if search_query == "*" else search_query
    if folder_to_search == "inbox":
        inbox_folder_id = _get_inbox_folder_id(token)
        if len(search_query) > 0:
            search_query = f"{search_query} AND parentFolderId eq '{inbox_folder_id}'"
        else:
            search_query = f"parentFolderId eq '{inbox_folder_id}'"
    elif folder_to_search:
        folders = folders or list_folders(token).result
        folder_found = _find_folder(folders, folder_to_search)
        if folder_found is None:
            raise ActionError(f"Folder '{folder_to_search}' not found.")
        folder_to_search_id = folder_found["id"]
        if len(search_query) > 0:
            search_query = (
                f"{search_query} AND parentFolderId eq '{folder_to_search_id}'"
            )
        else:
            search_query = f"parentFolderId eq '{folder_to_search_id}'"
    else:
        # If no folder is provided, search in all folders except 'Sent Items'
        folders = folders or list_folders(token).result
        folder_found = _find_folder(folders, "Sent Items")
        send_items_folder_id = folder_found["id"]
        if len(search_query) > 0:
            search_query = (
                f"{search_query} AND parentFolderId ne '{send_items_folder_id}'"
            )
        else:
            search_query = f"parentFolderId ne '{send_items_folder_id}'"
    emails = Emails(items=[], count=0)
    query = f"/me/messages?{items_per_query}{count_param}&$filter={search_query}"
    while query:
        messages_result = send_request(
            "get",
            query,
            "list messages",
            headers=headers,
        )
        emails.count = messages_result.get("@odata.count", 0)
        _messages = [message for message in messages_result["value"]]
        for message in _messages:
            if keys_to_return:
                message = {
                    k: v for k, v in message.items() if k.lower() in keys_to_return
                }
            else:
                for k in keys_to_pop:
                    message.pop(k, None)
            emails.items.append(message)
        query = messages_result.get("@odata.nextLink", None)
    if return_only_count:
        emails.items = emails.items[:50]
    return Response(result=emails)


@action(is_consequential=False)
def filter_by_recipients(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.Read", "User.Read"]],
    ],
    search_query: str = "*",
    from_: str = "",
    to_recipients: str = "",
    cc_recipients: str = "",
    bcc_recipients: str = "",
    folder_to_search: str = "inbox",
    return_only_count: bool = False,
) -> Response[Emails]:
    """Filter list of emails objects by recipients.

    Args:
        token: OAuth2 token to use for the operation.
        search_query: Query to search for emails. Default is '*'.
        folder_to_search: Folder to search for emails. Default is 'inbox'.
        from_: Email address of the sender to filter by.
        to_recipients: Comma separated list of email addresses of the recipients to filter by.
        cc_recipients: Comma separated list of email addresses of the cc recipients to filter by.
        bcc_recipients: Comma separated list of email addresses of the bcc recipients to filter by.
        return_only_count: Limit response size, but still return the count matching the query.
    Returns:
        The list of emails filtered by recipients.
    """
    if all(
        not param for param in [to_recipients, cc_recipients, bcc_recipients, from_]
    ):
        raise ActionError(
            "At least one of the parameters must be provided to filter by recipients."
        )
    to = to_recipients.split(",") if to_recipients else []
    cc = cc_recipients.split(",") if cc_recipients else []
    bcc = bcc_recipients.split(",") if bcc_recipients else []
    froms = from_ or None

    email_list = list_emails(
        token=token, search_query=search_query, folder_to_search=folder_to_search
    ).result
    filtered_emails = []
    for email in email_list.items:
        email_from = email.get("from", {})
        if to and any(
            recipient["emailAddress"]["address"] in to
            for recipient in email.get("toRecipients", [])
        ):
            filtered_emails.append(email)
            continue
        if cc and any(
            recipient["emailAddress"]["address"] in cc
            for recipient in email.get("ccRecipients", [])
        ):
            filtered_emails.append(email)
            continue
        if bcc and any(
            recipient["emailAddress"]["address"] in bcc
            for recipient in email.get("bccRecipients", [])
        ):
            filtered_emails.append(email)
            continue
        if (
            froms
            and "emailAddress" in email_from.keys()
            and email_from["emailAddress"]["address"] == froms
        ):
            filtered_emails.append(email)
            continue
    email_list.count = len(filtered_emails)
    if return_only_count:
        email_list.items = filtered_emails[:50]
    else:
        email_list.items = filtered_emails
    return Response(result=email_list)


@action(is_consequential=True)
def create_draft(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.ReadWrite"]],
    ],
    email: Email,
    html_content: bool = False,
) -> Response:
    """
    Create a draft email in the user's mailbox.

    Args:
        token: OAuth2 token to use for the operation.
        email: The email content to create a draft.
        html_content: Whether the body content is HTML.

    Returns:
        The created draft email.
    """
    if all(
        not param
        for param in [
            email.subject,
            email.body,
            email.to,
            email.cc,
            email.bcc,
            email.attachments,
        ]
    ):
        raise ActionError(
            "At least one of the parameters must be provided to create a draft."
        )
    headers = build_headers(token)
    data = _set_message_data(email, html_content)
    draft = send_request(
        "post",
        "/me/messages",
        "create draft message",
        data=data,
        headers=headers,
    )
    if email.attachments and len(email.attachments.attachments) > 0:
        for attachment in email.attachments.attachments:
            add_attachment(token, draft["id"], attachment)
    return Response(result=draft)


@action(is_consequential=True)
def update_draft(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.ReadWrite"]],
    ],
    email_id: str,
    email: Email,
    html_content: bool = False,
) -> Response:
    """
    Update a draft email in the user's mailbox.

    Args:
        token: OAuth2 token to use for the operation.
        email_id: The ID of the draft email to update.
        email: The email content to update a draft.
        html_content: Whether the body content is HTML.

    Returns:
        The created draft email.
    """
    if all(
        not param
        for param in [
            email.subject,
            email.body,
            email.to,
            email.cc,
            email.bcc,
            email.attachments,
        ]
    ):
        raise ActionError(
            "At least one of the parameters must be provided to update the draft."
        )
    headers = build_headers(token)
    data = _set_message_data(email, html_content)
    if email.attachments and len(email.attachments.attachments) > 0:
        data["attachments"] = []
        for attachment in email.attachments.attachments:
            file_attachment = _base64_attachment(attachment)
            data["attachments"].append(file_attachment)
    draft = send_request(
        "patch",
        f"/me/messages/{email_id}",
        "update draft message",
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
    email_id: str,
    attachment: EmailAttachment,
) -> Response:
    """
    Add an attachment to an email.

    If possible pass attachment as local file absolute filepath, or
    pass the content_bytes directly.

    The attachment
    Args:
        token: OAuth2 token to use for the operation.
        email_id: The ID of the email to add the attachment to.
        attachment: The attachment to add.

    Returns:
        The added attachment details.
    """
    headers = build_headers(token)
    data = _base64_attachment(attachment)
    attachment_response = send_request(
        "post",
        f"/me/messages/{email_id}/attachments",
        "add attachment",
        data=data,
        headers=headers,
    )
    if "id" in attachment_response.keys():
        return Response(result="Attachment added successfully")
    else:
        raise ActionError(f"Error on 'add attachment': {attachment_response.text}")


@action(is_consequential=True)
def send_email(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.Send"]],
    ],
    email: Email,
    save_to_sent_items: bool = True,
    html_content: bool = False,
) -> Response:
    """
    Send a new email.

    Args:
        token: OAuth2 token to use for the operation.
        email: The email content to send.
        save_to_sent_items: Whether to save the email to the sent items.
        html_content: Whether the body content is HTML.

    Returns:
        Response indicating the result of the send operation.
    """
    if all(
        not param
        for param in [
            email.subject,
            email.body,
            email.to,
            email.cc,
            email.bcc,
            email.attachments,
        ]
    ):
        raise ActionError(
            "At least one of the parameters must be provided to send an email"
        )
    headers = build_headers(token)
    data = _set_message_data(email, html_content)
    if email.attachments and len(email.attachments.attachments) > 0:
        data["attachments"] = []
        for attachment in email.attachments.attachments:
            file_attachment = _base64_attachment(attachment)
            data["attachments"].append(file_attachment)
    send_request(
        "post",
        "/me/sendMail",
        "send email",
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
    email_id: str,
    save_to_sent_items: bool = True,
) -> Response:
    """
    Send a draft message.

    Args:
        token: OAuth2 token to use for the operation.
        email_id: The ID of the draft email to send.
        save_to_sent_items: Whether to save the email to the sent items.

    Returns:
        Response indicating the result of the send operation.
    """
    headers = build_headers(token)
    send_request(
        "post",
        f"/me/messages/{email_id}/send",
        "send draft",
        data={"saveToSentItems": save_to_sent_items},
        headers=headers,
    )
    return Response(result="Draft email sent successfully")


@action(is_consequential=True)
def reply_to_email(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.Send", "Mail.ReadWrite"]],
    ],
    email_id: str,
    reply: Email,
    html_content: bool = False,
    reply_to_all: bool = True,
) -> Response:
    """
    Reply to an existing message.

    Args:
        token: OAuth2 token to use for the operation.
        email_id: The ID of the email to reply to.
        reply: The reply email properties that needs to be appended, set or deleted. Do not modify the body of the email.
        html_content: Whether the body content is HTML.
        reply_to_all: Whether to reply to all recipients.
    Returns:
        Response indicating the result of the reply operation.
    """
    if len(reply.body) == 0:
        raise ActionError("Reply cannot be empty.")
    headers = build_headers(token)
    endpoint = "createReplyAll" if reply_to_all else "createReply"
    reply_data = _set_message_data(reply, html_content, reply=True)
    reply_response = send_request(
        "post",
        f"/me/messages/{email_id}/{endpoint}",
        f"{endpoint} to email",
        data=reply_data,
        headers=headers,
    )
    draft_message_id = reply_response["id"]
    for attachment in reply.attachments.attachments:
        add_attachment(token, draft_message_id, attachment)
    send_request(
        "post",
        f"/me/messages/{draft_message_id}/send",
        "send {endpoint} email",
        headers=headers,
    )
    return Response(result="Reply sent successfully")


@action(is_consequential=True)
def forward_email(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.Send"]],
    ],
    email_id: str,
    to_recipients: str,
    comment: str = "",
) -> Response:
    """
    Forward an existing message.

    Args:
        token: OAuth2 token to use for the operation.
        email_id: The ID of the email to forward.
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
        f"/me/messages/{email_id}/forward",
        "forward email",
        data=data,
        headers=headers,
    )
    return Response(result=forward_response)


@action(is_consequential=True)
def move_email(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.ReadWrite"]],
    ],
    email_id: str,
    destination_folder_id: str,
) -> Response:
    """
    Move a message to a different folder.

    Args:
        token: OAuth2 token to use for the operation.
        email_id: The ID of the email to move.
        destination_folder_id: The ID of the destination folder.

    Returns:
        The moved email details.
    """
    headers = build_headers(token)
    move_response = send_request(
        "post",
        f"/me/messages/{email_id}/move",
        "move email",
        data={"destinationId": destination_folder_id},
        headers=headers,
    )
    return Response(result=move_response)


@action
def get_email_by_id(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.Read"]],
    ],
    email_id: str,
    show_full_body: bool = False,
) -> Response:
    """
    Get the details of a specific email.

    By default shows email's body preview. If you want to see the full body,
    set 'show_full_body' to True.

    The full 'body' of the email might return too much information for the chat to handle.

    Args:
        token: OAuth2 token to use for the operation.
        email_id: The ID of the email to retrieve.
        show_full_body: Whether to show the full body content.

    Returns:
        The message details.
    """
    headers = build_headers(token)
    message = send_request(
        "get",
        f"/me/messages/{email_id}",
        "get email",
        headers=headers,
    )
    if show_full_body:
        message.pop("bodyPreview", None)
    else:
        message.pop("body", None)
    return Response(result=message)


@action
def list_folders(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.Read", "User.Read"]],
    ],
    account: str = "me",
) -> Response:
    """
    List folders in the user's mailbox.

    Args:
        token: OAuth2 token to use for the operation.
        account: The email account. By default "me"

    Returns:
        Lists of the folders. Always show all folders including amount of email in them.
    """
    if not account or account.lower() == "me":
        account_me = _get_me(token)
        account = account_me["mail"]
    folders = _get_folder_structure(token, account)
    return Response(result=folders)


@action
def subscribe_notifications(
    token: OAuth2Secret[
        Literal["microsoft"], list[Literal["Mail.ReadWrite", "User.Read"]]
    ],
    email_folder: str,
    webhook_url: str,
    expiration_date: str,
    account: str = "me",
) -> Response:
    """
    Subscribe to notifications for new messages in a specific folder.

    Expiration date can be at maximum 72 hours to the future. Set that if user does not give specific date.

    Args:
        token: The OAuth2 token for authentication.
        email_folder: The folder to subscribe to - this should be the real name, not ID.
        webhook_url: The URL to receive notifications.
        expiration_date: The expiration date of the subscription. Format 'YYYY-MM-DDTHH:MM'. Timezone is UTC.
        account: The user account (a email address)

    Returns:
        Response: Confirmation of successful subscription.
    """
    headers = build_headers(token)
    folder = get_folder(token, email_folder, account)
    if not account or account.lower() == "me":
        subscription_user = "/me"
    else:
        subscription_user = f"users/{account}"
    target_folder = folder.result["id"]
    subscription_resource = (
        f"{subscription_user}/mailFolders('{target_folder}')/messages"
    )
    data = {
        "changeType": "created",
        "notificationUrl": webhook_url,
        "resource": subscription_resource,
        "expirationDateTime": f"{expiration_date}:00.0000000Z",
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
        _delete_subscription(subscription["id"], headers)
    return Response(result="All subscriptions deleted")


@action
def delete_subscription(
    token: OAuth2Secret[Literal["microsoft"], list[Literal["Mail.ReadWrite"]]],
    subscription_id: str,
) -> Response:
    """
    Delete one subscription

    Args:
        token: The OAuth2 token for authentication.
        subscription_id: The ID of the subscription to delete.

    Returns:
        Response: Confirmation of successful deletion
    """
    headers = build_headers(token)
    _delete_subscription(subscription_id, headers)
    return Response(result="Subscription deleted")


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


@action
def get_folder(
    token: OAuth2Secret[Literal["microsoft"], list[Literal["Mail.Read", "User.Read"]]],
    folder_to_search: str,
    account: str = "me",
) -> Response[dict]:
    """
    Get the folder details by name.

    Args:
        token: The OAuth2 token for authentication.
        folder_to_search: The name or ID of the folder to retrieve.
        account: The email account. By default "me"

    Returns:
        The folder dictionary

    Raises:
        Exception: If the folder is not found.
    """
    if not account or account.lower() == "me":
        account_me = _get_me(token)
        account = account_me["mail"]
    folder_structure = _get_folder_structure(token, account)
    folder = _find_folder(folder_structure, folder_to_search)
    if folder is None:
        raise ActionError(f"Folder '{folder_to_search}' not found.")
    return Response(result=folder)
