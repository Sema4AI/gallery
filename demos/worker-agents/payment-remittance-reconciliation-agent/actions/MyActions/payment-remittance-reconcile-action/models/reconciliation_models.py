from typing import Optional, Dict, List, Any, Type, TypeVar
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from pandas import Series
from enum import Enum
import numpy as np
import json

class ReconciliationPhase(str, Enum):
    PAYMENT_DATA_LOADING = "Payment Data Loading"
    PAYMENT_MATCHING = "Payment Matching"
    FACILITY_TYPE_RECONCILIATION = "Facility Type Reconciliation"
    INVOICE_LEVEL_RECONCILIATION = "Invoice Level Reconciliation"
    PAYMENT_RECONCILIATION = "PAYMENT_RECONCILIATION"
    
    
class ValidationSeverity(str, Enum):
    ERROR = "Error"
    WARNING = "Warning"
    INFO = "Info"

class ActionStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL_SUCCESS = "partial_success"
    
class ProcessingEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="The time when the event occurred")
    event_type: Optional[str] = Field(None, description="The type of event (e.g., 'Table Extraction', 'Validation Check')")
    description: Optional[str] = Field(None, description="A detailed description of the event")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details specific to the event")

    model_config = ConfigDict(json_encoders={Series: lambda v: v.to_list()})
    
class DataMetrics(BaseModel):
    metrics: Dict[str, Any] = Field(default_factory=dict, description="A dictionary to store various metrics")

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "metrics":
            super().__setattr__(name, value)
        else:
            if isinstance(value, Series):
                self.metrics[name] = value.to_list()
            else:
                self.metrics[name] = value

    def __getattr__(self, name: str) -> Any:
        return self.metrics.get(name)

    model_config = ConfigDict(json_encoders={Series: lambda v: v.to_list()})
    

class ValidationResult(BaseModel):
    rule_id: Optional[str] = Field(None, description="The unique identifier of the validation rule")
    passed: Optional[bool] = Field(None, description="Indicates whether the validation rule passed")
    message: Optional[str] = Field(None, description="The message describing the validation result")
    severity: Optional[ValidationSeverity] = Field(None, description="The severity level of the validation result")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details about the validation result")

class ValidationResults(BaseModel):
    rules_passed: int = Field(0, description="The number of validation rules that passed")
    rules_failed: int = Field(0, description="The number of validation rules that failed")
    results: List[ValidationResult] = Field(default_factory=list, description="The list of individual validation results")

    model_config = ConfigDict(json_encoders={Series: lambda v: v.to_list()})

    def add_result(self, rule_id: str, passed: bool, message: str, severity: ValidationSeverity, details: Optional[Dict[str, Any]] = None):
        self.results.append(ValidationResult(
            rule_id=rule_id,
            passed=passed,
            message=message,
            severity=severity,
            details=details
        ))
        if passed:
            self.rules_passed += 1
        else:
            self.rules_failed += 1




    def add_validation_results(self, *others: 'ValidationResults'):
        for other in others:
            self.rules_passed += other.rules_passed
            self.rules_failed += other.rules_failed
            self.results.extend(other.results)
        return self

    def get_overall_status(self) -> bool:
        # Return True if there are no error results
        return not any(result.severity == ValidationSeverity.ERROR for result in self.results)
    
    # define a function has_failures that returns True if there are any error results
    def has_failures(self) -> bool:
        return any(result.severity == ValidationSeverity.ERROR for result in self.results)
    
    def get_total_results(self) -> int:
        return self.rules_passed + self.rules_failed
    
    def get_rule_result(self, rule_id: str) -> Optional[ValidationResult]:
        for result in self.results:
            if result.rule_id == rule_id:
                return result
        return None
    

    @property
    def error_results(self) -> List[ValidationResult]:
        return [result for result in self.results if result.severity == ValidationSeverity.ERROR]

    @property
    def warning_results(self) -> List[ValidationResult]:
        return [result for result in self.results if result.severity == ValidationSeverity.WARNING]

    @property
    def info_results(self) -> List[ValidationResult]:
        return [result for result in self.results if result.severity == ValidationSeverity.INFO]
    
    
