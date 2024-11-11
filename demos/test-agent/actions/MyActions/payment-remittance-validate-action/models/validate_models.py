from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, Type, TypeVar, List, Union
from enum import Enum
from datetime import datetime
import json
import numpy as np
from pandas import Series
from sema4ai.di_client.document_intelligence_client.models.extracted_document_content import ExtractedDocumentContent
from sema4ai.di_client.document_intelligence_client.models.transformed_document_content import TransformedDocumentContent
from sema4ai.di_client.document_intelligence_client.models.computed_document_content import ComputedDocumentContent


class ProcessingPhase(str, Enum):
    EXTRACTION = "Extraction"
    TRANSFORMATION = "Transformation"
    VALIDATION = "Validation"
    
class ValidationStatus(str, Enum):
    VALIDATION_PASSED = "VALIDATION_PASSED"
    VALIDATION_FAILED = "VALIDATION_FAILED"

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

class PreprocessingSummary(BaseModel):
    page_patterns_compiled: Optional[bool] = Field(False, description="Indicates if page patterns were successfully compiled")
    header_identification_method: Optional[str] = Field(None, description="The method used to identify headers")
    charge_type_sections_identified: Optional[List[str]] = Field(default_factory=list, description="List of charge type sections identified in the document")

    model_config = ConfigDict(json_encoders={Series: lambda v: v.to_list()})

class TableExtractionMetrics(BaseModel):

    tables_per_page: Optional[Dict[int, int]] = Field(default_factory=dict, description="A mapping of page numbers to the number of tables extracted from each")
    empty_columns_dropped: Optional[List[str]] = Field(default_factory=list, description="List of column names that were dropped due to being empty")
    columns_renamed: Optional[Dict[str, str]] = Field(default_factory=dict, description="A mapping of original column names to their renamed versions")
    total_raw_tables: Optional[int] = Field(default=0, description="Total number of raw tables extracted")
    total_raw_rows: Optional[int] = Field(default=0, description="Total number of raw rows extracted")
    extracted_tables: Optional[int] = Field(default=0, description="Total number of tables successfully extracted")
    extracted_rows: Optional[int] = Field(default=0, description="Total number of rows successfully extracted")
    
    # New fields for invoice details
    invoice_details_extracted_tables: Optional[int] = Field(default=0, description="Number of invoice detail tables extracted")
    invoice_details_extracted_rows: Optional[int] = Field(default=0, description="Number of rows extracted from invoice detail tables")
    
    # New fields for summary tables
    summary_extracted_tables: Optional[int] = Field(default=0, description="Number of summary tables extracted")
    summary_extracted_rows: Optional[int] = Field(default=0, description="Number of rows extracted from summary tables")

    model_config = ConfigDict(json_encoders={Series: lambda v: v.to_list()})
    
class ValidationCheckpoint(BaseModel):
    stage: Optional[str] = Field(None, description="The stage of processing where the validation occurred")
    checks_performed: Optional[List[str]] = Field(default_factory=list, description="List of validation checks performed")
    checks_passed: Optional[List[str]] = Field(default_factory=list, description="List of validation checks that passed")
    checks_failed: Optional[List[str]] = Field(default_factory=list, description="List of validation checks that failed")

    model_config = ConfigDict(json_encoders={Series: lambda v: v.to_list()})

class TransformationStep(BaseModel):
    step_name: Optional[str] = Field(None, description="The name of the transformation step")
    rows_affected: Optional[int] = Field(0, description="The number of rows affected by this transformation")
    calculation_performed: Optional[str] = Field(None, description="Description of any calculation performed during this step")

    model_config = ConfigDict(json_encoders={Series: lambda v: v.to_list()})

class DataQualityIndicators(BaseModel):
    completeness: Optional[float] = Field(0.0, ge=0, le=1, description="Measure of data completeness (0-1)")
    consistency: Optional[float] = Field(0.0, ge=0, le=1, description="Measure of data consistency (0-1)")
    accuracy: Optional[float] = Field(0.0, ge=0, le=1, description="Measure of data accuracy (0-1)")

    model_config = ConfigDict(json_encoders={Series: lambda v: v.to_list()})

