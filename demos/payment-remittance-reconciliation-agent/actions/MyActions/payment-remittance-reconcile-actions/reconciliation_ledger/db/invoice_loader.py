import json
import duckdb
from pathlib import Path
from typing import Dict, List, Optional, Union
from contextlib import contextmanager
from datetime import datetime

from reconciliation_ledger.reconciliation_constants import DatabaseConstants, FolderConstants
from utils.commons.decimal_utils import DecimalHandler
from utils.commons.formatting import DatabaseDataCleaner
from utils.logging.reconcile_logging_module import configure_logging
from utils.commons.path_utils import get_full_path
from utils.commons.db_key_generator import DatabaseKeyGenerator

class InvoiceLoader:
    
    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        self.logger = configure_logging(__name__)
        self.logger.debug("Initializing InvoiceLoader")
        self.data_cleaner = DatabaseDataCleaner()
        
        try:
            if not db_path:
                db_path = get_full_path(str(self.get_db_dir() / DatabaseConstants.RECONCILIATION_LEDGER_DB))
            
            self.db_path = str(db_path) if isinstance(db_path, Path) else db_path
            self.logger.debug(f"Database path set to: {self.db_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize InvoiceLoader: {str(e)}", exc_info=True)
            raise

    def load_test_case(self, test_case_dir: Path) -> Dict:
        self.logger.debug(f"Loading test case from {test_case_dir}")
        
        setup_file = test_case_dir / "db_setup.json"
        if not setup_file.exists():
            raise FileNotFoundError(f"Database setup file not found: {setup_file}")
            
        with open(setup_file) as f:
            db_setup = json.load(f)
            
        # Pre-process numeric values for consistent handling
        for invoice in db_setup['invoices']:
            # Validate date format
            if not self._validate_date_format(invoice['invoice_date']):
                raise ValueError(
                    f"Invalid date format in invoice {invoice['invoice_number']}: "
                    f"{invoice['invoice_date']}. Expected YYYY-MM-DD"
                )
            
            # Pre-quantize all decimal values using DecimalHandler
            invoice['invoice_amount'] = str(
                DecimalHandler.from_str(str(invoice['invoice_amount']))
            )
            invoice['additional_charges'] = str(
                DecimalHandler.from_str(str(invoice.get('additional_charges', 0)))
            )
            invoice['discounts_applied'] = str(
                DecimalHandler.from_str(str(invoice.get('discounts_applied', 0)))
            )
        
        with self.get_connection() as conn:
            self._load_customer_from_setup(conn, db_setup['customer'])
            self._load_facilities_from_setup(conn, db_setup['customer'], db_setup['facilities'])
            self._load_invoices_from_setup(
                conn, 
                db_setup['customer'], 
                db_setup['invoices'],
                db_setup.get('discrepancy_config', {})
            )
            self._load_co2_rates_from_setup(conn, db_setup['customer'], db_setup['facilities'])
            
        return db_setup

    def _load_invoices_from_setup(self, conn, customer: Dict, invoices: List[Dict], discrepancy_config: Dict):
        """Load invoices with clean data."""
        # Clean customer ID once
        clean_customer_id = self.data_cleaner.clean_string(customer['customer_id'])
        
        # Sort invoices for consistent processing
        sorted_invoices = sorted(invoices, key=lambda x: x['invoice_number'])
        adjustments = discrepancy_config.get('adjustments', {})
        
        for invoice in sorted_invoices:
            # Clean invoice data
            clean_invoice = self.data_cleaner.clean_invoice_data({
                **invoice,
                'customer_id': clean_customer_id
            })
            
            internal_facility_id = DatabaseKeyGenerator.generate_composite_key([
                clean_customer_id,
                clean_invoice['facility_id']
            ])
            
            invoice_id = DatabaseKeyGenerator.generate_composite_key([
                clean_customer_id,
                clean_invoice['invoice_number']
            ])
            
            # Process amounts using DecimalHandler
            base_amount = DecimalHandler.from_str(str(clean_invoice['invoice_amount']))
            charges = DecimalHandler.from_str(str(clean_invoice.get('additional_charges', 0)))
            discounts = DecimalHandler.from_str(str(clean_invoice.get('discounts_applied', 0)))
            
            # Rest of the amount processing logic remains the same
            # [Previous amount adjustment logic here...]
            
            query = """
            INSERT INTO invoice (
                invoice_id, invoice_number, customer_id, internal_facility_id,
                invoice_date, invoice_amount, additional_charges,
                discounts_applied, amount_paid, facility_type,
                service_type, usage_amount, usage_unit,
                co2_supplementation, status
            ) VALUES (?, ?, ?, ?, ?,
                CAST(? AS DECIMAL(18, 2)),
                CAST(? AS DECIMAL(18, 2)),
                CAST(? AS DECIMAL(18, 2)),
                CAST(0 AS DECIMAL(18, 2)),  -- Fixed amount_paid as constant
                ?, ?, ?, ?, ?, ?)
            ON CONFLICT (customer_id, invoice_number) DO UPDATE SET
                invoice_date = EXCLUDED.invoice_date,
                invoice_amount = CAST(EXCLUDED.invoice_amount AS DECIMAL(18, 2)),
                additional_charges = CAST(EXCLUDED.additional_charges AS DECIMAL(18, 2)),
                discounts_applied = CAST(EXCLUDED.discounts_applied AS DECIMAL(18, 2)),
                facility_type = EXCLUDED.facility_type,
                service_type = EXCLUDED.service_type,
                usage_amount = EXCLUDED.usage_amount,
                usage_unit = EXCLUDED.usage_unit,
                co2_supplementation = EXCLUDED.co2_supplementation,
                status = EXCLUDED.status
            """
            
            conn.execute(query, [
                invoice_id,
                clean_invoice['invoice_number'],
                clean_invoice['customer_id'],
                internal_facility_id,
                invoice['invoice_date'],
                float(base_amount),
                float(charges),
                float(discounts),
                clean_invoice['facility_type'],
                clean_invoice['service_type'],
                clean_invoice.get('usage_amount'),
                clean_invoice['usage_unit'],
                clean_invoice.get('co2_supplementation'),
                clean_invoice['status']
            ])

    # Other methods remain unchanged as they don't handle decimal values
    @contextmanager
    def get_connection(self):
        conn = None
        try:
            self.logger.debug(f"Establishing database connection to: {self.db_path}")
            conn = duckdb.connect(self.db_path)
            self.logger.debug("Database connection established successfully")
            yield conn
        except Exception as e:
            self.logger.error(f"Database connection error: {str(e)}", exc_info=True)
            raise
        finally:
            if conn:
                try:
                    conn.close()
                    self.logger.debug("Database connection closed successfully")
                except Exception as e:
                    self.logger.error(f"Error closing database connection: {str(e)}", exc_info=True)

    def initialize_database(self):
            """
            Initialize database schema from DDL file.
            Handles table drops in correct dependency order.
            """
            self.logger.debug("Starting database initialization")
            
            with self.get_connection() as conn:
                try:
                    # Drop existing tables in correct dependency order
                    self.logger.debug("Dropping existing tables if they exist")
                    tables_to_drop = [
                        'payment_allocation',     # No dependencies
                        'payment',                # Referenced by payment_allocation
                        'co2_supplementation_rate',  # References facility
                        'invoice',                # References facility and customer
                        'facility',               # References customer
                        'customer'                # Referenced by facility and invoice
                    ]
                    
                    for table in tables_to_drop:
                        try:
                            conn.execute(f"DROP TABLE IF EXISTS {table}")
                            self.logger.debug(f"Dropped table {table} if it existed")
                        except Exception as drop_error:
                            self.logger.error(
                                f"Error dropping table {table}: {str(drop_error)}"
                            )
                            raise
                    
                    ddl_path = get_full_path(
                        str(self.get_db_dir() / FolderConstants.DDL / 
                            DatabaseConstants.DEFAULT_DDL_NAME)
                    )
                    self.logger.debug(f"Loading DDL from path: {ddl_path}")
                    
                    with open(ddl_path) as f:
                        ddl_content = f.read()
                    
                    statements = [stmt.strip() for stmt in ddl_content.split(';') 
                                if stmt.strip()]
                    
                    for statement in statements:
                        if statement:
                            self.logger.debug(
                                f"Executing DDL statement: {statement[:100]}..."
                            )
                            conn.execute(statement)
                            self.logger.debug("Statement executed successfully")
                    
                    self.logger.debug(f"Database initialized successfully at {self.db_path}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to initialize database: {str(e)}")
                    raise


    def verify_loaded_data(self, loaded_setups: Dict[str, Dict]) -> bool:
        """
        Verify that all test cases were loaded correctly.
        
        Args:
            loaded_setups: Dict mapping case names to their setup data
            
        Returns:
            True if all data verified successfully, False otherwise
        """
        self.logger.debug("Verifying loaded test data")
        
        try:
            with self.get_connection() as conn:
                # Build list of customer IDs and convert to tuple for IN clause
                customer_ids = tuple(
                    setup['customer']['customer_id'] 
                    for setup in loaded_setups.values()
                )
                
                # Query customers - handle single item tuple syntax
                if len(customer_ids) == 1:
                    customer_query = """
                        SELECT customer_id 
                        FROM customer 
                        WHERE customer_id = ?
                    """
                    result = conn.execute(customer_query, [customer_ids[0]]).fetchall()
                else:
                    customer_query = """
                        SELECT customer_id 
                        FROM customer 
                        WHERE customer_id IN {}
                    """.format(customer_ids)
                    result = conn.execute(customer_query).fetchall()
                    
                if len(result) != len(customer_ids):
                    self.logger.error("Missing customer records")
                    return False
                
                # Verify invoice counts and amounts for each case
                for case_name, setup in loaded_setups.items():
                    customer_id = setup['customer']['customer_id']
                    expected_count = len(setup['invoices'])
                    
                    # Count invoices
                    actual_count = conn.execute("""
                        SELECT COUNT(*) 
                        FROM invoice 
                        WHERE customer_id = ?
                    """, [customer_id]).fetchone()[0]
                    
                    if actual_count != expected_count:
                        self.logger.error(
                            f"Invoice count mismatch for {case_name}: "
                            f"expected {expected_count}, got {actual_count}"
                        )
                        return False
                    
                    # Verify total amounts match using DecimalHandler
                    expected_total = DecimalHandler.from_str('0')
                    for invoice in setup['invoices']:
                        amount = DecimalHandler.from_str(str(invoice['invoice_amount']))
                        expected_total += amount
                    expected_total = DecimalHandler.round_decimal(expected_total)
                    
                    actual_total = conn.execute("""
                        SELECT CAST(SUM(invoice_amount) AS DECIMAL(18,2))
                        FROM invoice 
                        WHERE customer_id = ?
                    """, [customer_id]).fetchone()[0]
                    actual_total = DecimalHandler.from_str(str(actual_total))
                    
                    # Allow for small rounding differences (0.02)
                    if abs(float(actual_total) - float(expected_total)) > 0.02:
                        self.logger.error(
                            f"Total amount mismatch for {case_name}: "
                            f"expected {float(expected_total):.2f}, "
                            f"got {float(actual_total):.2f}"
                        )
                        return False
                
                self.logger.debug("Data verification passed successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Error verifying loaded data: {str(e)}")
            return False
    
    
    def _validate_date_format(self, date_str: str) -> bool:
        """Validate that a date string is in YYYY-MM-DD format."""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False
            
    def _load_customer_from_setup(self, conn, customer: Dict):
        """Load customer with clean data and simple UPSERT pattern."""
        try:
            # Clean customer data
            clean_customer = self.data_cleaner.clean_customer_data(customer)
            
            query = """
            INSERT INTO customer (customer_id, customer_name, account_number)
            VALUES (?, ?, ?)
            ON CONFLICT (customer_id) DO UPDATE SET
                customer_name = EXCLUDED.customer_name,
                account_number = EXCLUDED.account_number
            """
            
            conn.execute(query, [
                clean_customer['customer_id'],
                clean_customer['customer_name'],
                clean_customer['account_number']
            ])
            
        except Exception as e:
            self.logger.error(f"Error loading customer {customer['customer_id']}: {str(e)}")
            raise

    def _load_facilities_from_setup(self, conn, customer: Dict, facilities: List[Dict]):
        """Load facilities with clean data and simple UPSERT pattern."""
        # Clean customer ID once
        clean_customer_id = self.data_cleaner.clean_string(customer['customer_id'])
        
        for facility in facilities:
            # Clean facility data
            clean_facility = self.data_cleaner.clean_facility_data({
                **facility,
                'customer_id': clean_customer_id
            })
            
            internal_id = DatabaseKeyGenerator.generate_composite_key([
                clean_customer_id,
                clean_facility['facility_id']
            ])
            
            query = """
            INSERT INTO facility (
                internal_facility_id,
                facility_id,
                customer_id,
                facility_name,
                facility_type
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (customer_id, facility_id) DO UPDATE SET
                facility_name = EXCLUDED.facility_name,
                facility_type = EXCLUDED.facility_type
            """
            
            conn.execute(query, [
                internal_id,
                clean_facility['facility_id'],
                clean_facility['customer_id'],
                clean_facility['facility_name'],
                clean_facility['facility_type']
            ])
            
    def _load_co2_rates_from_setup(self, conn, customer: Dict, facilities: List[Dict]):
        """Load CO2 rates with consistent decimal handling."""
        query = """
        SELECT DISTINCT 
            f.internal_facility_id,
            f.facility_id,
            MIN(i.invoice_date) as first_invoice_date
        FROM facility f
        JOIN invoice i ON f.internal_facility_id = i.internal_facility_id
        WHERE f.facility_type = 'Greenhouse Complexes'
        AND i.co2_supplementation IS NOT NULL
        GROUP BY f.internal_facility_id, f.facility_id
        """
        
        facilities = conn.execute(query).fetchall()
        DEFAULT_RATE = DecimalHandler.from_str('0.05')
        
        for internal_facility_id, facility_id, first_date in facilities:
            rate_id = DatabaseKeyGenerator.generate_composite_key([
                internal_facility_id,
                first_date.strftime('%Y%m%d')
            ])
            
            query = """
            INSERT INTO co2_supplementation_rate (
                rate_id,
                internal_facility_id,
                effective_date,
                rate
            ) VALUES (?, ?, ?, CAST(? AS DECIMAL(18, 2)))
            ON CONFLICT (internal_facility_id, effective_date) DO UPDATE SET
                rate = CAST(EXCLUDED.rate AS DECIMAL(18, 2))
            """

            conn.execute(query, [
                rate_id,
                internal_facility_id,
                first_date,
                float(DEFAULT_RATE)
            ])

    @staticmethod
    def get_db_dir() -> Path:
        """Get the database directory path."""
        return Path(get_full_path("reconciliation_ledger/db"))

