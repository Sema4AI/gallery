
from enum import Enum
from pathlib import Path

from utils.commons.path_utils import get_full_path


THRESHOLD_DISPREPENCY = .10

class DatabaseConstants:
    
    RECONCILIATION_LEDGER_DB_BASE_PATH = "reconciliation_ledger/db"
    RECONCILIATION_LEDGER_DB = "reconciliation_ledger.duckdb"
    DEFAULT_DDL_NAME = "reconciliation_ledger.ddl"
    COMPUTED_CONTENT_FILE = "computed_content.json"
    
    RECONCILIATION_CONTEXT_DB = "reconciliation_context.duckdb"
    RECONCILIATION_CONTEXT_DB_BASE_PATH = "context"

    
    @staticmethod
    def get_reconciliation_ledger_db_dir() -> Path:
        """Get the reconciliation database directory path."""
        return Path(get_full_path(DatabaseConstants.RECONCILIATION_LEDGER_DB_BASE_PATH))
    
    @staticmethod
    def get_default_reconciliation_ledger_db_path() -> str:
        """Get the default reconciliation database path."""
        return str(DatabaseConstants.get_reconciliation_ledger_db_dir() / DatabaseConstants.RECONCILIATION_LEDGER_DB)
    
    @staticmethod
    def get_reconciliation_context_db_dir() -> Path:
        """Get the reconciliation database directory path."""
        return Path(get_full_path(DatabaseConstants.RECONCILIATION_CONTEXT_DB_BASE_PATH))
        
    @staticmethod
    def get_default_reconciliation_context_db_path() -> str:
        """Get the default reconciliation database path."""
        return str(DatabaseConstants.get_reconciliation_context_db_dir() / DatabaseConstants.RECONCILIATION_CONTEXT_DB)
    


class FolderConstants:
    REFERENCE_DATA = "reference_data"
    WIRE = "wire"
    DB = "db"
    DDL = "ddl"

class TableNames:
    CUSTOMER = "customer"
    FACILITY = "facility"
    INVOICE = "invoice"
    PAYMENT = "payment"
    PAYMENT_ALLOCATION = "payment_allocation"

class DocumentStatus:
    PENDING = "PENDING"
    PAID = "PAID"
    DISCREPENCY = "DISCREPENCY"
    
    
    