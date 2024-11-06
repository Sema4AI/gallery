# Payment Remittance Reconciliation Agent

## Overview

The Payment Remittance Reconciliation Agent is an intelligent automation solution designed to handle the complex process of validating and reconciling payment remittances against accounts receivable records. This agent combines document intelligence capabilities with precise financial calculations to ensure accurate payment processing and reconciliation.

## Project Structure

```
payment-remittance-reconcile-agent/
├── actions/
│   └── MyActions/
│       ├── payment-remittance-reconcile-action/    # Main reconciliation logic
│       └── payment-remittance-validate-action/     # Validation processing
├── reconciliation_ledger/                          # Database and data management
│   └── test_generators/                           # Test data generation
└── runbook.md                                     # Detailed processing instructions
```

## Key Components

### 1. Payment Remittance Reconciliation Action

**Location**: `/actions/MyActions/payment-remittance-reconcile-action`

This component handles the core reconciliation process:

- **Invoice Loading**: Processes invoice data into DuckDB with precise decimal handling
- **Multi-Level Reconciliation**: Performs hierarchical analysis at payment, facility, and invoice levels
- **Decimal Precision**: Maintains exact decimal calculations throughout processing
- **Discrepancy Analysis**: Identifies and reports mismatches with detailed impact assessment

Key Features:
- Exact decimal precision for all monetary calculations
- Hierarchical reconciliation with early exit on match
- Comprehensive discrepancy reporting
- Facility-type based analysis
- Invoice-level matching

### 2. Payment Remittance Validation Action

**Location**: `/actions/MyActions/payment-remittance-validate-action`

Handles document validation and data integrity:

- **Document Extraction**: Processes remittance documents into structured data
- **Data Validation**: Performs comprehensive validation checks
- **Field Verification**: Ensures all required data is present and correctly formatted
- **Total Verification**: Validates payment totals and facility subtotals

Validation Checks:
- Invoice count verification
- Facility type subtotal validation
- Total payment amount validation
- Discounts and charges validation

### 3. Test Generation Framework

**Location**: `/reconciliation_ledger/test_generators`

Provides comprehensive test case generation:

- **Curated Test Cases**: Pre-defined scenarios for common reconciliation patterns
- **Dynamic Test Generation**: Creates test cases with controlled discrepancies
- **Database Setup**: Generates test database with precise decimal values
- **Markdown Generation**: Creates human-readable test documentation

Test Case Types:
- Reconciling cases (exact matches)
- Single facility discrepancies
- Multi-facility discrepancies
- Threshold adjustment cases

## Usage

### Installation

```bash
pip install -r requirements.txt
```

### Running Reconciliation

```python
from reconciliation_ledger.invoice_loader import InvoiceLoader
from invoice_reconciliation_service import InvoiceReconciliationLedgerService

# Initialize services
loader = InvoiceLoader()
reconciliation_service = InvoiceReconciliationLedgerService(config, context_manager)

# Process remittance
loader.load_reference_data()
reconciliation_service.analyze_payment_reconciliation(
    payment_reference="WIRE2024100502",
    threshold=Decimal('0.01')
)
```

### Generating Test Cases

```python
from reconciliation_ledger.test_generators import RemittanceTestGenerator

generator = RemittanceTestGenerator()
generator.generate_reconciling_case(customer_data)
generator.generate_single_facility_discrepancy(customer_data)
```

## Key Features

1. **Precise Financial Calculations**
   - Exact decimal precision throughout processing
   - Consistent rounding behavior
   - Threshold-based comparison

2. **Comprehensive Validation**
   - Multi-level validation checks
   - Detailed error reporting
   - Early validation failure detection

3. **Flexible Reconciliation**
   - Hierarchical reconciliation process
   - Early exit on successful matches
   - Detailed discrepancy analysis

4. **Robust Testing**
   - Curated test case library
   - Dynamic test case generation
   - Controlled discrepancy injection

## Configuration

Key configuration options:

```yaml
reconciliation:
  threshold: 0.01
  decimal_precision: 2
  early_exit: true
  
validation:
  strict_mode: true
  require_all_fields: true
  
database:
  type: duckdb
  decimal_handling: exact
```

## Development

### Running Tests

```bash
pytest tests/
```

### Generating Test Data

```bash
python -m reconciliation_ledger.test_generators.generate_test_cases
```

## Reporting

The agent generates standardized reports for both validation and reconciliation phases:

1. **Validation Reports**
   - Document integrity status
   - Field validation results
   - Calculation verifications

2. **Reconciliation Reports**
   - Match/mismatch status
   - Detailed discrepancy analysis
   - Impact assessments
   - Recommended actions

## Error Handling

The system provides comprehensive error handling:

- Detailed error messages
- Context preservation
- Graceful failure modes
- Recovery recommendations

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request with detailed description
4. Ensure all tests pass
5. Follow the coding standards

## License

Licensed under the MIT License. See LICENSE file for details.