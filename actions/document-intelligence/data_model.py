import json
import logging
from typing import Any

from data_sources import DocumentIntelligenceDataSource
from layout import _create_or_update_default_layout, _generate_translation_schema
from sema4ai.actions import ActionError, Response, action
from sema4ai.data import get_connection, query
from sema4ai_docint import build_di_service
from sema4ai_docint.agent_server_client import AgentServerClient, CategorizedSummary
from sema4ai_docint.models import (
    DataModel,
    Document,
    DocumentLayout,
)
from sema4ai_docint.models.constants import PROJECT_NAME
from sema4ai_docint.utils import normalize_name
from validation import _regenerate_quality_checks

logger = logging.getLogger(__name__)


def _drop_view(datasource: DocumentIntelligenceDataSource, view_name: str) -> None:
    """
    Drop views from the data server.

    Args:
        datasource: The document intelligence data source connection
        view_names: The names of the views to drop
    """
    get_connection().execute_sql(f"DROP VIEW IF EXISTS {PROJECT_NAME}.{view_name}")


@action
def generate_data_model_from_file(file_name: str) -> Response[dict[str, Any]]:
    """Generate a data model schema from an uploaded document file.

    Args:
        file_name: The name of the file to generate a data model from

    Returns:
        Response with generated schema and success message

    Raises:
        ActionError: If schema generation fails
    """
    client = AgentServerClient()
    try:
        schema = client.generate_schema(file_name)
    except Exception as e:
        raise ActionError(f"Failed to generate data model schema: {e}") from e

    return Response(
        result={"message": "Data model generated successfully", "schema": schema}
    )


@query
def describe_data_model(
    datasource: DocumentIntelligenceDataSource, data_model_name: str
) -> Response[dict[str, Any]]:
    """Retrieve and return a data model by name.

    Args:
        datasource: The document intelligence data source connection
        data_model_name: The name of the data model.

    Returns:
        Response The data model

    Raises:
        ActionError: If data model not found
    """
    data_model_name = normalize_name(data_model_name)
    data_model = DataModel.find_by_name(datasource, data_model_name)
    if not data_model:
        raise ActionError(f"Data model with name {data_model_name} not found")

    return Response(result=data_model.model_dump())


@query
def create_data_model_from_schema(
    datasource: DocumentIntelligenceDataSource,
    name: str,
    description: str,
    json_schema_text: str,
    prompt: str | None = None,
    summary: str | None = None,
) -> Response[dict[str, Any]]:
    """Create a new data model from JSON schema. Creates business views and default layout.

    Args:
        datasource: The document intelligence data source connection
        name: The name of the data model
        description: The description of the data model
        json_schema_text: The JSON schema to use to create the data model
        prompt: The prompt for the data model
        summary: (optional) The summary of the data model

    Returns:
        Response The data model

    Raises:
        ActionError: If data model already exists or creation fails
    """
    try:
        di_service = build_di_service(datasource)
        model = di_service.data_model.create_from_schema(
            name, description, json_schema_text, prompt, summary
        )
    except Exception as e:
        raise ActionError(f"Failed to create data model from schema: {e}") from e

    return Response(result=model)


@query
def update_data_model(
    datasource: DocumentIntelligenceDataSource,
    name: str,
    description: str,
    json_schema_text: str,
    prompt: str | None = None,
) -> Response[dict[str, Any]]:
    """Update a data model schema and regenerate views, layouts, and quality checks.

    Args:
        datasource: The document intelligence data source connection
        name: The name of the data model
        description: The new description for the data model
        json_schema_text: The JSON schema to use to update the data model
        prompt: The prompt for the data model

    Returns:
        Response The data model

    Raises:
        ActionError: If data model not found or update fails
    """
    model_json_schema = json.loads(json_schema_text)
    name = normalize_name(name)

    # First get the existing data model to check if name changed
    existing_data_model = DataModel.find_by_name(datasource, name)
    if not existing_data_model:
        raise ActionError(f"Data model with name {name} not found")

    data_model = DataModel.find_by_name(datasource, name)
    if not data_model:
        raise ActionError(f"Data model with name {name} not found")

    # Update the summary if the description or schema has changed
    description_changed = description != existing_data_model.description
    schema_changed = model_json_schema != existing_data_model.model_schema
    if description_changed or schema_changed:
        client = AgentServerClient()
        data_model.summary = client.summarize_with_args(
            {
                "Data model name": name,
                "Data model description": description,
                "Data model schema": model_json_schema,
            }
        )

    # Update the data model
    data_model.description = description
    data_model.model_schema = model_json_schema
    data_model.prompt = prompt
    data_model.update(datasource)

    # Create views
    try:
        create_business_views(datasource, name)
    except Exception as e:
        logger.error(f"Error creating views for data model {name}: {str(e)}")
        raise ActionError(
            f"Failed to create views for data model {name}: {str(e)}"
        ) from e

    # Create default layout using the business schema
    _create_or_update_default_layout(datasource, name, model_json_schema)

    # Update translation schema for each layout related to this data model
    layouts = DocumentLayout.find_by_data_model(datasource, name)
    for layout in layouts:
        if layout.name == "default":
            continue
        translation_schema = _generate_translation_schema(
            model_json_schema, layout.extraction_schema
        )
        layout.update_translation_schema(datasource, translation_schema)

    # Regenerate quality checks
    try:
        _regenerate_quality_checks(name, datasource)
    except Exception as e:
        logger.error(
            f"Error regenerating quality checks for data model {name}: {str(e)}"
        )
        raise ActionError(
            f"Failed to regenerate quality checks for data model {name}: {str(e)}"
        ) from e

    # Fetch the final data_model
    new_data_model = data_model.find_by_name(datasource, name)
    if not new_data_model:
        raise ActionError(f"Failed to create data model: {name}")

    return Response(
        result={
            "message": "Data model updated successfully",
            "new_data_model": new_data_model.to_json(),
        }
    )


