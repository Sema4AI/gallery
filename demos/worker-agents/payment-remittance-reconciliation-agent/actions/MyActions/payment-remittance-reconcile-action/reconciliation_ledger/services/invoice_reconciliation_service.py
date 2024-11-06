from typing import Dict, Any, List
import logging
from decimal import Decimal

from reconciliation_ledger.reconciliation_constants import DocumentStatus
from context.reconciliation_agent_context_manager import ReconciliationAgentContextManager
from reconciliation_ledger.db.invoice_loader import InvoiceLoader
from utils.commons.decimal_utils import DecimalHandler
from utils.commons.formatting import format_currency
from models.reconciliation_models import ReconciliationResult, ReconciliationSummaryMetrics, PaymentMatchResult, InvoiceAnalysisResult,InvoiceDetail, InvoiceDiscrepancy, FacilityAnalysisResult, FacilityDiscrepancy, FacilityAmounts, FacilityComponentDetail, FacilityComponents
from models.reconciliation_models import ReconciliationPhase 

class InvoiceReconciliationLedgerService:
    """
    Service for handling invoice reconciliation with the DuckDB ledger.
    Follows similar pattern to InvoiceLoader for consistency and simplicity.
    """
    
    def __init__(self, config: Dict, context_manager):
        self.logger = logging.getLogger(__name__)
        self.context_manager = context_manager
        self.loader = InvoiceLoader(config.get('db_path'))
        
        
    def store_payment_with_allocations(
        self,
        payment_data: Dict[str, Any],
        invoices: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Store payment and its allocations.
        
        Args:
            payment_data: Dictionary containing payment information
            invoices: List of invoice details
        
        Returns:
            Dictionary containing payment results
        """
        customer_id = payment_data['customer_id']
        self.logger.info(f"Storing payment for customer {customer_id}")
        
        try:
            with self.loader.get_connection() as conn:
                # Clean and parse monetary values
                total_payment = self._parse_monetary_value(payment_data['total_payment'])
                total_invoice = self._parse_monetary_value(payment_data['total_invoice_amount'])
                total_discounts = self._parse_monetary_value(payment_data.get('total_discounts', 0))
                total_charges = self._parse_monetary_value(payment_data.get('total_charges', 0))
                
                # Update payment data with cleaned values
                payment_data_clean = {
                    **payment_data,
                    'total_payment': float(total_payment),
                    'total_invoice_amount': float(total_invoice),
                    'total_discounts': float(total_discounts),
                    'total_charges': float(total_charges)
                }
                
                # Create payment record
                payment_id = self._create_payment_record(conn, payment_data_clean)
                
                # Create allocation records
                allocation_results = []
                total_allocated = Decimal('0')
                facility_totals = {}
                
                # Track running totals for validation
                total_invoice_amount = Decimal('0')
                total_discounts_sum = Decimal('0')
                total_charges_sum = Decimal('0')
                
                for invoice in invoices:
                    # Parse invoice amounts
                    amount_paid = self._parse_monetary_value(invoice['Amount Paid'])
                    invoice_amount = self._parse_monetary_value(invoice['Invoice Amount'])
                    discounts = self._parse_monetary_value(invoice.get('Discounts Applied', 0))
                    charges = self._parse_monetary_value(invoice.get('Additional Charges', 0))
                    
                    # Update running totals
                    total_allocated += amount_paid
                    total_invoice_amount += invoice_amount
                    total_discounts_sum += discounts
                    total_charges_sum += charges
                    
                    # Create allocation record
                    invoice_clean = {
                        **invoice,
                        'Amount Paid': float(amount_paid),
                        'Invoice Amount': float(invoice_amount),
                        'Discounts Applied': float(discounts),
                        'Additional Charges': float(charges)
                    }
                    
                    allocation = self._create_allocation_record(
                        conn, customer_id, payment_id, invoice_clean
                    )
                    allocation_results.append(allocation)
                    
                    # Update facility totals
                    facility_type = invoice['Facility Type']
                    facility_totals[facility_type] = \
                        facility_totals.get(facility_type, Decimal('0')) + amount_paid
                
                # Validate totals
                total_allocated = total_allocated.quantize(Decimal('0.01'))
                payment_amount = total_payment.quantize(Decimal('0.01'))
                
                if abs(payment_amount - total_allocated) > Decimal('0.01'):
                    self.context_manager.add_event(
                        "Payment Allocation Mismatch",
                        f"Total allocated ({format_currency(float(total_allocated))}) "
                        f"doesn't match payment ({format_currency(float(payment_amount))})"
                    )
                
                # Convert facility totals to float for return
                facility_totals_float = {
                    k: float(v.quantize(Decimal('0.01')))
                    for k, v in facility_totals.items()
                }
                
                # Log summary
                self.logger.info(
                    f"Stored payment {payment_id} with {len(allocation_results)} allocations:\n"
                    f"Total Payment: {format_currency(float(payment_amount))}\n"
                    f"Total Allocated: {format_currency(float(total_allocated))}\n"
                    f"Total Invoices: {len(invoices)}"
                )
                
                return {
                    "payment_id": payment_id,
                    "allocations": allocation_results,
                    "total_allocated": float(total_allocated),
                    "facility_totals": facility_totals_float,
                    "invoice_totals": {
                        "amount": float(total_invoice_amount),
                        "discounts": float(total_discounts_sum),
                        "charges": float(total_charges_sum)
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error storing payment: {str(e)}", exc_info=True)
            raise
        
        
    def analyze_payment_reconciliation(
        self,
        payment_reference: str,
        threshold: Decimal
    ) -> ReconciliationResult:
        """
        Perform complete payment reconciliation analysis.
        Manages its own phase contexts.
        
        Args:
            payment_reference: Payment reference to analyze
            threshold: Acceptable difference threshold
            
        Returns:
            ReconciliationResult with complete analysis
        """
        try:
            threshold = DecimalHandler.from_str(str(threshold))
            
            # Phase 1: Payment Matching
            with self.context_manager.phase_context(ReconciliationPhase.PAYMENT_MATCHING):
                match_results = self._match_payment_receivables(payment_reference, threshold)
                
                if match_results.matching_status == "Match":
                    return ReconciliationResult(
                        status="MATCHED",
                        customer_results=match_results
                    )
                    
            # Phase 2: Facility Analysis
            with self.context_manager.phase_context(ReconciliationPhase.FACILITY_TYPE_RECONCILIATION):
                facility_results = self._analyze_facility_type_discrepancies(
                    payment_reference, threshold)

            with self.context_manager.phase_context(ReconciliationPhase.INVOICE_LEVEL_RECONCILIATION):
                invoice_results = self._analyze_invoice_discrepancies(
                    payment_reference, threshold)

            # Create summary metrics
            return ReconciliationResult(
                status="DISCREPANCY_FOUND",
                customer_results=match_results,
                facility_results=facility_results,
                invoice_results=invoice_results
            )
        except Exception as e:
            self.logger.error(f"Reconciliation analysis failed: {str(e)}", exc_info=True)
            raise

    def _match_payment_receivables(
        self, 
        payment_reference: str,
        threshold: Decimal
    ) -> PaymentMatchResult:
        """Match payments using DecimalHandler."""
        with self.loader.get_connection() as conn:
            payment = conn.execute("""
                SELECT 
                    payment_id,
                    customer_id,
                    CAST(total_payment_paid AS DECIMAL(18, 2)) as total_payment_paid,
                    CAST(total_invoice_amount AS DECIMAL(18, 2)) as total_invoice_amount
                FROM payment 
                WHERE payment_reference = ?
            """, [payment_reference]).fetchone()
            
            if not payment:
                raise ValueError(f"Payment {payment_reference} not found")
            
            payment_amount = DecimalHandler.from_str(str(payment[2]))
            invoice_amount = DecimalHandler.from_str(str(payment[3]))
            
            # Get amounts from database with precision
            outstanding = conn.execute("""
                SELECT 
                    CAST(SUM(CAST(invoice_amount AS DECIMAL(18, 2))) AS DECIMAL(18, 2)) as base,
                    CAST(SUM(CAST(COALESCE(additional_charges, 0) AS DECIMAL(18, 2))) AS DECIMAL(18, 2)) as charges,
                    CAST(SUM(CAST(COALESCE(discounts_applied, 0) AS DECIMAL(18, 2))) AS DECIMAL(18, 2)) as discounts
                FROM invoice
                WHERE customer_id = ? AND status = 'PENDING'
            """, [payment[1]]).fetchone()
            
            base_amount = DecimalHandler.from_str(str(outstanding[0] or 0))
            charges = DecimalHandler.from_str(str(outstanding[1] or 0))
            discounts = DecimalHandler.from_str(str(outstanding[2] or 0))
            
            # Calculate net with DecimalHandler
            outstanding_balance = DecimalHandler.round_decimal(
                base_amount + charges - discounts
            )
            
            # Calculate discrepancy
            discrepancy = DecimalHandler.round_decimal(
                payment_amount - outstanding_balance
            )
            
            # Determine match status using threshold
            status = "Match" if abs(discrepancy) <= threshold else "Mismatch"
            
            return PaymentMatchResult(
                payment_id=payment[0],
                matching_status=status,
                payment_amount=payment_amount,
                outstanding_balance=outstanding_balance,
                base_amount=base_amount,
                total_charges=charges,
                total_discounts=discounts,
                threshold=threshold,
                discrepancy=discrepancy
            )
        
    def _analyze_facility_type_discrepancies(
        self,
        payment_reference: str,
        threshold: Decimal
    ) -> FacilityAnalysisResult:
        """Analyze facility discrepancies with DecimalHandler."""
        with self.loader.get_connection() as conn:
            # Get allocated amounts by facility
            allocations = conn.execute("""
                SELECT 
                    i.facility_type,
                    CAST(SUM(CAST(pa.amount_applied AS DECIMAL(18, 2))) AS DECIMAL(18, 2)) as allocated
                FROM payment_allocation pa
                JOIN invoice i ON pa.invoice_id = i.invoice_id 
                JOIN payment p ON pa.payment_id = p.payment_id
                WHERE p.payment_reference = ?
                GROUP BY i.facility_type
            """, [payment_reference]).fetchall()
            
            # Get invoice amounts by facility
            invoices = conn.execute("""
                SELECT 
                    i.facility_type,
                    CAST(SUM(CAST(i.invoice_amount AS DECIMAL(18, 2))) AS DECIMAL(18, 2)) as base,
                    CAST(SUM(CAST(COALESCE(i.additional_charges, 0) AS DECIMAL(18, 2))) AS DECIMAL(18, 2)) as charges,
                    CAST(SUM(CAST(COALESCE(i.discounts_applied, 0) AS DECIMAL(18, 2))) AS DECIMAL(18, 2)) as discounts
                FROM invoice i
                WHERE i.status = 'PENDING'
                GROUP BY i.facility_type
            """).fetchall()
            
            facility_totals = {}
            discrepancies = {}
            
            for row in invoices:
                facility_type = row[0]
                
                # Convert all amounts using DecimalHandler
                base = DecimalHandler.from_str(str(row[1]))
                charges = DecimalHandler.from_str(str(row[2]))
                discounts = DecimalHandler.from_str(str(row[3]))
                
                # Find allocation for this facility
                allocated = next(
                    (DecimalHandler.from_str(str(alloc[1])) 
                     for alloc in allocations if alloc[0] == facility_type),
                    DecimalHandler.from_str('0')
                )
                
                # Calculate net amounts
                ledger_net = DecimalHandler.round_decimal(base + charges - discounts)
                
                # Calculate difference
                difference = DecimalHandler.round_decimal(allocated - ledger_net)
                
                facility_totals[facility_type] = FacilityAmounts(
                    allocated=allocated,
                    outstanding=ledger_net
                )
                
                if abs(difference) > threshold:
                    discrepancies[facility_type] = FacilityDiscrepancy(
                        ledger_amount=ledger_net,
                        remittance_amount=allocated,
                        difference=difference,
                        components=FacilityComponentDetail(
                            allocated=FacilityComponents(
                                base=allocated,
                                charges=DecimalHandler.from_str('0'),
                                discounts=DecimalHandler.from_str('0')
                            ),
                            outstanding=FacilityComponents(
                                base=base,
                                charges=charges,
                                discounts=discounts
                            )
                        )
                    )
            
            return FacilityAnalysisResult(
                facility_totals=facility_totals,
                discrepancies=discrepancies,
                threshold=threshold
            )
            
            
    def _analyze_invoice_discrepancies(
        self,
        payment_reference: str,
        threshold: Decimal
    ) -> InvoiceAnalysisResult:
        """Internal method for invoice analysis using Pydantic model."""
        self.logger.info(f"Starting invoice analysis for payment reference: {payment_reference}")
        
        try:
            with self.loader.get_connection() as conn:
                # First lookup the payment
                payment = conn.execute("""
                    SELECT payment_id, customer_id
                    FROM payment 
                    WHERE payment_reference = CAST(? AS VARCHAR)
                """, [payment_reference]).fetchone()
                
                if not payment:
                    raise ValueError(f"Payment with reference {payment_reference} not found")
                
                payment_id = payment[0]
                
                # Get complete invoice and allocation details
                results = conn.execute("""
                    WITH payment_allocations AS (
                        SELECT 
                            i.invoice_number,
                            i.invoice_id,
                            CAST(pa.amount_applied AS DECIMAL(18, 2)) as allocated_amount,
                            CAST(COALESCE(pa.additional_charges, 0) AS DECIMAL(18, 2)) as allocated_charges,
                            CAST(COALESCE(pa.discounts_applied, 0) AS DECIMAL(18, 2)) as allocated_discounts
                        FROM payment_allocation pa
                        JOIN invoice i ON pa.invoice_id = i.invoice_id
                        WHERE pa.payment_id = ?
                    )
                    SELECT 
                        i.invoice_number,
                        f.facility_id,
                        i.facility_type,
                        i.service_type,
                        pa.allocated_amount,
                        pa.allocated_charges,
                        pa.allocated_discounts,
                        CAST(i.invoice_amount AS DECIMAL(18, 2)) as invoice_amount,
                        CAST(COALESCE(i.additional_charges, 0) AS DECIMAL(18, 2)) as charges,
                        CAST(COALESCE(i.discounts_applied, 0) AS DECIMAL(18, 2)) as discounts
                    FROM invoice i
                    JOIN facility f ON i.internal_facility_id = f.internal_facility_id
                    JOIN payment_allocations pa ON i.invoice_id = pa.invoice_id
                """, [payment_id]).fetchall()
                
                if not results:
                    raise ValueError(f"No invoices found for payment {payment_id}")
                
                # Process results into Pydantic models
                invoice_details = {}
                discrepancies = []
                
                for row in results:
                    invoice_number = row[0]
                    allocated_amount = Decimal(str(row[4]))
                    invoice_amount = Decimal(str(row[7]))
                    charges = Decimal(str(row[8]))
                    discounts = Decimal(str(row[9]))
                    
                    invoice_net = (invoice_amount + charges - discounts).quantize(Decimal('0.01'))
                    
                    invoice_details[invoice_number] = InvoiceDetail(
                        allocated_net=allocated_amount,
                        invoice_net=invoice_net,
                        facility_id=row[1],
                        facility_type=row[2],
                        service_type=row[3]
                    )
                    
                    # Check for discrepancy
                    difference = (allocated_amount - invoice_net).quantize(Decimal('0.01'))
                    if abs(difference) > threshold:
                        discrepancies.append(InvoiceDiscrepancy(
                            invoice_number=invoice_number,
                            difference=difference,
                            facility_id=row[1],
                            service_type=row[3],
                            discount_discrepancy=Decimal(str(row[6])) - discounts if row[6] != discounts else None,
                            charges_discrepancy=Decimal(str(row[5])) - charges if row[5] != charges else None
                        ))
                
                self.context_manager.add_event(
                    "Invoice Analysis",
                    f"Analyzed {len(invoice_details)} invoices, found {len(discrepancies)} with discrepancies"
                )
                
                return InvoiceAnalysisResult(
                    invoice_details=invoice_details,
                    discrepancies=discrepancies,
                    threshold=threshold
                )
                
        except Exception as e:
            self.logger.error(f"Error analyzing invoices: {str(e)}", exc_info=True)
            raise


    def _create_payment_record(
        self,
        conn,
        payment_data: Dict[str, Any]
    ) -> str:
        """Create payment record in database with UPSERT support."""
        query = """
        INSERT INTO payment (
            payment_id, customer_id, payment_date, bank_account_number,
            total_payment_paid, payment_reference, payment_method,
            total_invoice_amount, total_additional_charges,
            total_discounts_applied, total_invoices, remittance_notes
        ) VALUES (?, ?, ?, ?, 
            CAST(? AS DECIMAL(18, 2)), ?, ?, 
            CAST(? AS DECIMAL(18, 2)), 
            CAST(? AS DECIMAL(18, 2)), 
            CAST(? AS DECIMAL(18, 2)), 
            ?, ?)
        ON CONFLICT (payment_id) DO UPDATE SET
            total_payment_paid = CAST(EXCLUDED.total_payment_paid AS DECIMAL(18, 2)),
            total_invoice_amount = CAST(EXCLUDED.total_invoice_amount AS DECIMAL(18, 2)),
            total_additional_charges = CAST(EXCLUDED.total_additional_charges AS DECIMAL(18, 2)),
            total_discounts_applied = CAST(EXCLUDED.total_discounts_applied AS DECIMAL(18, 2)),
            total_invoices = EXCLUDED.total_invoices,
            remittance_notes = EXCLUDED.remittance_notes
        """
        
        payment_id = f"PMT-{payment_data['payment_date']}-{payment_data['payment_reference']}"
        
        # Convert all monetary values to Decimal for precise storage
        total_payment = Decimal(str(payment_data['total_payment'])).quantize(Decimal('0.01'))
        total_invoice = Decimal(str(payment_data['total_invoice_amount'])).quantize(Decimal('0.01'))
        total_charges = Decimal(str(payment_data.get('total_charges', 0))).quantize(Decimal('0.01'))
        total_discounts = Decimal(str(payment_data.get('total_discounts', 0))).quantize(Decimal('0.01'))
        
        conn.execute(query, [
            payment_id,
            payment_data['customer_id'],
            payment_data['payment_date'],
            payment_data['bank_account'],
            float(total_payment),
            payment_data['payment_reference'],
            payment_data['payment_method'],
            float(total_invoice),
            float(total_charges),
            float(total_discounts),
            payment_data['invoice_count'],
            payment_data.get('remittance_notes', '')
        ])
        
        return payment_id

    def _create_allocation_record(
        self,
        conn,
        customer_id: str,
        payment_id: str,
        invoice: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create allocation record in database with UPSERT support."""
        # First get the invoice_id for this customer's invoice
        query = """
        SELECT invoice_id 
        FROM invoice 
        WHERE customer_id = ? AND invoice_number = ?
        """
        
        result = conn.execute(query, [customer_id, invoice['Invoice Number']]).fetchone()
        if not result:
            raise ValueError(f"Invoice {invoice['Invoice Number']} not found for customer {customer_id}")
            
        invoice_id = result[0]
        
        # Now create allocation record using invoice_id
        query = """
        INSERT INTO payment_allocation (
            allocation_id, payment_id, invoice_id,
            amount_applied, invoice_amount, discounts_applied,
            additional_charges
        ) VALUES (?, ?, ?, 
            CAST(? AS DECIMAL(18, 2)), 
            CAST(? AS DECIMAL(18, 2)), 
            CAST(? AS DECIMAL(18, 2)), 
            CAST(? AS DECIMAL(18, 2)))
        ON CONFLICT (allocation_id) DO UPDATE SET
            amount_applied = CAST(EXCLUDED.amount_applied AS DECIMAL(18, 2)),
            invoice_amount = CAST(EXCLUDED.invoice_amount AS DECIMAL(18, 2)),
            discounts_applied = CAST(EXCLUDED.discounts_applied AS DECIMAL(18, 2)),
            additional_charges = CAST(EXCLUDED.additional_charges AS DECIMAL(18, 2))
        """
        
        allocation_id = f"ALLOC-{payment_id}-{invoice_id}"
        
        # Parse amounts ensuring they match DDL decimal precision
        amount_applied = Decimal(str(invoice['Amount Paid'])).quantize(Decimal('0.01'))
        invoice_amount = Decimal(str(invoice['Invoice Amount'])).quantize(Decimal('0.01'))
        discounts = Decimal(str(invoice.get('Discounts Applied', 0))).quantize(Decimal('0.01'))
        charges = Decimal(str(invoice.get('Additional Charges', 0))).quantize(Decimal('0.01'))
        
        conn.execute(query, [
            allocation_id,
            payment_id,
            invoice_id,
            float(amount_applied),
            float(invoice_amount),
            float(discounts),
            float(charges)
        ])
        
        return {
            "allocation_id": allocation_id,
            "invoice_id": invoice_id,
            "invoice_number": invoice['Invoice Number'],
            "amount": float(amount_applied),
            "invoice_amount": float(invoice_amount),
            "discounts": float(discounts),
            "charges": float(charges)
        }

    # def _match_payment_receivables(
    #     self, 
    #     payment_reference: str,
    #     threshold: Decimal
    # ) -> PaymentMatchResult:
    #     """Internal method for payment matching using Pydantic model."""
    #     self.logger.info(f"Looking up payment for reference: {payment_reference}")
        
    #     try:
    #         with self.loader.get_connection() as conn:
    #             # First lookup the payment with exact decimal precision
    #             payment = conn.execute("""
    #                 SELECT 
    #                     payment_id,
    #                     customer_id,
    #                     CAST(total_payment_paid AS DECIMAL(18, 2)) as total_payment_paid,
    #                     CAST(total_invoice_amount AS DECIMAL(18, 2)) as total_invoice_amount,
    #                     CAST(COALESCE(total_additional_charges, 0) AS DECIMAL(18, 2)) as total_additional_charges,
    #                     CAST(COALESCE(total_discounts_applied, 0) AS DECIMAL(18, 2)) as total_discounts_applied
    #                 FROM payment 
    #                 WHERE payment_reference = CAST(? AS VARCHAR)
    #             """, [payment_reference]).fetchone()
                
    #             if not payment:
    #                 raise ValueError(f"Payment with reference {payment_reference} not found in accounts receivable")
                
    #             payment_id = payment[0]
    #             customer_id = payment[1]
    #             payment_amount = Decimal(str(payment[2]))
                
    #             # Get total outstanding balance with exact decimal precision
    #             query = """
    #             SELECT 
    #                 CAST(SUM(CAST(invoice_amount AS DECIMAL(18, 2))) AS DECIMAL(18, 2)) as base_amount,
    #                 CAST(SUM(CAST(COALESCE(additional_charges, 0) AS DECIMAL(18, 2))) AS DECIMAL(18, 2)) as total_charges,
    #                 CAST(SUM(CAST(COALESCE(discounts_applied, 0) AS DECIMAL(18, 2))) AS DECIMAL(18, 2)) as total_discounts
    #             FROM invoice
    #             WHERE customer_id = CAST(? AS VARCHAR) 
    #             AND status = CAST(? AS VARCHAR)
    #             """
                
    #             result = conn.execute(query, [
    #                 customer_id,
    #                 DocumentStatus.PENDING
    #             ]).fetchone()
                
    #             if not result or result[0] is None:
    #                 raise ValueError(f"No outstanding invoices found for customer {customer_id}")
                
    #             # Convert all values to Decimal for precise calculations
    #             base_amount = Decimal(str(result[0] or 0))
    #             total_charges = Decimal(str(result[1] or 0))
    #             total_discounts = Decimal(str(result[2] or 0))
                
    #             # Calculate total outstanding with exact precision
    #             outstanding_balance = (base_amount + total_charges - total_discounts).quantize(Decimal('0.01'))
                
    #             # Calculate discrepancy with exact precision
    #             discrepancy = (payment_amount - outstanding_balance).quantize(Decimal('0.01'))
    #             status = "Match" if abs(discrepancy) <= threshold else "Mismatch"
                
    #             self.context_manager.add_event(
    #                 "Payment Matching",
    #                 f"Status: {status}, Discrepancy: {format_currency(float(abs(discrepancy)))}"
    #             )
                
    #             return PaymentMatchResult(
    #                 payment_id=payment_id,
    #                 matching_status=status,
    #                 payment_amount=payment_amount,
    #                 outstanding_balance=outstanding_balance,
    #                 base_amount=base_amount,
    #                 total_charges=total_charges,
    #                 total_discounts=total_discounts,
    #                 threshold=threshold,
    #                 discrepancy=discrepancy
    #             )
    #     except Exception as e:
    #         self.logger.error(f"Error matching payment: {str(e)}", exc_info=True)
    #         raise

    # def _analyze_facility_type_discrepancies(
    #     self,
    #     payment_reference: str,
    #     threshold: Decimal
    # ) -> FacilityAnalysisResult:
    #     """Internal method for facility analysis using Pydantic model."""
    #     self.logger.info(f"Starting facility type analysis for payment reference: {payment_reference}")
        
    #     try:
    #         with self.loader.get_connection() as conn:
    #             # First lookup the payment
    #             payment = conn.execute("""
    #                 SELECT 
    #                     payment_id,
    #                     customer_id
    #                 FROM payment 
    #                 WHERE payment_reference = ?
    #             """, [payment_reference]).fetchone()
                
    #             if not payment:
    #                 raise ValueError(f"Payment with reference {payment_reference} not found")
                
    #             payment_id = payment[0]
                
    #             # Get invoice amounts for these allocations
    #             invoice_totals = conn.execute("""
    #                 SELECT 
    #                     i.facility_type,
    #                     ROUND(CAST(SUM(CAST(i.invoice_amount AS DECIMAL(18, 2))) AS DECIMAL(18, 2)), 2) as invoice_total,
    #                     ROUND(CAST(SUM(CAST(COALESCE(i.additional_charges, 0) AS DECIMAL(18, 2))) AS DECIMAL(18, 2)), 2) as total_charges,
    #                     ROUND(CAST(SUM(CAST(COALESCE(i.discounts_applied, 0) AS DECIMAL(18, 2))) AS DECIMAL(18, 2)), 2) as total_discounts
    #                 FROM invoice i
    #                 JOIN payment_allocation pa ON i.invoice_id = pa.invoice_id
    #                 WHERE pa.payment_id = ?
    #                 GROUP BY i.facility_type
    #             """, [payment_id]).fetchall()
                
    #             # Get allocation amounts
    #             allocation_totals = conn.execute("""
    #                 SELECT 
    #                     i.facility_type,
    #                     ROUND(CAST(SUM(CAST(pa.amount_applied AS DECIMAL(18, 2))) AS DECIMAL(18, 2)), 2) as total_allocated
    #                 FROM payment_allocation pa
    #                 JOIN invoice i ON pa.invoice_id = i.invoice_id
    #                 WHERE pa.payment_id = ?
    #                 GROUP BY i.facility_type
    #             """, [payment_id]).fetchall()
                
    #             # Process results into Pydantic models
    #             facility_totals = {}
    #             discrepancies = {}
                
    #             allocation_lookup = {row[0]: Decimal(str(row[1])) for row in allocation_totals}
                
    #             for row in invoice_totals:
    #                 facility_type = row[0]
    #                 invoice_total = Decimal(str(row[1]))
    #                 charges = Decimal(str(row[2]))
    #                 discounts = Decimal(str(row[3]))
    #                 allocated = allocation_lookup.get(facility_type, Decimal('0'))
                    
    #                 facility_totals[facility_type] = FacilityAmounts(
    #                     allocated=allocated,
    #                     outstanding=invoice_total + charges - discounts
    #                 )
                    
    #                 # Check for discrepancy
    #                 net_invoice = invoice_total + charges - discounts
    #                 difference = (allocated - net_invoice).quantize(Decimal('0.01'))
                    
    #                 if abs(difference) > threshold:
    #                     discrepancies[facility_type] = FacilityDiscrepancy(
    #                         ledger_amount=net_invoice,
    #                         remittance_amount=allocated,
    #                         difference=difference,
    #                         components=FacilityComponentDetail(
    #                             allocated=FacilityComponents(
    #                                 base=allocated,
    #                                 charges=Decimal('0'),
    #                                 discounts=Decimal('0')
    #                             ),
    #                             outstanding=FacilityComponents(
    #                                 base=invoice_total,
    #                                 charges=charges,
    #                                 discounts=discounts
    #                             )
    #                         )
    #                     )
                
    #             self.context_manager.add_event(
    #                 "Facility Analysis",
    #                 f"Analyzed {len(facility_totals)} facility types, found {len(discrepancies)} with discrepancies"
    #             )
                
    #             return FacilityAnalysisResult(
    #                 facility_totals=facility_totals,
    #                 discrepancies=discrepancies,
    #                 threshold=threshold
    #             )
                
    #     except Exception as e:
    #         self.logger.error(f"Error analyzing facility types: {str(e)}", exc_info=True)
    #         raise

    def _analyze_invoice_discrepancies(
        self,
        payment_reference: str,
        threshold: Decimal
    ) -> InvoiceAnalysisResult:
        """Internal method for invoice analysis using Pydantic model."""
        self.logger.info(f"Starting invoice analysis for payment reference: {payment_reference}")
        
        try:
            with self.loader.get_connection() as conn:
                # First lookup the payment
                payment = conn.execute("""
                    SELECT payment_id, customer_id
                    FROM payment 
                    WHERE payment_reference = CAST(? AS VARCHAR)
                """, [payment_reference]).fetchone()
                
                if not payment:
                    raise ValueError(f"Payment with reference {payment_reference} not found")
                
                payment_id = payment[0]
                
                # Get complete invoice and allocation details
                results = conn.execute("""
                    WITH payment_allocations AS (
                        SELECT 
                            i.invoice_number,
                            i.invoice_id,
                            CAST(pa.amount_applied AS DECIMAL(18, 2)) as allocated_amount,
                            CAST(COALESCE(pa.additional_charges, 0) AS DECIMAL(18, 2)) as allocated_charges,
                            CAST(COALESCE(pa.discounts_applied, 0) AS DECIMAL(18, 2)) as allocated_discounts
                        FROM payment_allocation pa
                        JOIN invoice i ON pa.invoice_id = i.invoice_id
                        WHERE pa.payment_id = ?
                    )
                    SELECT 
                        i.invoice_number,
                        f.facility_id,
                        i.facility_type,
                        i.service_type,
                        pa.allocated_amount,
                        pa.allocated_charges,
                        pa.allocated_discounts,
                        CAST(i.invoice_amount AS DECIMAL(18, 2)) as invoice_amount,
                        CAST(COALESCE(i.additional_charges, 0) AS DECIMAL(18, 2)) as charges,
                        CAST(COALESCE(i.discounts_applied, 0) AS DECIMAL(18, 2)) as discounts
                    FROM invoice i
                    JOIN facility f ON i.internal_facility_id = f.internal_facility_id
                    JOIN payment_allocations pa ON i.invoice_id = pa.invoice_id
                """, [payment_id]).fetchall()
                
                if not results:
                    raise ValueError(f"No invoices found for payment {payment_id}")
                
                # Process results into Pydantic models
                invoice_details = {}
                discrepancies = []
                
                for row in results:
                    invoice_number = row[0]
                    allocated_amount = Decimal(str(row[4]))
                    invoice_amount = Decimal(str(row[7]))
                    charges = Decimal(str(row[8]))
                    discounts = Decimal(str(row[9]))
                    
                    invoice_net = (invoice_amount + charges - discounts).quantize(Decimal('0.01'))
                    
                    invoice_details[invoice_number] = InvoiceDetail(
                        allocated_net=allocated_amount,
                        invoice_net=invoice_net,
                        facility_id=row[1],
                        facility_type=row[2],
                        service_type=row[3]
                    )
                    
                    # Check for discrepancy
                    difference = (allocated_amount - invoice_net).quantize(Decimal('0.01'))
                    if abs(difference) > threshold:
                        discrepancies.append(InvoiceDiscrepancy(
                            invoice_number=invoice_number,
                            difference=difference,
                            facility_id=row[1],
                            service_type=row[3],
                            discount_discrepancy=Decimal(str(row[6])) - discounts if row[6] != discounts else None,
                            charges_discrepancy=Decimal(str(row[5])) - charges if row[5] != charges else None
                        ))
                
                self.context_manager.add_event(
                    "Invoice Analysis",
                    f"Analyzed {len(invoice_details)} invoices, found {len(discrepancies)} with discrepancies"
                )
                
                return InvoiceAnalysisResult(
                    invoice_details=invoice_details,
                    discrepancies=discrepancies,
                    threshold=threshold
                )
                
        except Exception as e:
            self.logger.error(f"Error analyzing invoices: {str(e)}", exc_info=True)
            raise
    def _analyze_invoice_discrepancies(
        self,
        payment_reference: str,
        threshold: Decimal
    ) -> InvoiceAnalysisResult:
        """Internal method for invoice analysis using Pydantic model."""
        self.logger.info(f"Starting invoice analysis for payment reference: {payment_reference}")
        
        try:
            with self.loader.get_connection() as conn:
                # First lookup the payment
                payment = conn.execute("""
                    SELECT payment_id, customer_id
                    FROM payment 
                    WHERE payment_reference = CAST(? AS VARCHAR)
                """, [payment_reference]).fetchone()
                
                if not payment:
                    raise ValueError(f"Payment with reference {payment_reference} not found")
                
                payment_id = payment[0]
                
                # Get complete invoice and allocation details
                results = conn.execute("""
                    WITH payment_allocations AS (
                        SELECT 
                            i.invoice_number,
                            i.invoice_id,
                            CAST(pa.amount_applied AS DECIMAL(18, 2)) as allocated_amount,
                            CAST(COALESCE(pa.additional_charges, 0) AS DECIMAL(18, 2)) as allocated_charges,
                            CAST(COALESCE(pa.discounts_applied, 0) AS DECIMAL(18, 2)) as allocated_discounts
                        FROM payment_allocation pa
                        JOIN invoice i ON pa.invoice_id = i.invoice_id
                        WHERE pa.payment_id = ?
                    )
                    SELECT 
                        i.invoice_number,
                        f.facility_id,
                        i.facility_type,
                        i.service_type,
                        pa.allocated_amount,
                        pa.allocated_charges,
                        pa.allocated_discounts,
                        CAST(i.invoice_amount AS DECIMAL(18, 2)) as invoice_amount,
                        CAST(COALESCE(i.additional_charges, 0) AS DECIMAL(18, 2)) as charges,
                        CAST(COALESCE(i.discounts_applied, 0) AS DECIMAL(18, 2)) as discounts
                    FROM invoice i
                    JOIN facility f ON i.internal_facility_id = f.internal_facility_id
                    JOIN payment_allocations pa ON i.invoice_id = pa.invoice_id
                """, [payment_id]).fetchall()
                
                if not results:
                    raise ValueError(f"No invoices found for payment {payment_id}")
                
                # Process results into Pydantic models
                invoice_details = {}
                discrepancies = []
                
                for row in results:
                    invoice_number = row[0]
                    allocated_amount = Decimal(str(row[4]))
                    invoice_amount = Decimal(str(row[7]))
                    charges = Decimal(str(row[8]))
                    discounts = Decimal(str(row[9]))
                    
                    invoice_net = (invoice_amount + charges - discounts).quantize(Decimal('0.01'))
                    
                    invoice_details[invoice_number] = InvoiceDetail(
                        allocated_net=allocated_amount,
                        invoice_net=invoice_net,
                        facility_id=row[1],
                        facility_type=row[2],
                        service_type=row[3]
                    )
                    
                    # Check for discrepancy
                    difference = (allocated_amount - invoice_net).quantize(Decimal('0.01'))
                    if abs(difference) > threshold:
                        discrepancies.append(InvoiceDiscrepancy(
                            invoice_number=invoice_number,
                            difference=difference,
                            facility_id=row[1],
                            service_type=row[3],
                            discount_discrepancy=Decimal(str(row[6])) - discounts if row[6] != discounts else None,
                            charges_discrepancy=Decimal(str(row[5])) - charges if row[5] != charges else None
                        ))
                
                self.context_manager.add_event(
                    "Invoice Analysis",
                    f"Analyzed {len(invoice_details)} invoices, found {len(discrepancies)} with discrepancies"
                )
                
                return InvoiceAnalysisResult(
                    invoice_details=invoice_details,
                    discrepancies=discrepancies,
                    threshold=threshold
                )
                
        except Exception as e:
            self.logger.error(f"Error analyzing invoices: {str(e)}", exc_info=True)
            raise

    
        
    def _parse_monetary_value(self, value: Any) -> Decimal:
        """Helper method to parse monetary values consistently."""
        if isinstance(value, str):
            # Remove currency symbol and commas
            clean_value = value.replace('$', '').replace(',', '')
            return Decimal(clean_value).quantize(Decimal('0.01'))
        return Decimal(str(value)).quantize(Decimal('0.01'))
        