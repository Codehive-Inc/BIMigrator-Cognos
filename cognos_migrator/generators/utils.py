"""
Utility functions for generators.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union


def get_extracted_dir(dir_path: Path) -> Optional[Path]:
    """
    Get the extracted directory path based on the given directory path.
    
    Args:
        dir_path: Directory path to check
        
    Returns:
        Path to the extracted directory if applicable, None otherwise
    """
    # Check if we should save extracted files
    if dir_path.parent and dir_path.parent.name == 'pbit':
        # Navigate up to get to the output directory
        output_dir = dir_path.parent.parent
        extracted_dir = output_dir / 'extracted'
        extracted_dir.mkdir(exist_ok=True)
        return extracted_dir
    return None


def save_json_to_extracted_dir(extracted_dir: Path, filename: str, data: Dict[str, Any]) -> None:
    """
    Save JSON data to a file in the extracted directory.
    
    Args:
        extracted_dir: Path to the extracted directory
        filename: Name of the file to save
        data: JSON data to save
    """
    json_file = extracted_dir / filename
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
