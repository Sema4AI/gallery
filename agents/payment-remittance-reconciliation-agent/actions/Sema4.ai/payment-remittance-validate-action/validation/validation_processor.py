from enum import unique
import json
import math
from re import sub
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple

# Import from DuckDB
from duckdb import table

# Import from sema4ai DI client models
from sema4ai.di_client.document_intelligence_client.models.document_work_item import DocumentWorkItem
from sema4ai.di_client.document_intelligence_client.models.document_format import DocumentFormat
from sema4ai.di_client.document_intelligence_client.models.raw_document_content import RawDocumentContent
from sema4ai.di_client.document_intelligence_client.models.extracted_document_content import ExtractedDocumentContent
from sema4ai.di_client.document_intelligence_client.models.transformed_document_content import TransformedDocumentContent
from sema4ai.di_client.document_intelligence_client.models.computed_document_content import ComputedDocumentContent
from sema4ai.di_client.document_intelligence_client.models.raw_document_content_all_of_raw_content import RawDocumentContentAllOfRawContent

# Import from utils
from utils.extraction.table_extractor import TableExtractor
from utils.extraction.document_intelligence_utils import DocumentIntelligenceUtility
from utils.extraction.document_processor_base import DocumentProcessorBase
from context.validate_agent_context_manager import ValidationAgentContextManager
from models.validate_models import (
    ValidationResults,
    ValidationSeverity,
    ValidationStatus,
    ProcessingPhase,
    ExtractionResult,
    TransformationResult,
    ValidationFinalResult
)
from utils.extraction.common_validation_rules import *
from utils.logging.ultimate_serializer import serialize_any_object_safely, clean_any_object_safely

# Import use case-specific constants
from validation.validation_constants import (
    CONFIG_FACILITY_NAME_MAPPING_KEY,
    COMPUTED_COLUMN_FACILITY_TYPE,
    COMPUTED_TOTAL_INVOICE_AMOUNT_BY_FACILITY_TYPE,
    COMPUTED_TOTAL_NUMBER_OF_INVOICES_IN_REMITTANCE,
    COLUMN_INVOICE_NUMBER,
    COLUMN_INVOICE_DATE,
    COLUMN_CO2_SUPPLEMENTATION,
    COLUMN_SUBTOTAL_INVOICE_AMOUNT,
    INVOICE_TABLE_KEY,
    SUBTOTALS_TABLE_KEY
)


COMPUTABLE_DOCUMENT_TYPE_FIELDS = [COMPUTED_TOTAL_NUMBER_OF_INVOICES_IN_REMITTANCE, COMPUTED_TOTAL_INVOICE_AMOUNT_BY_FACILITY_TYPE  ]

