"""Generator for model TMDL files."""
from typing import Dict, Any, Optional, List
from pathlib import Path

from .base_template_generator import BaseTemplateGenerator

class ModelTemplateGenerator(BaseTemplateGenerator):
    """Generator for model TMDL files."""
    
    def generate_model_tmdl(self, model_info: Dict[str, Any], output_dir: Optional[Path] = None) -> Path:
        """Generate model.tmdl file.
        
        Args:
            model_info: Model configuration data
            output_dir: Optional output directory override
            
        Returns:
            Path to generated file
        """
        if output_dir:
            self.output_dir = output_dir
            
        return self.generate_file('model', model_info)
