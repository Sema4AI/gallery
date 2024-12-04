from decimal import Decimal

import traceback
from typing import Optional

from sema4ai.actions import action
from sema4ai.di_client import DocumentIntelligenceClient
from sema4ai.di_client.document_intelligence_client.models.content_state import (
    ContentState,
)
from sema4ai.di_client.document_intelligence_client.models.document_work_item import (
    DocumentWorkItem,
)
from sema4ai.di_client.document_intelligence_client.models.processing_status import (
    ProcessingStatus,
)


from models.reconciliation_models import ReconciliationResponse
from reconciliation_ledger.db.invoice_loader import InvoiceLoader
from reconciliation_ledger.services.invoice_reconciliation_service import (
    InvoiceReconciliationLedgerService,
)
from context.reconciliation_agent_context_manager import (
    ReconciliationAgentContextManager,
)

from reconciliation_ledger.reconciliation_constants import DatabaseConstants
from models.reconciliation_models import ActionResponse, ActionStatus
from utils.logging.reconcile_logging_module import configure_logging
from utils.commons.path_utils import get_full_path
from utils.commons.formatting import parse_numeric_field
from utils.logging.ultimate_serializer import serialize_any_object_safely

logger = configure_logging(
    logger_name=__name__, log_config_filename="logging-reconcile.conf"
)

def create_di_client() -> DocumentIntelligenceClient:
    """Create and configure Document Intelligence client."""
    return DocumentIntelligenceClient()


@action
def get_remittance_work_item_for_reconciliation(remittance_id: str) -> ActionResponse:
    """
    This method retrieves the remittance work item using the provided remittance ID to start the reconciliation process.

    Args:
        remittance_id (str): ID of the remittance


    Returns:
        ActionResponse: Response object containing the status, message, and additional data if any.
    """
    logger.debug(f"Starting remittance work item retrieval for ID: {remittance_id}")
    try:
        di_client = create_di_client()
        work_item: DocumentWorkItem = di_client.get_document_work_item(remittance_id)
        customer_id = work_item.non_tbl_data.get("Customer ID")

        context_manager = ReconciliationAgentContextManager(
            remittance_id, work_item.source_document.document_name, customer_id
        )

        context_manager.add_event(
            "Retrieval Started",
            f"Retrieving work item for remittance ID: {remittance_id}",
        )

        if work_item.processing_status != ProcessingStatus.VALIDATION_COMPLETED:
            error_msg = f"Invalid work item status: {work_item.processing_status}. Expected: Validation Completed"
            logger.error(error_msg)
            context_manager.add_event("Error", error_msg)
            return ActionResponse(
                status=ActionStatus.FAILURE,
                message=error_msg,
                agent_insight_context=context_manager.get_agent_context(),
            )

        context_manager.add_event(
            "Work Item Retrieved",
            "Successfully retrieved work item in Validation Completed state",
        )

        context_manager.store_context()
        response = ActionResponse(
            status=ActionStatus.SUCCESS,
            message="Work item retrieved and validated successfully",
            agent_insight_context=context_manager.get_agent_context(),
            additional_data={"work_item": work_item},
        )
        logger.debug(f"Returning response: {response}")
        return response

    except Exception as e:
        error_msg = f"Error retrieving work item: {str(e)}"
        logger.error(error_msg, exc_info=True)
        context_manager.add_event("Error", error_msg)
        response = ActionResponse(
            status=ActionStatus.FAILURE,
            message=error_msg,
            additional_data={"error": str(e), "traceback": traceback.format_exc()},
        )
        logger.debug(f"Returning response: {response}")
        return response


