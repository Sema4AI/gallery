from sema4ai.actions import action
from sema4ai_docint.agent_server_client import AgentServerClient

from src.models import Sema4aiCreateSchemaRequest, Sema4aiCreateSchemaResponse


@action
def create_schema(
    create_schema_req: Sema4aiCreateSchemaRequest,
) -> Sema4aiCreateSchemaResponse:
    """
    Create a schema for the given file.

    Args:
        create_schema_req: The request to create a schema for the given file.

    Returns:
        The created schema.
    """
    schema = AgentServerClient().generate_schema(
        create_schema_req.file_name,
        start_page=create_schema_req.start_page,
        end_page=create_schema_req.end_page,
    )

    return Sema4aiCreateSchemaResponse(generated_schema=schema)
