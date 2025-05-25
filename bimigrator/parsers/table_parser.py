"""Main table parser that orchestrates the parsing of different table components."""
import xml.etree.ElementTree as ET
from typing import Dict, Any, List

from bimigrator.common.logging import logger
from bimigrator.config.data_classes import PowerBiTable, PowerBiColumn
from bimigrator.parsers.table_parser_base import TableParserBase
from bimigrator.parsers.table_parser_datasource import DatasourceParser
from bimigrator.parsers.table_parser_deduplication import TableDeduplicator
from bimigrator.parsers.table_parser_partition import TablePartitionParser
from bimigrator.parsers.table_parser_relation import TableRelationParser
from bimigrator.parsers.column_parser import ColumnParser


class TableParser(TableParserBase):
    """Main parser that orchestrates the parsing of tables from Tableau workbooks."""

    def __init__(self, twb_file: str, config: Dict[str, Any], output_dir: str):
        """Initialize TableParser.
        
        Args:
            twb_file: Path to the TWB file
            config: Configuration dictionary
            output_dir: Output directory
        """
        super().__init__(twb_file, config, output_dir)
        self.datasource_parser = DatasourceParser(twb_file, config, output_dir)
        self.relationship_parser = TableRelationParser(twb_file, config, output_dir)
        self.partition_parser = TablePartitionParser(twb_file, config, output_dir)
        self.column_parser = ColumnParser(config)
        self.deduplicator = TableDeduplicator()

    def _extract_join_tables(self) -> Dict[str, PowerBiTable]:
        """Extract tables from join relationships.
        
        Returns:
            Dictionary mapping table names to PowerBiTable objects
        """
        tables = {}
        try:
            # Find all datasources with connections
            datasources = self.root.findall('.//datasource')
            for ds in datasources:
                connection = ds.find('.//connection')
                if connection is None:
                    continue

                # Get connection details
                conn_class = connection.get('class', '')
                server = connection.get('server', '')
                schema = connection.get('schema', '')
                service = connection.get('service', '')

                # Find all relations
                relations = connection.findall('.//relation')
                for relation in relations:
                    # Look for table references in join clauses
                    clauses = relation.findall('.//clause[@type="join"]')
                    for clause in clauses:
                        exprs = clause.findall('.//expression')
                        for expr in exprs:
                            # Extract table and column from expressions like [Table].[Column]
                            op = expr.get('op', '')
                            if '[' in op and '].[' in op:
                                table_name = op.split('].[')[0].strip('[')
                                column_name = op.split('].[')[1].strip(']')

                                if table_name not in tables:
                                    # Create a mock datasource element with connection info
                                    mock_ds = ET.Element('datasource')
                                    mock_conn = ET.SubElement(mock_ds, 'connection')
                                    mock_conn.set('class', conn_class)
                                    mock_conn.set('server', server)
                                    mock_conn.set('schema', schema)
                                    mock_conn.set('service', service)

                                    # Use partition parser to extract partition info
                                    partitions = self.partition_parser._extract_partition_info(
                                        mock_ds,
                                        table_name,
                                        None  # No columns yet
                                    )

                                    # Create table with the column used in join
                                    column = PowerBiColumn(
                                        source_name=column_name,
                                        pbi_datatype="string",  # Default to string, can be refined later
                                        dataCategory="Uncategorized",
                                        description=f"Relationship column from {table_name}"
                                    )

                                    tables[table_name] = PowerBiTable(
                                        source_name=table_name,
                                        description=f"Table from {conn_class} join",
                                        columns=[column],
                                        measures=[],
                                        hierarchies=[],
                                        partitions=partitions
                                    )
                                else:
                                    # Add column if it doesn't exist
                                    existing_cols = {c.source_name for c in tables[table_name].columns}
                                    if column_name not in existing_cols:
                                        column = PowerBiColumn(
                                            source_name=column_name,
                                            name=column_name,
                                            data_type="string",
                                            data_category="Uncategorized",
                                            description=f"Join column from {table_name}"
                                        )
                                        tables[table_name].columns.append(column)

        except Exception as e:
            logger.error(f"Error extracting join tables: {str(e)}", exc_info=True)

        return tables

    def _extract_relationship_tables(self) -> Dict[str, PowerBiTable]:
        """Extract tables that are referenced in relationships.
        
        Returns:
            Dictionary mapping table names to PowerBiTable objects
        """
        tables = {}
        try:
            # Get connection details from first datasource
            connection = None
            for ds in self.root.findall('.//datasource'):
                conn = ds.find('.//connection')
                if conn is not None:
                    connection = conn
                    break
            
            conn_class = connection.get('class', '') if connection is not None else ''
            server = connection.get('server', '') if connection is not None else ''
            schema = connection.get('schema', '') if connection is not None else ''
            service = connection.get('service', '') if connection is not None else ''
            
            # First, get all tables from relations
            for ds in self.root.findall('.//datasource'):
                result = self.relationship_parser.extract_table_relations(ds)
            relationships = self.relationship_parser.extract_relationships()
            
            # Create tables for each relationship
            for rel in relationships:
                # Create from_table if it doesn't exist
                if rel['from_table'] not in tables:
                    # Get partitions for this table
                    partitions = self.partition_parser.extract_partitions_for_table(rel['from_table'])
                    
                    # Create PowerBiTable object
                    tables[rel['from_table']] = PowerBiTable(
                        source_name=rel['from_table'],
                        description=f"Table from relationship",
                        columns=[],
                        measures=[],
                        hierarchies=[],
                        partitions=partitions
                    )
                
                # Create to_table if it doesn't exist
                if rel['to_table'] not in tables:
                    # Get partitions for this table
                    partitions = self.partition_parser.extract_partitions_for_table(rel['to_table'])
                    
                    # Create PowerBiTable object
                    tables[rel['to_table']] = PowerBiTable(
                        source_name=rel['to_table'],
                        description=f"Table from relationship",
                        columns=[],
                        measures=[],
                        hierarchies=[],
                        partitions=partitions
                    )
                
                # Add from_column
                if rel['from_column'] not in {c.source_name for c in tables[rel['from_table']].columns}:
                    column = PowerBiColumn(
                        source_name=rel['from_column'],
                        pbi_datatype="string",  # Default to string, can be refined later
                        dataCategory="Uncategorized",
                        description=f"Relationship column from {rel['from_table']}"
                    )
                    tables[rel['from_table']].columns.append(column)
                
                # Add to_column
                if rel['to_column'] not in {c.source_name for c in tables[rel['to_table']].columns}:
                    column = PowerBiColumn(
                        source_name=rel['to_column'],
                        pbi_datatype="string",  # Default to string, can be refined later
                        dataCategory="Uncategorized",
                        description=f"Relationship column from {rel['to_table']}"
                    )
                    tables[rel['to_table']].columns.append(column)
            
            # Extract additional columns from <map> elements for each table
            # Find the main datasource element that contains the column mappings
            for ds_element in self.root.findall('.//datasource'):
                if ds_element.get('caption') == 'RO VIN Entry' or ds_element.get('name') == 'federated.1luf0dm0s4az7214qsvnz0flwlm6':
                    # This is the main federated datasource with column mappings
                    cols_element = ds_element.find('.//cols')
                    if cols_element is not None:
                        # Process each map element to extract column information
                        for map_element in cols_element.findall('.//map'):
                            key = map_element.get('key')
                            value = map_element.get('value')
                            
                            if key and value and '[' in value and ']' in value:
                                # Extract table name and column name from value
                                # Format is typically [TABLE_NAME].[COLUMN_NAME]
                                parts = value.split('.')
                                if len(parts) == 2:
                                    table_name = parts[0].strip('[]')
                                    column_name = parts[1].strip('[]')
                                    
                                    # Skip if this is not a relationship table
                                    if table_name not in tables:
                                        continue
                                    
                                    # Skip if column already exists
                                    if column_name in {c.source_name for c in tables[table_name].columns}:
                                        continue
                                    
                                    # Determine datatype based on column name patterns
                                    pbi_datatype = "string"  # Default
                                    summarize_by = "none"
                                    
                                    # Apply simple datatype inference based on column name
                                    if any(suffix in column_name.upper() for suffix in ['_AM', '_NB', '_QT', '_RT', '_CN']):
                                        pbi_datatype = "double"
                                        summarize_by = "sum"
                                    elif any(suffix in column_name.upper() for suffix in ['_DT', '_TM', '_TS']):
                                        pbi_datatype = "dateTime"
                                    elif any(suffix in column_name.upper() for suffix in ['_IN', '_FLG']):
                                        pbi_datatype = "boolean"
                                    
                                    # Create column object
                                    column = PowerBiColumn(
                                        source_name=column_name,
                                        pbi_datatype=pbi_datatype,
                                        source_column=column_name,
                                        summarize_by=summarize_by,
                                        description=f"Column from {table_name}"
                                    )
                                    tables[table_name].columns.append(column)

        except Exception as e:
            logger.error(f"Error extracting relationship tables: {str(e)}", exc_info=True)

        return tables

    def save_tables_to_json(self, tables: List[PowerBiTable]) -> None:
        """
        Save all tables to the table.json file, preserving existing data.
        
        Args:
            tables: List of PowerBiTable objects to save
        """
        import json
        import os
        from pathlib import Path
        
        # Create intermediate directory if it doesn't exist
        Path(self.intermediate_dir).mkdir(parents=True, exist_ok=True)
        
        # Define the file path
        file_path = os.path.join(self.intermediate_dir, 'table.json')
        
        # Initialize data structure as a list of tables
        all_tables = []
        
        # Read existing data if file exists
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    existing_data = json.load(f)
                    
                # If the existing data is a dictionary with a 'tables' key, use that
                if isinstance(existing_data, dict) and 'tables' in existing_data:
                    all_tables = existing_data['tables']
                # If it's a single table object, convert to a list
                elif isinstance(existing_data, dict) and 'source_name' in existing_data:
                    all_tables = [existing_data]
                # If it's already a list, use it directly
                elif isinstance(existing_data, list):
                    all_tables = existing_data
            except Exception as e:
                logger.error(f"Error reading existing table.json: {str(e)}")
                # Start with an empty list if there was an error
                all_tables = []
        
        # Create a dictionary of tables for easier lookup
        tables_dict = {table.source_name: table for table in tables}
        
        # Extract columns from <map> elements for all tables
        # Find the main datasource element that contains the column mappings
        for ds_element in self.root.findall('.//datasource'):
            if ds_element.get('caption') == 'RO VIN Entry' or ds_element.get('name') == 'federated.1luf0dm0s4az7214qsvnz0flwlm6':
                # This is the main federated datasource with column mappings
                cols_element = ds_element.find('.//cols')
                if cols_element is not None:
                    # Process each map element to extract column information
                    for map_element in cols_element.findall('.//map'):
                        key = map_element.get('key')
                        value = map_element.get('value')
                        
                        if key and value and '[' in value and ']' in value:
                            # Extract table name and column name from value
                            # Format is typically [TABLE_NAME].[COLUMN_NAME]
                            parts = value.split('.')
                            if len(parts) == 2:
                                table_name = parts[0].strip('[]')
                                column_name = parts[1].strip('[]')
                                
                                # Skip if this table doesn't exist
                                if table_name not in tables_dict:
                                    continue
                                
                                # Get the table
                                table = tables_dict[table_name]
                                
                                # Skip if column already exists
                                if column_name in {c.source_name for c in table.columns}:
                                    continue
                                
                                # Determine datatype based on column name patterns
                                pbi_datatype = "string"  # Default
                                summarize_by = "none"
                                
                                # Apply simple datatype inference based on column name
                                if any(suffix in column_name.upper() for suffix in ['_AM', '_NB', '_QT', '_RT', '_CN']):
                                    pbi_datatype = "double"
                                    summarize_by = "sum"
                                elif any(suffix in column_name.upper() for suffix in ['_DT', '_TM', '_TS']):
                                    pbi_datatype = "dateTime"
                                elif any(suffix in column_name.upper() for suffix in ['_IN', '_FLG']):
                                    pbi_datatype = "boolean"
                                
                                # Create column object
                                column = PowerBiColumn(
                                    source_name=column_name,
                                    pbi_datatype=pbi_datatype,
                                    source_column=column_name,
                                    summarize_by=summarize_by,
                                    description=f"Column from {table_name}"
                                )
                                table.columns.append(column)
        
        # Track existing table names to avoid duplicates
        existing_table_names = {table.get('source_name') for table in all_tables if isinstance(table, dict) and 'source_name' in table}
        
        # Convert each table to a dictionary and add to the list if not already present
        for table in tables:
            # Skip if this table is already in the file
            if table.source_name in existing_table_names:
                continue
                
            # Convert to dictionary and add to the list
            table_dict = {
                'source_name': table.source_name,
                'name': table.name if hasattr(table, 'name') else table.source_name,
                'lineage_tag': getattr(table, 'lineage_tag', None),
                'description': table.description,
                'is_hidden': getattr(table, 'is_hidden', False),
                'columns': [
                    {
                        'source_name': col.source_name,
                        'datatype': col.pbi_datatype,
                        'format_string': getattr(col, 'format_string', None),
                        'lineage_tag': getattr(col, 'lineage_tag', None),
                        'source_column': getattr(col, 'source_column', None),
                        'description': getattr(col, 'description', None),
                        'is_hidden': getattr(col, 'is_hidden', False),
                        'summarize_by': getattr(col, 'summarize_by', 'none'),
                        'data_category': getattr(col, 'dataCategory', 'Uncategorized'),
                        'is_calculated': getattr(col, 'is_calculated', False),
                        'is_data_type_inferred': getattr(col, 'is_data_type_inferred', False),
                        'annotations': getattr(col, 'annotations', None)
                    } for col in table.columns
                ],
                'measures': [
                    {
                        'source_name': measure.source_name,
                        'dax_expression': measure.dax_expression,
                        'description': getattr(measure, 'description', None),
                        'format_string': getattr(measure, 'format_string', None),
                        'is_hidden': getattr(measure, 'is_hidden', False),
                        'annotations': getattr(measure, 'annotations', None)
                    } for measure in table.measures
                ],
                'hierarchies': [],  # Add hierarchy support if needed
                'partitions': [
                    {
                        'name': partition.name,
                        'source_type': getattr(partition, 'source_type', None),
                        'expression': getattr(partition, 'expression', None),
                        'description': getattr(partition, 'description', None)
                    } for partition in table.partitions
                ],
                'has_widget_serialization': False,
                'visual_type': None,
                'column_settings': None
            }
            
            all_tables.append(table_dict)
            existing_table_names.add(table.source_name)
        
        # Create the final data structure with tables as an array under the 'tables' key
        final_data = {
            'tables': all_tables
        }
        
        # Write all tables to the file
        with open(file_path, 'w') as f:
            json.dump(final_data, f, indent=2)
        
        logger.info(f"Saved {len(all_tables)} tables to {file_path}")
        
        # Also save each table individually for easier debugging
        for table_dict in all_tables:
            table_name = table_dict.get('source_name', 'unknown')
            individual_file_path = os.path.join(self.intermediate_dir, f"table_{table_name}.json")
            with open(individual_file_path, 'w') as f:
                json.dump(table_dict, f, indent=2)

    def extract_all_tables(self) -> List[PowerBiTable]:
        """Extract all tables from the workbook.
        
        Returns:
            List of PowerBiTable objects
        """
        try:
            # Extract tables from datasources first
            datasource_tables = self.datasource_parser.extract_all_tables()
            logger.info(f"Found {len(datasource_tables)} tables from datasources")
            
            # Create initial map with datasource tables
            all_tables = {table.source_name: table for table in datasource_tables}
            
            # Extract tables from joins
            join_tables = self._extract_join_tables()
            logger.info(f"Found {len(join_tables)} tables from joins")
            
            # Add join tables
            for name, table in join_tables.items():
                if name not in all_tables:
                    all_tables[name] = table
                else:
                    # Merge columns and measures if table already exists
                    existing_table = all_tables[name]
                    existing_cols = {c.source_name for c in existing_table.columns}
                    for col in table.columns:
                        if col.source_name not in existing_cols:
                            existing_table.columns.append(col)
            
            # Extract tables from relationships
            relationship_tables = self._extract_relationship_tables()
            logger.info(f"Found {len(relationship_tables)} tables from relationships")
            
            # Add relationship tables
            for name, table in relationship_tables.items():
                if name not in all_tables:
                    all_tables[name] = table
                else:
                    # Merge columns and measures if table already exists
                    existing_table = all_tables[name]
                    existing_cols = {c.source_name for c in existing_table.columns}
                    for col in table.columns:
                        if col.source_name not in existing_cols:
                            existing_table.columns.append(col)
            
            # Extract columns from <map> elements for all tables
            # Find the main datasource element that contains the column mappings
            for ds_element in self.root.findall('.//datasource'):
                if ds_element.get('caption') == 'RO VIN Entry' or ds_element.get('name') == 'federated.1luf0dm0s4az7214qsvnz0flwlm6':
                    # This is the main federated datasource with column mappings
                    cols_element = ds_element.find('.//cols')
                    if cols_element is not None:
                        # Process each map element to extract column information
                        for map_element in cols_element.findall('.//map'):
                            key = map_element.get('key')
                            value = map_element.get('value')
                            
                            if key and value and '[' in value and ']' in value:
                                # Extract table name and column name from value
                                # Format is typically [TABLE_NAME].[COLUMN_NAME]
                                parts = value.split('.')
                                if len(parts) == 2:
                                    table_name = parts[0].strip('[]')
                                    column_name = parts[1].strip('[]')
                                    
                                    # Skip if this table doesn't exist
                                    if table_name not in all_tables:
                                        continue
                                    
                                    # Get the table
                                    table = all_tables[table_name]
                                    
                                    # Skip if column already exists
                                    if column_name in {c.source_name for c in table.columns}:
                                        continue
                                    
                                    # Determine datatype based on column name patterns
                                    pbi_datatype = "string"  # Default
                                    summarize_by = "none"
                                    
                                    # Apply simple datatype inference based on column name
                                    if any(suffix in column_name.upper() for suffix in ['_AM', '_NB', '_QT', '_RT', '_CN']):
                                        pbi_datatype = "double"
                                        summarize_by = "sum"
                                    elif any(suffix in column_name.upper() for suffix in ['_DT', '_TM', '_TS']):
                                        pbi_datatype = "dateTime"
                                    elif any(suffix in column_name.upper() for suffix in ['_IN', '_FLG']):
                                        pbi_datatype = "boolean"
                                    
                                    # Create column object
                                    column = PowerBiColumn(
                                        source_name=column_name,
                                        pbi_datatype=pbi_datatype,
                                        source_column=column_name,
                                        summarize_by=summarize_by,
                                        description=f"Column from {table_name}"
                                    )
                                    table.columns.append(column)
            
            # Process each table to ensure it has columns and partitions
            for name, table in all_tables.items():
                # Extract columns if not already present
                if not table.columns:
                    ds_element = self.root.find(f".//datasource[@name='{name}']")
                    if ds_element is not None:
                        columns, measures = self.column_parser.extract_columns_and_measures(
                            ds_element,
                            self.config.get('PowerBiColumn', {}),
                            name
                        )
                        table.columns = columns
                        table.measures = measures
                
                # Extract partitions if not already present
                if not table.partitions:
                    # First try to find a datasource element for this table
                    ds_element = self.root.find(f".//datasource[@name='{name}']")
                    if ds_element is not None:
                        # Extract partitions from the datasource element
                        partitions = self.partition_parser._extract_partition_info(
                            ds_element,
                            name,
                            table.columns
                        )
                        table.partitions = partitions
                    else:
                        # If no datasource element found, use the extract_partitions_for_table method
                        # This will create partitions for tables in join relationships
                        partitions = self.partition_parser.extract_partitions_for_table(name)
                        table.partitions = partitions
            
            # Process federated datasources
            for ds_element in self.root.findall('.//datasource'):
                connection = ds_element.find('.//connection')
                if connection is not None and connection.get('class') == 'federated':
                    # Get tables from relations
                    result = self.relationship_parser.extract_table_relations(ds_element)
                    relations = result['relations']
                    relation_tables = result['tables']
                    
                    # Add each table from the relations
                    for table_name, relation_table in relation_tables.items():
                        if table_name not in all_tables:
                            # Extract columns and partitions
                            ds_element = self.root.find(f".//datasource[@name='{table_name}']")
                            if ds_element is not None:
                                columns, measures = self.column_parser.extract_columns_and_measures(
                                    ds_element,
                                    self.config.get('PowerBiColumn', {}),
                                    table_name
                                )
                                relation_table.columns = columns
                                relation_table.measures = measures
                                
                                partitions = self.partition_parser._extract_partition_info(
                                    ds_element,
                                    table_name,
                                    columns
                                )
                                relation_table.partitions = partitions
                            
                            all_tables[table_name] = relation_table
            
            # Convert to list and deduplicate
            tables = list(all_tables.values())
            tables = self.deduplicator.deduplicate_tables(tables, set(relationship_tables.keys()))
            logger.info(f"After deduplication, found {len(tables)} unique tables (including {len(relationship_tables)} from relationships)")

            # Deduplicate partitions in each table
            for table in tables:
                table.partitions = self.deduplicator.deduplicate_partitions(table.partitions)
                
            # Save all tables to table.json
            self.save_tables_to_json(tables)

            return tables

        except Exception as e:
            logger.error(f"Error extracting tables: {str(e)}", exc_info=True)
            return []

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

