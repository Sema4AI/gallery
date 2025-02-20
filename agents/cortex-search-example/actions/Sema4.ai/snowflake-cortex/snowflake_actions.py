from sema4ai.actions import Response, action

from utils import execute_query

@action
def snowflake_execute_query(
    query: str,
    warehouse: str = "",
    database: str = None,
    schema: str = None,
    numeric_args: list = None,
) -> Response[list]:
    """
    Executes a specific query.

    Args:
        query: The query to execute.
        database: The database to use.
        schema: The schema to use.
        warehouse: The warehouse to use.
        numeric_args: A list of numeric arguments to pass to the query.

    Returns:
        The results of the query as a JSON string.
    """

    return Response(result=execute_query(
                query=query,
                warehouse=warehouse,
                database=database,
                schema=schema,
                numeric_args=numeric_args))
