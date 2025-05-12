"""Parser for extracting table information from Tableau workbooks."""
from pathlib import Path
import sys
from typing import Dict, Any, List, Optional
import uuid

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.dataclasses import PowerBiTable, PowerBiColumn, PowerBiMeasure, PowerBiHierarchy, PowerBiHierarchyLevel
from .base_parser import BaseParser

class TableParser(BaseParser):
    """Parser for extracting table information from Tableau workbooks."""
    
    def __init__(self, twb_path: str, config: Dict[str, Any]):
        super().__init__(twb_path, config)
    
    def extract_table_info(self, table_element) -> PowerBiTable:
        """Extract table information from a table element."""
        # Get table template config
        template_config = self.config['Templates']['mappings']['table']
        
        # Get PowerBiTable config for field mappings
        table_config = self.config[template_config['config']]
        print(f'Debug: Table config: {table_config}')
        
        # Extract table attributes
        source_name = self._get_mapping_value(table_config.get('source_name', {}), table_element, '')
        if not source_name:
            print('Debug: Table name is empty')
            return None
            
        print(f'Debug: Processing table {source_name}')
        
        # Extract other table attributes
        description = self._get_mapping_value(table_config.get('description', {}), table_element, None)
        is_hidden = self._get_mapping_value(table_config.get('is_hidden', {}), table_element, False)
        
        # Find column elements
        column_xpath = table_config.get('columns', {}).get('source_xpath', './/column')
        column_elements = self._find_elements(column_xpath)
        print(f'Debug: Found {len(column_elements)} columns')
        
        # Process columns
        columns = []
        for col_elem in column_elements:
            # Skip measure columns
            if col_elem.get('role') == 'measure':
                continue
                
            # Get column name
            col_name = col_elem.get('name')
            if not col_name:
                continue
                
            print(f'Debug: Processing column {col_name}')
            
            # Create column with default values
            column = PowerBiColumn(
                source_name=col_name,
                pbi_datatype='string',
                source_column=col_name
            )
            columns.append(column)
        
        # Process measures
        measures = []
        measure_elements = [e for e in column_elements if e.get('role') == 'measure']
        print(f'Debug: Found {len(measure_elements)} measures')
        
        for measure_elem in measure_elements:
            measure_name = measure_elem.get('name')
            if not measure_name:
                continue
                
            print(f'Debug: Processing measure {measure_name}')
            
            # Create measure with default SUM expression
            measure = PowerBiMeasure(
                source_name=measure_name,
                dax_expression=f'SUM([{measure_name}])'
            )
            measures.append(measure)
        
        # Create PowerBiTable using dataclass
        table = PowerBiTable(
            source_name=source_name,
            description=description,
            is_hidden=is_hidden,
            columns=columns,
            measures=measures,
            hierarchies=[],
            partitions=[],
            annotations={}
        )
        
        return table
    
    def extract_all_tables(self) -> List[PowerBiTable]:
        """Extract all table information from the workbook.
        
        Returns:
            List[PowerBiTable]: List of extracted tables
        """
        print('\nDebug: Extracting tables...')
        mapping = self.config['PowerBiTable']
        print(f'Debug: Table mapping config: {mapping}')
        
        xpath = mapping.get('source_xpath', '//relation[@type="table"]')
        print(f'Debug: Using XPath: {xpath}')
        
        table_elements = self._find_elements(xpath)
        print(f'Debug: Found {len(table_elements)} table elements')
        
        if not table_elements:
            print('Debug: No table elements found. Trying alternative XPath: //datasources/datasource/connection/relation')
            table_elements = self._find_elements('//datasources/datasource/connection/relation')
            print(f'Debug: Found {len(table_elements)} table elements with alternative XPath')
        
        tables = []
        for i, table_elem in enumerate(table_elements, 1):
            print(f'\nDebug: Processing table {i}/{len(table_elements)}')
            print(f'Debug: Table element attributes: {table_elem.attrib}')
            print(f'Debug: Table element tag: {table_elem.tag}')
            print(f'Debug: Table element text: {table_elem.text}')
            
            table = self.extract_table_info(table_elem)
            if table:
                print(f'Debug: Successfully extracted table: {table.source_name}')
                tables.append(table)
            else:
                print('Debug: Failed to extract table info')
        
        print(f'\nDebug: Total tables extracted: {len(tables)}')
        for table in tables:
            print(f'Debug: - {table.source_name} ({len(table.columns)} columns, {len(table.measures)} measures, {len(table.hierarchies)} hierarchies)')
        
        return tables
    
    def _map_datatype(self, tableau_type: str) -> str:
        """Map Tableau datatypes to Power BI datatypes."""
        type_mapping = self.config.get('tableau_datatype_to_tmdl', {})
        return type_mapping.get(tableau_type.lower(), 'string')


def parse_workbook(twb_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a Tableau workbook file.
    
    Args:
        twb_path: Path to the TWB file
        config: Configuration dictionary
        
    Returns:
        Dict containing extracted table information
    """
    parser = TableParser(twb_path, config)
    data = {
        'PowerBiTables': parser.extract_all_tables()
    }
    
    # Save intermediate file
    parser.save_intermediate(data, 'tables')
    
    return data
