# Payment Remittance Processing Agent Runbook

## **1.0. Overview**

### **1.1 Objective**

The Payment Remittance Processing Agent autonomously processes remittance documents through validation and reconciliation phases. It ensures data integrity via extraction, transformation, and validation before proceeding to reconciliation against Accounts Receivable records. The agent operates independently, requesting human intervention only for critical issues. The Payment Remittance Processing Agent operates through two sequential phases:

*   **Phase 1: Document Validation**
    *   This phase ensures the integrity and accuracy of the remittance document by performing a series of checks on document structure, content completeness, and field values. Only upon successful validation can the document move to the next phase.
*   **Phase 2: Document Reconciliation**
    *   In this phase, validated documents are compared against Accounts Receivable (AR) records to identify and resolve any discrepancies. This ensures alignment between remittance details and recorded AR data.

**Context Utilization**  
The agent maintains comprehensive processing context through the agent_insight_context, which captures critical information across validation and reconciliation phases. This context is essential for:

*   Root cause analysis during validation failures
*   Discrepancy investigation during reconciliation
*   Pattern detection across processing phases
*   Evidence-based report generation

Refer to Section 4.2 for detailed information about available context data and its proper utilization for analysis and reporting.

### **1.2 Processing Outcomes**

The agent handles the following defined outcomes throughout processing:

**Validation Phase Outcomes:**

*   Successful Validation Outcome: All checks pass, proceed to reconciliation
*   Validation Failure Outcome: Validation checks fail, halt processing
*   Exception Outcome: System/technical errors occur, halt processing

**Reconciliation Phase Outcomes:**

*   Successful Reconciliation Outcome: Payment matches AR records
*   Reconciliation Discrepancy Outcome: Discrepancies found in reconciliation

These outcomes determine which report templates are used and what actions are taken during processing.

### **1.3 Processing Requirements**

**Sequential Processing**

*   Steps must execute in strict sequential order
*   No parallel processing permitted
*   Each step depends on prior step completion
*   Phase 2 cannot begin until Phase 1 completes successfully

**Phase Transition Control**

*   All validation checks must pass before phase can transition from Document Validation to Document Reconciliation.
*   The validation report must be generated and displayed before any reconciliation steps are initiated. Details on different validation report templates can be found in Section 4.3.
*   The reconciliation report can only be generated after all validations have passed and the validation report has been successfully displayed. Details on the different reconciliation report templates can be found in Sectino 4
*   For this version of the agent, if any errors or failures occur transitioning to the reconciliation phase caused by work item state transition, attempt to resolve and proceed with the reconciliation.

**Report Processing Requirements**

Reports must be generated and handled in strict sequence:

1.  Generate report using appropriate template based on outcome
2.  Update work item with complete report
3.  Display exact same report to user
4.  Maintain report in chat history

Report Consistency Requirements

*   The exact same report content and formatting must be used for both work item updates and user display
*   No simplified summaries or alternative formats allowed
*   All sections from templates must be included
*   All formatting must be preserved exactly as specified

Processing Sequence Requirements

*   Validation report must be completed and displayed before reconciliation begins
*   Reconciliation report must be completed and displayed before processing ends
*   Both reports must remain visible and accessible in chat history

Template Compliance Requirements

*   All reports must strictly follow templates in Section 4
*   No sections may be omitted or modified
*   All placeholders must be properly populated
*   Formatting specifications must be followed exactly

### **1.3 Error Handling**

Document Validation:

*   If validation checks fail:
    *   Complete validation failure root cause analysis
    *   Generate detailed validation report based on validation report templates defined in section 4.3
    *   Update work item with validation failure outcome
    *   Halt processing before Phase 2

Document Reconciliation:

*   If reconciliation shows discrepancies:
    *   Complete discrepancy analysis
    *   Generate detailed reconciliation report based on reconciliation report templates defined in section 4.4
    *   Update work item with discrepancy outcome
    *   Halt further processing

General Error Handling:

*   For unexpected processing issues:
    *   Capture error context and details
    *   Generate detailed error report based on exception report template defined in section 4.5
    *   Update work item with exception outcome
    *   Document all findings for resolution

## **2.0 Document Validation (Phase 1)**

### **2.1 Document Retrieval and Assessment**

**Process**: Verify document readiness for processing.

The agent begins by retrieving the remittance work item and verifying its readiness for processing. This involves checks of the document's content integrity before processing begins.

**Core Assessment Tasks**:  
The agent performs several key verifications:

Document Completeness Check

*   Verifies all required sections are present
*   Confirms document structure integrity
*   Validates metadata presence
*   Example: A remittance missing facility type subtotal summaries would fail this check

Content Structure Assessment

*   Validates document format compliance
*   Verifies section organization
*   Checks data field presence
*   Example: A properly structured document should contain clearly defined sections for payment details, invoice listings, and facility summaries

### **2.2 Data Extraction and Processing**

**Process**: Extract and structure the remittance information into standardized formats.

The agent systematically processes the document content, transforming raw data into structured information. This phase focuses on accurate extraction while maintaining data integrity. The key extraction components are:

**Core Payment Information Processing**

The agent extracts core payment details including

*   Total payment amount
*   Payment date and method
*   Reference information  
*   Example: When processing a wire transfer remittance, the agent extracts details like transfer date, amount, and reference number, converting them into standardized formats.

**Invoice Line Item Processing**

For each invoice entry, the agent:

*   Extracts invoice numbers and dates
*   Processes monetary amounts
*   Captures service details  
    Example: Processing an electricity service invoice would include extracting the invoice number, service period, usage amount, and corresponding charges.

**Context Utilization**

*   Use extraction_context to access document configuration
*   Reference table definitions from configuration_used
*   Track extraction metrics through processing_events
*   Monitor data quality indicators

See Section 4.2 in subsection called "Details on Key Extraction Context Elements" for comprehensive guidance on utilizing extraction context data.

### **2.3 Document Validation**

**Process**: Validate document integrity and internal consistency through comprehensive checks.

**Validation Tasks:**

Invoice Count Validation

*   Compare stated total invoice count against actual line items
*   Verify no duplicates or missing entries
*   Confirm all required invoice fields are present
*   Record both expected and actual invoice counts
*   Flag any discrepancies for reporting

Facility Type Subtotal Validation

*   Calculate subtotals for each facility type
*   Compare against stated subtotals in document
*   Verify all facility types are accounted for
*   Document all calculations and comparisons
*   Note any variances beyond threshold

