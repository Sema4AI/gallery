from typing import Annotated

from reducto.types.shared.parse_response import ResultFullResult
from sema4ai.actions import Response, Secret, SecretSpec, action
from sema4ai_docint import build_di_service
from sema4ai_docint.services.persistence import ChatFilePersistenceService

from src.models import ParseInput, Sema4aiParseResponse


@action
async def parse(
    sema4_api_key: Annotated[Secret, SecretSpec(tag="document-intelligence")],
    parse_input: ParseInput,
) -> Response[Sema4aiParseResponse]:
    """
    Parse the given file and return the parsed content.

    Args:
        sema4_api_key: The Sema4.AI API Key for Document Intelligence.
        parse_input: The input for the parse operation containing the file name and the parse configuration.

    Returns:
        The parsed document. A unique ID is used to later refer to this output for later steps.
    """
    di = build_di_service(
        datasource=None,
        sema4_api_key=sema4_api_key.value,
        persistence_service=ChatFilePersistenceService(),
    )

    doc = await di.document_v2.new_document(parse_input.file_name)
    parse_resp = await di.document_v2.parse(
        doc,
        force_reload=parse_input.force_reload,
        config={"options": {"chunking": {"chunk_mode": parse_input.chunking_mode}}},
    )
    assert isinstance(parse_resp.result, ResultFullResult)

    return Response(
        result=Sema4aiParseResponse.from_result(
            parse_resp, full_output=parse_input.full_output
        )
    )
