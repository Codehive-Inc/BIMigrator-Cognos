"""Generator for model TMDL files."""
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import json

from .base_template_generator import BaseTemplateGenerator
from .table_template_generator import TableTemplateGenerator
from config.dataclasses import PowerBiModel, PowerBiTable

class ModelTemplateGenerator(BaseTemplateGenerator):
    """Generator for model TMDL files."""
    
    def __init__(self, config_path: str, input_path: Optional[str] = None, output_dir: Optional[Path] = None):
        super().__init__(config_path, input_path, output_dir)
        self.table_generator = TableTemplateGenerator(config_path, input_path, output_dir)
    
    def generate_model_tmdl(self, model: PowerBiModel, tables: List[PowerBiTable], output_dir: Optional[Path] = None) -> Tuple[Path, List[Path]]:
        """Generate model.tmdl file and all table files.
        
        Args:
            model: PowerBiModel instance
            tables: List of PowerBiTable instances
            output_dir: Optional output directory override
            
        Returns:
            Tuple of (model file path, list of table file paths)
        """
        if output_dir:
            self.output_dir = output_dir
            self.table_generator.output_dir = output_dir
        
        # Prepare template data
        template_data = {
            'model_name': model.model_name,
            'default_culture': model.culture,  # Use same culture for both
            'source_culture': model.culture,
            # Convert data access options to strings
            'legacy_redirects': str(model.data_access_options.legacy_redirects).lower(),
            'return_null_errors': str(model.data_access_options.return_error_values_as_null).lower(),
            # Convert query order list to JSON string
            'query_order_list': json.dumps(model.query_order),
            # Convert boolean to string
            'time_intelligence_enabled': str(model.time_intelligence_enabled).lower()
        }
        
        # Generate model.tmdl
        model_path = self.generate_file('model', template_data)
        
        # Generate table TMDL files using table generator
        table_paths = self.table_generator.generate_all_tables(tables)
        
        return model_path, table_paths