@query
def set_data_model_prompt(
    datasource: DocumentIntelligenceDataSource, name: str, prompt: str
) -> Response[dict[str, Any]]:
    """Set the system prompt for a data model.

    Args:
        datasource: The document intelligence data source connection
        name: The name of the data model
        prompt: The prompt for the data model

    Returns:
        Response with updated data model

    Raises:
        ActionError: If data model not found or prompt setting fails
    """
    name = normalize_name(name)
    data_model = DataModel.find_by_name(datasource, name)
    if not data_model:
        raise ActionError(f"Data model with name {name} not found")

    data_model.set_prompt(datasource, prompt)

    updated_data_model = data_model.find_by_name(datasource, name)
    if not updated_data_model:
        raise ActionError(f"Failed to set prompt for data model: {name}")

    return Response(result=updated_data_model.model_dump())


@query
def create_business_views(
    datasource: DocumentIntelligenceDataSource, data_model_name: str, force: bool = False
) -> Response[dict[str, Any]]:
    """Create SQL views for a data model in the database.

    Args:
        datasource: The document intelligence data source connection
        data_model_name: The name of the data model
        force: Whether to force the creation of views even if they already exist (default: False)

    Returns:
        Response with success message

    Raises:
        ActionError: If data model not found, project creation fails, or view generation fails
    """
    try:
        di_service = build_di_service(datasource)
        result = di_service.data_model.create_business_views(data_model_name, force=force)
    except Exception as e:
        raise ActionError(f"Failed to create business views: {e}") from e

    return Response(result=result)


# work-with-documents actions
@query
def list_data_models(
    datasource: DocumentIntelligenceDataSource,
) -> Response[list[dict[str, Any]]]:
    """Retrieve all data models from the database.

    Args:
        datasource: The document intelligence data source connection

    Returns:
        Response The list of data models.
    """
    data_models = DataModel.find_all(datasource)
    return Response(result=[data_model.model_dump() for data_model in data_models])


@query
def choose_data_model(
    datasource: DocumentIntelligenceDataSource,
    file_name: str,
    expected_confidence: float = 0.7,
) -> Response[dict]:
    """Match a document to the best data model using AI classification.
    Args:
        datasource: The document intelligence data source connection
        file_name: The name of an uploaded file
        expected_confidence: (optional, default=0.7) The minimum confidence score for a match to be returned

    Returns:
        Response with matched data model and confidence score
    """
    data_models = DataModel.find_all(datasource)
    if not data_models:
        return Response(result={"Message": "No data models found."})

    # Filter to data_models that have a summary
    data_models = [data_model for data_model in data_models if data_model.summary]
    if not data_models:
        return Response(
            result={
                "Message": "Data models exist in the system, but no data models have summaries. Load a document into a data model to define a summary."
            }
        )

    # Summarize the current file
    agent_client = AgentServerClient()
    summary = agent_client.summarize(file_name)

    # Match the summary of the novel document to a data model.
    classified_data_models = [
        CategorizedSummary(
            summary=data_model.summary,
            category=data_model.name,
        )
        for data_model in data_models
    ]

    match, score = agent_client.categorize(
        classified_data_models,
        summary,
    )

    if score >= expected_confidence:
        return Response(
            result={
                "Message": f"Document matched to {match.category} with confidence {score}",
                "matched_data_model_name": match.category,
                "match_confidence": score,
            }
        )
    else:
        return Response(
            result={
                "Message": f"No data model matched the summary with the expected confidence. Best match was {match.category} with confidence {score}",
                "matched_data_model_name": match.category,
                "match_confidence": score,
            }
        )


