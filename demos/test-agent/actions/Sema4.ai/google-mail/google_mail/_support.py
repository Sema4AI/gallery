import base64
import os
import time
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import markdown
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sema4ai.actions import ActionError

from google_mail._models import Attachment, Draft, Drafts, Email


def _create_message(sender, to, subject, body, cc=None, bcc=None, attachments=None):
    message = MIMEMultipart()
    # Checking all params if they are set as this same method is used to create
    # draft messages
    if to:
        message["to"] = to
    if sender:
        message["from"] = sender
    if subject:
        message["subject"] = subject
    if cc:
        message["cc"] = cc
    if bcc:
        message["bcc"] = bcc
    if body:
        # Convert Markdown to HTML
        html_content = markdown.markdown(body)
        alternative_part = MIMEMultipart("alternative")
        plain_part = MIMEText(body, "plain")

        html_part = MIMEText(html_content, "html")
        alternative_part.attach(plain_part)
        alternative_part.attach(html_part)
        message.attach(alternative_part)
    # Attach files
    if attachments:
        for file in attachments:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(open(file, "rb").read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(file)}",
            )
            message.attach(part)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}


def _send_message(service, user_id, message):
    try:
        message = (
            service.users().messages().send(userId=user_id, body=message).execute()
        )
        return None
    except Exception as error:
        raise ActionError(f"An error occurred: {error}")


def _list_messages_with_query(service, user_id="me", query="", max_results=10):
    message_list = []
    try:
        response = (
            service.users()
            .messages()
            .list(userId=user_id, q=query, maxResults=max_results)
            .execute()
        )
        messages = response.get("messages", [])

        if not messages:
            print("No messages found.")
        else:
            for message in messages:
                msg = _get_message_by_id(service, user_id, message["id"])
                message_list.append(msg)
    except Exception as error:
        raise ActionError(f"An error occurred: {error}")
    return message_list


def _get_message_by_id(service, user_id, message_id):
    try:
        msg = (
            service.users()
            .messages()
            .get(userId=user_id, id=message_id, format="full")
            .execute()
        )
        return msg
    except Exception as error:
        raise ActionError(f"An error occurred: {error}")


def _get_message_details(message, return_content=False):
    headers = message["payload"]["headers"]
    email = Email()
    email.id_ = message["id"]
    for header in headers:
        if header["name"] == "From":
            email.from_ = header["value"]
        elif header["name"] == "To":
            email.to = header["value"]
        elif header["name"] == "Subject":
            email.subject = header["value"]
        elif header["name"] == "Date":
            email.date = header["value"]

    email.labels = message.get("labelIds", [])
    email.attachments = []
    body = ""
    html_body = ""
    for part in message["payload"].get("parts", []):
        if return_content:
            if part["mimeType"] == "text/plain" and "data" in part["body"]:
                body += base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
            elif part["mimeType"] == "text/html" and "data" in part["body"]:
                html_body += base64.urlsafe_b64decode(part["body"]["data"]).decode(
                    "utf-8"
                )
        if part["filename"]:
            attachment = Attachment()
            attachment.filename = part["filename"]
            attachment.mimetype = part["mimeType"]
            attachment.filesize = int(part["body"]["size"])
            email.attachments.append(attachment)
    # NOTE. Returning the html_body only if body is empty (for now)
    email.body = body if body else html_body
    return email


def _get_label_id(service, label_name):
    try:
        response = service.users().labels().list(userId="me").execute()
        labels = response.get("labels", [])
        for label in labels:
            if label["name"].lower() == label_name.lower():
                return label["id"]
        raise ActionError(f'Label "{label_name}" not found.')
    except Exception as error:
        raise ActionError(f"An error occurred while fetching label ID: {error}")


def _get_current_labels(service, message_id):
    try:
        message = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="metadata")
            .execute()
        )
        return message["labelIds"]
    except Exception as error:
        raise ActionError(f"An error occurred while fetching labels: {error}")


def _move_email_to_label(service, email_ids, new_label_id):
    batch_size = 10
    for i in range(0, len(email_ids), batch_size):
        batch = service.new_batch_http_request(callback=_create_batch_callback)
        for email_id in email_ids[i : i + batch_size]:
            current_labels = _get_current_labels(service, email_id)
            if new_label_id in current_labels:
                print(f"Email with ID {email_id} already has the label {new_label_id}.")
                continue
            labels_to_remove = [
                label
                for label in current_labels
                if label not in ["UNREAD", "STARRED", new_label_id]
            ]

            # Create the modify request
            modify_request = {
                "removeLabelIds": labels_to_remove,
                "addLabelIds": [new_label_id],
            }
            batch.add(
                service.users()
                .messages()
                .modify(userId="me", id=email_id, body=modify_request)
            )
        _execute_batch_with_retry(batch)


