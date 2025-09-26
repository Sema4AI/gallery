from pathlib import Path

from reducto.types import ParseResponse
from sema4ai.actions import Secret, action
from sema4ai.actions.chat import get_file
from sema4ai_docint import build_extraction_service

from models import Sema4aiParseResponse


@action
def parse(sema4_api_key: Secret, file_name: str) -> Sema4aiParseResponse:
    """
    Parse the given file and return the parsed content.

    Args:
        sema4_api_key: The Sema4.AI API Key for Document Intelligence.
        file_name: The name of the file to parse. Must be attached to the current thread.

    Returns:
        The parsed document. A unique ID is used to later refer to this output for later steps.
    """
    local_file: Path = get_file(file_name)

    extraction_service = build_extraction_service(sema4_api_key.value)
    parse_resp: ParseResponse = extraction_service.parse(local_file)

    return Sema4aiParseResponse(job_id=parse_resp.job_id, result=parse_resp.result)
