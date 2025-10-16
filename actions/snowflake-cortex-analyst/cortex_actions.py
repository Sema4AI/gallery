import os

import requests
from sema4ai.actions import ActionError, Response, Secret, action
from utils import get_snowflake_connection, is_running_in_spcs


def parse_semantic_model_input(input_value: str) -> tuple[str, str | list[str]]:
    """
    Parse semantic model input and determine type and value(s).
    
    Args:
        input_value: The raw input string containing file path(s) or view name(s).
    
    Returns:
        tuple of (field_name, field_value)
        field_name: One of 'semantic_model_file', 'semantic_model_files', 
                    'semantic_view', 'semantic_views'
        field_value: Either a string (single) or list of strings (multiple)
    
    Raises:
        ValueError: If input is invalid or mixes file paths with view names.
    """
    # Clean the input value from potential surrounding quotes
    cleaned = input_value.strip()
    
    # Remove surrounding single or double quotes if present (wrapping quotes only)
    # Don't strip if the string contains the same quote character internally
    # (which indicates quoted identifiers like "DB"."SCHEMA"."VIEW")
    if cleaned.startswith("'") and cleaned.endswith("'") and cleaned.count("'") == 2:
        cleaned = cleaned[1:-1]
    elif cleaned.startswith('"') and cleaned.endswith('"') and cleaned.count('"') == 2:
        cleaned = cleaned[1:-1]
    
    # Split by comma to detect multiple entries
    entries = [entry.strip() for entry in cleaned.split(',')]
    # Remove empty entries
    entries = [entry for entry in entries if entry]
    
    if not entries:
        raise ValueError("No valid semantic model entries found in input")
    
    # Detect type based on first entry (all must be same type)
    is_file = entries[0].startswith('@')
    
    # Validate all entries are the same type
    for entry in entries:
        if entry.startswith('@') != is_file:
            raise ValueError(
                "Cannot mix file paths (starting with @) and view names in the same request. "
                f"Found mixed types in input: {entries}"
            )
    
    # Determine field name and return appropriate structure
    if len(entries) == 1:
        if is_file:
            return 'semantic_model_file', entries[0]
        else:
            return 'semantic_view', entries[0]
    else:
        if is_file:
            return 'semantic_model_files', entries
        else:
            return 'semantic_views', entries


@action
def ask_cortex_analyst(
    semantic_model: Secret, 
    message: str
) -> Response[dict]:
    """
    Sends a message to the Cortex Analyst.

    Args:
        semantic_model: The semantic model file path or view name. Can be:
            - A single file path (starts with @): '@DB.SCHEMA.STAGE/file.yaml'
            - A single view name fully qualified: 'DB.SCHEMA.VIEW_NAME'
            - Multiple file paths (comma-separated): '@DB.SCHEMA.STAGE/file1.yaml, @DB.SCHEMA.STAGE/file2.yaml'
            - Multiple view names (comma-separated): 'DB.SCHEMA.VIEW1, DB.SCHEMA.VIEW2'
        message: The message to send.

    Returns:
        The response from the Cortex Analyst that contains an SQL query if successful.
    """
    try:
        
        with get_snowflake_connection() as conn:
            # Parse the semantic model input to determine the correct API field
            field_name, field_value = parse_semantic_model_input(semantic_model.value)
            
            request_body = {
                "timeout": 600, # 10 minutes
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": message}]}
                ],
                field_name: field_value,
            }

            if is_running_in_spcs():
                snowflake_account = os.getenv("SNOWFLAKE_ACCOUNT")
                snowflake_host = os.getenv("SNOWFLAKE_HOST")

                if snowflake_host.startswith("snowflake."):
                    snowflake_host = snowflake_host.replace(
                        "snowflake", snowflake_account.lower().replace("_", "-"), 1
                    )

                base_url = f"https://{snowflake_host}/api/v2/cortex/analyst/message"
                with open("/snowflake/session/token", "r") as f:
                    token = f.read().strip()
                token_type = "OAUTH"
            else:
                base_url = f"https://{conn.account.replace('_', '-')}.snowflakecomputing.com/api/v2/cortex/analyst/message"
                token_type = "KEYPAIR_JWT"
                token = conn.auth_class._jwt_token

            headers = {
                "Authorization": f"Bearer {token}",
                "X-Snowflake-Authorization-Token-Type": token_type,
                "Content-Type": "application/json",
            }
            
            try:
                response = requests.post(
                    f"{base_url}", headers=headers, json=request_body, verify=True
                )
                response.raise_for_status()
                return Response(result=response.json())
            except requests.exceptions.HTTPError as e:
                # Try to extract error message from response body
                error_detail = ""
                try:
                    error_body = response.json()
                    if isinstance(error_body, dict):
                        # Try to get the error message from common Snowflake error fields
                        error_detail = (
                            error_body.get('message') or 
                            error_body.get('error') or 
                            error_body.get('error_description') or
                            str(error_body)
                        )
                except Exception:
                    error_detail = response.text if response.text else str(e)
                
                # Provide helpful context based on the field name
                model_info = f"{field_name}={field_value}"
                
                # Add specific guidance for view-based models
                view_guidance = ""
                if 'view' in field_name.lower():
                    view_guidance = (
                        f"  - Semantic view name must be fully qualified (e.g., 'DATABASE.SCHEMA.VIEW_NAME')\n"
                        f"    Your value: '{field_value}' - ensure it includes database and schema\n"
                    )
                
                error_message = (
                    f"Cortex Analyst API error (HTTP {response.status_code}): {error_detail}\n"
                    f"Request used: {model_info}\n"
                    f"Common issues:\n"
                    f"{view_guidance}"
                    f"  - User's default role does not have permissions to access the schema or stage (Analyst uses Python SDK and REST API calls which means default role is always used)\n"
                    f"  - Semantic model file/view does not exist or is not accessible\n"
                    f"  - Insufficient permissions to access the model\n"
                    f"  - Invalid semantic model specification\n"
                    f"  - Stage or view path is incorrect"
                )
                raise ActionError(error_message) from e
    
    except ValueError as e:
        # Convert ValueError (from parse_semantic_model_input) to ActionError
        raise ActionError(str(e)) from e
    except ActionError:
        # Re-raise ActionError as-is
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise ActionError(f"Failed to communicate with Cortex Analyst: {str(e)}") from e