def _move_email_to_trash(service, email_ids):
    batch_size = 10
    for i in range(0, len(email_ids), batch_size):
        batch = service.new_batch_http_request(callback=_create_batch_callback)
        for email_id in email_ids[i : i + batch_size]:
            batch.add(service.users().messages().trash(userId="me", id=email_id))

        result = _execute_batch_with_retry(batch)
        print(result)


def _create_batch_callback(request_id, response, exception):
    if exception is not None:
        raise ActionError(f"An error occurred: {exception}")
    else:
        print(f"Request ID {request_id} completed successfully.")


def _execute_batch_with_retry(batch):
    max_retries = 5
    retry_delay = 1  # Start with 1 second delay
    for retry in range(max_retries):
        try:
            batch.execute()
            return
        except Exception as error:
            if hasattr(error, "resp") and error.resp.status in [429, 500, 503]:
                print(
                    f"Rate limit exceeded or server error: {error}. Retrying in {retry_delay} seconds..."
                )
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                raise ActionError(f"An error occurred: {error}")


def _get_google_service(token):
    creds = Credentials(token=token.access_token)
    service = build("gmail", "v1", credentials=creds)
    return service


def _create_draft(service, message_body):
    try:
        draft = (
            service.users()
            .drafts()
            .create(userId="me", body={"message": message_body})
            .execute()
        )
        print(f'Draft created with ID: {draft["id"]}')
        return draft["id"]
    except Exception as error:
        raise ActionError(f"An error occurred: {error}")


def _update_draft(service, draft_id, message_body):
    try:
        draft = (
            service.users()
            .drafts()
            .update(userId="me", id=draft_id, body={"message": message_body})
            .execute()
        )
        print(f"Draft with ID {draft_id} updated.")
        return draft["id"]
    except Exception as error:
        raise ActionError(f"An error occurred: {error}")


def _delete_draft(service, draft_id):
    try:
        service.users().drafts().delete(userId="me", id=draft_id).execute()
        print(f"Draft with ID {draft_id} deleted.")
    except Exception as error:
        raise ActionError(f"An error occurred: {error}")


def _send_draft(service, draft_id):
    try:
        sent_message = (
            service.users().drafts().send(userId="me", body={"id": draft_id}).execute()
        )
        print(f"Draft with ID {draft_id} sent.")
        return sent_message
    except Exception as error:
        raise ActionError(f"An error occurred: {error}")


def _get_draft_by_id(service, draft_id):
    try:
        draft = service.users().drafts().get(userId="me", id=draft_id).execute()
        print(f"Draft with ID {draft_id} found.")
        return draft
    except Exception as error:
        raise ActionError(f"An error occurred: {error}")


def _get_message_headers(email):
    headers = {
        header["name"].lower(): header["value"]
        for header in email["message"]["payload"]["headers"]
    }
    return headers


def _list_drafts(service, query=None):
    draft_list = Drafts(items=[])
    try:
        params = {"userId": "me"}
        if query:
            params["q"] = query
        results = service.users().drafts().list(**params).execute()
        drafts = results.get("drafts", [])
        for draft in drafts:
            draft_details = (
                service.users().drafts().get(userId="me", id=draft["id"]).execute()
            )
            draft_item = Draft(draft_id=draft["id"], message=draft_details)
            draft_list.items.append(draft_item)
        return draft_list
    except Exception as error:
        print(f"An error occurred: {error}")
        return None


def _extract_body(message):
    if "parts" in message["payload"]:
        for part in message["payload"]["parts"]:
            if part["mimeType"] == "text/plain":
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                return body
    return None


def _remove_labels_from_emails(service, email_ids, label_ids):
    try:
        batch_size = 10
        for i in range(0, len(email_ids), batch_size):
            batch = service.new_batch_http_request(callback=_create_batch_callback)
            for email_id in email_ids[i : i + batch_size]:
                # Create the modify request
                modify_request = {
                    "removeLabelIds": label_ids,
                }
                batch.add(
                    service.users()
                    .messages()
                    .modify(userId="me", id=email_id, body=modify_request)
                )
            _execute_batch_with_retry(batch)
    except Exception as error:
        raise ActionError(f"An error occurred while removing labels: {error}")
