from typing import Literal

import requests
from models import SalesforceResponse
from sema4ai.actions import OAuth2Secret, Response, action


@action
def query_data(
    query: str,
    credentials: OAuth2Secret[
        Literal["salesforce"], list[Literal["api", "refresh_token"]]
    ],
) -> Response[SalesforceResponse]:
    """Runs a Salesforce Object Query Language (SOQL) to search Salesforce data for specific information.

    This endpoint should be used to read data from Salesforce.

    Args:
        query: SOQL query to execute
        credentials: JSON containing the OAuth2 credentials.

    Returns:
        Objects that matched the search query.
    """
    url = f"{credentials.metadata['server']}/services/data/v62.0/query/"
    headers = {
        "Authorization": f"Bearer {credentials.access_token}",
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers, params={"q": query})
    response.raise_for_status()

    return Response(result=SalesforceResponse(**response.json()))
