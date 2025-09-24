import json
import logging
from typing import Any

from data_sources import DocumentIntelligenceDataSource
from sema4ai.actions import ActionError, Response, action
from sema4ai.actions.chat import get_file
from sema4ai.data import query
from sema4ai_docint import build_di_service
from sema4ai_docint.agent_server_client import (
    AgentServerClient,
    CategorizedSummary,
    DocumentClassificationError,
)
from sema4ai_docint.extraction import TransformDocumentLayout
from sema4ai_docint.extraction.transform import transform_content
from sema4ai_docint.models import (
    DataModel,
    Document,
    DocumentLayout,
    Mapping,
    MappingRow,
)
from sema4ai_docint.utils import normalize_name, validate_extraction_schema

logger = logging.getLogger(__name__)
DEFAULT_LAYOUT_NAME = "default"


def _generate_translation_schema(
    data_model_schema: str, layout_schema: str
) -> dict[str, Any]:
    """
    Create a set of rules to translate JSON objects from the layout's schema to the data model's schema.
    Args:
        data_model_schema: The data model's schema
        layout_schema: The layout's schema
    Returns:
        The translation schema
    """
    client = AgentServerClient()

    mapping_rules_text = client.create_mapping(data_model_schema, layout_schema)
    mapping_rules = json.loads(mapping_rules_text)
    if not isinstance(mapping_rules, list):
        raise ValueError("mapping should be a list")

    mapping = Mapping(rules=[MappingRow(**rule) for rule in mapping_rules])  # type: ignore
    return mapping.model_dump()  # type: ignore


def _upsert_schema(
    name: str,
    data_model_name: str,
    extraction_schema: dict[str, Any],
    translation_schema: dict[str, Any],
    summary: str | None,
    datasource: DocumentIntelligenceDataSource,
) -> None:
    """
    Upserts a schema into the database. If a schema with the same name exists,
    it will be updated with the new extraction schema. Otherwise, a new schema will be created.
    Args:
        name: The name of the schema
        data_model_name: The name of the data model
        extraction_schema: The extraction schema to store
    """
    try:
        # Try to find existing schema
        schema = DocumentLayout.find_by_name(datasource, data_model_name, name)
        if schema:
            schema.extraction_schema = extraction_schema
            schema.translation_schema = translation_schema
            schema.summary = summary
            schema.update(datasource)
        else:
            # Schema doesn't exist, create it
            schema = DocumentLayout(
                name=name,
                data_model=data_model_name,
                extraction_schema=extraction_schema,
                translation_schema=translation_schema,
                summary=summary,
            )
            schema.insert(datasource)
    except Exception as e:
        logger.error(f"Error upserting schema: {e!s}")
        raise ValueError("Failed to upsert schema") from e


def _create_or_update_default_layout(
    datasource: DocumentIntelligenceDataSource,
    data_model_name: str,
    business_schema: dict[str, Any],
) -> None:
    """Create or update the default layout for a data model.

    This method handles the creation or update of the default layout for a data model.
    The business schema is used directly as the extraction schema, and a direct mapping
    is created for the translation schema.

    Args:
        datasource: The document intelligence data source connection
        data_model_name: The name of the data model
        business_schema: The business schema to base the layout on

    Raises:
        ActionError: If layout creation/update fails
    """
    existing_layout = None
    try:
        data_model_name = normalize_name(data_model_name)
        existing_layout = DocumentLayout.find_by_name(
            datasource, data_model_name, DEFAULT_LAYOUT_NAME
        )

        mapping_rules = []
        for field_name in business_schema.get("properties", {}).keys():
            mapping_rules.append(
                {
                    "source": field_name,
                    "target": field_name,
                }
            )

        translation_schema = {"rules": mapping_rules}

        # Generate summary for the default layout or if existing layout has no summary
        summary = None
        if not existing_layout or not existing_layout.summary:
            client = AgentServerClient()
            summary = client.summarize_with_args(
                {
                    "Layout name": DEFAULT_LAYOUT_NAME,
                    "Data model name": data_model_name,
                    "Layout schema": business_schema,
                }
            )

        if existing_layout:
            existing_layout.extraction_schema = business_schema
            existing_layout.translation_schema = translation_schema
            existing_layout.summary = summary
            existing_layout.update(datasource)
        else:
            layout = DocumentLayout(
                name=DEFAULT_LAYOUT_NAME,
                data_model=data_model_name,
                extraction_schema=business_schema,
                translation_schema=translation_schema,
                summary=summary,
            )
            layout.insert(datasource)
    except Exception as e:
        verb = "updating" if existing_layout else "creating"
        logger.error(
            f"Error {verb} default layout for data model {data_model_name}: {str(e)}"
        )
        raise ActionError(
            f"Failed to {verb} default layout for data model {data_model_name}: {str(e)}"
        ) from e


