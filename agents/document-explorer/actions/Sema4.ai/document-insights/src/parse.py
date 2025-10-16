from pathlib import Path
from typing import Annotated

from reducto.types import ParseResponse
from reducto.types.shared.parse_response import ResultFullResult
from sema4ai.actions import ActionError, Secret, SecretSpec, action
from sema4ai.actions.chat import get_file
from sema4ai_docint import build_extraction_service

from src.models import Sema4aiParseResponse


@action
def parse(
    sema4_api_key: Annotated[Secret, SecretSpec(tag="document-intelligence")],
    file_name: str,
) -> Sema4aiParseResponse:
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
    parse_resp: ParseResponse = extraction_service.parse_file(local_file)

    # The sema4ai-docint library guarantees a ResultFullResult, but the types don't reflect that.
    if not isinstance(parse_resp.result, ResultFullResult):
        raise ActionError(
            f"Unexpected result type: {type(parse_resp.result)}. Expected ResultFullResult."
        )
    full_parse_result: ResultFullResult = parse_resp.result

    return Sema4aiParseResponse(job_id=parse_resp.job_id, result=full_parse_result)
