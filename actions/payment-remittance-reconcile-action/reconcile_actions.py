from decimal import Decimal

import traceback

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

from models.reconciliation_models import ReconciliationResult, RemittanceFields
from reconciliation_ledger.db.invoice_loader import InvoiceLoader
from reconciliation_ledger.services.invoice_reconciliation_service import (
    InvoiceReconciliationLedgerService,
)
from context.reconciliation_agent_context_manager import (
    ReconciliationAgentContextManager,
)

from reconciliation_ledger.reconciliation_constants import DatabaseConstants
from models.reconciliation_models import (
    ActionResponse,
    ActionStatus,
    ReconciliationPhase,
)
from utils.logging.reconcile_logging_module import configure_logging
from utils.commons.path_utils import get_full_path
from utils.commons.formatting import parse_numeric_field

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
    logger.info(f"Starting remittance work item retrieval for ID: {remittance_id}")
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
            f"Successfully retrieved work item in Validation Completed state",
        )

        context_manager.store_context()
        response = ActionResponse(
            status=ActionStatus.SUCCESS,
            message="Work item retrieved and validated successfully",
            agent_insight_context=context_manager.get_agent_context(),
            additional_data={"work_item": work_item},
        )
        logger.info(f"Returning response: {response}")
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
        logger.info(f"Returning response: {response}")
        return response


@action
def store_and_analyze_payment(
    remittance_id: str, threshold: float = 0.01
) -> ActionResponse:
    """
    Combined action to store payment data and perform reconciliation analysis atomically.

    Args:
        remittance_id (str): ID of the remittance
        threshold (float): Acceptable difference threshold


    Returns:
        ActionResponse: Response object containing status, message, and reconciliation results
    """
    logger.info(
        f"Starting combined payment storage and analysis for remittance ID: {remittance_id}"
    )
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
        )

        context_manager.add_event(
            "Process Started",
            "Beginning combined payment storage and reconciliation analysis",
        )

        # Part 1: Store Payment Data
        storage_result = None
        with context_manager.phase_context(ReconciliationPhase.PAYMENT_DATA_LOADING):
            storage_result = _store_payment_data(
                content.computed_content, context_manager
            )

            if not storage_result:
                raise ValueError("Failed to store payment data")

            context_manager.add_event(
                "Payment Stored",
                f"Payment {storage_result['payment_id']} stored with "
                f"{len(storage_result['allocations'])} allocations",
            )

        # Part 2: Perform Reconciliation Analysis
        analysis_result = None
        with context_manager.phase_context(ReconciliationPhase.PAYMENT_MATCHING):
            # Parse remittance fields
            fields_data = content.computed_content["fields"]
            remittance_fields = RemittanceFields(
                customer_name=fields_data["Customer Name"],
                customer_id=fields_data["Customer ID"],
                payment_date=fields_data["Payment Date"],
                payment_method=fields_data["Payment Method"],
                payment_reference=fields_data["Payment Reference Number"],
                total_payment=Decimal(
                    str(fields_data["Total Payment Paid"])
                    .replace("$", "")
                    .replace(",", "")
                ),
                total_invoice_amount=Decimal(
                    str(fields_data["Total Invoice Amount"])
                    .replace("$", "")
                    .replace(",", "")
                ),
                total_discounts=Decimal(
                    str(fields_data.get("Total Discounts Applied", 0))
                ),
                total_charges=Decimal(
                    str(fields_data.get("Total Additional Charges", 0))
                ),
                bank_account=fields_data.get("Bank Account Number", "*****0000"),
                remittance_notes=fields_data.get("Remittance Notes"),
            )

            # Initialize ledger service (reuse from storage phase)
            db_path = get_full_path(
                str(
                    InvoiceLoader.get_db_dir()
                    / DatabaseConstants.RECONCILIATION_LEDGER_DB
                )
            )
            ledger_db_config = {"db_path": db_path}
            ledger_service = InvoiceReconciliationLedgerService(
                ledger_db_config, context_manager
            )

            # Perform reconciliation analysis
            reconciliation_result = ledger_service.analyze_payment_reconciliation(
                remittance_fields.payment_reference, Decimal(str(threshold))
            )

            # Add remittance fields to result
            complete_result_dict = reconciliation_result.model_dump()
            complete_result_dict["remittance_fields"] = remittance_fields
            analysis_result = ReconciliationResult(**complete_result_dict)

            context_manager.add_event(
                "Analysis Completed", "Reconciliation analysis completed successfully"
            )

        # Prepare combined response
        final_result = {
            "storage_result": storage_result,
            "reconciliation_results": analysis_result,
        }

        # Store final context and return response
        context_manager.store_context()

        response = ActionResponse(
            status=ActionStatus.SUCCESS,
            message="Payment storage and reconciliation analysis completed successfully",
            agent_insight_context=context_manager.get_agent_context(),
            additional_data=final_result,
        )
        logger.info(f"Returning response: {response}")
        return response

    except ValueError as ve:
        error_msg = f"Validation error in payment processing: {str(ve)}"
        logger.error(error_msg)
        if "context_manager" in locals():
            context_manager.add_event("Error", error_msg)
        response = ActionResponse(
            status=ActionStatus.FAILURE,
            message=error_msg,
            additional_data={"error_type": "validation_error", "error": str(ve)},
        )
        return response

    except Exception as e:
        error_msg = f"Payment processing failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        if "context_manager" in locals():
            context_manager.add_event("Error", error_msg)
        response = ActionResponse(
            status=ActionStatus.FAILURE,
            message=error_msg,
            additional_data={
                "error_type": "system_error",
                "error": str(e),
                "traceback": traceback.format_exc(),
            },
        )
        return response


