# Remittance Document Generator

## Overview

The Test Generator component provides a sophisticated framework for creating realistic test scenarios that validate both the document processing capabilities and business logic of the Worker Agent. This component is critical for ensuring the agent can handle complex real-world scenarios including various types of discrepancies and edge cases.

## Architecture

```
test_generators/
├── curated_test_cases/           # Pre-defined test scenarios
├── test_cases/                   # Generated test outputs
├── remittance_test_generator.py  # Main generator
├── db_setup_generator.py         # Database configuration
└── utils/                        # Generator utilities
```

## Key Components

### 1. Test Case Generation
Three primary types of test cases:

```python
class RemittanceTestGenerator:
    def generate_reconciling_case(self, customer_data: Dict):
        """Generate perfectly matching test case."""
        pass
        
    def generate_single_facility_discrepancy(self, customer_data: Dict):
        """Generate test case with systematic facility-type variance."""
        pass
        
    def generate_multi_facility_discrepancy(self, customer_data: Dict):
        """Generate test case with multiple facility discrepancies."""
        pass
```

### 2. Test File Generation

Each test case generates three key files:

1. **Markdown File** (`remittance.md`)
   - Customer-facing document view
   - Original payment amounts
   - Facility subtotals
   - Invoice details

2. **Database Setup** (`db_setup.json`)
   - Table structures
   - Adjusted amounts
   - Configuration settings

3. **Metadata** (`metadata.json`)
   - Test case parameters
   - Expected outcomes
   - Validation data

## Test Case Types

### 1. Reconciling Case
Perfect match scenario:
```python
def _generate_reconciling_case(self, customer_data: Dict):
    """
    Generate test case where all amounts match exactly.
    """
    # Generate base invoices
    invoices, facility_subtotals = self._generate_base_invoices()
    
    # Calculate totals
    total_invoice_amount = sum(
        Decimal(str(inv['Amount Due']))
        for inv in invoices
    )
    total_discounts = sum(
        Decimal(str(inv['Discounts']))
        for inv in invoices
    )
    
    # Set payment to match exactly
    payment_amount = total_invoice_amount - total_discounts
```

### 2. Single Facility Discrepancy
Controlled variance testing:
```python
def _generate_single_facility_discrepancy(self, customer_data: Dict):
    """
    Generate test case with 2% systematic difference in one facility type.
    """
    # Generate base invoices
    invoices, facility_subtotals = self._generate_base_invoices()
    
    # Apply 2% increase to Greenhouse Complex invoices
    for invoice in invoices:
        if invoice['Facility Type'] == 'Greenhouse Complexes':
            amount = Decimal(str(invoice['Amount Due']))
            invoice['Amount Due'] = float(
                amount * Decimal('1.02')
            )
```

### 3. Multi-Facility Discrepancy - Not Fully Implemented
Complex scenario testing:
```python
def _generate_multi_facility_discrepancy(self, customer_data: Dict):
    """
    Generate test case with various facility type discrepancies.
    """
    invoices, facility_subtotals = self._generate_base_invoices()
    
    adjustments = {
        'Greenhouse Complexes': Decimal('1.015'),
        'Vertical Farming Units': Decimal('0.99'),
        'Hydroponics Systems': {
            'condition': 'water_service',
            'factor': Decimal('1.02')
        }
    }
```

## Usage

### Basic Test Generation to see Customer, Facility, and Invoice Data before Deploying Agent

This enables you to load up your Accounts Receivables System with the invoices that have been sent to customers. This will be used as the source of truth when the Agent performs the reconciliation process. 

```python
from reconciliation_ledger.test_generators import RemittanceTestGenerator

generator = RemittanceTestGenerator()

# Generate test cases
generator.generate_reconciling_case(customer_data)
generator.generate_single_facility_discrepancy(customer_data)
generator.generate_multi_facility_discrepancy(customer_data)
```

### Loading Test Cases

```python
from reconciliation_ledger.test_generators import CuratedTestLoader

loader = CuratedTestLoader()
loaded_cases = loader.load_all_test_cases()
```

## Test Case Structure

### 1. Document Generation
```python
def _generate_markdown_content(
    self,
    customer_data: Dict,
    invoices: List[Dict],
    facility_subtotals: Dict[str, Decimal],
    payment_amount: Decimal
) -> List[str]:
    """
    Generate markdown representation of remittance document.
    """
    pass
```

### 2. Database Setup
```python
def _generate_db_setup(
    self,
    case_name: str,
    customer_data: Dict,
    adjusted_invoices: List[Dict],
    discrepancy_config: Dict
) -> Dict:
    """
    Generate database configuration for test case.
    """
    pass
```

## Configuration

```yaml
test_generation:
  decimal_precision: 2
  rounding_mode: ROUND_HALF_UP
  
discrepancies:
  single_facility:
    variance: 0.02
    facility_type: Greenhouse Complexes
    
  multi_facility:
    variances:
      - facility: Greenhouse Complexes
        factor: 1.015
      - facility: Vertical Farming Units
        factor: 0.99
```