@action
def store_and_analyze_payment(
    remittance_id: str, threshold: float = 0.01
) -> ReconciliationResponse:
    """
    Combined action to store payment data and perform reconciliation analysis atomically.

    Args:
        remittance_id (str): ID of the remittance
        threshold (float): Acceptable difference threshold for reconciliation matching
    """
    logger.debug(
        f"Starting combined payment storage and analysis for remittance ID: {remittance_id}"
    )
    context_manager = None
    try:
        # Initialize clients and get work item
        di_client = create_di_client()
        work_item = di_client.get_document_work_item(remittance_id)
        content = di_client.get_document_content(remittance_id, ContentState.COMPUTED)

        # Initialize context manager
        context_manager = ReconciliationAgentContextManager(
            remittance_id,
            work_item.source_document.document_name,
            content.computed_content["fields"]["Customer ID"],
            load_existing=False,
        )

        # Initialize ledger service
        db_path = get_full_path(
            str(InvoiceLoader.get_db_dir() / DatabaseConstants.RECONCILIATION_LEDGER_DB)
        )
        ledger_db_config = {"db_path": db_path}
        ledger_service = InvoiceReconciliationLedgerService(
            ledger_db_config, context_manager
        )

        # Part 1: Store payment data
        storage_result = _store_payment_data(
            content.computed_content, context_manager, ledger_service
        )
        if not storage_result:
            error_msg = "Failed to store payment data"
            context_manager.add_event("Error", error_msg)
            context_manager.store_context()
            return ReconciliationResponse(
                status=ActionStatus.FAILURE,
                message=error_msg,
                agent_insight_context=context_manager.get_agent_context(),
                reconciliation_result=None,
            )

        # Part 2: Perform reconciliation analysis
        analysis_result = ledger_service.analyze_payment_reconciliation(
            content.computed_content["fields"]["Payment Reference Number"],
            Decimal(str(threshold)),
        )

        # Store final context and create response with proper model instance
        context_manager.store_context()

        return ReconciliationResponse(
            status=ActionStatus.SUCCESS,
            message="Payment storage and reconciliation analysis completed successfully",
            agent_insight_context=context_manager.get_agent_context(),
            reconciliation_result=analysis_result.model_dump(),
        )
    except ValueError as ve:
        error_msg = f"Validation error in payment processing: {str(ve)}"
        logger.error(error_msg)
        if context_manager:
            context_manager.add_event("Validation Error", error_msg)
            context_manager.store_context()
        return ReconciliationResponse(
            status=ActionStatus.FAILURE,
            message=error_msg,
            agent_insight_context=context_manager.get_agent_context()
            if context_manager
            else None,
            reconciliation_result=None,
        )
    except Exception as e:
        error_msg = f"Payment processing failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        if context_manager:
            context_manager.add_event("Error", error_msg)
            context_manager.store_context()
        return ReconciliationResponse(
            status=ActionStatus.FAILURE,
            message=error_msg,
            agent_insight_context=context_manager.get_agent_context()
            if context_manager
            else None,
            reconciliation_result=None,
        )
    finally:
        try:
            
            # Clean up ledger service connections
            if ledger_service and hasattr(ledger_service, 'connection_manager'):
                logger.debug("Cleaning up ledger service connections")
                ledger_service.connection_manager.cleanup()
                
            # Clean up context manager connections
            if context_manager and hasattr(context_manager, 'connection_manager'):
                logger.debug("Cleaning up context manager connections")
                context_manager.connection_manager.cleanup()
                
        except Exception as cleanup_error:
            logger.error(f"Error during connection cleanup: {str(cleanup_error)}", exc_info=True)


@action
def update_work_item_with_reconciliation_success(
    remittance_id: str,
    reconciliation_success_summary: str,
    reconciliation_success_detailed_report: str,
) -> ActionResponse:
    """Updates work item status for successful reconciliation.

    Note: The `remittance_id` field is mandatory for identifying the document being reconciled.

    Call this after:
    1. Reconciliation analysis shows MATCHED
    2. Report is generated
    3. Threshold check is complete

    Args:
        remittance_id: Document ID (required)
        reconciliation_success_summary: Brief status summary (required)
        reconciliation_success_detailed_report: Full report using Successful Reconciliation Report Template (required)

    Returns:
        ActionResponse: Status update result
    """
    return _update_work_item_reconciliation_status(
        remittance_id,
        "SUCCESS",
        "RECONCILED",
        reconciliation_success_summary,
        reconciliation_success_detailed_report,
        True,
    )



