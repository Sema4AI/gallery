from decimal import Decimal

from multiprocessing import context
import traceback
from typing import Optional

from sema4ai.actions import action
from sema4ai.di_client import DocumentIntelligenceClient
from sema4ai.di_client.document_intelligence_client.models.content_state import ContentState
from sema4ai.di_client.document_intelligence_client.models.document_work_item import DocumentWorkItem
from sema4ai.di_client.document_intelligence_client.models.processing_status import ProcessingStatus

from models.reconciliation_models import ReconciliationResponse, ReconciliationResult, RemittanceFields
from reconciliation_ledger.db.invoice_loader import InvoiceLoader
from reconciliation_ledger.services.invoice_reconciliation_service import InvoiceReconciliationLedgerService
from context.reconciliation_agent_context_manager import ReconciliationAgentContextManager

from reconciliation_ledger.reconciliation_constants import DatabaseConstants
from models.reconciliation_models import ActionResponse, ActionStatus, ReconciliationPhase
from utils.logging.reconcile_logging_module import configure_logging
from utils.commons.path_utils import get_full_path
from utils.commons.formatting import parse_numeric_field
from utils.logging.ultimate_serializer import serialize_any_object_safely

logger = configure_logging(logger_name=__name__, log_config_filename="logging-reconcile.conf")

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
        customer_id = work_item.non_tbl_data.get('Customer ID')
        
        context_manager = ReconciliationAgentContextManager(
            remittance_id,
            work_item.source_document.document_name,
            customer_id
        )
        
        context_manager.add_event("Retrieval Started", f"Retrieving work item for remittance ID: {remittance_id}")
        
        if work_item.processing_status != ProcessingStatus.VALIDATION_COMPLETED:
            error_msg = f"Invalid work item status: {work_item.processing_status}. Expected: Validation Completed"
            logger.error(error_msg)
            context_manager.add_event("Error", error_msg)
            return ActionResponse(
                status=ActionStatus.FAILURE,
                message=error_msg,
                agent_insight_context=context_manager.get_agent_context()
            )
            
        context_manager.add_event(
            "Work Item Retrieved",
            f"Successfully retrieved work item in Validation Completed state"
        )
        
        context_manager.store_context()
        response = ActionResponse(
            status=ActionStatus.SUCCESS,
            message="Work item retrieved and validated successfully",
            agent_insight_context=context_manager.get_agent_context(),
            additional_data={"work_item": work_item}
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
            additional_data={"error": str(e), "traceback": traceback.format_exc()}
        )
        logger.info(f"Returning response: {response}")
        return response

