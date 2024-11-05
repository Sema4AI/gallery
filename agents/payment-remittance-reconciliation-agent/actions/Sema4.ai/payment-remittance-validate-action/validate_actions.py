import traceback
from typing import Optional
import numpy as np
import pandas as pd
from pydantic import BaseModel

from sema4ai.actions import action
from sema4ai.di_client import DocumentIntelligenceClient
from sema4ai.di_client.document_intelligence_client.models.content_state import (
    ContentState,
)
from sema4ai.di_client.document_intelligence_client.models.document_work_item import (
    DocumentWorkItem,
)
from sema4ai.di_client.document_intelligence_client.models.computed_document_content import (
    ComputedDocumentContent,
)

from validation.validation_processor import ValidationProcessor

from utils.logging.validate_logging_module import configure_logging
from models.validate_models import (
    ProcessingPhase,
    ExtractionResult,
    ValidationFinalResult,
    ValidationStatus,
    ActionResponse,
    ActionStatus,
)
from context.validate_agent_context_manager import ValidationAgentContextManager
from utils.logging.ultimate_serializer import (
    serialize_any_object_safely,
    clean_any_object_safely,
)


# Configure logging
logger = configure_logging(
    logger_name=__name__, log_config_path="logging-validate-actions.conf"
)


def create_di_client() -> DocumentIntelligenceClient:
    """
    Create and return a Document Intelligence client.

    Returns:
        DocumentIntelligenceClient: An instance of the Document Intelligence client.
    """
    return DocumentIntelligenceClient()


@action
def get_remittance_work_item_for_validation(remittance_id: str) -> DocumentWorkItem:
    """
    Retrieve a remittance work item.

    This action fetches the work item for a given remittance ID. It should be called
    at the beginning of the remittance processing workflow to obtain the document
    details and raw contentm for validation.

    Args:
        remittance_id (str): The unique identifier of the remittance document.

    Returns:
        DocumentWorkItem: An object containing details of the remittance work item.

    Raises:
        ActionsError: If an error occurs while fetching the remittance work item.

    Example:
        work_item = get_remittance_work_item("REM-2024-001")
    """
    logger.info(f"Starting to fetch work item for remittance ID: {remittance_id}")
    try:
        # Initialize the Document Intelligence client
        doc_intel_client: DocumentIntelligenceClient = create_di_client()
        logger.debug("Document Intelligence client created successfully.")

        # Retrieve the remittance work item
        remittance_work_item: DocumentWorkItem = (
            doc_intel_client.get_document_work_item(remittance_id)
        )
        logger.info(f"Retrieved work item for remittance ID: {remittance_id}")
        return remittance_work_item

    except Exception as e:
        logger.error(
            f"Error occurred while fetching remittance work item for ID: {remittance_id}",
            exc_info=True,
        )
        raise e


