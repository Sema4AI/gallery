from dotenv import load_dotenv
from msal import ConfidentialClientApplication
import json
from pathlib import Path
import os
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
import webbrowser


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
    httpd = HTTPServer(("localhost", 5000), AuthorizationHandler)
    httpd.handle_request()
    return httpd.auth_code


def get_microsoft_token() -> str:
    client_id = os.getenv("MICROSOFT_CLIENT_ID")
    tenant_id = os.getenv("MICROSOFT_TENANT_ID")
    client_secret = os.getenv("MICROSOFT_CLIENT_SECRET")
    scopes = os.getenv("MICROSOFT_SCOPES")

    redirect_uri = "http://localhost:5000/callback"
    app = ConfidentialClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        client_credential=client_secret,
    )
    scopes = scopes.split(",")
    auth_url = app.get_authorization_request_url(scopes, redirect_uri=redirect_uri)
    print(f"Authorization URL: {auth_url}")
    auth_code = get_auth_code(auth_url)
    result = app.acquire_token_by_authorization_code(
        auth_code, scopes=scopes, redirect_uri=redirect_uri
    )

    if "access_token" in result:
        access_token = result["access_token"]
        # Update the "access_token" in all the json files in devdata directory
        for file in os.listdir(devdata_directory):
            if file.endswith(".json"):
                file_path = devdata_directory / file
                with open(file_path, "r+") as json_file:
                    data = json.load(json_file)
                    if "token" in data and "access_token" in data["token"]:
                        data["token"]["access_token"] = access_token
                        json_file.seek(0)
                        json.dump(data, json_file, indent=4)
                        json_file.truncate()
    else:
        print(
            f"Error acquiring token: {result.get('error')}, {result.get('error_description')}"
        )


if __name__ == "__main__":
    get_microsoft_token()