@action
def store_and_analyze_payment(remittance_id: str, threshold: float = 0.01) -> ReconciliationResponse:
    """
    Combined action to store payment data and perform reconciliation analysis atomically.
    
    Args:
        remittance_id (str): ID of the remittance
        threshold (float): Acceptable difference threshold for reconciliation matching
    
    Returns:
        ReconciliationResponse containing:
        - status: Action execution status ("SUCCESS" or "FAILURE")
        - message: Description of action result
        - agent_insight_context: Processing context information
        - reconciliation_result: Complete reconciliation analysis including:
            - status: Overall reconciliation status ("MATCHED" or "DISCREPANCY_FOUND")
            - payment_reference: Payment reference number
            - payment_amount: Total remittance amount
            - ar_balance: Total amount in AR system
            - total_difference: Total discrepancy amount
            - processing_metrics: Summary of processing statistics
                - total_invoices: Number of invoices processed
                - facility_types: List of all facility types processed
                - facility_type_count: Number of unique facility types
                - service_types: List of all service types processed
                - service_type_count: Number of unique services
                - all_matched: Whether all amounts matched within threshold
            - discrepancy_summary: Summary of discrepancies found (if any)
                - total_difference: Total amount discrepancy
                - affected_facility_count: Number of facilities with discrepancies
                - affected_invoice_count: Number of invoices with discrepancies
                - total_remittance_amount: Total amount from remittance
                - total_ar_amount: Total amount in AR system
                - facility_differences: List of facility-level discrepancies
                - affected_service_types: List of services with discrepancies
            - invoice_discrepancies: List of invoice-level discrepancies (if any)
            - remittance_fields: Original remittance information
            - threshold: Reconciliation threshold used
    
    Example Success Response:
        {
            "status": "SUCCESS",
            "message": "Payment storage and reconciliation analysis completed successfully",
            "reconciliation_result": {
                "status": "MATCHED",
                "payment_reference": "WIRE2024100502",
                "payment_amount": "2636905.41",
                "ar_balance": "2636905.41",
                "total_difference": "0.00",
                "processing_metrics": {
                    "total_invoices": 42,
                    "facility_types": ["Greenhouse Complexes", "Vertical Farming Units", ...],
                    "facility_type_count": 5,
                    "service_types": ["Electricity", "Water", "Solar Panel Generation", ...],
                    "service_type_count": 8,
                    "all_matched": true
                },
                "discrepancy_summary": null,
                "invoice_discrepancies": null,
                "remittance_fields": { ... }
            }
        }
    
    Example Discrepancy Response:
        {
            "status": "SUCCESS",
            "message": "Payment storage and reconciliation analysis completed successfully",
            "reconciliation_result": {
                "status": "DISCREPANCY_FOUND",
                "payment_reference": "WIRE2024100502",
                "payment_amount": "2636905.41",
                "ar_balance": "2645189.47",
                "total_difference": "-8284.06",
                "processing_metrics": {
                    "total_invoices": 42,
                    "facility_types": ["Greenhouse Complexes", "Vertical Farming Units", ...],
                    "facility_type_count": 5,
                    "service_types": ["Electricity", "Water", "Solar Panel Generation", ...],
                    "service_type_count": 8,
                    "all_matched": false
                },
                "discrepancy_summary": {
                    "total_difference": "-8284.06",
                    "affected_facility_count": 1,
                    "affected_invoice_count": 3,
                    "facility_differences": [ ... ],
                    "affected_service_types": ["Electricity", "Water"]
                },
                "invoice_discrepancies": [ ... ],
                "remittance_fields": { ... }
            }
        }
    """
    logger.info(f"Starting combined payment storage and analysis for remittance ID: {remittance_id}")
    try:
        # Initialize clients and get work item
        di_client = create_di_client()
        work_item = di_client.get_document_work_item(remittance_id)
        content = di_client.get_document_content(remittance_id, ContentState.COMPUTED)
        
        # Initialize context manager
        context_manager = ReconciliationAgentContextManager(
            remittance_id,
            work_item.source_document.document_name,
            content.computed_content['fields']['Customer ID']
        )
        
        context_manager.add_event(
            "Process Started", 
            "Beginning combined payment storage and reconciliation analysis"
        )
        
        # Part 1: Store Payment Data
        storage_result = None
        with context_manager.phase_context(ReconciliationPhase.PAYMENT_DATA_LOADING):
            storage_result = _store_payment_data(
                content.computed_content,
                context_manager
            )
            
            if not storage_result:
                raise ValueError("Failed to store payment data")
                
            context_manager.add_event(
                "Payment Stored",
                f"Payment {storage_result['payment_id']} stored with "
                f"{len(storage_result['allocations'])} allocations"
            )
        
        # Part 2: Perform Reconciliation Analysis
        with context_manager.phase_context(ReconciliationPhase.PAYMENT_MATCHING):
            # Parse remittance fields
            fields_data = content.computed_content['fields']
            remittance_fields = RemittanceFields(
                customer_name=fields_data['Customer Name'],
                customer_id=fields_data['Customer ID'],
                payment_date=fields_data['Payment Date'],
                payment_method=fields_data['Payment Method'],
                payment_reference=fields_data['Payment Reference Number'],
                total_payment=Decimal(str(fields_data['Total Payment Paid']).replace('$', '').replace(',', '')),
                total_invoice_amount=Decimal(str(fields_data['Total Invoice Amount']).replace('$', '').replace(',', '')),
                total_discounts=Decimal(str(fields_data.get('Total Discounts Applied', 0))),
                total_charges=Decimal(str(fields_data.get('Total Additional Charges', 0))),
                bank_account=fields_data.get('Bank Account Number', '*****0000'),
                remittance_notes=fields_data.get('Remittance Notes')
            )
            
            # Initialize ledger service
            db_path = get_full_path(str(InvoiceLoader.get_db_dir() / DatabaseConstants.RECONCILIATION_LEDGER_DB))
            ledger_db_config = {"db_path": db_path}
            ledger_service = InvoiceReconciliationLedgerService(ledger_db_config, context_manager)
            
            # Perform reconciliation analysis
            analysis_result = ledger_service.analyze_payment_reconciliation(
                remittance_fields.payment_reference,
                Decimal(str(threshold))
            )
            
            context_manager.add_event(
                "Analysis Completed",
                "Reconciliation analysis completed successfully"
            )
        
            if analysis_result.status == "DISCREPANCY_FOUND":
                context_manager.add_event(
                    "Discrepancy Found",
                    f"Discrepancy found in payment reconciliation: {analysis_result.total_difference}"
                )   
        
        # Store final context and create response with proper model instance
        context_manager.store_context()
        
        return ReconciliationResponse(
            status=ActionStatus.SUCCESS,
            message="Payment storage and reconciliation analysis completed successfully",
            agent_insight_context=context_manager.get_agent_context(),
            reconciliation_result=analysis_result.model_dump()  # Convert to dict for validation
        )
        
    except ValueError as ve:
        error_msg = f"Validation error in payment processing: {str(ve)}"
        logger.error(error_msg)
        if 'context_manager' in locals():
            context_manager.add_event("Error", error_msg)
        return ReconciliationResponse(
            status=ActionStatus.FAILURE,
            message=error_msg,
            reconciliation_result=None
        )
        
    except Exception as e:
        error_msg = f"Payment processing failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        if 'context_manager' in locals():
            context_manager.add_event("Error", error_msg)
        return ReconciliationResponse(
            status=ActionStatus.FAILURE,
            message=error_msg,
            reconciliation_result=None
        )

