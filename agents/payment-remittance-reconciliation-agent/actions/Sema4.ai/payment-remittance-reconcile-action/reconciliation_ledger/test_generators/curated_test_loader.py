from pathlib import Path
import json
from typing import Dict, List, Optional

from reconciliation_ledger.db.invoice_loader import InvoiceLoader
from reconciliation_ledger.reconciliation_constants import BASE_ACTIONS_DIR
from utils.commons.decimal_utils import DecimalJsonEncoder
from utils.logging.reconcile_logging_module import configure_logging
from utils.commons.path_utils import get_full_path

class CuratedTestLoader:
    """
    Client for loading curated test cases into the reconciliation database.
    Traverses through test case folders in the configured curated test cases directory
    and loads their db_setup.json files into the database.
    """
    
    DEFAULT_CURATED_CASES_DIR = f"{BASE_ACTIONS_DIR}reconciliation_ledger/test_generators/curated_test_cases"
    
    def __init__(self, cases_dir: Optional[Path] = None):
        """
        Initialize the loader with optional custom directory path.
        
        Args:
            cases_dir: Optional custom path to curated test cases directory
        """
        self.logger = configure_logging(__name__)
        
        if cases_dir:
            self.cases_dir = Path(cases_dir)
        else:
            self.cases_dir = Path(get_full_path(self.DEFAULT_CURATED_CASES_DIR))
            
        self.invoice_loader = InvoiceLoader()
        self.loaded_cases: Dict[str, Dict] = {}

    def load_all_test_cases(self) -> Dict[str, Dict]:
        """
        Load all curated test cases into the database.
        
        Returns:
            Dict mapping case names to their loaded setup data
        """
        self.logger.info(f"Loading all test cases from: {self.cases_dir}")
        
        try:
            # Initialize database first
            self.invoice_loader.initialize_database()
            
            # Find all test case directories
            case_dirs = [d for d in self.cases_dir.iterdir() if d.is_dir()]
            self.logger.info(f"Found {len(case_dirs)} test cases to load")
            
            # Load each test case
            for case_dir in case_dirs:
                try:
                    case_name = case_dir.name
                    self.logger.info(f"Loading test case: {case_name}")
                    
                    setup = self.invoice_loader.load_test_case(case_dir)
                    self.loaded_cases[case_name] = setup
                    
                    self.logger.info(f"Successfully loaded test case: {case_name}")
                    
                except Exception as case_error:
                    self.logger.error(f"Error loading test case {case_dir.name}: {str(case_error)}")
                    raise
                    
            # # Verify all test cases were loaded correctly
            # self.logger.info("Verifying loaded test cases...")
            # if self.invoice_loader.verify_loaded_data(self.loaded_cases):
            #     self.logger.info("All test cases loaded and verified successfully")
            # else:
            #     raise ValueError("Test case verification failed")
                
            return self.loaded_cases
            
        except Exception as e:
            self.logger.error(f"Failed to load test cases: {str(e)}")
            raise

    def get_loaded_case_details(self) -> List[Dict]:
        """
        Get summary details of all loaded test cases.
        
        Returns:
            List of dicts containing case name, customer info, and invoice counts
        """
        details = []
        
        for case_name, setup in self.loaded_cases.items():
            customer = setup['customer']
            invoice_count = len(setup['invoices'])
            facility_count = len(setup['facilities'])
            
            details.append({
                'case_name': case_name,
                'customer_id': customer['customer_id'],
                'customer_name': customer['customer_name'],
                'invoice_count': invoice_count,
                'facility_count': facility_count
            })
            
        return details

    def verify_case_files(self, case_dir: Path) -> bool:
        """
        Verify that a test case directory contains all required files.
        
        Args:
            case_dir: Path to test case directory
            
        Returns:
            True if all required files exist, False otherwise
        """
        required_files = [
            "db_setup.json",
            "metadata.json",
            "remittance.md"
        ]
        
        try:
            for file_name in required_files:
                file_path = case_dir / file_name
                if not file_path.exists():
                    self.logger.error(f"Missing required file {file_name} in {case_dir}")
                    return False
                if file_path.stat().st_size == 0:
                    self.logger.error(f"Empty file {file_name} in {case_dir}")
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Error verifying case files in {case_dir}: {str(e)}")
            return False
        
    def get_formatted_cases(self, indent: int = 2) -> str:
            """
            Get formatted JSON string of all loaded cases.
            
            Args:
                indent: Number of spaces for indentation
                
            Returns:
                Formatted JSON string of loaded cases
            """
            return json.dumps(self.loaded_cases, cls=DecimalJsonEncoder, indent=indent)

    def get_formatted_details(self, indent: int = 2) -> str:
        """
        Get formatted JSON string of case details.
        
        Args:
            indent: Number of spaces for indentation
            
        Returns:
            Formatted JSON string of case details
        """
        details = self.get_loaded_case_details()
        return json.dumps(details, cls=DecimalJsonEncoder, indent=indent)

    def print_loading_summary(self):
        """Print summary of loaded test cases."""
        details = self.get_loaded_case_details()
        self.logger.info("\n=== Loaded Test Cases Summary ===")
        
        for detail in details:
            self.logger.info(f"\nCase: {detail['case_name']}")
            self.logger.info(f"Customer: {detail['customer_name']} ({detail['customer_id']})")
            self.logger.info(f"Invoices: {detail['invoice_count']}")
            self.logger.info(f"Facilities: {detail['facility_count']}")

if __name__ == "__main__":
    loader = CuratedTestLoader()
    loader.load_all_test_cases()