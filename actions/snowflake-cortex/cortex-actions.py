# Import python packages
import json
import requests
from sema4ai.actions import action
from snowflake.core import Root

from utils import execute_query, get_snowflake_connection, is_running_in_spcs
import os

@action
def cortex_get_search_specification(warehouse: str, database: str, schema: str, service: str) -> list:
    """
    Returns the name of the search column and a list of the names of the attribute columns
    for the provided cortex search serice

    Args:
        warehouse: The warehouse to use.
        database: The database to use.
        schema: The schema to use.
        service: The service to use.

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
    result = execute_query(query=query, warehouse=warehouse, database=database, schema=schema, numeric_args=[service])
    return result

@action
def cortex_search(query: str, warehouse: str, database: str, schema: str, service: str,
                  columns: list | None = None, filter: dict | None = None, limit: int = 5) -> str:
    """
    Queries the cortex search service in the session state and returns a list of results

    Args:
        query: The query to execute
        warehouse: The warehouse to use
        database: The database to use
        schema: The schema to use
        service: The service to use
        columns: The columns to return, optional, defaults to None
        filter: The filter to apply, optional, defaults to None
        limit: The limit to apply, optional, defaults to 5

    Returns:
        The results of the query as a JSON string
    """
    try:
        with get_snowflake_connection(warehouse=warehouse, database=database, schema=schema) as conn:
            cortex_search_service = (
                Root(conn)
                .databases[database]
                .schemas[schema]
                .cortex_search_services[service]
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
def cortex_analyst_message(semantic_model_file: str, message: str) -> str:
    """
    Sends a message to the Cortex Analyst.

    Args:
        semantic_model_file: The semantic model file to use.
        message: The message to send to the Cortex Analyst.

    Returns:
        The response from the Cortex Analyst as a JSON string.
    """
    with get_snowflake_connection() as conn:
        request_body = {
            "timeout": 50000,
            "messages": [{"role": "user", "content": [{"type": "text", "text": message}]}],
            "semantic_model_file": semantic_model_file
        }

        token_type = "KEYPAIR_JWT"
        base_url = None
        url = "/analyst/message"
        token = None
        try:   
            if (is_running_in_spcs()):
                snowflake_account   = os.getenv("SNOWFLAKE_ACCOUNT")
                snowflake_host = os.getenv("SNOWFLAKE_HOST")
                if snowflake_host.startswith("snowflake."):
                    snowflake_host = snowflake_host.replace("snowflake", snowflake_account.lower().replace("_", "-"), 1)
                base_url = f"https://{snowflake_host}/api/v2/cortex"
                with open("/snowflake/session/token", "r") as f:
                    token = f.read().strip()
                token_type = "OAUTH"
            else:
                base_url = f"https://{conn.account}.snowflakecomputing.com/api/v2/cortex"
                token_type = "KEYPAIR_JWT"
                token = conn.auth_class._jwt_token

            headers = {
                "Authorization": f"Bearer {token}",
                "X-Snowflake-Authorization-Token-Type": token_type,
                "Content-Type": "application/json"
            }
            response = requests.post(f'{base_url}{url}', headers=headers, json=request_body, verify=False)
            return response.text
        except Exception as e:
            return json.dumps({"error": str(e)})
