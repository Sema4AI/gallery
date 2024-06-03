from google_auth_oauthlib.flow import InstalledAppFlow

from dotenv import load_dotenv
import json
import os
from pathlib import Path


devdata_directory = Path(__file__).absolute().parent / "devdata"
load_dotenv(devdata_directory / ".env")

# List of scopes
# https://developers.google.com/identity/protocols/oauth2/scopes#gmail


def do_oauth2_flow():
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.readonly",
    ]
    CLIENT_SECRETS_FILE = os.getenv("OAUTH_CLIENT_JSON")
    FLOW_BROWSER_PORT = int(os.getenv("OAUTH_FLOW_BROWSER_PORT", 8881))
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    credentials = flow.run_local_server(port=FLOW_BROWSER_PORT)
    access_token = credentials.token
    print(f"\nAccess Token: {access_token}\n")
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


if __name__ == "__main__":
    do_oauth2_flow()
