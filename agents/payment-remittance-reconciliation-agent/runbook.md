# Payment Remittance Processing Agent Runbook

## 1\. Overview

### 1.1 Objective

The Payment Remittance Processing Agent autonomously handles remittance documents through validation and reconciliation phases. It ensures data integrity via extraction, transformation, and validation before proceeding to reconciliation against Accounts Receivable records. The agent operates independently, requesting human intervention only for critical issues.

### 1.2 Critical Processing Requirements

#### 1.2.1 Sequential Processing

*   Steps must execute in strict sequential order
*   No parallel processing permitted
*   Each step depends on prior step completion
*   Phase 2 cannot begin until Phase 1 completes successfully

#### 1.2.2 Phase Transition Control

*   Validation phase must complete successfully before reconciliation
*   All validation checks must pass

#### 1.2.3 Error Handling

*   Halt processing immediately on any failure
*   Do not proceed to subsequent steps
*   Update work item status as failed
*   Provide detailed error report
*   Validation failures prevent reconciliation phase entry

## 2\. Processing Phases

### 2.1 Phase 1: Document Validation

#### 2.1.1 Document Retrieval and Assessment

**Process**: Verify document readiness for processing.

The agent begins by retrieving the remittance work item and verifying its readiness for processing. This involves comprehensive checks of the document's status and content integrity before processing begins.

**Core Assessment Tasks**:  
The agent performs several key verifications:

Document Completeness Check

*   Verifies all required sections are present
*   Confirms document structure integrity
*   Validates metadata presence
*   Example: A remittance missing its facility type summaries section would fail this check

Status Verification

*   Checks current document processing status
*   Only continue if the processing status is marked as Extraction Completed.

Content Structure Assessment

*   Validates document format compliance
*   Verifies section organization
*   Checks data field presence
*   Example: A properly structured document should contain clearly defined sections for payment details, invoice listings, and facility summaries

#### 2.1.2 Data Extraction and Processing

**Process**: Extract and structure the remittance information into standardized formats.

The agent systematically processes the document content, transforming raw data into structured information. This phase focuses on accurate extraction while maintaining data integrity.

**Key Extraction Components**:

Payment Information Processing  
The agent extracts core payment details including:

*   Total payment amount
*   Payment date and method
*   Reference information  
    Example: When processing a wire transfer remittance, the agent extracts details like transfer date, amount, and reference number, converting them into standardized formats.

Invoice Line Item Processing  
For each invoice entry, the agent:

*   Extracts invoice numbers and dates
*   Processes monetary amounts
*   Captures service details  
    Example: Processing an electricity service invoice would include extracting the invoice number, service period, usage amount, and corresponding charges.

Facility Information Extraction  
The agent processes facility-related data:

*   Facility identifiers
*   Service types
*   Usage metrics  
    Example: For a greenhouse facility, the agent would extract both electricity and water usage data, along with any supplementary services.

#### 2.1.3 Document Validation

**Process**: Validate document accuracy and internal consistency through comprehensive checks.

The agent performs multi-level validation to ensure document integrity and accuracy. Each validation addresses specific aspects of the remittance data.

**Key Validation Areas**:

Total Payment Validation  
The agent examines the stated total payment amount against the sum of all individual invoice payments, considering both discounts and additional charges. For example:
* Add all individual invoice payment amounts
* Subtract the total discounts
* Add any additional charges
* Compare the calculated total to the stated total payment

Facility Type Subtotal Validation  
The agent verifies facility-level calculations:
* Calculates subtotals for each facility type
* Compares against stated facility totals
* Verifies cross-facility consistency
* Sum all greenhouse facility invoices
* Sum all vertical farming unit invoices
* Compare each subtotal against stated facility totals
* Verify that facility subtotals sum to the total payment

Invoice Count and Consistency  
The agent performs detailed invoice validation:
* Verifies the stated total invoice count matches actual line items
* Checks for duplicate invoice numbers
* Validates invoice date sequences
* Ensures all required invoice fields are present
* Count all invoice line items
* Verify unique invoice numbers
* Confirm all required fields are populated
* Compare against the stated total

