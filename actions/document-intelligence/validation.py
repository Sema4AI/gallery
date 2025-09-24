import json
import logging
from typing import Any, cast

from data_sources import DocumentIntelligenceDataSource
from pydantic import BaseModel
from sema4ai.actions import ActionError, Response
from sema4ai.data import query
from sema4ai_docint.agent_server_client import AgentServerClient
from sema4ai_docint.models import DataModel, initialize_dataserver
from sema4ai_docint.models.constants import PROJECT_NAME
from sema4ai_docint.utils import normalize_name
from sema4ai_docint.validation import (
    ValidationRule,
    validate_document_extraction,
)

logger = logging.getLogger(__name__)


class TestValidationRulesParams(BaseModel):
    """Parameters for the test_validation_rules function.

    Attributes:
        validation_rules: List of ValidationRule objects
        document_id: The ID of the document to validate
    """

    validation_rules: list[ValidationRule]
    document_id: str


class StoreValidationRulesParams(BaseModel):
    """Parameters for the store_validation_rules function.

    Attributes:
        validation_rules: List of ValidationRule objects
        data_model_name: The name of the data model
    """

    validation_rules: list[ValidationRule]
    data_model_name: str


def _regenerate_quality_checks(
    data_model_name: str,
    datasource: DocumentIntelligenceDataSource,
) -> dict[str, Any]:
    """Regenerate quality checks for a data model using existing rule descriptions.

    This method is useful when the data model views have been updated and the existing
    SQL queries in quality checks have become invalid. It regenerates the SQL queries
    while preserving the rule names and descriptions.

    Args:
        data_model_name: The name of the data model
        datasource: The document intelligence data source connection

    Returns:
        dict with the regenerated validation rules

    Raises:
        ValueError: If the regeneration fails or no existing quality checks are found
    """
    data_model_name = normalize_name(data_model_name)
    data_model = DataModel.find_by_name(datasource, data_model_name)
    if not data_model:
        raise ValueError(f"Data model with name {data_model_name} not found")

    if not data_model.views:
        raise ValueError(f"No views found for data model {data_model_name}")

    # Handle case where no quality checks exist
    if not data_model.quality_checks:
        return {
            "Message": "No existing quality checks found for data model. Use generate_quality_checks to create new ones.",
            "Rules": [],
            "RegeneratedCount": 0,
        }

    # Parse existing quality checks
    try:
        existing_rules = [ValidationRule(**rule) for rule in data_model.quality_checks]
    except Exception as e:
        raise ValueError(f"Failed to parse existing quality checks: {e}") from e

    # Generate new validation rules using the existing descriptions
    client = AgentServerClient()
    try:
        new_quality_checks = []
        for rule in existing_rules:
            new_quality_check = client.generate_validation_rules(
                rule.rule_description,
                data_model,
                datasource,
                limit_count=1,
            )
            new_quality_checks.append(new_quality_check[0])
        # Replace all existing rules with the newly generated ones
        updated_rules = new_quality_checks

        # Store the updated validation rules
        _store_validation_rules(datasource, data_model_name, updated_rules)

        return {
            "Message": "Quality checks regenerated successfully",
            "Rules": updated_rules,
            "RegeneratedCount": len(updated_rules),
        }

    except Exception as e:
        raise ValueError(f"Failed to regenerate validation rules: {e}") from e


def _store_validation_rules(
    datasource: DocumentIntelligenceDataSource,
    data_model_name: str,
    quality_checks: list[dict[str, str]],
) -> None:
    """Store the quality checks in the database.

    Args:
        datasource: The document intelligence data source connection
        data_model_name: The name of the data model
        quality_checks: A dict where each key is a view name and the value is a list of
                          quality checks: each containing rule_name, rule_description, and sql_query
    """
    try:
        data_model_name = normalize_name(data_model_name)
        data_model = DataModel.find_by_name(datasource, data_model_name)
        if not data_model:
            raise ActionError(f"Data model with name {data_model_name} not found")

        # Convert the list of dicts to ValidationRule objects and then to JSON-serializable dicts
        rules = [ValidationRule(**rule).model_dump() for rule in quality_checks]
        data_model.quality_checks = cast(Any, json.dumps(rules))

        data_model.update(datasource)
    except Exception as e:
        logger.error(f"Error storing quality checks: {str(e)}")
        raise ActionError(f"Error storing quality checks: {str(e)}") from e