class ValidationSeverity(str, Enum):
    ERROR = "Error"
    WARNING = "Warning"
    INFO = "Info"

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
    



class ProcessingSummary(BaseModel):
    phase: Optional[ProcessingPhase] = Field(None, description="The current processing phase")
    start_time: Optional[datetime] = Field(None, description="The start time of the processing phase")
    end_time: Optional[datetime] = Field(None, description="The end time of the processing phase")
    processing_events: Optional[List[ProcessingEvent]] = Field(default_factory=list, description="A list of processing events that occurred during this phase")
    data_metrics: Optional[DataMetrics] = Field(default_factory=DataMetrics, description="Metrics about the data processed in this phase")
    preprocessing_summary: Optional[PreprocessingSummary] = Field(None, description="Summary of the preprocessing steps")
    table_extraction_metrics: TableExtractionMetrics = Field(default_factory=TableExtractionMetrics, escription="Metrics related to table extraction")
    transformation_steps: Optional[List[TransformationStep]] = Field(default_factory=list, description="List of transformation steps performed")
    performance_metrics: Optional[Dict[str, float]] = Field(default_factory=dict, description="Performance metrics for various processing steps")
    data_quality_indicators: Optional[DataQualityIndicators] = Field(default_factory=DataQualityIndicators, description="Indicators of data quality for this phase")

    model_config = ConfigDict(json_encoders={Series: lambda v: v.to_list()})

class ProcessingContext(BaseModel):
    document_id: Optional[str] = Field(None, description="The unique identifier of the document being processed")
    document_name: Optional[str] = Field(None, description="The name of the document being processed")
    processing_phase: Optional[ProcessingPhase] = Field(None, description="The current processing phase")
    summary: Optional[ProcessingSummary] = Field(default_factory=ProcessingSummary, description="A summary of the processing for this phase")
    validation_results: Optional[ValidationResults] = Field(default_factory=ValidationResults, description="Results of validation checks, if applicable")
    configuration_used: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Configuration settings used for this processing phase")
    additional_context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Any additional context relevant to this processing phase")

    model_config = ConfigDict(json_encoders={Series: lambda v: v.to_list()})


