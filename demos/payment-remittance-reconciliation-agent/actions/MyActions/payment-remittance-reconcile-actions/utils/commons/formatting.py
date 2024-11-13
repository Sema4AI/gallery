from typing import Any, Dict, Optional, Union
from decimal import Decimal


def format_currency(
    amount: Union[float, Decimal, int],
    currency_symbol: str = "$",
    decimal_places: int = 2,
) -> str:
    """
    Format a number as currency with thousands separator and fixed decimal places.

    Args:
        amount: The amount to format
        currency_symbol: Currency symbol to use (default: $)
        decimal_places: Number of decimal places to show (default: 2)

    Returns:
        str: Formatted currency string

    Examples:
        >>> format_currency(1234567.89)
        '$1,234,567.89'
        >>> format_currency(-1234.56, '£')
        '-£1,234.56'
        >>> format_currency(1000)
        '$1,000.00'
    """
    try:
        # Convert to float in case we get a string or Decimal
        amount = float(amount)

        # Handle negative amounts
        is_negative = amount < 0
        abs_amount = abs(amount)

        # Format with comma as thousands separator and fixed decimal places
        formatted = f"{abs_amount:,.{decimal_places}f}"

        # Add currency symbol and handle negative sign
        if is_negative:
            return f"-{currency_symbol}{formatted}"
        return f"{currency_symbol}{formatted}"

    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid amount for currency formatting: {amount}") from e


def format_percentage(
    value: Union[float, Decimal, int],
    decimal_places: int = 2,
    include_symbol: bool = True,
) -> str:
    """
    Format a number as a percentage with fixed decimal places.

    Args:
        value: The value to format (e.g., 0.156 for 15.6%)
        decimal_places: Number of decimal places to show (default: 2)
        include_symbol: Whether to include the % symbol (default: True)

    Returns:
        str: Formatted percentage string

    Examples:
        >>> format_percentage(0.1567)
        '15.67%'
        >>> format_percentage(1.45, decimal_places=1)
        '145.0%'
        >>> format_percentage(0.0872, include_symbol=False)
        '8.72'
    """
    try:
        # Convert to float and multiply by 100 for percentage
        percentage = float(value) * 100

        # Format with fixed decimal places
        formatted = f"{percentage:.{decimal_places}f}"

        # Remove trailing zeros after decimal point if any
        if "." in formatted:
            formatted = formatted.rstrip("0").rstrip(".")

        # Add percentage symbol if requested
        if include_symbol:
            return f"{formatted}%"
        return formatted

    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid value for percentage formatting: {value}") from e


def format_number(
    value: Union[float, Decimal, int],
    decimal_places: int = None,
    thousands_separator: bool = True,
) -> str:
    """
    Format a number with optional decimal places and thousands separator.

    Args:
        value: The number to format
        decimal_places: Number of decimal places (None for auto)
        thousands_separator: Whether to include thousands separator

    Returns:
        str: Formatted number string

    Examples:
        >>> format_number(1234567.89)
        '1,234,567.89'
        >>> format_number(1234.5678, decimal_places=3)
        '1,234.568'
        >>> format_number(1234, thousands_separator=False)
        '1234'
    """
    try:
        value = float(value)

        # Format with specified decimal places
        if decimal_places is not None:
            formatted = f"{value:.{decimal_places}f}"
        else:
            formatted = str(value)

        # Add thousands separator if requested
        if thousands_separator:
            parts = formatted.split(".")
            parts[0] = "{:,}".format(int(parts[0]))
            formatted = ".".join(parts)

        return formatted

    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid value for number formatting: {value}") from e


def format_usage(
    amount: Union[float, Decimal, int],
    unit: str,
    decimal_places: int = 2,
    thousands_separator: bool = True,
) -> str:
    """
    Format a usage amount with unit.

    Args:
        amount: The usage amount
        unit: The unit of measurement (e.g., kWh, Gallons)
        decimal_places: Number of decimal places
        thousands_separator: Whether to include thousands separator

    Returns:
        str: Formatted usage string

    Examples:
        >>> format_usage(1234567.89, 'kWh')
        '1,234,567.89 kWh'
        >>> format_usage(1234.5, 'Gallons', decimal_places=1)
        '1,234.5 Gallons'
    """
    try:
        formatted_amount = format_number(
            amount,
            decimal_places=decimal_places,
            thousands_separator=thousands_separator,
        )
        return f"{formatted_amount} {unit}"

    except ValueError as e:
        raise ValueError(f"Invalid amount for usage formatting: {amount}") from e


