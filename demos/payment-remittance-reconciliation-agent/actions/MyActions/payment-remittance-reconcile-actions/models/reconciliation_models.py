from typing import Optional, Dict, List, Any, Type, TypeVar, Union
from decimal import Decimal
from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict, validator

from pandas import Series
from enum import Enum
import numpy as np
import json

from utils.commons.decimal_utils import DecimalHandler

class ReconciliationPhase(str, Enum):
    PAYMENT_DATA_LOADING = "Payment Data Loading"
    PAYMENT_MATCHING = "Payment Matching"
    FACILITY_TYPE_RECONCILIATION = "Facility Type Reconciliation"
    INVOICE_LEVEL_RECONCILIATION = "Invoice Level Reconciliation"
    PAYMENT_RECONCILIATION = "Payment Reconciliation"
    
    
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
    payment_reconciliation: Optional[ReconciliationContext] = None
    
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




# ----------------------------------------------------------- Reconciliation Related Models -------------------------------------------------------#


class RemittanceFields(BaseModel):
    """Core remittance information with explicit net/gross amounts."""
    customer_name: str
    customer_id: str
    payment_date: Union[str, date, datetime]
    payment_method: str
    payment_reference: str
    
    # Net amount - what customer actually paid after discounts
    total_payment: Decimal = Field(
        ...,
        description="Net amount paid by customer (after discounts applied)"
    )
    
    # Gross amount - original invoice amounts before any discounts/charges
    total_invoice_amount: Decimal = Field(
        ...,
        description="Gross AR amount before discounts/charges (sum of original invoice amounts)"
    )
    
    # Adjustment components
    total_discounts: Decimal = Field(
        ...,
        description="Total discounts applied (reduces gross to net)"
    )
    total_charges: Decimal = Field(
        ...,
        description="Total additional charges applied (adds to gross)"
    )
    
    bank_account: str
    remittance_notes: Optional[str] = None

    @validator('payment_date')
    def validate_payment_date(cls, v):
        """Convert any date input to YYYY-MM-DD string format."""
        if isinstance(v, datetime):
            return v.date().isoformat()
        elif isinstance(v, date):
            return v.isoformat()
        elif isinstance(v, str):
            try:
                # Try to parse the string to validate it's a proper date
                parsed_date = datetime.strptime(v, "%Y-%m-%d").date()
                return parsed_date.isoformat()
            except ValueError:
                try:
                    # Try alternate format MM/DD/YYYY
                    parsed_date = datetime.strptime(v, "%m/%d/%Y").date()
                    return parsed_date.isoformat()
                except ValueError:
                    raise ValueError("Invalid date format. Use YYYY-MM-DD or MM/DD/YYYY")
        raise ValueError("Invalid date type")

    @validator('total_payment', 'total_invoice_amount', 'total_discounts', 'total_charges')
    def validate_decimal_amounts(cls, v):
        """Ensure all monetary values are properly handled as decimals."""
        if isinstance(v, (int, float)):
            v = str(v)
        return DecimalHandler.from_str(str(v))

    @validator('total_discounts')
    def validate_discounts(cls, v, values):
        """Ensure discounts don't exceed gross amount."""
        if 'total_invoice_amount' in values:
            gross = DecimalHandler.from_str(str(values['total_invoice_amount']))
            discounts = DecimalHandler.from_str(str(v))
            if discounts > gross:
                raise ValueError("Discounts cannot exceed total invoice amount")
        return v

    @property
    def net_ar_amount(self) -> Decimal:
        """Calculate net AR amount (gross - discounts + charges) using DecimalHandler."""
        # Convert each value to ensure proper decimal handling
        gross = DecimalHandler.from_str(str(self.total_invoice_amount))
        discounts = DecimalHandler.from_str(str(self.total_discounts))
        charges = DecimalHandler.from_str(str(self.total_charges))
        
        # Perform calculations with proper rounding
        net = DecimalHandler.round_decimal(gross - discounts)
        if charges > Decimal('0'):
            net = DecimalHandler.round_decimal(net + charges)
            
        return net

    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True
        json_encoders = {
            Decimal: str,
            date: lambda d: d.isoformat(),
            datetime: lambda dt: dt.date().isoformat()
        }

class FacilityAmountSummary(BaseModel):
    """Summary of amounts for a facility type."""
    facility_type: str
    remittance_amount: Decimal  # Net amount from customer payment
    ar_system_amount: Decimal   # Net AR amount (gross - discounts)
    difference: Decimal         # remittance - ar_system
    service_types: List[str]
    invoice_count: int
    has_discrepancy: bool

    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True
        json_encoders = {
            Decimal: str
        }
        
        
class InvoiceDiscrepancyDetail(BaseModel):
    """Detailed invoice discrepancy information."""
    invoice_number: str
    facility_id: str
    facility_type: str
    service_type: str
    remittance_amount: Decimal  # Net amount from remittance
    ar_amount: Decimal         # Net AR amount (after discounts)
    difference: Decimal        # remittance - ar

    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True
        json_encoders = {
            Decimal: str
        }

class DiscrepancySummary(BaseModel):
    """Complete discrepancy analysis summary."""
    total_difference: Decimal
    affected_facility_count: int
    affected_invoice_count: int
    total_remittance_amount: Decimal
    total_ar_amount: Decimal
    facility_differences: List[FacilityAmountSummary]
    affected_service_types: List[str]

    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True
        json_encoders = {
            Decimal: str
        }

class ReconciliationResult(BaseModel):
    """Complete reconciliation analysis result."""
    status: str = Field(..., description="MATCHED or DISCREPANCY_FOUND")
    payment_reference: str
    payment_amount: Decimal  # Net amount paid by customer
    ar_balance: Decimal     # Net AR balance (gross - discounts)
    total_difference: Decimal
    discrepancy_summary: Optional[DiscrepancySummary] = None
    invoice_discrepancies: Optional[List[InvoiceDiscrepancyDetail]] = None
    remittance_fields: Optional[RemittanceFields] = None
    threshold: Optional[Decimal] = Field(default=Decimal('0.01'))

    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True
        json_encoders = {
            Decimal: str
        }

class ReconciliationResponse(ActionResponse):
    """Response model for reconciliation actions."""
    reconciliation_result: Optional[Union[ReconciliationResult, Dict[str, Any]]] = Field(
        default=None,
        description="Reconciliation analysis result"
    )

    @validator('reconciliation_result')
    def validate_reconciliation_result(cls, v):
        """Validate and convert reconciliation result."""
        if isinstance(v, dict):
            return ReconciliationResult(**v)
        return v

    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True
        json_encoders = {
            Decimal: str
        }
        
        
class ProcessingMetrics(BaseModel):
    """Model for processing summary metrics."""
    total_invoices: int
    facility_types: List[str]
    facility_type_count: int
    service_types: List[str]
    service_type_count: int
    all_matched: bool

class ReconciliationResult(BaseModel):
    """Enhanced reconciliation result model with processing metrics."""
    status: str
    payment_reference: str
    payment_amount: Decimal
    ar_balance: Decimal
    total_difference: Decimal
    processing_metrics: ProcessingMetrics
    discrepancy_summary: Optional[DiscrepancySummary]
    invoice_discrepancies: Optional[List[InvoiceDiscrepancyDetail]]
    remittance_fields: RemittanceFields
    threshold: Decimal