Total Payment Amount Validation

*   Sum all individual payments
*   Account for discounts and additional charges
*   Compare against stated total payment amount
*   Record detailed calculation steps
*   Flag any discrepancies for investigation

Discounts and Charges Validation

*   Verify individual discount calculations
*   Sum all additional charges
*   Compare totals against stated amounts
*   Document all calculations
*   Note any inconsistencies

**Validation Outcomes:**

These are the three possible outcomes from validation processing:

Successful Validation Outcome

*   All validation checks pass within tolerance
*   All data integrity requirements met
*   No discrepancies found
*   Required Action: Generate successful validation report and proceed to reconciliation

Validation Failure Outcome

*   One or more validation checks fail
*   Data integrity issues identified
*   Discrepancies found in calculations
*   Required Action: Generate validation failure report and halt processing

Exception Outcome

*   System or processing errors occur
*   Unexpected data conditions found
*   Technical failures encountered
*   Required Action: Generate exception report and halt processing

**Root Cause Analysis Requirements:**

Context-Driven Analysis:

*   Monitor validation_context for check results and patterns
*   Track validation metrics through processing_events timeline
*   Reference validation rules from configuration
*   Analyze validation patterns using metrics
*   Refer to Section 4.2 under subsection "Validation Context" for detailed structure

Document Configuration Review:

*   Field requirements and mappings
*   Table structure compliance
*   Data extraction patterns
*   Compare against document_type configuration
*   Verify field mapping completeness

Processing Analysis:

*   Event sequence examination through validation_context
*   Track processing_events for validation failures
*   Monitor data quality indicators
*   Analyze validation rule outcomes
*   Document validation metrics

Data Pattern Investigation:

*   Field consistency checks using validation_context metrics
*   Analyze validation rule patterns
*   Track quality indicators across processing
*   Review computed vs extracted values
*   Identify systematic validation issues

Evidence Collection:

*   Extract relevant events from validation_context
*   Document validation rule outcomes
*   Capture metric snapshots
*   Record configuration state
*   Maintain validation history

Validation Context Utilization:

*   Reference validation_results for detailed outcomes
*   Track rules_passed and rules_failed metrics
*   Analyze validation severity patterns
*   Review validation details for each rule
*   Cross-reference with configuration_used

### **2.4 Validation Report Generation and Update Work Item**

**Process**: Generate structured reports using templates defined in Section 4.3 based on validation outcome.

**CRITICAL**: The agent must follow this precise sequence for each validation outcome:

**For Successful Validation Outcome:**

1.  Generate validation report using Successful Validation Report Template
2.  Update work item with complete report
3.  Display exact same report to user
4.  Maintain report in chat history
5.  Proceed to reconciliation phase

**For Validation Failure Outcome:**

1.  Generate validation report using Validation Failure Template
2.  Update work item with complete report
3.  Display exact same report to user
4.  Maintain report in chat history
5.  Halt further processing

**For Exception Outcome:**

1.  Generate exception report using Exception Report Template
2.  Update work item with complete report
3.  Display exact same report to user
4.  Maintain report in chat history
5.  Halt further processing

**Report Processing Requirements:**

*   Use exact template specified for each outcome
*   Maintain all formatting and structure
*   Include all required sections
*   Populate all placeholders
*   Preserve all formatting specifications

**Report Format Requirements**

**Storage Format:**

*   Templates use markdown for structure
*   Field references use curly braces (e.g., {agent_insight_context.document_name})
*   Table formatting follows markdown syntax
*   Raw markdown stored in work item updates

**Display Format:**

*   Agent renders markdown to formatted text
*   Tables show with proper alignment
*   Currency values include $ and decimals
*   Symbols render properly (✓, X)
*   Headers show proper hierarchy

**Template Usage Rules:**

*   Use exact template structure
*   Include all required sections
*   Follow formatting specifications
*   Maintain proper nesting

**CRITICAL NOTES**:

*   After generating and displaying a successful validation report, the agent must immediately proceed to payment reconciliation.
*   The agent MUST NOT WAIT FOR USER INPUT before proceeding to the next stage after displaying a successful validation report.
*   This maintains processing momentum and ensures efficient document processing.

## **3.0 Payment Reconciliation (Phase 2)**

### **3.1 Reconciliation Prerequisites**

**Process**: Verify all requirements are met before beginning reconciliation.

The agent must confirm the following:

Completion of Phase 1

*   All validation reports are displayed
*   No pending validation issues exist
*   Validation Report has been successfully shown to the user.

Data Availability

*   Computed content is accessible
*   All required fields are present  
    Example: Missing facility type summaries would prevent reconciliation initiation

System Readiness

*   AR system access is confirmed
*   Reference data is available
*   Processing resources are available  
    Example: Inability to access AR records would halt reconciliation

### **3.2 Payment Record Processing**

**Process**: Execute hierarchical reconciliation analysis with staged processing.

**Store Payment Records**

*   Store payment information
*   Record payment allocations
*   Verify decimal precision maintained

### **3.3 Multi-Level Reconciliation Analysis**

**Payment Level Match**

*   Compare total payment owed vs paid after applying  discounts and charges.
*   Apply configured threshold for match. Defualts to .01 for all customers with exceptions.
*   If match found:
*   Generate success report
    *   Call reconciliation success update
    *   Complete processing
*   If mismatch found:
    *   Document discrepancy
    *   Proceed to facility analysis

**Facility Type Analysis (if needed)**

*   For each facility type:
    *   Calculate allocated amounts
    *   Sum invoices with precision
    *   Compare against AR records
    *   Track all components:
        *   Base amounts
        *   Charges
        *   Discounts
*   If discrepancies found:
    *   Generate facility level report
    *   Proceed to invoice analysis

**Invoice Level Analysis (if needed)**

*   For each affected invoice:
    *   Match payment allocations
    *   Compare base amounts
    *   Verify all components
    *   Document variations
*   Upon completion:
    *   Generate comprehensive report
    *   Call reconciliation discrepancy update
    *   Halt further processing

### **3.4 Reconciliation Resolution**

**Process**: Analyze reconciliation results and determine outcome.

Results Compilation

*   Gather all analysis details
*   Calculate total discrepancies
*   Identify impacted areas
*   Document precision metrics

Outcome Determination

