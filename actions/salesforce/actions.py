import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from sema4ai.actions import Response, Secret, action

from models import SalesforceResponse

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")


def _auth_client_credentials(client_id, client_secret, domain) -> str:
    response = requests.post(
        f"{domain}/services/oauth2/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        },
    )

    response.raise_for_status()

    return response.json()["access_token"]


@action
def query_data(
    query: str,
    client_id: Secret = Secret.model_validate(os.getenv("CLIENT_ID", "")),
    client_secret: Secret = Secret.model_validate(os.getenv("CLIENT_SECRET", "")),
    domain: Secret = Secret.model_validate(os.getenv("DOMAIN", "")),
) -> Response[SalesforceResponse]:
    """Runs a Salesforce Object Query Language (SOQL) to search Salesforce data for specific information.

    This endpoint should be used to read data from Salesforce.

    Args:
        query: SOQL query to execute
        client_id: Salesforce connected app client id.
        client_secret: Salesforce connected app client secret.
        domain: Salesforce domain.

    Returns:
        Objects that matched the search query.
    """
    access_token = _auth_client_credentials(
        client_id.value, client_secret.value, domain.value
    )

    url = f"{domain.value}/services/data/v62.0/query/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers, params={"q": query})
    response.raise_for_status()

    return Response(result=SalesforceResponse(**response.json()))
