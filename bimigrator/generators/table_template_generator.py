"""Generator for table TMDL files."""
import json
from typing import Dict, Any, Optional, List
from pathlib import Path

from bimigrator.config.data_classes import PowerBiTable
from .base_template_generator import BaseTemplateGenerator


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
            self.output_dir = output_dir.parent
            self.pbit_dir = output_dir
            self.extracted_dir = self.output_dir / 'extracted'

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
                'summarize_by': column.summarize_by if hasattr(column, 'summarize_by') else None,
                'data_category': column.dataCategory if hasattr(column, 'dataCategory') else None,
                # Add new properties for calculated columns
                'is_calculated': column.is_calculated if hasattr(column, 'is_calculated') else False,
                'is_data_type_inferred': column.is_data_type_inferred if hasattr(column,
                                                                                 'is_data_type_inferred') else False,
                'annotations': column.annotations if hasattr(column, 'annotations') and column.annotations else None
            }

            # Debug output for calculated columns
            if column_data['is_calculated']:
                print(
                    f"Debug: Column '{column.source_name}' is a calculated column with type=calculated and isDataTypeInferred={column_data['is_data_type_inferred']}")
                if column_data['annotations']:
                    print(f"Debug: Column '{column.source_name}' has annotations: {column_data['annotations']}")

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
        # Prepare partition data
        print(f'\nDebug: Processing partitions for table {table.source_name}')
        partitions_data = []
        for partition in table.partitions:
            print(f'Debug: Partition data - name: {partition.name}, source_type: {partition.source_type}')
            partition_data = {
                'name': partition.name,
                'source_type': partition.source_type,
                'expression': partition.expression
            }
            partitions_data.append(partition_data)

        # Use consistent table name throughout
        template_data = {
            'source_name': table.source_name,
            'name': table.source_name,  # Use source_name directly
            'lineage_tag': table.lineage_tag if hasattr(table, 'lineage_tag') else None,
            'description': table.description,
            'is_hidden': table.is_hidden,
            'columns': columns_data,
            'measures': measures_data,
            'hierarchies': hierarchies_data,
            'partitions': partitions_data,
            # Add widget serialization if needed
            'has_widget_serialization': False,  # Set to True if needed
            'visual_type': None,
            'column_settings': None
        }
        print(f'Debug: Template data - table name: {template_data["name"]}')
        print(
            f'Debug: Template data - columns: {len(columns_data)}, measures: {len(measures_data)}, hierarchies: {len(hierarchies_data)}')

        # Generate the file with consistent table name
        return self.generate_file('table', template_data, name=table.source_name)

    def generate_all_tables(self, tables: List[PowerBiTable], relationships: Optional[List[Dict[str, Any]]] = None, output_dir: Optional[Path] = None) -> List[Path]:
        """Generate TMDL files for all tables.
        
        Args:
            tables: List of PowerBiTable instances
            relationships: Optional list of relationship dictionaries
            output_dir: Optional output directory override
            
        Returns:
            List of paths to generated files
        """
        print('\nDebug: Generating table TMDL files...')
        if output_dir:
            self.output_dir = output_dir.parent
            self.pbit_dir = output_dir
            self.extracted_dir = self.output_dir / 'extracted'
            print(f'Debug: Using output directory: {output_dir}')

        # Get tables referenced in relationships
        relationship_tables = set()
        if relationships:
            for rel in relationships:
                relationship_tables.add(rel.from_table)
                relationship_tables.add(rel.to_table)
                print(f'Debug: Found relationship table: {rel.from_table} -> {rel.to_table}')

        # Create a dictionary to track unique table names
        # This ensures we don't generate duplicate TMDL files for tables with the same name
        unique_tables = {}
        for table in tables:
            # Always keep tables that are referenced in relationships
            if table.source_name in relationship_tables:
                unique_tables[table.source_name] = table
                print(f'Debug: Keeping table {table.source_name} (referenced in relationships)')
            # For other tables, use complexity-based deduplication
            elif table.source_name in unique_tables:
                existing_table = unique_tables[table.source_name]
                existing_complexity = len(existing_table.columns) + len(existing_table.measures)
                new_complexity = len(table.columns) + len(table.measures)

                if new_complexity > existing_complexity:
                    # Replace with the more complex table
                    unique_tables[table.source_name] = table
                    print(f'Debug: Replacing table {table.source_name} with more complex version')
            else:
                unique_tables[table.source_name] = table

        # Use the unique tables dictionary
        unique_table_list = list(unique_tables.values())
        print(f'Debug: Processing {len(unique_table_list)} unique tables (including {len(relationship_tables)} from relationships)')

        table_paths = []
        for i, table in enumerate(unique_table_list, 1):
            print(f'\nDebug: Processing table {i}/{len(unique_table_list)}: {table.source_name}')
            
            # Skip empty tables (tables with no columns, measures, hierarchies, or partitions)
            if not table.columns and not table.measures and not table.hierarchies and not table.partitions:
                print(f'Debug: Skipping empty table {table.source_name} - no columns, measures, hierarchies, or partitions')
                continue
                
            # Skip tables that only have a single "id" column that was created for relationships
            if len(table.columns) == 1 and table.columns[0].source_name == 'id' and not table.measures and not table.hierarchies and not table.partitions:
                print(f'Debug: Skipping table {table.source_name} - only has a mock "id" column')
                continue
                
            # Skip tables that have partitions but no columns or measures
            if not table.columns and not table.measures and table.partitions:
                print(f'Debug: Skipping table {table.source_name} - has partitions but no columns or measures')
                continue
                
            try:
                table_path = self.generate_table_tmdl(table)
                print(f'Debug: Generated TMDL file: {table_path}')
                table_paths.append(table_path)
            except Exception as e:
                print(f'Debug: Error generating TMDL for table {table.source_name}: {str(e)}')
                raise

        print(f'\nDebug: Successfully generated {len(table_paths)} table TMDL files')
        return table_paths