## Actions


@action
def generate_translation_schema(
    datasource: DocumentIntelligenceDataSource,
    data_model_name: str,
    layout_schema: str,
) -> Response[dict[str, Any]]:
    """
    Create translation rules to map layout schema to data model schema.
    Args:
        data_model_name: The name of the data model to generate a translation schema for
        layout_schema: Extraction schema of the layout to generate a translation schema for
    Returns:
        Dict containing translation mapping rules
    Raises:
        ValueError: If mapping generation fails
    """

    try:
        di_service = build_di_service(datasource)
        result = di_service.layout.generate_translation_schema(
            data_model_name, layout_schema
        )
        return Response(result=result)
    except Exception as e:
        raise ActionError(f"Failed to generate translation schema: {e}") from e


@action
def generate_layout(
    file_name: str,
    datasource: DocumentIntelligenceDataSource,
    data_model_name: str,
) -> Response[dict[str, Any]]:
    """Generate a layout from the given file.
    Args:
        file_name: The name of the PDF file to generate a layout from
        datasource: The document intelligence data source connection
        data_model_name: The name of the data model to generate a layout for
    Returns:
        Response containing generated layout schema
    Raises:
        ActionError: If layout generation fails
    """
    client = AgentServerClient()
    try:
        data_model = DataModel.find_by_name(datasource, data_model_name)
        if not data_model:
            raise ActionError(f"Data model with name {data_model_name} not found")
        # The LLM can understand the structure from the JSON schema itself
        model_schema_json = json.dumps(data_model.model_schema, indent=2)
        extraction_schema_dict = client.generate_schema(file_name, model_schema_json)
    except ValueError as e:
        raise ActionError(f"Failed to generate extraction schema: {e}") from e

    return Response(
        result={
            "message": "Layout generated successfully",
            "schema": extraction_schema_dict,
        }
    )


## Queries


@query
def describe_layout(
    datasource: DocumentIntelligenceDataSource, data_model_name: str, name: str
) -> Response[dict[str, Any]]:
    """
    Fetch an extraction schema by name.
    Args:
        datasource: The document intelligence data source connection
        data_model_name: The name of the data model this layout belongs to
        name: Name of the layout to fetch
    Returns:
        Response containing the layout schema and metadata
    Raises:
        ActionError: If layout not found
    """
    data_model_name = normalize_name(data_model_name)
    name = normalize_name(name)
    # Try to find existing layout
    layout = DocumentLayout.find_by_name(datasource, data_model_name, name)
    if not layout:
        raise ActionError(
            f"Layout with name {name} not found in data model {data_model_name}"
        )
    return Response(result=layout.model_dump())


@query
def generate_layout_name(
    file_name: str,
) -> Response[dict[str, Any]]:
    """
    Generate a layout name for a document.
    Args:
        file_name: The name of the file to generate a layout name for
    Returns:
        Response containing the generated layout name
    """
    pdf_path = get_file(file_name)
    agent_client = AgentServerClient()
    try:
        images = agent_client._pdf_to_images(pdf_path)
        layout_name = agent_client.generate_document_layout_name(
            [image.get("value") for image in images], file_name
        )
        return Response(result={"layout_name": layout_name})
    except Exception as e:
        logger.error(f"Error generating layout name: {e}")
        raise ActionError(f"Failed to generate layout name: {str(e)}") from e


