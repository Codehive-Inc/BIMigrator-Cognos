"""Generator for table TMDL files."""
from typing import Dict, Any, Optional, List
from pathlib import Path
import json

from .base_template_generator import BaseTemplateGenerator
from config.dataclasses import PowerBiTable, PowerBiColumn, PowerBiMeasure, PowerBiHierarchy

class TableTemplateGenerator(BaseTemplateGenerator):
    """Generator for table TMDL files."""
    
    def generate_table_tmdl(self, table: PowerBiTable, output_dir: Optional[Path] = None) -> Path:
        """Generate table.tmdl file.
        
        Args:
            table: PowerBiTable instance
            output_dir: Optional output directory override
            
        Returns:
            Path to generated file
        """
        if output_dir:
            self.output_dir = output_dir
            
        # Prepare column data
        columns_data = []
        for column in table.columns:
            column_data = {
                'name': column.name,
                'datatype': column.datatype,
                'format_string': column.format_string,
                'lineage_tag': column.lineage_tag,
                'source_column': column.source_column,
                'description': column.description,
                'is_hidden': column.is_hidden,
                'data_category': column.data_category if hasattr(column, 'data_category') else None
            }
            columns_data.append(column_data)
            
        # Prepare measure data
        measures_data = []
        for measure in table.measures:
            measure_data = {
                'name': measure.name,
                'expression': measure.expression,
                'format_string': measure.format_string,
                'description': measure.description,
                'is_hidden': measure.is_hidden
            }
            measures_data.append(measure_data)
            
        # Prepare hierarchy data
        hierarchies_data = []
        for hierarchy in table.hierarchies:
            # Prepare level data
            levels_data = []
            for level in hierarchy.levels:
                level_data = {
                    'name': level.name,
                    'column_name': level.column_name,
                    'ordinal': level.ordinal
                }
                levels_data.append(level_data)
                
            hierarchy_data = {
                'name': hierarchy.name,
                'description': hierarchy.description,
                'is_hidden': hierarchy.is_hidden,
                'levels': levels_data
            }
            hierarchies_data.append(hierarchy_data)
            
        # Prepare template data
        template_data = {
            'name': table.name,
            'lineage_tag': table.lineage_tag,
            'description': table.description if hasattr(table, 'description') else None,
            'is_hidden': table.is_hidden if hasattr(table, 'is_hidden') else False,
            'columns': columns_data,
            'measures': measures_data,
            'hierarchies': hierarchies_data,
            # Add widget serialization if needed
            'has_widget_serialization': False,  # Set to True if needed
            'visual_type': None,
            'column_settings': None
        }
        
        # Generate table.tmdl in tables subdirectory
        tables_dir = self.output_dir / 'tables'
        tables_dir.mkdir(exist_ok=True)
        return self.generate_file('table', template_data, name=table.name, output_dir=tables_dir)
    
    def generate_all_tables(self, tables: List[PowerBiTable], output_dir: Optional[Path] = None) -> List[Path]:
        """Generate TMDL files for all tables.
        
        Args:
            tables: List of PowerBiTable instances
            output_dir: Optional output directory override
            
        Returns:
            List of paths to generated files
        """
        print('\nDebug: Generating table TMDL files...')
        if output_dir:
            self.output_dir = output_dir
            print(f'Debug: Using output directory: {output_dir}')
        
        print(f'Debug: Processing {len(tables)} tables')
        table_paths = []
        for i, table in enumerate(tables, 1):
            print(f'\nDebug: Processing table {i}/{len(tables)}: {table.name}')
            try:
                table_path = self.generate_table_tmdl(table)
                print(f'Debug: Generated TMDL file: {table_path}')
                table_paths.append(table_path)
            except Exception as e:
                print(f'Debug: Error generating TMDL for table {table.name}: {str(e)}')
                raise
        
        print(f'\nDebug: Successfully generated {len(table_paths)} table TMDL files')
        return table_paths
