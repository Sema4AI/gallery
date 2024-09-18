import base64
import requests


from sema4ai.actions import ActionError
from pathlib import Path
from microsoft_mail.models import Email

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
    :return: JSON response data if available.
    :raises: RequestException for any request failures.
    """
    try:
        query_url = url if BASE_GRAPH_URL in url else f"{BASE_GRAPH_URL}{url}"
        response = requests.request(
            method, query_url, headers=headers, json=data, params=params
        )
        response.raise_for_status()  # Raises a HTTPError for bad responses
        if response.status_code not in [200, 201, 202, 204]:
            raise ActionError(f"Error on '{req_name}': {response.text}")
        # Check if the response has JSON content
        if "application/json" in response.headers.get("Content-Type", ""):
            return response.json()
        return None
    except Exception as e:
        raise ActionError(f"Error on '{req_name}': {str(e)}")


def _get_me(token):
    headers = build_headers(token)
    return send_request("get", "/me", "get me", headers=headers)


def _read_file(attachment):
    file_content = ""
    with open(attachment.filepath, "rb") as file:
        file_content = file.read()
    return base64.b64encode(file_content).decode("utf-8")


def _base64_attachment(attachment):
    c_bytes = (
        attachment.content_bytes if attachment.content_bytes else _read_file(attachment)
    )
    if attachment.filepath != "" and (attachment.name is None or attachment.name == ""):
        attachment.name = Path(attachment.filepath).name

    data = {
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": (
            attachment.name
            if attachment.name and len(attachment.name) > 0
            else "UNNAMED_ATTACHMENT"
        ),
        "contentBytes": c_bytes,
    }
    return data


def _set_message_data(
    message: Email, html_content: bool, existing_message=None
) -> dict:
    data = existing_message or {}
    if message.subject:
        data["subject"] = message.subject
    if message.body and not existing_message:
        data["body"] = {
            "contentType": "HTML" if html_content else "Text",
            "content": message.body,
        }
    if message.to and len(message.to) > 0:
        data["toRecipients"] = [
            {
                "emailAddress": {
                    "address": recipient.address,
                    "name": recipient.name if recipient.name else recipient.address,
                }
            }
            for recipient in message.to
        ]
    if message.importance:
        data["importance"] = message.importance
    if message.cc and len(message.cc) > 0:
        data["ccRecipients"] = [
            {
                "emailAddress": {
                    "address": recipient.address,
                    "name": recipient.name if recipient.name else recipient.address,
                }
            }
            for recipient in message.cc
        ]
    if message.bcc and len(message.bcc) > 0:
        data["bccRecipients"] = [
            {
                "emailAddress": {
                    "address": recipient.address,
                    "name": recipient.name if recipient.name else recipient.address,
                }
            }
            for recipient in message.bcc
        ]
    if message.reply_to:
        data["replyTo"] = {
            "emailAddress": {
                "address": message.reply_to.address,
                "name": (
                    message.reply_to.name
                    if message.reply_to.name
                    else message.reply_to.name.address
                ),
            }
        }
    if "toRecipients" in data.keys() and existing_message:
        data["toRecipients"] = data["toRecipients"].extend(existing_message["sender"])
    return data


def _get_folder_structure(token, account, folder_id=None):
    headers = build_headers(token)
    if folder_id:
        url = f"/users/{account}/mailFolders/{folder_id}/childFolders"
    else:
        url = f"/users/{account}/mailFolders"

    response = send_request("get", url, "get folder structure", headers=headers)
    folders = response.get("value", [])

    folder_structure = []
    for folder in folders:
        subfolders = _get_folder_structure(token, account, folder["id"])
        folder_structure.append(
            {
                "name": folder["displayName"],
                "id": folder["id"],
                "childFolders": subfolders,
            }
        )

    return folder_structure


def _delete_subscription(subscription_id: str, headers: dict):
    send_request(
        "delete",
        f"/subscriptions/{subscription_id}",
        "delete subscription",
        headers=headers,
    )


def _find_folder(folders, folder_to_search):
    for folder in folders:
        if folder["name"].lower() == folder_to_search.lower():
            return folder
        elif (
            "sent" in folder_to_search.lower()
            and folder["name"].replace(" ", "").lower() == "sentitems"
        ):
            return folder
        # If the folder has child folders, search within them recursively
        if "childFolders" in folder and len(folder["childFolders"]) > 0:
            result = _find_folder(folder["childFolders"], folder_to_search)
            if result:
                return result
    return None
