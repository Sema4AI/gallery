# Payment Remittance Reconciliation Actions

## Overview

The Payment Remittance Reconciliation Action represents the core reconciliation phase of the Worker Agent, demonstrating advanced document-centric workflow automation. This component handles the complex task of matching payment remittances against accounts receivable records with precise financial calculations and comprehensive discrepancy analysis.

## Architecture

```
payment-remittance-reconcile-action/
├── reconciliation_ledger/              # Core reconciliation engine
│   ├── db/                            # Database management
│   ├── services/                      # Business logic services
│   └── test_generators/               # Test case generation
├── context/                           # Context management
├── models/                            # Data models
└── utils/                             # Utility functions
```

## Key Components

### 1. Reconciliation Ledger
Core financial processing engine:

- **Database Management**
  - DuckDB/Neo4j integration 
  - Exact decimal handling
  - Transaction integrity
  - Data persistence

- **Services**
  - Payment processing
  - Multi-level reconciliation
  - Discrepancy detection
  - Report generation

### 2. Multi-Level Reconciliation Analysis

The reconciliation process follows a hierarchical approach:

1. **Payment Level**
   ```python
   def analyze_payment_level(self, payment_data: Dict) -> MatchResult:
       """
       Performs top-level payment matching with early exit on success.
       """
       payment_amount = self._parse_monetary_value(payment_data['total_payment'])
       ar_balance = self._calculate_ar_balance(payment_data['customer_id'])
       
       if abs(payment_amount - ar_balance) <= self.threshold:
           return MatchResult(status="SUCCESS", difference=Decimal('0.00'))
   ```

2. **Facility Level**
   ```python
   def analyze_facility_level(self, payment_id: str) -> List[FacilityDiscrepancy]:
       """
       Analyzes discrepancies at facility type level.
       """
       facility_totals = self._calculate_facility_totals(payment_id)
       ar_facility_totals = self._get_ar_facility_totals(payment_id)
       
       return self._compare_facility_totals(facility_totals, ar_facility_totals)
   ```

3. **Invoice Level**
   ```python
   def analyze_invoice_level(self, facility_discrepancies: List[FacilityDiscrepancy]) -> List[InvoiceDiscrepancy]:
       """
       Performs detailed invoice-level analysis for facilities with discrepancies.
       """
       invoice_discrepancies = []
       for facility in facility_discrepancies:
           invoices = self._get_facility_invoices(facility.facility_id)
           discrepancies = self._analyze_invoices(invoices)
           invoice_discrepancies.extend(discrepancies)
       return invoice_discrepancies
   ```


## Usage

### Basic Reconciliation Flow

```python
from reconciliation_ledger.invoice_loader import InvoiceLoader
from invoice_reconciliation_service import InvoiceReconciliationLedgerService

# Initialize services
loader = InvoiceLoader()
service = InvoiceReconciliationLedgerService(config, context_manager)

# Perform reconciliation
result = service.analyze_payment_reconciliation(
    payment_reference="WIRE2024100502",
    threshold=Decimal('0.01')
)

# Process results
if result.status == "MATCHED":
    service.process_successful_match(result)
else:
    service.handle_discrepancies(result)
```

### Handling Discrepancies

```python
def handle_discrepancies(self, result: ReconciliationResult):
    """
    Process discrepancies found during reconciliation.
    """
    # Generate detailed report
    report = self.generate_discrepancy_report(result)
    
    # Update work item status
    self.update_work_item_with_reconciliation_success(
        status="DISCREPANCY_FOUND",
        details=report
    )
    
    # Notify relevant teams
    self.send_notifications(result)
```

    