@action
def run_remittance_extraction(remittance_id: str) -> ActionResponse:
    """
    Perform data extraction on a remittance document.

    This action executes the extraction process for a given remittance ID. It should be called
    after retrieving the work item. The function extracts relevant information from the raw document
    conten including fields and tabular data.

    Args:
        remittance_id (str): The unique identifier of the remittance document.
    Returns:
        ActionResponse: An object containing the status, message, agent insight context, and additional data.
    """

    logger.info(f"Starting extraction process for remittance ID: {remittance_id}")
    doc_intel_client: DocumentIntelligenceClient = create_di_client()
    agent_context_manager = None
    try:
        logger.debug("Document Intelligence client created successfully.")

        # Retrieve the remittance work item
        remittance_work_item = doc_intel_client.get_document_work_item(remittance_id)
        document_name = remittance_work_item.source_document.document_name
        logger.info(f"Retrieved work item for document: {document_name}")

        # Get the Agent context and send back to agent
        agent_context_manager = ValidationAgentContextManager(
            remittance_id, document_name, load_existing=True
        )

        # Fetch the raw content for the remittance document
        raw_content = doc_intel_client.get_document_content(
            remittance_id, ContentState.RAW
        )
        logger.info(f"Fetched raw content for document: {document_name}")

        # Initialize the Remittance Processor and run extraction
        remittance_processor = ValidationProcessor(
            remittance_work_item, agent_context_manager=agent_context_manager
        )

        extraction_result: ExtractionResult = (
            remittance_processor.extract_and_structure_content(raw_content)
        )
        agent_context_manager.add_event(
            "Extraction Complete",
            f"Extraction process completed successfully for document: {document_name}",
        )
        logger.info(
            f"Extraction and structuring completed for document: {document_name}"
        )
        logger.info(
            f"Extracted content from Processor is : {serialize_any_object_safely(extraction_result.document_content)}"
        )

        # Clean the content before passing the ExtractedContent to DI service
        cleaned_extracted_content = clean_any_object_safely(
            extraction_result.document_content
        )

        # Store the cleaned extracted content
        doc_intel_client.store_extracted_content(cleaned_extracted_content)
        agent_context_manager.add_event(
            "Extracted Content Stored",
            f"Stored extracted content for document: {document_name}",
        )
        logger.info(f"Stored extracted content for document: {document_name}")

        # Get the updated agent context
        agent_context = agent_context_manager.get_agent_context()

        # Determine if there were any errors during extraction
        extraction_status = agent_context.get_phase_status(ProcessingPhase.EXTRACTION)
        if extraction_status == "Failed":
            status = ActionStatus.FAILURE
            message = f"Extraction failed for document: {document_name}. Please review the errors and take corrective actions."
            logger.error(
                f"Extraction failed for document: {document_name}. Please review the errors and take corrective actions."
            )
            logger.error(
                f"Extraction Errors: {agent_context.get_validation_results(ProcessingPhase.EXTRACTION)}"
            )
            _add_document_format_to_context(
                remittance_work_item, doc_intel_client, agent_context_manager
            )
        else:
            status = ActionStatus.SUCCESS
            message = f"Extraction completed successfully for document: {document_name}. Proceed to the next step in your runbook."

        # Store the Agent Context before returning
        agent_context_manager.store_context()

        logger.info(
            f"Extraction process completed with status: {status} for document: {document_name}"
        )
        return ActionResponse(
            status=status,
            message=message,
            agent_insight_context=agent_context,
            additional_data={"document_name": document_name},
        )
    except Exception as e:
        _add_document_format_to_context(
            remittance_work_item, doc_intel_client, agent_context_manager
        )
        return handle_action_exception(remittance_id, e, agent_context_manager)


