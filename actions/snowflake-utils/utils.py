from contextlib import closing, contextmanager
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
        try:
            if warehouse:
                cursor.execute(f'USE WAREHOUSE "{warehouse.upper()}"')
        except snowflake.connector.errors.ProgrammingError as e:
            raise ValueError(
                f"Failed to use warehouse '{warehouse}'. "
                f"Error: {str(e)}\n"
                f"Common issues:\n"
                f"  - Warehouse does not exist\n"
                f"  - Insufficient permissions to use this warehouse\n"
                f"  - Warehouse name is misspelled"
            ) from e
        
        try:
            if database:
                cursor.execute(f'USE DATABASE "{database.upper()}"')
        except snowflake.connector.errors.ProgrammingError as e:
            raise ValueError(
                f"Failed to use database '{database}'. "
                f"Error: {str(e)}\n"
                f"Common issues:\n"
                f"  - Database does not exist\n"
                f"  - Insufficient permissions to access this database\n"
                f"  - Database name is misspelled"
            ) from e
        
        try:
            if schema:
                cursor.execute(f'USE SCHEMA "{schema.upper()}"')
        except snowflake.connector.errors.ProgrammingError as e:
            raise ValueError(
                f"Failed to use schema '{schema}'. "
                f"Error: {str(e)}\n"
                f"Common issues:\n"
                f"  - Schema does not exist\n"
                f"  - Insufficient permissions to access this schema\n"
                f"  - Schema name is misspelled"
            ) from e

        try:
            cursor.execute(query, numeric_args)
        except snowflake.connector.errors.ProgrammingError as e:
            raise ValueError(
                f"Failed to execute query. "
                f"Error: {str(e)}\n"
                f"Query: {query}\n"
                f"Common issues:\n"
                f"  - Table or view does not exist\n"
                f"  - SQL syntax error\n"
                f"  - Insufficient permissions to access the objects\n"
                f"  - Object names are misspelled"
            ) from e

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
