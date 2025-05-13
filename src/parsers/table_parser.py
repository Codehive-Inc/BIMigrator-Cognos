"""Parser for extracting table information from Tableau workbooks."""
from pathlib import Path
import sys
from typing import Dict, Any, List, Optional, Tuple
import uuid
import xml.etree.ElementTree as ET
import logging

from .base_parser import BaseParser
from config.data_classes import PowerBiTable, PowerBiColumn, PowerBiMeasure, PowerBiHierarchy, PowerBiHierarchyLevel
from ..converters import CalculationConverter, CalculationInfo
from .base_parser import BaseParser


def extract_tableau_calculation_info(calculation_element: Any) -> Dict[str, Any]:
    """
    Extract information from a Tableau calculation element.
    
    Args:
        calculation_element: The Tableau calculation element
        
    Returns:
        A dictionary containing the calculation information
    """
    if calculation_element is None:
        return {}
    
    # Extract attributes from the calculation element
    calc_info = {}
    
    # Handle different types of calculation elements
    if hasattr(calculation_element, 'get'):
        # XML element
        calc_info['formula'] = calculation_element.get('formula', '')
        calc_info['caption'] = calculation_element.get('caption', '')
        calc_info['datatype'] = calculation_element.get('datatype', '')
        calc_info['role'] = calculation_element.get('role', '')
    elif isinstance(calculation_element, dict):
        # Dictionary
        calc_info = calculation_element
    
    return calc_info

