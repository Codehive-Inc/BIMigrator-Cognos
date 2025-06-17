"""
JSON encoder for model classes
"""
import json
import dataclasses
from datetime import datetime
from typing import Any


class ModelJSONEncoder(json.JSONEncoder):
    """JSON encoder that can handle model classes"""
    
    def default(self, obj: Any) -> Any:
        """Convert object to JSON serializable format"""
        # Handle dataclasses
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
        
        # Handle datetime objects
        if isinstance(obj, datetime):
            return obj.isoformat()
            
        # Let the base class handle other types or raise TypeError
        return super().default(obj)


def model_to_dict(obj: Any) -> Any:
    """Convert a model object to a dictionary recursively"""
    if dataclasses.is_dataclass(obj):
        # Convert dataclass to dict
        result = {}
        for field in dataclasses.fields(obj):
            value = getattr(obj, field.name)
            result[field.name] = model_to_dict(value)
        return result
    elif isinstance(obj, list):
        # Convert list items
        return [model_to_dict(item) for item in obj]
    elif isinstance(obj, dict):
        # Convert dict values
        return {key: model_to_dict(value) for key, value in obj.items()}
    elif isinstance(obj, datetime):
        # Convert datetime to ISO format string
        return obj.isoformat()
    else:
        # Return primitive types as is
        return obj
