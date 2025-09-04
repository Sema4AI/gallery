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
- Retrieving details of a specific email by subject.
- Listing all folders in the user's mailbox.
- Subscribing to notifications for new emails or other mailbox changes.
- Deleting all active subscriptions for notifications.
- Deleting a specific subscription by ID.
- Getting a list of active subscriptions.
- Retrieving details of a specific folder in the user's mailbox.
- Adding categories to emails.
- Removing categories from emails.
- Listing master categories with their colors.
- Flagging emails with different statuses.
"""

from sema4ai.actions import action, OAuth2Secret, Response, ActionError
from sema4ai.actions.chat import attach_file
from microsoft_mail.models import Email, EmailAttachment, Emails, MessageFlag, Category
from microsoft_mail.support import (
    _find_folder,
    _get_inbox_folder_id,
    _base64_attachment,
    _set_message_data,
    _delete_subscription,
    _get_folder_structure,
    _get_me,
    _ensure_category_exists,
    _get_category_info,
)
from dotenv import load_dotenv
from typing import Literal
from pathlib import Path
import os
import base64
import tempfile

from microsoft_mail.support import build_headers, send_request


load_dotenv(Path(__file__).absolute().parent.parent / "devdata" / ".env")


@action
def list_emails(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.Read", "User.Read"]],
    ],
    search_query: str,
    folder_to_search: str = "inbox",
    properties_to_return: str = "",
    max_emails_to_return: int = -1,
    return_only_count: bool = False,
    has_attachments: bool = False,
) -> Response[Emails]:
    """
    List emails in the user's mailbox matching search query using Microsoft Graph API OData syntax.

    When searching emails in a specific folder, the folder name should be provided in the 'folder_to_search' parameter and NOT in the 'search_query'.

    Use action 'filter_by_recipients' if there are any conditions related to recipients ('to', 'cc', 'bcc' or 'from').

    Microsoft Graph API Query Syntax Examples:

    Basic Queries:
        - "*" or "" - Get all emails
        - "hasAttachments eq true" - Emails with attachments
        - "isRead eq false" - Unread emails
        - "importance eq 'high'" - High importance emails
        - "flag/flagStatus eq 'flagged'" - Flagged emails

    Date/Time Queries:
        - "receivedDateTime ge 2024-01-01T00:00:00Z" - Emails from 2024 onwards
        - "receivedDateTime ge 2024-01-01" - Emails from 2024 onwards (date only)
        - "receivedDateTime ge 2024-01-01 AND receivedDateTime le 2024-12-31" - Emails in 2024
        - "createdDateTime ge 2024-01-01T00:00:00Z" - Emails created from 2024

    Subject/Body Queries:
        - "contains(subject, 'meeting')" - Subject contains 'meeting'
        - "subject eq 'Important Update'" - Exact subject match
        - "contains(body/content, 'urgent')" - Body contains 'urgent'
        - "startswith(subject, 'RE:')" - Subject starts with 'RE:'

    Sender/Recipient Queries:
        - "from/emailAddress/address eq 'john@example.com'" - From specific sender
        - "contains(from/emailAddress/address, '@company.com')" - From company domain
        - "toRecipients/any(r: r/emailAddress/address eq 'jane@example.com')" - To specific recipient

    Combined Queries:
        - "hasAttachments eq true AND receivedDateTime ge 2024-01-01" - Attachments from 2024
        - "isRead eq false AND importance eq 'high'" - Unread high importance
        - "contains(subject, 'urgent') OR importance eq 'high'" - Urgent subject OR high importance
        - "receivedDateTime ge 2024-01-01 AND (hasAttachments eq true OR importance eq 'high')" - Complex query

    Folder Queries:
        - Use folder_to_search parameter instead of parentFolderId in search_query
        - "inbox" - Search in inbox folder
        - "Sent Items" - Search in sent items
        - "Drafts" - Search in drafts folder
        - Custom folder names work if they exist

    Query Rules:
        - Use uppercase boolean operators: AND, OR, NOT
        - Use single quotes for string values: 'value'
        - Use ISO 8601 format for dates: 2024-01-01T00:00:00Z
        - Use comparison operators: eq, ne, gt, ge, lt, le
        - Use functions: contains(), startswith(), endswith()
        - Group conditions with parentheses: (condition1 OR condition2) AND condition3

    Args:
        token: OAuth2 token to use for the operation.
        search_query: OData query to search for emails. Use Microsoft Graph API syntax.
        folder_to_search: The folder to search for emails. Default is 'inbox'.
        properties_to_return: The properties to return in the response. Default is all properties. Comma separated list of properties, like 'id,subject,body,toRecipients'.
        max_emails_to_return: Maximum number of emails to return. Default is -1 (return all emails).
        return_only_count: Limit response size, but still return the count matching the query.
        has_attachments: Filter emails to only include those with attachments. Default is False.

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

    # Handle has_attachments parameter
    if has_attachments:
        if search_query == "*" or search_query == "":
            search_query = "hasAttachments eq true"
        else:
            search_query = f"({search_query}) AND hasAttachments eq true"
    else:
        # Keep "*" as "*" for "get all" queries, only convert empty string
        search_query = "*" if search_query == "*" else ("" if search_query == "" else search_query)

    # Handle folder filtering
    use_folder_endpoint = False
    if folder_to_search == "inbox":
        inbox_folder_id = _get_inbox_folder_id(token)
        if len(search_query) > 0:
            search_query = f"{search_query} AND parentFolderId eq '{inbox_folder_id}'"
        else:
            search_query = f"parentFolderId eq '{inbox_folder_id}'"
        # Try using the folder-specific endpoint instead of parentFolderId filter
        use_folder_endpoint = True
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

    # Enable client-side filtering for hasAttachments when folder filtering is involved
    # This is a workaround for Microsoft Graph API issues with hasAttachments + parentFolderId
    needs_client_side_filtering = has_attachments and folder_to_search == "inbox"

    # Use folder-specific endpoint for inbox to avoid parentFolderId filter issues
    if use_folder_endpoint and folder_to_search == "inbox":
        # Remove parentFolderId from search_query since we're using folder endpoint
        search_query_for_endpoint = search_query.replace(f" AND parentFolderId eq '{inbox_folder_id}'", "").replace(f"parentFolderId eq '{inbox_folder_id}'", "")
        if search_query_for_endpoint.strip() == "" or search_query_for_endpoint.strip() == "*":
            # For "get all" queries, don't use $filter parameter
            query = f"/me/mailFolders/{inbox_folder_id}/messages?{items_per_query}{count_param}"
        else:
            query = f"/me/mailFolders/{inbox_folder_id}/messages?{items_per_query}{count_param}&$filter={search_query_for_endpoint}"
    else:
        if search_query.strip() == "" or search_query.strip() == "*":
            # For "get all" queries, don't use $filter parameter
            query = f"/me/messages?{items_per_query}{count_param}"
        else:
            query = f"/me/messages?{items_per_query}{count_param}&$filter={search_query}"

    # If we're doing client-side filtering, remove hasAttachments from the query
    if needs_client_side_filtering:
        # Remove hasAttachments from the query since we'll filter client-side
        query_without_attachments = query.replace("&$filter=hasAttachments eq true", "").replace("&$filter=hasAttachments eq true AND", "&$filter=")
        if "&$filter=" in query_without_attachments and query_without_attachments.split("&$filter=")[1].strip() == "":
            query_without_attachments = query_without_attachments.replace("&$filter=", "")
        query = query_without_attachments

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
            if max_emails_to_return > 0 and len(emails.items) >= max_emails_to_return:
                query = None
                break
        query = messages_result.get("@odata.nextLink", None)

    # Apply client-side filtering for hasAttachments when needed
    if needs_client_side_filtering:
        filtered_emails = []
        for email in emails.items:
            # Check if email has attachments
            has_attachments_value = email.get("hasAttachments", False)
            if has_attachments_value:
                filtered_emails.append(email)
        emails.items = filtered_emails
        emails.count = len(filtered_emails)

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
        email_id: The unique identifier of the email to update.
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

    Args:
        token: OAuth2 token to use for the operation.
        email_id: The unique identifier of the email to add the attachment to.
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
        email_id: The unique identifier of the email to send.
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
        email_id: The unique identifier of the email to reply to.
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
        email_id: The unique identifier of the email to forward.
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
        email_id: The unique identifier of the email to move.
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
    save_attachments: bool = False,
) -> Response:
    """
    Get the details of a specific email and optionally attach files to the chat.

    By default shows email's body preview. If you want to see the full body,
    set 'show_full_body' to True.

    The full 'body' of the email might return too much information for the chat to handle.

    Args:
        token: OAuth2 token to use for the operation.
        email_id: The unique identifier of the email to retrieve.
        show_full_body: Whether to show the full body content.
        save_attachments: Whether to attach the email attachments to the chat using sema4ai.actions.chat.

    Returns:
        The message details.
    """
    # The environment variable is used to test the action
    email_id = email_id or os.getenv("EMAIL_WITH_ATTACHMENTS")
    if not email_id:
        raise ActionError("Email ID is required")
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

    if save_attachments:
        # Fetch attachments separately
        attachments_response = send_request(
            "get",
            f"/me/messages/{email_id}/attachments",
            "get email attachments",
            headers=headers,
        )
        attachments = attachments_response.get("value", [])

        message["attachments"] = []
        for attachment in attachments:
            attachment_name = attachment["name"]
            attachment_content = attachment["contentBytes"]

            # Create a temporary file to save the attachment
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{attachment_name}") as temp_file:
                temp_file.write(base64.b64decode(attachment_content))
                temp_file_path = temp_file.name

            # Attach the file to the chat using sema4ai.actions.chat
            attach_file(temp_file_path, name=attachment_name)
            message["attachments"].append(attachment_name)

    return Response(result=message)


