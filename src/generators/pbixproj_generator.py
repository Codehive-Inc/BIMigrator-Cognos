import json
from pathlib import Path
from typing import Dict, Any, Optional

from config.data_classes import PowerBiProject
from .base_template_generator import BaseTemplateGenerator

class PbixprojGenerator(BaseTemplateGenerator):
    """Generator for .pbixproj.json files"""
    
    def __init__(self, config_path: str, input_path: str, output_dir: Path):
        super().__init__(config_path, input_path, output_dir)
        
    def generate_pbixproj(self, project_info: PowerBiProject, output_dir: Optional[Path] = None) -> Path:
        """Generate .pbixproj.json file
        
        Args:
            project_info: Project configuration data
            output_dir: Optional output directory override
            
        Returns:
            Path to generated file
        """
        if output_dir:
            self.output_dir = output_dir.parent
            self.pbit_dir = output_dir
            self.extracted_dir = self.output_dir / 'extracted'
            
        # Convert PowerBiProject to dict
        project_data = {
            'version': project_info.version,
            'created': project_info.created.isoformat(),
            'lastModified': project_info.last_modified.isoformat()
        }
        
        # Write .pbixproj.json
        output_path = self.pbit_dir / '.pbixproj.json'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(project_data, f, indent=2)
            
        return output_path
