from sema4ai.actions import ActionError, Response, Table
from sema4ai.data import query, get_connection
import concurrent.futures
from typing import Dict, Any, List

def process_single_table(table_name: str, connection) -> Dict[str, Any]:
    """Process a single table to get its columns, sample data, and row count."""
    try:
        # Combine queries for better performance - get columns and count in one go
        combined_query = f"""
        SELECT * FROM snowflake_database (
            WITH table_info AS (
                SELECT 
                    'column_info' as query_type,
                    column_name as info,
                    data_type as detail,
                    is_nullable as extra
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                ORDER BY column_name
            ),
            row_count AS (
                SELECT 
                    'row_count' as query_type,
                    COUNT(*)::VARCHAR as info,
                    '' as detail,
                    '' as extra
                FROM {table_name}
            )
            SELECT * FROM table_info
            UNION ALL
            SELECT * FROM row_count
        )
        """
        
        # Get sample data with random sampling
        sample_query = f"""
        SELECT * FROM snowflake_database (
            SELECT * FROM {table_name} SAMPLE (10 ROWS)
        )
        """
        
        # Execute both queries
        combined_result = connection.query(combined_query, {})
        sample_result = connection.query(sample_query, {})
        
        # Parse the combined result
        combined_data = combined_result.to_table()
        columns_info = []
        row_count = 0
        
        for row in combined_data.rows:
            query_type = str(row[0])
            if query_type == 'column_info':
                columns_info.append([row[1], row[2], row[3]])
            elif query_type == 'row_count':
                row_count = int(row[1])
        
        # Create a mock table for columns (to maintain compatibility)
        from sema4ai.actions import Table
        columns_table = Table(
            columns=['column_name', 'data_type', 'is_nullable'],
            rows=columns_info
        )
        
        return {
            'table_name': table_name,
            'columns': columns_table,
            'sample_data': sample_result.to_table(),
            'row_count': row_count
        }
        
    except Exception as e:
        return {
            'table_name': table_name,
            'error': str(e)
        }

@query
def get_tables_info() -> Response[str]:
    """
    Returns all available database tables, along with details of each of their columns with datatypes, and a random sample of 10 rows to give a hint how the data looks in practise. ALWAYS use this method before running any queries against database.

    Returns:
        A markdown structure that includes all available database tables, along with details of each of their columns with datatypes, and a random sample of 10 rows to give a hint how the data looks in practise.
    """
    # First, get all tables
    tables_query = """
    SELECT * FROM snowflake_database (
        SELECT table_name, table_type
        FROM information_schema.tables
        WHERE table_type = 'BASE TABLE'
        ORDER BY table_name
    )
    """
    
    connection = get_connection()
    tables_result = connection.query(tables_query, {})
    
    # Get table names from the result
    tables_data = tables_result.to_table()
    table_names = [str(row[0]) for row in tables_data.rows]
    
    # Process tables in parallel for much better performance
    all_results = []
    
    # Use ThreadPoolExecutor to process tables in parallel
    # Note: We use threads instead of processes because database connections work better with threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(table_names), 5)) as executor:
        # Submit all table processing tasks
        future_to_table = {
            executor.submit(process_single_table, table_name, connection): table_name 
            for table_name in table_names
        }
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_table):
            table_name = future_to_table[future]
            try:
                result = future.result()
                all_results.append(result)
            except Exception as e:
                all_results.append({
                    'table_name': table_name,
                    'error': f"Parallel processing error: {str(e)}"
                })
    
    # Sort results by table name to maintain consistent output
    all_results.sort(key=lambda x: x['table_name'])
    
    # Format the comprehensive results as markdown
    markdown_output = "# Database Tables Information\n\n"
    
    for table_info in all_results:
        if 'error' in table_info:
            markdown_output += f"## Table: {table_info['table_name']}\n\n"
            markdown_output += f"**Error:** {table_info['error']}\n\n"
        else:
            row_count = table_info.get('row_count', 'Unknown')
            markdown_output += f"## Table: {table_info['table_name']}\n\n"
            markdown_output += f"**Total Rows:** {row_count:,}\n\n" if isinstance(row_count, int) else f"**Total Rows:** {row_count}\n\n"
            
            # Add columns information
            markdown_output += "### Columns\n\n"
            markdown_output += "| Column Name | Data Type | Is Nullable |\n"
            markdown_output += "|-------------|-----------|-------------|\n"
            
            for col_row in table_info['columns'].rows:
                col_name = str(col_row[0])
                data_type = str(col_row[1])
                is_nullable = str(col_row[2])
                markdown_output += f"| {col_name} | {data_type} | {is_nullable} |\n"
            
            # Add sample data with better empty table handling
            markdown_output += "\n### Sample Data\n\n"
            
            if isinstance(row_count, int) and row_count == 0:
                markdown_output += "**This table is empty (0 rows)**\n"
            elif table_info['sample_data'].rows:
                markdown_output += f"*Showing sample of up to 10 rows (table has {row_count:,} total rows)*\n\n" if isinstance(row_count, int) else "*Showing sample of up to 10 rows*\n\n"
                
                # Create markdown table headers
                headers = [str(col) for col in table_info['sample_data'].columns]
                markdown_output += "| " + " | ".join(headers) + " |\n"
                markdown_output += "|" + "|".join(["-" * (len(header) + 2) for header in headers]) + "|\n"
                
                # Add sample data rows
                for sample_row in table_info['sample_data'].rows:
                    row_data = [str(val) if val is not None else "NULL" for val in sample_row]
                    markdown_output += "| " + " | ".join(row_data) + " |\n"
            else:
                if isinstance(row_count, int) and row_count > 0:
                    markdown_output += f"*No sample data could be retrieved (table has {row_count:,} rows)*\n"
                else:
                    markdown_output += "*No sample data available*\n"
            
            markdown_output += "\n---\n\n"
    
    return Response(result=markdown_output)