class ReconciliationContext(BaseModel):
    phase: ReconciliationPhase
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    events: List[ProcessingEvent] = Field(default_factory=list)
    metrics: DataMetrics = Field(default_factory=DataMetrics)
    validation_results: Optional[ValidationResults] = None
    additional_context: Dict[str, Any] = Field(default_factory=dict)

class ReconciliationAgentInsightContext(BaseModel):
    document_id: str
    document_name: str
    customer_id: str
    payment_data_loading: Optional[ReconciliationContext] = None
    payment_matching: Optional[ReconciliationContext] = None
    facility_type_reconciliation: Optional[ReconciliationContext] = None
    invoice_level_reconciliation: Optional[ReconciliationContext] = None
    overall_status: Optional[str] = None
    overall_processing_time: float = 0.0

    def get_phase_context(self, phase: ReconciliationPhase) -> Optional[ReconciliationContext]:
        return getattr(self, phase.value.lower().replace(" ", "_"), None)

    def set_phase_context(self, phase: ReconciliationPhase, context: ReconciliationContext):
        setattr(self, phase.value.lower().replace(" ", "_"), context)

    def get_all_validation_results(self) -> Dict[ReconciliationPhase, ValidationResults]:
        return {
            phase: context.validation_results
            for phase in ReconciliationPhase
            if (context := self.get_phase_context(phase)) and context.validation_results
        }

    def get_overall_validation_status(self) -> bool:
        return all(
            results.get_overall_status()
            for results in self.get_all_validation_results().values()
        )
        
        
T = TypeVar('T', bound='ActionResponse')

class ActionResponse(BaseModel):
    status: ActionStatus = Field(..., description="The overall status of the action")
    message: str = Field(..., description="A brief summary or instruction for the agent")
    agent_insight_context: Optional[ReconciliationAgentInsightContext] = None
    additional_data: Optional[Dict[str, Any]] = Field(None, description="Any additional data that might be relevant")

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            np.integer: lambda v: int(v),
            np.floating: lambda v: float(v),
            np.ndarray: lambda v: v.tolist(),
            Enum: lambda v: v.value,
        },
        arbitrary_types_allowed=True
    )

    def model_dump(self, **kwargs):
        return self._depth_limited_dump(self, max_depth=10)

    def model_dump_json(self, **kwargs):
        return json.dumps(self.model_dump(), **kwargs)

    @classmethod
    def _depth_limited_dump(cls, obj, current_depth=0, max_depth=10):
        if current_depth > max_depth:
            return str(obj)

        if isinstance(obj, BaseModel):
            return {
                k: cls._depth_limited_dump(v, current_depth + 1, max_depth)
                for k, v in obj.__dict__.items()
                if not k.startswith('_') and v is not None
            }
        elif isinstance(obj, dict):
            return {
                k: cls._depth_limited_dump(v, current_depth + 1, max_depth)
                for k, v in obj.items() if v is not None
            }
        elif isinstance(obj, list):
            return [cls._depth_limited_dump(item, current_depth + 1, max_depth) for item in obj]
        elif isinstance(obj, (datetime, np.datetime64)):
            return obj.isoformat()
        elif isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return str(obj)

    @classmethod
    def model_validate(cls: Type[T], obj: Any) -> T:
        if isinstance(obj, dict):
            obj = cls._prepare_for_validation(obj)
        return super().model_validate(obj)

    @staticmethod
    def _prepare_for_validation(data: Dict[str, Any]) -> Dict[str, Any]:
        if 'agent_insight_context' in data and isinstance(data['agent_insight_context'], dict):
            data['agent_insight_context'] = ReconciliationAgentInsightContext.model_validate(data['agent_insight_context'])
        return data

    def __str__(self):
        return f"ActionResponse(status={self.status.value}, message='{self.message}')"

    def __repr__(self):
        return self.__str__()