*   Apply threshold analysis (0.01)
*   Complete root cause assessment
*   Compile evidence chain
*   Document resolution path

### **3.5 Reconciliation Report Generation and Update Work Item**

**Process**: Generate required reports based on reconciliation outcome.

**CRITICAL**: The agent must follow this precise sequence for each reconciliation outcome:

**For Successful Reconciliation Outcome:**

1.  Generate report using Successful Reconciliation Template
    *   Include all Document & Match Details
    *   Complete Payment Analysis section
    *   Document all Processing Summary metrics
2.  Update work item with complete report
3.  Display exact same report to user
4.  Maintain report in chat history
5.  Proceed to completion tasks

**For Reconciliation Discrepancy Outcome:**

1.  Generate report using Reconciliation Discrepancy Template
    *   Include complete Document & Discrepancy Overview
    *   Perform detailed Discrepancy Analysis
    *   Complete Impact Assessment
2.  Update work item with complete report
3.  Display exact same report to user
4.  Maintain report in chat history
5.  Halt further processing

**Report Processing Requirements:**

*   Use exact template specified for each outcome
*   Maintain all formatting and structure
*   Include all required sections
*   Populate all placeholders
*   Preserve all formatting specifications

**Report Format Requirements**

Format Rules

*   Apply proper markdown formatting
*   Format all currency values with $ prefix
*   Show proper symbols (✓, X)
*   Maintain heading hierarchy

Display Requirements

*   Convert markdown to formatted text
*   Present tables with proper alignment
*   Show currency values in standard format
*   Display status symbols correctly

**CRITICAL NOTES**:

*   All reconciliation reports must strictly follow the templates defined in Section 4.4
*   No template sections may be omitted
*   All placeholders must be properly populated
*   Formatting must be consistently applied

### **3.6 Phase2 Completion Requirements**

**Process**: Verify and finalize reconciliation processing.

*   All reconciliation analysis completed
*   Reports generated using required templates
*   Work item updates confirmed
*   Processing metrics captured

## **4.0 Validation and Reconciliation Report Templates**

CRITICAL: These templates are mandatory formats for all validation and reconciliation reporting. The generated report is used first for work item updates and then for user communication, ensuring consistency across all reconciliation outcomes.

### **4.1 Important Usage Guidelines**

**Template Selection**

*   Use Exception Report for system/processing errors
*   Use Reconciliation Success for exact matches
*   Use Discrepancy Report for threshold violations

**Report Generation and Display Rules:**

*   Each report must be generated once and used consistently
*   The same report content must be used for:
    *   Work item updates
    *   User display
    *   Chat history
*   No variations or summaries are permitted
*   Reports must be displayed in full
*   All formatting must be preserved

**Critical Requirements**

*   Templates are mandatory formats
*   Must be used consistently
*   Follow exact structure
*   Maintain all sections

**Context Requirements**

*   All templates require full agent_insight_context
*   Reconciliation templates need computed_content
*   Exception template needs error context
*   All need processing metrics

**Data Handling**

*   Use exact decimal precision
*   Follow threshold rules precisely
*   Maintain data integrity
*   Document all calculations

**Critical Rules**

*   Never skip required sections
*   Always show calculations
*   Maintain format exactly
*   Include all metrics

**Processing Sequence**

1.  Generate report using template
2.  Validate completeness
3.  Update work item
4.  Present to user

### **4.2 Guide to Using Agent Context for Report Generation**

**Overview**  
The agent_insight_context provides essential information for generating validation failure, exception, and reconciliation reports. This context captures both document processing state and business logic outcomes through two distinct phases:

1.  Validation Phase Context
    *   Extraction configuration and results
    *   Validation rules and outcomes
    *   Document processing state
    *   Computed content structure
2.  Reconciliation Phase Context
    *   Payment matching results
    *   Facility-level analysis
    *   Invoice-level reconciliation
    *   Rate and pricing analysis

**Validation Phase Context Components**

The `agent_insight_context` for the validation phase  primarily consists of three main components, which reflect distinct phases of document processing:

**1. Extraction Context**

The **Extraction Context** is designed to capture the extraction process in detail, providing a basis for subsequent validation and reconciliation steps. This section includes configurations, events, metrics, and field mappings aligned with document processing needs.

**Summary of the Extraction Context Structure**

```

"extraction_context":  
{  
"document_id": "unique_identifier_for_the_document",  
"document_name": "document_name_with_format",  
"processing_phase": "Extraction",  
"summary": {  
"phase": "Extraction",  
"start_time": "start_timestamp",  
"end_time": "end_timestamp",  
"processing_events": [  
{  
"timestamp": "event_timestamp",  
"event_type": "Event Type (e.g., Extraction Start)",  
"description": "Brief description of the event",  
"details": { "key": "value pairs for additional event details" }  
}  
],  
"data_metrics": {  
"metrics": {  
"Metrics on Table Extracted": {  
"total_raw_tables": "count",  
"total_raw_rows": "count",  
"extracted_tables": "count",  
"extracted_rows": "count",  
"combined_summary_total": "sum_of_all_subtotals",  
"combined_summary_facility_types": "unique_facility_type_count"  
}  
}  
},  
"table_extraction_metrics": {  
"tables_per_page": { "page_number": "table_count" },  
"empty_columns_dropped": [],  
"columns_renamed": {},  
"total_raw_tables": "count",  
"total_raw_rows": "count",  
"extracted_tables": "count",  
"extracted_rows": "count"  
},  
"transformation_steps": [],  
"performance_metrics": {},  
"data_quality_indicators": {  
"completeness": "percentage",  
"consistency": "percentage",  
"accuracy": "percentage"  
}  
},  
"validation_results": {  
"rules_passed": "count",  
"rules_failed": "count",  
"results": [  
{  
"rule_id": "unique_rule_identifier",  
"passed": "boolean",  
"message": "description_of_the_result",  
"severity": "Error | Warning | Info",  
"details": { "key": "value pairs for additional result details" }  
}  
]  
},  
"configuration_used": {  
"document_type": {  
"non_tbl_fields": [{ "name": "field_name", "requirement": "Required or Optional" }],  
"tbl_fields": [{  
"name": "table_name",  
"table_definition": [  
{ "column": "column_name", "requirement": "Required or Optional" }  
]  
}]  
},  
"document_format": {  
"non_tbl_fields_mapping": [{ "field_name": "source_field", "field_identifier": "mapped_identifier" }],  
"tables": [  
{  
"tbl_fields_mapping": [{ "source": "source_column", "output": "mapped_column" }]  
}  
],  
"prompt_examples": "Markdown table format for prompt examples",  
"custom_config": { "camelot_flavor": "config_value" }  
}  
},  
"additional_context": {}  
}
```