def parse_numeric_field(value: Any) -> float:
    """
    Helper to consistently parse numeric fields

    Handles various input formats:
    - Float/integer values
    - String values with currency symbols ($)
    - String values with commas as thousand separators

    Args:
        value: The value to parse, can be string, float, int or None

    Returns:
        float: The parsed numeric value
    """
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Remove currency symbol and commas
        clean_value = value.strip().replace("$", "").replace(",", "")
        return float(clean_value)
    return 0.0


from decimal import InvalidOperation
from utils.commons.decimal_utils import DecimalHandler


def parse_threshold(threshold_str: str) -> Decimal:
    """
    Safely parse threshold string to Decimal using DecimalHandler.

    Args:
        threshold_str: String representation of threshold (e.g., "0.01", "1%", "")

    Returns:
        Decimal: Parsed threshold value with consistent precision

    Raises:
        ValueError: If threshold is invalid
    """
    # Default threshold if empty string
    if not threshold_str:
        return DecimalHandler.from_str("0.01")

    try:
        # Remove % sign if present
        clean_str = threshold_str.strip().replace("%", "")

        # Convert to Decimal with consistent handling
        threshold_decimal = DecimalHandler.from_str(clean_str)

        # If given as percentage (e.g., "1" for 1%), convert to decimal
        if threshold_decimal > DecimalHandler.from_str("1"):
            threshold_decimal = DecimalHandler.calc_percentage(
                DecimalHandler.from_str("1"),
                threshold_decimal / DecimalHandler.from_str("100"),
            )

        # Validate range
        if threshold_decimal <= DecimalHandler.from_str("0"):
            raise ValueError("Threshold must be positive")

        return threshold_decimal

    except (InvalidOperation, ValueError) as e:
        raise ValueError(
            f"Invalid threshold value: {threshold_str}. Must be a positive number or percentage."
        )


# First create a data cleaning utility class
class DatabaseDataCleaner:
    """Utility class for cleaning and standardizing database input data."""

    @staticmethod
    def clean_string(value: Optional[str]) -> Optional[str]:
        """Clean string values by trimming whitespace and standardizing None values."""
        if value is None:
            return None
        return str(value).strip()

    @staticmethod
    def clean_customer_data(customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean customer-related data fields."""
        return {
            "customer_id": DatabaseDataCleaner.clean_string(
                customer_data["customer_id"]
            ),
            "customer_name": DatabaseDataCleaner.clean_string(
                customer_data["customer_name"]
            ),
            "account_number": DatabaseDataCleaner.clean_string(
                customer_data["account_number"]
            ),
        }

    @staticmethod
    def clean_facility_data(facility_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean facility-related data fields."""
        return {
            "facility_id": DatabaseDataCleaner.clean_string(
                facility_data["facility_id"]
            ),
            "facility_name": DatabaseDataCleaner.clean_string(
                facility_data["facility_name"]
            ),
            "facility_type": DatabaseDataCleaner.clean_string(
                facility_data["facility_type"]
            ),
            "customer_id": DatabaseDataCleaner.clean_string(
                facility_data["customer_id"]
            ),
        }

    @staticmethod
    def clean_invoice_data(invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean invoice-related data fields."""
        return {
            "invoice_number": DatabaseDataCleaner.clean_string(
                invoice_data["invoice_number"]
            ),
            "customer_id": DatabaseDataCleaner.clean_string(
                invoice_data["customer_id"]
            ),
            "facility_id": DatabaseDataCleaner.clean_string(
                invoice_data["facility_id"]
            ),
            "facility_type": DatabaseDataCleaner.clean_string(
                invoice_data["facility_type"]
            ),
            "service_type": DatabaseDataCleaner.clean_string(
                invoice_data.get("service_type")
            ),
            "usage_unit": DatabaseDataCleaner.clean_string(
                invoice_data.get("usage_unit")
            ),
            "status": DatabaseDataCleaner.clean_string(invoice_data["status"]),
            # Preserve numeric fields
            "invoice_amount": invoice_data["invoice_amount"],
            "additional_charges": invoice_data.get("additional_charges"),
            "discounts_applied": invoice_data.get("discounts_applied"),
            "amount_paid": invoice_data.get("amount_paid", 0),
            "usage_amount": invoice_data.get("usage_amount"),
            "co2_supplementation": invoice_data.get("co2_supplementation"),
        }