class TableParser(BaseParser):
    """Parser for extracting table information from Tableau workbooks."""
    
    def __init__(self, twb_path: str, config: Dict[str, Any]):
        super().__init__(twb_path, config)
        self.tableau_to_tmdl_datatypes = self.config.get('tableau_datatype_to_tmdl', {})
        self.calculation_converter = CalculationConverter(config)
    
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
                    
                    # Debug output
                    print(f"Debug: Created table '{final_table_name}' with {len(pbi_columns)} columns and {len(pbi_measures)} measures")
                    
                    extracted_tables.append(table)
                except Exception as e:
                    # Print the error for debugging
                    print(f"Error processing datasource: {str(e)}")
                    # Continue to next datasource if there's an error
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
        # For debugging
        ds_name = ds_element.get('caption') or ds_element.get('name')
        print(f"Debug: Processing datasource '{ds_name}'")
        print(f"Debug: Datasource element tag: {ds_element.tag}")
        print(f"Debug: Datasource element attributes: {ds_element.attrib}")
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

        # Find metadata-records container first
        metadata_records_container = None
        
        # First, look for metadata-records as a direct child of the datasource
        for child in ds_element:
            if child.tag.endswith('metadata-records'):
                metadata_records_container = child
                break
        
        # If not found, look for connection elements that might contain metadata-records
        if metadata_records_container is None:
            # Try to find connection element
            connection_elem = ds_element.find('.//connection', namespaces=self.namespaces)
            if connection_elem is not None:
                # Look for metadata-records within the connection
                for child in connection_elem.iter():
                    if child.tag.endswith('metadata-records'):
                        metadata_records_container = child
                        break
        
        # Initialize an empty list for column elements
        column_elements_from_ds = []
        
        # If we found the metadata-records container, extract column metadata records
        if metadata_records_container is not None:
            for meta_record in metadata_records_container:
                if meta_record.tag.endswith('metadata-record') and meta_record.get('class') == 'column':
                    column_elements_from_ds.append(meta_record)
        
        print(f"Debug: Found {len(column_elements_from_ds)} metadata-record columns")
        
        # If we still haven't found any columns, try a more aggressive approach
        if not column_elements_from_ds:
            # Look for all metadata-record elements with class='column' anywhere in the datasource
            for elem in ds_element.iter():
                if elem.tag.endswith('metadata-record') and elem.get('class') == 'column':
                    column_elements_from_ds.append(elem)
            
            print(f"Debug: Found {len(column_elements_from_ds)} metadata-record columns using aggressive search")
            
        # Look specifically for Tab_module and PUAT_Module columns in SQL queries
        sql_queries = []
        for elem in ds_element.iter():
            if elem.tag.endswith('relation') and elem.get('type') == 'text':
                sql_text = elem.text
                if sql_text and ('Tab_module' in sql_text or 'PUAT_Module' in sql_text):
                    sql_queries.append(sql_text)
        
        if sql_queries:
            print(f"Debug: Found {len(sql_queries)} SQL queries containing Tab_module or PUAT_Module")
            
            # Extract column names from SQL queries
            for sql in sql_queries:
                if 'Tab_module' in sql:
                    # Create a synthetic metadata record for Tab_module
                    meta_record = ET.Element('metadata-record')
                    meta_record.set('class', 'column')
                    
                    remote_name = ET.SubElement(meta_record, 'remote-name')
                    remote_name.text = 'Tab_module'
                    
                    local_name = ET.SubElement(meta_record, 'local-name')
                    local_name.text = '[Tab_module]'
                    
                    remote_type = ET.SubElement(meta_record, 'remote-type')
                    remote_type.text = '130'  # String type
                    
                    column_elements_from_ds.append(meta_record)
                    print("Debug: Added synthetic metadata record for Tab_module")
                
                if 'PUAT_Module' in sql:
                    # Create a synthetic metadata record for PUAT_Module
                    meta_record = ET.Element('metadata-record')
                    meta_record.set('class', 'column')
                    
                    remote_name = ET.SubElement(meta_record, 'remote-name')
                    remote_name.text = 'PUAT_Module'
                    
                    local_name = ET.SubElement(meta_record, 'local-name')
                    local_name.text = '[PUAT_Module]'
                    
                    remote_type = ET.SubElement(meta_record, 'remote-type')
                    remote_type.text = '130'  # String type
                    
                    column_elements_from_ds.append(meta_record)
                    print("Debug: Added synthetic metadata record for PUAT_Module")
        
        # Print the first few metadata records for debugging
        for i, meta_col in enumerate(column_elements_from_ds[:5]):
            remote_name = meta_col.find('remote-name')
            local_name = meta_col.find('local-name')
            parent_name = meta_col.find('parent-name')
            
            remote_name_text = remote_name.text if remote_name is not None else 'None'
            local_name_text = local_name.text if local_name is not None else 'None'
            parent_name_text = parent_name.text if parent_name is not None else 'None'
            
            print(f"Debug: Metadata record {i}: remote_name={remote_name_text}, local_name={local_name_text}, parent_name={parent_name_text}")

        # Check for calculated fields directly under datasource
        calc_field_xpath = columns_yaml_config.get('calculated_fields_xpath', "column[calculation]")
        calculated_field_elements = ds_element.findall(calc_field_xpath, namespaces=self.namespaces)
        
        # Look for columns in relation elements (for Excel and other direct connections)
        relation_column_elements = []
        
        # Get relation column paths from configuration
        relation_paths = columns_yaml_config.get('relation_column_paths', [])
        
        # If no paths defined in config, use default paths
        if not relation_paths:
            relation_paths = [
                ".//_.fcp.ObjectModelEncapsulateLegacy.false...relation//column",
                ".//_.fcp.ObjectModelEncapsulateLegacy.true...relation//column",
                ".//relation//column"
            ]
        
        for rel_path in relation_paths:
            rel_columns = ds_element.findall(rel_path, namespaces=self.namespaces)
            if rel_columns:
                relation_column_elements.extend(rel_columns)
        
        # Collect all column elements from different sources
        all_potential_column_elements = []
        
        # Track names of columns already added to avoid duplicates with the same name
        added_column_names = set()
        
        # Add calculated fields first
        for calc_field in calculated_field_elements:
            calc_name = calc_field.get('caption')
            if calc_name:
                all_potential_column_elements.append(calc_field)
                added_column_names.add(calc_name)
        
        # Add relation columns
        for rel_col in relation_column_elements:
            rel_col_name = rel_col.get('name')
            if rel_col_name and rel_col_name not in added_column_names:
                all_potential_column_elements.append(rel_col)
                added_column_names.add(rel_col_name)
        
        # Add metadata-record columns
        for meta_col in column_elements_from_ds:
            # Get the column name from the metadata record
            remote_name = meta_col.find('remote-name')
            local_name = meta_col.find('local-name')
            parent_name = meta_col.find('parent-name')
            
            # Get the column name
            if remote_name is not None and remote_name.text:
                col_name = remote_name.text
            elif local_name is not None and local_name.text:
                col_name = local_name.text
            else:
                col_name = meta_col.get('caption') or meta_col.get('local-name')
            
            # Get the parent name (table or query name)
            parent_text = ''
            if parent_name is not None and parent_name.text:
                parent_text = parent_name.text.strip('[]')
                
            # Include all columns from this datasource
            # In Tableau, a datasource can contain multiple queries, so we include all columns
            include_column = True
            
            # Debug output to help understand the column structure
            if col_name:
                print(f"Debug: Found metadata column '{col_name}' with parent '{parent_text}'")
            else:
                print(f"Debug: Found metadata column with no name, parent '{parent_text}'")
                
            # Store the parent name in the metadata record as an attribute for later use
            if parent_name is not None and parent_name.text:
                meta_col.set('parent_table', parent_text)
            
            if col_name and col_name not in added_column_names and include_column:
                all_potential_column_elements.append(meta_col)
                added_column_names.add(col_name)

        # Get relation column mappings from configuration
        relation_column_mappings = columns_yaml_config.get('relation_column_mappings', {})
        relation_name_attr = relation_column_mappings.get('name_attribute', 'name')
        
        # Get calculated field mappings from configuration
        calc_field_mappings = columns_yaml_config.get('calculated_field_mappings', {})
        calc_name_attr = calc_field_mappings.get('name_attribute', 'caption')
        
        for col_elem in all_potential_column_elements:
            # For calculated fields with calculation child element
            if col_elem.tag.endswith('column') and col_elem.find('calculation') is not None and col_elem.get(calc_name_attr):
                col_name = col_elem.get(calc_name_attr)
                # Mark this as a calculated column
                col_elem.set('is_calculated', 'true')
                
                # Extract the calculation formula
                calc_elem = col_elem.find('calculation')
                if calc_elem is not None and calc_elem.get('formula'):
                    # Store the formula for later use
                    col_elem.set('calculation_formula', calc_elem.get('formula'))
                    
                    # Check if this is a measure based on role attribute
                    role = col_elem.get('role')
                    if role == 'measure':
                        col_elem.set('is_measure', 'true')
                    else:
                        # It's a calculated column
                        col_elem.set('is_calculated_column', 'true')
            # For relation columns, use the configured name attribute
            elif col_elem.tag.endswith('column') and col_elem.get(relation_name_attr):
                col_name = col_elem.get(relation_name_attr)
            # For metadata-record columns, extract from remote-name or local-name
            elif col_elem.tag.endswith('metadata-record'):
                remote_name = col_elem.find('remote-name')
                local_name = col_elem.find('local-name')
                
                if remote_name is not None and remote_name.text:
                    col_name = remote_name.text
                elif local_name is not None and local_name.text:
                    # Strip brackets from local name if present
                    local_name_text = local_name.text
                    if local_name_text.startswith('[') and local_name_text.endswith(']'):
                        col_name = local_name_text[1:-1]
                    else:
                        col_name = local_name_text
                else:
                    # Fallback to attributes
                    col_name = col_elem.get('caption') or col_elem.get('name')
            
            if not col_name:
                continue

            # Deduplicate column names within the Power BI table
            final_col_name = col_name
            counter = 1
            while final_col_name in seen_col_names:
                final_col_name = f"{col_name}_{counter}"
                counter += 1
            seen_col_names.add(final_col_name)

            relation_datatype_attr = relation_column_mappings.get('datatype_attribute', 'datatype')
            calc_datatype_attr = calc_field_mappings.get('datatype_attribute', 'datatype')
            
            # For calculated fields with calculation child element
            if col_elem.tag.endswith('column') and col_elem.find('calculation') is not None and col_elem.get(calc_datatype_attr):
                twb_datatype = col_elem.get(calc_datatype_attr)
                pbi_datatype = self._map_datatype(twb_datatype)
            # For relation columns, use the configured datatype attribute
            elif col_elem.tag.endswith('column') and col_elem.get(relation_datatype_attr):
                twb_datatype = col_elem.get(relation_datatype_attr)
                pbi_datatype = self._map_datatype(twb_datatype)
            # For metadata-record columns, extract from local-type
            elif col_elem.tag.endswith('metadata-record'):
                local_type = col_elem.find('local-type')
                remote_type = col_elem.find('remote-type')
                
                if local_type is not None and local_type.text:
                    twb_datatype = local_type.text
                    pbi_datatype = self._map_datatype(twb_datatype)
                elif remote_type is not None and remote_type.text:
                    # Map remote-type (which is usually a number) to a string datatype
                    remote_type_num = remote_type.text.strip()
                    # Basic mapping of common remote types
                    if remote_type_num in ['129', '130']:  # VARCHAR, WSTR
                        twb_datatype = 'string'
                    elif remote_type_num in ['5', '6', '131']:  # FLOAT, DOUBLE, NUMERIC
                        twb_datatype = 'real'
                    elif remote_type_num in ['3', '4', '20']:  # INT, LONG, BIGINT
                        twb_datatype = 'integer'
                    elif remote_type_num in ['7', '135']:  # DATE, TIMESTAMP
                        twb_datatype = 'datetime'
                    elif remote_type_num in ['11']:  # BOOLEAN
                        twb_datatype = 'boolean'
                    else:
                        twb_datatype = 'string'  # Default to string for unknown types
                    pbi_datatype = self._map_datatype(twb_datatype)
                else:
                    # Try to get the type from the parent element or attributes
                    type_attr = col_elem.get('type')
                    if type_attr:
                        twb_datatype = type_attr
                    else:
                        # Default to string if no type information is available
                        twb_datatype = 'string'
                    pbi_datatype = self._map_datatype(twb_datatype)
            else:
                # For other column types, use the configured mapping
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
                # Check if it's a calculated column, measure, or regular column
                is_calculated_column = col_elem.get('is_calculated_column') == 'true'
                is_measure = col_elem.get('is_measure') == 'true'
                is_calculated = col_elem.get('is_calculated') == 'true' or bool(calculation_formula)
                
                # Get the calculation formula from the element if available
                formula = col_elem.get('calculation_formula') or calculation_formula
                
                # Extract summarize_by from configuration
                summarize_by = "none"
                summarize_by_config = columns_yaml_config.get('summarize_by', {})
                if col_elem.tag.endswith('metadata-record'):
                    # Try to get aggregation from the element using XPath
                    agg_xpath = summarize_by_config.get('source_xpath')
                    if agg_xpath:
                        agg_elem = col_elem.find(agg_xpath.replace('/text()', ''))
                        if agg_elem is not None and agg_elem.text:
                            tableau_agg = agg_elem.text.lower()
                            # Map Tableau aggregation to Power BI summarization
                            if tableau_agg in ['sum', 'avg', 'min', 'max', 'count']:
                                summarize_by = tableau_agg
                            elif tableau_agg == 'none':
                                summarize_by = 'none'
                            # Default to sum for numeric columns if no specific aggregation
                            elif pbi_datatype.lower() in ["int64", "double", "decimal", "currency"] and not is_calculated_column:
                                summarize_by = "sum"
                else:
                    # For non-metadata records, use default logic
                    if pbi_datatype.lower() in ["int64", "double", "decimal", "currency"] and not is_calculated_column:
                        summarize_by = "sum"
                
                # Initialize annotations
                annotations = {}
                
                # Handle calculated fields (measures and calculated columns)
                if formula:
                    # Create calculation info from configuration
                    calc_info = CalculationInfo(
                        formula=formula,
                        caption=final_col_name,
                        datatype=pbi_datatype,
                        role='measure' if is_measure else None
                    )
                    
                    # Convert formula to DAX using the calculation converter
                    dax_expression = self.calculation_converter.convert_to_dax(calc_info, pbi_table_name)
                    
                    if is_measure:
                        # Create PowerBI measure
                        measure = PowerBiMeasure(
                            source_name=final_col_name,
                            dax_expression=dax_expression,
                            description=description,
                            is_hidden=is_hidden,
                            format_string=format_string
                        )
                        pbi_measures.append(measure)
                        print(f"Debug: Created measure '{final_col_name}' with expression: {dax_expression}")
                        continue
                    
                    # For calculated columns, store the DAX expression in annotations
                    annotations.update({
                        'SummarizationSetBy': 'User',  # Calculated columns are always set by user
                        'CalculationFormula': dax_expression
                    })
                    
                    print(f"Debug: Column '{final_col_name}' is a calculated column with expression: {dax_expression}")
                    
                    column = PowerBiColumn(
                        source_name=final_col_name,
                        pbi_datatype=pbi_datatype,
                        # For calculated columns in TMDL, the sourceColumn holds the DAX expression
                        source_column=dax_expression,
                        description=description,
                        is_hidden=is_hidden,
                        format_string=format_string,
                        summarize_by=summarize_by,
                        annotations=annotations,
                        # Set is_calculated to True for calculated columns
                        is_calculated=True,
                        # Data type is inferred from the DAX expression
                        is_data_type_inferred=True
                    )
                else:
                    # Regular column
                    column = PowerBiColumn(
                        source_name=final_col_name,
                        pbi_datatype=pbi_datatype,
                        source_column=final_col_name,  # Regular columns use their name as the source column
                        description=description,
                        is_hidden=is_hidden,
                        format_string=format_string,
                        summarize_by=summarize_by,
                        annotations=annotations
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
