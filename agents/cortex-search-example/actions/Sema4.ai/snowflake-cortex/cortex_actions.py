import os

import requests
import snowflake.core.cortex.inference_service._generated.models as inference_models
from sema4ai.actions import Response, Secret, action
from snowflake.core import Root
from snowflake.core.cortex.lite_agent_service._generated.models import (
    AgentRunRequest,
    Message,
    Tool,
    ToolToolSpec,
)
from utils import execute_query, get_snowflake_connection, is_running_in_spcs


@action
def cortex_get_search_specification(
    warehouse: Secret, database: Secret, schema: Secret, service: Secret
) -> Response[list]:
    """
    Returns the name of the search column and a list of the names of the attribute columns
    for the provided cortex search serice.

    Args:
        warehouse: Your Snowflake virtual warehouse to use for queries.
        database: Your Snowflake database to use for queries.
        schema: Your Snowflake schema to use for queries.
        service: The name of the Cortex Search service to use.

    Returns:
        The column specification.
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
    return Response(result=result)


@action
def cortex_search(
    query: str,
    warehouse: Secret,
    database: Secret,
    schema: Secret,
    service: Secret,
    columns: list | None = None,
    filter: dict | None = None,
    limit: int = 5,
) -> Response[list]:
    """
    Queries the cortex search service in the session state and returns a list of results.

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
        The results of the query.
    """
    with get_snowflake_connection(
        warehouse=warehouse.value, database=database.value, schema=schema.value
    ) as conn:
        cortex_search_service = (
            Root(conn)
            .databases[database.value]
            .schemas[schema.value]
            .cortex_search_services[service.value]
        )

        context_documents = cortex_search_service.search(
            query, columns=columns or [], filter=filter or {}, limit=limit
        )
        return Response(result=context_documents.results)


@action
def cortex_llm_complete(model: str, prompt: str) -> Response[list]:
    """
    Completes the inference for the provided message.

    Args:
        model: The model to use
        prompt: The prompt to use

    Returns:
        List of events.
    """

    with get_snowflake_connection() as conn:
        cortex_inference = Root(conn).cortex_inference_service
        req = inference_models.CompleteRequest(
            model=model, messages=[{"role": "user", "content": prompt}]
        )

        # TODO: Add tools once they are supported
        inference_result = cortex_inference.complete(req)

        events_dict = [
            {"event": event.event, "data": event.data}
            for event in inference_result.events()
        ]

        return Response(result=events_dict)


@action
def cortex_agent_chat(
    query: str, service: Secret, semantic_model_file: Secret
) -> Response[list]:
    """
    Chat with the cortex agent.

    Args:
        query: The query to use
        service: The search service to use
        semantic_model_file: The path to a Snowflake Stage containing the semantic model file

    Returns:
        The chat result.
    """
    with get_snowflake_connection() as conn:
        cortex_agent = Root(conn).cortex_agent_service
        req = AgentRunRequest(
            model="mistral-large2",
            messages=[Message(role="user", content=[{"type": "text", "text": query}])],
            tools=[
                Tool(tool_spec=ToolToolSpec(type="cortex_search", name="search1")),
                Tool(
                    tool_spec=ToolToolSpec(
                        type="cortex_analyst_text_to_sql", name="analyst1"
                    )
                ),
            ],
            tool_resources={
                "analyst1": {"semantic_model_file": semantic_model_file.value},
                "search1": {"name": service.value},
            },
        )
        inference_result = cortex_agent.Run(req)

        events_dict = [
            {"event": event.event, "data": event.data}
            for event in inference_result.events()
        ]

        return Response(result=events_dict)


@action
def cortex_analyst_message(semantic_model_file: Secret, message: str) -> Response[dict]:
    """
    Sends a message to the Cortex Analyst.

    Args:
        semantic_model_file: The path to a Snowflake Stage containing the semantic model file.
        message: The message to send.

    Returns:
        The response from the Cortex Analyst.
    """
    with get_snowflake_connection() as conn:
        request_body = {
            "timeout": 50000,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": message}]}
            ],
            "semantic_model_file": semantic_model_file.value,
        }

        if is_running_in_spcs():
            snowflake_account = os.getenv("SNOWFLAKE_ACCOUNT")
            snowflake_host = os.getenv("SNOWFLAKE_HOST")

            if snowflake_host.startswith("snowflake."):
                snowflake_host = snowflake_host.replace(
                    "snowflake", snowflake_account.lower().replace("_", "-"), 1
                )

            base_url = f"https://{snowflake_host}/api/v2/cortex/analyst/message"
            with open("/snowflake/session/token", "r") as f:
                token = f.read().strip()
            token_type = "OAUTH"
        else:
            base_url = f"https://{conn.account}.snowflakecomputing.com/api/v2/cortex/analyst/message"
            token_type = "KEYPAIR_JWT"
            token = conn.auth_class._jwt_token

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Snowflake-Authorization-Token-Type": token_type,
            "Content-Type": "application/json",
        }
        response = requests.post(
            f"{base_url}", headers=headers, json=request_body, verify=False
        )
        response.raise_for_status()

        return Response(result=response.json())
