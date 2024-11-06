from pathlib import Path

from utils.commons.path_utils import get_full_path


THRESHOLD_DISPREPENCY = 0.10
# BASE_ACTIONS_DIR = "actions/Sema4.ai/payment-remittance-reconcile-action"
BASE_ACTIONS_DIR = ""

class DatabaseConstants:
    RECONCILIATION_LEDGER_DB_BASE_PATH = f"{BASE_ACTIONS_DIR}reconciliation_ledger/db"
    RECONCILIATION_LEDGER_DDL_BASE_PATH = f"{RECONCILIATION_LEDGER_DB_BASE_PATH}/ddl"

    RECONCILIATION_LEDGER_DB = "reconciliation_ledger.duckdb"
    DEFAULT_DDL_NAME = "reconciliation_ledger.ddl"
    COMPUTED_CONTENT_FILE = "computed_content.json"

    RECONCILIATION_CONTEXT_DB = "reconciliation_context.duckdb"
    RECONCILIATION_CONTEXT_DB_BASE_PATH = f"{BASE_ACTIONS_DIR}context/db"
    

    @staticmethod
    def get_reconciliation_ledger_db_dir() -> Path:
        """Get the reconciliation database directory path."""
        return Path(get_full_path(DatabaseConstants.RECONCILIATION_LEDGER_DB_BASE_PATH))

    @staticmethod
    def get_default_reconciliation_ledger_db_path() -> str:
        """Get the default reconciliation database path."""
        return str(
            DatabaseConstants.get_reconciliation_ledger_db_dir()
            / DatabaseConstants.RECONCILIATION_LEDGER_DB
        )

    @staticmethod
    def get_reconciliation_context_db_dir() -> Path:
        """Get the reconciliation database directory path."""
        return Path(
            get_full_path(DatabaseConstants.RECONCILIATION_CONTEXT_DB_BASE_PATH)
        )

    @staticmethod
    def get_default_reconciliation_context_db_path() -> str:
        """Get the default reconciliation database path."""
        return str(
            DatabaseConstants.get_reconciliation_context_db_dir()
            / DatabaseConstants.RECONCILIATION_CONTEXT_DB
        )
        
        
    @staticmethod
    def get_reconciliation_db_ddl_dir() -> Path:
        """Get the reconciliation database directory path."""
        return Path(
            get_full_path(DatabaseConstants.RECONCILIATION_LEDGER_DDL_BASE_PATH)
        )
        
    @staticmethod
    def get_default_ddl_path() -> str:
        """Get the default DDL file path."""
        return str(
            DatabaseConstants.get_reconciliation_db_ddl_dir()
            / DatabaseConstants.DEFAULT_DDL_NAME
        )


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