class RemittanceFields(BaseModel):
    """Fields specific to a remittance document"""
    customer_name: str = Field(
        default="Sample Customer",
        description="Name of the customer making the payment"
    )
    customer_id: str = Field(
        default="CUS-00000",
        description="Unique identifier for the customer"
    )
    payment_date: str = Field(
        default=datetime.now().strftime("%Y-%m-%d"),
        description="Date when the payment was made"
    )
    payment_method: str = Field(
        default="Wire Transfer",
        description="Method of payment (e.g., Wire Transfer, ACH)"
    )
    payment_reference: str = Field(
        default="PMT-00000",
        description="Unique reference number for the payment"
    )
    total_payment: Decimal = Field(
        default=Decimal('0.00'),
        description="Total amount of the payment"
    )
    total_invoice_amount: Decimal = Field(
        default=Decimal('0.00'),
        description="Total amount of all invoices being paid"
    )
    total_discounts: Decimal = Field(
        default=Decimal('0.00'),
        description="Total discounts applied across all invoices"
    )
    total_charges: Decimal = Field(
        default=Decimal('0.00'),
        description="Total additional charges across all invoices"
    )
    bank_account: str = Field(
        default="*****0000",
        description="Masked bank account number"
    )
    remittance_notes: Optional[str] = Field(
        default=None,
        description="Additional notes provided with the remittance"
    )

class PaymentMatchResult(BaseModel):
    """Result of payment matching analysis"""
    payment_id: str = Field(
        default="PMT-00000",
        description="Unique identifier for the payment record"
    )
    matching_status: str = Field(
        default="Pending",
        description="Match or Mismatch"
    )
    payment_amount: Decimal = Field(
        default=Decimal('0.00'),
        description="Total amount of the payment"
    )
    outstanding_balance: Decimal = Field(
        default=Decimal('0.00'),
        description="Total outstanding balance in AR system"
    )
    base_amount: Decimal = Field(
        default=Decimal('0.00'),
        description="Base amount before adjustments"
    )
    total_charges: Decimal = Field(
        default=Decimal('0.00'),
        description="Sum of all additional charges"
    )
    total_discounts: Decimal = Field(
        default=Decimal('0.00'),
        description="Sum of all applied discounts"
    )
    threshold: Decimal = Field(
        default=Decimal('0.01'),
        description="Acceptable difference threshold for matching"
    )
    discrepancy: Decimal = Field(
        default=Decimal('0.00'),
        description="Difference between payment and outstanding balance"
    )

class FacilityComponents(BaseModel):
    """Detailed components of facility amounts"""
    base: Decimal = Field(
        default=Decimal('0.00'),
        description="Base amount component"
    )
    charges: Decimal = Field(
        default=Decimal('0.00'),
        description="Additional charges component"
    )
    discounts: Decimal = Field(
        default=Decimal('0.00'),
        description="Applied discounts component"
    )

class FacilityComponentDetail(BaseModel):
    """Components for both allocated and outstanding amounts"""
    allocated: FacilityComponents = Field(
        default_factory=FacilityComponents,
        description="Components of allocated amount"
    )
    outstanding: FacilityComponents = Field(
        default_factory=FacilityComponents,
        description="Components of outstanding amount"
    )

class FacilityAmounts(BaseModel):
    """Amounts for a facility type"""
    allocated: Decimal = Field(
        default=Decimal('0.00'),
        description="Amount allocated to the facility"
    )
    outstanding: Decimal = Field(
        default=Decimal('0.00'),
        description="Outstanding amount for the facility"
    )

class FacilityDiscrepancy(BaseModel):
    """Details of facility type discrepancy"""
    ledger_amount: Decimal = Field(
        default=Decimal('0.00'),
        description="Amount recorded in the ledger"
    )
    remittance_amount: Decimal = Field(
        default=Decimal('0.00'),
        description="Amount stated in the remittance"
    )
    difference: Decimal = Field(
        default=Decimal('0.00'),
        description="Difference between ledger and remittance amounts"
    )
    components: FacilityComponentDetail = Field(
        default_factory=FacilityComponentDetail,
        description="Detailed breakdown of amount components"
    )