**Details on Key Extraction Context Elements**

*   **Summary**
    *   Processing Events: A chronological record of key steps in the extraction process, including:
        *   Non-tabular Data Storage: Initial extraction and storage of core fields like "Customer ID" and "Total Payment Paid."
        *   Table Extraction Events: Breakdown of individual table extractions by page, headers, and processing metrics. Events highlight details such as:
        *   Table headers and structure for each page
        *   Row and discrepancy counts
        *   Summary Metrics: Aggregates data (e.g., "Total Amount Due," "Total Payment Sent") across facility types, aiding in cross-verification during reconciliation.
    *   Summary Metrics: Aggregates total rows, discrepancies, and amounts across tables.
    *   Summary Table Consolidation: Combines information from all facility types and subtotals, supporting validation during reconciliation.
*   **Data Metrics**: Provides aggregated metrics such as:
    *   Total Tables and Rows: A high-level view of all tables and rows in the document.
    *   Extraction Success Metrics: Number of tables and rows successfully extracted.
    *   Invoice Details and Summary Data: Rows and metrics specific to invoice details and subtotals.
*   **Table Extraction Metrics**:
    *   Tables per Page: Distribution of tables extracted per page.
    *   Empty and Renamed Columns: Lists any columns that were dropped or renamed during extraction.
*   **Validation Results**
    *   The Validation Results section captures detailed outcomes of all validation checks performed on extracted document data. It is particularly crucial when validation failures occur, as the structured insights are instrumental for the LLM’s analysis and troubleshooting. Each result is categorized based on rule success, failure, and severity, with the following key components:
        *   Rules Passed and Failed: Total counts of passed and failed validation rules, establishing the overall success rate and highlighting areas of concern if failures are high.
        *   Validation Result Details:
            *   Rule ID: Unique identifier of each validation rule, allowing precise tracking of specific validation checks.
            *   Message: A descriptive message outlining the nature of each result, providing context and clarity.
            *   Details: Additional details for each result, offering in-depth context or specific findings, such as field-specific discrepancies or data anomalies. This is valuable for identifying the data elements causing errors.
    *   **Overall Status and Failure Checks**:
        *   **Overall Status**: A boolean indication of whether any critical errors (`severity == "Error"`) exist in the results. If false, it signals that errors are present and need resolution.
        *   **Failures Present**: Highlights if any critical errors are detected, enabling the LLM to flag validation failures and focus on the root causes.
    *   **Categorized Results Access**:
        *   **Error Results**: Direct access to all results flagged as errors.
        *   **Warning Results**: Collection of results flagged as warnings, signaling potential but non-blocking issues.
        *   **Info Results**: Collection of results flagged as informational, helpful for full transparency in analysis.
*   **Configuration Used**
    *   **Document Type**:
        *   **Non-Tabular Fields**: Lists essential fields and their requirement status (e.g., Required, Optional), providing guidance on which fields must undergo validation.
        *   **Tabular Fields**: Describes each table’s required columns (e.g., "Invoice Details" with fields like "Invoice Reference" and "Amount Due"), aligning extraction outputs with expected schema.
    *   **Document Format**:
        *   **Field Mappings**: Maps extracted fields to their identifiers within the document schema to ensure extracted data follows the expected format.
        *   **Prompt-related Configuration**:
            *   **Prompt Examples**: Sample data structures for specific tables (e.g., Invoice Details and Facility Type Subtotals) provide formatting guidance for extraction prompts.
            *   **Extraction Prompt**: Configuration used to guide the extraction model, including settings like the `camelot_flavor` parameter (e.g., "lattice") for table parsing.

**2. Transformation Context**: 

The **Transformation Context** structures and enriches the extracted data, preparing it for validation and reconciliation. This context includes calculated fields, data mappings, and transformation events, providing a bridge between raw extraction and meaningful validation.

**Summary of the Transformation Context Structure**

```

"transformation_context": {  
"document_id": "unique_document_identifier",  
"document_name": "document_name_with_format",  
"processing_phase": "Transformation",  
"summary": {  
"phase": "Transformation",  
"start_time": "transformation_start_timestamp",  
"end_time": "transformation_end_timestamp",  
"processing_events": [  
{  
"timestamp": "event_timestamp",  
"event_type": "Event Type (e.g., Transformation Start)",  
"description": "Brief description of the event",  
"details": { "key": "value pairs for additional details" }  
}  
],  
"data_metrics": {  
"metrics": {}  
},  
"table_extraction_metrics": {  
"tables_per_page": {},  
"empty_columns_dropped": [],  
"columns_renamed": {},  
"total_raw_tables": "count",  
"total_raw_rows": "count",  
"extracted_tables": "count",  
"extracted_rows": "count",  
"invoice_details_extracted_tables": "count",  
"invoice_details_extracted_rows": "count",  
"summary_extracted_tables": "count",  
"summary_extracted_rows": "count"  
},  
"transformation_steps": [  
{  
"step_name": "Computation Step",  
"results": {  
"calculated_field": "computed_value",  
"additional_metric": "metric_value"  
}  
}  
],  
"performance_metrics": {},  
"data_quality_indicators": {  
"completeness": "percentage",  
"consistency": "percentage",  
"accuracy": "percentage"  
}  
},  
"validation_results": {  
"rules_passed": "count",  
"rules_failed": "count",  
"results": [  
{  
"rule_id": "unique_rule_identifier",  
"passed": "boolean",  
"message": "description_of_the_result",  
"severity": "Error | Warning | Info",  
"details": { "key": "value pairs for additional result details" }  
}  
]  
},  
"configuration_used": {},  
"additional_context": {}  
}
```

**Details on Key Transformation Context Elements**

*   **Transformation Summary**
    *   Processing Events: Sequentially documents transformation events, capturing timestamps and descriptions for each action, such as the start of transformations or computed fields completion. Key events include:
        *   Facility Type Totals Computation: Calculates totals for each facility type, including discounts and adjustments.
        *   Computed Fields: Summarizes derived fields such as `total_invoice_line_items`, subtotals by facility type, and the overall `computed_total_amount_paid`.
    *   Data Metrics: Placeholder for any metrics specific to transformation processes. Currently, it remains empty but is reserved for future use or additional metrics.
    *   Table Extraction Metrics: Even though extraction metrics are not directly modified in transformation, this placeholder records any tables or rows reprocessed or adjusted during transformation.