@action
def run_remittance_transformation(remittance_id: str) -> ActionResponse:
    """
    Perform data transformation on extracted remittance data.
    This action executes the transformation process for a given remittance ID. It should be called
    after successful extraction. It refines the data by standardizing formats,
    computing fields, and preparing the data for further processing.

    Args:
        remittance_id (str): The ID of the remittance.

    Returns:
        ActionResponse: An ActionResponse object containing the status, message, agent insight context, and additional data.

    """
    logger.info(f"Starting transformation process for remittance ID: {remittance_id}")
    agent_context_manager = None
    try:
        doc_intel_client: DocumentIntelligenceClient = create_di_client()
        logger.debug("Document Intelligence client created successfully.")

        # Retrieve the remittance work item and extracted content
        remittance_work_item = doc_intel_client.get_document_work_item(remittance_id)
        document_name = remittance_work_item.source_document.document_name
        extracted_content = doc_intel_client.get_document_content(
            remittance_id, ContentState.EXTRACTED
        )
        logger.info(f"Retrieved extracted content for document: {document_name}")

        # Initialize the Remittance Processor and run transformation
        agent_context_manager = ValidationAgentContextManager(
            remittance_id, document_name, load_existing=True
        )
        remittance_processor = ValidationProcessor(
            remittance_work_item, agent_context_manager=agent_context_manager
        )

        transformation_result = remittance_processor.transform_and_enrich_content(
            extracted_content
        )
        agent_context_manager.add_event(
            "Transformation Complete",
            f"Transformation process completed successfully for document: {document_name}",
        )
        logger.info(
            f"Transformation and enrichment completed for document: {document_name}"
        )

        # Clean and store the transformed content
        cleaned_transformed_content = clean_pydantic_object(
            transformation_result.document_content
        )
        doc_intel_client.store_transformed_content(cleaned_transformed_content)
        agent_context_manager.add_event(
            "Transformed Content Stored",
            f"Stored transformed content for document: {document_name}",
        )
        logger.info(f"Stored transformed content for document: {document_name}")

        # Get the updated agent context
        agent_context = agent_context_manager.get_agent_context()

        # Determine if there were any errors during transformation
        transformation_status = agent_context.get_phase_status(
            ProcessingPhase.TRANSFORMATION
        )
        if transformation_status == "Failed":
            status = ActionStatus.FAILURE
            message = f"Transformation failed for document: {document_name}. Please review the errors and take corrective actions."
            logger.error(
                f"Transformation failed for document: {document_name}. Please review the errors and take corrective actions."
            )
            logger.error(
                f"Transformation Errors: {agent_context.get_validation_results(ProcessingPhase.TRANSFORMATION)}"
            )
            _add_document_format_to_context(
                remittance_work_item, doc_intel_client, agent_context_manager
            )
        else:
            status = ActionStatus.SUCCESS
            message = f"Transformation completed successfully for document: {document_name}. Proceed to the next step in your runbook."

        # Store the Agent Context before returning
        agent_context_manager.store_context()

        logger.info(
            f"Transformation process completed with status: {status} for document: {document_name}"
        )
        return ActionResponse(
            status=status,
            message=message,
            agent_insight_context=agent_context,
            additional_data={"document_name": document_name},
        )
    except Exception as e:
        _add_document_format_to_context(
            remittance_work_item, doc_intel_client, agent_context_manager
        )
        return handle_action_exception(e, agent_context_manager)


@action
def run_remittance_validation(remittance_id: str) -> ActionResponse:
    """
    Perform validation on transformed remittance data.

    This action executes the validation process for a given remittance ID. It should be called
    after successful transformation. It applies business rules and checks data integrity.

    Args:
        remittance_id (str): The ID of the remittance.

    Returns:
        ActionResponse: An ActionResponse object containing the status, message, agent insight context, and additional data.
    """
    logger.info(f"Starting validation process for remittance ID: {remittance_id}")
    agent_context_manager = None
    try:
        doc_intel_client: DocumentIntelligenceClient = create_di_client()
        logger.debug("Document Intelligence client created successfully.")

        # Retrieve the remittance work item and
        remittance_work_item = doc_intel_client.get_document_work_item(remittance_id)
        document_name = remittance_work_item.source_document.document_name

        # Retrieve the transformed content
        transformed_content = doc_intel_client.get_document_content(
            remittance_id, ContentState.TRANSFORMED
        )
        logger.info(f"Retrieved transformed content for document: {document_name}")

        # Initialize the Remittance Processor and run validation
        agent_context_manager = ValidationAgentContextManager(
            remittance_id, document_name, load_existing=True
        )
        remittance_processor = ValidationProcessor(
            remittance_work_item, agent_context_manager=agent_context_manager
        )

        validation_final_result: ValidationFinalResult = (
            remittance_processor.validate_and_finalize_content(transformed_content)
        )
        agent_context_manager.add_event(
            "Validation Complete",
            f"Validation process completed for document: {document_name}",
        )
        logger.info(f"Validation completed for document: {document_name}")

        # If there are validatino errors, then computed content will be the validation results, otherwise it will be the transformed content
        # RFAArdless, save the the computed content in document database. If there are failures, we'l need to acess the validation results on the next call
        computed_content: ComputedDocumentContent = (
            validation_final_result.document_content
        )
        # Store teh computed content which is the same as transformed into document database
        logger.info(f"Storing computed content for document: {document_name}")
        doc_intel_client.store_computed_content(computed_content)
        logger.info(f"Stored computed content for document: {document_name}")
        agent_context_manager.add_event(
            "Computed Content Stored",
            f"Stored computed content for document: {document_name}",
        )

        # Get the updated agent context
        agent_context = agent_context_manager.get_agent_context()

        # Return Details to teh Agent based on if there are any failures
        if (
            validation_final_result.validation_status
            == ValidationStatus.VALIDATION_PASSED
        ):
            status = ActionStatus.SUCCESS
            message = f"Validation completed successfully for document: {document_name}. All checks passed."
        else:
            status = ActionStatus.FAILURE
            _add_document_format_to_context(
                remittance_work_item, doc_intel_client, agent_context_manager
            )
            validation_results = agent_context.get_validation_results(
                ProcessingPhase.VALIDATION
            )
            failed_rules = [r for r in validation_results.results if not r.passed]
            message = f"Validation failed for document: {document_name}. {len(failed_rules)} rule(s) failed. Please review the errors in the validation results and take corrective actions."
            logger.error(
                f"Validation failed for document: {document_name}. Failed rules: {[r.rule_id for r in failed_rules]}"
            )

        # Store the Agent Context before returning
        agent_context_manager.store_context()

        logger.info(
            f"Validation process completed with status: {status} for document: {document_name}"
        )
        return ActionResponse(
            status=status, message=message, agent_insight_context=agent_context
        )
    except Exception as e:
        _add_document_format_to_context(
            remittance_work_item, doc_intel_client, agent_context_manager
        )
        return handle_action_exception(remittance_id, e, agent_context_manager)


