"""Set of actions operating on Sharepoint files,

Currently supporting:
- Downloading file(s) from the Sharepoint
- Upload a file to the Sharepoint site
- Searching files in the Sharepoint
"""

import os
from pathlib import Path
from typing import Literal

import sema4ai_http
from microsoft_sharepoint.models import File, FileList, Location
from microsoft_sharepoint.sharepoint_site_action import (
    get_sharepoint_site,
    search_for_site,
)
from microsoft_sharepoint.support import (
    BASE_GRAPH_URL,
    build_headers,
    send_request,
)
from sema4ai.actions import ActionError, OAuth2Secret, Response, action


@action(is_consequential=False)
def download_sharepoint_file(
    filename: str,
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Files.Read"]],
    ],
    site_id: str = "",
    location: str = "",
    target_folder: str = "",
    download_all_matching: bool = False,
) -> Response[list[str]]:
    """
    Download file(s) from the Sharepoint.

    Args:
        location: "me" or "my files" or the name of the Sharepoint site or empty to search in all sites
        filename: name of the file to download (including the path)
        target_folder: folder to download the file to
        donwload_all_matching: whether to download all files matching the search criteria
        token: OAuth2 token to use for the operation

    Returns:
        List of downloaded files and their locations
    """
    headers = build_headers(token)
    site_known = True

    if location.lower() in ["me", "my files", "myfiles"]:
        download_url = f"{BASE_GRAPH_URL}/me/drive/items"
        search_location = "me"
        site_known = True
    elif site_id != "":
        site_id = site_id if len(site_id.split(",")) == 1 else site_id.split(",")[1]
        download_url = f"{BASE_GRAPH_URL}/sites/{site_id}/drive/items"
    elif location != "":
        response = search_for_site(site_name=location, token=token)
        sites = response.result["value"]
        if len(sites) == 0:
            raise ActionError(f"Site {location} not found")
        elif len(sites) > 1:
            raise ActionError(f"Multiple sites with name {location} found")
        id_field = sites[0]["id"]
        site_id = id_field.split(",")[-1]
        download_url = f"{BASE_GRAPH_URL}/sites/{site_id}/drive/items"
    else:
        download_url = f"{BASE_GRAPH_URL}/sites"
        site_known = False
        search_location = ""
    response = search_sharepoint_files(
        location=search_location, search_text=filename, token=token
    )
    files = response.result.files
    if len(files) == 0:
        raise ActionError(f"File {filename} not found")
    elif len(files) > 1 and not download_all_matching:
        filenames = "\n".join([item["name"] for item in files])
        return Response(
            result=f"Multiple files with name {filename} found\n{filenames}."
        )
    downloaded_files = []
    for afile in files:
        fileinfo = afile.file
        item_file_id = fileinfo["id"]
        item_file_name = fileinfo["name"]
        site_id = fileinfo["parentReference"]["siteId"]
        if site_known:
            download_file_url = f"{download_url}/{item_file_id}/content"
        else:
            download_file_url = f"{download_url}/{site_id}/items/{item_file_id}/content"
        download_r = sema4ai_http.get(download_file_url, headers=headers)

        if target_folder == "":
            target_folder = os.getcwd()
        filepath = Path(target_folder) / item_file_name
        with open(filepath, "wb") as f:
            f.write(download_r.content)
        downloaded_files.append(str(filepath.resolve()))
    return Response(result=downloaded_files)


@action
def search_sharepoint_files(
    search_text: str,
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Files.Read.All"]],
    ],
    location: str = "",
) -> Response[FileList]:
    """
    Search files in the Sharepoint site.

    Args:
        location: "me" or "my files" or the id of the Sharepoint site or empty to search in all sites
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
    if location.lower() in ["me", "my files", "myfiles"]:
        search_payload["requests"][0]["scopes"] = ["/me/drive"]
    elif location != "":
        search_payload["requests"][0]["scopes"] = [f"/sites/{location}/drive"]
    search_results = send_request(
        "post", "/search/query", "Search files", headers=headers, data=search_payload
    )
    files = []
    if search_results["value"][0]["hitsContainers"][0]["total"] > 0:
        for result in search_results["value"][0]["hitsContainers"][0]["hits"]:
            parent = result["resource"]["parentReference"]
            id_field = parent["siteId"]
            site_id = id_field.split(",")[1]
            site_response = get_sharepoint_site(site_id=site_id, token=token)
            site_name = site_response.result["displayName"]
            files.append(
                File(
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
    location: str = "me",
) -> Response[str]:
    """
    Upload a file to the Sharepoint site.

    Args:
        location: "me" or "my files" or the name of the Sharepoint site.
        filename: name of the file.
        token: OAuth2 token to use for the operation.

    Returns:
        Result of the operation
    """
    headers = build_headers(token)
    upload_file = Path(filename)
    filesize = os.path.getsize(upload_file)

    if location.lower() in ["me", "my files", "myfiles"]:
        upload_url = f"{BASE_GRAPH_URL}/me/drive/root:/{upload_file.name}:/content"
        upload_session_url = (
            f"{BASE_GRAPH_URL}/me/drive/root:/{upload_file.name}:/createUploadSession"
        )
    else:
        response = search_for_site(location, token)
        sites = response.result["value"]
        if len(sites) == 0:
            raise ActionError(f"Site {location} not found")
        elif len(sites) > 1:
            raise ActionError(f"Multiple sites with name {location} found")
        id_field = sites[0]["id"]
        site_id = id_field.split(",")[1]
        upload_url = (
            f"{BASE_GRAPH_URL}/sites/{site_id}/drive/root:/{upload_file.name}:/content"
        )
        upload_session_url = f"{BASE_GRAPH_URL}/sites/{site_id}/drive/root:/{upload_file.name}:/createUploadSession"
    headers.update({"Content-Type": "application/octet-stream"})
    if filesize <= 4000000:  # 4MB
        with open(filename, "rb") as file:
            file_content = file.read()
        upload_response = sema4ai_http.put(
            upload_url, headers=headers, body=file_content
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
        with open(filename, "rb") as file:
            i = 0
            while True:
                chunk_data = file.read(chunk_size)
                if not chunk_data:
                    break
                start = i * chunk_size
                end = start + len(chunk_data) - 1
                headers.update({"Content-Range": f"bytes {start}-{end}/{filesize}"})
                chunk_response = sema4ai_http.put(
                    upload_url, headers=headers, body=chunk_data
                )
                if not chunk_response.ok():
                    raise ActionError(f"Failed to upload file: {chunk_response.text}")
                i += 1
        return Response(result="File uploaded successfully")
