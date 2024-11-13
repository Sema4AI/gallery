import re
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional

# Import from sema4ai DI client models
from sema4ai.di_client.document_intelligence_client.models.doc_type import DocType
from sema4ai.di_client.document_intelligence_client.models.document_format import (
    DocumentFormat,
)

# Import from utils
from context.validate_agent_context_manager import ValidationAgentContextManager
from models.validate_models import ValidationResults, ValidationSeverity
from utils.extraction.common_validation_rules import (
    RULE_PREFIX_FOR_MISSING_REQUIRED_FIELD,
    RULE_PREFIX_FOR_INVALID_FIELD_FORMAT_FIELD,
)

# Set up logging
import logging


class FieldTypes:
    DATE_FIELDS = ["Payment Date", "Invoice Date"]
    MONETARY_FIELDS = [
        "Total Payment Amount",
        "Total Discounts Applied",
        "Total Payment Paid",
        "Total Additional Charges",
        "Invoice Amount",
        "Amount Paid",
        "Additional Charges",
        "Discounts Applied",
        "Total Invoice Amount",
    ]
    USAGE_FIELDS = ["Usage (kWh/Gallons)"]
    PERCENTAGE_FIELDS = ["Discount Rate"]


class DocumentIntelligenceUtility:
    """
    A utility class for working with DocumentType and DocumentFormat mappings and data processing.

    Terminology:
    - DocumentType (or Type): The standardized schema that defines the structure of the document data.
    - DocumentFormat (or Format): The specific format of a document, which may vary between different sources or systems.

    Mapping Directions:
    - Type to Format: Mapping from the standardized DocumentType fields to the specific DocumentFormat fields.
    - Format to Type: Mapping from the specific DocumentFormat fields to the standardized DocumentType fields.

    This utility provides methods for:
    1. Checking field mappings between DocumentType and DocumentFormat.
    2. Identifying mapped and unmapped fields.
    3. Mapping data between DocumentFormat and DocumentType.
    4. Extracting tables from raw document content.
    5. Accessing custom configuration.

    Note: This utility assumes that field names are unique across all tables and non-table fields within a DocumentType.
    When a method doesn't explicitly mention Type or Format in its name, it typically works with
    DocumentType as the base and checks for mappings to DocumentFormat.
    """

    def __init__(
        self,
        document_type: DocType,
        document_format: DocumentFormat,
        insight_tracker: ValidationAgentContextManager,
    ):
        """
        Initialize the DocumentIntelligenceUtility.

        Args:
            document_type (DocType): The standardized schema that defines the structure of the document data.
            document_format (DocumentFormat): The specific format of a document.
            insight_tracker (AgentInsightContextManager): The context manager for tracking insights and events.
        """
        self._document_type = document_type
        self._document_format = document_format
        self._logger = logging.getLogger(__name__)
        self.insight_tracker = insight_tracker

    def standardize_non_tabular_to_doc_type_schema(
        self, non_tabular_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        self.insight_tracker.add_event(
            "Non-tabular Schema Standardization Start",
            "Beginning standardization of non-tabular data to document type schema",
            {"non_tabular_fields": len(non_tabular_data)},
        )

        standardized_non_tabular = {}
        mapped_fields = []
        unmapped_fields = []

        # Note that the extacted fields are already mapped to the document type fields by the DI pipeline
        # So loooping thorugh to see if required fields are present in the data
        for field in self._document_type.non_tbl_fields:
            doc_type_field = field.name
            if doc_type_field in non_tabular_data:
                standardized_non_tabular[doc_type_field] = non_tabular_data[
                    doc_type_field
                ]
                mapped_fields.append(doc_type_field)
            else:
                unmapped_fields.append(doc_type_field)
                if field.requirement == "Required":
                    self.insight_tracker.add_warning(
                        f"Non-tabular Field Mapping Error. Required field '{doc_type_field}' not found in data"
                    )

        self.insight_tracker.add_event(
            "Non-tabular Field Mapping Summary",
            "Summary of non-tabular field mappings",
            {"mapped_fields": mapped_fields, "unmapped_fields": unmapped_fields},
        )

        return standardized_non_tabular

    def standardize_tabular_to_doc_type_schema(
        self, data: Dict[str, List[Dict[str, Any]]], table_name: str
    ) -> Dict[str, pd.DataFrame]:
        self._logger.info(
            "Starting standardization of tabular data to document type schema"
        )
        self.insight_tracker.add_event(
            "Tabular Schema Standardization Start",
            "Beginning standardization of tabular data to document type schema",
            {"tabular_tables": len(data)},
        )

        # Dynamically create the standardized tables dictionary
        standardized_tables = {}

        # Fetch field definitions for the specific table from the document schema
        tbl_fields_for_table = [
            field
            for field in self._document_type.tbl_fields
            if field.name == table_name
        ]

        # Handle each table (assuming there's one table per entry in the dictionary)
        for table_name, table_data in data.items():
            self._logger.info(f"Standardizing table: {table_name}")

            # Convert the table data into a DataFrame for easier manipulation
            df = pd.DataFrame(table_data)

            mapped_columns = []
            unmapped_columns = []
            column_mapping = {}

            # Dynamic field mapping with flexible handling like the original approach
            for col in df.columns:
                mapped_col = self.map_format_to_type_field(
                    col
                )  # Keep the dynamic approach here
                if mapped_col:
                    column_mapping[col] = mapped_col
                    mapped_columns.append(col)
                else:
                    unmapped_columns.append(col)

            # Apply the column mapping to the DataFrame
            standardized_df = df.rename(columns=column_mapping)

            # Preserve the 'Page' column from the raw data, if present
            if "Page" in df.columns:
                standardized_df["Page"] = df["Page"]

            # Convert the DataFrame back to a dictionary for further processing
            standardized_tables[table_name] = standardized_df.to_dict("records")

            # Log insight tracking for the column mapping
            self.insight_tracker.add_event(
                "Tabular Column Mapping Summary",
                f"Summary of tabular field mappings for table: {table_name}",
                {
                    "mapped_columns": mapped_columns,
                    "unmapped_columns": unmapped_columns,
                },
            )

        self._logger.info(
            "Completed standardization of tabular data to document type schema"
        )
        return standardized_tables

    def map_format_to_type_field(
        self, format_field: str, multiple_mappings: Dict[str, List[str]] = None
    ) -> Optional[str]:
        """
        Map a DocumentFormat field name to its corresponding DocumentType field name.
        This method checks both non-table fields and table fields for the mapping.

        Args:
            format_field (str): The name of the field in DocumentFormat.
            multiple_mappings (Dict[str, List[str]], optional): Custom multiple mappings configuration. Defaults to None.

        Returns:
            Optional[str]: The corresponding DocumentType field name, or None if not found.
        """
        # Check non-table fields mapping
        for field_mapping in self._document_format.non_tbl_fields_mapping:
            if field_mapping.field_identifier == format_field:
                return field_mapping.field_name

        # Check table fields mapping
        for table in self._document_format.tables:
            for field_mapping in table.tbl_fields_mapping:
                if field_mapping.output == format_field:
                    return field_mapping.source

        # Check custom multiple mappings if no source mapping found yet
        if multiple_mappings:
            mapped_field_doc_type = self.find_doc_type_mapped_to_multiple_formats(
                multiple_mappings, format_field
            )
            if mapped_field_doc_type:
                # Log that the format field mapping is found in the custom multiple mappings config
                self.insight_tracker.add_event(
                    "Field Mapping Found",
                    f"Field '{format_field}' has a custom multiple mappings config",
                    {
                        "format_field": format_field,
                        "type_field": mapped_field_doc_type,
                        "multiple_mappings_map": multiple_mappings,
                    },
                )
                return mapped_field_doc_type

        return None

    def find_doc_type_mapped_to_multiple_formats(
        self, mapping: Dict[str, List[str]], format_mapping: str
    ) -> Optional[str]:
        """
        Assume that a tabular column is defined in the document type and it is mapped to multiple columns in the document format.
        e.g: { "Facility ID": ["Unit ID", "System ID", "Facility"] }
        Given a column name from the document format, find the corresponding doc type column name .
        Since DI only supports one-to-one mapping, this method is used to find the doc type column name when there is a one-to-many mapping and
        advacned config map in document format is used to store the mapping.

        Args:
            mapping (Dict[str, List[str]]): The dictionary containing lists of strings.
            format_mapping (str): The value to search for in the lists.

        Returns:
            Optional[str]: The key corresponding to the list containing the format_mapping value, or None if not found.
        """
        for key, values in mapping.items():
            if format_mapping in values:
                return key
        return None

    def validate_and_clean_tabular(
        self,
        data: List[Dict[str, Any]],
        table_type: str,
        exclude_field_validate_list: List[str] = [],
    ) -> Tuple[pd.DataFrame, ValidationResults]:
        self._logger.info(f"Starting Validate and Clean for tabular data: {table_type}")
        self.insight_tracker.add_event(
            f"{table_type} Validation Start",
            f"Beginning validation and cleaning of {table_type} data",
        )

        validation_results = ValidationResults()
        df = pd.DataFrame(data)

        # Log the columns present in the DataFrame
        self._logger.info(
            f"Columns present in {table_type} data: {df.columns.tolist()}"
        )

        table_fields_for_type = [
            field
            for field in self._document_type.tbl_fields
            if field.name == table_type
        ]

        for doc_type_field in table_fields_for_type:
            for column in doc_type_field.table_definition:
                field_name = column.column
                if field_name in exclude_field_validate_list:
                    self.insight_tracker.add_event(
                        "Field Validation Skip",
                        f"Skipping validation for field: {field_name}",
                    )
                    continue

                if field_name not in df.columns:
                    if column.requirement == "Required":
                        error_message = f"Required field '{field_name}' is missing"
                        self._logger.error(error_message)
                        validation_results.add_result(
                            rule_id=f"{RULE_PREFIX_FOR_MISSING_REQUIRED_FIELD}{field_name.upper().replace(' ', '_')}",
                            passed=False,
                            message=error_message,
                            severity=ValidationSeverity.ERROR,
                            details={
                                "field_name": field_name,
                                "table_type": table_type,
                            },
                        )
                        self.insight_tracker.add_event(
                            "Missing Required Field",
                            error_message,
                            {"table_type": table_type, "field_name": field_name},
                        )
                else:
                    df = self.convert_field_based_on_type(
                        df, field_name, field_name, validation_results, table_type
                    )

        # Validate that all required fields are present
        required_fields = [
            column.column
            for doc_type_field in table_fields_for_type
            for column in doc_type_field.table_definition
            if doc_type_field.name == table_type
            if column.requirement == "Required"
            and column.column not in exclude_field_validate_list
        ]
        missing_required_fields = set(required_fields) - set(df.columns)
        for missing_field in missing_required_fields:
            error_message = f"Required field '{missing_field}' is missing"
            self._logger.error(error_message)
            validation_results.add_result(
                rule_id=f"{RULE_PREFIX_FOR_MISSING_REQUIRED_FIELD}{missing_field.upper().replace(' ', '_')}",
                passed=False,
                message=error_message,
                severity=ValidationSeverity.ERROR,
                details={"field_name": missing_field, "table_type": table_type},
            )
            self.insight_tracker.add_event(
                "Missing Required Field",
                error_message,
                {"table_type": table_type, "field_name": missing_field},
            )

        self.insight_tracker.add_event(
            f"{table_type} Validation Complete",
            f"Completed validation and cleaning of {table_type} data",
            {
                "total_fields": len(df.columns),
                "rules_passed": validation_results.rules_passed,
                "rules_failed": validation_results.rules_failed,
            },
        )
        self._logger.info(
            f"Completed Validate and Clean for tabular data: {table_type}"
        )
        return df, validation_results

    def validate_and_clean_non_tabular(
        self, data: Dict[str, Any], exclude_field_validate_list: List[str] = []
    ) -> Tuple[Dict[str, Any], ValidationResults]:
        self._logger.info("Starting Validate and Clean for non-tabular data")
        self.insight_tracker.add_event(
            "Non-tabular Validation Start",
            "Beginning validation and cleaning of non-tabular data",
        )

        validation_results = ValidationResults()
        cleaned_data = {}

        for field_name, value in data.items():
            if field_name in exclude_field_validate_list:
                self.insight_tracker.add_event(
                    "Field Validation Skip",
                    f"Skipping validation for field: {field_name}",
                )
                cleaned_data[field_name] = value
                continue

            doc_type_field = self._get_doc_type_field(field_name)
            if not doc_type_field:
                self._logger.warning(f"No document type field found for: {field_name}")
                continue

            if doc_type_field.requirement == "Required" and (
                value is None or value == ""
            ):
                validation_results.add_result(
                    rule_id=f"MISSING_REQUIRED_FIELD_{field_name.upper().replace(' ', '_')}",
                    passed=False,
                    message=f"Required field '{field_name}' is missing or empty",
                    severity=ValidationSeverity.ERROR,
                    details={"field": field_name},
                )
            else:
                cleaned_value = self.convert_single_field(
                    value, field_name, validation_results
                )
                cleaned_data[field_name] = cleaned_value

        self.insight_tracker.add_event(
            "Non-tabular Validation Complete",
            "Completed validation and cleaning of non-tabular data",
            {
                "total_fields": len(data),
                "cleaned_fields": len(cleaned_data),
                "validation_issues": validation_results.rules_failed,
            },
        )
        self._logger.info("Completed Validate and Clean for non-tabular data")
        return cleaned_data, validation_results

    def _get_doc_type_field(self, field_name: str) -> Any:
        """Get the document type field definition for a given field name."""
        for field in self._document_type.non_tbl_fields:
            if field.name == field_name:
                return field
        return None

    def convert_field_based_on_type(
        self,
        df: pd.DataFrame,
        format_field: str,
        field_name: str,
        validation_results: ValidationResults,
        table_type: str,
    ) -> pd.DataFrame:
        try:
            original_values = df[format_field].copy()
            self._logger.info(
                f"Field Conversion Start, Converting field: '{format_field}' (mapped to '{field_name}')"
            )

            def convert_value(value):
                try:
                    if field_name in FieldTypes.MONETARY_FIELDS:
                        if isinstance(value, str):
                            value = re.sub(r"[\$,]", "", value)
                        return float(value)
                    elif field_name in FieldTypes.DATE_FIELDS:
                        return pd.to_datetime(value, errors="coerce").date()
                    elif field_name in FieldTypes.USAGE_FIELDS:
                        if isinstance(value, str):
                            value_match = re.search(r"(\d+(?:,\d+)?)", value)
                            unit_match = re.search(r"(kWh|Gallons)", value)
                            if value_match and unit_match:
                                numeric_value = float(
                                    value_match.group(1).replace(",", "")
                                )
                                unit = unit_match.group(1)
                                return f"{numeric_value} {unit}"
                        return value
                    elif field_name in FieldTypes.PERCENTAGE_FIELDS:
                        if isinstance(value, str):
                            value = value.rstrip("%")
                        return float(value) / 100
                    else:
                        return value
                except Exception:
                    return pd.NA

            df[format_field] = df[format_field].apply(convert_value)

            # Log conversions and errors, including page numbers
            changes = (original_values != df[format_field]) & (
                ~original_values.isna() | ~df[format_field].isna()
            )
            if changes.any():
                change_details = (
                    df[changes]
                    .groupby("Page")
                    .apply(lambda x: x.index.tolist())
                    .to_dict()
                )
                # self.insight_tracker.add_event("Field Conversion",
                #                             f"Converted field: '{format_field}' (mapped to '{field_name}')",
                #                             {"table_type": table_type, "changes_by_page": change_details})

            # Check for and log conversion errors
            errors = df[format_field].isna() & ~original_values.isna()
            if errors.any():
                error_details = (
                    df[errors]
                    .groupby("Page")
                    .apply(lambda x: x.index.tolist())
                    .to_dict()
                )
                for page, row_indices in error_details.items():
                    error_samples = original_values.loc[row_indices].head().tolist()
                    validation_results.add_result(
                        rule_id=f"{RULE_PREFIX_FOR_INVALID_FIELD_FORMAT_FIELD}{field_name.upper().replace(' ', '_')}",
                        passed=False,
                        message=f"Invalid format for {table_type} Column '{format_field}' (mapped to '{field_name}') on page {page}",
                        severity=ValidationSeverity.ERROR,
                        details={
                            "format_field": format_field,
                            "mapped_field": field_name,
                            "table_type": table_type,
                            "page": page,
                            "affected_rows": row_indices,
                            "error_samples": error_samples,
                        },
                    )
                self.insight_tracker.add_event(
                    "Field Conversion Error",
                    f"Error converting field: '{format_field}' (mapped to '{field_name}')",
                    {"table_type": table_type, "errors_by_page": error_details},
                )

        except Exception as e:
            self._logger.error(
                f"Error in convert_field_based_on_type: {str(e)}", exc_info=True
            )
            validation_results.add_result(
                rule_id=f"{RULE_PREFIX_FOR_INVALID_FIELD_FORMAT_FIELD}{field_name.upper().replace(' ', '_')}",
                passed=False,
                message=f"Error processing {table_type} Column '{format_field}' (mapped to '{field_name}'): {str(e)}",
                severity=ValidationSeverity.ERROR,
                details={
                    "format_field": format_field,
                    "mapped_field": field_name,
                    "table_type": table_type,
                    "error": str(e),
                },
            )
            self.insight_tracker.add_event(
                "Field Conversion Error",
                f"Error processing field: '{format_field}' (mapped to '{field_name}')",
                {
                    "table_type": table_type,
                    "format_field": format_field,
                    "mapped_field": field_name,
                    "error": str(e),
                },
            )

        return df

    def convert_single_field(
        self, value: Any, field_name: str, validation_results: ValidationResults
    ) -> Any:
        try:
            original_value = value
            if field_name in FieldTypes.MONETARY_FIELDS:
                if isinstance(value, str):
                    # Use regex to remove $ and , similar to the DataFrame version
                    value = re.sub(r"[\$,]", "", value)
                value = float(value)
            elif field_name in FieldTypes.DATE_FIELDS:
                value = pd.to_datetime(value, errors="coerce").date()
            elif field_name in FieldTypes.USAGE_FIELDS:
                if isinstance(value, str):
                    value_match = re.search(r"(\d+(?:,\d+)?)", value)
                    unit_match = re.search(r"(kWh|Gallons)", value)
                    if value_match and unit_match:
                        numeric_value = float(value_match.group(1).replace(",", ""))
                        unit = unit_match.group(1)
                        value = f"{numeric_value} {unit}"
                    else:
                        # If the format doesn't match, keep the original value
                        pass
            elif field_name in FieldTypes.PERCENTAGE_FIELDS:
                if isinstance(value, str):
                    value = value.rstrip("%")
                value = float(value) / 100

            # if value != original_value:
            #     self.insight_tracker.add_event("Field Conversion",
            #                                 f"Converted field: {field_name}",
            #                                 {"original_value": original_value, "converted_value": value})
            return value
        except Exception as e:
            validation_results.add_result(
                rule_id=f"{RULE_PREFIX_FOR_INVALID_FIELD_FORMAT_FIELD}{field_name.upper().replace(' ', '_')}",
                passed=False,
                message=f"Invalid format for Non-Tabular Field: '{field_name}': {str(e)}",
                severity=ValidationSeverity.ERROR,
                details={"field": field_name, "value": value, "error": str(e)},
            )
            self.insight_tracker.add_event(
                "Field Conversion Error",
                f"Error converting field: {field_name}",
                {"field": field_name, "value": value, "error": str(e)},
            )
            return value

    def has_field_mapping(self, field_name: str) -> bool:
        """
        Check if a field has a mapping between DocumentType and DocumentFormat.

        This method checks both non-table fields and table fields for a mapping.

        Args:
            field_name (str): The name of the field in DocumentType to check.

        Returns:
            bool: True if the DocumentType field has a mapping to a DocumentFormat field, False otherwise.
        """
        self.insight_tracker.add_event(
            "Field Mapping Check", f"Checking mapping for field: {field_name}"
        )

        # Check non-table fields
        for field_mapping in self._document_format.non_tbl_fields_mapping:
            if field_mapping.field_name == field_name:
                self._logger.debug(f"Field '{field_name}' has a non-table mapping")
                self.insight_tracker.add_event(
                    "Field Mapping Found",
                    f"Field '{field_name}' has a non-table mapping",
                )
                return True

        # Check table fields
        for table in self._document_format.tables:
            for field_mapping in table.tbl_fields_mapping:
                if field_mapping.source == field_name:
                    if field_mapping.output:  # Check if the output is not empty
                        self._logger.debug(f"Field '{field_name}' has a table mapping")
                        self.insight_tracker.add_event(
                            "Field Mapping Found",
                            f"Field '{field_name}' has a table mapping",
                        )
                        return True
                    else:
                        self.insight_tracker.add_warning(
                            f"Field '{field_name}' has an empty output mapping"
                        )

        self.insight_tracker.add_event(
            "Field Mapping Not Found", f"Field '{field_name}' has no mapping"
        )
        return False

    def is_field_required(self, field_name: str) -> bool:
        """
        Check if a field (either non-table or table) is configured to be required.

        Args:
            field_name (str): The name of the field to check.

        Returns:
            bool: True if the field is required, False otherwise.
        """
        self.insight_tracker.add_event(
            "Field Requirement Check", f"Checking if field '{field_name}' is required"
        )

        # Check non-table fields
        for field in self._document_type.non_tbl_fields:
            if field.name == field_name:
                is_required = field.requirement == "Required"
                self.insight_tracker.add_event(
                    "Field Requirement Result",
                    f"Non-table field '{field_name}' is {'required' if is_required else 'not required'}",
                )
                return is_required

        # Check table fields
        for table in self._document_type.tbl_fields:
            for field in table.table_definition:
                if field.column == field_name:
                    is_required = field.requirement == "Required"
                    self.insight_tracker.add_event(
                        "Field Requirement Result",
                        f"Table field '{field_name}' is {'required' if is_required else 'not required'}",
                    )
                    return is_required

        self.insight_tracker.add_warning(
            f"Field '{field_name}' not found in DocumentType"
        )
        return False

    def get_unmapped_fields(self) -> Tuple[List[str], List[str]]:
        """
        Get all DocumentType fields that do not have a mapping to DocumentFormat fields.

        This method checks both non-table fields and table fields for mappings.

        Returns:
            Tuple[List[str], List[str]]: A tuple containing:
                - A list of unmapped non-table DocumentType fields
                - A list of unmapped table DocumentType fields
        """
        unmapped_non_table = [
            field.name
            for field in self._document_type.non_tbl_fields
            if not self.has_field_mapping(field.name)
        ]

        unmapped_table = []
        for table in self._document_type.tbl_fields:
            unmapped_table.extend(
                [
                    field.column
                    for field in table.table_definition
                    if not self.has_field_mapping(field.column)
                ]
            )

        return unmapped_non_table, unmapped_table

    @ValidationAgentContextManager.track_method_execution(
        method_name="get_mapped_fields"
    )
    def get_mapped_fields(self) -> Tuple[List[str], List[str]]:
        """
        Get all DocumentType fields that have a mapping to DocumentFormat fields.

        This method checks both non-table fields and table fields for mappings.

        Returns:
            Tuple[List[str], List[str]]: A tuple containing:
                - A list of mapped non-table DocumentType fields
                - A list of mapped table DocumentType fields
        """
        mapped_non_table = [
            field.name
            for field in self._document_type.non_tbl_fields
            if self.has_field_mapping(field.name)
        ]

        mapped_table = []
        for table in self._document_type.tbl_fields:
            mapped_table.extend(
                [
                    field.column
                    for field in table.table_definition
                    if self.has_field_mapping(field.column)
                ]
            )

        return mapped_non_table, mapped_table

    def map_type_to_format_field(self, type_field: str) -> Optional[str]:
        """
        Map a field from the document type to its corresponding field in the document format.

        Args:
            type_field (str): The field name in the document type.

        Returns:
            Optional[str]: The corresponding field name in the document format, or None if not found.
        """
        try:
            # Check non-tabular fields
            for mapping in self._document_format.non_tbl_fields_mapping:
                if mapping.field_name == type_field:
                    # self.insight_tracker.add_event(
                    #     "Field Mapping Success",
                    #     f"Mapped non-tabular field: {type_field} to {mapping.field_identifier}",
                    #     {"type_field": type_field, "format_field": mapping.field_identifier}
                    # )
                    return mapping.field_identifier

            # Check tabular fields
            for table in self._document_format.tables:
                for mapping in table.tbl_fields_mapping:
                    # if mapping.source == type_field:
                    #     self.insight_tracker.add_event(
                    #         "Field Mapping Success",
                    #         f"Mapped tabular field: {type_field} to {mapping.output}",
                    #         {"type_field": type_field, "format_field": mapping.output}
                    #     )
                    return mapping.output

            # If no mapping found, log a warning and return None
            self.insight_tracker.add_event(
                "Field Mapping Warning",
                f"No mapping found for field: {type_field}",
                {"field": type_field},
            )
            return None

        except Exception as e:
            self.insight_tracker.add_event(
                "Field Mapping Error",
                f"Error occurred while mapping field: {type_field}",
                {"field": type_field, "error": str(e)},
            )
            self._logger.error(
                f"Error in map_type_to_format_field: {str(e)}", exc_info=True
            )
            return None

    def get_table_info(self) -> List[Dict[str, Any]]:
        """
        Get detailed information about all tables defined in the document type schema.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing table information with keys:
                - name: The name of the table
                - description: The table's description
                - field_count: Number of fields in the table
                - required_fields: Number of required fields
                - columns: List of all column names
                - required_columns: List of required column names
                - optional_columns: List of optional column names
        """
        self.insight_tracker.add_event(
            "Table Info Retrieval",
            "Retrieving detailed table information from document type schema",
        )

        try:
            table_info = []
            for table in self._document_type.tbl_fields:
                columns = [field.column for field in table.table_definition]
                required_columns = [
                    field.column
                    for field in table.table_definition
                    if field.requirement == "Required"
                ]
                optional_columns = [
                    field.column
                    for field in table.table_definition
                    if field.requirement == "Optional"
                ]

                info = {
                    "name": table.name,
                    "description": table.description,
                    "field_count": len(table.table_definition),
                    "required_fields": len(required_columns),
                    "columns": columns,
                    "required_columns": required_columns,
                    "optional_columns": optional_columns,
                }
                table_info.append(info)

                # Log detailed information about each table
                self.insight_tracker.add_event(
                    "Table Details Retrieved",
                    f"Retrieved information for table: {table.name}",
                    {
                        "table_name": table.name,
                        "total_columns": len(columns),
                        "required_columns": len(required_columns),
                        "optional_columns": len(optional_columns),
                    },
                )

            self.insight_tracker.add_event(
                "Table Info Retrieved",
                f"Found detailed information for {len(table_info)} tables",
                {"tables": [info["name"] for info in table_info]},
            )

            return table_info

        except Exception as e:
            self._logger.error(f"Error retrieving table info: {str(e)}", exc_info=True)
            self.insight_tracker.add_event(
                "Table Info Retrieval Error",
                f"Error occurred while retrieving table information: {str(e)}",
            )
            return []

    def get_table_columns(self, table_name: str) -> Dict[str, List[str]]:
        """
        Get all column names for a specific table.

        Args:
            table_name (str): The name of the table to get columns for

        Returns:
            Dict[str, List[str]]: A dictionary containing:
                - all_columns: List of all column names
                - required_columns: List of required column names
                - optional_columns: List of optional column names

        Raises:
            ValueError: If the specified table name is not found in the schema
        """
        self.insight_tracker.add_event(
            "Table Columns Retrieval", f"Retrieving columns for table: {table_name}"
        )

        try:
            # Find the specified table
            table = next(
                (
                    table
                    for table in self._document_type.tbl_fields
                    if table.name == table_name
                ),
                None,
            )

            if table is None:
                error_msg = f"Table '{table_name}' not found in schema"
                self._logger.error(error_msg)
                self.insight_tracker.add_event(
                    "Table Columns Retrieval Error", error_msg
                )
                raise ValueError(error_msg)

            # Get column lists
            all_columns = [field.column for field in table.table_definition]
            required_columns = [
                field.column
                for field in table.table_definition
                if field.requirement == "Required"
            ]
            optional_columns = [
                field.column
                for field in table.table_definition
                if field.requirement == "Optional"
            ]

            result = {
                "all_columns": all_columns,
                "required_columns": required_columns,
                "optional_columns": optional_columns,
            }

            self.insight_tracker.add_event(
                "Table Columns Retrieved",
                f"Successfully retrieved columns for table: {table_name}",
                {
                    "table_name": table_name,
                    "total_columns": len(all_columns),
                    "required_columns": len(required_columns),
                    "optional_columns": len(optional_columns),
                },
            )

            return result

        except Exception as e:
            self._logger.error(
                f"Error retrieving table columns: {str(e)}", exc_info=True
            )
            self.insight_tracker.add_event(
                "Table Columns Retrieval Error",
                f"Error occurred while retrieving table columns: {str(e)}",
            )
            raise

    def get_custom_config(self) -> Dict[str, Any]:
        """
        Get the custom configuration of the DocumentFormat.

        Returns:
            Dict[str, Any]: The custom configuration dictionary.
        """
        return self._document_format.custom_config

    def get_custom_config_value(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Get a value from the custom configuration using the provided key.

        Args:
            key (str): The key to look up in the custom configuration.
            default (Optional[Any]): The default value to return if the key is not found. Defaults to None.

        Returns:
            Any: The value associated with the key in the custom configuration, or the default value if the key is not found.
        """

        custom_config = self._document_format.custom_config
        value = custom_config.get(key, default)

        if value is None:
            self.insight_tracker.add_warning(
                f"No value found for custom config key '{key}', using default"
            )

        return value

    def _get_mapping_summary(self, row: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Generate a summary of field mappings for a table row.

        Args:
            row (Dict[str, Any]): A dictionary representing a single row of the standardized table.

        Returns:
            Dict[str, List[str]]: A dictionary with 'mapped_columns' and 'unmapped_columns' lists.
        """
        mapped_columns = []
        unmapped_columns = []

        for field_name in row.keys():
            mapped_field = self.map_type_to_format_field(field_name)
            if mapped_field:
                mapped_columns.append(f"{field_name} -> {mapped_field}")
            else:
                unmapped_columns.append(field_name)

        return {"mapped_columns": mapped_columns, "unmapped_columns": unmapped_columns}