@query
def create_layout_from_schema(
    datasource: DocumentIntelligenceDataSource,
    name: str,
    data_model_name: str,
    json_schema: str,
    translation_rules: str | dict,
    summary: str | None = None,
) -> Response[dict[str, Any]]:
    """
    Creates a new document layout for a data model with the given JSON schema.
    This is a power-tool which is only appropriate for users which understand how
    the JSON schema is used with document layouts.
    Args:
        datasource: The document intelligence data source connection
        name: Name of the layout to create
        data_model_name: Name of the data model this layout belongs to
        json_schema: The JSON schema to use to create the layout
        translation_rules: The translation rules to use to transform the content
        summary: A summary to use when matching documents to this layout
    Returns:
        Response containing the created document layout
    Raises:
        ActionError: If layout creation fails or layout already exists
    """
    original_name = name
    name = normalize_name(name)
    data_model_name = normalize_name(data_model_name)

    # Check if layout with this name already exists in the data model
    existing_layout = DocumentLayout.find_by_name(datasource, data_model_name, name)
    if existing_layout:
        raise ActionError(
            f"Cannot create layout '{original_name}' because after normalizing special characters "
            f"it becomes '{name}', which already exists in data model '{data_model_name}'."
        )

    data_model = DataModel.find_by_name(datasource, data_model_name)
    if not data_model:
        raise ActionError(f"Data model with name {data_model_name} not found")

    # validate that the caller gave a valid json schema
    extraction_schema = validate_extraction_schema(json_schema)

    # Use or generate translation rules
    if isinstance(translation_rules, str):
        if translation_rules == "":
            # if the caller doesn't provide translation rules, create an empty mapping
            rules: dict[str, Any] = {"rules": []}
        else:
            rules = json.loads(translation_rules)
    else:
        rules = translation_rules

    # assume that the LLM gave us a list of rules rather than our dict configuration
    if isinstance(rules, list):
        print("provided rules were a list, coercing into a dictionary")
        rules = {"rules": rules}

    # If summary is not provided, generate a summary from the schema
    if not summary:
        client = AgentServerClient()
        summary = client.summarize_with_args(
            {
                "Layout name": name,
                "Data model name": data_model_name,
                "Layout schema": extraction_schema,
            }
        )

    # Store the validated schema with mapping
    _upsert_schema(name, data_model_name, extraction_schema, rules, summary, datasource)

    return Response(
        result={
            "message": f"Layout {name} created successfully",
            "schema": extraction_schema,
            "summary": summary,
        }
    )


@query
def update_layout_from_schema(
    datasource: DocumentIntelligenceDataSource,
    name: str,
    data_model_name: str,
    json_schema: str,
    translation_rules: str | dict,
    summary: str | None = None,
) -> Response[dict[str, Any]]:
    """
    Updates an existing document layout with a new JSON schema.
    This is a power-tool which is only appropriate for users which understand how
    the JSON schema is used with document layouts.
    Args:
        datasource: The document intelligence data source connection
        name: Name of the layout to update
        data_model_name: Name of the data model this layout belongs to
        json_schema: The new JSON schema to use for the layout
        translation_rules: The new translation rules to use to transform the content
        summary: A new summary to use when matching documents to this layout
    Returns:
        Response containing the updated document layout
    Raises:
        ActionError: If layout update fails or layout not found
    """
    original_name = name
    name = normalize_name(name)
    data_model_name = normalize_name(data_model_name)

    # Check if layout with this name exists in the data model
    existing_layout = DocumentLayout.find_by_name(datasource, data_model_name, name)
    if not existing_layout:
        raise ActionError(
            f"Cannot update layout '{original_name}' because after normalizing special characters "
            f"it becomes '{name}', which does not exist in data model '{data_model_name}'."
        )

    data_model = DataModel.find_by_name(datasource, data_model_name)
    if not data_model:
        raise ActionError(f"Data model with name {data_model_name} not found")

    # validate that the caller gave a valid json schema
    extraction_schema = validate_extraction_schema(json_schema)

    # Use or generate translation rules
    if isinstance(translation_rules, str):
        if translation_rules == "":
            # if the caller doesn't provide translation rules, create an empty mapping
            rules: dict[str, Any] = {"rules": []}
        else:
            rules = json.loads(translation_rules)
    else:
        rules = translation_rules

    # assume that the LLM gave us a list of rules rather than our dict configuration
    if isinstance(rules, list):
        print("provided rules were a list, coercing into a dictionary")
        rules = {"rules": rules}

    # If summary is not provided, generate a summary from the schema
    if not summary:
        client = AgentServerClient()
        summary = client.summarize_with_args(
            {
                "Layout name": name,
                "Data model name": data_model_name,
                "Layout schema": extraction_schema,
            }
        )

    # Update the existing layout with new schema and rules
    _upsert_schema(name, data_model_name, extraction_schema, rules, summary, datasource)

    return Response(
        result={
            "message": f"Layout {name} updated successfully",
            "schema": extraction_schema,
            "summary": summary,
        }
    )


