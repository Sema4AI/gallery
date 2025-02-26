from sema4ai.actions import Response, Secret, action

from models import Column, Schema, Table, Warehouse
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


@action
def snowflake_get_warehouses() -> Response[list[Warehouse]]:
    """
    Gets the warehouses in the account.

    Returns:
        The warehouses in the account.
    """
    return Response(
        result=[
            Warehouse.model_validate(warehouse)
            for warehouse in execute_query(query="SHOW WAREHOUSES")
        ]
    )


@action
def snowflake_get_databases(warehouse: str) -> Response[list[str]]:
    """
    Returns the databases in the account.

    Args:
        warehouse: The warehouse to use.

    Returns:
        The databases in the account.
    """

    sql = """
    select database_name from SNOWFLAKE.information_schema.databases
    order by database_name
    """
    response = execute_query(query=sql, warehouse=warehouse)

    return Response(result=[row["DATABASE_NAME"] for row in response])


@action
def snowflake_get_schemas(warehouse: str, database: str) -> Response[list[Schema]]:
    """
    Get the schemas from the database.

    Args:
        warehouse: The warehouse to use.
        database: The database to get the schemas from.

    Returns:
        The schemas in the database as a JSON string.
    """

    sql = """
        SELECT schema_name, schema_owner, created, last_altered
        FROM information_schema.schemata
        WHERE catalog_name = :1
        ORDER BY schema_name;
    """
    reponse = execute_query(
        query=sql, warehouse=warehouse, database=database, numeric_args=[database]
    )

    return Response(result=[Schema.model_validate(schema) for schema in reponse])


@action
def snowflake_get_tables(
    warehouse: str, database: str, schema: str
) -> Response[list[Table]]:
    """
    Get the table names from the database.

    Args:
        warehouse: The warehouse to use.
        database: The database to get the tables from.
        schema: The schema to get the tables from.

    Returns:
        The table names in the database as a JSON string.
    """
    sql = """
        SELECT table_name, table_type
        FROM information_schema.tables
        WHERE table_schema = :1
        ORDER BY table_name;
    """
    response = execute_query(
        query=sql,
        warehouse=warehouse,
        database=database,
        schema=schema,
        numeric_args=[schema],
    )

    return Response(result=[Table.model_validate(table) for table in response])


def snowflake_get_columns(
    warehouse: str, database: str, schema: str, table: str
) -> Response[list[Column]]:
    """
    Get the columns in the table.

    Args:
        warehouse: The warehouse to use.
        database: The database to get the columns from.
        schema: The schema to get the columns from.
        table: The table to get the columns from.

    Returns:
        The columns in the table as a JSON string.
    """

    sql = """
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = :1 AND table_schema = :2
    ORDER BY column_name;
    """
    response = execute_query(
        query=sql,
        warehouse=warehouse,
        database=database,
        schema=schema,
        numeric_args=[table, schema],
    )

    return Response(result=[Column.model_validate(column) for column in response])
