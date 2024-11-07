from decimal import ROUND_HALF_UP, Decimal
import json
from typing import Any

class DecimalHandler:
    """Ensures consistent decimal handling across all components."""
    
    PRECISION = Decimal('0.01')
    ROUNDING = ROUND_HALF_UP
    
    @classmethod
    def from_float(cls, value: float) -> Decimal:
        """Convert float to Decimal with consistent precision."""
        return Decimal(str(value)).quantize(cls.PRECISION, rounding=cls.ROUNDING)
    
    @classmethod
    def from_str(cls, value: str) -> Decimal:
        """Convert string to Decimal with consistent precision."""
        return Decimal(value).quantize(cls.PRECISION, rounding=cls.ROUNDING)
    
    @classmethod
    def round_decimal(cls, value: Decimal) -> Decimal:
        """Round decimal to consistent precision."""
        return value.quantize(cls.PRECISION, rounding=cls.ROUNDING)
    
    @classmethod
    def calc_percentage(cls, value: Decimal, percentage: Decimal) -> Decimal:
        """Calculate percentage with consistent precision."""
        result = value * percentage
        return result.quantize(cls.PRECISION, rounding=cls.ROUNDING)
    
    


class DecimalJsonEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal values."""
    
    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)

