from abc import ABC, abstractmethod

from sema4ai.di_client.document_intelligence_client.models.raw_document_content import RawDocumentContent
from sema4ai.di_client.document_intelligence_client.models.extracted_document_content import ExtractedDocumentContent
from sema4ai.di_client.document_intelligence_client.models.transformed_document_content import TransformedDocumentContent
from models.validate_models import ExtractionResult, TransformationResult, ValidationFinalResult


class DocumentProcessorBase(ABC):
    """
    Abstract Base Class for processing documents through three key phases: 
    1. Extracting and Structuring content.
    2. Processing and Enriching content for validation and downstream use.
    3. Validating and Finalizing the processed content for further operations.

    This base class ensures consistency across all document processors and provides
    a standardized flow for document processing. Every custom document processor 
    should implement the three abstract methods defined here.
    
    Typical Workflow:
    - Phase 1: Extract and structure content from raw documents (e.g., PDF invoices).
    - Phase 2: Transform and enrich structured content to prepare it for validation and 
      other downstream operations (e.g., adding totals or categorizing facilities).
    - Phase 3: Validate the processed content for completeness, correctness, and consistency.

    """

    @abstractmethod
    def extract_and_structure_content(
        self, content_to_process: RawDocumentContent
    ) -> ExtractionResult:
        """
        Extract and structure content from a raw document.

        This method processes raw input, such as scanned PDFs or digital documents,
        and structures the extracted content into a usable format. The output contains
        extracted fields, tables, and metadata required for further processing.

        Args:
            content_to_process (RawDocumentContent): 
                The raw document content to be extracted and structured. This could 
                include text, tables, and metadata from a digital or scanned source.

        Returns:
            ExtractedDocumentContent: 
                A structured representation of the document's content, including fields, 
                tables, and any metadata necessary for the next processing step.

        Example Use Case:
            - Extracting table data from remittance invoices and storing it in 
              structured formats like DataFrames or dictionaries for downstream processing.
        """
        pass

    @abstractmethod
    def transform_and_enrich_content(
        self, extracted_structured_data: ExtractedDocumentContent
    ) -> TransformationResult:
        """
        Process and enrich the structured content for validation and downstream use.

        This method applies necessary transformations and enrichments to the 
        extracted content. These could include operations like adding totals, 
        mapping fields to standard formats, and computing derived fields (e.g., 
        subtotal or CO2 adjustments).

        Args:
            extracted_structured_data (ExtractedDocumentContent): 
                The content extracted from the raw document, organized into structured fields
                and tables.

        Returns:
            TransformedDocumentContent: 
                The enriched content ready for validation and further use by downstream 
                agents or workflows.

        Example Use Case:
            - Adding a new column for 'Facility Type' to invoices and computing 
              group totals or subtotals for different facilities.
        """
        pass

    @abstractmethod
    def validate_and_finalize_content(
        self, transformed_doc: TransformedDocumentContent
    ) -> ValidationFinalResult:
        """
        Validate and finalize the processed content.

        This method ensures that the enriched and transformed content is correct, 
        complete, and consistent according to predefined rules (e.g., checking if 
        totals match across invoices). The output is a set of validation results 
        indicating whether the content is ready for downstream tasks.

        Args:
            transformed_doc (TransformedDocumentContent): 
                The transformed content that needs validation for correctness 
                and consistency.

        Returns:
            ValidationResults: 
                The results of the validation process, indicating success or any 
                errors or warnings that need resolution.

        Example Use Case:
            - Validating that the total payment amount matches the sum of 
              invoice amounts, fees, and discounts across all tables.
        """
        pass