@action
def update_work_item_with_reconciliation_discrepancy(
    remittance_id: str, discrepancy_summary: str, discrepancy_detailed_report: str
) -> ActionResponse:
    """Updates work item status when reconciliation finds discrepancies.
    
    Note: The `remittance_id` field is mandatory for identifying the document.

    Call this after:
    1. Analysis shows DISCREPANCY_FOUND
    2. Discrepancy analysis is complete
    3. Report is generated

    Before:
    - Displaying chat report

    Args:
        remittance_id: Document ID (required)
        discrepancy_summary: Brief summary of discrepancies (required)
        discrepancy_detailed_report: Full report using discrepancy template (required)

    Returns:
        ActionResponse: Status update result
    """
    return _update_work_item_reconciliation_status(
        remittance_id,
        "FAILURE",
        "DISCREPANCY_FOUND",
        discrepancy_summary,
        discrepancy_detailed_report,
        False,
    )


@action
def update_work_item_with_reconciliation_exception(
    remittance_id: str, error_summary: str, error_detailed_report: str
) -> ActionResponse:
    """Updates work item status when reconciliation encounters an exception.

    Note: The `remittance_id` field is mandatory for identifying the document being reconciled.

    Call this after:
    1. Exception is caught
    2. Error context captured
    3. Exception report generated

    Before:
    - Displaying error report

    Args:
        remittance_id: Document ID (required)
        error_summary: Brief error description (required)
        error_detailed_report: Full report using exception template (required)

    Returns:
        ActionResponse: Status update result
    """
    return _update_work_item_reconciliation_status(
        remittance_id,
        "ERROR",
        "RECONCILIATION_ERROR",
        error_summary,
        error_detailed_report,
        False,
    )


def _update_work_item_reconciliation_status(
    remittance_id: str,
    technical_status: str,
    business_status: str,
    status_summary: str,
    detailed_report: Optional[str],
    is_reconciled: bool,
) -> ActionResponse:
    """Internal helper for updating work item reconciliation status.

    Process:
    1. Connect to DI client
    2. Update work item status
    3. Log status change
    4. Return result

    Args:
        remittance_id: Document ID
        technical_status: SUCCESS/FAILURE/ERROR
        business_status: RECONCILED/DISCREPANCY_FOUND/RECONCILIATION_ERROR
        status_summary: Brief outcome summary
        detailed_report: Full formatted report
        is_reconciled: Whether reconciliation succeeded

    Returns:
        ActionResponse with status update result and report data
    """
    logger.debug(
        f"Updating reconciliation status for remittance ID: {remittance_id}\n"
        f"Technical Status: {technical_status}\n"
        f"Business Status: {business_status}\n"
        f"Summary: {status_summary}"
    )
    context_manager = None
    try:
        di_client = create_di_client()
        # Get work item to access document name
        work_item = di_client.get_document_work_item(remittance_id)

        # Initialize context manager for status updates
        context_manager = ReconciliationAgentContextManager(
            remittance_id,
            work_item.source_document.document_name,
            work_item.non_tbl_data.get("Customer ID"),
            load_existing=True,
        )

        context_manager.add_event(
            "Status Update",
            f"Updating work item status to {business_status}",
            {
                "technical_status": technical_status,
                "business_status": business_status,
                "summary": status_summary,
            },
        )

        result = di_client.work_items_complete_stage(
            remittance_id, technical_status, status_summary, detailed_report
        )

        if result is None:
            logger.warn(
                "Result was none returned by DI Client for work_items_complete_stage"
            )
            context_manager.add_event(
                "Warning", "No result returned from status update"
            )

        logger.debug(f"Successfully updated work item status to: {business_status}")
        context_manager.add_event(
            "Status Update Complete", f"Status updated to {business_status}"
        )
        context_manager.store_context()

        return ActionResponse(
            status=ActionStatus.SUCCESS,
            message=f"Work item status updated to {business_status}",
            agent_insight_context=context_manager.get_agent_context(),
            additional_data={
                "technical_status": technical_status,
                "business_status": business_status,
                "reconciliation_report": detailed_report,
                "is_reconciled": is_reconciled,
            },
        )
    except Exception as e:
        error_msg = f"Error updating reconciliation status: {str(e)}"
        logger.error(error_msg, exc_info=True)

        if context_manager:  # More consistent with other functions
            context_manager.add_event("Error", error_msg)
            context_manager.store_context()

        return ActionResponse(
            status=ActionStatus.FAILURE,
            message=error_msg,
            agent_insight_context=context_manager.get_agent_context()
            if context_manager
            else None,
            additional_data={"error": str(e), "traceback": traceback.format_exc()},
        )


