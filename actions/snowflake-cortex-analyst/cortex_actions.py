import os

import requests
from sema4ai.actions import Response, Secret, action
from utils import get_snowflake_connection, is_running_in_spcs

@action
def ask_cortex_analyst(semantic_model_file: Secret, message: str) -> Response[dict]:
    """
    Sends a message to the Cortex Analyst.

    Args:
        semantic_model_file: The path to a Snowflake Stage containing the semantic model file.
        message: The message to send.

    Returns:
        The response from the Cortex Analyst.
    """
    with get_snowflake_connection() as conn:
        # Clean the semantic_model_file value from potential extra quotes
        clean_path = semantic_model_file.value
        # Remove surrounding single quotes if present
        if clean_path.startswith("'") and clean_path.endswith("'"):
            clean_path = clean_path[1:-1]
        
        request_body = {
            "timeout": 50000,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": message}]}
            ],
            "semantic_model_file": clean_path,
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
            base_url = f"https://{conn.account}.snowflakecomputing.com/api/v2/cortex/analyst/message"
            token_type = "KEYPAIR_JWT"
            token = conn.auth_class._jwt_token

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Snowflake-Authorization-Token-Type": token_type,
            "Content-Type": "application/json",
        }
        response = requests.post(
            f"{base_url}", headers=headers, json=request_body, verify=False
        )
        response.raise_for_status()

        return Response(result=response.json())