@query
def generate_validation_rules(
    data_model_name: str,
    description: str | None,
    datasource: DocumentIntelligenceDataSource,
    limit_count: int = 1,
) -> Response[dict[str, Any]]:
    """
    Generate validation rules for a data model. This function requires either generates a single validation
    rule from the provided description or automatically generates `limit_count` validation rules. Callers
    must provide only one of `description` and `limit_count`, never both. This function should be called
    with a limit_count if the goal is to generate generic validation rules. This function should be called
    with the description if generating a specific rule.

    Args:
        data_model_name: The name of the data model for which to generate validation rules (string).
        description: Natural language description of the validation rules to generate (string, optional).
                     This is mutally exclusive with limit_count.
        datasource: The document intelligence data source connection that provides
                    access to the database and data model information
        limit_count: The maximum number of validation rules to generate (defaults to 1).
                     This is mutually exclusive with description.
    Returns:
        Response with the generated validation rules
    Raises:
        ActionError: If the validation rule generation fails.
    """
    if description and limit_count != 1:
        raise ActionError("If a description is provided, limit count must be 1")

    data_model_name = normalize_name(data_model_name)
    data_model = DataModel.find_by_name(datasource, data_model_name)
    if not data_model:
        raise ActionError(f"Data model with name {data_model_name} not found")

    if not data_model.views or not data_model.model_schema:
        raise ActionError(
            "Validation rules cannot be generated because views or schema are not found"
        )

    client = AgentServerClient()
    try:
        validation_rules = client.generate_validation_rules(
            data_model=data_model,
            datasource=datasource,
            limit_count=limit_count,
            rules_description=description,
        )

        # Check if there are any error cases in the generated rules
        error_rules = []
        valid_rules = []

        for rule in validation_rules:
            if rule.get("error_message") and rule.get("error_message").strip():
                # This is an error case - collect it for reporting
                error_rules.append(rule)
            elif rule.get("sql_query") and rule.get("sql_query").strip():
                # This is a valid rule
                valid_rules.append(rule)
            else:
                # Skip rules with neither valid SQL nor error message
                logger.warning(
                    f"Skipping rule '{rule.get('rule_name', 'unnamed')}' with no valid SQL or error message"
                )

        # Prepare response based on what we have
        if error_rules and valid_rules:
            # Mixed case: some valid rules, some errors
            response_summary = {
                "Message": f"Validation rules generation completed with mixed results. {len(valid_rules)} valid rules generated, {len(error_rules)} rules had data type errors.",
                "Valid_Rules_Count": len(valid_rules),
                "Error_Rules_Count": len(error_rules),
                "Valid_Rules": valid_rules,
                "Error_Rules": error_rules,
                "Note": "Valid rules can be stored using store_validation_rules. Error rules could not be created due to data type mismatches.",
            }
            return Response(result=response_summary)
        elif error_rules and not valid_rules:
            # All rules had errors
            error_summary = {
                "Message": "Validation rules generation completed with data type errors",
                "Valid_Rules_Count": 0,
                "Error_Rules_Count": len(error_rules),
                "Error_Rules": error_rules,
                "Note": "No valid rules could be created. All rules had data type issues that prevent safe SQL generation.",
            }
            return Response(result=error_summary)
        elif valid_rules and not error_rules:
            # All rules were valid
            success_summary = {
                "Message": "Validation rules generated successfully",
                "Valid_Rules_Count": len(valid_rules),
                "Valid_Rules": valid_rules,
            }
            return Response(result=success_summary)
        else:
            # No valid rules and no error rules (shouldn't happen)
            raise ActionError(
                "No valid validation rules could be generated and no error information was provided"
            )
    except Exception as e:
        raise ActionError(f"Failed to generate validation rules: {e}") from e