def _store_payment_data(
    content: dict,
    context_manager: ReconciliationAgentContextManager,
    ledger_service: InvoiceReconciliationLedgerService,
) -> dict:
    """Helper function to store payment data in the ledger."""
    logger.debug("Starting payment data storage")

    try:
        fields = content["fields"]
        invoices = content["invoice_details"]

        logger.debug(f"Processing fields: {serialize_any_object_safely(fields)}")
        logger.debug(f"Found {len(invoices)} invoices to process")

        if not invoices:
            raise ValueError("No invoice details found in remittance")

        invoice_count = str(fields.get("Total Invoices", "0")).strip()
        if not invoice_count.isdigit():
            logger.warning(f"Invalid invoice count format: {invoice_count}")
            invoice_count = "0"

        if int(invoice_count) != len(invoices):
            raise ValueError(
                f"Invoice count mismatch: header shows {invoice_count}, "
                f"but found {len(invoices)} invoice details"
            )

        # Parse payment data with validation
        try:
            payment_data = {
                "customer_id": str(fields["Customer ID"]),
                "customer_name": str(fields["Customer Name"]),
                "payment_date": str(fields["Payment Date"]),
                "payment_method": str(fields["Payment Method"]),
                "payment_reference": str(fields["Payment Reference Number"]),
                "total_payment": parse_numeric_field(fields["Total Payment Paid"]),
                "bank_account": str(fields["Bank Account Number"]),
                "remittance_notes": str(fields.get("Remittance Notes", "")),
                "total_invoice_amount": parse_numeric_field(
                    fields["Total Invoice Amount"]
                ),
                "total_discounts": parse_numeric_field(
                    fields.get("Total Discounts Applied", 0)
                ),
                "total_charges": parse_numeric_field(
                    fields.get("Total Additional Charges", 0)
                ),
                "invoice_count": len(invoices),
            }
        except KeyError as ke:
            raise ValueError(f"Missing required field in payment data: {ke}")
        except ValueError as ve:
            raise ValueError(f"Error parsing payment amounts: {ve}")

        logger.debug(
            f"Parsed payment data: {serialize_any_object_safely(payment_data)}"
        )

        # Process invoices with validation
        processed_invoices = []
        for idx, invoice in enumerate(invoices, 1):
            try:
                processed_invoice = {
                    **invoice,
                    "Invoice Amount": parse_numeric_field(invoice["Invoice Amount"]),
                    "Amount Paid": parse_numeric_field(invoice["Amount Paid"]),
                    "Discounts Applied": parse_numeric_field(
                        invoice.get("Discounts Applied", 0)
                    ),
                    "Additional Charges": parse_numeric_field(
                        invoice.get("Additional Charges", 0)
                    ),
                }
                processed_invoices.append(processed_invoice)
            except (KeyError, ValueError) as e:
                raise ValueError(f"Error processing invoice {idx}: {e}")

        logger.debug(f"Processed {len(processed_invoices)} invoices")

        result = ledger_service.store_payment_with_allocations(
            payment_data, processed_invoices
        )
        logger.debug(
            f"Successfully stored payment data: {serialize_any_object_safely(result)}"
        )

        return result

    except Exception as e:
        logger.error(f"Error in _store_payment_data: {str(e)}", exc_info=True)
        raise
