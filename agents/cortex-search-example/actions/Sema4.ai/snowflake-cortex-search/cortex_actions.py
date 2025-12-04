from sema4ai.actions import Response, Secret, action
from snowflake.core import Root
from pydantic import BaseModel, Field
from typing import Annotated
from sema4ai.data import execute_snowflake_query, get_snowflake_connection

class CortexSearchRequest(BaseModel):
    """Request model for Cortex search operations."""
    
    query: Annotated[
        str, 
        Field(description="The full-text search query to find relevant content. This is for semantic search only and should NOT contain filter conditions. Example: 'customer feedback about returns'")
    ]
    
    columns: Annotated[
        list | None, 
        Field(
            default=None,
            description="A list of the columns to return. These columns must be based on the columns returned by cortex_get_search_specification and this must be a list."
        )
    ]
    
    filter: Annotated[
        dict | None, 
        Field(
            default=None,
            description="""Dictionary specifying filter conditions using Snowflake Cortex Search syntax. Only use columns that are part of the attribute_columns returned by cortex_get_search_specification.
            Must use specific operators:
            - "@eq": Equality filter. Example: {"@eq": {"COLUMN_NAME": "value"}}
            - "@contains": Array contains filter. Example: {"@contains": {"ARRAY_COLUMN": "value"}}
            - "@gte": Greater than or equal. Example: {"@gte": {"NUMERIC_COLUMN": 10}}
            - "@lte": Less than or equal. Example: {"@lte": {"NUMERIC_COLUMN": 100}}
            
            Logical operators can combine conditions:
            - "@and": Example: {"@and": [{"@eq": {"COL1": "val1"}}, {"@eq": {"COL2": "val2"}}]}
            - "@or": Example: {"@or": [{"@eq": {"COL1": "val1"}}, {"@eq": {"COL1": "val2"}}]}
            - "@not": Example: {"@not": {"@eq": {"COL1": "val1"}}}"""
        )
    ]
    
    limit: Annotated[
        int, 
        Field(
            default=10,
            description="The limit to apply, optional, defaults to 10"
        )
    ]

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
            attribute_columns
        FROM
        INFORMATION_SCHEMA.CORTEX_SEARCH_SERVICES
        WHERE SERVICE_NAME = :1
    """
    result = execute_snowflake_query(
        query=query,
        warehouse=warehouse.value.upper(),
        database=database.value.upper(),
        schema=schema.value.upper(),
        numeric_args=[service.value.upper()],
    )
    return Response(result=result)


@action
def cortex_search(
    query: CortexSearchRequest,
    warehouse: Secret,
    database: Secret,
    schema: Secret,
    service: Secret
) -> Response[list]:
    """
    Queries the cortex search service in the session state and returns a list of results.
    Mind the nesting of { "query": { "query": "...", "columns": [...], "filter": {...}, "limit": 10 } }
    when providing the arguments to this action. You will often need to check the results of
    cortex_get_search_specification to get the correct columns information for use in the columns argument.
    (The columns, filter, and limit are optional and can be omitted.)

    Args:
        query: The search request containing query, columns, filter, and limit parameters.
        warehouse: Your Snowflake virtual warehouse to use for queries
        database: Your Snowflake database to use for queries
        schema: Your Snowflake schema to use for queries
        service: The name of the Cortex Search service to use

    Returns:
        The results of the query.
    """

    try:
        # The request is already a validated Pydantic model
        request = query
        print(f"Received cortex search request for query: {request.query}")
        
    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        print(f"ERROR: {error_msg}")
        return Response(result=[], error=error_msg)
    
    try:
        # Handle empty string for columns by converting it to None
        validated_columns = request.columns
        if validated_columns == '':
            validated_columns = None

        with get_snowflake_connection(
            warehouse=warehouse.value.upper(), 
            database=database.value.upper(), 
            schema=schema.value.upper()
        ) as conn:
            print(f"Established Snowflake connection to {database.value.upper()}.{schema.value.upper()}")
            
            cortex_search_service = (
                Root(conn)
                .databases[database.value.upper()]
                .schemas[schema.value.upper()]
                .cortex_search_services[service.value.upper()]
            )

            context_documents = cortex_search_service.search(
                request.query, 
                columns=validated_columns or [], 
                filter=request.filter or {}, 
                limit=request.limit
            )
            
            print(f"Cortex search completed successfully. Found {len(context_documents.results)} results")
            return Response(result=context_documents.results)
            
    except Exception as conn_error:
        if "connection" in str(conn_error).lower():
            error_msg = f"Snowflake connection error: {str(conn_error)}"
            print(f"ERROR: {error_msg}")
            return Response(result=[], error=error_msg)
        elif "cortex" in str(conn_error).lower() or "search" in str(conn_error).lower():
            error_msg = f"Cortex search service error: {str(conn_error)}"
            print(f"ERROR: {error_msg}")
            return Response(result=[], error=error_msg)
        elif "warehouse" in str(conn_error).lower():
            error_msg = f"Warehouse access error: {str(conn_error)}. Check if warehouse '{warehouse.value.upper()}' is available and accessible."
            print(f"ERROR: {error_msg}")
            return Response(result=[], error=error_msg)
        elif "database" in str(conn_error).lower() or "schema" in str(conn_error).lower():
            error_msg = f"Database/Schema access error: {str(conn_error)}. Check if database '{database.value.upper()}' and schema '{schema.value.upper()}' exist and are accessible."
            print(f"ERROR: {error_msg}")
            return Response(result=[], error=error_msg)
        else:
            error_msg = f"Unexpected error during cortex search: {str(conn_error)}"
            print(f"ERROR: {error_msg}")
            return Response(result=[], error=error_msg)