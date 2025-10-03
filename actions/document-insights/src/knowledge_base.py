import logging
from typing import Any

from src.data_sources import (
    DocumentIntelligenceDataSource,
    DocumentIntelligencePGVector,
)
from src.models import Sema4aiQueryKnowledgeBaseRequest

from sema4ai.actions import ActionError, Response, Secret
from sema4ai.data import query
from sema4ai_docint import build_di_service, DIService
from sema4ai_docint.services._knowledge_base_service import _KnowledgeBaseService

logger = logging.getLogger(__name__)


def _require_kb_service(di_service: DIService) -> _KnowledgeBaseService:
    """
    Raise an error if the knowledge base service is not available.
    """
    kb_service = di_service.knowledge_base
    if kb_service is None:
        raise ActionError("KnowledgeBase Service requires a PGVector datasource.")
    return kb_service


@query
def query_document_in_kb(
    datasource: DocumentIntelligenceDataSource,
    pg_vector: DocumentIntelligencePGVector,
    sema4_api_key: Secret,
    query_data: Sema4aiQueryKnowledgeBaseRequest,
) -> Response[list[dict[str, Any]]]:
    """Get document in data model format.
    Args:
        datasource: Document intelligence data source connection
        pg_vector: Document intelligence PGVector data source connection
        sema4_api_key: Sema4.ai cloud backend API key
        query_data: Query knowledge base data

    Note: either file_name or document_id is required. If both are provided, a composite search is performed.

    Returns:
        Response with document data as dict with view names as keys

    Raises:
        ActionError: If document or data model not found
    """
    di_service = build_di_service(datasource, sema4_api_key.value, pg_vector=pg_vector)
    kb_service = _require_kb_service(di_service)

    query_result = kb_service.query(
        document_name=query_data.document_name,
        document_id=query_data.document_id,
        natural_language_query=query_data.natural_language_query,
        relevance=query_data.relevance,
    )

    # Convert the result to a list of dictionaries
    table_result = [result.model_dump() for result in query_result]

    return Response(result=table_result)


@query
def ingest(
    datasource: DocumentIntelligenceDataSource,
    pg_vector: DocumentIntelligencePGVector,
    sema4_api_key: Secret,
    file_name: str,
) -> Response[str]:
    """Insert the document into the knowledge base.

    Args:
        datasource: Document intelligence data source connection
        pg_vector: Document intelligence PGVector data source connection
        sema4_api_key: Sema4.ai cloud backend API key
        file_name: File name to insert

    Returns:
        Success message with the document id of the inserted document.
    """
    di_service = build_di_service(datasource, sema4_api_key.value, pg_vector=pg_vector)
    kb_service = _require_kb_service(di_service)

    result_message = kb_service.ingest(file_name)

    return Response(result=result_message)
