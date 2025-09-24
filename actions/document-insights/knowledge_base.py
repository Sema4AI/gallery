import logging

from sema4ai.actions import Response, Secret
from sema4ai.data import query
from sema4ai_docint import build_di_service

from data_sources import (
    DocumentIntelligenceDataSource,
    DocumentIntelligencePGVector,
)
from models import Sema4aiQueryKnowledgeBaseRequest

logger = logging.getLogger(__name__)


@query
def query_knowledge_base(
    datasource: DocumentIntelligenceDataSource,
    pg_vector: DocumentIntelligencePGVector,
    sema4_api_key: Secret,
    request: Sema4aiQueryKnowledgeBaseRequest,
) -> Response[list[dict]]:
    """Get document in data model format.
    Args:
        datasource: Document intelligence data source connection
        pg_vector: Document intelligence PGVector data source connection
        sema4_api_key: Sema4.ai cloud backend API key
        request: Query knowledge base request containing document_id, document_name, natural_language_query, and relevance

    Note: either file_name or document_id is required. If both are provided, a composite search is performed.

    Returns:
        Response with document data as dict with view names as keys

    Raises:
        ActionError: If document or data model not found
    """
    di_service = build_di_service(datasource, sema4_api_key.value, pg_vector=pg_vector)

    table_result = di_service.knowledge_base.query(
        document_name=request.document_name,
        document_id=request.document_id,
        natural_language_query=request.natural_language_query,
        relevance=request.relevance,
    )

    return Response(result=table_result)


@query
def parse_and_store(
    datasource: DocumentIntelligenceDataSource,
    pg_vector: DocumentIntelligencePGVector,
    sema4_api_key: Secret,
    file_name: str,
) -> Response[str]:
    """Insert the parsed document chunks into the knowledge base.

    Args:
        datasource: Document intelligence data source connection
        pg_vector: Document intelligence PGVector data source connection
        sema4_api_key: Sema4.ai cloud backend API key
        file_name: File name to insert

    Returns:
        Success message with the document id of the inserted document.
    """
    di_service = build_di_service(datasource, sema4_api_key.value, pg_vector=pg_vector)

    result_message = di_service.knowledge_base.ingest(file_name)

    return Response(result=result_message)
