from dotenv import load_dotenv
from msal import ConfidentialClientApplication
import json
from pathlib import Path
import os
import requests
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
import webbrowser

BASE_GRAPH_URL = "https://graph.microsoft.com/v1.0"

devdata_directory = Path(__file__).absolute().parent
load_dotenv(devdata_directory / ".env")
# TODO. Collect all scopes from actions


class AuthorizationHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        if "code" in query_params:
            auth_code = query_params["code"][0]
            self.server.auth_code = auth_code
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"Authentication successful! You can close this window.")
        else:
            self.send_response(400)
            self.end_headers()


def get_auth_code(auth_url):
    webbrowser.open(auth_url)
    httpd = HTTPServer(("localhost", 4567), AuthorizationHandler)
    httpd.handle_request()
    return httpd.auth_code


def get_microsoft_token() -> str:
    client_id = os.getenv("MICROSOFT_CLIENT_ID")
    tenant_id = os.getenv("MICROSOFT_TENANT_ID")
    client_secret = os.getenv("MICROSOFT_CLIENT_SECRET")
    scopes = os.getenv("MICROSOFT_SCOPES")

    redirect_uri = os.getenv("MICROSOFT_REDIRECT_URI", "http://localhost:5000/callback")
    app = ConfidentialClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        client_credential=client_secret,
    )
    scopes = scopes.split(",")
    auth_url = app.get_authorization_request_url(scopes, redirect_uri=redirect_uri)
    auth_code = get_auth_code(auth_url)
    result = app.acquire_token_by_authorization_code(
        auth_code, scopes=scopes, redirect_uri=redirect_uri
    )

    if "access_token" in result:
        access_token = result["access_token"]
        # # Update the "access_token" in all the json files in devdata directory
        # for file in os.listdir(devdata_directory):
        #     if file.endswith(".json"):
        #         file_path = devdata_directory / file
        #         with open(file_path, "r+") as json_file:
        #             data = json.load(json_file)
        #             if "token" in data and "access_token" in data["token"]:
        #                 data["token"]["access_token"] = access_token
        #                 json_file.seek(0)
        #                 json.dump(data, json_file, indent=4)
        #                 json_file.truncate()
        return access_token
    else:
        print(
            f"Error acquiring token: {result.get('error')}, {result.get('error_description')}"
        )
        return None


def build_headers(access_token):
    return {
        "Authorization": f"Bearer {access_token}",
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
            raise ValueError(f"Error on '{req_name}': {response.text}")
        # Check if the response has JSON content
        if "application/json" in response.headers.get("Content-Type", ""):
            return response.json()
        return None
    except Exception as e:
        raise ValueError(f"Error on '{req_name}': {str(e)}")


def _get_me(token):
    # scope required: User.Read
    headers = build_headers(token)
    return send_request("get", "/me", "get me", headers=headers)


if __name__ == "__main__":
    access_token = get_microsoft_token()
    if access_token:
        print(f"Access token: {access_token}")
        headers = build_headers(access_token)
        response = _get_me(access_token)
        print(response)
