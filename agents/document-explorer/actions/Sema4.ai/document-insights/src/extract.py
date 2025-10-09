from typing import Annotated

from sema4ai.actions import ActionError, Secret, SecretSpec, action
from sema4ai.actions.chat import get_file
from sema4ai_docint import build_extraction_service

from src.models import Sema4aiExtractRequest, Sema4aiExtractResponse


@action
def extract(
    sema4_api_key: Annotated[Secret, SecretSpec(tag="document-intelligence")],
    extract_req: Sema4aiExtractRequest,
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

    # Coerce the input into a dict
    if isinstance(extract_req.extraction_schema, str):
        import json

        extraction_schema = json.loads(extract_req.extraction_schema)
    else:
        extraction_schema = extract_req.extraction_schema

    extraction_service = build_extraction_service(sema4_api_key.value)

    extract_resp = extraction_service.extract_with_schema(
        local_file if extract_req.file_name else job_id,
        extraction_schema,
        prompt="",  # Generic instructions that apply to the document as a whole
        extraction_config=extract_req.extraction_config,
        start_page=extract_req.start_page,
        end_page=extract_req.end_page,
    )

    return Sema4aiExtractResponse(result=extract_resp.results)  # type: ignore