*   **Transformation Steps**
    *   Lists specific steps in transforming extracted data, focusing on computational and enrichment tasks that support validation.
        *   Computed Fields: Includes fields derived from extracted data, such as `total_invoice_line_items` and `invoice_subtotals_grouped_by_facility_type`. These computed fields are crucial for cross-checking in validation.
        *   Facility Type Totals: Totals by facility type (e.g., AgriTech Services, Greenhouse Complexes) are computed here, supporting subtotal validation.
*   **Transformation Events**
    *   Captures the timestamped events for each transformation step. Events could range from initializing transformations to specific calculations, such as computing total invoice amounts across line items. These provide critical reference points for tracing data lineage and supporting troubleshooting efforts.
    *   Transformation Metrics: Encompasses calculated fields (e.g., facility type subtotals, total invoice line items) that provide cumulative insights.
    *   Transformation Events: Summarizes computed totals and transformations, making it easier to cross-validate transformed values with extracted metrics.
    *   Data Quality Indicators: Measures like completeness, consistency, and accuracy are captured, highlighting any potential issues in data preparation before validation.

**3. Validation Context**: 

The **Validation Context** provides critical information on the final checks performed on extracted and transformed data, focusing on ensuring data quality and adherence to defined validation rules. This context captures essential details, especially during validation failures, making it a vital reference for an LLM conducting root cause analysis. Below is a structured summary, followed by an in-depth breakdown of important elements within this context.

**Validation Context Structure Summary**

```
{
  "validation_context": {
    "document_id": "unique_document_identifier",
    "document_name": "document_name_with_format",
    "processing_phase": "Validation",
    "summary": {
      "phase": "Validation",
      "start_time": "start_timestamp",
      "end_time": "end_timestamp",
      "processing_events": [
        {
          "timestamp": "event_timestamp",
          "event_type": "Event Type (e.g., Validation Start)",
          "description": "Brief description of the event",
          "details": { "key": "value pairs for additional event details" }
        }
      ],
      "data_metrics": {
        "metrics": {
          "validation_metrics": {
            "total_validations": "total_validation_count",
            "passed_validations": "passed_validation_count",
            "failed_validations": "failed_validation_count",
            "pass_rate": "pass_rate_percentage"
          }
        }
      },
      "table_extraction_metrics": {},
      "transformation_steps": [],
      "performance_metrics": {},
      "data_quality_indicators": {
        "completeness": "percentage",
        "consistency": "percentage",
        "accuracy": "percentage"
      }
    },
    "validation_results": {
      "rules_passed": "count",
      "rules_failed": "count",
      "results": [
        {
          "rule_id": "validation_rule_identifier",
          "passed": "boolean",
          "message": "Result description",
          "severity": "Severity level (Info, Warning, Error)",
          "details": { "key": "value pairs with rule-specific details" }
        }
      ]
    }
  }
}
```

**Details on Key Validation Context Elements**

*   **Processing Events**: A chronological record of the validation activities, including events such as:
    *   Validation Start: Indicates the beginning of validation.
    *   Discounts and Charges Validation: Details the matching status of discounts and additional charges, providing extracted versus computed values and identifying any discrepancies.
    *   Validation Complete: Marks the completion of the validation process.
*   **Data Metrics**:
    *   **Validation Metrics**: Key statistics on validation outcomes, which are valuable for a high-level assessment of data integrity:
        *   Total Validations: The total number of validation rules applied to the document.
        *   Passed Validations: Number of validation rules that passed successfully.
        *   Failed Validations: Number of validation rules that failed.
        *   Pass Rate: The overall success rate for validation.
*   **Validation Results**
    *   The validation_results section is the core component of the validation context, containing detailed information on each rule's outcome. Each entry provides specifics on validation success or failure, making it crucial for identifying and analyzing issues when validation fails. Key elements include:
        *   **Rules Passed and Failed**:
            *   Rules Passed: Indicates the total count of successfully validated rules.
            *   Rules Failed: Counts the validation rules that did not meet the criteria, highlighting areas that need attention.
        *   **Individual Validation Results**: Each result entry includes:
            *   Rule ID: A unique identifier for each validation rule, allowing precise tracking.
            *   Passed: Boolean indicating if the validation rule was successful.
            *   Message: Descriptive information on the rule's result, which aids in understanding the rule's objective and outcome.
            *   Severity: Classification of the result's importance—`Info` for informational results, `Warning` for potential issues, and `Error` for critical failures.
            *   Details: Additional data specific to the validation rule, which provides more context on each validation check. This information is essential when troubleshooting validation failures.
        *   **Specific Validation Rules and Their Checks**:
            *   TOTAL_INVOICES: Verifies that the total count of invoices matches the number of invoice line items extracted.
            *   FACILITY_TYPE_SUBTOTALS: Checks if facility type subtotals match between extracted and computed values, providing a breakdown for each facility type.
            *   TOTAL_PAYMENT: Compares extracted and computed totals for payment, allowing precise detection of payment-related discrepancies.
            *   TOTAL_DISCOUNTS: Ensures discounts are accurately captured and consistent with computed totals.
            *   TOTAL_CHARGES: Confirms the alignment of additional charges between extracted and computed amounts.

**Reconciliation Phase Context Components**

The agent_insight_context during reconciliation phases provides comprehensive information about payment processing, matching analysis, and discrepancy detection across four distinct phases. This context is crucial for generating detailed reports and understanding the reconciliation process outcomes.

**1. Payment Data Loading Context**

The Payment Data Loading Context captures the initial phase of payment processing, including data validation, storage, and basic analysis.

**Summary of Payment Data Loading Context Structure**

