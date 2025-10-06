import base64
import datetime
from decimal import Decimal

from sema4ai.actions import Response, Secret, action, Table
from utils import execute_query


def serialize_value(value):
    """Convert non-JSON-serializable values to JSON-compatible types.
    
    Handles all major Snowflake data types:
    - DATE, DATETIME, TIME, TIMESTAMP* → ISO format string
    - NUMBER, DECIMAL → float
    - BINARY, VARBINARY → base64 encoded string
    - VECTOR → list (from memoryview)
    - VARIANT, OBJECT → dict (already JSON-compatible)
    - ARRAY → list (already JSON-compatible)
    - GEOGRAPHY, GEOMETRY → dict/GeoJSON (already JSON-compatible)
    """
    if value is None:
        return None
    elif isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
        return value.isoformat()
    elif isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, (bytes, bytearray)):
        # BINARY/VARBINARY types - encode as base64 string
        return base64.b64encode(value).decode('ascii')
    elif isinstance(value, memoryview):
        # VECTOR type - convert to list
        return list(value)
    elif isinstance(value, (str, int, float, bool)):
        return value
    elif isinstance(value, (list, dict)):
        # ARRAY, OBJECT, VARIANT, GEOGRAPHY, GEOMETRY types
        return value
    else:
        # Fallback for any other unexpected types
        return str(value)


@action
def snowflake_execute_query(
    query: str,
    warehouse: Secret,
    database: Secret,
    schema: Secret,
    numeric_args: list = None,
    row_limit: int = 10000,
) -> Response[Table]:
    """
    Executes a specific query and returns results as a Table.

    Args:
        query: The query to execute.
        database: Your Snowflake database to use for queries.
        schema: Your Snowflake schema to use for queries.
        warehouse: Your Snowflake virtual warehouse to use for queries.
        numeric_args: A list of numeric arguments to pass to the query.
        row_limit: Maximum number of rows to return (default: 10000). 
                   Set to prevent memory issues with large result sets.
                   Consider adding LIMIT clause in your SQL for better performance.

    Returns:
        The results of the query as a Table (limited to row_limit rows).
    """

    result = execute_query(
        query=query,
        warehouse=warehouse.value,
        database=database.value,
        schema=schema.value,
        numeric_args=numeric_args,
    )
    
    # Apply row limit to prevent memory issues
    limited_result = result[:row_limit] if result else []
    
    # Convert list of dicts to Table format (columns and rows)
    if limited_result:
        columns = list(limited_result[0].keys())
        # Ensure consistent column order and serialize values for JSON compatibility
        rows = [[serialize_value(row[col]) for col in columns] for row in limited_result]
        
        # Add warning row if results were truncated
        if len(result) > row_limit:
            # Add a special column to indicate truncation
            columns_with_warning = ["_RESULT_INFO"] + columns
            warning_row = [
                f"⚠️ Results truncated: showing {row_limit} of {len(result)} total rows. Add LIMIT to your SQL for better performance."
            ] + [""] * len(columns)
            rows_with_warning = [warning_row] + [[""] + row for row in rows]
            return Response(result=Table(columns=columns_with_warning, rows=rows_with_warning))
        
        return Response(result=Table(columns=columns, rows=rows))
    else:
        return Response(result=Table(columns=[], rows=[]))
