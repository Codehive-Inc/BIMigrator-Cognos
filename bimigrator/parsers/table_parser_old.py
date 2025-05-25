"""Parser for extracting table information from Tableau workbooks."""
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional

from bimigrator.common.logging import logger
from bimigrator.config.data_classes import PowerBiTable, PowerBiColumn, PowerBiMeasure, PowerBiPartition
from bimigrator.converters import CalculationInfo
from bimigrator.generators.tmdl_generator import TMDLGenerator
from bimigrator.helpers.calculation_tracker import CalculationTracker
from bimigrator.parsers.base_parser import BaseParser
from bimigrator.parsers.column_parser import ColumnParser
from bimigrator.parsers.connections.connection_factory import ConnectionParserFactory


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

    def __init__(self, twb_file: str, config: Dict[str, Any], output_dir: str):
        """
        Initialize TableParser.
        
        Args:
            twb_file: Path to the TWB file
            config: Configuration dictionary
            output_dir: Output directory
        """
        super().__init__(twb_file, config, output_dir)
        # Initialize calculation tracker with the base output directory
        output_path = Path(output_dir)
        # Strip off pbit or extracted directories to get base directory
        if output_path.name == 'pbit' or output_path.name == 'extracted':
            output_path = output_path.parent
        base_output_dir = output_path
        
        # Update config with output directory
        config['output_dir'] = str(base_output_dir)
        
        self.column_parser = ColumnParser(config)
        self.connection_factory = ConnectionParserFactory(config)
        self.tmdl_generator = TMDLGenerator(config)
        self.output_dir = output_dir
        self.calculation_tracker = CalculationTracker(base_output_dir / 'extracted')

    def _extract_partition_info(
            self,
            ds_element: ET.Element,
            table_name: str,
            columns: Optional[List[PowerBiColumn]] = None
    ) -> List[PowerBiPartition]:
        """Extract partition information from a datasource element.
        
        Args:
            ds_element: Datasource element
            table_name: Name of the table
            columns: Optional list of PowerBiColumn objects with type information

        Returns:
            List of PowerBiPartition objects
        """
        partitions = []
        try:
            # Find the connection element
            connection = ds_element.find('.//connection')
            if connection is not None:
                # Log connection details
                conn_details = {
                    'class': connection.get('class'),
                    'server': connection.get('server'),
                    'database': connection.get('dbname'),
                    'schema': connection.get('schema'),
                    'username': connection.get('username'),
                    'port': connection.get('port'),
                    'authentication': connection.get('authentication'),
                    'table_name': table_name
                }
                
                # Save connection details to extracted folder
                import json
                import os
                # Use the intermediate_dir from BaseParser which is already properly configured
                os.makedirs(self.intermediate_dir, exist_ok=True)
                partitions_file = os.path.join(self.intermediate_dir, 'partitions.json')
                
                existing_data = {}
                if os.path.exists(partitions_file):
                    with open(partitions_file, 'r') as f:
                        existing_data = json.load(f)
                
                if 'connections' not in existing_data:
                    existing_data['connections'] = []
                existing_data['connections'].append(conn_details)
                
                with open(partitions_file, 'w') as f:
                    json.dump(existing_data, f, indent=2)
                
                logger.info(f"Connection details for table {table_name}: {json.dumps(conn_details, indent=2)}")
                
                # Get the appropriate connection parser
                parser = self.connection_factory.get_parser(connection)

                # Find relation elements - try both with and without namespaces
                relations = connection.findall('.//relation')

                # If no relations found, try with wildcard namespace
                if not relations:
                    for element in connection.findall('.//*'):
                        if element.tag.endswith('relation'):
                            relations.append(element)

                # Process each relation and log
                for relation in relations:
                    logger.info(f"Processing relation for table {table_name}: {relation.attrib}")
                    new_partitions = parser.extract_partition_info(connection, relation, table_name, columns)
                    logger.info(f"Generated {len(new_partitions)} partitions for relation")
                    partitions.extend(new_partitions)

        except Exception as e:
            logger.error(f"Error extracting partition info: {str(e)}", exc_info=True)

        return partitions

    def _get_datasource_id(self, ds_element: ET.Element) -> str:
        """Get a unique ID for a datasource element.
        
        Args:
            ds_element: Datasource element
            
        Returns:
            Unique ID string
        """
        # Try to get existing ID
        ds_id = ds_element.get('id') or ds_element.get('name')
        if not ds_id:
            # Generate a new UUID if no ID exists
            ds_id = str(uuid.uuid4())
        return ds_id

    def extract_all_tables(self) -> List[PowerBiTable]:
        """Extract all table information from the workbook based on datasources and their relations.
        
        Returns:
            List[PowerBiTable]: List of extracted tables
        """
        tables = []
        try:
            # Get all datasources
            datasources = self.root.findall('.//datasource')
            logger.info(f"Found {len(datasources)} datasources")

            # Track unique table names to avoid duplicates
            seen_table_names = set()

            # Process each datasource
            for ds_element in datasources:
                # Get datasource name and caption
                ds_name = ds_element.get('name', '')
                ds_caption = ds_element.get('caption', ds_name)
                logger.info(f"Processing datasource: {ds_name} (caption: {ds_caption})")

                # Skip datasources without a connection
                connection = ds_element.find('.//connection')
                if connection is None:
                    logger.info(f"Skipping datasource {ds_name} - no connection found")
                    continue

                # Get datasource ID for deduplication
                ds_id = self._get_datasource_id(ds_element)

                # Get table name from relation element for Excel sheets
                table_name = ds_caption or ds_name
                if connection.get('class') == 'excel-direct':
                    # Find the relation element
                    relation = connection.find('.//relation')
                    if relation is not None:
                        sheet_name = relation.get('name')
                        if sheet_name:
                            table_name = sheet_name

                # Extract columns and measures
                columns_yaml_config = self.config.get('PowerBiColumn', {})
                columns, measures = self.column_parser.extract_columns_and_measures(
                    ds_element,
                    columns_yaml_config,
                    table_name  # Use consistent table name for DAX expressions
                )

                # Handle federated datasources
                if connection.get('class') == 'federated':
                    # For federated datasources, try both encapsulated and non-encapsulated formats
                    relations = [
                        *connection.findall('.//relation'),
                        *connection.findall('./_.fcp.ObjectModelEncapsulateLegacy.false...relation'),
                        *connection.findall('./_.fcp.ObjectModelEncapsulateLegacy.true...relation')
                    ]
                    # Always use caption/name as the table name
                    # The relation name is just for internal use

                # Create a unique table name if needed
                final_table_name = table_name
                counter = 1
                while final_table_name in seen_table_names:
                    final_table_name = f"{table_name}_{counter}"
                    counter += 1
                seen_table_names.add(final_table_name)

                # Extract partition information
                all_partitions = self._extract_partition_info(ds_element, final_table_name, columns)

                # Deduplicate partitions based on name and source file
                seen_partitions = {}
                for partition in all_partitions:
                    # Extract file name from M code
                    file_key = None
                    if 'File.Contents' in partition.expression:
                        start = partition.expression.find('File.Contents("') + len('File.Contents("')
                        end = partition.expression.find('"', start)
                        if start > -1 and end > -1:
                            file_key = partition.expression[start:end]

                    # Create unique key from file name and partition name
                    key = (file_key, partition.name) if file_key else partition.name

                    if key not in seen_partitions:
                        seen_partitions[key] = partition

                # Use unique partitions
                partitions = list(seen_partitions.values())

                # Calculation tracking is now handled in ColumnParser

                # Create PowerBiTable
                table = PowerBiTable(
                    source_name=final_table_name,
                    description=f"Imported from Tableau datasource: {ds_name}",
                    columns=columns,
                    measures=measures,
                    hierarchies=[],
                    partitions=partitions
                )

                tables.append(table)
                logger.info(
                    f"Added table {final_table_name} with {len(columns)} columns, {len(measures)} measures, and {len(partitions)} partitions")

            # Deduplicate tables based on source_name
            unique_tables = {}
            for table in tables:
                key = table.source_name
                if key in unique_tables:
                    existing_table = unique_tables[key]
                    # Keep the table with more columns/measures
                    existing_complexity = len(existing_table.columns) + len(existing_table.measures)
                    new_complexity = len(table.columns) + len(table.measures)
                    if new_complexity > existing_complexity:
                        unique_tables[key] = table
                else:
                    unique_tables[key] = table

            tables = list(unique_tables.values())
            logger.info(f"After deduplication, found {len(tables)} unique tables")

        except Exception as e:
            logger.error(f"Error extracting tables: {str(e)}", exc_info=True)

        return tables

    def parse_workbook(self, twb_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a Tableau workbook file.

        Args:
            twb_path: Path to the TWB file
            config: Configuration dictionary

        Returns:
            Dict containing extracted table information
        """
        self.twb_path = twb_path
        self.config = config
        self.workbook = self._load_workbook()

        tables = self.extract_all_tables()

        return {
            'tables': tables
        }

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

        # Print the first few metadata records for debugging
        for i, meta_col in enumerate(column_elements_from_ds[:5]):
            remote_name = meta_col.find('remote-name')
            local_name = meta_col.find('local-name')
            parent_name = meta_col.find('parent-name')

            remote_name_text = remote_name.text if remote_name is not None else 'None'
            local_name_text = local_name.text if local_name is not None else 'None'
            parent_name_text = parent_name.text if parent_name is not None else 'None'

            print(
                f"Debug: Metadata record {i}: remote_name={remote_name_text}, local_name={local_name_text}, parent_name={parent_name_text}")

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
            if col_elem.tag.endswith('column') and col_elem.find('calculation') is not None and col_elem.get(
                    calc_name_attr):
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
            if col_elem.tag.endswith('column') and col_elem.find('calculation') is not None and col_elem.get(
                    calc_datatype_attr):
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
                    if calculation_formula.strip().upper().startswith(
                            ("SUM(", "AVERAGE(", "COUNT(", "MIN(", "MAX(", "CALCULATE(")):
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
                            elif pbi_datatype.lower() in ["int64", "double", "decimal",
                                                          "currency"] and not is_calculated_column:
                                summarize_by = "sum"
                else:
                    # For non-metadata records, use default logic
                    if pbi_datatype.lower() in ["int64", "double", "decimal", "currency"] and not is_calculated_column:
                        summarize_by = "sum"

                # Initialize annotations
                annotations = {}

                # Check for explicit aggregation in Tableau XML to set SummarizationSetBy annotation
                has_explicit_aggregation = False

                # Instead of trying to detect the aggregation element directly,
                # use the summarize_by value that's already been determined
                # If summarize_by is anything other than 'none', it means there's an explicit aggregation
                has_explicit_aggregation = summarize_by != 'none'

                # Set SummarizationSetBy annotation based on whether there's explicit aggregation
                annotations['SummarizationSetBy'] = 'User' if has_explicit_aggregation else 'Automatic'

                # Add PBI_FormatHint annotation for numeric columns
                if pbi_datatype.lower() in ["int64", "double", "decimal", "currency"]:
                    # For numeric columns, add the format hint
                    annotations['PBI_FormatHint'] = {"isGeneralNumber": True}

                print(
                    f"Debug: Column '{final_col_name}': summarize_by={summarize_by}, SummarizationSetBy={annotations['SummarizationSetBy']}")

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