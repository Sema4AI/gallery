from reducto.types import ExtractResponse
from sema4ai.actions import ActionError, Secret, action
from sema4ai.actions.chat import get_file
from sema4ai_docint import build_extraction_service

from models import Sema4aiExtractRequest, Sema4aiExtractResponse


@action
def extract(
    sema4_api_key: Secret, extract_req: Sema4aiExtractRequest
) -> Sema4aiExtractResponse:
    """
    Extract the given schema from the given file.

    Args:
        sema4_api_key: The Sema4.AI API Key for Document Intelligence.
        extract_req: The request to extract the given schema from the given file.

    Returns:
        The extracted data.
    """
    if extract_req.file_name:
        local_file = get_file(extract_req.file_name)
    elif extract_req.job_id:
        job_id = extract_req.job_id
    else:
        raise ActionError("One of file_name or job_id must be provided")

    if not extract_req.extraction_schema:
        raise ActionError(
            "Must provide a JSONSchema in the schema. This schema must describe an object and controls the extracted data."
        )

    extraction_service = build_extraction_service(sema4_api_key.value)

    extract_resp: ExtractResponse = extraction_service.extract_with_schema(
        local_file if extract_req.file_name else job_id,
        extract_req.extraction_schema,
        prompt="",  # Generic instructions that apply to the document as a whole
        extraction_config=extract_req.extraction_config,
        start_page=extract_req.start_page,
        end_page=extract_req.end_page,
    )

    # Sanity check that disable_chunking=True
    if len(extract_resp.result) > 1:
        raise ActionError(
            "Multiple results found. Update response to handle multiple extracted objects"
        )

    return Sema4aiExtractResponse(result=extract_resp.result[0])  # type: ignore