```
{
  "payment_data_loading": {
    "phase": "Payment Data Loading",
    "start_time": "timestamp",
    "end_time": "timestamp",
    "events": [
      {
        "timestamp": "event_timestamp",
        "event_type": "Event Type (e.g., Payment Data Processing Start)",
        "description": "Brief description of the event",
        "details": {
          "key": "value pairs for event details"
        }
      }
    ],
    "metrics": {
      "total_invoices": "count",
      "unique_facility_types": "count",
      "unique_service_types": "count",
      "document_metrics": {
        "customer_id": "identifier",
        "payment_reference": "reference",
        "payment_date": "date"
      },
      "payment_amounts": {
        "total_payment": "amount",
        "total_invoice": "amount",
        "total_discounts": "amount",
        "total_charges": "amount",
        "net_amount": "amount"
      },
      "facility_metrics": {
        "invoice_counts": {
          "facility_type": "count"
        },
        "amount_totals": {
          "facility_type": "amount"
        },
        "service_types": ["service_type_list"],
        "facility_distribution": {
          "facility_type": {
            "invoice_count": "count",
            "total_amount": "amount",
            "percentage": "percentage"
          }
        }
      }
    }
  }
}
```

**Key Components of Payment Data Loading Context**

*   Processing Events
    *   Payment Data Processing Start: Marks beginning of data validation
    *   Payment Record Created: Records successful payment record creation
    *   Payment Loading Complete: Indicates completion of data loading
*   Core Metrics
    *   Document Identifiers: Customer ID, payment reference, dates
    *   Payment Totals: Tracks various payment amounts (total, invoice, discounts, charges)
    *   Facility Analysis: Distribution of invoices and amounts across facilities
*   Distribution Analysis
    *   Invoice Distribution: Counts by facility type
    *   Amount Distribution: Payment totals by facility
    *   Service Type Mapping: Links between facilities and services
    *   Percentage Analysis: Relative distribution of amounts

**2. Payment Matching Context**

The Payment Matching Context focuses on the initial comparison between payment amounts and AR records.

**Summary of Payment Matching Context Structure**

```

"payment_matching": {  
"phase": "Payment Matching",  
"start_time": "timestamp",  
"end_time": "timestamp",  
"events": [  
{  
"timestamp": "event_timestamp",  
"event_type": "Event Type (e.g., Payment Matching Start)",  
"description": "Description of matching event",  
"details": {  
"payment_reference": "reference",  
"customer_id": "identifier",  
"payment_date": "date"  
}  
}  
],  
"metrics": {  
"metrics": {  
"payment_totals": {  
"customer_payment": "amount",  
"ar_gross": "amount",  
"ar_discounts": "amount",  
"ar_net": "amount"  
},  
"document_metrics": {  
"payment_method": "method",  
"bank_account": "account"  
},  
"matching_results": {  
"total_difference": "amount",  
"has_discrepancy": "boolean",  
"threshold": "amount"  
}  
}  
}  
}
```

**Key Components of Payment Matching Context**

*   Matching Events
    *   Payment Matching Start: Initial comparison setup
    *   Payment Matching Complete: Results of matching process
    *   Difference Detection: Recording of any discrepancies found
*   Payment Analysis
    *   Customer Payment Details: Total payment information
    *   AR System Values: Gross amount, discounts, net total
    *   Discrepancy Tracking: Difference calculations and threshold comparisons
*   Matching Metrics
    *   Total Differences: Overall payment vs AR comparison
    *   Threshold Analysis: Comparison against acceptable variance
    *   Match Status: Binary outcome of matching process

**3. Facility Type Reconciliation Context**

The Facility Type Reconciliation Context provides detailed analysis at the facility level.

Summary of Facility Type Reconciliation Context Structure

```

"facility_type_reconciliation": {  
"phase": "Facility Type Reconciliation",  
"start_time": "timestamp",  
"end_time": "timestamp",  
"events": [  
{  
"timestamp": "event_timestamp",  
"event_type": "Event Type (e.g., Facility Analysis Start)",  
"description": "Description of facility analysis",  
"details": {  
"facilities_analyzed": "count",  
"facilities_with_issues": "count"  
}  
}  
],  
"metrics": {  
"metrics": {  
"facility_analysis": {  
"total_facilities": "count",  
"facilities_with_discrepancies": "count",  
"facility_details": {  
"facility_type": {  
"remittance_amount": "amount",  
"ar_amount": "amount",  
"difference": "amount",  
"service_types": ["service_type_list"],  
"invoice_count": "count",  
"has_discrepancy": "boolean"  
}  
}  
}  
}  
}  
}
```

**Key Components of Facility Type Reconciliation Context**

*   Facility Analysis Events
    *   Analysis Initialization: Start of facility-level analysis
    *   Analysis Completion: Summary of facility findings
    *   Issue Detection: Recording of facility-level discrepancies
*   Facility Metrics
    *   Totals and Counts: Number of facilities analyzed
    *   Discrepancy Tracking: Facilities with issues
    *   Service Distribution: Services per facility type
*   Detailed Analysis
    *   Amount Comparisons: Remittance vs AR amounts
    *   Service Type Analysis: Service distribution by facility
    *   Discrepancy Details: Specific differences found

**4. Invoice Level Reconciliation Context**

The Invoice Level Reconciliation Context provides the most granular analysis of discrepancies.

**Summary of Invoice Level Reconciliation Context Structure**

```

"invoice_level_reconciliation": {  
"phase": "Invoice Level Reconciliation",  
"start_time": "timestamp",  
"end_time": "timestamp",  
"events": [  
{  
"timestamp": "event_timestamp",  
"event_type": "Event Type (e.g., Invoice Analysis Start)",  
"description": "Description of invoice analysis",  
"details": {  
"total_analyzed": "count",  
"discrepancies_found": "count"  
}  
}  
],  
"metrics": {  
"metrics": {  
"invoice_analysis": {  
"total_invoices": "count",  
"invoices_analyzed": "count",  
"invoices_with_discrepancies": "count",  
"discrepancy_summary": {  
"by_facility": { "facility_type": "count" },  
"by_service": { "service_type": "count" }  
}  
}  
}  
}  
}
```

**Key Components of Invoice Level Reconciliation Context**

*   Invoice Analysis Events
    *   Analysis Start: Beginning of invoice-level examination
    *   Discrepancy Detection: Finding of specific invoice issues
    *   Analysis Completion: Summary of invoice findings
*   Invoice Metrics
    *   Processing Totals: Numbers of invoices analyzed
    *   Discrepancy Counts: Issues found per category
    *   Distribution Analysis: Issues by facility and service type
*   Categorical Analysis
    *   Facility-Based Grouping: Issues grouped by facility
    *   Service-Based Grouping: Issues grouped by service type
    *   Pattern Detection: Identification of systematic issues

**Context Usage Guidelines**