@query
def execute_select_query(query: str) -> Response[Table]:
    """
    Executes a given Snowflake SQL query. MUST be valid Snowflake SQL. Before calling this tool make sure to understand the structure of the data with get_tables_info tool. This tool only allows SELECT queries. Anything else will raise an error before query execution.

    Args:
        query: The Snowflake SQL query to execute.

    Returns:
        The result of the query execution.
        
    Raises:
        ActionError: If the query is invalid, contains dangerous operations, or execution fails.
    """
    # Input validation
    if not query or not query.strip():
        raise ActionError("Query cannot be empty")
    
    query = query.strip()
    
    # Remove trailing semicolon if present (common user habit)
    if query.endswith(';'):
        query = query[:-1].strip()
    
    # Basic security checks - prevent dangerous operations
    dangerous_keywords = [
        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE',
        'GRANT', 'REVOKE', 'MERGE', 'CALL', 'EXECUTE'
    ]
    
    query_upper = query.upper()
    for keyword in dangerous_keywords:
        if f' {keyword} ' in f' {query_upper} ' or query_upper.startswith(f'{keyword} '):
            raise ActionError(f"Query contains potentially dangerous operation: {keyword}. Only SELECT queries are allowed for safety.")
    
    # Ensure query is wrapped in snowflake_database() if not already
    if not query_upper.startswith('SELECT * FROM SNOWFLAKE_DATABASE'):
        query = f"""
        SELECT * FROM snowflake_database (
            {query}
        )
        """
    
    try:
        params = {}
        result = get_connection().query(query, params)
        
        # Check if result is empty or has issues
        table_result = result.to_table()
        
        return Response(result=table_result)
        
    except Exception as e:
        original_error = str(e)
        error_msg_lower = original_error.lower()
        
        # Extract the core SQL error message (often buried in stack traces)
        # Look for common Snowflake error patterns
        if 'sql compilation error:' in error_msg_lower:
            # Extract just the SQL compilation error part
            start_idx = original_error.lower().find('sql compilation error:')
            if start_idx != -1:
                core_error = original_error[start_idx:].split('\n')[0]
                raise ActionError(f"{core_error}\n\nHint: Use get_tables_info() to see available tables and columns.")
        
        elif 'syntax error' in error_msg_lower:
            raise ActionError(f"SQL Syntax Error: {original_error}\n\nHint: Check your SQL syntax - common issues include missing quotes, incorrect table names, or invalid operators.")
        
        elif 'object does not exist' in error_msg_lower or 'invalid identifier' in error_msg_lower:
            raise ActionError(f"Object Not Found: {original_error}\n\nHint: Use get_tables_info() first to see all available tables and their columns.")
        
        elif 'permission' in error_msg_lower or 'access' in error_msg_lower or 'privilege' in error_msg_lower:
            raise ActionError(f"Access Denied: {original_error}\n\nHint: You may not have permission to access the requested tables or perform this operation.")
        
        elif 'timeout' in error_msg_lower or 'cancelled' in error_msg_lower:
            raise ActionError(f"Query Timeout: {original_error}\n\nHint: Try adding LIMIT clause to reduce result size, or simplify your query.")
        
        elif 'connection' in error_msg_lower or 'network' in error_msg_lower:
            raise ActionError(f"Connection Error: {original_error}\n\nHint: Database connection issue - please try again.")
        
        else:
            # For unknown errors, expose the full original error but with context
            raise ActionError(f"Query Failed: {original_error}\n\nIf this error persists, please check your query syntax and table permissions.")