@action
def update_work_item_with_reconciliation_success(
    remittance_id: str,
    reconciliation_success_summary: str, 
    reconciliation_success_detailed_report: str
) -> ActionResponse:
    """Updates work item status for successful reconciliation.
    
    Call this after:
    1. Reconciliation analysis shows MATCHED
    2. Report is generated
    3. Threshold check is complete
    
    Before:
    - Displaying chat report
    - Further processing

    Args:
        remittance_id: Document ID
        reconciliation_success_summary: Brief status summary
        reconciliation_success_detailed_report: Full report using runbook template

    Returns:
        ActionResponse: Status update result
    """
    return _update_work_item_reconciliation_status(
        remittance_id,
        "SUCCESS",
        "RECONCILED",
        reconciliation_success_summary,
        reconciliation_success_detailed_report,
        True
    )
@action
def update_work_item_with_reconciliation_discrepancy(
    remittance_id: str,
    discrepancy_summary: str, 
    discrepancy_detailed_report: str
) -> ActionResponse:
    """Updates work item status when reconciliation finds discrepancies.
    
    Call this after:
    1. Analysis shows DISCREPANCY_FOUND
    2. Discrepancy analysis is complete
    3. Report is generated
    
    Before:
    - Displaying chat report
    - Halting processing
    
    Args:
        remittance_id: Document ID
        discrepancy_summary: Brief summary of discrepancies
        discrepancy_detailed_report: Full report using discrepancy template
    
    Returns:
        ActionResponse: Status update result
    """
    return _update_work_item_reconciliation_status(
        remittance_id,
        "FAILURE",
        "DISCREPANCY_FOUND",
        discrepancy_summary,
        discrepancy_detailed_report,
        False
    )
    
@action
def update_work_item_with_reconciliation_exception(
    remittance_id: str,
    error_summary: str, 
    error_detailed_report: str
) -> ActionResponse:
    """Updates work item status when reconciliation encounters an exception.
        
    Call this after:
    1. Exception is caught
    2. Error context captured
    3. Exception report generated
    
    Before:
    - Displaying error report
    - Final process termination
    
    Args:
        remittance_id: Document ID
        error_summary: Brief error description
        error_detailed_report: Full report using exception template
        
    Returns:
        ActionResponse: Status update result
    """
    return _update_work_item_reconciliation_status(
            remittance_id,
        "ERROR",
        "RECONCILIATION_ERROR",
        error_summary,
        error_detailed_report,
        False
        )
        