def _update_work_item_status(
    remittance_id: str, status: str, message: str, details: Optional[str]
) -> ActionResponse:
    logger.info(
        f"Updating status for remittance ID: {remittance_id} to {status}, status message: {message}"
    )
    if details:
        logger.info(f"Details: {details}")
    try:
        doc_intel_client: DocumentIntelligenceClient = create_di_client()
        logger.debug("Document Intelligence client created successfully.")

        # Update the work item with the provided status
        doc_intel_client.work_items_complete_stage(
            remittance_id, status, message, details
        )

        logger.debug(
            f"Successfully updated status for remittance ID: {remittance_id} to {status}"
        )

        # Send the detailed validation report to the user to it can be displayed on the Agent Chat
        return ActionResponse(
            status=ActionStatus.SUCCESS,
            message="Display the the detail Validation Report to the user",
            additional_data={"detailed_validation_report": details},
        )
    except Exception as e:
        logger.error(
            f"Error occurred while updating remittance processing status: {str(e)}",
            exc_info=True,
        )
        return ActionResponse(
            status=ActionStatus.FAILURE,
            message=f"An error occurred when updating remittance to {status}: {str(e)}",
            additional_data={
                "error": str(e),
                "traceback": traceback.format_exc().splitlines(),
            },
        )


@action
def update_work_item_with_validation_failure(
    remittance_id: str,
    validation_failure_summary: str,
    validation_failure_detailed_report: str,
) -> ActionResponse:
    """
    Update the work item status to 'FAILURE' with validation failure details.

    Args:
        remittance_id (str): The ID of the remittance.
        validation_failure_summary (str): Summary of the validation failure.
        validation_failure_detailed_report (str): Detailed report of the validation failure.

    Returns:
        ActionResponse: The response indicating the success or failure of the action.
    """
    return _update_work_item_status(
        remittance_id,
        "FAILURE",
        validation_failure_summary,
        validation_failure_detailed_report,
    )


@action
def update_work_item_with_validation_success(
    remittance_id: str,
    validation_success_summary: str,
    validation_success_detailed_report: str,
) -> ActionResponse:
    """
    Update the work item status to 'SUCCESS' after validation succeeds.

    Args:
        remittance_id (str): The ID of the remittance.
        validation_success_summary (str): Summary of the validation success report.
        validation_success_detailed_report (str): Detailed report of the validation success.

    Returns:
        ActionResponse: The response indicating the success or failure of the action.
    """
    return _update_work_item_status(
        remittance_id,
        "SUCCESS",
        validation_success_summary,
        validation_success_detailed_report,
    )


