from pathlib import Path
from typing import Dict, Any, Optional
from config.data_classes import PowerBiVersion
from .base_template_generator import BaseTemplateGenerator


class VersionGenerator(BaseTemplateGenerator):
    """Generator for version information."""
    
    def __init__(self, config_path: str, input_path: str, output_dir: Path):
        super().__init__(config_path, input_path, output_dir)
    
    def generate_version(self, version_info: PowerBiVersion, output_dir: Optional[Path] = None) -> Path:
        """Generate the version file."""
        if output_dir:
            self.output_dir = output_dir.parent
            self.pbit_dir = output_dir
            self.extracted_dir = self.output_dir / 'extracted'
        
        return self.generate_file('version', version_info)
