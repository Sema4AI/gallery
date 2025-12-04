import base64
import datetime
import os
from decimal import Decimal
from contextlib import closing

from sema4ai.actions import ActionError, Response, Secret, action, Table, chat
from sema4ai.data import get_snowflake_connection, execute_snowflake_query


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
def who_am_I(warehouse: Secret) -> Response[str]:
    """
    Returns the current user, role, warehouse, database, and schema information. If you get an error from any other tool calls, use this tool to get the current user, role, warehouse, database, and schema information and let user know that they need to check if the permissions for the resource are set correctly.
    
    Args:
        warehouse: The Snowflake warehouse to use
        
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
            
            # Get current database and schema (may be None if not set)
            cursor.execute("SELECT CURRENT_DATABASE(), CURRENT_SCHEMA()")
            result = cursor.fetchone()
            current_database = result[0] if result[0] else "None (not set)"
            current_schema = result[1] if result[1] else "None (not set)"
            
            # Get current warehouse (may be None if not set)
            cursor.execute("SELECT CURRENT_WAREHOUSE()")
            result = cursor.fetchone()
            current_warehouse = result[0] if result[0] else "None (not set)"
            
            # Test warehouse access
            warehouse_status = "✅ ACCESSIBLE"
            try:
                cursor.execute(f"USE WAREHOUSE {warehouse.value}")
                # Update current warehouse after successful USE
                current_warehouse = warehouse.value
            except Exception as e:
                warehouse_status = f"❌ ERROR: {str(e)}"
            
            # Check if this is an application user (starts with 'ACTIONS_')
            if user.upper().startswith('ACTIONS_'):
                # Application context - don't show user, show context instead
                user_info = f"""Current Snowflake Session Information:
- Context: APPLICATION
- Role: {role}
- Warehouse: {current_warehouse}
- Database: {current_database}
- Schema: {current_schema}

Warehouse Access Status:
- Warehouse ({warehouse.value}): {warehouse_status}

**Access Management:** To grant access to Snowflake resources, use the APPLICATION ROLE: {role}"""
            else:
                # Regular user context
                user_info = f"""Current Snowflake Session Information:
- User: {user}
- Role: {role}
- Warehouse: {current_warehouse}
- Database: {current_database}
- Schema: {current_schema}

Warehouse Access Status:
- Warehouse ({warehouse.value}): {warehouse_status}

