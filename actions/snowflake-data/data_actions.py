from sema4ai.actions import ActionError, Response, Table, action, Secret
import concurrent.futures
from typing import Dict, Any, List
import snowflake.connector
from contextlib import closing
from snowflake_connection import get_snowflake_connection

def process_single_table(table_name: str, warehouse: str, database: str, schema: str) -> Dict[str, Any]:
    """Process a single table to get its columns, sample data, and row count."""
    try:
        with get_snowflake_connection() as connection, closing(connection.cursor()) as cursor:
            # Use the provided warehouse, database, and schema
            cursor.execute(f"USE WAREHOUSE {warehouse}")
            cursor.execute(f"USE DATABASE {database}")
            cursor.execute(f"USE SCHEMA {schema}")
            
            # Get column information
            columns_query = f"""
            SELECT 
                column_name,
                data_type,
                is_nullable
            FROM information_schema.columns
            WHERE table_name = '{table_name.upper()}'
            ORDER BY column_name
            """
            
            cursor.execute(columns_query)
            columns_info = [[str(val) if val is not None else "NULL" for val in row] for row in cursor.fetchall()]
            
            # Get row count
            count_query = f"SELECT COUNT(*) FROM {table_name}"
            cursor.execute(count_query)
            row_count = cursor.fetchone()[0]
            
            # Get sample data (limit to 10 rows)
            sample_query = f"SELECT * FROM {table_name} LIMIT 10"
            cursor.execute(sample_query)
            # Convert to strings and truncate long values
            sample_data = []
            for row in cursor.fetchall():
                processed_row = []
                for val in row:
                    if val is None:
                        processed_row.append("NULL")
                    else:
                        str_val = str(val)
                        # Truncate if longer than 100 characters
                        if len(str_val) > 100:
                            processed_row.append(str_val[:97] + "...")
                        else:
                            processed_row.append(str_val)
                sample_data.append(processed_row)
            sample_columns = [desc[0] for desc in cursor.description]
            
            # Create tables for compatibility with existing interface
            columns_table = Table(
                columns=['column_name', 'data_type', 'is_nullable'],
                rows=columns_info
            )
            
            sample_table = Table(
                columns=sample_columns,
                rows=sample_data
            )
            
            return {
                'table_name': table_name,
                'columns': columns_table,
                'sample_data': sample_table,
                'row_count': row_count
            }
        
    except Exception as e:
        return {
            'table_name': table_name,
            'error': str(e)
        }

