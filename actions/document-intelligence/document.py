import json
import logging
from typing import Annotated, Any

from data_sources import DocumentIntelligenceDataSource
from pydantic import BaseModel
from sema4ai.actions import ActionError, Response, Secret, SecretSpec, Table, action
from sema4ai.actions.chat import get_file
from sema4ai.data import query
from sema4ai_docint import build_di_service
from sema4ai_docint.extraction import (
    TransformDocumentLayout,
)
from sema4ai_docint.extraction.process import (
    ExtractAndTransformContentParams,
    ExtractionSchemaInput,
    TranslationSchemaInput,
)
from sema4ai_docint.extraction.transform import _apply_mapping
from sema4ai_docint.models import (
    Document,
    ExtractionResult,
    Mapping,
    MappingRow,
)
from sema4ai_docint.utils import normalize_name

logger = logging.getLogger(__name__)

# Set to True to disable SSL verification when talking to backend.sema4.ai
DISABLE_SSL_VERIFICATION = False


class ExtractResult(BaseModel):
    """The extracted content from a document with optional citations."""

    extracted_content: dict[str, Any]
    citations: dict[str, Any] | None = None


@action
def extract_document(
    sema4_api_key: Annotated[Secret, SecretSpec(tag="document-intelligence")],
    datasource: DocumentIntelligenceDataSource,
    file_name: str,
    extraction_schema: ExtractionSchemaInput,
    data_model_prompt: str | None = None,
    extraction_config: dict[str, Any] | None = None,
    document_layout_prompt: str | None = None,
) -> ExtractResult:
    """Extract structured data from document using schema.

    Args:
        sema4_api_key: Sema4.ai cloud backend API key
        file_name: PDF file name to process
        extraction_schema: Extraction schema to use for processing (string or ExtractionSchema dict).
                          This defines the structure for extracting data from the document.
                          Should contain JSONSchema properties like 'type', 'properties', 'required'.
        data_model_prompt: Optional system prompt for processing
        extraction_config: Optional extraction configuration for processing.
        document_layout_prompt: Optional system prompt for layout processing

    Returns:
        Response with extracted content as dict and citations as dict.

    Raises:
        ActionError: If document processing fails
    """

    pdf_path = get_file(file_name)
    try:
        di_service = build_di_service(datasource, sema4_api_key.value)
        extract_result: ExtractionResult = (
            di_service.extraction.extract_with_data_model(
                pdf_path,
                extraction_schema,
                data_model_prompt,
                extraction_config,
                document_layout_prompt,
            )
        )

        return ExtractResult(
            extracted_content=extract_result.results,
            citations=extract_result.citations,
        )
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise ActionError(f"Failed to process document: {str(e)}") from e


@action
def translate_extracted_document(
    extracted_content: dict[str, Any],
    translation_schema: TranslationSchemaInput,
) -> Response[dict[str, Any]]:
    """Transform extracted content using translation rules.
    Args:
        extracted_content: Extracted content from document
        translation_schema: Translation schema to transform content (string or TranslationSchema dict).
                         This defines how to transform extracted data into the target format.
                         Should contain a 'rules' array with mapping rules.
    Returns:
        Response with transformed content as dict
    Raises:
        ActionError: If content transformation fails
    """
    # Parse the translation schema as a str or dict
    if isinstance(translation_schema, str):
        parsed_schema = json.loads(translation_schema)
    else:
        parsed_schema = translation_schema

    # Validate that we have a dict with rules
    if not isinstance(parsed_schema, dict):
        raise ValueError("Translation schema must be a valid JSON object")

    rules_list = parsed_schema.get("rules", [])
    if not isinstance(rules_list, list):
        raise ValueError("Translation schema must contain a 'rules' array")

    # Convert them into our MappingRow object
    rules = [MappingRow(**rule) for rule in rules_list]
    mapping = Mapping(rules=rules)

    try:
        transform_client = TransformDocumentLayout()
        transformed_content = _apply_mapping(
            transform_client, extracted_content, mapping
        )
    except Exception as e:
        logger.error(f"Error transforming content: {str(e)}")
        raise ActionError(f"Failed to transform content: {str(e)}") from e

    return Response(result={"transformed_content": transformed_content})


## Queries


@query
def describe_document(
    datasource: DocumentIntelligenceDataSource, document_id: str
) -> Response[dict[str, Any]]:
    """Get document details from database.
    Args:
        datasource: Document intelligence data source connection
        document_id: Document ID to retrieve
    Returns:
        Response containing document data as dict
    Raises:
        ActionError: If document not found
    """
    document = Document.find_by_id(datasource, document_id)
    if not document:
        raise ActionError(f"Document with ID {document_id} not found")

    return Response(result=document.model_dump())