**Access Management:** To grant access to Snowflake resources, grant permissions to either:
- User: {user}
- Role: {role}"""
            
            return Response(result=user_info)
    
    except Exception as e:
        original_error = str(e)
        error_msg_lower = original_error.lower()
        
        # Detailed error categorization and reporting
        if 'sql compilation error:' in error_msg_lower:
            start_idx = original_error.lower().find('sql compilation error:')
            if start_idx != -1:
                core_error = original_error[start_idx:].split('\n')[0]
                return Response(result=None, error=f"{core_error}\n\nHint: Check the warehouse name. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")
        
        elif 'object does not exist' in error_msg_lower or 'invalid identifier' in error_msg_lower:
            return Response(result=None, error=f"Object Not Found: {original_error}\n\nHint: Verify that the warehouse '{warehouse.value}' exists and you have access to it. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")
        
        elif 'permission' in error_msg_lower or 'access' in error_msg_lower or 'privilege' in error_msg_lower:
            return Response(result=None, error=f"Access Denied: {original_error}\n\nHint: You may not have permission to access the specified warehouse. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources. Grant USAGE privilege on the warehouse to your user or role.")
        
        elif 'connection' in error_msg_lower or 'network' in error_msg_lower or 'timeout' in error_msg_lower:
            return Response(result=None, error=f"Connection Error: {original_error}\n\nHint: Database connection issue - please check your network connection and try again. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")
        
        elif 'authentication' in error_msg_lower or 'credentials' in error_msg_lower or 'login' in error_msg_lower:
            return Response(result=None, error=f"Authentication Error: {original_error}\n\nHint: Failed to authenticate with Snowflake. Please verify your credentials are correct. When ran in Work Room, ensure the Sema4.ai Native App is properly configured.")
        
        elif 'warehouse' in error_msg_lower and ('suspended' in error_msg_lower or 'resume' in error_msg_lower):
            return Response(result=None, error=f"Warehouse State Error: {original_error}\n\nHint: The warehouse may be suspended or resuming. Please wait a moment and try again, or check the warehouse status in Snowflake.")
        
        else:
            return Response(result=None, error=f"Failed to get current session information: {original_error}\n\nPlease check your warehouse parameter and Snowflake connection. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")

@action
def show_grants(warehouse: Secret) -> Response[Table]:
    """
    Shows the grants for the current user and role as a table. This is useful for debugging permission issues 
    and understanding what access the current user has in Snowflake.
    
    Args:
        warehouse: The Snowflake warehouse to use
        
    Returns:
        A Table with grants for the current user and role. First column indicates the grant type 
        (USER or ROLE), followed by all grant details from Snowflake.
    """
    try:
        with get_snowflake_connection() as connection, closing(connection.cursor()) as cursor:
            # Set the warehouse
            try:
                cursor.execute(f"USE WAREHOUSE {warehouse.value}")
            except Exception as e:
                return Response(result=None, error=f"Failed to use warehouse '{warehouse.value}': {str(e)}\n\nHint: Verify that the warehouse exists and you have USAGE privilege on it.")
            
            # Get current user and role
            cursor.execute("SELECT CURRENT_USER(), CURRENT_ROLE()")
            result = cursor.fetchone()
            user = result[0]
            role = result[1]
            
            # Collect all grants with their column info
            user_grants_data = []
            user_columns = []
            role_grants_data = []
            role_columns = []
            
            # Show grants to user
            try:
                # Quote the username to handle special characters like @ and .
                cursor.execute(f'SHOW GRANTS TO USER "{user}"')
                user_grants_result = cursor.fetchall()
                
                if user_grants_result:
                    # Get column names from cursor description
                    user_columns = [desc[0] for desc in cursor.description]
                    user_grants_data = [dict(zip(user_columns, grant)) for grant in user_grants_result]
            except Exception as e:
                pass  # We'll handle errors when building the final table
            
            # Show grants to role
            try:
                # Quote the role name to handle special characters
                cursor.execute(f'SHOW GRANTS TO ROLE "{role}"')
                role_grants_result = cursor.fetchall()
                
                if role_grants_result:
                    # Get column names from cursor description
                    role_columns = [desc[0] for desc in cursor.description]
                    role_grants_data = [dict(zip(role_columns, grant)) for grant in role_grants_result]
            except Exception as e:
                pass  # We'll handle errors when building the final table
            
            # Merge column lists to get all unique columns
            all_column_names = []
            if user_columns:
                all_column_names.extend(user_columns)
            if role_columns:
                for col in role_columns:
                    if col not in all_column_names:
                        all_column_names.append(col)
            
            # If no columns at all, return error
            if not all_column_names:
                return Response(result=Table(
                    columns=["grant_type", "message"],
                    rows=[[f"USER: {user}", "Unable to retrieve grants"], [f"ROLE: {role}", "Unable to retrieve grants"]]
                ))
            
            # Build unified table with grant_type as first column
            columns = ["grant_type"] + all_column_names
            all_rows = []
            
            # Add user grants
            for grant_dict in user_grants_data:
                row = [f"USER: {user}"]
                for col in all_column_names:
                    row.append(grant_dict.get(col, None))  # None if column doesn't exist
                all_rows.append(row)
            
            # Add role grants
            for grant_dict in role_grants_data:
                row = [f"ROLE: {role}"]
                for col in all_column_names:
                    row.append(grant_dict.get(col, None))  # None if column doesn't exist
                all_rows.append(row)
            
            if all_rows:
                # Serialize all values for JSON compatibility
                serialized_rows = []
                for row in all_rows:
                    serialized_row = [serialize_value(val) for val in row]
                    serialized_rows.append(serialized_row)
                
                return Response(result=Table(columns=columns, rows=serialized_rows))
            else:
                # No grants found at all
                return Response(result=Table(
                    columns=["grant_type", "message"],
                    rows=[[f"USER: {user}", "No grants found"], [f"ROLE: {role}", "No grants found"]]
                ))
    
    except Exception as e:
        original_error = str(e)
        error_msg_lower = original_error.lower()
        
        # Detailed error categorization and reporting
        if 'sql compilation error:' in error_msg_lower:
            start_idx = original_error.lower().find('sql compilation error:')
            if start_idx != -1:
                core_error = original_error[start_idx:].split('\n')[0]
                return Response(result=None, error=f"{core_error}\n\nHint: There may be an issue with the SHOW GRANTS command. This could happen if the user or role name contains special characters. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")
        
        elif 'object does not exist' in error_msg_lower or 'invalid identifier' in error_msg_lower:
            return Response(result=None, error=f"Object Not Found: {original_error}\n\nHint: Verify that the warehouse exists and you have access to it. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")
        
        elif 'permission' in error_msg_lower or 'access' in error_msg_lower or 'privilege' in error_msg_lower:
            return Response(result=None, error=f"Access Denied: {original_error}\n\nHint: You may not have permission to view grants. To use SHOW GRANTS, you typically need to be the owner of the user/role or have elevated privileges. When ran in Work Room, ensure the Sema4.ai Native App is granted appropriate permissions.")
        
        elif 'connection' in error_msg_lower or 'network' in error_msg_lower or 'timeout' in error_msg_lower:
            return Response(result=None, error=f"Connection Error: {original_error}\n\nHint: Database connection issue - please check your network connection and try again. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")
        
        elif 'authentication' in error_msg_lower or 'credentials' in error_msg_lower or 'login' in error_msg_lower:
            return Response(result=None, error=f"Authentication Error: {original_error}\n\nHint: Failed to authenticate with Snowflake. Please verify your credentials are correct. When ran in Work Room, ensure the Sema4.ai Native App is properly configured.")
        
        elif 'warehouse' in error_msg_lower and ('suspended' in error_msg_lower or 'resume' in error_msg_lower):
            return Response(result=None, error=f"Warehouse State Error: {original_error}\n\nHint: The warehouse may be suspended or resuming. Please wait a moment and try again, or check the warehouse status in Snowflake.")
        
        else:
            return Response(result=None, error=f"Failed to retrieve grants information: {original_error}\n\nPlease check your warehouse parameter and Snowflake connection. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")


@action
def get_databases_schemas(warehouse: Secret, database_filter: str = None) -> Response[Table]:
    """
    Shows all databases the user can see and the schemas within each database.
    Useful for discovering available data structures and checking access permissions.
    
    Args:
        warehouse: The Snowflake warehouse to use
        database_filter: Optional filter to match database names (case-insensitive). 
                        Will match databases containing this string. 
                        E.g., "oil" matches "OIL_AND_GAS", "oil_data", "MY_OIL_DB"
        
    Returns:
        A Table with database names and their corresponding schemas. 
        Columns: database_name, created_on, schema_name, is_default, is_current, owner, comment, and other metadata from Snowflake.
    """
    try:
        with get_snowflake_connection() as connection, closing(connection.cursor()) as cursor:
            # Set the warehouse
            try:
                cursor.execute(f"USE WAREHOUSE {warehouse.value}")
            except Exception as e:
                return Response(result=None, error=f"Failed to use warehouse '{warehouse.value}': {str(e)}\n\nHint: Verify that the warehouse exists and you have USAGE privilege on it.")
            
            # Get all databases with optional filter
            if database_filter:
                # Use LIKE for case-insensitive pattern matching (LIKE is case-insensitive in SHOW commands)
                # Wrap filter with % for substring matching
                filter_pattern = f"%{database_filter}%"
                cursor.execute(f"SHOW DATABASES LIKE '{filter_pattern}'")
            else:
                cursor.execute("SHOW DATABASES")
            databases = cursor.fetchall()
            
            if not databases:
                if database_filter:
                    message = f"No databases found matching filter '{database_filter}'"
                else:
                    message = "No databases found or accessible"
                return Response(result=Table(
                    columns=["database_name", "schema_name", "message"],
                    rows=[["N/A", "N/A", message]]
                ))
            
            # Get column names from SHOW DATABASES
            db_columns = [desc[0] for desc in cursor.description]
            db_name_idx = db_columns.index('name') if 'name' in db_columns else 0
            
            all_rows = []
            
            # For each database, get its schemas
            for db_row in databases:
                db_name = db_row[db_name_idx]
                
                try:
                    # Quote database name to handle special characters
                    cursor.execute(f'SHOW SCHEMAS IN DATABASE "{db_name}"')
                    schemas = cursor.fetchall()
                    
                    if schemas:
                        # Get schema column info
                        schema_columns = [desc[0] for desc in cursor.description]
                        
                        # Add each schema as a row
                        for schema_row in schemas:
                            # Combine database name with schema info
                            combined_row = [db_name] + list(schema_row)
                            all_rows.append(combined_row)
                    else:
                        # Database with no accessible schemas
                        all_rows.append([db_name, "N/A", "No schemas found or accessible"])
                        
                except Exception as e:
                    # If we can't access schemas in this database, note it
                    all_rows.append([db_name, "ERROR", f"Unable to list schemas: {str(e)}"])
            
            if all_rows:
                # Build column names: database_name + schema columns
                if schemas and cursor.description:
                    # Get column names from SHOW SCHEMAS and rename 'name' to 'schema_name' for clarity
                    schema_cols = [desc[0] for desc in cursor.description]
                    schema_cols = [col if col != 'name' else 'schema_name' for col in schema_cols]
                    columns = ["database_name"] + schema_cols
                else:
                    columns = ["database_name", "schema_name", "message"]
                
                # Serialize all values
                serialized_rows = [[serialize_value(val) for val in row] for row in all_rows]
                
                return Response(result=Table(columns=columns, rows=serialized_rows))
            else:
                return Response(result=Table(
                    columns=["database_name", "schema_name", "message"],
                    rows=[["N/A", "N/A", "No data available"]]
                ))
    
    except Exception as e:
        original_error = str(e)
        error_msg_lower = original_error.lower()
        
        if 'sql compilation error:' in error_msg_lower:
            start_idx = original_error.lower().find('sql compilation error:')
            if start_idx != -1:
                core_error = original_error[start_idx:].split('\n')[0]
                return Response(result=None, error=f"{core_error}\n\nHint: There may be an issue with the SHOW command. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")
        
        elif 'permission' in error_msg_lower or 'access' in error_msg_lower or 'privilege' in error_msg_lower:
            return Response(result=None, error=f"Access Denied: {original_error}\n\nHint: You may not have permission to view databases and schemas. When ran in Work Room, ensure the Sema4.ai Native App is granted appropriate permissions.")
        
        elif 'connection' in error_msg_lower or 'network' in error_msg_lower or 'timeout' in error_msg_lower:
            return Response(result=None, error=f"Connection Error: {original_error}\n\nHint: Database connection issue - please check your network connection and try again.")
        
        else:
            return Response(result=None, error=f"Failed to retrieve databases and schemas: {original_error}\n\nPlease check your warehouse parameter and Snowflake connection.")


@action
def get_tables_views(warehouse: Secret, database_schema: str) -> Response[Table]:
    """
    Shows all tables and views in a specified database.schema that the user can see.
    Uses SHOW OBJECTS and filters to only return tables and views (TABLE, VIEW, MATERIALIZED VIEW).
    Note: Semantic views are NOT returned by SHOW OBJECTS - use get_semantic_views for those.
    
    Args:
        warehouse: The Snowflake warehouse to use
        database_schema: The database and schema in format "database.schema" (e.g., "MY_DB.PUBLIC")
        
    Returns:
        A Table with all tables and views in the specified schema.
        First column is fully_qualified_name (database.schema.table_name) for easy copy/paste in queries.
        Other columns include: created_on, name, kind (TABLE/VIEW/MATERIALIZED VIEW), database_name, schema_name, and other metadata from Snowflake.
    """
    try:
        # Parse database.schema
        parts = database_schema.split('.')
        if len(parts) != 2:
            return Response(result=None, error=f"Invalid database_schema format: '{database_schema}'. Expected format: 'DATABASE.SCHEMA' (e.g., 'MY_DB.PUBLIC')")
        
        database = parts[0].strip()
        schema = parts[1].strip()
        
        if not database or not schema:
            return Response(result=None, error=f"Database or schema name is empty. Provided: '{database_schema}'")
        
        with get_snowflake_connection() as connection, closing(connection.cursor()) as cursor:
            # Set the warehouse
            try:
                cursor.execute(f"USE WAREHOUSE {warehouse.value}")
            except Exception as e:
                return Response(result=None, error=f"Failed to use warehouse '{warehouse.value}': {str(e)}\n\nHint: Verify that the warehouse exists and you have USAGE privilege on it.")
            
            # Show tables and views in the schema
            # Use SHOW OBJECTS which returns all object types in one query
            try:
                cursor.execute(f'SHOW OBJECTS IN SCHEMA "{database}"."{schema}"')
                objects_result = cursor.fetchall()
                
                if not objects_result:
                    return Response(result=Table(
                        columns=["fully_qualified_name", "database", "schema", "name", "kind", "message"],
                        rows=[["N/A", database, schema, "N/A", "N/A", "No tables or views found or accessible"]]
                    ))
                
                # Get column names and find relevant column indices
                columns = [desc[0] for desc in cursor.description]
                name_idx = columns.index('name') if 'name' in columns else 0
                kind_idx = columns.index('kind') if 'kind' in columns else -1
                
                # Filter to only include tables and views
                # Valid kinds: TABLE, VIEW, MATERIALIZED VIEW
                # Note: SEMANTIC VIEW does not appear in SHOW OBJECTS
                table_view_kinds = {'TABLE', 'VIEW', 'MATERIALIZED VIEW'}
                filtered_rows = []
                
                for row in objects_result:
                    if kind_idx >= 0:
                        object_kind = row[kind_idx]
                        # Only include tables and views
                        if object_kind in table_view_kinds:
                            filtered_rows.append(row)
                    else:
                        # If no kind column, include all (shouldn't happen but safe fallback)
                        filtered_rows.append(row)
                
                if not filtered_rows:
                    return Response(result=Table(
                        columns=["fully_qualified_name", "database", "schema", "name", "kind", "message"],
                        rows=[["N/A", database, schema, "N/A", "N/A", "No tables or views found in this schema"]]
                    ))
                
                # Add fully_qualified_name as the first column
                columns = ["fully_qualified_name"] + columns
                
                # Serialize all values and add fully qualified name to each row
                serialized_rows = []
                for row in filtered_rows:
                    object_name = row[name_idx]
                    fully_qualified = f"{database}.{schema}.{object_name}"
                    serialized_row = [fully_qualified] + [serialize_value(val) for val in row]
                    serialized_rows.append(serialized_row)
                
                return Response(result=Table(columns=columns, rows=serialized_rows))
                
            except Exception as e:
                error_str = str(e)
                error_lower = error_str.lower()
                
                if 'does not exist' in error_lower:
                    return Response(result=None, error=f"Database or schema not found: {database}.{schema}\n\nHint: Verify the database and schema names are correct and you have access to them. Use get_databases_schemas to see available databases and schemas.")
                elif 'permission' in error_lower or 'access' in error_lower:
                    return Response(result=None, error=f"Access Denied: Cannot access {database}.{schema}\n\nHint: You may not have USAGE privilege on the database or schema. Check permissions using show_grants.")
                else:
                    raise
    
    except Exception as e:
        original_error = str(e)
        error_msg_lower = original_error.lower()
        
        if 'sql compilation error:' in error_msg_lower:
            start_idx = original_error.lower().find('sql compilation error:')
            if start_idx != -1:
                core_error = original_error[start_idx:].split('\n')[0]
                return Response(result=None, error=f"{core_error}\n\nHint: Check the database.schema format. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")
        
        elif 'permission' in error_msg_lower or 'access' in error_msg_lower or 'privilege' in error_msg_lower:
            return Response(result=None, error=f"Access Denied: {original_error}\n\nHint: You may not have permission to view tables and views. When ran in Work Room, ensure the Sema4.ai Native App is granted appropriate permissions.")
        
        elif 'connection' in error_msg_lower or 'network' in error_msg_lower or 'timeout' in error_msg_lower:
            return Response(result=None, error=f"Connection Error: {original_error}\n\nHint: Database connection issue - please check your network connection and try again.")
        
        else:
            return Response(result=None, error=f"Failed to retrieve tables and views: {original_error}\n\nPlease check your parameters and Snowflake connection.")


@action
def get_stages(warehouse: Secret, database_schema: str) -> Response[Table]:
    """
    Shows all stages in a specified database.schema that the user can see.
    Stages are used for loading and unloading data to/from Snowflake.
    
    Args:
        warehouse: The Snowflake warehouse to use
        database_schema: The database and schema in format "database.schema" (e.g., "MY_DB.PUBLIC")
        
    Returns:
        A Table with all stages in the specified schema.
        First column is fully_qualified_name (database.schema.stage_name) for easy copy/paste in queries.
        Other columns include: name, url, owner, type, and other metadata from Snowflake.
    """
    try:
        # Parse database.schema
        parts = database_schema.split('.')
        if len(parts) != 2:
            return Response(result=None, error=f"Invalid database_schema format: '{database_schema}'. Expected format: 'DATABASE.SCHEMA' (e.g., 'MY_DB.PUBLIC')")
        
        database = parts[0].strip()
        schema = parts[1].strip()
        
        if not database or not schema:
            return Response(result=None, error=f"Database or schema name is empty. Provided: '{database_schema}'")
        
        with get_snowflake_connection() as connection, closing(connection.cursor()) as cursor:
            # Set the warehouse
            try:
                cursor.execute(f"USE WAREHOUSE {warehouse.value}")
            except Exception as e:
                return Response(result=None, error=f"Failed to use warehouse '{warehouse.value}': {str(e)}\n\nHint: Verify that the warehouse exists and you have USAGE privilege on it.")
            
            # Show stages in the schema
            try:
                cursor.execute(f'SHOW STAGES IN SCHEMA "{database}"."{schema}"')
                stages = cursor.fetchall()
                
                if not stages:
                    return Response(result=Table(
                        columns=["fully_qualified_name", "database", "schema", "name", "message"],
                        rows=[["N/A", database, schema, "N/A", "No stages found or accessible"]]
                    ))
                
                # Get column names and find the name column index
                columns = [desc[0] for desc in cursor.description]
                name_idx = columns.index('name') if 'name' in columns else 0
                
                # Add fully_qualified_name as the first column
                columns = ["fully_qualified_name"] + columns
                
                # Serialize all values and add fully qualified name to each row
                serialized_rows = []
                for row in stages:
                    stage_name = row[name_idx]
                    fully_qualified = f"{database}.{schema}.{stage_name}"
                    serialized_row = [fully_qualified] + [serialize_value(val) for val in row]
                    serialized_rows.append(serialized_row)
                
                return Response(result=Table(columns=columns, rows=serialized_rows))
                
            except Exception as e:
                error_str = str(e)
                error_lower = error_str.lower()
                
                if 'does not exist' in error_lower:
                    return Response(result=None, error=f"Database or schema not found: {database}.{schema}\n\nHint: Verify the database and schema names are correct and you have access to them. Use get_databases_schemas to see available databases and schemas.")
                elif 'permission' in error_lower or 'access' in error_lower:
                    return Response(result=None, error=f"Access Denied: Cannot access {database}.{schema}\n\nHint: You may not have USAGE privilege on the database or schema. Check permissions using show_grants.")
                else:
                    raise
    
    except Exception as e:
        original_error = str(e)
        error_msg_lower = original_error.lower()
        
        if 'sql compilation error:' in error_msg_lower:
            start_idx = original_error.lower().find('sql compilation error:')
            if start_idx != -1:
                core_error = original_error[start_idx:].split('\n')[0]
                return Response(result=None, error=f"{core_error}\n\nHint: Check the database.schema format. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")
        
        elif 'permission' in error_msg_lower or 'access' in error_msg_lower or 'privilege' in error_msg_lower:
            return Response(result=None, error=f"Access Denied: {original_error}\n\nHint: You may not have permission to view stages. When ran in Work Room, ensure the Sema4.ai Native App is granted appropriate permissions.")
        
        elif 'connection' in error_msg_lower or 'network' in error_msg_lower or 'timeout' in error_msg_lower:
            return Response(result=None, error=f"Connection Error: {original_error}\n\nHint: Database connection issue - please check your network connection and try again.")
        
        else:
            return Response(result=None, error=f"Failed to retrieve stages: {original_error}\n\nPlease check your parameters and Snowflake connection.")


@action
def get_stage_files(warehouse: Secret, stage_name: str, limit: int = 20) -> Response[Table]:
    """
    Lists files in a Snowflake stage with their properties, sorted by newest first.
    Useful for viewing data files before loading them into tables.
    
    Args:
        warehouse: The Snowflake warehouse to use
        stage_name: The fully qualified stage name in format "database.schema.stage_name" 
                   (e.g., "MY_DB.PUBLIC.MY_STAGE") or stage name with @ prefix (e.g., "@MY_DB.PUBLIC.MY_STAGE")
        limit: Maximum number of files to return, sorted by newest first (default: 20)
        
    Returns:
        A Table with all files in the stage and their properties.
        Sorted by last_modified descending (newest first).
        Columns:
        - full_stage_path: Complete path for copy/paste (@DATABASE.SCHEMA.STAGE/file.txt)
        - name: Clean file path within stage (folders only, no stage name prefix)
        - size: File size in bytes
        - md5: File checksum
        - last_modified: Timestamp
    """
    try:
        # Handle @ prefix if provided
        stage_name_clean = stage_name.strip()
        if stage_name_clean.startswith('@'):
            stage_name_clean = stage_name_clean[1:]
        
        # Parse database.schema.stage if provided, otherwise assume it's just stage name
        parts = stage_name_clean.split('.')
        if len(parts) == 3:
            database = parts[0].strip()
            schema = parts[1].strip()
            stage = parts[2].strip()
            # For LIST command - use quoted identifiers
            fully_qualified_stage_quoted = f'@"{database}"."{schema}"."{stage}"'
            # For display - use simple format without quotes
            fully_qualified_stage_simple = f'@{database}.{schema}.{stage}'
        elif len(parts) == 1:
            # Just stage name, will use current database/schema context
            stage = parts[0].strip()
            fully_qualified_stage_quoted = f'@"{stage}"'
            fully_qualified_stage_simple = f'@{stage}'
        else:
            return Response(result=None, error=f"Invalid stage_name format: '{stage_name}'. Expected format: 'DATABASE.SCHEMA.STAGE' or 'STAGE' or '@DATABASE.SCHEMA.STAGE'")
        
        with get_snowflake_connection() as connection, closing(connection.cursor()) as cursor:
            # Set the warehouse
            try:
                cursor.execute(f"USE WAREHOUSE {warehouse.value}")
            except Exception as e:
                return Response(result=None, error=f"Failed to use warehouse '{warehouse.value}': {str(e)}\n\nHint: Verify that the warehouse exists and you have USAGE privilege on it.")
            
            # List files in the stage
            try:
                cursor.execute(f'LIST {fully_qualified_stage_quoted}')
                files = cursor.fetchall()
                
                if not files:
                    return Response(result=Table(
                        columns=["full_stage_path", "name", "size", "md5", "last_modified", "message"],
                        rows=[["N/A", "N/A", 0, "N/A", "N/A", "No files found in stage"]]
                    ))
                
                # Get column names
                columns = [desc[0] for desc in cursor.description]
                
                # Find indices for name and last_modified columns
                name_idx = columns.index('name') if 'name' in columns else 0
                last_modified_idx = columns.index('last_modified') if 'last_modified' in columns else -1
                
                # Convert to list of dicts for easier sorting
                files_list = []
                for row in files:
                    file_dict = dict(zip(columns, row))
                    files_list.append(file_dict)
                
                # Sort by last_modified descending (newest first)
                if last_modified_idx >= 0:
                    def get_sort_key(file_dict):
                        last_mod = file_dict.get('last_modified')
                        if last_mod is None:
                            return datetime.datetime.min
                        # If it's already a datetime object, use it directly
                        if isinstance(last_mod, (datetime.datetime, datetime.date)):
                            return last_mod
                        # If it's a string, try to parse it
                        if isinstance(last_mod, str):
                            try:
                                # Try parsing RFC 2822 format: "Wed, 25 Jun 2025 12:52:35 GMT"
                                from email.utils import parsedate_to_datetime
                                return parsedate_to_datetime(last_mod)
                            except:
                                # If parsing fails, return the string for alphabetical sort
                                return last_mod
                        return datetime.datetime.min
                    
                    files_list.sort(key=get_sort_key, reverse=True)
                
                # Apply limit
                files_list = files_list[:limit]
                
                # Add full_stage_path as the first column
                output_columns = ["full_stage_path"] + columns
                
                # Convert back to rows and add full stage path
                serialized_rows = []
                for file_dict in files_list:
                    # Get the file name/path within the stage
                    file_name = file_dict.get('name', '')
                    
                    # Snowflake's LIST may return paths with stage name as a prefix directory
                    # e.g., for stage "FILES", it returns "files/myfile.txt" instead of "myfile.txt"
                    file_name_clean = file_name
                    if isinstance(file_name, str):
                        # Check if name already includes the full stage path
                        if file_name.startswith(fully_qualified_stage_quoted) or file_name.startswith(fully_qualified_stage_simple):
                            # Already has full path, just use it without quotes
                            full_path = file_name.replace(fully_qualified_stage_quoted, fully_qualified_stage_simple)
                        elif file_name.startswith('@'):
                            # Has some stage prefix but different format
                            full_path = file_name
                        else:
                            # Remove stage name prefix if it appears at the start (case-insensitive)
                            # Snowflake sometimes adds the stage name as a directory prefix
                            if '/' in file_name:
                                first_part = file_name.split('/')[0]
                                # Check if first part matches stage name (case-insensitive)
                                if first_part.upper() == stage.upper():
                                    # Remove the stage name prefix for both full_path and clean name
                                    file_name_clean = '/'.join(file_name.split('/')[1:])
                            
                            # Construct full path
                            if file_name_clean:
                                full_path = f"{fully_qualified_stage_simple}/{file_name_clean}".replace('//', '/')
                            else:
                                full_path = fully_qualified_stage_simple
                    else:
                        full_path = fully_qualified_stage_simple
                    
                    # Build row with full_stage_path first, then all original columns
                    # But replace the 'name' column value with the cleaned version
                    row = [full_path]
                    for col in columns:
                        if col == 'name':
                            # Use cleaned name without stage prefix
                            row.append(serialize_value(file_name_clean))
                        else:
                            row.append(serialize_value(file_dict.get(col)))
                    serialized_rows.append(row)
                
                return Response(result=Table(columns=output_columns, rows=serialized_rows))
                
            except Exception as e:
                error_str = str(e)
                error_lower = error_str.lower()
                
                if 'does not exist' in error_lower or 'invalid identifier' in error_lower:
                    return Response(result=None, error=f"Stage not found: {stage_name}\n\nHint: Verify the stage name is correct and you have access to it. Use get_stages to see available stages.")
                elif 'permission' in error_lower or 'access' in error_lower:
                    return Response(result=None, error=f"Access Denied: Cannot access stage {stage_name}\n\nHint: You may not have READ privilege on the stage. Check permissions using show_grants.")
                else:
                    raise
    
    except Exception as e:
        original_error = str(e)
        error_msg_lower = original_error.lower()
        
        if 'sql compilation error:' in error_msg_lower:
            start_idx = original_error.lower().find('sql compilation error:')
            if start_idx != -1:
                core_error = original_error[start_idx:].split('\n')[0]
                return Response(result=None, error=f"{core_error}\n\nHint: Check the stage name format. Expected: 'DATABASE.SCHEMA.STAGE' or '@DATABASE.SCHEMA.STAGE'. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")
        
        elif 'permission' in error_msg_lower or 'access' in error_msg_lower or 'privilege' in error_msg_lower:
            return Response(result=None, error=f"Access Denied: {original_error}\n\nHint: You may not have permission to list files in the stage. When ran in Work Room, ensure the Sema4.ai Native App is granted appropriate permissions.")
        
        elif 'connection' in error_msg_lower or 'network' in error_msg_lower or 'timeout' in error_msg_lower:
            return Response(result=None, error=f"Connection Error: {original_error}\n\nHint: Database connection issue - please check your network connection and try again.")
        
        else:
            return Response(result=None, error=f"Failed to retrieve stage files: {original_error}\n\nPlease check your parameters and Snowflake connection.")


@action
def download_stage_file(
    warehouse: Secret, 
    file_path: str, 
    target_folder: str = ""
) -> Response[str]:
    """
    Downloads a single file from a Snowflake stage and adds it to the chat context.
    The file will be available for viewing and analysis in the conversation.
    
    First verifies file existence and READ permissions before attempting download.
    Provides detailed error messages if file is not found or permissions are insufficient.
    
    Args:
        warehouse: The Snowflake warehouse to use
        file_path: The full stage path to the file - you can copy this directly from get_stage_files output.
                  Format: "@DATABASE.SCHEMA.STAGE/path/to/file.csv" or "DATABASE.SCHEMA.STAGE/path/to/file.csv"
                  Example: "@CALL_CENTER_DATA.PUBLIC.FILES/files/report.pdf"
        target_folder: Local folder to download the file to (default: current working directory)
        
    Returns:
        Status message with the local filepath where the file was downloaded.
        
    Required Permissions:
        - READ privilege on the stage to download files
        - Use show_grants() to check your current permissions
    """
    try:
        # Clean up the file path
        file_path_clean = file_path.strip()
        if not file_path_clean.startswith('@'):
            file_path_clean = '@' + file_path_clean
        
        # Convert clean path format (@db.schema.stage/file) to quoted format for Snowflake
        # Split the path into stage part and file part
        if '/' in file_path_clean:
            stage_part, file_part = file_path_clean.split('/', 1)
        else:
            stage_part = file_path_clean
            file_part = ''
        
        # Add quotes around identifiers in the stage part
        # @database.schema.stage -> @"database"."schema"."stage"
        stage_part_clean = stage_part.lstrip('@')
        stage_parts = stage_part_clean.split('.')
        if len(stage_parts) == 3:
            file_path_quoted = f'@"{stage_parts[0]}"."{stage_parts[1]}"."{stage_parts[2]}"'
        elif len(stage_parts) == 1:
            file_path_quoted = f'@"{stage_parts[0]}"'
        else:
            file_path_quoted = stage_part
        
        # Add back the file part
        if file_part:
            file_path_quoted = f"{file_path_quoted}/{file_part}"
        
        # Extract filename from path
        filename = os.path.basename(file_path_clean)
        if not filename:
            return Response(result=None, error=f"Could not extract filename from path: {file_path}")
        
        # Set target folder
        if target_folder == "":
            target_folder = os.getcwd()
        
        # Ensure target folder exists
        os.makedirs(target_folder, exist_ok=True)
        
        # Full local path where file will be downloaded
        local_file_path = os.path.join(target_folder, filename)
        
        with get_snowflake_connection() as connection, closing(connection.cursor()) as cursor:
            # Set the warehouse
            try:
                cursor.execute(f"USE WAREHOUSE {warehouse.value}")
            except Exception as e:
                return Response(result=None, error=f"Failed to use warehouse '{warehouse.value}': {str(e)}\n\nHint: Verify that the warehouse exists and you have USAGE privilege on it.")
            
            # First, check if we can list the file (verifies both file existence and READ permissions)
            try:
                list_command = f"LIST {file_path_quoted}"
                cursor.execute(list_command)
                list_result = cursor.fetchall()
                
                if not list_result:
                    # File doesn't exist or no permission to see it
                    return Response(result=None, error=f"File not found or no READ permission: {file_path}\n\nPossible issues:\n1. File path is incorrect\n2. File doesn't exist in the stage\n3. You don't have READ privilege on the stage\n\nHint: Use get_stage_files to verify the file exists and check permissions with show_grants.")
                
                # File exists and we have permission to list it
                file_info = list_result[0]
                print(f"File found: {file_info}")
                
            except Exception as list_error:
                error_str = str(list_error)
                error_lower = error_str.lower()
                
                if 'does not exist' in error_lower:
                    return Response(result=None, error=f"Stage or file does not exist: {file_path}\n\nHint: Verify the stage path and file path are correct. Use get_stages to see available stages and get_stage_files to list files.")
                elif 'permission' in error_lower or 'access' in error_lower or 'privilege' in error_lower:
                    return Response(result=None, error=f"Permission denied to access stage: {file_path}\n\nYou need READ privilege on the stage to download files.\n\nTo check your current permissions, use: show_grants()\nTo grant access (if you're an admin): GRANT READ ON STAGE <stage_name> TO ROLE <your_role>")
                else:
                    return Response(result=None, error=f"Error verifying file access: {error_str}\n\nHint: Check the file path format. Expected: '@DATABASE.SCHEMA.STAGE/path/to/file'")
            
            # Download file from stage using GET command
            try:
                # GET command downloads file to specified directory
                get_command = f"GET {file_path_quoted} 'file://{target_folder}/'"
                print(f"Executing: {get_command}")
                cursor.execute(get_command)
                result = cursor.fetchone()
                print(f"GET result: {result}")
                
                # Check if file was downloaded successfully
                if not os.path.exists(local_file_path):
                    return Response(result=None, error=f"File was not downloaded successfully.\nExpected at: {local_file_path}\nSnowflake result: {result}\n\nThis might indicate a permissions issue with the GET command (different from LIST).")
                
                # Get file size
                file_size = os.path.getsize(local_file_path)
                file_size_mb = file_size / (1024 * 1024)
                
                # Add file to chat context
                basename = os.path.basename(local_file_path)
                with open(local_file_path, "rb") as f:
                    chat.attach_file_content(name=basename, data=f.read())
                
                status_msg = f"Downloaded file '{filename}' ({file_size_mb:.2f} MB) from stage and added to chat.\nLocal path: {os.path.abspath(local_file_path)}"
                return Response(result=status_msg)
                
            except Exception as e:
                error_str = str(e)
                error_lower = error_str.lower()
                
                if 'permission' in error_lower or 'access' in error_lower or 'privilege' in error_lower:
                    return Response(result=None, error=f"Permission denied to GET file: {file_path}\n\nThe GET command requires READ privilege on the stage.\nYou were able to LIST the file but not download it.\n\nTo check permissions: show_grants()\nRequired privilege: GRANT READ ON STAGE <stage_name> TO ROLE <your_role>")
                else:
                    raise
    
    except Exception as e:
        original_error = str(e)
        error_msg_lower = original_error.lower()
        
        if 'sql compilation error:' in error_msg_lower:
            start_idx = original_error.lower().find('sql compilation error:')
            if start_idx != -1:
                core_error = original_error[start_idx:].split('\n')[0]
                return Response(result=None, error=f"{core_error}\n\nHint: Check the file path format. Expected: '@DATABASE.SCHEMA.STAGE/path/to/file'. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")
        
        elif 'permission' in error_msg_lower or 'access' in error_msg_lower or 'privilege' in error_msg_lower:
            return Response(result=None, error=f"Access Denied: {original_error}\n\nHint: You may not have permission to download files from the stage. When ran in Work Room, ensure the Sema4.ai Native App is granted appropriate permissions.")
        
        elif 'connection' in error_msg_lower or 'network' in error_msg_lower or 'timeout' in error_msg_lower:
            return Response(result=None, error=f"Connection Error: {original_error}\n\nHint: Database connection issue - please check your network connection and try again.")
        
        else:
            return Response(result=None, error=f"Failed to download file: {original_error}\n\nPlease check your parameters and Snowflake connection.")


@action
def get_semantic_views(warehouse: Secret, database_schema: str) -> Response[Table]:
    """
    Shows all semantic views in a specified database.schema that the user can see.
    Semantic views are Cortex AI-powered views that don't show up in SHOW OBJECTS.
    
    Args:
        warehouse: The Snowflake warehouse to use
        database_schema: The database and schema in format "database.schema" (e.g., "MY_DB.PUBLIC")
        
    Returns:
        A Table with all semantic views in the specified schema.
        First column is fully_qualified_name (database.schema.view_name) for easy copy/paste in queries.
        Other columns include metadata from Snowflake SHOW SEMANTIC VIEWS command.
    """
    try:
        # Parse database.schema
        parts = database_schema.split('.')
        if len(parts) != 2:
            return Response(result=None, error=f"Invalid database_schema format: '{database_schema}'. Expected format: 'DATABASE.SCHEMA' (e.g., 'MY_DB.PUBLIC')")
        
        database = parts[0].strip()
        schema = parts[1].strip()
        
        if not database or not schema:
            return Response(result=None, error=f"Database or schema name is empty. Provided: '{database_schema}'")
        
        with get_snowflake_connection() as connection, closing(connection.cursor()) as cursor:
            # Set the warehouse
            try:
                cursor.execute(f"USE WAREHOUSE {warehouse.value}")
            except Exception as e:
                return Response(result=None, error=f"Failed to use warehouse '{warehouse.value}': {str(e)}\n\nHint: Verify that the warehouse exists and you have USAGE privilege on it.")
            
            # Show semantic views in the schema
            try:
                cursor.execute(f'SHOW SEMANTIC VIEWS IN SCHEMA "{database}"."{schema}"')
                semantic_views = cursor.fetchall()
                
                if not semantic_views:
                    return Response(result=Table(
                        columns=["fully_qualified_name", "database", "schema", "name", "message"],
                        rows=[["N/A", database, schema, "N/A", "No semantic views found or accessible"]]
                    ))
                
                # Get column names and find the name column index
                columns = [desc[0] for desc in cursor.description]
                name_idx = columns.index('name') if 'name' in columns else 0
                
                # Add fully_qualified_name as the first column
                columns = ["fully_qualified_name"] + columns
                
                # Serialize all values and add fully qualified name to each row
                serialized_rows = []
                for row in semantic_views:
                    view_name = row[name_idx]
                    fully_qualified = f"{database}.{schema}.{view_name}"
                    serialized_row = [fully_qualified] + [serialize_value(val) for val in row]
                    serialized_rows.append(serialized_row)
                
                return Response(result=Table(columns=columns, rows=serialized_rows))
                
            except Exception as e:
                error_str = str(e)
                error_lower = error_str.lower()
                
                if 'does not exist' in error_lower:
                    return Response(result=None, error=f"Database or schema not found: {database}.{schema}\n\nHint: Verify the database and schema names are correct and you have access to them. Use get_databases_schemas to see available databases and schemas.")
                elif 'permission' in error_lower or 'access' in error_lower:
                    return Response(result=None, error=f"Access Denied: Cannot access {database}.{schema}\n\nHint: You may not have USAGE privilege on the database or schema. Check permissions using show_grants.")
                elif 'unsupported' in error_lower or 'not supported' in error_lower:
                    return Response(result=None, error=f"Semantic views may not be supported in your Snowflake edition or version: {error_str}\n\nHint: Semantic views require Snowflake Cortex features. Check your account capabilities.")
                else:
                    raise
    
    except Exception as e:
        original_error = str(e)
        error_msg_lower = original_error.lower()
        
        if 'sql compilation error:' in error_msg_lower:
            start_idx = original_error.lower().find('sql compilation error:')
            if start_idx != -1:
                core_error = original_error[start_idx:].split('\n')[0]
                return Response(result=None, error=f"{core_error}\n\nHint: Check the database.schema format. Semantic views require Snowflake Cortex features. When ran in Work Room, ensure the Sema4.ai Native App is granted access to the necessary Snowflake resources.")
        
        elif 'permission' in error_msg_lower or 'access' in error_msg_lower or 'privilege' in error_msg_lower:
            return Response(result=None, error=f"Access Denied: {original_error}\n\nHint: You may not have permission to view semantic views. When ran in Work Room, ensure the Sema4.ai Native App is granted appropriate permissions.")
        
        elif 'connection' in error_msg_lower or 'network' in error_msg_lower or 'timeout' in error_msg_lower:
            return Response(result=None, error=f"Connection Error: {original_error}\n\nHint: Database connection issue - please check your network connection and try again.")
        
        else:
            return Response(result=None, error=f"Failed to retrieve semantic views: {original_error}\n\nPlease check your parameters and Snowflake connection. Note: Semantic views require Snowflake Cortex features.")


@action
def validate_db_schema_access(warehouse: Secret, database: str, schema: str) -> Response[str]:
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
                cursor.execute(f"USE DATABASE {database}")
            except Exception as e:
                database_status = f"❌ ERROR: {str(e)}"
            
            # Test schema access
            try:
                cursor.execute(f"USE SCHEMA {schema}")
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
- Database ({database}): {database_status}
- Schema ({schema}): {schema_status}

**Access Management:** To grant access to Snowflake resources, use the APPLICATION ROLE: {role}"""
            else:
                # Regular user context
                user_info = f"""Current Snowflake Session Information:
- User: {user}
- Role: {role}

Resource Access Status:
- Warehouse ({warehouse.value}): {warehouse_status}
- Database ({database}): {database_status}
- Schema ({schema}): {schema_status}

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
        # Convert ValueError to ActionError for proper error reporting
        raise ActionError(str(e)) from e
    except Exception as e:
        # Catch any other unexpected errors
        raise ActionError(f"Failed to execute Snowflake query: {str(e)}") from e