@query
def delete_layout(
    datasource: DocumentIntelligenceDataSource, data_model_name: str, name: str
) -> Response[str]:
    """Delete a layout from the database.

    Args:
        datasource: The document intelligence data source connection
        data_model_name: The name of the data model this layout belongs to
        name: The name of the layout to delete

    Returns:
        Response containing "Success" if deletion was successful

    Raises:
        ActionError: If the layout is not found
    """
    data_model_name = normalize_name(data_model_name)
    name = normalize_name(name)
    layout = DocumentLayout.find_by_name(datasource, data_model_name, name)
    if not layout:
        raise ActionError(
            f"Layout with name {name} not found in data model {data_model_name}"
        )

    layout.delete(datasource)
    return Response(result="Success")


@query
def list_layouts(
    datasource: DocumentIntelligenceDataSource,
) -> Response[list[dict[str, Any]]]:
    """List all layouts from the database.

    Args:
        datasource: The document intelligence data source connection

    Returns:
        Response containing list of all layout dictionaries
    """
    layouts = DocumentLayout.find_all(datasource)
    return Response(result=[layout.model_dump() for layout in layouts])


@query
def list_layouts_by_model(
    datasource: DocumentIntelligenceDataSource, data_model_name: str
) -> Response[list[dict[str, Any]]]:
    """List all layouts for a specific data model.

    Args:
        datasource: The document intelligence data source connection
        data_model_name: The name of the data model

    Returns:
        Response containing list of layout dictionaries for the given data model

    Raises:
        ActionError: If no layouts found for the specified data model
    """
    data_model_name = normalize_name(data_model_name)
    layouts = DocumentLayout.find_by_data_model(datasource, data_model_name)

    if not layouts:
        raise ActionError(f"No layouts found for data model: {data_model_name}")

    return Response(result=[layout.model_dump() for layout in layouts])


@query
def choose_document_layout(
    datasource: DocumentIntelligenceDataSource,
    data_model_name: str,
    file_name: str,
    expected_confidence: float = 0.95,
) -> Response[dict[str, Any]]:
    """Choose a document layout for a data model.

    Args:
        datasource: The document intelligence data source connection
        data_model_name: The name of the data model
        file_name: The name of the file to choose a layout for
        expected_confidence: The minimum confidence score for a match to be returned (0.0 to 1.0)

    Returns:
        Response with the following structure:
        {
            "Message": str,           # Human-readable message about the result
            "layout_name": str,       # The matched layout name or "default"
            "confidence": float,      # Confidence score (0.0 to 1.0) or None
            "method": str,           # "image" or "text" classification method used
            "fallback_used": bool    # Whether default layout was used as fallback
        }
    """
    # Validate parameters
    if not (0.0 <= expected_confidence <= 1.0):
        raise ActionError(
            f"expected_confidence must be between 0.0 and 1.0, got {expected_confidence}"
        )

    data_model_name = normalize_name(data_model_name)

    # Get all layouts for this data model
    all_layouts = DocumentLayout.find_by_data_model(datasource, data_model_name)
    if not all_layouts:
        logger.warning(f"No layouts found for data model {data_model_name}")
        raise ActionError(f"No layouts found for data model {data_model_name}")

    # Get file path
    pdf_path = get_file(file_name)
    agent_client = AgentServerClient()

    # Try image-based classification first if supported
    if agent_client._supports_image_conversion(file_name):
        logger.info(f"Attempting image-based classification for file '{file_name}'")
        try:
            images = agent_client._pdf_to_images(pdf_path)
            match = agent_client.classify_document_multi_signal(
                [image.get("value") for image in images],
                [layout.name for layout in all_layouts],
                file_name,
            )

            logger.info(f"Multi-signal classification successful: matched to '{match}'")
            return Response(
                result={
                    "Message": f"Document matched to {match} using multi-signal classification",
                    "layout_name": match,
                    "confidence": None,  # Image classification doesn't provide confidence scores
                    "method": "multi-signal",
                    "fallback_used": False,
                }
            )

        except DocumentClassificationError as e:
            logger.warning(f"Multi-signal classification failed with error: {e}")
            return Response(
                result={
                    "Message": "No layout matched the document.",
                    "layout_name": "NOT FOUND",
                    "confidence": None,
                    "method": "multi-signal",
                    "fallback_used": False,
                }
            )
        except Exception as e:
            logger.error(
                f"Unexpected error occurred during multi-signal classification: {e}"
            )
            raise ActionError(
                f"Error occurred during multi-signal classification: {str(e)}"
            )

    # Fall back to text-based classification
    logger.info(f"Attempting text-based classification for file '{file_name}'")
    # Get layouts with summaries for text-based classification
    layouts_with_summaries = [layout for layout in all_layouts if layout.summary]
    if not layouts_with_summaries:
        logger.warning(
            f"No layouts with summaries found for data model {data_model_name}"
        )
        raise ActionError(
            f"No layouts found for data model {data_model_name} with summaries"
        )
    try:
        summary = agent_client.summarize(file_name)

        # Match the summary of the document to a layout
        classified_layouts = [
            CategorizedSummary(
                summary=layout.summary,
                category=layout.name,
            )
            for layout in layouts_with_summaries
        ]

        # Match the summary to a layout in this data model
        match, score = agent_client.categorize(classified_layouts, summary)

        logger.info(
            f"Text-based classification result: '{match.category}' with confidence {score}"
        )

        if score >= expected_confidence:
            return Response(
                result={
                    "Message": f"Document matched to {match.category} with confidence {score:.3f}",
                    "layout_name": match.category,
                    "confidence": score,
                    "method": "text",
                    "fallback_used": False,
                }
            )
        else:
            logger.warning(
                f"Best match '{match.category}' with confidence {score:.3f} below threshold {expected_confidence}"
            )
            return Response(
                result={
                    "Message": f"No layout matched with expected confidence. Best match was {match.category} with confidence {score:.3f}.",
                    "layout_name": "NOT FOUND",
                    "confidence": score,
                    "method": "text",
                    "fallback_used": False,
                }
            )

    except Exception as e:
        logger.error(f"Error during text-based classification: {e}")
        raise ActionError(f"Error during text classification: {str(e)}")