def clean_pydantic_object(obj: BaseModel) -> BaseModel:
    """
    Clean a Pydantic object to ensure all data is serializable.
    """
    cleaned_data = {}
    for field_name, field_value in obj.dict().items():
        if isinstance(field_value, BaseModel):
            cleaned_data[field_name] = clean_pydantic_object(field_value)
        elif isinstance(field_value, list):
            cleaned_data[field_name] = [
                clean_pydantic_object(item)
                if isinstance(item, BaseModel)
                else clean_value(item)
                for item in field_value
            ]
        elif isinstance(field_value, dict):
            cleaned_data[field_name] = {
                k: clean_pydantic_object(v)
                if isinstance(v, BaseModel)
                else clean_value(v)
                for k, v in field_value.items()
            }
        else:
            cleaned_data[field_name] = clean_value(field_value)
    return obj.__class__(**cleaned_data)


def clean_value(value):
    """
    Clean individual values to ensure they are serializable.
    """
    if isinstance(value, (pd.DataFrame, pd.Series)):
        return value.to_dict()
    elif isinstance(value, np.ndarray):
        return value.tolist()
    elif isinstance(value, np.integer):
        return int(value)
    elif isinstance(value, np.floating):
        return float(value)
    elif pd.api.types.is_scalar(value) and pd.isna(value):
        return None
    elif isinstance(value, (list, np.ndarray)):
        return [clean_value(v) for v in value]
    return value


def handle_action_exception(
    remittance_id: str,
    e: Exception,
    agent_context_manager: Optional[ValidationAgentContextManager] = None,
    custom_message: Optional[str] = None,
) -> ActionResponse:
    """
    Handle exceptions that occur during action execution.

    Args:
        e (Exception): The exception that occurred.
        agent_context_manager (Optional[AgentInsightContextManager]): The agent context manager.
        custom_message (Optional[str]): A custom message to include in the response.

    Returns:
        ActionResponse: The response indicating the failure of the action.
    """
    error_msg = f"Error occurred: {str(e)}"
    logger.error(error_msg, exc_info=True)

    # Update the work item to failure status
    doc_intel_client: DocumentIntelligenceClient = create_di_client()
    logger.error(f"Marking work item as failure for remittance ID: {remittance_id}")
    doc_intel_client.work_items_complete_stage(
        remittance_id,
        status="FAILURE",
        status_reason=custom_message
        or f"An error occurred during processing: {str(e)}",
        log_details_path=error_msg,
    )
    logger.error(f"Finishing marking Work item as failied: {remittance_id}")

    agent_context_on_error = None
    if agent_context_manager and agent_context_manager.get_agent_context():
        agent_context_manager.add_error(
            "Error Occurred", f"An error occurred: {str(e)}"
        )
        agent_context_manager.store_context()
        agent_context_on_error = agent_context_manager.get_agent_context()

    return ActionResponse(
        status=ActionStatus.FAILURE,
        agent_insight_context=agent_context_on_error,
        message=custom_message or f"An error occurred during processing: {str(e)}",
        additional_data={
            "error": str(e),
            "traceback": traceback.format_exc().splitlines(),
        },
    )


def _add_document_format_to_context(
    remittance_work_item: DocumentWorkItem,
    doc_intel_client: DocumentIntelligenceClient,
    agent_context_manager,
):
    """
    Add document format to the agent context manager.

    Args:
        remittance_work_item (DocumentWorkItem): The remittance work item.
        doc_intel_client (DocumentIntelligenceClient): The Document Intelligence client.
        agent_context_manager (AgentInsightContextManager): The agent context manager.
    """
    if remittance_work_item:
        prompt_details: dict = {
            "prompt_instructions": remittance_work_item.source_document.document_format.prompt_instructions,
            "prompt_examples": remittance_work_item.source_document.document_format.prompt_examples,
        }
        agent_context_manager.add_context("User Prompt Instructions", prompt_details)
        agent_context_manager = clean_any_object_safely(agent_context_manager)
