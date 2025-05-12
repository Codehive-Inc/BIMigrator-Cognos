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
        print(f'\nDebug: Processing columns for table {table.source_name}')
        columns_data = []
        for column in table.columns:
            print(f'Debug: Column data - source_name: {column.source_name}, datatype: {column.pbi_datatype}')
            column_data = {
                'source_name': column.source_name,
                'datatype': column.pbi_datatype,
                'format_string': column.format_string,
                'lineage_tag': column.lineage_tag if hasattr(column, 'lineage_tag') else None,
                'source_column': column.source_column,
                'description': column.description,
                'is_hidden': column.is_hidden,
                'data_category': column.dataCategory if hasattr(column, 'dataCategory') else None
            }
            columns_data.append(column_data)
            
        # Prepare measure data
        print(f'\nDebug: Processing measures for table {table.source_name}')
        measures_data = []
        for measure in table.measures:
            print(f'Debug: Measure data - source_name: {measure.source_name}, expression: {measure.dax_expression}')
            measure_data = {
                'source_name': measure.source_name,
                'expression': measure.dax_expression,
                'format_string': measure.format_string,
                'description': measure.description,
                'is_hidden': measure.is_hidden
            }
            measures_data.append(measure_data)
            
        # Prepare hierarchy data
        print(f'\nDebug: Processing hierarchies for table {table.source_name}')
        hierarchies_data = []
        for hierarchy in table.hierarchies:
            print(f'Debug: Hierarchy data - name: {hierarchy.name}')
            # Prepare level data
            levels_data = []
            for level in hierarchy.levels:
                print(f'Debug: Level data - name: {level.name}, column: {level.column_name}')
                level_data = {
                    'source_name': level.name,
                    'column_name': level.column_name
                }
                levels_data.append(level_data)
                
            hierarchy_data = {
                'source_name': hierarchy.name,
                'description': hierarchy.description,
                'is_hidden': hierarchy.is_hidden,
                'levels': levels_data
            }
            hierarchies_data.append(hierarchy_data)
            
        # Prepare template data
        print(f'\nDebug: Preparing template data for table {table.source_name}')
        template_data = {
            'source_name': table.source_name,
            'lineage_tag': table.lineage_tag if hasattr(table, 'lineage_tag') else None,
            'description': table.description,
            'is_hidden': table.is_hidden,
            'columns': columns_data,
            'measures': measures_data,
            'hierarchies': hierarchies_data,
            # Add widget serialization if needed
            'has_widget_serialization': False,  # Set to True if needed
            'visual_type': None,
            'column_settings': None
        }
        print(f'Debug: Template data - source_name: {template_data["source_name"]}')
        print(f'Debug: Template data - columns: {len(columns_data)}, measures: {len(measures_data)}, hierarchies: {len(hierarchies_data)}')
        
        # Generate table.tmdl in tables subdirectory
        tables_dir = self.output_dir / 'tables'
        tables_dir.mkdir(exist_ok=True)
        # Add name to template_data for handlebars
        template_data['name'] = template_data['source_name']
        print(f'Debug: Added name to template data: {template_data["name"]}')
        return self.generate_file('table', template_data, name=table.source_name)
    
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
            print(f'\nDebug: Processing table {i}/{len(tables)}: {table.source_name}')
            try:
                table_path = self.generate_table_tmdl(table)
                print(f'Debug: Generated TMDL file: {table_path}')
                table_paths.append(table_path)
            except Exception as e:
                print(f'Debug: Error generating TMDL for table {table.source_name}: {str(e)}')
                raise
        
        print(f'\nDebug: Successfully generated {len(table_paths)} table TMDL files')
        return table_paths
