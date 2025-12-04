import base64
import datetime
from decimal import Decimal

from sema4ai.actions import ActionError, Response, Secret, action, Table
from sema4ai.data import execute_snowflake_query


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
    numeric_args: list = None,
    row_limit: int = 10000,
) -> Response[Table]:
    """
    Executes a specific query and returns results as a Table.
    
    All table and column references in the query should use fully qualified names 
    (e.g., DATABASE.SCHEMA.TABLE) to work across different databases and schemas.

    Args:
        query: The query to execute. Use fully qualified table names (DATABASE.SCHEMA.TABLE).
        warehouse: Your Snowflake virtual warehouse to use for queries.
        numeric_args: A list of numeric arguments to pass to the query.
        row_limit: Maximum number of rows to return (default: 10000). 
                   Set to prevent memory issues with large result sets.
                   Consider adding LIMIT clause in your SQL for better performance.

    Returns:
        The results of the query as a Table (limited to row_limit rows).
    """

    try:
        result = execute_snowflake_query(
            query=query,
            warehouse=warehouse.value,
            numeric_args=numeric_args,
        )
        
        # Apply row limit to prevent memory issues
        limited_result = result[:row_limit] if result else []
        
        # Convert list of dicts to Table format (columns and rows)
        if limited_result:
            columns = list(limited_result[0].keys())
            # Ensure consistent column order and serialize values for JSON compatibility
            rows = [[serialize_value(row[col]) for col in columns] for row in limited_result]
            return Response(result=Table(columns=columns, rows=rows))
        else:
            return Response(result=Table(columns=[], rows=[]))
    
    except ValueError as e:
        # Convert ValueError (from utils.py) to ActionError for proper error reporting
        raise ActionError(str(e)) from e
    except Exception as e:
        # Catch any other unexpected errors
        raise ActionError(f"Failed to execute Snowflake query: {str(e)}") from e