@action
def get_email_by_subject(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Mail.Read"]],
    ],
    subject: str,
    folder_to_search: str = "inbox",
    show_full_body: bool = False,
    save_attachments: bool = False,
    exact_match: bool = False,
) -> Response:
    """
    Get the details of a specific email by subject and optionally attach files to the chat.

    By default shows email's body preview. If you want to see the full body,
    set 'show_full_body' to True.

    The full 'body' of the email might return too much information for the chat to handle.

    Args:
        token: OAuth2 token to use for the operation.
        subject: The subject line to search for.
        folder_to_search: The folder to search for emails. Default is 'inbox'.
        show_full_body: Whether to show the full body content.
        save_attachments: Whether to attach the email attachments to the chat using sema4ai.actions.chat.
        exact_match: Whether to match the subject exactly (case-insensitive). Default is False (partial match).

    Returns:
        The message details of the first email found with the matching subject.
        Raises ActionError if no email is found with the specified subject.
    """
    if not subject:
        raise ActionError("Subject is required")

    headers = build_headers(token)
    headers["ConsistencyLevel"] = "eventual"

    # Build search query based on exact_match parameter
    if exact_match:
        search_query = f"subject eq '{subject}'"
    else:
        search_query = f"contains(subject, '{subject}')"

    # Handle folder filtering
    if folder_to_search == "inbox":
        inbox_folder_id = _get_inbox_folder_id(token)
        search_query = f"{search_query} AND parentFolderId eq '{inbox_folder_id}'"
    elif folder_to_search:
        folders = list_folders(token).result
        folder_found = _find_folder(folders, folder_to_search)
        if folder_found is None:
            raise ActionError(f"Folder '{folder_to_search}' not found.")
        folder_to_search_id = folder_found["id"]
        search_query = f"{search_query} AND parentFolderId eq '{folder_to_search_id}'"
    else:
        # If no folder is provided, search in all folders except 'Sent Items'
        folders = list_folders(token).result
        folder_found = _find_folder(folders, "Sent Items")
        send_items_folder_id = folder_found["id"]
        search_query = f"{search_query} AND parentFolderId ne '{send_items_folder_id}'"

    # Search for emails with the subject
    query = f"/me/messages?$top=1&$filter={search_query}"
    messages_result = send_request(
        "get",
        query,
        "search emails by subject",
        headers=headers,
    )

    messages = messages_result.get("value", [])
    if not messages:
        raise ActionError(f"No email found with subject containing '{subject}'")

    # Get the first matching email
    message = messages[0]
    email_id = message["id"]

    # Get full email details
    full_message = send_request(
        "get",
        f"/me/messages/{email_id}",
        "get email by subject",
        headers=headers,
    )

    if show_full_body:
        full_message.pop("bodyPreview", None)
    else:
        full_message.pop("body", None)

    if save_attachments:
        # Fetch attachments separately
        attachments_response = send_request(
            "get",
            f"/me/messages/{email_id}/attachments",
            "get email attachments",
            headers=headers,
        )
        attachments = attachments_response.get("value", [])

        full_message["attachments"] = []
        for attachment in attachments:
            attachment_name = attachment["name"]
            attachment_content = attachment["contentBytes"]

            # Create a temporary file to save the attachment
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{attachment_name}") as temp_file:
                temp_file.write(base64.b64decode(attachment_content))
                temp_file_path = temp_file.name

            # Attach the file to the chat using sema4ai.actions.chat
            attach_file(temp_file_path, name=attachment_name)
            full_message["attachments"].append(attachment_name)

    return Response(result=full_message)


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


