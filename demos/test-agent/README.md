# Sema4.ai Payment Remittance Reconciliation Agent

## Overview

This repository provides a reference implementation demonstrating how to build intelligent Worker Agents that leverage Sema4.ai's Document Intelligence (DI) Service platform. The Payment Remittance Reconciliation Agent showcases end-to-end document processing using DI's sophisticated Work Item architecture and content state management capabilities.

### The Evolution of Document Intelligence

Traditional document processing focuses on basic extraction and classification, but modern enterprises face challenges requiring a more sophisticated approach:

*   Processing thousands of varied document formats monthly
*   Complex validation and reconciliation requirements
*   Need for complete processing state management
*   Integration with multiple enterprise systems
*   Requirement for selective human engagement
*   Business user control over automation rules

This reference implementation demonstrates how Worker Agents address these challenges through:

1.  **Complete Document Lifecycle Management**: End-to-end processing from ingestion through reconciliation
2.  **State-Driven Processing**: Leveraging DI's content state management for reliable processing
3.  **Intelligent Work Management**: Using Work Items for process orchestration
4.  **Business User Control**: Enabling non-technical users to configure and manage automation

## Agent Processing Pipeline & Capabilities

The agent follows a comprehensive runbook defining its processing workflow across validation and reconciliation phases. This instruction manual ensures reliable, deterministic document processing while maintaining appropriate controls.

### Processing Philosophy

*   Strict sequential processing
*   Mandatory phase completion
*   Selective human engagement
*   Comprehensive audit trails

### Intelligent Work Management

The agent demonstrates enterprise-scale document processing by leveraging DI's Work Item architecture:

*   **Work Item Lifecycle**: Creation through completion tracking
*   **State Management**: Complex state transitions and updates
*   **Human Integration**: Seamless expertise integration

## Document Lifecycle & DI Service Integration

