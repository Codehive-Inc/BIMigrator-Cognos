"""Parser for extracting table information from Tableau workbooks."""
from pathlib import Path
import sys
from typing import Dict, Any, List, Optional, Tuple
import uuid
import xml.etree.ElementTree as ET

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.dataclasses import PowerBiTable, PowerBiColumn, PowerBiMeasure, PowerBiHierarchy, PowerBiHierarchyLevel
from .base_parser import BaseParser

class TableParser(BaseParser):
    """Parser for extracting table information from Tableau workbooks."""
    
    def __init__(self, twb_path: str, config: Dict[str, Any]):
        super().__init__(twb_path, config)
        self.tableau_to_tmdl_datatypes = self.config.get('tableau_datatype_to_tmdl', {})
    
    def _map_datatype(self, tableau_type: str) -> str:
        """Map Tableau datatypes to Power BI datatypes.
        
        Args:
            tableau_type: Tableau datatype string
            
        Returns:
            Power BI datatype string
        """
        if not tableau_type or not isinstance(tableau_type, str):
            print(f"Warning: Invalid datatype '{tableau_type}', using 'string' as default")
            return 'string'
            
        return self.tableau_to_tmdl_datatypes.get(tableau_type.lower(), 'string')
    
    def extract_all_tables(self) -> List[PowerBiTable]:
        """Extract all table information from the workbook based on datasources and their relations.
        
        Returns:
            List[PowerBiTable]: List of extracted tables
        """
        try:
            table_config_yaml = self.config.get('PowerBiTable')
            if not table_config_yaml:
                print("Error: 'PowerBiTable' configuration not found.")
                return []

            datasource_xpath = table_config_yaml.get('source_xpath')
            if not datasource_xpath:
                print("Error: 'source_xpath' for PowerBiTable (datasources) not defined.")
                return []

            datasource_elements = self._find_elements(datasource_xpath)
            
            # Initialize default datatype mapping if not provided in config
            if not self.tableau_to_tmdl_datatypes:
                self.tableau_to_tmdl_datatypes = {
                    'string': 'string',
                    'integer': 'int64',
                    'real': 'double',
                    'boolean': 'boolean',
                    'date': 'dateTime',
                    'datetime': 'dateTime'
                }

            extracted_tables = []
            seen_table_names = set()  # To ensure unique Power BI table names
            datasource_info = {}  # Store datasource info for relation processing

            # First pass: Process datasources and extract their basic information
            for ds_element in datasource_elements:
                try:
                    table_name_mapping = table_config_yaml.get('source_name', {})
                    
                    # Try 'source_attribute' (e.g., caption)
                    table_name = self._get_mapping_value(table_name_mapping, ds_element)
                    
                    # Fallback to 'fallback_attribute' (e.g., name) if primary is None or empty
                    if not table_name and 'fallback_attribute' in table_name_mapping:
                        fallback_attr = table_name_mapping['fallback_attribute']
                        table_name = ds_element.get(fallback_attr)

                    if not table_name:
                        continue
                    
                    # Store datasource information for later use
                    ds_id = ds_element.get('name')
                    if ds_id:
                        datasource_info[ds_id] = {
                            'name': table_name,
                            'element': ds_element
                        }
                    
                    # Use the original table name without adding suffixes
                    # This ensures we only have one table per datasource
                    final_table_name = table_name
                    seen_table_names.add(final_table_name)

                    description_mapping = table_config_yaml.get('description', {})
                    description = self._get_mapping_value(description_mapping, ds_element)

                    is_hidden_mapping = table_config_yaml.get('is_hidden', {})
                    is_hidden = self._get_mapping_value(is_hidden_mapping, ds_element, default_value=False)

                    # Extract Columns for this Datasource
                    columns_yaml_config = table_config_yaml.get('columns_config', {})
                    pbi_columns, pbi_measures = self._extract_columns_and_measures_for_datasource(
                        ds_element, columns_yaml_config, final_table_name
                    )

                    # Create the table object
                    table = PowerBiTable(
                        source_name=final_table_name,  # Use the de-duplicated name
                        description=description,
                        is_hidden=is_hidden,
                        columns=pbi_columns,
                        measures=pbi_measures,
                        hierarchies=[],
                        partitions=[],
                        annotations={}
                    )
                    extracted_tables.append(table)
                except Exception:
                    # Silently continue to next datasource if there's an error
                    continue

            # Second pass: Process relations within datasources if configured
            relation_config = table_config_yaml.get('relation_config')
            if relation_config:
                relation_xpath = relation_config.get('source_xpath')
                if relation_xpath:
                    print(f"\nDebug: Looking for relations using XPath: {relation_xpath}")
                    print(f"Debug: Found {len(datasource_info)} datasources to process for relations")
                    
                    for ds_id, ds_info in datasource_info.items():
                        ds_element = ds_info['element']
                        print(f"Debug: Processing datasource '{ds_info['name']}' (ID: {ds_id}) for relations")
                        try:
                            # Find relations within this datasource
                            relation_elements = ds_element.findall(relation_xpath, namespaces=self.namespaces)
                            print(f"Debug: Found {len(relation_elements)} relation elements in datasource '{ds_info['name']}'")
                            
                            # If no relations found directly, try a more generic approach
                            if not relation_elements:
                                print(f"Debug: Trying alternate approach to find relations in datasource '{ds_info['name']}'")
                                # Try to find any relation elements anywhere in this datasource
                                relation_elements = ds_element.findall(".//relation", namespaces=self.namespaces)
                                print(f"Debug: Found {len(relation_elements)} relation elements with alternate approach")
                                
                                # If still no relations, try without namespaces
                                if not relation_elements:
                                    relation_elements = ds_element.findall(".//relation")
                                    print(f"Debug: Found {len(relation_elements)} relation elements without namespaces")
                            
                            
                            for rel_element in relation_elements:
                                # Process relation based on its type
                                table_type_attr = relation_config.get('table_type', {}).get('source_attribute')
                                rel_type = rel_element.get(table_type_attr) if table_type_attr else None
                                
                                # Get table name from relation
                                table_name_attr = relation_config.get('table_name', {}).get('source_attribute')
                                rel_table_name = rel_element.get(table_name_attr) if table_name_attr else None
                                
                                # If no name, try to generate one based on type
                                if not rel_table_name:
                                    if rel_type == 'table':
                                        rel_table_name = f"Table_{len(extracted_tables)}"
                                    elif rel_type == 'text':
                                        rel_table_name = f"SQL_Query_{len(extracted_tables)}"
                                    elif rel_type == 'join':
                                        rel_table_name = f"Join_{len(extracted_tables)}"
                                    else:
                                        rel_table_name = f"Relation_{len(extracted_tables)}"
                                
                                # Create a unique name for this relation
                                rel_final_name = f"{ds_info['name']} - {rel_table_name}"
                                counter = 1
                                while rel_final_name in seen_table_names:
                                    rel_final_name = f"{ds_info['name']} - {rel_table_name}_{counter}"
                                    counter += 1
                                seen_table_names.add(rel_final_name)
                                
                                # Handle SQL queries (text type relations)
                                description = f"Table {rel_table_name} from datasource {ds_info['name']}"
                                if rel_type == 'text':
                                    # Try to extract SQL query text
                                    sql_query_xpath = relation_config.get('sql_query', {}).get('source_xpath')
                                    if sql_query_xpath:
                                        try:
                                            sql_text = rel_element.text
                                            if sql_text and len(sql_text) > 10:  # Basic validation
                                                # Truncate long SQL for description
                                                sql_preview = sql_text[:100] + '...' if len(sql_text) > 100 else sql_text
                                                description = f"SQL Query: {sql_preview}"
                                        except Exception:
                                            pass
                                
                                # Create a table entry for this relation
                                rel_table = PowerBiTable(
                                    source_name=rel_final_name,
                                    description=description,
                                    is_hidden=False,
                                    columns=[],  # Could extract columns if needed
                                    measures=[],
                                    hierarchies=[],
                                    partitions=[],
                                    annotations={'relation_type': rel_type or 'unknown'}
                                )
                                extracted_tables.append(rel_table)
                        except Exception:
                            # Silently continue if there's an error processing relations
                            continue

            return extracted_tables
        except Exception:
            # Return empty list if there's an error in the overall process
            return []
    
    def _extract_columns_and_measures_for_datasource(
        self, 
        ds_element: ET.Element, 
        columns_yaml_config: Dict,
        pbi_table_name: str  # For DAX expressions in measures
    ):  # -> Tuple[List[PowerBiColumn], List[PowerBiMeasure]]
        """Extract columns and measures from a datasource element.
        
        Args:
            ds_element: Datasource element
            columns_yaml_config: YAML configuration for columns
            pbi_table_name: Table name for DAX expressions
            
        Returns:
            Tuple of (columns, measures)
        """
        pbi_columns = []
        pbi_measures = []
        seen_col_names = set()

        col_list_xpath = columns_yaml_config.get('source_xpath')
        if not col_list_xpath:
            return pbi_columns, pbi_measures

        # Find column elements relative to the datasource element
        column_elements_from_ds = ds_element.findall(col_list_xpath, namespaces=self.namespaces)

        # Check for calculated fields directly under datasource
        direct_calc_field_xpath = "column[calculation]"
        calculated_field_elements = ds_element.findall(direct_calc_field_xpath, namespaces=self.namespaces)
        
        # Combine all potential column elements
        all_potential_column_elements = list(column_elements_from_ds)
        
        # Add calculated fields if they're not already included
        for cf_elem in calculated_field_elements:
            cf_name = cf_elem.get('name')
            if cf_name:
                # Check if this calculated field is already in our list
                existing = False
                for col in column_elements_from_ds:
                    col_name = col.get('caption') or col.get('local-name')
                    if col_name == cf_name:
                        existing = True
                        break
                        
                if not existing:
                    all_potential_column_elements.append(cf_elem)

        for col_elem in all_potential_column_elements:
            col_name_mapping = columns_yaml_config.get('name', {})
            col_name = self._get_mapping_value(col_name_mapping, col_elem)
            if not col_name and 'fallback_attribute' in col_name_mapping:
                col_name = col_elem.get(col_name_mapping['fallback_attribute'])
            
            if not col_name:
                continue

            # Deduplicate column names within the Power BI table
            final_col_name = col_name
            counter = 1
            while final_col_name in seen_col_names:
                final_col_name = f"{col_name}_{counter}"
                counter += 1
            seen_col_names.add(final_col_name)

            datatype_mapping_cfg = columns_yaml_config.get('datatype', {})
            twb_datatype = self._get_mapping_value(datatype_mapping_cfg, col_elem, default_value='string')
            pbi_datatype = self._map_datatype(twb_datatype)

            description_mapping_cfg = columns_yaml_config.get('description', {})
            description = self._get_mapping_value(description_mapping_cfg, col_elem)
            
            is_hidden_mapping_cfg = columns_yaml_config.get('is_hidden', {})
            is_hidden = self._get_mapping_value(is_hidden_mapping_cfg, col_elem, default_value=False)

            format_string_mapping_cfg = columns_yaml_config.get('format_string', {})
            format_string = self._get_mapping_value(format_string_mapping_cfg, col_elem)

            role_mapping_cfg = columns_yaml_config.get('role', {})
            role = self._get_mapping_value(role_mapping_cfg, col_elem)

            calc_formula_mapping_cfg = columns_yaml_config.get('calculation_formula', {})
            calculation_formula = self._get_mapping_value(calc_formula_mapping_cfg, col_elem)

            # Decide if it's a measure or a column
            is_measure_role = (role == 'measure')
            is_calculated_measure_candidate = bool(calculation_formula) and role != 'dimension'

            if is_measure_role or is_calculated_measure_candidate:
                dax_expression = None
                if calculation_formula:
                    # Basic attempt to see if it's DAX-like or needs SUM wrapper
                    if calculation_formula.strip().upper().startswith(("SUM(", "AVERAGE(", "COUNT(", "MIN(", "MAX(", "CALCULATE(")):
                        dax_expression = f"/* Original TWB: {calculation_formula} */ {calculation_formula}"
                    else:
                        dax_expression = f"SUMX('{pbi_table_name}', {calculation_formula})"
                else:
                    dax_expression = f"SUM('{pbi_table_name}'[{final_col_name}])"
                
                measure = PowerBiMeasure(
                    source_name=final_col_name,
                    dax_expression=dax_expression,
                    description=description,
                    is_hidden=is_hidden,
                    format_string=format_string
                )
                pbi_measures.append(measure)
            else:
                # It's a regular column
                summarize_by = "none"
                if pbi_datatype.lower() in ["int64", "double", "decimal", "currency"]:
                    summarize_by = "sum"

                column = PowerBiColumn(
                    source_name=final_col_name,
                    pbi_datatype=pbi_datatype,
                    source_column=final_col_name,
                    description=description,
                    is_hidden=is_hidden,
                    format_string=format_string,
                    summarize_by=summarize_by
                )
                pbi_columns.append(column)

        return pbi_columns, pbi_measures
    
    # The old extract_all_tables method has been replaced with a new implementation above
        
    def _get_datasource_id(self, element: ET.Element) -> str:
        """Get the datasource ID for a table element to help with deduplication.
        
        Args:
            element: The table element
            
        Returns:
            Datasource ID or empty string if not found
        """
        # Try to find the connection attribute which often contains the datasource ID
        connection = element.get('connection', '')
        if connection:
            return connection
            
        # Try to find the parent datasource element
        parent = element
        while parent is not None:
            if parent.tag.endswith('datasource'):
                return parent.get('name', '')
            parent = parent.getparent() if hasattr(parent, 'getparent') else None
            
        return ''
        
    def _find_columns_for_datasource(self, datasource_name: str) -> List[ET.Element]:
        """Find columns associated with a specific datasource.
        
        Args:
            datasource_name: The name of the datasource
            
        Returns:
            List of column elements associated with the datasource
        """
        # Try to find columns in datasource-dependencies sections
        columns = []
        
        # Find all datasource-dependencies elements that reference this datasource
        dependency_xpath = f"//datasource-dependencies[@datasource='{datasource_name}']//column"
        try:
            columns.extend(self.root.findall(dependency_xpath, self.namespaces))
        except Exception as e:
            print(f"Debug: Error finding columns with dependency XPath: {str(e)}")
        
        # Also look for columns directly in the datasource definition
        datasource_xpath = f"//datasource[@name='{datasource_name}']//column"
        try:
            columns.extend(self.root.findall(datasource_xpath, self.namespaces))
        except Exception as e:
            print(f"Debug: Error finding columns with datasource XPath: {str(e)}")
            
        print(f"Debug: Found {len(columns)} columns for datasource '{datasource_name}'")
        return columns
        
    def _extract_nested_tables(self, join_element) -> List[ET.Element]:
        """Extract table relations from a join relation element.
        
        Args:
            join_element: The join relation element
            
        Returns:
            List of table relation elements
        """
        tables = []
        
        # Find all relation elements within this join
        relations = join_element.findall('.//relation', self.namespaces)
        
        for relation in relations:
            relation_type = relation.get('type', '')
            relation_name = relation.get('name', '')
            
            if relation_type == 'table' and relation_name:
                print(f'Debug: Found nested table: {relation_name}')
                tables.append(relation)
            elif relation_type == 'text' and relation_name:
                # Handle SQL query relations
                print(f'Debug: Found SQL query table: {relation_name}')
                tables.append(relation)
                
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