@action
def flag_email(
    token: OAuth2Secret[Literal["microsoft"], list[Literal["Mail.ReadWrite"]]],
    email_id: str,
    flag: MessageFlag,
) -> Response:
    """
    Flag email by setting the flag status.

    Possible flag statuses are:
    - 'notFlagged'
    - 'flagged'
    - 'complete'

    Args:
        token: The OAuth2 token for authentication.
        email_id: The unique identifier of the email to flag.
        flag: The flag status to set.

    Returns:
        Response indicating the result of the flagging operation.
    """
    headers = build_headers(token)
    data = {
        "flag": {
            # "completedDateTime": {"@odata.type": "microsoft.graph.dateTimeTimeZone"},
            # "dueDateTime": {"@odata.type": "microsoft.graph.dateTimeTimeZone"},
            "flagStatus": flag.flag_status
            # "startDateTime": {"@odata.type": "microsoft.graph.dateTimeTimeZone"},
        }
    }
    flag_response = send_request(
        "patch",
        f"/me/messages/{email_id}",
        "flag email",
        data=data,
        headers=headers,
    )
    return Response(result=flag_response)


@action(is_consequential=True)
def add_category(
    token: OAuth2Secret[Literal["microsoft"], list[Literal["Mail.ReadWrite"]]],
    email_id: str,
    category: Category,
) -> Response:
    """
    Add a category to an email while preserving existing categories.
    Creates the category in master categories if it doesn't exist.

    Args:
        token: The OAuth2 token for authentication.
        email_id: The unique identifier of the email to add the category to.
        category: The category to add to the email (includes display_name and color).

    Returns:
        Response indicating the result of the category addition operation.
    """
    headers = build_headers(token)

    # 1. Creates the category if it doesn't exist - Check if category exists in master categories and create if needed
    _ensure_category_exists(token, category.display_name, headers, category.color)

    # Verify the category was created with the correct color
    category_info = _get_category_info(token, category.display_name, headers)
    if category_info and category_info.get("color", "").lower() != category.color.lower():
        print(f"Warning: Category color mismatch. Expected {category.color}, but found {category_info.get('color')}")
    else:
        print(f"Category '{category.display_name}' created successfully with color {category_info.get('color') if category_info else category.color}")

    # 2. Preserves existing categories - Get the current categories and add the new one without removing existing ones
    current_message = send_request(
        "get",
        f"/me/messages/{email_id}",
        "get email for categories",
        headers=headers,
    )

    # Get existing categories or initialize empty list
    existing_categories = current_message.get("categories", [])

    # Add the new category if it doesn't already exist (preserve existing categories)
    if category.display_name not in existing_categories:
        existing_categories.append(category.display_name)
    else:
        return Response(result=f"Category '{category.display_name}' already exists on this email")

    # Update the email with the new categories
    data = {
        "categories": existing_categories
    }

    update_response = send_request(
        "patch",
        f"/me/messages/{email_id}",
        "add category to email",
        data=data,
        headers=headers,
    )
    return Response(result=update_response)


