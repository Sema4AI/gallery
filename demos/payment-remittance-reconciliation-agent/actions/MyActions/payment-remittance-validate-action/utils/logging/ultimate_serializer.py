from decimal import Decimal
from enum import Enum
import json
import numpy as np
import pandas as pd
from pydantic import BaseModel
from datetime import date, datetime, time
from typing import Any, Union


class SerializableJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)  # or str(obj) if you prefer string representation
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (pd.DataFrame, pd.Series)):
            return obj.to_dict()
        elif isinstance(obj, (date, datetime)):
            return obj.isoformat()
        elif isinstance(obj, time):
            return obj.isoformat()
        elif isinstance(obj, Enum):
            return obj.value
        elif pd.isna(obj):
            return None
        return super().default(obj)


def clean_any_object_safely(obj: Any) -> Any:
    """
    Clean a Pydantic object or any nested structure to ensure all data is serializable.
    """
    if isinstance(obj, BaseModel):
        return clean_any_object_safely(obj.dict())
    elif isinstance(obj, dict):
        return {k: clean_any_object_safely(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_any_object_safely(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(clean_any_object_safely(item) for item in obj)
    elif isinstance(obj, (date, datetime)):
        return obj.isoformat()
    elif isinstance(obj, time):
        return obj.isoformat()
    elif isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (pd.DataFrame, pd.Series)):
        return obj.to_dict()
    elif pd.isna(obj):
        return None
    return obj    


def serialize_any_object_safely(obj: Any, indent: int = 4) -> str:
    """
    Clean and serialize any object (Pydantic or not) to a JSON string.

    This function will:
    1. Clean the object (if it's a Pydantic model or contains Pydantic models)
    2. Serialize the cleaned object to JSON

    Args:
        obj (Any): The object to serialize. Can be a Pydantic model, dict, list, or any serializable type.
        indent (int, optional): Number of spaces for indentation in the resulting JSON.

    Returns:
        str: A JSON string representation of the cleaned and serialized object.
    """
    cleaned_obj = clean_any_object_safely(obj)
    return json.dumps(cleaned_obj, cls=SerializableJSONEncoder, indent=indent)




#E.g: Example Usage
#logger.debug(serialize_pydantic(extraction_result, indent=4))