@query
def delete_document(
    datasource: DocumentIntelligenceDataSource, document_id: str
) -> Response[bool]:
    """Delete document from database.
    Args:
        datasource: Document intelligence data source connection
        document_id: Document ID to delete
    Returns:
        Response with True if deleted, False otherwise
    Raises:
        ActionError: If document not found
    """
    document = Document.find_by_id(datasource, document_id)
    if not document:
        raise ActionError(f"Document with ID {document_id} not found")

    success = document.delete(datasource)
    return Response(result=success)


@query
def find_documents_by_layout(
    datasource: DocumentIntelligenceDataSource, data_model_name: str, layout_name: str
) -> Response[list[dict[str, Any]]]:
    """Find documents using specific layout.
    Args:
        datasource: Document intelligence data source connection
        data_model_name: Data model name to search
        layout_name: Layout name to search
    Returns:
        Response with list of matching documents
    """
    data_model_name = normalize_name(data_model_name)
    layout_name = normalize_name(layout_name)
    documents = Document.find_by_document_layout(
        datasource, data_model_name, layout_name
    )
    return Response(result=[document.model_dump() for document in documents])


@query
def ingest(
    sema4_api_key: Annotated[Secret, SecretSpec(tag="document-intelligence")],
    datasource: DocumentIntelligenceDataSource,
    file_name: str,
    data_model_name: str,
    layout_name: str,
) -> Response[dict[str, Any]]:
    """Ingest document into data model using layout with automatic validation and retry.

    This function creates PERSISTENT state by storing the document, extracted content,
    and transformed content in the database. It automatically validates the processed
    document and retries with different configurations if validation fails.

    Args:
        sema4_api_key: Sema4.ai cloud backend API key
        datasource: Document intelligence data source connection
        file_name: file name to process
        data_model_name: Data model name for document
        layout_name: Document layout to use for processing

    Returns:
        Response with created document containing extracted and transformed content,
        validation results, and retry information if applicable.

    Raises:
        ActionError: If document processing fails after all retry attempts
    """
    try:
        di_service = build_di_service(
            datasource,
            sema4_api_key.value,
        )
        response_data = di_service.document.ingest(
            file_name,
            data_model_name,
            layout_name,
        )
        return Response(result=response_data)

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise ActionError(f"Failed to process document: {str(e)}") from e


@query
def list_documents(
    datasource: DocumentIntelligenceDataSource, data_model_name: str
) -> Response[list[dict[str, Any]]]:
    """List all documents from the database for a specific data model.

    Args:
        datasource: The document intelligence data source connection
        data_model_name: Name of the data model to filter documents by
    Returns:
        Response containing list of documents from the database for the specified data model
    Raises:
        ActionError: If there are database connection issues or data model not found
    """
    data_model_name = normalize_name(data_model_name)
    documents = Document.find_by_data_model(datasource, data_model_name)
    return Response(result=[document.model_dump() for document in documents])


@query
def query_document(
    sema4_api_key: Annotated[Secret, SecretSpec(tag="document-intelligence")],
    datasource: DocumentIntelligenceDataSource,
    document_id: str,
) -> Response[dict[str, Table | None] | Table | None]:
    """Get document in data model format.
    Args:
        datasource: Document intelligence data source connection
        document_id: Document ID to retrieve
    Returns:
        Response with document data as dict with view names as keys
    Raises:
        ActionError: If document or data model not found
    """
    di_service = build_di_service(datasource, sema4_api_key.value)
    results_dict = di_service.document.query(document_id)

    return Response(result=results_dict)


@query
def extract_and_transform_content(
    sema4_api_key: Annotated[Secret, SecretSpec(tag="document-intelligence")],
    params: ExtractAndTransformContentParams,
    datasource: DocumentIntelligenceDataSource,
) -> Response[dict[str, Any]]:
    """Extract, transform, validate content with automatic retry and schema storage.

    This function performs the complete document processing pipeline:
    1. Extract and transform content using provided schemas
    2. Validate the processed document
    3. If validation fails, automatically retry with different configurations
    4. Store successful schemas in database for future use

    Args:
        sema4_api_key: Sema4.ai cloud backend API key
        params: ExtractAndTransformContentParams object containing:
            - file_name: file name to process
            - extraction_schema: Extraction schema as JSON string (must be valid JSON)
            - translation_schema: Translation schema as dict with "rules" key containing array of mapping rules
            - data_model_name: Data model name for document
            - layout_name: Document layout to use for processing
        datasource: Document intelligence data source connection

    Returns:
        Response with created document containing extracted and transformed content,
        validation results, and retry information if applicable.

    Raises:
        ActionError: If document processing fails after all retry attempts
    """

    try:
        di_service = build_di_service(
            datasource,
            sema4_api_key.value,
        )
        response_data = di_service.document.extract_with_schema(params)
        return Response(result=response_data)

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise ActionError(f"Failed to process document: {str(e)}") from e
