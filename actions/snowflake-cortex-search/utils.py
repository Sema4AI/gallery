from contextlib import closing,contextmanager
from pathlib import Path

import pandas as pd
import snowflake.connector
from sema4ai.data import get_snowflake_connection_details


def _get_snowflake_connection(
    role: str = None,
    warehouse: str = None,
    database: str = None,
    schema: str = None,
) -> snowflake.connector.SnowflakeConnection:
    """
    Get a Snowflake connection based on the authentication method.

    This function determines the authentication method (SPCS or local machine)
    and constructs the appropriate connection credentials.
    """
    snowflake.connector.paramstyle = "numeric"

    config = get_snowflake_connection_details(
        role=role, warehouse=warehouse, database=database, schema=schema
    )

    return snowflake.connector.connect(**config)


@contextmanager
def get_snowflake_connection(
    warehouse: str = None, database: str = None, schema: str = None, role: str = None
):
    """Get Snowflake connection as context manager."""
    conn = None
    try:
        conn = _get_snowflake_connection(role, warehouse, database, schema)
        yield conn
    finally:
        if conn:
            conn.close()

def execute_query(
    query: str,
    warehouse: str | None = None,
    database: str | None = None,
    schema: str | None = None,
    numeric_args: list | None = None,
) -> list[dict]:
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
    numeric_args = numeric_args or []

    with get_snowflake_connection(warehouse, database, schema) as conn, closing(
        conn.cursor()
    ) as cursor:
        if warehouse:
            cursor.execute(f'USE WAREHOUSE "{warehouse.upper()}"')
        if database:
            cursor.execute(f'USE DATABASE "{database.upper()}"')
        if schema:
            cursor.execute(f'USE SCHEMA "{schema.upper()}"')

        cursor.execute(query, numeric_args)

        if cursor._query_result_format == "arrow":
            results = cursor.fetch_pandas_all()
            return (
                results.astype(object).where(pd.notnull, None).to_dict(orient="records")
            )

        else:
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            result = [dict(zip(columns, row)) for row in rows]
            return result

def is_running_in_spcs() -> bool:
    """
    Checks if the action is running in Snowpark Container Services.

    Returns:
        True if the action is running in Snowpark Container Services, False otherwise.
    """
    return Path("/snowflake/session/token").exists()
