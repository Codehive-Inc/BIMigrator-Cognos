"""Generator for model TMDL files."""
from typing import Dict, Any, Optional, List
from pathlib import Path
import json

from .base_template_generator import BaseTemplateGenerator
from config.data_classes import PowerBiModel, PowerBiTable

class ModelTemplateGenerator(BaseTemplateGenerator):
    """Generator for model TMDL files."""
    
    def generate_model_tmdl(self, model: PowerBiModel, output_dir: Optional[Path] = None) -> Path:
        """Generate model.tmdl file.
        
        Args:
            model: PowerBiModel instance
            output_dir: Optional output directory override
            
        Returns:
            Path to generated file
        """
        if output_dir:
            self.output_dir = output_dir
        
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
        
        # Generate table TMDL files
        for table in model.tables:
            self.generate_table_tmdl(table)
        
        return model_path
    
    def generate_table_tmdl(self, table: str) -> Path:
        """Generate table TMDL file.
        
        Args:
            table: Table name
            
        Returns:
            Path to generated file
        """
        # Prepare template data
        template_data = {
            'name': table,  # Use table name directly
            'source_name': table,  # Use same name for source
            'columns': []  # Empty columns list since we handle columns separately
        }
        
        # Use table name for file name
        return self.generate_file('table', template_data, name=table)
