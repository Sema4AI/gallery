from typing import Annotated

from reducto.types.shared.parse_response import ResultFullResult
from sema4ai.actions import Secret, SecretSpec, action
from sema4ai_docint import build_di_service
from sema4ai_docint.services.persistence import ChatFilePersistenceService

from src.models import Sema4aiParseResponse


@action
async def parse(
    sema4_api_key: Annotated[Secret, SecretSpec(tag="document-intelligence")],
    file_name: str,
    force_reload: bool = False,
) -> Sema4aiParseResponse:
    """
    Parse the given file and return the parsed content.

    Args:
        sema4_api_key: The Sema4.AI API Key for Document Intelligence.
        file_name: The name of the file to parse. Must be attached to the current thread.
        force_reload: Bypass the parse cache and force a new parse. Defaults to False. Should only be enabled for debugging purposes.
    Returns:
        The parsed document. A unique ID is used to later refer to this output for later steps.
    """
    di = build_di_service(
        datasource=None,
        sema4_api_key=sema4_api_key.value,
        persistence_service=ChatFilePersistenceService(),
    )

    doc = await di.document_v2.new_document(file_name)
    parse_resp = await di.document_v2.parse(doc, force_reload=force_reload)
    assert isinstance(parse_resp.result, ResultFullResult)

    return Sema4aiParseResponse.from_result(parse_resp)