@action
def get_tables_info(warehouse: Secret, database: Secret, schema: Secret) -> Response[str]:
    """
    Returns all available database tables, along with details of each of their columns with datatypes, and a random sample of 10 rows to give a hint how the data looks in practise. ALWAYS use this method before running any queries against database.

    Args:
        warehouse: The Snowflake warehouse to use
        database: The Snowflake database to use  
        schema: The Snowflake schema to use

    Returns:
        A markdown structure that includes all available database tables, along with details of each of their columns with datatypes, and a random sample of 10 rows to give a hint how the data looks in practise.
    """
    try:
        with get_snowflake_connection() as connection, closing(connection.cursor()) as cursor:
            # Use the provided warehouse, database, and schema
            cursor.execute(f"USE WAREHOUSE {warehouse.value}")
            cursor.execute(f"USE DATABASE {database.value}")
            cursor.execute(f"USE SCHEMA {schema.value}")
            
            # Now get all tables
            tables_query = """
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_type = 'BASE TABLE'
            ORDER BY table_name
            """
            
            cursor.execute(tables_query)
            tables_data = cursor.fetchall()
            table_names = [str(row[0]) for row in tables_data]
        
        # Check if any tables were found
        if not table_names:
            return Response(result="No tables found in the specified database and schema. Please verify the database and schema names, and ensure you have the necessary permissions to view tables.")
        
        # Process tables in parallel for much better performance
        all_results = []
        
        # Use ThreadPoolExecutor to process tables in parallel
        # Note: We use threads instead of processes because database connections work better with threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(table_names), 5)) as executor:
            # Submit all table processing tasks
            future_to_table = {
                executor.submit(process_single_table, table_name, warehouse.value, database.value, schema.value): table_name 
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
                return Response(result=None, error=f"{core_error}\n\nHint: Check warehouse, database, and schema names. Use correct credentials and when ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")
        
        elif 'syntax error' in error_msg_lower:
            return Response(result=None, error=f"SQL Syntax Error: {original_error}\n\nHint: Check your warehouse, database, and schema names. Use correct credentials and when ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")
        
        elif 'object does not exist' in error_msg_lower or 'invalid identifier' in error_msg_lower:
            return Response(result=None, error=f"Object Not Found: {original_error}\n\nHint: Verify that the warehouse, database, and schema exist and you have access to them. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")
        
        elif 'permission' in error_msg_lower or 'access' in error_msg_lower or 'privilege' in error_msg_lower:
            return Response(result=None, error=f"Access Denied: {original_error}\n\nHint: You may not have permission to access the specified warehouse, database, or schema. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")
        
        elif 'timeout' in error_msg_lower or 'cancelled' in error_msg_lower:
            return Response(result=None, error=f"Connection Timeout: {original_error}\n\nHint: Check if the warehouse is running and accessible. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")
        
        elif 'connection' in error_msg_lower or 'network' in error_msg_lower:
            return Response(result=None, error=f"Connection Error: {original_error}\n\nHint: Database connection issue - please try again. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")
        
        else:
            # For unknown errors, expose the full original error but with context
            return Response(result=None, error=f"Failed to get table information: {original_error}\n\nPlease check your warehouse, database, and schema parameters. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")

@action
def execute_select_query(query: str, warehouse: Secret, database: Secret, schema: Secret) -> Response[Table]:
    """
    Executes a given Snowflake SQL query. MUST be valid Snowflake SQL. Before calling this tool make sure to understand the structure of the data with get_tables_info tool. This tool only allows SELECT queries. Anything else will raise an error before query execution.

    Args:
        query: The Snowflake SQL query to execute.
        warehouse: The Snowflake warehouse to use
        database: The Snowflake database to use  
        schema: The Snowflake schema to use

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
    
    try:
        with get_snowflake_connection() as connection, closing(connection.cursor()) as cursor:
            # Use the provided warehouse, database, and schema
            cursor.execute(f"USE WAREHOUSE {warehouse.value}")
            cursor.execute(f"USE DATABASE {database.value}")
            cursor.execute(f"USE SCHEMA {schema.value}")
            
            # Execute the user's query
            cursor.execute(query)
            # Convert to strings and truncate long values
            results = []
            for row in cursor.fetchall():
                processed_row = []
                for val in row:
                    if val is None:
                        processed_row.append("NULL")
                    else:
                        str_val = str(val)
                        # Truncate if longer than 100 characters
                        if len(str_val) > 100:
                            processed_row.append(str_val[:97] + "...")
                        else:
                            processed_row.append(str_val)
                results.append(processed_row)
            columns = [desc[0] for desc in cursor.description]
            
            # Create a Table object for the response
            table_result = Table(
                columns=columns,
                rows=results
            )
            
            return Response(result=table_result)
        
    except Exception as e:
        original_error = str(e)
        error_msg_lower = original_error.lower()
        
        # Create a detailed error message that includes the query context
        error_context = f"\n\n**Query that failed:**\n```sql\n{query}\n```\n"
        
        # Extract the core SQL error message (often buried in stack traces)
        # Look for common Snowflake error patterns
        if 'sql compilation error:' in error_msg_lower:
            # Extract the full SQL compilation error with line numbers if available
            start_idx = original_error.lower().find('sql compilation error:')
            if start_idx != -1:
                # Try to get multiple lines of the error message to capture line numbers and position info
                error_lines = original_error[start_idx:].split('\n')[:3]  # Get up to 3 lines
                core_error = '\n'.join([line.strip() for line in error_lines if line.strip()])
                return Response(result=None, error=f"{core_error}{error_context}\nHint: Use get_tables_info() to see available tables and columns.")
        
        elif 'syntax error' in error_msg_lower:
            # Look for line/position information in syntax errors
            if 'line' in error_msg_lower or 'position' in error_msg_lower:
                return Response(result=None, error=f"SQL Syntax Error: {original_error}{error_context}\nHint: Check the syntax at the indicated line/position. Common issues include missing quotes, incorrect table names, or invalid operators.")
            else:
                return Response(result=None, error=f"SQL Syntax Error: {original_error}{error_context}\nHint: Check your SQL syntax - common issues include missing quotes, incorrect table names, or invalid operators.")
        
        elif 'object does not exist' in error_msg_lower or 'invalid identifier' in error_msg_lower:
            return Response(result=None, error=f"Object Not Found: {original_error}{error_context}\nHint: Use get_tables_info() first to see all available tables and their columns.")
        
        elif 'permission' in error_msg_lower or 'access' in error_msg_lower or 'privilege' in error_msg_lower:
            return Response(result=None, error=f"Access Denied: {original_error}{error_context}\nHint: You may not have permission to access the requested tables or perform this operation. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")
        
        elif 'timeout' in error_msg_lower or 'cancelled' in error_msg_lower:
            return Response(result=None, error=f"Query Timeout: {original_error}{error_context}\nHint: Try adding LIMIT clause to reduce result size, or simplify your query.")
        
        elif 'connection' in error_msg_lower or 'network' in error_msg_lower:
            return Response(result=None, error=f"Connection Error: {original_error}\n\nHint: Database connection issue - please try again.")
        
        else:
            # For unknown errors, expose the full original error but with context
            return Response(result=None, error=f"Query Failed: {original_error}{error_context}\nIf this error persists, please check your query syntax and table permissions.")

@action
def who_am_I(warehouse: Secret, database: Secret, schema: Secret) -> Response[str]:
    """
    Returns the current user, role, warehouse, database, and schema information. If you get an error from any other tool calls, use this tool to get the current user, role, warehouse, database, and schema information and let user know that they need to check if the permissions for the resource are set correctly.

    Args:
        warehouse: The Snowflake warehouse to use
        database: The Snowflake database to use  
        schema: The Snowflake schema to use

    Returns:
        A formatted string with current user, role, warehouse, database, and schema information.
    """
    try:
        with get_snowflake_connection() as connection, closing(connection.cursor()) as cursor:
            # First, get user and role info (this should always work if connection is valid)
            cursor.execute("SELECT CURRENT_USER(), CURRENT_ROLE()")
            result = cursor.fetchone()
            user = result[0]
            role = result[1]
            
            # Test each resource separately and collect status
            warehouse_status = "✅ ACCESSIBLE"
            database_status = "✅ ACCESSIBLE"
            schema_status = "✅ ACCESSIBLE"
            
            # Test warehouse access
            try:
                cursor.execute(f"USE WAREHOUSE {warehouse.value}")
            except Exception as e:
                warehouse_status = f"❌ ERROR: {str(e)}"
            
            # Test database access
            try:
                cursor.execute(f"USE DATABASE {database.value}")
            except Exception as e:
                database_status = f"❌ ERROR: {str(e)}"
            
            # Test schema access
            try:
                cursor.execute(f"USE SCHEMA {schema.value}")
            except Exception as e:
                schema_status = f"❌ ERROR: {str(e)}"
            
            # Check if this is an application user (starts with 'ACTIONS_')
            if user.upper().startswith('ACTIONS_'):
                # Application context - don't show user, show context instead
                user_info = f"""Current Snowflake Session Information:
- Context: APPLICATION
- Role: {role}

Resource Access Status:
- Warehouse ({warehouse.value}): {warehouse_status}
- Database ({database.value}): {database_status}
- Schema ({schema.value}): {schema_status}

**Access Management:** To grant access to Snowflake resources, use the APPLICATION ROLE: {role}"""
            else:
                # Regular user context
                user_info = f"""Current Snowflake Session Information:
- User: {user}
- Role: {role}

Resource Access Status:
- Warehouse ({warehouse.value}): {warehouse_status}
- Database ({database.value}): {database_status}
- Schema ({schema.value}): {schema_status}

**Access Management:** To grant access to Snowflake resources, grant permissions to either:
- User: {user}
- Role: {role}"""
            
            return Response(result=user_info)
    
    except Exception as e:
        original_error = str(e)
        error_msg_lower = original_error.lower()
        
        if 'sql compilation error:' in error_msg_lower:
            start_idx = original_error.lower().find('sql compilation error:')
            if start_idx != -1:
                core_error = original_error[start_idx:].split('\n')[0]
                return Response(result=None, error=f"{core_error}\n\nHint: Check warehouse, database, and schema names. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")
        
        elif 'object does not exist' in error_msg_lower or 'invalid identifier' in error_msg_lower:
            return Response(result=None, error=f"Object Not Found: {original_error}\n\nHint: Verify that the warehouse, database, and schema exist and you have access to them. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")
        
        elif 'permission' in error_msg_lower or 'access' in error_msg_lower or 'privilege' in error_msg_lower:
            return Response(result=None, error=f"Access Denied: {original_error}\n\nHint: You may not have permission to access the specified warehouse, database, or schema. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")
        
        elif 'connection' in error_msg_lower or 'network' in error_msg_lower:
            return Response(result=None, error=f"Connection Error: {original_error}\n\nHint: Database connection issue - please try again. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")
        
        else:
            return Response(result=None, error=f"Failed to get user information: {original_error}\n\nPlease check your warehouse, database, and schema parameters. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")