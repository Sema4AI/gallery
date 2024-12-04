
from pathlib import Path

from utils.commons.validate_path_utils import get_full_path


COLUMN_INVOICE_NUMBER = "Invoice Number"
COLUMN_INVOICE_DATE = "Invoice Date"
COLUMN_CO2_SUPPLEMENTATION = "CO2 Supplementation"
COLUMN_SUBTOTAL_INVOICE_AMOUNT = "Subtotal Invoice Amount"

CONFIG_FACILITY_NAME_MAPPING_KEY = "facility_name_mapping"
CONFIG_CO2_POLICY_KEY = "co2_policy"
CONFIG_MULTIPLE_FIELD_MAPPING_KEY="multiple_field_mappings" 

COMPUTED_COLUMN_FACILITY_TYPE = "Facility Type"
COMPUTED_TOTAL_INVOICE_AMOUNT_BY_FACILITY_TYPE = "Total Invoice Amount by Facility Type"
COMPUTED_TOTAL_NUMBER_OF_INVOICES_IN_REMITTANCE = "Total Invoices in Remittance"


INVOICE_TABLE_KEY = 'invoice_table'
SUBTOTALS_TABLE_KEY = 'subtotals_table'

class DatabaseConstants:

    VALIDATION_CONTEXT_DB = "validation_context.duckdb"
    VALIDATION_DB_BASE_PATH = "context"

    
    @staticmethod
    def get_validation_db_dir() -> Path:
        """Get the validation database directory path."""
        return Path(get_full_path(DatabaseConstants.VALIDATION_DB_BASE_PATH))


    @staticmethod
    def get_default_validation_db_path() -> str:
        """Get the default validation database path."""
        return str(DatabaseConstants.get_validation_db_dir() / DatabaseConstants.VALIDATION_CONTEXT_DB)
