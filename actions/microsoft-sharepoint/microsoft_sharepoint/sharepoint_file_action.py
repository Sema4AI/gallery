"""Set of actions operating on Sharepoint files,

Currently supporting:
- Downloading file(s) from the Sharepoint
- Upload a file to the Sharepoint site
- Searching files in the Sharepoint
"""
from typing import Literal

import sema4ai_http
from microsoft_sharepoint.models import File, FileList, Location, SiteIdentifier
from microsoft_sharepoint.sharepoint_site_action import (
    get_sharepoint_site,
    search_for_site,
)
from microsoft_sharepoint.support import (
    BASE_GRAPH_URL,
    build_headers,
    send_request,
)
from sema4ai.actions import ActionError, OAuth2Secret, Response, action, chat

@action(is_consequential=False)
def download_sharepoint_file(
    filelist: FileList,
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Files.Read"]],
    ],
    site_id: SiteIdentifier = SiteIdentifier(value=""),
    attach: bool = False,
) -> Response[list[str]]:
    """
    Download file(s) from the Sharepoint. Allows use of file_id or name. If file_id is given, it is used directly. If only name is given, a search is performed.

    Args:
        filelist: file or files (FileList) with at least file_id or name
        token: OAuth2 token to use for the operation
        site_id: SiteIdentifier for the SharePoint site (can be a plain name like 'me', 'my files', a site name, or a full site ID).
        attach: whether to download all files matching the search criteria

    Returns:
        List of downloaded files and their locations
    """
    headers = build_headers(token)
    headers["Content-Type"] = "application/octet-stream"
    downloaded_files = []

    files = filelist.files if isinstance(filelist, FileList) else [filelist]
    for afile in files:
        # Use file_id if present
        file_id = getattr(afile, "file_id", None) or afile.file.get("id") or ""
        name = getattr(afile, "name", None) or afile.file.get("name") or ""
        fileinfo_data = afile.file if hasattr(afile, "file") else afile
        parent_ref = fileinfo_data.get("parentReference", {})
        # Use the value from SiteIdentifier
        resolved_site_id = parent_ref.get("siteId", "") or site_id.value
        drive_type = parent_ref.get("driveType", "")

        if file_id:
            # Robust endpoint selection
            if drive_type == "personal":
                download_file_url = f"{BASE_GRAPH_URL}/me/drive/items/{file_id}/content"
            elif resolved_site_id:
                download_file_url = f"{BASE_GRAPH_URL}/sites/{resolved_site_id}/drive/items/{file_id}/content"
            else:
                # If both site_id and drive_type are missing, assume OneDrive
                download_file_url = f"{BASE_GRAPH_URL}/me/drive/items/{file_id}/content"
            item_file_name = name or fileinfo_data.get("name", file_id)
            download_r = sema4ai_http.get(download_file_url, headers=headers)
            if attach:
                if not isinstance(download_r.data, bytes):
                    raise ActionError(f"Downloaded content for '{item_file_name}' is not bytes. Response: {download_r.data}")
                chat.attach_file_content(name=item_file_name, data=download_r.data)
            downloaded_files.append(item_file_name)
        elif name:
            # Search for the file by name
            from microsoft_sharepoint.sharepoint_file_action import search_sharepoint_files
            search_resp = search_sharepoint_files(search_text=name, token=token, site_id=resolved_site_id)
            found_files = [f for f in search_resp.result.files if (getattr(f, "name", None) or f.file.get("name")) == name]
            if not found_files:
                raise ActionError(f"File with name '{name}' not found.")
            for found in found_files:
                found_fileinfo = found.file if hasattr(found, "file") else found
                found_file_id = getattr(found, "file_id", None) or found_fileinfo.get("id")
                found_parent_ref = found_fileinfo.get("parentReference", {})
                found_site_id = found_parent_ref.get("siteId", "") or resolved_site_id
                found_drive_type = found_parent_ref.get("driveType", "")
                # Robust endpoint selection for found files
                if found_drive_type == "personal":
                    download_file_url = f"{BASE_GRAPH_URL}/me/drive/items/{found_file_id}/content"
                elif found_site_id:
                    download_file_url = f"{BASE_GRAPH_URL}/sites/{found_site_id}/drive/items/{found_file_id}/content"
                else:
                    download_file_url = f"{BASE_GRAPH_URL}/me/drive/items/{found_file_id}/content"
                item_file_name = getattr(found, "name", None) or found_fileinfo.get("name", found_file_id)
                download_r = sema4ai_http.get(download_file_url, headers=headers)
                if attach:
                    if not isinstance(download_r.data, bytes):
                        raise ActionError(f"Downloaded content for '{item_file_name}' is not bytes. Response: {download_r.data}")
                    chat.attach_file_content(name=item_file_name, data=download_r.data)
                downloaded_files.append(item_file_name)
        else:
            raise ActionError("Each file must have at least a file_id or name.")
    return Response(result=downloaded_files)