@query
def set_document_layout_summary(
    datasource: DocumentIntelligenceDataSource,
    data_model_name: str,
    layout_name: str,
    summary: str,
) -> Response[dict[str, Any]]:
    """Set the summary for a document layout.

    Args:
        datasource: The document intelligence data source connection
        data_model_name: The name of the data model
        layout_name: The name of the document layout
        summary: The summary for the document layout
    Returns:
        Response containing success message
    Raises:
        ActionError: If layout not found
    """
    data_model_name = normalize_name(data_model_name)
    layout_name = normalize_name(layout_name)

    layout = DocumentLayout.find_by_name(datasource, data_model_name, layout_name)
    if not layout:
        raise ActionError(
            f"Layout with name {layout_name} not found in data model {data_model_name}"
        )

    layout.summary = summary
    layout.update(datasource)

    return Response(
        result={"Message": f"Summary set on document layout {layout_name} successfully"}
    )


@query
def set_translation_schema(
    datasource: DocumentIntelligenceDataSource,
    layout_name: str,
    data_model_name: str,
    translation_schema: str | dict[str, Any],
) -> Response[dict[str, Any]]:
    """
    Store a translation schema for an existing layout.
    Args:
        datasource: The document intelligence data source connection
        layout_name: Name of the layout to create translation schema for
        data_model_name: Name of the data model this layout belongs to
        translation_schema: The object corresponding to the translation schema
    Returns:
        Response containing success message and translation schema
    Raises:
        ActionError: If layout or data model not found, or schema invalid
    """
    data_model_name = normalize_name(data_model_name)
    layout_name = normalize_name(layout_name)

    # Find the layout
    layout = DocumentLayout.find_by_name(datasource, data_model_name, layout_name)
    if not layout:
        raise ActionError(
            f"Layout with name {layout_name} not found in data model {data_model_name}"
        )

    # Find the data model to get the business schema
    data_model = DataModel.find_by_name(datasource, data_model_name)
    if not data_model:
        raise ActionError(f"Data model with name {data_model_name} not found")

    # Make sure the translation schema is a dict
    if isinstance(translation_schema, str):
        translation_schema = json.loads(translation_schema)
        if not isinstance(translation_schema, dict):
            raise ActionError(
                f"Translation schema should be a JSON object: {translation_schema}"
            )

    # Validates that the translation schema is a valid Mapping object
    if "rules" not in translation_schema:
        raise ActionError(
            f"Translation schema should have a 'rules' key: {translation_schema}"
        )
    _ = Mapping(rules=[MappingRow(**rule) for rule in translation_schema["rules"]])

    # Update each document with the new translation schema
    transformer = TransformDocumentLayout()
    docs = Document.find_by_document_layout(datasource, data_model_name, layout_name)
    for doc in docs:
        # Re-transform the extracted content into translated content with the new translation rules (implicitly checks that the translation rules are a valid Mapping object)
        transformed_content = transform_content(
            transformer, doc.extracted_content, translation_schema
        )  # type: ignore

        # Store the update, but don't save it.
        doc.translated_content = transformed_content

    # Commit the updates to the docs
    for doc in docs:
        doc.update(datasource)

    # Finally, update the layout with the new translation schema after all documents are updated
    layout.translation_schema = translation_schema
    layout.update(datasource)

    return Response(
        result={
            "message": f"Translation schema set on layout {layout_name} successfully. Reprocessed {len(docs)} documents",
            "translation_schema": translation_schema,
        }
    )


