import json
import requests
import os

from sema4ai.actions import action, Secret
from snowflake.core import Root
from utils import execute_query, get_snowflake_connection, is_running_in_spcs


@action
def cortex_get_search_specification(
    warehouse: Secret, database: Secret, schema: Secret, service: Secret
) -> list:
    """
    Returns the name of the search column and a list of the names of the attribute columns
    for the provided cortex search serice

    Args:
        warehouse: Your Snowflake virtual warehouse to use for queries.
        database: Your Snowflake database to use for queries.
        schema: Your Snowflake schema to use for queries.
        service: The name of the Cortex Search service to use.

    Returns:
        The column specification as a JSON string.
    """
    query = """
        SELECT
            service_name,
            columns,
            search_column,
            attribute_columns,

        FROM
        INFORMATION_SCHEMA.CORTEX_SEARCH_SERVICES
        WHERE SERVICE_NAME = :1
    """
    result = execute_query(
        query=query,
        warehouse=warehouse.value,
        database=database.value,
        schema=schema.value,
        numeric_args=[service.value],
    )
    return result


@action
def cortex_search(
    query: str,
    warehouse: Secret,
    database: Secret,
    schema: Secret,
    service: Secret,
    columns: list,
    filter: dict | None = None,
    limit: int = 5,
) -> str:
    """
    Queries the cortex search service in the session state and returns a list of results

    Args:
        query: The query to execute
        warehouse: Your Snowflake virtual warehouse to use for queries
        database: Your Snowflake database to use for queries
        schema: Your Snowflake schema to use for queries
        service: The name of the Cortex Search service to use
        columns: The columns to return
        filter: The filter to apply, optional, defaults to None
        limit: The limit to apply, optional, defaults to 5

    Returns:
        The results of the query as a JSON string
    """
    try:
        with get_snowflake_connection(
            warehouse=warehouse.value, database=database.value, schema=schema.value
        ) as conn:
            cortex_search_service = (
                Root(conn)
                .databases[database.value]
                .schemas[schema.value]
                .cortex_search_services[service.value]
            )

            # Only pass non-None values to search
            search_args = {"query": query, "limit": limit}
            if columns is not None:
                search_args["columns"] = columns
            if filter is not None:
                search_args["filter"] = filter

            context_documents = cortex_search_service.search(**search_args)
            return json.dumps(context_documents.results)
    except Exception as e:
        return json.dumps({"error": str(e)})


@action
def cortex_analyst_message(semantic_model_file: Secret, message: str) -> str:
    """
    Sends a message to the Cortex Analyst.

    Args:
        semantic_model_file: The path to a Snowflake Stage containing the semantic model file for Cortex Analyst.
        message: The message to send to the Cortex Analyst.

    Returns:
        The response from the Cortex Analyst as a JSON string.
    """
    with get_snowflake_connection() as conn:
        request_body = {
            "timeout": 50000,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": message}]}
            ],
            "semantic_model_file": semantic_model_file.value,
        }

        token_type = "KEYPAIR_JWT"
        base_url = None
        url = "/analyst/message"
        token = None
        try:
            if is_running_in_spcs():
                snowflake_account = os.getenv("SNOWFLAKE_ACCOUNT")
                snowflake_host = os.getenv("SNOWFLAKE_HOST")
                if snowflake_host.startswith("snowflake."):
                    snowflake_host = snowflake_host.replace(
                        "snowflake", snowflake_account.lower().replace("_", "-"), 1
                    )
                base_url = f"https://{snowflake_host}/api/v2/cortex"
                with open("/snowflake/session/token", "r") as f:
                    token = f.read().strip()
                token_type = "OAUTH"
            else:
                base_url = (
                    f"https://{conn.account}.snowflakecomputing.com/api/v2/cortex"
                )
                token_type = "KEYPAIR_JWT"
                token = conn.auth_class._jwt_token

            headers = {
                "Authorization": f"Bearer {token}",
                "X-Snowflake-Authorization-Token-Type": token_type,
                "Content-Type": "application/json",
            }
            response = requests.post(
                f"{base_url}{url}", headers=headers, json=request_body, verify=False
            )
            return response.text
        except Exception as e:
            return json.dumps({"error": str(e)})