@action
def search_sharepoint_files(
    search_text: str,
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Files.Read.All"]],
    ],
    site_id: SiteIdentifier = SiteIdentifier(value=""),
) -> Response[FileList]:
    """
    Search files in the Sharepoint site.

    Args:
        site_id: SiteIdentifier for the SharePoint site (can be a plain name like 'me', 'my files', a site name, or a full site ID), or empty to search in all sites
        search_text: text to search for, use "*" to search for all files
        token: OAuth2 token to use for the operation

    Returns:
        List of files matching the search criteria
    """
    headers = build_headers(token)
    if len(search_text) == 0:
        raise ActionError("Search text cannot be empty")
    search_payload = {
        "requests": [
            {
                "entityTypes": ["driveItem"],
                "query": {"queryString": search_text},
            }
        ]
    }
    site_id_value = site_id.value
    if site_id_value.lower() in ["me", "my files", "myfiles"]:
        search_payload["requests"][0]["scopes"] = ["/me/drive"]
    elif site_id_value != "":
        search_payload["requests"][0]["scopes"] = [f"/sites/{site_id_value}/drive"]
    search_results = send_request(
        "post", "/search/query", "Search files", headers=headers, data=search_payload
    )
    files = []
    if search_results["value"][0]["hitsContainers"][0]["total"] > 0:
        for result in search_results["value"][0]["hitsContainers"][0]["hits"]:
            parent = result["resource"]["parentReference"]
            id_field = parent["siteId"]
            resolved_site_id = id_field.split(",")[1]
            site_response = get_sharepoint_site(site_id=SiteIdentifier(value=resolved_site_id), token=token)
            site_name = site_response.result["displayName"]
            filename = result["resource"]["name"]
            fileid = result["resource"]["id"]
            result["resource"].pop("id")
            result["resource"].pop("name")
            files.append(
                File(
                    file_id=fileid,
                    name=filename,
                    file=result["resource"],
                    location=Location(name=site_name, url=result["resource"]["webUrl"]),
                )
            )
    return Response(result=FileList(files=files))


@action
def upload_file_to_sharepoint(
    filename: str,
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Files.ReadWrite"]],
    ],
    site_id: SiteIdentifier = SiteIdentifier(value="me"),
) -> Response[str]:
    """
    Upload a file to the Sharepoint site.

    Args:
        site_id: SiteIdentifier for the SharePoint site (can be a plain name like 'me', 'my files', a site name, or a full site ID).
        filename: name of the file.
        token: OAuth2 token to use for the operation.

    Returns:
        Result of the operation
    """
    headers = build_headers(token)
    try:
        _ = chat.get_file(filename)
    except Exception as e:
        raise ActionError(f"File {filename} not found in Files: {e}")
    chat_file_content = chat.get_file_content(filename)
    filesize = len(chat_file_content)

    site_id_value = site_id.value
    if site_id_value.lower() in ["me", "my files", "myfiles"]:
        upload_url = f"{BASE_GRAPH_URL}/me/drive/root:/{filename}:/content"
        upload_session_url = (
            f"{BASE_GRAPH_URL}/me/drive/root:/{filename}:/createUploadSession"
        )
    else:
        response = search_for_site(site_id_value, token)
        sites = response.result["value"]
        if len(sites) == 0:
            raise ActionError(f"Site {site_id_value} not found")
        elif len(sites) > 1:
            raise ActionError(f"Multiple sites with name {site_id_value} found")
        id_field = sites[0]["id"]
        resolved_site_id = id_field.split(",")[1]
        upload_url = (
            f"{BASE_GRAPH_URL}/sites/{resolved_site_id}/drive/root:/{filename}:/content"
        )
        upload_session_url = f"{BASE_GRAPH_URL}/sites/{resolved_site_id}/drive/root:/{filename}:/createUploadSession"
    headers.update({"Content-Type": "application/octet-stream"})
    if filesize <= 4000000:  # 4MB
        upload_response = sema4ai_http.put(
            upload_url, headers=headers, body=chat_file_content
        )
        if upload_response.status_code in [200, 201]:
            web_url_parts = upload_response.json()["webUrl"].split("/")[:-1]
            web_url = "/".join(web_url_parts)
            return Response(
                result=f"File uploaded successfully and can be found at {web_url}"
            )
        else:
            raise ActionError(f"Failed to upload file: {upload_response.text}")
    else:
        # upload bigger file in session
        upload_session_response = sema4ai_http.post(upload_session_url, headers=headers)
        upload_url = upload_session_response.json()["uploadUrl"]
        chunk_size = 327680  # 320KB
        i = 0
        while True:
            start = i * chunk_size
            end = start + chunk_size
            chunk_data = chat_file_content[start:end]
            if not chunk_data:
                break
            chunk_start = start
            chunk_end = start + len(chunk_data) - 1
            headers.update({"Content-Range": f"bytes {chunk_start}-{chunk_end}/{filesize}"})
            chunk_response = sema4ai_http.put(
                upload_url, headers=headers, body=chunk_data
            )
            if not chunk_response.ok():
                raise ActionError(f"Failed to upload file: {chunk_response.text}")
            i += 1
        return Response(result="File uploaded successfully")