def _update_work_item_reconciliation_status(
    remittance_id: str,
    technical_status: str,
    business_status: str,
    status_summary: str,
    detailed_report: Optional[str],
    is_reconciled: bool
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
    logger.info(
        f"Updating reconciliation status for remittance ID: {remittance_id}\n"
        f"Technical Status: {technical_status}\n"
        f"Business Status: {business_status}\n"
        f"Summary: {status_summary}"
    )
        
    try:
        di_client = create_di_client()
        
        result = di_client.work_items_complete_stage(
            remittance_id,
            technical_status,
            status_summary,
            detailed_report
        )
        
        if result is None:
            logger.warn("Result was none returned by DI Client for work_items_complete_stage")
            # raise Exception("Failed to update work item status")
   
        logger.info(f"Successfully updated work item status to: {business_status}")
        
        return ActionResponse(
            status=ActionStatus.SUCCESS,
            message=f"Work item status updated to {business_status}",
            additional_data={
                "technical_status": technical_status,
                "business_status": business_status,
                "reconciliation_report": detailed_report,
                "is_reconciled": is_reconciled
            }
        )
        
    except Exception as e:
        error_msg = f"Error updating reconciliation status: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return ActionResponse(
            status=ActionStatus.FAILURE,
            message=error_msg,
            additional_data={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )


    
def _store_payment_data(content: dict, context_manager: ReconciliationAgentContextManager) -> dict:
    """Helper function to store payment data in the ledger."""
    logger.info("Starting payment data storage")
    
    try:
    fields = content['fields']
    invoices = content['invoice_details']
    
        logger.debug(f"Processing fields: {serialize_any_object_safely(fields)}")
        logger.debug(f"Found {len(invoices)} invoices to process")
        
    if not invoices:
        raise ValueError("No invoice details found in remittance")
        
        invoice_count = str(fields.get('Total Invoices', '0')).strip()
        if not invoice_count.isdigit():
            logger.warning(f"Invalid invoice count format: {invoice_count}")
            invoice_count = '0'
            
        if int(invoice_count) != len(invoices):
        raise ValueError(
                f"Invoice count mismatch: header shows {invoice_count}, "
            f"but found {len(invoices)} invoice details"
        )
    
        # Parse payment data with validation
        try:
    payment_data = {
                "customer_id": str(fields['Customer ID']),
                "customer_name": str(fields['Customer Name']),
                "payment_date": str(fields['Payment Date']),
                "payment_method": str(fields['Payment Method']),
                "payment_reference": str(fields['Payment Reference Number']),
        "total_payment": parse_numeric_field(fields['Total Payment Paid']),
                "bank_account": str(fields['Bank Account Number']),
                "remittance_notes": str(fields.get('Remittance Notes', '')),
        "total_invoice_amount": parse_numeric_field(fields['Total Invoice Amount']),
        "total_discounts": parse_numeric_field(fields.get('Total Discounts Applied', 0)),
        "total_charges": parse_numeric_field(fields.get('Total Additional Charges', 0)),
        "invoice_count": len(invoices)
    }
        except KeyError as ke:
            raise ValueError(f"Missing required field in payment data: {ke}")
        except ValueError as ve:
            raise ValueError(f"Error parsing payment amounts: {ve}")
    
        logger.debug(f"Parsed payment data: {serialize_any_object_safely(payment_data)}")
        
        # Process invoices with validation
    processed_invoices = []
        for idx, invoice in enumerate(invoices, 1):
            try:
        processed_invoice = {
            **invoice,
            'Invoice Amount': parse_numeric_field(invoice['Invoice Amount']),
            'Amount Paid': parse_numeric_field(invoice['Amount Paid']),
            'Discounts Applied': parse_numeric_field(invoice.get('Discounts Applied', 0)),
            'Additional Charges': parse_numeric_field(invoice.get('Additional Charges', 0))
        }
        processed_invoices.append(processed_invoice)
            except (KeyError, ValueError) as e:
                raise ValueError(f"Error processing invoice {idx}: {e}")
                
        logger.debug(f"Processed {len(processed_invoices)} invoices")
    
    # Initialize ledger service and store data
    db_path = get_full_path(str(InvoiceLoader.get_db_dir() / DatabaseConstants.RECONCILIATION_LEDGER_DB))
    ledger_db_config = {"db_path": db_path}
    ledger_service = InvoiceReconciliationLedgerService(ledger_db_config, context_manager)
    
        result = ledger_service.store_payment_with_allocations(payment_data, processed_invoices)
        logger.info(f"Successfully stored payment data: {serialize_any_object_safely(result)}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in _store_payment_data: {str(e)}", exc_info=True)
        raise