class ValidationProcessor(DocumentProcessorBase):


    def __init__(self, remittance_work_item: DocumentWorkItem, agent_context_manager: ValidationAgentContextManager):
        self.logger = logging.getLogger(__name__)
        self.work_item = remittance_work_item 
        self.source_document = remittance_work_item.source_document
        
        self.agent_insight_context_manager : ValidationAgentContextManager = agent_context_manager
        
        self.di_utility : DocumentIntelligenceUtility = DocumentIntelligenceUtility(self.source_document.document_type, self.source_document.document_format, self.agent_insight_context_manager)
        self.table_extractor = TableExtractor(self.source_document, self.agent_insight_context_manager)


    @ValidationAgentContextManager.track_method_execution(method_name="extract_and_structure_content")
    def extract_and_structure_content(self, raw_document: RawDocumentContent) -> ExtractionResult:
        """
        Extracts and structures content from a raw document.

        This method performs a series of steps to extract, standardize, validate, and structure
        the content of a raw document. It tracks the execution of the extraction process and logs
        relevant events and information.

        Args:
            raw_document (RawDocumentContent): The raw content of the document to be processed.

        Returns:
            ExtractionResult: The result of the extraction process, including the structured content
            and the agent insight context.
        """
        with self.agent_insight_context_manager.phase_context(ProcessingPhase.EXTRACTION):
            self.logger.info(f"Starting extraction process for document: {self.source_document.document_name}")

            self.agent_insight_context_manager.add_event("Extraction Start", 
                                                        f"Beginning extraction process for document: {self.source_document.document_name}")
            
            # Step 1: Add document type and format configs to agent context
            self._add_document_configs_to_agent_context()

            # Step 2: Extract non-tabular fields already parsed and mapped by the DI Pipeline
            non_tabular_data: Dict = self._extract_non_tabular_fields()

            # Step 3: Extract tables from raw content using TableExtractor with Regular Expressions
            extraction_result: Dict[str, Any] = self._extract_tables(raw_document.raw_content)
            
            # Based on our Extraction Propmpt, we have two tables: Invoice Details and Summary of the Subtotals by Facility Type
            invoice_details_df = extraction_result.get('invoice_details', pd.DataFrame())
            summary_df = extraction_result.get('summary', pd.DataFrame())

            # Step 4: Standardize the data to the document type schema and validate 
            standardized_non_tabular_data = self.di_utility.standardize_non_tabular_to_doc_type_schema(non_tabular_data)
            
            invoice_details_table_name = self._get_remittance_table_names().get(INVOICE_TABLE_KEY, None)
            subtotals_table_name = self._get_remittance_table_names().get(SUBTOTALS_TABLE_KEY, None)
            if invoice_details_table_name is None or subtotals_table_name is None:
                raise ValueError("Could not find invoice details table")

            standardized_invoice_details = self.di_utility.standardize_tabular_to_doc_type_schema({"table_data": invoice_details_df.to_dict('records')}, 
                                                                                                  table_name=invoice_details_table_name)
            # Summary Table already mapped by the DI Pipeline
            standardized_summary = summary_df.to_dict('records')

            # Step 5: Perform type conversations and validate data for both non-tabular and tabular data
            all_validation_results = ValidationResults()
            
            converted_non_tabular_data, non_tabular_validation = self.di_utility.validate_and_clean_non_tabular(
                standardized_non_tabular_data, 
                exclude_field_validate_list=COMPUTABLE_DOCUMENT_TYPE_FIELDS
            )
            all_validation_results.add_validation_results(non_tabular_validation)

            converted_invoice_details_df, invoice_details_validation = self.di_utility.validate_and_clean_tabular(
                standardized_invoice_details["table_data"], 
                invoice_details_table_name,
                exclude_field_validate_list=COMPUTABLE_DOCUMENT_TYPE_FIELDS
            )
            all_validation_results.add_validation_results(invoice_details_validation)

            converted_summary_df, summary_validation = self.di_utility.validate_and_clean_tabular(
                standardized_summary, 
                subtotals_table_name,
                exclude_field_validate_list=COMPUTABLE_DOCUMENT_TYPE_FIELDS
            )
            all_validation_results.add_validation_results(summary_validation)
            

            # Add validation results to agent context
            self.agent_insight_context_manager.add_validation_results(all_validation_results)
            
            # Step 6: Prepare extracted content for both non-tabular and tabular data
            # clean_invoice_details_df = converted_invoice_details_df.apply(lambda col: col.where(pd.notna(col), None))
            # clean_summary_df = converted_summary_df.apply(lambda col: col.where(pd.notna(col), None))
            clean_invoice_details_dict = clean_any_object_safely(converted_invoice_details_df.to_dict('records'))
            clean_summary_df_dict = clean_any_object_safely(converted_summary_df.to_dict('records'))
            extracted_content = {
                'document_id': self.source_document.document_id,
                'document_name': self.source_document.document_name,
                'fields': converted_non_tabular_data,
                'invoice_details': clean_invoice_details_dict,
                'summary': clean_summary_df_dict
            }

            # Create ExtractedDocumentContent
            extracted_document_content = ExtractedDocumentContent(
                content_state="Extracted",
                document_id=self.source_document.document_id,
                extracted_content=extracted_content
            )

            # Step 7: Create and return ExtractionResult
            extraction_result = ExtractionResult(
                document_content=extracted_document_content, 
                agent_insight_context=self.agent_insight_context_manager.get_agent_context()
            )
            self.logger.info(f"Completed extraction process for document: {self.source_document.document_name}")

            return extraction_result

            
    @ValidationAgentContextManager.track_method_execution(method_name="transform_and_enrich_content")
    def transform_and_enrich_content(self, extracted_document_content: ExtractedDocumentContent) -> TransformationResult:
        """
        Transforms and enriches the extracted content of a document.

        This method performs a series of steps to transform and enrich the extracted content of a document.
        It tracks the execution of the transformation process and logs relevant events and information.

        Args:
            extracted_document_content (ExtractedDocumentContent): The extracted content of the document to be processed.

        Returns:
            TransformationResult: The result of the transformation process, including the enriched content
            and the agent insight context.
        """
        with self.agent_insight_context_manager.phase_context(ProcessingPhase.TRANSFORMATION):
            # Use the helper function for setup and initial logging
            document_id, invoice_details_df, summary_df, non_tabular_data = self._setup_transformation(extracted_document_content)
            
            # Compute Total Number of Invoice Line Items Field
            total_invoice_line_items = self._compute_total_invoice_line_items(invoice_details_df)
            
            # Extract subtotals for each Facility Type
            invoice_subtotals_by_facility_type = self._compute_invoice_totals_by_facility_type(invoice_details_df)
            
            # Compute total amount paid
            total_amount_paid = self._compute_total_amount_paid(invoice_details_df)
            
            clean_invoice_details_dict = clean_any_object_safely(invoice_details_df.to_dict('records'))
            clean_summary_df_dict = clean_any_object_safely(summary_df.to_dict('records'))
            # Enrich the content with computed fields
            enriched_content = {
                'document_id': document_id,
                'fields': non_tabular_data,
                'invoice_details': clean_invoice_details_dict,
                'summary': clean_summary_df_dict,
                'computed_fields': {
                    'total_invoice_line_items': total_invoice_line_items,
                    'invoice_subtotals_grouped_by_facility_type': invoice_subtotals_by_facility_type,
                    'computed_total_amount_paid': total_amount_paid
                }
            }
            
            self.agent_insight_context_manager.add_event(
                "Computed Fields",
                "Computed fields for the extracted content",
                {
                    "computed_fields": {
                        "total_invoice_line_items": total_invoice_line_items,
                        "invoice_subtotals_grouped_by_facility_type": invoice_subtotals_by_facility_type,
                        "computed_total_amount_paid": total_amount_paid
                    }
                }
            )
            
            transformed_document_content = TransformedDocumentContent(
                content_state="Transformed",
                document_id=document_id,
                transformed_content=enriched_content
            )
            
            self.agent_insight_context_manager.add_event("Transformation Complete", "Completed content transformation and enrichment")
            
            self.logger.info("transformed_document_content being return as part of Trasnforemd REsult is: " + serialize_any_object_safely(transformed_document_content))
            return TransformationResult(
                document_content=transformed_document_content,
                agent_insight_context=self.agent_insight_context_manager.get_agent_context()
            )
                        
    @ValidationAgentContextManager.track_method_execution(method_name="validate_and_finalize_content")
    def validate_and_finalize_content(self, transformed_doc: TransformedDocumentContent) -> ValidationFinalResult:

        """
        Validates and finalizes the transformed content of a document.

        This method performs a series of steps to validate and finalize the transformed content of a document.
        It tracks the execution of the validation process and logs relevant events and information.

        Args:
            transformed_doc (TransformedDocumentContent): The transformed content of the document to be processed.

        Returns:
            ValidationFinalResult: The result of the validation process, including the finalized content
            and the agent insight context. If there are validation failures, the content will be the validation results.
            Otherwise, it will be the transformed content.
        """
        
        with self.agent_insight_context_manager.phase_context(ProcessingPhase.VALIDATION):
            self.agent_insight_context_manager.add_event("Validation Start", "Beginning content validation")

            validation_results = ValidationResults()

            self._validate_total_invoices(transformed_doc, validation_results)
            self._validate_facility_type_subtotals(transformed_doc, validation_results)
            self._validate_total_payment(transformed_doc, validation_results)
            self._validate_discounts_and_charges(transformed_doc, validation_results)
            
            # Compile Validation metrics for the Agent
            self._calculate_validation_metrics_and_save_to_agent_context(validation_results)

            # if there are failures, then the content of teh ComputedDocumentContent will be he validation results if not then the transformed content
            computed_content = None
            vaildation_status = None
            if validation_results.has_failures():
                vaildation_status = ValidationStatus.VALIDATION_FAILED
                computed_content = validation_results.model_dump()
            else:
                vaildation_status = ValidationStatus.VALIDATION_PASSED  
                computed_content = transformed_doc.transformed_content
            
            computed_document_content : ComputedDocumentContent = ComputedDocumentContent(
                content_state="Computed",
                document_id=transformed_doc.document_id,
                computed_content=computed_content
            )   
            
            self.agent_insight_context_manager.add_event("Validation Complete", "Completed content validation")

            return ValidationFinalResult(
                validation_status=vaildation_status,
                document_content= computed_document_content,
                agent_insight_context=self.agent_insight_context_manager.get_agent_context() # has the full avlidation results as well
            )
    def _validate_total_invoices(self, transformed_doc, validation_results):
        total_invoices = int(transformed_doc.transformed_content['fields']['Total Invoices'])
        computed_total = transformed_doc.transformed_content['computed_fields']['total_invoice_line_items']
        
        validation_results.add_result(
            rule_id=RULE_TOTAL_INVOICES,
            passed=(total_invoices == computed_total),
            message=f"Total Invoices ({total_invoices}) {'matches' if total_invoices == computed_total else 'does not match'} the number of invoice line items ({computed_total})",
            severity=ValidationSeverity.ERROR if total_invoices != computed_total else ValidationSeverity.INFO,
            details={"extracted_total": total_invoices, "computed_total": computed_total}
        )

    def _validate_facility_type_subtotals(self, transformed_doc, validation_results):
        computed_subtotals = transformed_doc.transformed_content['computed_fields']['invoice_subtotals_grouped_by_facility_type']
        summary_data = transformed_doc.transformed_content['summary']
        
        all_subtotals_match = True
        details = {}
        mismatched_types = []

        for summary_item in summary_data:
            facility_type = summary_item['Facility Type']
            extracted_subtotal = float(summary_item['Subtotal Invoice Amount'])
            computed_subtotal = computed_subtotals.get(facility_type, 0)
            
            subtotal_matches = abs(computed_subtotal - extracted_subtotal) < 0.25
            
            if not subtotal_matches:
                all_subtotals_match = False
                mismatched_types.append(facility_type)
            
            details[facility_type] = {
                "computed_subtotal": computed_subtotal,
                "extracted_subtotal": extracted_subtotal,
                "matches": subtotal_matches
            }

        message = "All facility type subtotals match" if all_subtotals_match else f"Subtotals do not match for the following facility types: {', '.join(mismatched_types)}"

        validation_results.add_result(
            rule_id=RULE_FACILITY_TYPE_SUBTOTALS,
            passed=all_subtotals_match,
            message=message,
            severity=ValidationSeverity.ERROR if not all_subtotals_match else ValidationSeverity.INFO,
            details={"all_subtotals": details, "mismatched_types": mismatched_types}
        )

    def _find_extracted_subtotal(self, summary_data, facility_type):
        matching_row = summary_data[summary_data['Facility Type'] == facility_type]
        if not matching_row.empty:
            return float(matching_row['Subtotal Invoice Amount'].iloc[0])
        return 0.0
    
    def _validate_total_payment(self, transformed_doc, validation_results):
        extracted_total_payment = float(transformed_doc.transformed_content['fields']['Total Payment Paid'])
        computed_total_payment = transformed_doc.transformed_content['computed_fields']['computed_total_amount_paid']
        
        is_matching = abs(extracted_total_payment - computed_total_payment) < 0.01
        
        validation_results.add_result(
            rule_id=RULE_TOTAL_PAYMENT,
            passed=is_matching,
            message=f"Total Payment {'matches' if is_matching else 'does not match'}: Extracted ({extracted_total_payment:.2f}) vs Computed ({computed_total_payment:.2f})",
            severity=ValidationSeverity.ERROR if not is_matching else ValidationSeverity.INFO,
            details={"extracted_total_payment": extracted_total_payment, "computed_total_payment": computed_total_payment, "difference": extracted_total_payment - computed_total_payment}
        )

    def _validate_discounts_and_charges(self, transformed_doc, validation_results):
        # Extract totals from fields
        fields = transformed_doc.transformed_content['fields']
        total_discounts = float(fields.get('Total Discounts Applied', 0))
        total_charges = float(fields.get('Total Additional Charges', 0))

        # Extract invoice details
        invoice_details = transformed_doc.transformed_content['invoice_details']

        # Compute sums from invoice details
        computed_discounts = sum(float(item.get('Discounts Applied', 0)) for item in invoice_details)
        computed_charges = sum(float(item.get('Additional Charges', 0)) for item in invoice_details)

        # Validate discounts
        discounts_match = abs(total_discounts - computed_discounts) < 0.01
        validation_results.add_result(
            rule_id=RULE_TOTAL_DISCOUNTS,
            passed=discounts_match,
            message=f"Total Discounts {'match' if discounts_match else 'do not match'}: Total ({total_discounts:.2f}) vs Computed ({computed_discounts:.2f})",
            severity=ValidationSeverity.ERROR if not discounts_match else ValidationSeverity.INFO,
            details={"total_discounts": total_discounts, "computed_discounts": computed_discounts}
        )

        # Validate charges
        charges_match = abs(total_charges - computed_charges) < 0.01
        validation_results.add_result(
            rule_id=RULE_TOTAL_CHARGES,
            passed=charges_match,
            message=f"Total Additional Charges {'match' if charges_match else 'do not match'}: Total ({total_charges:.2f}) vs Computed ({computed_charges:.2f})",
            severity=ValidationSeverity.ERROR if not charges_match else ValidationSeverity.INFO,
            details={"total_charges": total_charges, "computed_charges": computed_charges}
        )

        # Log validation results
        self.logger.info(f"Discounts validation: {'Passed' if discounts_match else 'Failed'}")
        self.logger.info(f"Charges validation: {'Passed' if charges_match else 'Failed'}")

        # Add event to agent context
        self.agent_insight_context_manager.add_event(
            "Discounts and Charges Validation",
            f"Discounts: {'Match' if discounts_match else 'Mismatch'}, Charges: {'Match' if charges_match else 'Mismatch'}",
            {
                "discounts_match": discounts_match,
                "charges_match": charges_match,
                "total_discounts": total_discounts,
                "computed_discounts": computed_discounts,
                "total_charges": total_charges,
                "computed_charges": computed_charges
            }
        )

    def _calculate_validation_metrics_and_save_to_agent_context(self, validation_results: ValidationResults):
        """
        Compile and save validation metrics to the agent context.

        Args:
            validation_results (ValidationResults): The validation results to compile metrics from.
        """
        # Compile validation metrics
        total_validations = validation_results.get_total_results()
        passed_validations = sum(1 for result in validation_results.results if result.passed)
        failed_validations = total_validations - passed_validations        
        
        # Add detailed validation metrics to agent context
        validation_metrics = {"validation_metrics": {
            "total_validations": total_validations,
            "passed_validations": passed_validations,
            "failed_validations": failed_validations,
            "pass_rate": passed_validations / total_validations if total_validations > 0 else 0
        }}  
        self.agent_insight_context_manager.update_metrics(validation_metrics)
        # Add all validation results to the agent context
        self.agent_insight_context_manager.add_validation_results(validation_results)
            

    
    def _compute_facility_type(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Facility Type'] = df['Invoice Number'].apply(self.get_facility_type)
        return df

    def _compute_total_invoice_line_items(self, df: pd.DataFrame) -> int:
        return len(df)
    
    def _compute_invoice_totals_by_facility_type(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Compute the total paid amount per facility type, taking into account discounts.
        Formula: Sum(Invoice Amount - Discounts Applied) grouped by Facility Type
        
        Args:
            df (pd.DataFrame): DataFrame containing invoice details
            
        Returns:
            Dict[str, float]: Dictionary mapping facility types to their total paid amounts
        """
        self.logger.info("Computing invoice totals by facility type")
        self.logger.info(f"Invoice Amount is: {df['Invoice Amount']}. Type is {type(df['Invoice Amount'])}")
        self.logger.info(f"Discounts Applied is: {df['Discounts Applied']}. Type is {type(df['Discounts Applied'])}")
        # Calculate net amount paid per row (Invoice Amount - Discounts Applied)
        df['Net Amount'] = df['Invoice Amount'] - df['Discounts Applied']
        
        # Group by Facility Type and sum the net amounts
        facility_totals = df.groupby('Facility Type')['Net Amount'].sum().to_dict()
        
        self.agent_insight_context_manager.add_event(
            "Facility Type Totals Computation",
            "Computed totals by facility type including discount adjustments",
            {"totals": facility_totals}
        )
    
        return facility_totals


    def _compute_total_amount_paid(self, df: pd.DataFrame) -> float:
        # Log all values and compute the sum in one go using apply
        self.logger.info("Computing total amount paid")
        total_amount_paid = df['Amount Paid'].apply(lambda x: self.logger.info(f"Adding: {x}") or x).sum()
        self.logger.info(f"Total amount paid: {total_amount_paid}")
        return total_amount_paid

    def _add_document_configs_to_agent_context(self):
        """Add document type and format configurations to the agent context."""
        doc_type_config = {
            'non_tbl_fields': [field.dict() for field in self.source_document.document_type.non_tbl_fields],
            'tbl_fields': [table.dict() for table in self.source_document.document_type.tbl_fields],
        }
        doc_format_config = {
            'non_tbl_fields_mapping': [mapping.dict() for mapping in self.source_document.document_format.non_tbl_fields_mapping],
            'tables': [table.dict() for table in self.source_document.document_format.tables],
            'prompt_examples': self.source_document.document_format.prompt_examples,
            'custom_config': self.source_document.document_format.custom_config,
        }
        self.agent_insight_context_manager.add_document_type_config(doc_type_config)
        self.agent_insight_context_manager.add_document_format_config(doc_format_config)
        
    def _setup_transformation(self, extracted_document_content: ExtractedDocumentContent) -> Tuple[str, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        document_id = extracted_document_content.document_id
        invoice_details_data: List[Dict[str, Any]] = extracted_document_content.extracted_content['invoice_details']
        summary_data: List[Dict[str, Any]] = extracted_document_content.extracted_content['summary']
        non_tabular_data: Dict[str, Any] = extracted_document_content.extracted_content['fields']

        # Convert tabular data to DataFrames
        invoice_details_df = pd.DataFrame(invoice_details_data)
        summary_df = pd.DataFrame(summary_data)

        # Calculate metrics for tabular data
        invoice_details_rows = invoice_details_df.shape[0]
        invoice_details_columns = invoice_details_df.shape[1]
        summary_rows = summary_df.shape[0]
        summary_columns = summary_df.shape[1]

        # Calculate metrics for non-tabular data
        num_non_tabular_fields = len(non_tabular_data)

        # Log the start of the transformation process and the metrics
        self.logger.info("Starting content transformation and enrichment")
        self.logger.info(f"Document ID: {document_id}")
        self.logger.info(f"Invoice Details - Rows: {invoice_details_rows}, Columns: {invoice_details_columns}")
        self.logger.info(f"Summary - Rows: {summary_rows}, Columns: {summary_columns}")
        self.logger.info(f"Non-Tabular Data - Fields: {num_non_tabular_fields}")

        # Add event to agent context
        self.agent_insight_context_manager.add_event(
            "Transformation and Enrichment Start",
            "Beginning content transformation and enrichment",
            {
                "document_id": document_id,
                "invoice_details_metrics": {
                    "num_rows": invoice_details_rows,
                    "num_columns": invoice_details_columns
                },
                "summary_metrics": {
                    "num_rows": summary_rows,
                    "num_columns": summary_columns
                },
                "non_tabular_data_metrics": {
                    "num_fields": num_non_tabular_fields
                }
            }
        )

        return document_id, invoice_details_df, summary_df, non_tabular_data

    def _extract_non_tabular_fields(self) -> Dict:
        """Extract non-tabular fields from the work item."""
        non_tabular_data = self.work_item.non_tbl_data
        self.agent_insight_context_manager.add_event(
            event_type="Non-tabular Data", 
            description="Stored non-tabular fields extracted by DI Multi-Modal Pipeline", 
            details={"fields": non_tabular_data}
        )
        return non_tabular_data
    
    def _add_facility_type_and_process_co2(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Facility Type column and process CO2 Supplementation data."""
        if 'Facility Type' not in df.columns:
            df['Facility Type'] = df['Invoice Number'].apply(self.get_facility_type)
            

        
        if 'CO2 Supplementation' in df.columns:
            df['CO2 Supplementation'] = df['CO2 Supplementation'].replace(',', '').astype(float)
        
        self.agent_insight_context_manager.add_event(
            "Facility Type and CO2 Processing",
            "Added Facility Type and processed CO2 Supplementation data",
            {"columns_added": ['Facility Type', 'CO2 Supplementation']}
        )
        
        return df
    
    def get_facility_type(self, invoice_reference):
            """
            Extracts the facility type from the invoice reference.

            Args:
                invoice_reference (str): The invoice reference string.

            Returns:
                str: The facility type.
            """
            parts = invoice_reference.split('-')
            if len(parts) >= 3:
                facility_type_abbr = parts[1]
                facility_name_mapping_str = self.di_utility.get_custom_config_value(CONFIG_FACILITY_NAME_MAPPING_KEY, "{}")
                
                # Replace single quotes with double quotes to make it valid JSON
                facility_name_mapping_str = facility_name_mapping_str.replace("'", '"')
                
                # Convert the string to a dictionary
                facility_name_mapping = json.loads(facility_name_mapping_str)
                
                # Get the facility type from the mapping
                facility_type = facility_name_mapping.get(f'INV-{facility_type_abbr}', 'Unknown')
                
                if facility_type == 'Unknown':
                    # Log an event if the facility type is unknown
                    self.agent_insight_context_manager.add_event(
                        "Unknown Facility Type", 
                        f"Encountered unknown facility type: INV-{facility_type_abbr}"
                    )
                
                return facility_type
            return 'Unknown'

   
    def _log_unknown_facility_type(self, facility_id: str):
        """
        Log an unknown facility type to the agent context.

        Args:
            facility_id (str): The facility ID that couldn't be mapped to a known type.
        """
        self.agent_insight_context_manager.add_event(
            "Unknown Facility Type",
            f"Encountered unknown Facility ID: {facility_id}",
            {"facility_id": facility_id}
        )

        # Add to a list of unknown facility IDs in the agent context
        unknown_facilities = self.agent_insight_context_manager.get_context('unknown_facilities', [])
        unknown_facilities.append(facility_id)
        self.agent_insight_context_manager.add_context('unknown_facilities', unknown_facilities)

 
    @ValidationAgentContextManager.track_method_execution(method_name="_extract_tables")
    def _extract_tables(self, raw_content_pages: List[RawDocumentContentAllOfRawContent]) -> Dict[str, Any]:
        extraction_result = self.table_extractor.extract_tables_from_pages(raw_content_pages)

        # Log event and update metrics for invoice details
        if 'invoice_details' in extraction_result and isinstance(extraction_result['invoice_details'], pd.DataFrame):
            invoice_details_df = extraction_result['invoice_details']
            self.agent_insight_context_manager.add_event(
                "Invoice Details Extraction Complete", 
                f"Completed invoice details extraction. DataFrame shape: {invoice_details_df.shape}, "
                f"Columns: {', '.join(invoice_details_df.columns.tolist())}"
            )

        # Log event and update metrics for summary
        if 'summary' in extraction_result and isinstance(extraction_result['summary'], pd.DataFrame):
            summary_df = extraction_result['summary']
            self.agent_insight_context_manager.add_event(
                "Summary Table Extraction Complete", 
                f"Completed summary table extraction. DataFrame shape: {summary_df.shape}, "
                f"Columns: {', '.join(summary_df.columns.tolist())}"
            )

        # Log overall metrics and update the agent context
        if 'metrics' in extraction_result:
            metrics = extraction_result['metrics']
            self.agent_insight_context_manager.add_event(
                "Table Extraction Complete",
                f"Completed table extraction. Metrics: {metrics}"
            )
            
            # Update the metrics in the agent context
            self.agent_insight_context_manager.update_metrics({"Metrics on Table Extracted": metrics})

        return extraction_result
    
    @ValidationAgentContextManager.track_method_execution(method_name="_calculate_co2_supplementation")
    def _calculate_co2_supplementation(self, df: pd.DataFrame, document_format: DocumentFormat) -> Dict[str, float]:
        self.agent_insight_context_manager.add_event("CO2 Supplementation Calculation Start", "Beginning calculation of CO2 supplementation")
        facility_type_mapping = self.di_utility.get_custom_config_value(CONFIG_FACILITY_NAME_MAPPING_KEY, {})
        greenhouse_prefix = next(k for k, v in facility_type_mapping.items() if v == 'Greenhouse Complexes')
        
        greenhouse_df = df[df['Invoice Reference'].str.startswith(greenhouse_prefix)]
        co2_supplementation = greenhouse_df.groupby('Facility ID')['CO2 Supplementation (kg)'].sum().to_dict()
        
        self.agent_insight_context_manager.add_event("CO2 Supplementation Calculation Complete", f"Calculated CO2 supplementation for {len(co2_supplementation)} greenhouse facilities")
        return co2_supplementation

    @ValidationAgentContextManager.track_method_execution(method_name="_apply_co2_policy")
    def _apply_co2_policy(self, co2_data: Dict[str, float], policy: Dict[str, Any]) -> Dict[str, float]:
        self.agent_insight_context_manager.add_event("CO2 Policy Application Start", "Beginning application of CO2 policy")
        adjustments = {}
        for facility, amount in co2_data.items():
            if amount > policy.get('threshold', float('inf')):
                adjustment = amount * policy.get('adjustment_rate', 0)
                adjustments[facility] = -adjustment  # NFAAtive adjustment (reduction in payment)
                self.agent_insight_context_manager.add_event(f"CO2 Adjustment for {facility}", f"Applied adjustment of {adjustment}")
        
        self.agent_insight_context_manager.add_event("CO2 Policy Application Complete", f"Applied CO2 policy adjustments to {len(adjustments)} facilities")
        return adjustments
    

 
    def _get_remittance_table_names(self) -> Dict[str, str]:
        """
        Get the configured names of the Invoice Details and Facility Type Subtotals tables
        using the generic document intelligence utilities.
        
        Returns:
            Dict[str, str]: Dictionary containing:
                - INVOICE_TABLE_KEY: Name of the invoice details table
                - SUBTOTALS_TABLE_KEY: Name of the facility type subtotals table
                
        Raises:
            ValueError: If either required table cannot be found in the schema
        """
        self.agent_insight_context_manager.add_event(
            "Remittance Table Names Retrieval",
            "Beginning identification of remittance table names"
        )
        
        try:
            tables_info = self.di_utility.get_table_info()
            invoice_table_name = None
            subtotals_table_name = None
            
            # Find the tables based on their characteristic columns
            for table in tables_info:
                columns = set(table['columns'])
                
                # Invoice table has unique columns like Invoice Number and CO2 Supplementation
                invoice_identifiers = {
                    COLUMN_INVOICE_NUMBER,
                    COLUMN_INVOICE_DATE,
                    COLUMN_CO2_SUPPLEMENTATION
                }
                
                if invoice_identifiers.issubset(columns):
                    invoice_table_name = table['name']
                    
                # Subtotals table has Subtotal Invoice Amount and Facility Type
                subtotals_identifiers = {
                    COLUMN_SUBTOTAL_INVOICE_AMOUNT,
                    COMPUTED_COLUMN_FACILITY_TYPE
                }
                
                if subtotals_identifiers.issubset(columns):
                    subtotals_table_name = table['name']
            
            if not invoice_table_name or not subtotals_table_name:
                error_msg = "Could not find both required tables in schema"
                self.logger.error(error_msg)
                self.agent_insight_context_manager.add_event(
                    "Remittance Table Names Error",
                    error_msg
                )
                raise ValueError(error_msg)
                
            self.logger.info(f"Successfully identified remittance tables: Invoice={invoice_table_name}, Subtotals={subtotals_table_name}")
            
            self.agent_insight_context_manager.add_event(
                "Remittance Table Names Retrieved",
                "Successfully identified remittance table names",
                {
                    "invoice_table": invoice_table_name,
                    "subtotals_table": subtotals_table_name
                }
            )
            
            return {
                INVOICE_TABLE_KEY: invoice_table_name,
                SUBTOTALS_TABLE_KEY: subtotals_table_name
            }
            
        except Exception as e:
            self.logger.error(f"Error identifying remittance tables: {str(e)}", exc_info=True)
            self.agent_insight_context_manager.add_event(
                "Remittance Table Names Error",
                f"Error occurred while identifying table names: {str(e)}"
            )
            raise
 