@query
def update_layout_extraction_config(
    datasource: DocumentIntelligenceDataSource,
    name: str,
    data_model_name: str,
    extraction_config: str | dict[str, Any],
) -> Response[dict[str, Any]]:
    """Update the extraction configuration for a layout. This is a power-tool which is only appropriate for users which understand how
    the extraction configuration is used with document layouts.

    Args:
        datasource: The document intelligence data source connection
        name: The name of the layout
        data_model_name: The name of the data model this layout belongs to
        extraction_config: The JSON configuration for extraction settings.
                          Can be either a JSON string or a Python dict.

    Returns:
        Response containing the updated layout

    Raises:
        ActionError: If the layout is not found or configuration is invalid
    """
    data_model_name = normalize_name(data_model_name)
    name = normalize_name(name)

    try:
        existing_layout = DocumentLayout.find_by_name(datasource, data_model_name, name)
        if not existing_layout:
            raise ActionError(f"Layout with name {name} not found")

        # Parse and validate the extraction configuration
        if isinstance(extraction_config, str):
            try:
                parsed_config = json.loads(extraction_config)
                if not isinstance(parsed_config, dict):
                    raise ActionError(
                        f"Extraction configuration should be a JSON object: {extraction_config}"
                    )
            except json.JSONDecodeError as e:
                raise ActionError(f"Invalid JSON in extraction configuration: {e}")
        elif isinstance(extraction_config, dict):
            parsed_config = extraction_config

        # Update the layout with the new extraction configuration
        existing_layout.extraction_config = parsed_config
        existing_layout.update(datasource)

        # Fetch and return the updated layout
        updated_layout = DocumentLayout.find_by_name(datasource, data_model_name, name)
        return Response(result=updated_layout.model_dump())

    except Exception as e:
        logger.error(
            f"Error updating extraction configuration for layout {name}: {str(e)}"
        )
        raise ActionError(f"Failed to update extraction configuration: {str(e)}") from e


@query
def set_document_layout_prompt(
    datasource: DocumentIntelligenceDataSource,
    name: str,
    data_model_name: str,
    prompt: str,
) -> Response[dict[str, Any]]:
    """Set the system prompt for a document layout. This is a power-tool which is only appropriate for users which understand how
    the prompt is used with document layouts.

    Args:
        datasource: The document intelligence data source connection
        name: The name of the layout
        data_model_name: The name of the data model this layout belongs to
        prompt: The prompt for the layout

    Returns:
        Response containing the updated layout

    Raises:
        ActionError: If the layout is not found or configuration is invalid
    """
    data_model_name = normalize_name(data_model_name)
    name = normalize_name(name)

    try:
        existing_layout = DocumentLayout.find_by_name(datasource, data_model_name, name)
        if not existing_layout:
            raise ActionError(f"Layout with name {name} not found")

        # Update the layout with the new prompt
        existing_layout.system_prompt = prompt
        existing_layout.update(datasource)

        # Fetch and return the updated layout
        updated_layout = DocumentLayout.find_by_name(datasource, data_model_name, name)
        return Response(result=updated_layout.model_dump())

    except Exception as e:
        logger.error(f"Error setting prompt for layout {name}: {str(e)}")
        raise ActionError(f"Failed to set prompt: {str(e)}") from e