class FacilityAnalysisResult(BaseModel):
    """Result of facility type analysis"""
    facility_totals: Dict[str, FacilityAmounts] = Field(
        default_factory=dict,
        description="Totals by facility type"
    )
    discrepancies: Dict[str, FacilityDiscrepancy] = Field(
        default_factory=dict,
        description="Discrepancies found by facility type"
    )
    threshold: Decimal = Field(
        default=Decimal('0.01'),
        description="Threshold used for discrepancy detection"
    )

class InvoiceDetail(BaseModel):
    """Details for a single invoice"""
    allocated_net: Decimal = Field(
        default=Decimal('0.00'),
        description="Net amount allocated to the invoice"
    )
    invoice_net: Decimal = Field(
        default=Decimal('0.00'),
        description="Net amount on the invoice"
    )
    facility_id: str = Field(
        default="FAC-00000",
        description="ID of the facility associated with the invoice"
    )
    facility_type: str = Field(
        default="Unknown",
        description="Type of facility (e.g., Greenhouse, Hydroponics)"
    )
    service_type: str = Field(
        default="Unknown",
        description="Type of service provided (e.g., Electricity, Water)"
    )

class InvoiceDiscrepancy(BaseModel):
    """Details of invoice level discrepancy"""
    invoice_number: str = Field(
        default="INV-00000",
        description="Invoice reference number"
    )
    difference: Decimal = Field(
        default=Decimal('0.00'),
        description="Total discrepancy amount for the invoice"
    )
    facility_id: str = Field(
        default="FAC-00000",
        description="Facility ID associated with the invoice"
    )
    service_type: str = Field(
        default="Unknown",
        description="Type of service on the invoice"
    )
    discount_discrepancy: Optional[Decimal] = Field(
        default=None,
        description="Difference in discount amounts, if applicable"
    )
    charges_discrepancy: Optional[Decimal] = Field(
        default=None,
        description="Difference in additional charges, if applicable"
    )

class InvoiceAnalysisResult(BaseModel):
    """Result of invoice level analysis"""
    invoice_details: Dict[str, InvoiceDetail] = Field(
        default_factory=dict,
        description="Details for all analyzed invoices"
    )
    discrepancies: List[InvoiceDiscrepancy] = Field(
        default_factory=list,
        description="List of found invoice discrepancies"
    )
    threshold: Decimal = Field(
        default=Decimal('0.01'),
        description="Threshold used for discrepancy detection"
    )

class ReconciliationSummaryMetrics(BaseModel):
    """Summary metrics for the reconciliation"""
    total_discrepancy: Decimal = Field(
        default=Decimal('0.00'),
        description="Total amount of all discrepancies found"
    )
    facility_types_with_issues: int = Field(
        default=0,
        description="Number of facility types with discrepancies"
    )
    invoices_with_issues: int = Field(
        default=0,
        description="Number of invoices with discrepancies"
    )

class ReconciliationResult(BaseModel):
    """Complete reconciliation analysis result including remittance details"""
    status: str = Field(
        default="PENDING",
        description="MATCHED or DISCREPANCY_FOUND"
    )
    customer_results: PaymentMatchResult = Field(
        default_factory=PaymentMatchResult,
        description="Results of customer-level payment matching"
    )
    facility_results: Optional[FacilityAnalysisResult] = Field(
        default=None,
        description="Results of facility-level analysis, if performed"
    )
    invoice_results: Optional[InvoiceAnalysisResult] = Field(
        default=None,
        description="Results of invoice-level analysis, if performed"
    )
    summary_metrics: Optional[ReconciliationSummaryMetrics] = Field(
        default=None,
        description="Summary metrics of the reconciliation process"
    )
    remittance_fields: RemittanceFields = Field(
        default_factory=RemittanceFields,
        description="Original remittance document fields"
    )

    class Config:
        """Pydantic model configuration"""
        json_encoders = {
            Decimal: str  # Ensure Decimals serialize properly
        }