@action(is_consequential=True)
def remove_category(
    token: OAuth2Secret[Literal["microsoft"], list[Literal["Mail.ReadWrite"]]],
    email_id: str,
    category_name: str,
) -> Response:
    """
    Remove a category from an email.

    Args:
        token: The OAuth2 token for authentication.
        email_id: The unique identifier of the email to remove the category from.
        category_name: The name of the category to remove.

    Returns:
        Response indicating the result of the category removal operation.
    """
    headers = build_headers(token)

    # First, get the current categories of the email
    current_message = send_request(
        "get",
        f"/me/messages/{email_id}",
        "get email for categories",
        headers=headers,
    )

    # Get existing categories or initialize empty list
    # Categories are returned as an array of strings (category names)
    existing_categories = current_message.get("categories", [])

    # Check if category exists and remove it
    if category_name not in existing_categories:
        raise ActionError(f"Category '{category_name}' not found on this email")

    # Remove the category from the list
    updated_categories = [cat for cat in existing_categories if cat != category_name]

    # Update the email with the updated categories
    data = {
        "categories": updated_categories
    }

    update_response = send_request(
        "patch",
        f"/me/messages/{email_id}",
        "remove category from email",
        data=data,
        headers=headers,
    )
    return Response(result=update_response)


@action
def list_master_categories(
    token: OAuth2Secret[Literal["microsoft"], list[Literal["Mail.ReadWrite"]]],
) -> Response:
    """
    List all master categories with their colors.

    Args:
        token: The OAuth2 token for authentication.

    Returns:
        Response containing the list of master categories with their colors.
    """
    headers = build_headers(token)

    try:
        response = send_request(
            "get",
            "/me/outlook/masterCategories",
            "list master categories",
            headers=headers,
        )
        if response and "value" in response:
            categories = response["value"]
            return Response(result={
                "categories": categories,
                "count": len(categories)
            })
        else:
            return Response(result={"categories": [], "count": 0})
    except Exception as e:
        raise ActionError(f"Error listing master categories: {str(e)}")
