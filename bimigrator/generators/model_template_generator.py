"""Generator for model TMDL files."""
import json
from pathlib import Path
from typing import Optional, List, Tuple, Any

from bimigrator.config.data_classes import PowerBiModel, PowerBiTable
from .base_template_generator import BaseTemplateGenerator
from .table_template_generator import TableTemplateGenerator


class ModelTemplateGenerator(BaseTemplateGenerator):
    """Generator for model TMDL files."""

    def __init__(self, config: dict[str,Any], input_path: Optional[str] = None, output_dir: Optional[Path] = None):
        super().__init__(config, input_path, output_dir)
        self.table_generator = TableTemplateGenerator(config, input_path, output_dir)

    def generate_model_tmdl(self, model: PowerBiModel, tables: List[PowerBiTable], output_dir: Optional[Path] = None) -> \
    Tuple[Path, List[Path]]:
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
            # Format query order list with table names, using raw strings to avoid HTML encoding
            'query_order_list': json.dumps([table.source_name.strip() for table in tables],
                                           ensure_ascii=False) if tables else '[]',
            # Convert boolean to 1/0 for time intelligence
            'time_intelligence_enabled': '1' if model.time_intelligence_enabled else '0',
            # Add desktop version if available
            'desktop_version': getattr(model, 'desktop_version', None),
            # Add table references with proper spacing
            'tables': [table.source_name.strip() for table in tables]
        }

        # Generate model.tmdl
        model_path = self.generate_file('model', template_data)

        # Get paths of already generated table TMDL files
        table_paths = []
        for table in tables:
            table_file = self.pbit_dir / 'Model' / 'tables' / f'{table.source_name}.tmdl'
            if table_file.exists():
                table_paths.append(table_file)

        return model_path, table_paths
