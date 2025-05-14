"""Generator for model TMDL files."""
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import json

from .base_template_generator import BaseTemplateGenerator
from .table_template_generator import TableTemplateGenerator
from config.data_classes import PowerBiModel, PowerBiTable

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
            self.output_dir = output_dir.parent
            self.pbit_dir = output_dir
            self.extracted_dir = self.output_dir / 'extracted'
            
            # Update table generator paths
            self.table_generator.output_dir = self.output_dir
            self.table_generator.pbit_dir = self.pbit_dir
            self.table_generator.extracted_dir = self.extracted_dir
        
        # Prepare template data
        template_data = {
            'model_name': model.model_name,
            'default_culture': model.culture,  # Use same culture for both
            'source_culture': model.culture,
            # No need to convert data access options to strings since they are flags
            'legacy_redirects': model.data_access_options.legacy_redirects,
            'return_null_errors': model.data_access_options.return_error_values_as_null,
            # Convert query order list to JSON string
            'query_order_list': json.dumps(model.query_order),
            # Convert boolean to 1/0 for time intelligence
            'time_intelligence_enabled': '1' if model.time_intelligence_enabled else '0',
            # Add desktop version if available
            'desktop_version': getattr(model, 'desktop_version', None),
            # Add table references with proper spacing
            'tables': [table.source_name.strip() for table in tables]
        }
        
        # Generate model.tmdl
        model_path = self.generate_file('model', template_data)
        
        # Generate table TMDL files using table generator
        table_paths = self.table_generator.generate_all_tables(tables)
        
        return model_path, table_paths
