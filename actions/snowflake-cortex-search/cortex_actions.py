import snowflake.core.cortex.inference_service._generated.models as inference_models
from sema4ai.actions import Response, Secret, action
from snowflake.core import Root
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
        warehouse=warehouse.value.upper(),
        database=database.value.upper(),
        schema=schema.value.upper(),
        numeric_args=[service.value.upper()],
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
    limit: int = 10,
) -> Response[list]:
    """
    Queries the cortex search service in the session state and returns a list of results.

    Args:
        query: The full-text search query to find relevant content. This is for semantic search only 
               and should NOT contain filter conditions. Example: "customer feedback about returns"
        warehouse: Your Snowflake virtual warehouse to use for queries
        database: Your Snowflake database to use for queries
        schema: Your Snowflake schema to use for queries
        service: The name of the Cortex Search service to use
        columns: The columns to return. These columns must be based on the columns returned by cortex_get_search_specification.
        filter: Dictionary specifying filter conditions using Snowflake Cortex Search syntax. Only use columns that are part of the attribute_columns returned by cortex_get_search_specification.
            Must use specific operators:
            - "@eq": Equality filter. Example: {"@eq": {"COLUMN_NAME": "value"}}
            - "@contains": Array contains filter. Example: {"@contains": {"ARRAY_COLUMN": "value"}}
            - "@gte": Greater than or equal. Example: {"@gte": {"NUMERIC_COLUMN": 10}}
            - "@lte": Less than or equal. Example: {"@lte": {"NUMERIC_COLUMN": 100}}
            
            Logical operators can combine conditions:
            - "@and": Example: {"@and": [{"@eq": {"COL1": "val1"}}, {"@eq": {"COL2": "val2"}}]}
            - "@or": Example: {"@or": [{"@eq": {"COL1": "val1"}}, {"@eq": {"COL1": "val2"}}]}
            - "@not": Example: {"@not": {"@eq": {"COL1": "val1"}}}
        limit: The limit to apply, optional, defaults to 10

    Returns:
        The results of the query.
    """
    with get_snowflake_connection(
        warehouse=warehouse.value.upper(), database=database.value.upper(), schema=schema.value.upper()
    ) as conn:
        cortex_search_service = (
            Root(conn)
            .databases[database.value.upper()]
            .schemas[schema.value.upper()]
            .cortex_search_services[service.value]
        )

        context_documents = cortex_search_service.search(
            query, columns=columns or [], filter=filter or {}, limit=limit
        )
        return Response(result=context_documents.results)
