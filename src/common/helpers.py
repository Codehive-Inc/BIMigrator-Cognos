import io
import json
import zipfile
from pathlib import Path
from typing import Dict, Any

import yaml


def zip_directory(path: Path):
    buffer = io.BytesIO()
    files = path.rglob('*')
    with zipfile.ZipFile(
            buffer, 'w',
            compression=zipfile.ZIP_LZMA,
            allowZip64=True
    ) as zipped:
        for file in files:
            zipped.write(file, arcname=file.relative_to(path.parent))
    return buffer


def load_config(path: str) -> Dict[str, Any]:
    """Load configuration from YAML or JSON file."""
    with open(path, 'r') as f:
        if path.endswith('.yaml') or path.endswith('.yml'):
            return yaml.safe_load(f)
        return json.load(f)