Adjustment Validation  
The agent validates all payment adjustments:
* Verifies discount calculations
* Validates additional charges
* Ensures adjustment totals match stated amounts
* Calculate individual discount amounts
* Sum all discounts
* Compare against stated total discounts
* Verify discount application rules

#### 2.1.4 Validation Error Analysis

**Process**: When validation failures occur, perform comprehensive analysis using agent context to determine root cause.

The agent must systematically analyze validation failures through:

Document Configuration Analysis
* Review document type configuration
  - Required vs. optional fields
  - Table structure requirements
  - Field mapping configurations
* Check data extraction configuration
  - User prompt instructions
  - Field mapping rules
  - Validation criteria

Processing Event Review
* Examine extraction sequence
  - Table extraction events
  - Field mapping results
  - Transformation steps
* Analyze computation flow
  - Calculation events
  - Data transformations
  - Field derivations

Data Pattern Investigation
* Review data consistency
  - Column presence across tables
  - Field value patterns
  - Structure consistency
* Check relationships
  - Between tables
  - Across sections
  - Field dependencies

Root Cause Analysis Example:
For zero amount validations:
1. Review agent context to check:
   * Table extraction events for column presence
   * Field mapping configurations
   * Document structure processing
2. Analyze potential causes:
   * Missing facility type column
   * Incorrect table structure
   * Failed column mapping
3. Check document configuration:
   * Required field definitions
   * Table structure requirements
   * Field relationship rules

Evidence Collection:
* Document relevant events from context
* Note configuration settings
* Track data transformations
* Record structural patterns

#### 2.1.5 Validation Results Processing

**Process**: Process validation outcomes and determine next steps based on results.

The agent handles validation results through distinct pathways:

For Successful Validation:
1. Verify all validations passed within tolerance
2. Generate comprehensive success report
3. Update work item status to "VALIDATION_COMPLETED"
4. Prepare data for reconciliation phase

For Failed Validation:
1. Perform validation error analysis using agent context
2. Document root cause findings
3. Generate detailed failure report including:
   * Specific failed validations
   * Impact assessment
   * Root cause analysis
   * Evidence from agent context
4. Update work item status to "VALIDATION_FAILED"
5. Halt further processing

#### 2.1.6 Report Generation

The agent generates structured reports for all validation outcomes. 

**Note: After generating the report, the agent must immediately proceed to the next step focused on payment reconciliation.**

Reports must include:

**For Success**:

```
# Validation Report

**Stage**: Validation
**Status**: SUCCESS
**Timestamp**: [Current Timestamp]

## Summary
All validation checks have passed successfully. The document demonstrates complete internal consistency and is ready for reconciliation processing.

## Validation Results

### Overall Metrics
- Total Checks Performed: 4
- Checks Passed: 4
- Checks Failed: 0

### Passed Validations
1. Invoice Count Validation
   - Expected Count: 35
   - Actual Count: 35
   - Status: ✓ PASSED

2. Facility Type Subtotal Validation
   - Greenhouse Complexes
     * Expected: $450,000.00
     * Calculated: $450,000.00
     * Difference: $0.00
   - Vertical Farming Units
     * Expected: $275,000.00
     * Calculated: $275,000.00
     * Difference: $0.00
   - Hydroponics Systems
     * Expected: $150,000.00
     * Calculated: $150,000.00
     * Difference: $0.00
   - Status: ✓ PASSED

3. Total Payment Validation
   - Expected: $875,000.00
   - Calculated: $875,000.00
   - Difference: $0.00
   - Status: ✓ PASSED

4. Discounts and Charges Validation
   - Total Discounts
     * Expected: $12,500.00
     * Calculated: $12,500.00
     * Difference: $0.00
   - Additional Charges
     * Expected: $2,500.00
     * Calculated: $2,500.00
     * Difference: $0.00
   - Status: ✓ PASSED

## Next Steps
Now proceeding with reconciliation phase. Processing will continue automatically unless explicitly paused for review. Initiating reconciliation...
```