The agent demonstrates key DI Service integration points throughout the document lifecycle via the [Document Intelligence Client](https://pypi.org/project/sema4ai-di-client/). This client provides comprehensive document processing capabilities through its API.

### 1. Validation Phase

```python
@action
def run_remittance_validation(remittance_id: str) -> ActionResponse:
    """Document validation with DI Service integration."""
    di_client = create_di_client()
    
    # 1. Get initial work item
    work_item = di_client.get_document_work_item(remittance_id)
    
    # 2. Process through content states
    raw_content = di_client.get_document_content(
        remittance_id, 
        ContentState.RAW
    )
    
    # 3. Store extracted content after processing
    extracted_content = ExtractedDocumentContent(
        document_id=remittance_id,
        extracted_fields={...},
        extracted_tables={...}
    )
    di_client.store_extracted_content(extracted_content)
    
    # 4. Transform and store transformed content
    transformed_content = TransformedDocumentContent(
        document_id=remittance_id,
        transformed_data={...}
    )
    di_client.store_transformed_content(transformed_content)
    
    # 5. Update validation status
    validation_result = di_client.work_items_complete_stage(
        remittance_id,
        ProcessingStatus.VALIDATION_COMPLETED,
        validation_summary,
        detailed_report
    )
```

### 2. Reconciliation Phase

```python
@action
def store_and_analyze_payment(remittance_id: str) -> ActionResponse:
    """Payment reconciliation with DI Service integration."""
    di_client = create_di_client()
    
    # 1. Verify work item state
    work_item = di_client.get_document_work_item(remittance_id)
    if work_item.processing_status != ProcessingStatus.VALIDATION_COMPLETED:
        raise ValueError("Invalid work item state")
    
    # 2. Get computed content
    computed_content = di_client.get_document_content(
        remittance_id,
        ContentState.COMPUTED
    )
    
    # 3. Store computed reconciliation results
    computed_results = ComputedDocumentContent(
        document_id=remittance_id,
        computed_content={
            'reconciliation_results': reconciliation_data,
            'facility_analysis': facility_data,
            'discrepancy_details': discrepancy_data
        }
    )
    di_client.store_computed_content(computed_results)
    
    # 4. Perform reconciliation
    reconciliation_result = ledger_service.analyze_payment_reconciliation(
        payment_reference,
        threshold
    )
    
    # 5. Update final status
    status_result = di_client.work_items_complete_stage(
        remittance_id,
        final_status,
        reconciliation_summary,
        detailed_report
    )
```

### Error Handling & Recovery

```python
def handle_action_exception(
    remittance_id: str,
    e: Exception,
    context_manager: Optional[ContextManager] = None
) -> ActionResponse:
    """Enterprise-grade error handling with DI Service."""
    di_client = create_di_client()
    
    # Update work item to failure status
    di_client.work_items_complete_stage(
        remittance_id,
        "FAILURE",
        str(e),
        traceback.format_exc()
    )
    
    # Clean up any intermediate content states
    di_client.remove_document_content(
        remittance_id,
        ContentState.TRANSFORMED
    )
 
```

### Auxiliary DI Service Capabilities

The Document Intelligence Client provides additional utilities for document processing:

#### 1. Document Type Management

```python
def setup_document_processing(document_type_name: str, document_class: str):
    """Configure document processing parameters."""
    di_client = create_di_client()
    
    # Get document type configuration
    doc_type = di_client.get_document_type(document_type_name)
    if not doc_type:
        raise ValueError(f"Unknown document type: {document_type_name}")
        
    # Get specific format configuration
    doc_format = di_client.get_document_format(
        document_type_name,
        document_class
    )
    if not doc_format:
        raise ValueError(f"Unknown format {document_class} for type {document_type_name}")
    
    return doc_type, doc_format
```

#### 2. Content State Management

```python
def manage_content_states(remittance_id: str):
    """Manage document content through states."""
    di_client = create_di_client()
    
    # Get current content state
    content = di_client.get_document_content(
        remittance_id,
        current_state
    )
    
    # Remove outdated content
    if needs_cleanup:
        di_client.remove_document_content(
            remittance_id,
            outdated_state
        )
```

#### 3. Work Item Lifecycle Control

```python
def process_work_item(remittance_id: str):
    """Demonstrate work item lifecycle management."""
    di_client = create_di_client()
    
    # Get work item details
    work_item = di_client.get_document_work_item(remittance_id)
    
    # Update processing stage
    di_client.work_items_complete_stage(
        remittance_id,
        "SUCCESS",
        "Processing completed successfully",
        detailed_report
    )
```

These capabilities enable the agent to:

*   Configure document processing parameters
*   Manage content through its lifecycle
*   Control work item state transitions
*   Handle errors and recovery
*   Ensure data consistency

The DI Service Client provides the foundation for reliable, enterprise-scale document processing while maintaining strict control over document states and processing flows.

## Core Components

### 1. Document Processing

*   Multi-modal extraction pipeline
*   Format-specific field mapping
*   Comprehensive validation rules
*   Precise decimal handling

### 2. Business Logic

*   Multi-stage reconciliation
*   Facility-type analysis
*   Invoice-level matching
*   Discrepancy detection

### 3. Integration

*   Accounts receivable system integration
*   Payment system connectivity
*   Notification service integration
*   Audit trail generation

## Key Features

### 1. Precision Financial Processing

*   Exact decimal handling
*   Configurable tolerance thresholds
*   Multi-level validation
*   Comprehensive audit trails

### 2. Business User Controls

*   Visual document type configuration
*   Natural language runbook definition
*   Discrepancy threshold management
*   Processing rule customization

### 3. Enterprise Integration

*   Standard API interfaces
*   Secure data handling
*   Configurable connectors
*   Robust error handling

## Repository Structure

```
payment-remittance-reconcile-agent/
├── actions/
│   └── MyActions/
│       ├── payment-remittance-reconcile-action/    # Main reconciliation logic
│       │   ├── reconciliation_ledger/              # Core reconciliation engine
│       │   │   ├── db/                            # Database operations
│       │   │   ├── services/                      # Business services
│       │   │   └── test_generators/               # Test case generation
│       │   ├── context/                           # Context management
│       │   ├── models/                            # Data models
│       │   └── utils/                             # Utilities
│       │       ├── commons/                       # Common utilities
│       │       ├── context/                       # Context utilities  
│       │       └── logging/                       # Logging configuration
│       └── payment-remittance-validate-action/     # Validation processing
│           ├── validation/                         # Core validation logic
│           │   ├── validation_processor.py         # Main validation orchestration
│           │   └── validation_constants.py         # Validation rules & thresholds
│           ├── context/                            # Validation context management
│           │   └── validate_agent_context_manager.py  # Context tracking
│           ├── models/                             # Validation data models
│           │   └── validate_models.py              # Model definitions
│           └── utils/                              # Validation utilities
│               ├── commons/                        # Common utilities
│               ├── context/                        # Context utilities
│               ├── extraction/                     # Extraction helpers
│               ├── logging/                        # Logging utilities
│               └── validation/                     # Validation helpers
├── agent-spec.yaml                                # Agent specification
└── runbook.md                                     # Agent Instruction Manual
```

## Getting Started

### Prerequisites

*   Sema4.ai Studio
*   Sema4.ai DI Service installed and configured
*   Access to target systems (AR, payment processing)
*   Document type and format configurations

## Document Generation Test Framework

The testing framework provides comprehensive test case generation:

**Reconciling Cases**

*   Perfect matches between remittance and database
*   Validated totals and subtotals
*   Complete audit trail

**Single Facility Discrepancies**

*   Controlled 2% variance in specific facility types
*   Systematic discrepancy patterns
*   Verifiable reconciliation paths

**Multi-Facility Discrepancies**

*   Complex discrepancy patterns
*   Multiple facility type variations
*   Cross-facility validations

## Development Process

**Document Type Definition**

*   Field mappings
*   Table structures
*   Validation rules

**Agent Development**

*   Implement validation logic
*   Configure reconciliation rules
*   Set up integration points

**Testing**

*   Generate test cases
*   Validate processing
*   Verify integration