*   Report Generation
    *   Use context progressively through phases
    *   Reference specific metrics for detailed analysis
    *   Include relevant events in chronological order
*   Discrepancy Analysis
    *   Start with payment-level discrepancies
    *   Drill down through facility-level analysis
    *   Conclude with invoice-specific issues
*   Pattern Identification
    *   Compare metrics across phases
    *   Look for systematic issues in facility groupings
    *   Analyze service-type patterns
*   Threshold Management
    *   Reference specified thresholds consistently
    *   Compare against standard tolerances
    *   Note cumulative impacts of discrepancies

This context structure provides comprehensive data for generating validation failure reports, exception reports, and reconciliation analysis, enabling the agent to provide detailed insights into the reconciliation process and its outcomes.

### **4.3 Validation Report Templates**

CRITICAL: These templates are mandatory formats for all validation reporting. The generated report is first used for work item updates and then presented to users in formatted form before moving to the reconciliation phase.

CRITICAL: After generating the report and sending it to chat, the agent must immediately proceed to the next step focused on payment reconciliation.

**1. Successful Validation Report Template Details**

For the below successful validation report template, use the following instructions:

*   Document Details
    *   Provide information about customer name, customer id, payment preference and total paid amount by the customer
*   Table Samples
    *   Show 3 rows in tabular form for each of the tables configured in the document type
    *   Use the agent_insight_context.extraction_context.configuration used to get metadata about the tables and columns and then use the invoice_details and the summary list get the 3 sample rows
*   Validation Results
    *   Provide overall metrics such as total checks performed, checks passed, checks failed, pass rate %
    *   Then list out each Rule, its status (Pass or Fail), message and details

**Successful Validation Report Template**

```

# **Validation Report**

**Document**: {agent_insight_context.document_name}  
**Stage**: Validation  
**Processing Result**: Validation Successful  
**Timestamp**: {validation_context.summary.start_time}

## **Document Details**

{Document Details}

## **Table Samples**

{Table Samples}

## **Validation Results**

{Validation Results}
```

**2. Validation Failure Template Details**

For the below validation failure template, use the following instructions:

1.  Document & Discrepancy Overview
    *   Extract key details from computed_content
    *   Show total discrepancy amount
    *   Highlight affected areas
2.  Discrepancy Analysis
    *   Use reconciliation results to analyze:
        *   Facility level discrepancies
        *   Invoice level issues
        *   Pattern identification
    *   Include all supporting metrics
3.  Impact Assessment
    *   Calculate financial impact
    *   Document affected business areas
    *   Provide correction guidance
    *   Include verification requirements

**Validation Failure Template**

```

# Validation Report

**Document**: {agent_insight_context.document_name}  
**Stage**: Validation  
**Processing Result**: Validation Failed  
**Timestamp**: {validation_context.summary.start_time}

## Document Details

{Document Details}

## Table Samples

{Table Samples}

## Validation Results

### Failed Rules

{Failed Rules}

### Passed Rules

{Passed Rules}

## Failure Analysis

### {Failure Analysis}

## Recommendations

{Recommendations}

## Next Steps

{Next Steps}
```

### **4.4 Reconciliation Report Templates**

**1. Successful Reconciliation Report Template Details**

For the below successful reconciliation report template, use the following instructions:

1.  Document & Match Details
    *   Extract remittance details from computed_content
    *   Show matching status and amount from reconciliation results
    *   Include key processing metrics
2.  Payment Analysis
    *   Use reconciliation results to show:
        *   Payment details and matching
        *   Facility type allocations
        *   Service type breakdowns
    *   Include all relevant metrics
3.  Processing Summary
    *   Extract metrics from processing events
    *   Show validation statuses
    *   Include performance data
    *   Document completeness indicators

**Successful Reconciliation Report Template**

```
# Reconciliation Report

**Document**: {agent_insight_context.document_name}  
**Status**: RECONCILED  
**Match Amount**: ${reconciliation_result.payment_amount:,.2f}  
**Timestamp**: {agent_insight_context.summary.start_time}

## Summary

✅ Payment successfully reconciled with AR records  
Total matched amount: ${reconciliation_result.payment_amount:,.2f}  
All amounts within threshold of ${reconciliation_result.threshold:,.2f}

## Payment Details

### Remittance Information

*   Customer: {remittance_fields.customer_name}
*   Reference: {reconciliation_result.payment_reference}
*   Date: {remittance_fields.payment_date}
*   Method: {remittance_fields.payment_method}
*   Account: {remittance_fields.bank_account}

### Amount Reconciliation

*   Payment Amount: ${reconciliation_result.payment_amount:,.2f}
*   AR Balance: ${reconciliation_result.ar_balance:,.2f}
*   Difference: ${abs(reconciliation_result.total_difference):,.2f}
*   Match Status: ✓ Within Threshold

## Processing Details

### Document Analysis

*   Total Invoices: {processing_metrics.total_invoices}
*   Facility Types: {processing_metrics.facility_type_count}  
    {for facility in processing_metrics.facility_types}  
    • {facility}  
    {endfor}
*   Service Types: {processing_metrics.service_type_count}  
    {for service in processing_metrics.service_types}  
    • {service}  
    {endfor}

### Facility Summaries

{for facility in facility_summaries}

#### {facility.facility_type}

*   Amount: ${facility.remittance_amount:,.2f}
*   Services: {", ".join(facility.service_types)}
*   Invoices: {facility.invoice_count}
*   Match Status: ✓ Reconciled  
    {endfor}

## Processing Metrics

### Validation Results

*   Field Validations: {validation_metrics.total_validations}
*   Rules Passed: {validation_metrics.passed_validations}
*   Data Quality Score: {data_quality_indicators.accuracy}%
*   Match Confidence: 100%

### Processing Performance

*   Start Time: {summary.start_time}
*   End Time: {summary.end_time}
*   Total Duration: {overall_processing_time:.2f} seconds
*   Status: ✓ Complete

## Next Steps

1.  Payment cleared for posting
2.  Reconciliation record archived
3.  No additional action required  
```

**2. Reconciliation Discrepancy Report Template Details**

For the below reconciliation discrepancy report template, use the following instructions:

Document & Discrepancy Overview

*   Extract key details from computed_content
*   Show total discrepancy amount
*   Highlight affected areas

Discrepancy Analysis

*   Use reconciliation results to analyze:
    *   Facility level discrepancies
    *   Invoice level issues
    *   Pattern identification