@query
def set_data_model_summary(
    datasource: DocumentIntelligenceDataSource, data_model_name: str, summary: str
) -> Response[dict[str, Any]]:
    """Set a summary for a data model used in document matching.

    Args:
        datasource: The document intelligence data source connection
        data_model_name: The name of the data model
        summary: The summary for the data model

    Returns:
        Response with success message

    Raises:
        ActionError: If data model not found
    """
    data_model_name = normalize_name(data_model_name)
    data_model = DataModel.find_by_name(datasource, data_model_name)
    if not data_model:
        raise ActionError(f"Data model with name {data_model_name} not found")

    data_model.summary = summary
    data_model.update(datasource)

    return Response(
        result={"Message": f"Summary set on data model {data_model_name} successfully"}
    )


@query
def delete_data_model_after_explicit_confirmation(
    datasource: DocumentIntelligenceDataSource,
    data_model_name: str,
    deletion_confirmation: str = "",
) -> Response[dict[str, Any]]:
    """Delete a data model and all its associated layouts, documents, and views. Must be called after explicit confirmation.
    This action can be called only after user has explicitly typed 'PERMANENTLY DELETE' and not just agreed to the warning message.

    This action performs a cascading delete of:
    - All documents associated with the data model
    - All layouts associated with the data model
    - All database views created for the data model
    - The data model itself

    WARNING: This operation is non-recoverable. All data will be permanently deleted. User must type 'PERMANENTLY DELETE'.

    Args:
        datasource: The document intelligence data source connection
        data_model_name: The name of the data model to delete
        deletion_confirmation: Confirmation string typed by the user. User must explicitly type 'PERMANENTLY DELETE'.
                         This is a safety measure to prevent accidental deletions, should not be auto-populated.

    Returns:
        Response with deletion summary including counts of deleted resources

    Raises:
        ActionError: If the data model doesn't exist, confirmation code doesn't match, or deletion fails
    """
    if deletion_confirmation != "PERMANENTLY DELETE":
        raise ActionError(
            f"Deletion of data model '{data_model_name}' requires explicit confirmation. "
            f"WARNING: This will permanently delete the data model and all associated resources."
        )

    data_model_name = normalize_name(data_model_name)

    # Check if data model exists
    data_model = DataModel.find_by_name(datasource, data_model_name)
    if not data_model:
        raise ActionError(f"Data model with name {data_model_name} not found")

    # Get counts of resources that will be deleted for user awareness
    documents = Document.find_by_data_model(datasource, data_model_name)
    layouts = DocumentLayout.find_by_data_model(datasource, data_model_name)
    view_count = len(data_model.views) if data_model.views else 0

    logger.warning(
        f"Deleting data model '{data_model_name}' with {len(documents)} documents, "
        f"{len(layouts)} layouts, and {view_count} views"
    )

    deletion_summary = {
        "data_model_name": data_model_name,
        "deleted_documents": 0,
        "deleted_layouts": 0,
        "deleted_views": 0,
        "errors": [],
    }

    try:
        # 1. Bulk delete all documents associated with this data model
        if documents:
            try:
                deleted_docs_count = Document.delete_by_data_model(
                    datasource, data_model_name
                )
                deletion_summary["deleted_documents"] = deleted_docs_count
            except Exception as e:
                deletion_summary["errors"].append(
                    f"Error bulk deleting documents: {str(e)}"
                )
                logger.error(
                    f"Error bulk deleting documents for data model {data_model_name}: {str(e)}"
                )

        # 2. Bulk delete all layouts associated with this data model
        if layouts:
            try:
                deleted_layouts_count = DocumentLayout.delete_by_data_model(
                    datasource, data_model_name
                )
                deletion_summary["deleted_layouts"] = deleted_layouts_count
            except Exception as e:
                deletion_summary["errors"].append(
                    f"Error bulk deleting layouts: {str(e)}"
                )
                logger.error(
                    f"Error bulk deleting layouts for data model {data_model_name}: {str(e)}"
                )

        # 3. Drop all database views associated with this data model
        if data_model.views:
            for view in data_model.views:
                try:
                    view_name = view.get("name")
                    if view_name:
                        _drop_view(datasource, view_name)
                        deletion_summary["deleted_views"] += 1
                except Exception as e:
                    deletion_summary["errors"].append(
                        f"Error dropping view {view_name}: {str(e)}"
                    )
                    logger.error(f"Error dropping view {view_name}: {str(e)}")

        # 4. Finally, delete the data model itself
        success = data_model.delete(datasource)
        if not success:
            raise ActionError(f"Failed to delete data model {data_model_name}")

        # Check if there were any errors during deletion
        if deletion_summary["errors"]:
            error_message = f"Failed to delete data model '{data_model_name}' due to errors: {', '.join(deletion_summary['errors'])}"
            logger.error(error_message)
            raise ActionError(error_message)

        # If no errors, return success response
        message = f"Data model '{data_model_name}' and all associated resources deleted successfully"
        return Response(
            result={"message": message, "deletion_summary": deletion_summary}
        )

    except Exception as e:
        logger.error(f"Failed to delete data model {data_model_name}: {str(e)}")
        raise ActionError(
            f"Failed to delete data model {data_model_name}: {str(e)}"
        ) from e