class AgentInsightContext(BaseModel):
    document_id: str = Field(..., description="The unique identifier of the document")
    document_name: str = Field(..., description="The name of the document")
    extraction_context: Optional[ProcessingContext] = Field(None, description="Context for the extraction phase")
    transformation_context: Optional[ProcessingContext] = Field(None, description="Context for the transformation phase")
    validation_context: Optional[ProcessingContext] = Field(None, description="Context for the validation phase")
    overall_processing_time: Optional[float] = Field(0.0, description="Total time taken for all processing phases in seconds")
    overall_status: Optional[str] = Field(None, description="Overall status of the document processing (e.g., 'Completed', 'Failed')")

    model_config = ConfigDict(json_encoders={Series: lambda v: v.to_list()})
    
    
    def get_phase_status(self, phase: ProcessingPhase) -> str:
        """
        Get the status of a specific processing phase.

        This method retrieves the overall status of the specified phase based on its validation results.
        If the phase has no validation results or an empty list of results, it is considered "Passed".

        Args:
            phase (ProcessingPhase): The processing phase to get the status for.

        Returns:
            str: A string representing the status of the phase. Possible values are:
                - "Passed": All validations for the phase passed or no validations were performed.
                - "Failed": At least one validation for the phase failed.
                - "Not Processed": If the context for the phase is not available.
        """
        context = getattr(self, f"{phase.value.lower()}_context")
        if not context:
            return "Not Processed"

        if not context.validation_results or not context.validation_results.results:
            return "Passed"
        
        return "Passed" if context.validation_results.get_overall_status() else "Failed"

    def get_validation_results(self, phase: ProcessingPhase) -> Optional[ValidationResults]:
        """
        Retrieve validation results for a specific processing phase.

        Args:
            phase (ProcessingPhase): The processing phase to get validation results for.

        Returns:
            Optional[ValidationResults]: The validation results for the specified phase, or None if not available.
        """
        context = getattr(self, f"{phase.value.lower()}_context")
        return context.validation_results if context else None
    
    def reset_validation_results(self, phase: ProcessingPhase):
        """
        Reset validation results for a specific processing phase.

        Args:
            phase (ProcessingPhase): The processing phase to reset validation results for.
        """
        context = getattr(self, f"{phase.value.lower()}_context")
        if context:
            context.validation_results = ValidationResults()

    def get_processing_summary(self, phase: ProcessingPhase) -> Optional[ProcessingSummary]:
        """
        Retrieve the processing summary for a specific phase.

        Args:
            phase (ProcessingPhase): The processing phase to get the summary for.

        Returns:
            Optional[ProcessingSummary]: The processing summary for the specified phase, or None if not available.
        """
        context = getattr(self, f"{phase.value.lower()}_context")
        return context.summary if context else None

    def get_processing_events(self, phase: ProcessingPhase) -> List[ProcessingEvent]:
        """
        Retrieve the list of processing events for a specific phase.

        Args:
            phase (ProcessingPhase): The processing phase to get events for.

        Returns:
            List[ProcessingEvent]: A list of processing events for the specified phase. Returns an empty list if no events are found.
        """
        context = getattr(self, f"{phase.value.lower()}_context")
        return context.summary.processing_events if context and context.summary else []

    def get_data_metrics(self, phase: ProcessingPhase) -> Optional[DataMetrics]:
        """
        Retrieve data metrics for a specific processing phase.

        Args:
            phase (ProcessingPhase): The processing phase to get data metrics for.

        Returns:
            Optional[DataMetrics]: The data metrics for the specified phase, or None if not available.
        """
        context = getattr(self, f"{phase.value.lower()}_context")
        return context.summary.data_metrics if context and context.summary else None

    def get_table_extraction_metrics(self) -> Optional[TableExtractionMetrics]:
        """
        Retrieve table extraction metrics from the extraction phase.

        Returns:
            Optional[TableExtractionMetrics]: The table extraction metrics, or None if not available.
        """
        if self.extraction_context and self.extraction_context.summary:
            return self.extraction_context.summary.table_extraction_metrics
        return None

    def get_transformation_steps(self) -> List[TransformationStep]:
        """
        Retrieve the list of transformation steps from the transformation phase.

        Returns:
            List[TransformationStep]: A list of transformation steps. Returns an empty list if no steps are found.
        """
        if self.transformation_context and self.transformation_context.summary:
            return self.transformation_context.summary.transformation_steps
        return []

    def get_data_quality_indicators(self, phase: ProcessingPhase) -> Optional[DataQualityIndicators]:
        """
        Retrieve data quality indicators for a specific processing phase.

        Args:
            phase (ProcessingPhase): The processing phase to get data quality indicators for.

        Returns:
            Optional[DataQualityIndicators]: The data quality indicators for the specified phase, or None if not available.
        """
        context = getattr(self, f"{phase.value.lower()}_context")
        return context.summary.data_quality_indicators if context and context.summary else None

    def get_all_validation_results(self) -> Dict[ProcessingPhase, ValidationResults]:
        """
        Retrieve validation results for all processing phases.

        Returns:
            Dict[ProcessingPhase, ValidationResults]: A dictionary mapping processing phases to their respective validation results.
            Only phases with available validation results are included.
        """
        return {
            phase: self.get_validation_results(phase)
            for phase in ProcessingPhase
            if self.get_validation_results(phase) is not None
        }

    def get_overall_validation_status(self) -> bool:
        """
        Determine the overall validation status across all processing phases.

        Returns:
            bool: True if all phases have passed validation, False otherwise.
        """
        return all(
            results.get_overall_status()
            for results in self.get_all_validation_results().values()
        )

    def get_error_results(self, phase: Optional[ProcessingPhase] = None) -> List[ValidationResult]:
        """
        Retrieve error results from validation, optionally filtered by processing phase.

        Args:
            phase (Optional[ProcessingPhase]): The specific phase to get error results for. If None, retrieves errors from all phases.

        Returns:
            List[ValidationResult]: A list of validation results with error severity.
        """
        if phase:
            results = self.get_validation_results(phase)
            return results.error_results if results else []
        else:
            return [
                error
                for results in self.get_all_validation_results().values()
                for error in results.error_results
            ]

    def get_warning_results(self, phase: Optional[ProcessingPhase] = None) -> List[ValidationResult]:
        """
        Retrieve warning results from validation, optionally filtered by processing phase.

        Args:
            phase (Optional[ProcessingPhase]): The specific phase to get warning results for. If None, retrieves warnings from all phases.

        Returns:
            List[ValidationResult]: A list of validation results with warning severity.
        """
        if phase:
            results = self.get_validation_results(phase)
            return results.warning_results if results else []
        else:
            return [
                warning
                for results in self.get_all_validation_results().values()
                for warning in results.warning_results
            ]

    def get_processing_time(self, phase: ProcessingPhase) -> Optional[float]:
        """
        Calculate the processing time for a specific phase.

        Args:
            phase (ProcessingPhase): The processing phase to get the processing time for.

        Returns:
            Optional[float]: The processing time in seconds for the specified phase, or None if not available.
        """
        context = getattr(self, f"{phase.value.lower()}_context")
        if context and context.summary and context.summary.start_time and context.summary.end_time:
            return (context.summary.end_time - context.summary.start_time).total_seconds()
        return None

    def get_configuration_used(self, phase: ProcessingPhase) -> Dict[str, Any]:
        """
        Retrieve the configuration used for a specific processing phase.

        Args:
            phase (ProcessingPhase): The processing phase to get the configuration for.

        Returns:
            Dict[str, Any]: The configuration used for the specified phase. Returns an empty dictionary if no configuration is found.
        """
        context = getattr(self, f"{phase.value.lower()}_context")
        return context.configuration_used if context else {}

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the AgentInsightContext instance to a dictionary.

        Returns:
            Dict[str, Any]: A dictionary representation of the AgentInsightContext instance.
        """
        return json.loads(self.model_dump_json())

    def model_dump_json(self, **kwargs):
        """
        Serialize the AgentInsightContext instance to a JSON string.

        Args:
            **kwargs: Additional keyword arguments to pass to json.dumps().

        Returns:
            str: A JSON string representation of the AgentInsightContext instance.
        """
        return json.dumps(self.model_dump(exclude_none=True), default=self._json_default, **kwargs)

    @staticmethod
    def _json_default(obj):
        """
        Custom JSON encoder for handling non-standard types during serialization.

        Args:
            obj: The object to be serialized.

        Returns:
            A JSON-serializable representation of the object.
        """
        if isinstance(obj, Series):
            return obj.to_list()
        elif hasattr(obj, 'model_dump'):
            return obj.model_dump()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)


class PhaseResult(BaseModel):
    agent_insight_context: Optional[AgentInsightContext] = Field(None, description="The context of the agent insight")
    document_content: Optional[Union[ExtractedDocumentContent, TransformedDocumentContent, ComputedDocumentContent]] = Field(None, description="The content of the phase result")

    model_config = ConfigDict(json_encoders={Series: lambda v: v.to_list()})

class ExtractionResult(PhaseResult):
    document_content: Optional[ExtractedDocumentContent] = Field(None, description="The content of the extraction result")

class TransformationResult(PhaseResult):
    document_content: Optional[TransformedDocumentContent] = Field(None, description="The content of the transformation result")

class ValidationFinalResult(PhaseResult):
    # add a field for to indicate the status of the validation
    validation_status: Optional[ValidationStatus] = Field(None, description="The status of the validation")
    document_content: Optional[ComputedDocumentContent] = Field(None, description="The content of the validation final result")

T = TypeVar('T', bound='ActionResponse')

class ActionStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL_SUCCESS = "partial_success"

class ActionResponse(BaseModel):
    status: ActionStatus = Field(..., description="The overall status of the action")
    message: str = Field(..., description="A brief summary or instruction for the agent")
    agent_insight_context: Optional[AgentInsightContext] = None
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
            data['agent_insight_context'] = AgentInsightContext.model_validate(data['agent_insight_context'])
        return data

    def __str__(self):
        return f"ActionResponse(status={self.status.value}, message='{self.message}')"

    def __repr__(self):
        return self.__str__()
    
    