**For Failure**:

```
# Validation Report

**Stage**: Validation
**Status**: FAILURE
**Timestamp**: [Current Timestamp]

## Summary
Validation process failed due to critical discrepancies in facility type subtotals and total payment calculations.

## Validation Results

### Overall Metrics
- Total Checks Performed: 4
- Checks Passed: 2
- Checks Failed: 2

### Failed Validations

1. Facility Type Subtotal Validation
   - Discrepancies Found:
     * Type A Facilities
       - Stated: $450,000.00
       - Calculated: $458,284.06
       - Difference: $8,284.06
     * Type B Facilities
       - Stated: $425,000.00
       - Calculated: $425,000.00
       - Difference: $0.00
   - Status: ✗ FAILED
   - Impact: HIGH

2. Total Payment Validation
   - Expected: $875,000.00
   - Calculated: $883,284.06
   - Difference: $8,284.06
   - Status: ✗ FAILED
   - Impact: HIGH

## Impact Assessment
1. Financial Impact:
   - Material difference of $8,284.06
   - Represents 0.95% of total payment amount
   - Exceeds standard tolerance threshold

2. Processing Impact:
   - Halts reconciliation phase processing
   - Requires manual review and correction
   - May affect downstream payment applications

## Next Steps
1. Document requires manual review
2. Focus on Type A Facilities calculations
3. Reprocess after corrections
4. Update validation rules if needed
```

### 2.2 Phase 2: Payment Reconciliation

#### 2.2.1 Reconciliation Prerequisites

**Process**: Verify all requirements are met before beginning reconciliation.

The agent must confirm:

Phase 1 Completion

*   Status is "VALIDATION\_COMPLETED"
*   All validation reports are stored and accessible
*   No pending validation issues exist
*   Example: A document with status "VALIDATION\_COMPLETED" but missing validation reports would fail this check

Data Availability

*   Computed content is accessible
*   Processing context is maintained
*   All required fields are present  
    Example: Missing facility type summaries would prevent reconciliation initiation

System Readiness

*   AR system access is confirmed
*   Reference data is available
*   Processing resources are available  
    Example: Inability to access AR records would halt reconciliation

#### 2.2.2 Payment Storage and Multi-Level Reconciliation Analysis

**Process**: Store payment data and perform hierarchical reconciliation analysis with early exit on match.

Payment Data Storage

*   Store customer information
*   Create payment record
*   Record invoice allocations
*   Verify storage completion
*   Maintain decimal precision

For multi-level reconciliation analysis, the agent executes reconciliation through progressive levels of detail:

Payment Level Match  
The agent first attempts to match at the highest level:

*   Compare total payment against AR records
*  **The default .01  must always be used for the analysis unless told otherwise.** 
*   Evaluate match status
*   Record successful match
*   Generate success report
*   Exit reconciliation process

Facility Type Level Analysis  
If payment-level match fails, analyze by facility type:

*   Group transactions by facility type
*   Calculate type-level totals
*   Compare against AR records

Invoice Level Analysis  
For facility types with discrepancies:

*   Analyze individual invoices
*   Match line item amounts
*   Verify adjustments

#### 2.2.3 Discrepancy Processing

**Process**: Handle and document any found discrepancies.

The agent processes discrepancies through systematic analysis:

Discrepancy Classification

*   Categorize by type:
    *   Payment amount mismatch
    *   Facility type subtotal variance
    *   Individual invoice difference
*   Assign severity levels
*   Calculate materiality

Impact Analysis

*   Calculate financial impact
*   Assess business implications
*   Determine processing effects

#### 2.2.4 Results Processing and Reporting

**Process**: Generate comprehensive reconciliation results and update work item status.

The agent generates detailed reports based on reconciliation outcomes:

For Successful Reconciliation:

