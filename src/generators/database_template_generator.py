"""Generator for database TMDL files."""
from typing import Dict, Any, Optional
from pathlib import Path

from .base_template_generator import BaseTemplateGenerator

class DatabaseTemplateGenerator(BaseTemplateGenerator):
    """Generator for database TMDL files."""
    
    def generate_database_tmdl(self, database_info: Dict[str, Any], output_dir: Optional[Path] = None) -> Path:
        """Generate database.tmdl file.
        
        Args:
            database_info: Database configuration data
            output_dir: Optional output directory override
            
        Returns:
            Path to generated file
        """
        if output_dir:
            self.output_dir = output_dir
            
        return self.generate_file('database', database_info)