*   Include all supporting metrics

Impact Assessment

*   Calculate financial impact
*   Document affected business areas
*   Provide correction guidance
*   Include verification requirements

**Reconciliation Discrepancy Report Template**

```
# Reconciliation Report

**Document**: {agent_insight_context.document_name}  
**Status**: DISCREPANCY_FOUND
**Total Discrepancy**: ${abs(reconciliation_result.total_difference):,.2f}
**Timestamp**: {agent_insight_context.summary.start_time}

## Summary

X Payment reconciliation found discrepancies requiring review
Affected Facilities: {discrepancy_summary.affected_facility_count}
Total Difference: ${abs(reconciliation_result.total_difference):,.2f}

## Payment Details

### Remittance Information

*   Customer: {remittance_fields.customer_name}
*   Reference: {reconciliation_result.payment_reference}
*   Date: {remittance_fields.payment_date}
*   Method: {remittance_fields.payment_method}
*   Account: {remittance_fields.bank_account}

### Amount Analysis

*   Remittance Amount: ${reconciliation_result.payment_amount:,.2f}
*   AR Balance: ${reconciliation_result.ar_balance:,.2f}
*   Net Difference: ${abs(reconciliation_result.total_difference):,.2f}
*   Threshold: ${reconciliation_result.threshold:,.2f}

## Discrepancy Analysis

### Facility Level Discrepancies

{for facility in discrepancy_summary.facility_differences}
{if facility.has_discrepancy}

#### X {facility.facility_type}

*   Remittance Amount: ${facility.remittance_amount:,.2f}
*   AR System Amount: ${facility.ar_system_amount:,.2f}
*   Difference: ${abs(facility.difference):,.2f}
*   Affected Services: {", ".join(facility.service_types)}
*   Invoice Count: {facility.invoice_count}
    {endif}
    {endfor}

### Invoice Level Discrepancies

Found {len(invoice_discrepancies)} invoices with discrepancies:

{for invoice in invoice_discrepancies}

#### {invoice.invoice_number}

*   Remittance: ${invoice.remittance_amount:,.2f}
*   AR System: ${invoice.ar_amount:,.2f}
*   Difference: ${abs(invoice.difference):,.2f}
*   Service: {invoice.service_type}
*   Facility ID: {invoice.facility_id}
    {endfor}

## Root Cause Analysis

### Pattern Analysis

*   Discrepancy Distribution:
    • Affected Facilities: {discrepancy_summary.affected_facility_count}
    • Affected Invoices: {discrepancy_summary.affected_invoice_count}
    • Service Types: {", ".join(discrepancy_summary.affected_service_types)}

### Timing Analysis

*   Invoice Date Range: {min_date} to {max_date}
*   Processing Date: {agent_insight_context.summary.start_time}
*   Rate Changes: {identify_rate_changes()}
*   System Updates: {check_system_updates()}

## Impact Assessment

### Financial Impact

*   Total Discrepancy: ${abs(reconciliation_result.total_difference):,.2f}
*   Percentage of Payment: {(abs(reconciliation_result.total_difference) / reconciliation_result.payment_amount * 100):.2f}%
*   Materiality Threshold: ${reconciliation_result.threshold:,.2f}
*   Impact Level: {determine_impact_level()}

## Recommended Actions

### Immediate Steps

1.  Review discrepancies with accounting team
2.  Verify rate applications
3.  Check customer terms
4.  Prepare adjustment documentation
```

### **4.5 Exception Report Template Details**

For the below exception report template, use the following instructions:

1.  Document & Processing Details
    *   Extract state at time of error from agent_insight_context
    *   Include processing phase and timestamp
    *   Document which action was being performed
2.  Exception Analysis
    *   Use error details from agent_insight_context to provide:
        *   Error classification
        *   Processing impact
        *   Data quality implications
    *   Examine processing events timeline
    *   Note any patterns or anomalies
3.  Root Cause Analysis
    *   Use configuration metadata and document format info
    *   Analyze processing metrics and events
    *   Identify potential failure points
    *   Examine data state at time of error
4.  Recovery Guidance
    *   Provide specific actions based on error type
    *   Include both technical and business process steps
    *   Define verification requirements
    *   Note dependencies and prerequisites

**Exception Report Template**

```

# Exception Report

**Document**: {agent_insight_context.document_name}  
**Stage**: {agent_insight_context.processing_phase} 
**Processing Status**: Exception Encountered
**Timestamp**: {agent_insight_context.summary.start_time}

## Exception Details

### Error Classification

*   Type: {error_type from agent_insight_context}
*   Severity: {Critical/High/Medium based on impact}
*   Component: {affected_component from events}
*   Operation: {failed_operation from events}

### Processing State

*   Last Successful Phase: {agent_insight_context.last_successful_phase}
*   Failed Operation: {agent_insight_context.summary.processing_events[-1].description}
*   Processing Progress: {percentage or stage indicator}
*   Data State: {data quality metrics if available}

## Root Cause Analysis

### Processing Timeline

{Analyze last 5 events from agent_insight_context.summary.processing_events}

### System State at Failure

*   Memory Usage: {from performance_metrics}
*   Processing Time: {from overall_processing_time}
*   Data Quality Indicators: {from data_quality_indicators}
*   Active Components: {from configuration_used}

### Document Context

*   Document Type: {from document_type}
*   Format Requirements: {from document_format}
*   Processing Rules: {from configuration_used}
*   Validation State: {from validation_results}
```

### **4.6 Report Processing Requirements**

**1. Report Generation Rules**

*   Generate exactly one report per outcome
*   Use appropriate template based on outcome
*   Populate all placeholders with correct data
*   Maintain precise decimal calculations
*   Follow all formatting specifications

**2. Work Item Update Rules**

*   Store complete report in work item
*   Preserve all formatting and structure
*   Include all sections and details
*   Maintain data precision
*   Keep full audit trail

**3. User Display Rules**

*   Show exact same report as stored in work item
*   Display complete report without modifications
*   Maintain all formatting and structure
*   Present in proper sequence
*   Keep reports visible in chat history

**4. Verification Requirements**

*   Verify report completeness
*   Check all sections present
*   Validate formatting compliance
*   Confirm data accuracy
*   Ensure proper display

**5. Prohibited Practices**

*   No simplified summaries
*   No alternate formats
*   No partial reports
*   No format modifications
*   No content variations