```
# Reconciliation Report

**Status**: RECONCILED
**Timestamp**: [Current Timestamp]

## Summary
Payment successfully reconciled with all records. All facility types and invoices matched AR system records within tolerance levels.

## Payment Details
- Reference: WT-2024-10502
- Date: [Current Date]
- Total Amount: $875,000.00

## Reconciliation Results
✅ Payment successfully matched to AR records
- Payment Amount: $875,000.00
- AR Balance: $875,000.00
- Difference: $0.00
- Processed Invoices: 35

### Facility Type Reconciliation
All facility types successfully matched:
1. Type A Facilities
   - Amount: $450,000.00
   - Status: ✓ Matched
   - Invoices: 18

2. Type B Facilities
   - Amount: $425,000.00
   - Status: ✓ Matched
   - Invoices: 17

## Processing Metrics
- Processing Time: 2.3 seconds
- Validation Steps: 15
- Confidence Score: 100%

## Next Steps
1. Payment ready for posting
2. No further action required
3. Documentation archived
```

For Reconciliation with Discrepancies:

```
# Reconciliation Report

**Status**: DISCREPANCY_FOUND
**Timestamp**: [Current Timestamp]

## Summary
Discrepancies found during reconciliation. Type B Facilities show mismatches with AR system records.

## Payment Details
- Reference: WT-2024-10502
- Date: [Current Date]
- Total Amount: $875,000.00

## Discrepancy Details

### 1. Facility Type Level
✓ Type A Facilities
- Remittance Amount: $450,000.00
- AR System Amount: $450,000.00
- Status: Matched

❌ Type B Facilities
- Remittance Amount: $425,000.00
- AR System Amount: $426,500.00
- Difference: -$1,500.00
- Affected Invoices: 1

### 2. Invoice Level Analysis
Found 1 invoice with discrepancy:

1. Invoice B-1002
   - Remittance: $92,500.00
   - AR System: $94,000.00
   - Difference: -$1,500.00
   - Category: Base Amount Mismatch

## Root Cause Analysis
1. Pattern Analysis:
   - Single invoice affected
   - Recent rate adjustment period
   - Isolated to Type B Facilities

2. Impact Analysis:
   - Material difference identified
   - Represents 0.17% of total payment
   - Exceeds standard threshold

## Recommendations
1. Immediate Actions:
   - Review Invoice B-1002
   - Verify rate application
   - Check for adjustments
   - Prepare variance report

2. Process Improvements:
   - Update rate verification
   - Enhance matching rules
   - Review tolerance levels

## Next Steps
1. Place payment on hold
2. Review discrepant invoice
3. Prepare adjustment request
4. Update reconciliation rules
```

#### 2.2.5 Phase Completion Requirements

**Process**: Ensure proper completion of reconciliation phase.

Final Verification Tasks:

Data Completeness

*   All reconciliation steps completed
*   Results properly documented
*   Reports generated and stored
*   Status updates applied

Context Management

*   Processing metrics captured
*   Audit trail complete
*   Analysis context preserved
*   Results archived

Status Requirements

*   Correct final status applied
*   Reports properly attached
*   Notifications generated
*   Processing logs complete

## 3\. Additional Guidelines

### 3.1 Processing Controls

The agent maintains strict processing controls throughout:

Sequence Management

*   Follow defined processing order
*   Verify step completion
*   Maintain process integrity
*   Track state transitions

Context Handling

*   Preserve processing context
*   Maintain data lineage
*   Track decision points
*   Enable audit capability

Error Management

*   Apply consistent error handling
*   Maintain error context
*   Enable recovery paths
*   Document error patterns

### 3.2 Performance Requirements

The agent monitors and maintains performance metrics:

Processing Efficiency

*   Track step duration
*   Monitor resource usage
*   Record throughput metrics
*   Maintain performance logs

Quality Metrics

*   Validation accuracy
*   Match precision
*   Processing reliability
*   Error rates

### 3.3 Security and Compliance

The agent ensures secure processing:

Data Protection

*   Secure data handling
*   Access control enforcement
*   Audit trail maintenance
*   Compliance verification

Processing Controls

*   Authority verification
*   Permission enforcement
*   Activity logging
*   Compliance monitoring