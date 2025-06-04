import os
import json
from pathlib import Path
import urllib.parse
import sema4ai_http
from dotenv import load_dotenv
from models import SalesforceResponse
from sema4ai.actions import Response, Secret, action

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")


def _auth_client_credentials(client_id, client_secret, domain_url) -> str:
    response = sema4ai_http.post(
        f"{domain_url}/services/oauth2/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        fields={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        },
        encode_multipart=False
    )

    response.raise_for_status()
    response_json = json.loads(response.text)
    return response_json["access_token"]


@action
def query_data(
    query: str,
    client_id: Secret,
    client_secret: Secret,
    domain_url: Secret,
) -> Response[SalesforceResponse]:
    """Runs a Salesforce Object Query Language (SOQL) to search Salesforce data for specific information.

    This endpoint should be used to read data from Salesforce.

    Args:
        query: SOQL query to execute
        client_id: Salesforce connected app client id.
        client_secret: Salesforce connected app client secret.
        domain_url: Salesforce domain url.

    Returns:
        Objects that matched the search query.
    """
    _client_id = client_id.value or os.getenv("CLIENT_ID", "")
    _client_secret = client_secret.value or os.getenv("CLIENT_SECRET", "")
    _domain_url = domain_url.value or os.getenv("DOMAIN_URL", "")

    access_token = _auth_client_credentials(_client_id, _client_secret, _domain_url)

    url = f"{_domain_url}/services/data/v62.0/query"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = sema4ai_http.get(url, headers=headers, fields={"q": query})
    response.raise_for_status()
    response_json = json.loads(response.text)
    return Response(result=SalesforceResponse(**response_json))
