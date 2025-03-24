from sema4ai.actions import Response, Secret, action
from utils import execute_query


@action
def snowflake_execute_query(
    query: str,
    warehouse: Secret,
    database: Secret,
    schema: Secret,
    numeric_args: list = None,
) -> Response[list]:
    """
    Executes a specific query.

    Args:
        query: The query to execute.
        database: Your Snowflake database to use for queries.
        schema: Your Snowflake schema to use for queries.
        warehouse: Your Snowflake virtual warehouse to use for queries.
        numeric_args: A list of numeric arguments to pass to the query.

    Returns:
        The results of the query as a JSON string.
    """

    return Response(
        result=execute_query(
            query=query,
            warehouse=warehouse.value,
            database=database.value,
            schema=schema.value,
            numeric_args=numeric_args,
        )
    )