@query
def test_validation_rules(
    params: TestValidationRulesParams,
    datasource: DocumentIntelligenceDataSource,
) -> Response[dict[str, Any]]:
    """Test validation rules against a specific document to verify data quality and processing accuracy.

    Args:
        params: TestValidationRulesParams object containing:
            - validation_rules: List of ValidationRule objects that MUST contain at least one rule
            - document_id: The unique identifier of the document to validate against (string)
        datasource: The document intelligence data source connection that provides
                   access to the database containing the processed document data

    Returns:
        Response with the validation summary

    Raises:
        ActionError: If the validation process fails

    """
    try:
        validation_summary = validate_document_extraction(
            params.document_id, datasource, params.validation_rules
        )
        return Response(result=validation_summary)
    except Exception as e:
        raise ActionError(f"Failed to test validation rules: {e}")


@query
def store_validation_rules(
    params: StoreValidationRulesParams,
    datasource: DocumentIntelligenceDataSource,
) -> Response[dict[str, Any]]:
    """Store validation rules for a data model.

    Args:
        params: StoreValidationRulesParams object containing:
            - validation_rules: List of ValidationRule objects
            - data_model_name: The name of the data model
        datasource: The document intelligence data source connection

    Returns:
        Response confirming the storage operation

    Raises:
        ActionError: If the action fails
    """
    try:
        data_model_name = normalize_name(params.data_model_name)
        data_model = DataModel.find_by_name(datasource, data_model_name)
        if not data_model:
            raise ActionError(f"Data model with name {data_model_name} not found")

        # Convert the list of dicts to ValidationRule objects and then to JSON-serializable dicts
        rules = [rule.model_dump() for rule in params.validation_rules]
        data_model.quality_checks = cast(Any, json.dumps(rules))

        data_model.update(datasource)

        return Response(
            result={
                "Message": f"Successfully stored {len(params.validation_rules)} validation rules for data model '{data_model_name}'",
                "Stored_Rules_Count": len(params.validation_rules),
                "Data_Model_Name": data_model_name,
            }
        )
    except Exception as e:
        logger.error(f"Error storing validation rules: {str(e)}")
        raise ActionError(f"Error storing validation rules: {str(e)}") from e


@query
def validate_document(
    data_model_name: str,
    document_id: str,
    datasource: DocumentIntelligenceDataSource,
) -> Response[dict[str, Any]]:
    """Validate a document against quality checks.

    Args:
        data_model_name: The name of the data model
        document_id: The ID of the document to validate
        datasource: The document intelligence data source connection

    Returns:
        Response containing validation results with overall status and rule outcomes

    Raises:
        ActionError: If data model not found, no quality checks exist, project creation fails, or validation fails
    """
    data_model_name = normalize_name(data_model_name)
    data_model = DataModel.find_by_name(datasource, data_model_name)
    if not data_model:
        raise ActionError(f"Data model with name {data_model_name} not found")

    if not data_model.quality_checks:
        raise ActionError(f"No quality checks found for data model {data_model_name}")

    # Initialize the objects in MindsDB (project)
    try:
        initialize_dataserver(PROJECT_NAME, data_model.views)
    except Exception as e:
        raise ActionError(
            "Failed to create the document intelligence data-server project"
        ) from e

    # Parse quality checks - all stored rules should be valid
    quality_checks = [ValidationRule(**rule) for rule in data_model.quality_checks]

    validation_summary = validate_document_extraction(
        document_id, datasource, quality_checks
    )

    if validation_summary.overall_status == "failed":
        raise ActionError(
            f"Document validation encountered errors: {validation_summary.model_dump()}"
        )
    return Response(result=validation_summary.model_dump())
