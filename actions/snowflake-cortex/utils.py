import os
import pandas as pd
import snowflake.connector
from pathlib import Path
from contextlib import closing, contextmanager
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

    token = None
    try:
        with open("/snowflake/session/token", "r") as f:
            token = f.read().strip()
    except Exception:
        pass

    if token:
        return snowflake.connector.connect(
            host=os.getenv("SNOWFLAKE_HOST"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            token=token,
            authenticator="oauth",
            warehouse=warehouse,
            database=database,
            schema=schema,
        )
    else:
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
    warehouse: str = "",
    database: str = None,
    schema: str = None,
    numeric_args: list = None,
) -> list:
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
            cursor.execute(f'USE WAREHOUSE "{warehouse}"')
        if database:
            cursor.execute(f'USE DATABASE "{database}"')
        if schema:
            cursor.execute(f'USE SCHEMA "{schema}"')

        cursor.execute(query, numeric_args)

        if cursor._query_result_format == "arrow":
            results = cursor.fetch_pandas_all()
            return results.where(pd.notna, None).to_dict(orient="records")
        else:
            columns = [desc[0] for desc in cursor.description]  # Extract column names
            rows = cursor.fetchall()
            result = [dict(zip(columns, row)) for row in rows]
            return result


def is_running_in_spcs() -> bool:
    """
    Returns True if the action is running in Snowpark Container Services, False otherwise.
    Args:
        None
    Returns:
        True if the action is running in Snowpark Container Services, False otherwise.
    """
    return Path("/snowflake/session/token").exists()
