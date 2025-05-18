"""Generator for TMDL files in Power BI."""
import os
from typing import Dict, Any, List
from pathlib import Path

from config.data_classes import PowerBiTable


class TMDLGenerator:
    """Generator for TMDL files in Power BI."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the TMDL generator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
    def generate_table_tmdl(self, table: PowerBiTable) -> str:
        """Generate TMDL content for a table.
        
        Args:
            table: PowerBiTable object containing table information
            
        Returns:
            TMDL content as string
        """
        tmdl_lines = [
            'table {',
            f'    name: "{table.name}"'
        ]
        
        # Add description if present
        if table.description:
            tmdl_lines.append(f'    description: "{table.description}"')
            
        # Add columns section if there are columns
        if table.columns:
            tmdl_lines.append('    columns: {')
            for col in table.columns:
                tmdl_lines.append(f'        {col.name}: {{')
                tmdl_lines.append(f'            dataType: {col.pbi_datatype}')
                if col.source_name:
                    tmdl_lines.append(f'            sourceName: "{col.source_name}"')
                if col.description:
                    tmdl_lines.append(f'            description: "{col.description}"')
                if col.expression:
                    tmdl_lines.append(f'            expression: "{col.expression}"')
                tmdl_lines.append('        }')
            tmdl_lines.append('    }')
            
        # Add measures section if there are measures
        if table.measures:
            tmdl_lines.append('    measures: {')
            for measure in table.measures:
                tmdl_lines.append(f'        {measure.name}: {{')
                if measure.expression:
                    tmdl_lines.append(f'            expression: "{measure.expression}"')
                if measure.description:
                    tmdl_lines.append(f'            description: "{measure.description}"')
                tmdl_lines.append('        }')
            tmdl_lines.append('    }')
            
        # Add hierarchies section if there are hierarchies
        if table.hierarchies:
            tmdl_lines.append('    hierarchies: {')
            for hierarchy in table.hierarchies:
                tmdl_lines.append(f'        {hierarchy.name}: {{')
                if hierarchy.levels:
                    tmdl_lines.append('            levels: {')
                    for level in hierarchy.levels:
                        tmdl_lines.append(f'                {level.name}: {{')
                        tmdl_lines.append(f'                    ordinal: {level.ordinal}')
                        tmdl_lines.append(f'                    column: "{level.column}"')
                        tmdl_lines.append('                }')
                    tmdl_lines.append('            }')
                tmdl_lines.append('        }')
            tmdl_lines.append('    }')
            
        # Add partitions section if there are partitions
        if table.partitions:
            tmdl_lines.append('    partitions: {')
            for partition in table.partitions:
                tmdl_lines.append(f'        {partition.name}: {{')
                if partition.source_type:
                    tmdl_lines.append(f'            type: {partition.source_type}')
                if partition.expression:
                    # Properly indent M code within the TMDL file
                    m_code_lines = partition.expression.split('\n')
                    if len(m_code_lines) > 1:
                        tmdl_lines.append('            expression: #"')
                        for m_line in m_code_lines:
                            tmdl_lines.append('                ' + m_line)
                        tmdl_lines.append('            "#')
                    else:
                        tmdl_lines.append(f'            expression: "{partition.expression}"')
                if partition.description:
                    tmdl_lines.append(f'            description: "{partition.description}"')
                tmdl_lines.append('        }')
            tmdl_lines.append('    }')
            
        tmdl_lines.append('}')
        
        return '\n'.join(tmdl_lines)
        
    def save_table_tmdl(self, table: PowerBiTable, output_dir: str) -> str:
        """Save a table's TMDL content to a file.
        
        Args:
            table: PowerBiTable object containing table information
            output_dir: Directory to save the TMDL file in
            
        Returns:
            Path to the created TMDL file
        """
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Generate TMDL content
        tmdl_content = self.generate_table_tmdl(table)
        
        # Create file path
        file_path = os.path.join(output_dir, f"{table.name}.tmdl")
        
        # Write TMDL content to file
        with open(file_path, 'w') as f:
            f.write(tmdl_content)
            
        return file_path
        
    def save_all_tables(self, tables: List[PowerBiTable], output_dir: str) -> List[str]:
        """Save multiple tables' TMDL content to files.
        
        Args:
            tables: List of PowerBiTable objects
            output_dir: Directory to save the TMDL files in
            
        Returns:
            List of paths to created TMDL files
        """
        saved_files = []
        for table in tables:
            file_path = self.save_table_tmdl(table, output_dir)
            saved_files.append(file_path)
        return saved_files