@action
def update_work_item_status(
    remittance_id: str, status_summary: str, detailed_report: str, is_reconciled: bool
) -> ActionResponse:
    """
    Update work item status based on reconciliation results.

    Args:
        remittance_id (str): ID of the remittance
        status_summary (str): Brief summary of reconciliation outcome
        detailed_report (str): Comprehensive reconciliation report
        is_reconciled (bool): Whether the reconciliation was successful

    Returns:
        ActionResponse: Response object containing the status, message, and additional data if any.
    """
    logger.info(f"Updating work item status for ID: {remittance_id}")

    try:
        di_client = create_di_client()
        work_item = di_client.get_document_work_item(remittance_id)

        context_manager = ReconciliationAgentContextManager(
            remittance_id,
            work_item.source_document.document_name,
            work_item.non_tbl_data.get("Customer ID"),
            load_existing=True,
        )

        context_manager.add_event(
            "Status Update Started",
            f"Updating status for remittance ID: {remittance_id}",
        )

        # Map business status to technical status
        technical_status = "SUCCESS" if is_reconciled else "FAILURE"

        # Update the work item status using the provided summary and report
        result = di_client.work_items_complete_stage(
            remittance_id,
            technical_status,
            status_summary,  # Use provided summary as status_reason
            detailed_report,  # Use full report as log_details_path
        )

        if result is None:
            error_msg = "Failed to update work item status"
            context_manager.add_event("Error", error_msg)
            raise Exception(error_msg)

        business_status = "RECONCILED" if is_reconciled else "DISCREPANCY_FOUND"
        logger.info(f"Work item status updated to: {business_status}")
        context_manager.add_event(
            "Status Updated", f"Work item status updated to: {business_status}"
        )

        # Store the Agent Context before returnin
        context_manager.store_context()

        response = ActionResponse(
            status=ActionStatus.SUCCESS,
            message=f"Work item status updated to {business_status}",
            agent_insight_context=context_manager.get_agent_context(),
            additional_data={
                "technical_status": technical_status,
                "business_status": business_status,
                "status_summary": status_summary,
                "has_detailed_report": bool(detailed_report),
            },
        )
        logger.info(f"Returning response: {response}")
        return response

    except Exception as e:
        error_msg = f"Status update failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        context_manager.add_event("Error", error_msg)
        response = ActionResponse(
            status=ActionStatus.FAILURE,
            message=error_msg,
            additional_data={"error": str(e), "traceback": traceback.format_exc()},
        )
        logger.info(f"Returning response: {response}")
        return response


def _store_payment_data(
    content: dict, context_manager: ReconciliationAgentContextManager
) -> dict:
    """Helper function to store payment data in the ledger."""
    fields = content["fields"]
    invoices = content["invoice_details"]

    if not invoices:
        raise ValueError("No invoice details found in remittance")

    if int(fields["Total Invoices"]) != len(invoices):
        raise ValueError(
            f"Invoice count mismatch: header shows {fields['Total Invoices']}, "
            f"but found {len(invoices)} invoice details"
        )

    # Parse payment data
    payment_data = {
        "customer_id": fields["Customer ID"],
        "customer_name": fields["Customer Name"],
        "payment_date": fields["Payment Date"],
        "payment_method": fields["Payment Method"],
        "payment_reference": fields["Payment Reference Number"],
        "total_payment": parse_numeric_field(fields["Total Payment Paid"]),
        "bank_account": fields["Bank Account Number"],
        "remittance_notes": fields.get("Remittance Notes", ""),
        "total_invoice_amount": parse_numeric_field(fields["Total Invoice Amount"]),
        "total_discounts": parse_numeric_field(
            fields.get("Total Discounts Applied", 0)
        ),
        "total_charges": parse_numeric_field(fields.get("Total Additional Charges", 0)),
        "invoice_count": len(invoices),
    }

    # Process invoices
    processed_invoices = []
    for invoice in invoices:
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

    # Initialize ledger service and store data
    db_path = get_full_path(
        str(InvoiceLoader.get_db_dir() / DatabaseConstants.RECONCILIATION_LEDGER_DB)
    )
    ledger_db_config = {"db_path": db_path}
    ledger_service = InvoiceReconciliationLedgerService(
        ledger_db_config, context_manager
    )

    return ledger_service.store_payment_with_allocations(
        payment_data, processed_invoices
    )
