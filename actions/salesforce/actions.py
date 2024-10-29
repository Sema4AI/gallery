import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from models import SalesforceResponse
from sema4ai.actions import Response, Secret, action

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")


@action
def query_data(
    query: str,
    access_token: Secret = Secret.model_validate(os.getenv("ACCESS_TOKEN", "")),
    domain: Secret = Secret.model_validate(os.getenv("DOMAIN", "")),
) -> Response[SalesforceResponse]:
    """Runs a Salesforce Object Query Language (SOQL) to search Salesforce data for specific information.

    This endpoint should be used to read data from Salesforce.

    Args:
        query: SOQL query to execute
        access_token: access token to make the request
        domain: Salesforce domain

    Returns:
        Objects that matched the search query.
    """
    url = f"{domain.value}/services/data/v62.0/query/"
    headers = {
        "Authorization": f"Bearer {access_token.value}",
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers, params={"q": query})
    response.raise_for_status()

    return Response(result=SalesforceResponse(**response.json()))
