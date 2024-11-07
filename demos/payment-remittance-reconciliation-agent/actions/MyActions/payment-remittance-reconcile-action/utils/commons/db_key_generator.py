
import uuid
from typing import List

class DatabaseKeyGenerator:
    """Utility class for generating database primary keys"""
    
    @staticmethod
    def generate_uuid() -> str:
        """
        Generate a UUID-based primary key.
        Returns a string representation of UUID4.
        """
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_composite_key(parts: List[str], separator: str = "_") -> str:
        """
        Generate a composite key from multiple parts.
        
        Args:
            parts (List[str]): List of strings to combine
            separator (str): Separator to use between parts
            
        Returns:
            str: Combined key with separator
            
        Raises:
            ValueError: If no valid parts are provided
        """
        valid_parts = [str(part) for part in parts if part is not None]
        if not valid_parts:
            raise ValueError("No valid parts provided for composite key generation")
        return separator.join(valid_parts)

    @staticmethod
    def generate_payment_id(date_str: str, reference: str) -> str:
        """
        Generate a payment ID using date and reference.
        
        Args:
            date_str (str): Payment date in YYYYMMDD format
            reference (str): Payment reference number
            
        Returns:
            str: Payment ID in format PMT_YYYYMMDD_REFERENCE
        """
        clean_ref = ''.join(c for c in reference if c.isalnum())
        return f"PMT_{date_str}_{clean_ref}"

    @staticmethod
    def generate_allocation_id() -> str:
        """
        Generate an allocation ID.
        Returns a prefixed UUID.
        """
        return f"ALLOC_{str(uuid.uuid4())}"
