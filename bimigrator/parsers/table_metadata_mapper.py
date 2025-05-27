"""Mapper for handling datasource to table mapping in Tableau workbooks."""
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Tuple, Set, Optional

from bimigrator.common.logging import logger
from bimigrator.config.data_classes import PowerBiTable, PowerBiColumn, PowerBiMeasure, PowerBiPartition
from bimigrator.parsers.connections.connection_factory import ConnectionParserFactory
from bimigrator.parsers.column_parser import ColumnParser


class TableMetadataMapper:
    """Maps Tableau datasources to Power BI tables with proper column associations."""
    
    def __init__(self, config: Dict[str, Any], column_parser: ColumnParser):
        """Initialize TableMetadataMapper.
        
        Args:
            config: Configuration dictionary
            column_parser: Column parser instance
        """
        self.config = config
        self.column_parser = column_parser
        self.connection_factory = ConnectionParserFactory(config)
        
    def identify_datasource_type(self, ds_element: ET.Element) -> str:
        """Identify the type of datasource.
        
        Args:
            ds_element: Datasource element
            
        Returns:
            String identifying the datasource type
        """
        connection = ds_element.find('.//connection')
        if connection is None:
            logger.info(f"Datasource {ds_element.get('name', 'unknown')} has no connection, skipping")
            return "unknown"
            
        conn_class = connection.get('class', '')
        logger.info(f"Datasource {ds_element.get('name', 'unknown')} has connection class: {conn_class}")
        
        # Check for federated datasource
        if conn_class == 'federated':
            logger.info(f"Identified federated datasource: {ds_element.get('name', 'unknown')}")
            return "federated"
            
        # Check for parameter datasource
        if ds_element.find('.//column[@param-domain-type]') is not None:
            logger.info(f"Identified parameter datasource: {ds_element.get('name', 'unknown')}")
            return "parameter"
            
        # Check for SQL query datasource
        relation = connection.find('.//relation[@type="text"]')
        if relation is not None:
            logger.info(f"Identified SQL query datasource: {ds_element.get('name', 'unknown')}")
            return "sql_query"
            
        # Check for multi-table datasource by looking at relations
        relations = connection.findall('.//relation')
        joins = connection.findall('.//relation/join')
        
        if len(joins) > 0:
            logger.info(f"Identified multi-table join datasource: {ds_element.get('name', 'unknown')}")
            return "multi_table_join"
            
        if len(relations) > 1:
            logger.info(f"Identified multi-table datasource: {ds_element.get('name', 'unknown')}")
            return "multi_table"
            
        # Check for Excel datasource
        if conn_class == 'excel-direct':
            logger.info(f"Identified Excel datasource: {ds_element.get('name', 'unknown')}")
            return "excel"
        
        # Default to single-table
        logger.info(f"Identified single-table datasource: {ds_element.get('name', 'unknown')}")
        return "single_table"
    
    def extract_table_name_from_datasource(self, ds_element: ET.Element) -> str:
        """Extract table name from datasource element.
        
        Args:
            ds_element: Datasource element
            
        Returns:
            Table name
        """
        ds_name = ds_element.get('name', '')
        ds_caption = ds_element.get('caption', ds_name)
        
        connection = ds_element.find('.//connection')
        if connection is None:
            return ds_caption or ds_name
            
        conn_class = connection.get('class', '')
        
        # For Excel datasources, use sheet name
        if conn_class == 'excel-direct':
            relation = connection.find('.//relation')
            if relation is not None:
                sheet_name = relation.get('name')
                if sheet_name:
                    file_name = self._extract_file_name_from_connection(connection)
                    if file_name:
                        return f"{sheet_name} ({file_name})"
                    return sheet_name
        
        # For other datasources, use caption or name
        return ds_caption or ds_name
    
    def _extract_file_name_from_connection(self, connection: ET.Element) -> Optional[str]:
        """Extract file name from connection element.
        
        Args:
            connection: Connection element
            
        Returns:
            File name or None if not found
        """
        # Try to get filename from dbname attribute
        dbname = connection.get('dbname', '')
        if dbname:
            # Extract just the file name without path or extension
            import os
            file_base = os.path.basename(dbname)
            file_name = os.path.splitext(file_base)[0]
            return file_name
            
        # Try to get filename from named-connection
        named_connection = connection.find('.//named-connection')
        if named_connection is not None:
            connection_name = named_connection.get('name', '')
            if connection_name:
                # Remove any special characters or prefixes
                import re
                file_name = re.sub(r'^excel\.|.xlsx$', '', connection_name)
                return file_name
                
        return None
        
    def _extract_partitions(self, ds_element: ET.Element, table_name: str, columns: List[PowerBiColumn]) -> List[PowerBiPartition]:
        """Extract partition information from a datasource element.
        
        Args:
            ds_element: Datasource element
            table_name: Name of the table
            columns: List of columns for the table
            
        Returns:
            List of PowerBiPartition objects
        """
        partitions = []
        try:
            # Find the connection element
            connection = ds_element.find('.//connection')
            if connection is not None:
                # Get the appropriate connection parser
                parser = self.connection_factory.get_parser(connection)
                
                # Find relation elements
                relations = connection.findall('.//relation')
                
                # If no relations found, try with wildcard namespace
                if not relations:
                    for element in connection.findall('.//*'):
                        if element.tag.endswith('relation'):
                            relations.append(element)
                
                # Process each relation
                for relation in relations:
                    logger.info(f"Processing relation for table {table_name}: {relation.attrib}")
                    new_partitions = parser.extract_partition_info(connection, relation, table_name, columns)
                    logger.info(f"Generated {len(new_partitions)} partitions for relation")
                    partitions.extend(new_partitions)
                    
                    # If we found partitions, we can stop
                    if partitions:
                        break
                
                # If no partitions were found, create a default one
                if not partitions:
                    # Try to determine the connection type
                    conn_class = connection.get('class', '')
                    if conn_class == 'excel-direct':
                        # Create a default Excel partition
                        dbname = connection.get('dbname', '')
                        sheet_name = table_name.split(' ')[0] if ' ' in table_name else table_name
                        
                        # Generate a simple M code for Excel
                        m_code = f"""	let
					Source = Excel.Workbook(File.Contents("{dbname}"), null, true),
					{sheet_name}_Sheet = Source{{[Item="{sheet_name}",Kind="Sheet"]}}[Data],
					#"Promoted Headers" = Table.PromoteHeaders({sheet_name}_Sheet, [PromoteAllScalars=true])
				in
					#"Promoted Headers"""
                        
                        partition = PowerBiPartition(
                            name=sheet_name,
                            source_type="m",
                            expression=m_code
                        )
                        partitions.append(partition)
                    elif conn_class in ['sqlserver', 'oracle', 'mysql', 'postgres']:
                        # Create a default SQL partition
                        server = connection.get('server', '')
                        database = connection.get('dbname', '')
                        schema = connection.get('schema', '')
                        
                        # Generate a simple M code for SQL
                        m_code = f"""	let
					Source = Sql.Database("{server}", "{database}"),
					{table_name} = Source{{[Schema="{schema}",Item="{table_name}"]}}[Data]
				in
					{table_name}"""
                        
                        partition = PowerBiPartition(
                            name=table_name,
                            source_type="m",
                            expression=m_code
                        )
                        partitions.append(partition)
                    else:
                        # Create a generic partition
                        partition = PowerBiPartition(
                            name=table_name,
                            source_type="m",
                            expression=f"// TODO: Generate M code for {conn_class} connection\n"
                        )
                        partitions.append(partition)
        except Exception as e:
            logger.error(f"Error extracting partition info: {str(e)}", exc_info=True)
            
        return partitions
    
    def process_single_table_datasource(self, ds_element: ET.Element, seen_table_names: Set[str]) -> List[PowerBiTable]:
        """Process a datasource that maps to a single table.
        
        Args:
            ds_element: Datasource element
            seen_table_names: Set of already used table names
            
        Returns:
            List containing a single PowerBiTable
        """
        # Get datasource name and caption
        ds_name = ds_element.get('name', '')
        
        # Extract table name
        table_name = self.extract_table_name_from_datasource(ds_element)
        
        # Create a unique table name if needed
        final_table_name = table_name
        counter = 1
        while final_table_name in seen_table_names:
            final_table_name = f"{table_name}_{counter}"
            counter += 1
        
        # Extract all columns, measures, hierarchies directly
        columns, measures = self.column_parser.extract_columns_and_measures(
            ds_element, 
            self.config.get('PowerBiColumn', {}),
            final_table_name
        )
        
        # Extract partitions
        partitions = self._extract_partitions(ds_element, final_table_name, columns)
        
        # Create a single table with the datasource name
        table = PowerBiTable(
            source_name=final_table_name,
            description=f"Single-table datasource from {ds_name}",
            columns=columns,
            measures=measures,
            hierarchies=[],
            partitions=partitions
        )
        
        return [table]
    
    def process_excel_datasource(self, ds_element: ET.Element, seen_table_names: Set[str]) -> List[PowerBiTable]:
        """Process an Excel datasource.
        
        Args:
            ds_element: Datasource element
            seen_table_names: Set of already used table names
            
        Returns:
            List containing a single PowerBiTable
        """
        # Excel datasources are essentially single-table datasources with special naming
        return self.process_single_table_datasource(ds_element, seen_table_names)
    
    def process_sql_query_datasource(self, ds_element: ET.Element, seen_table_names: Set[str]) -> List[PowerBiTable]:
        """Process a datasource based on a SQL query.
        
        Args:
            ds_element: Datasource element
            seen_table_names: Set of already used table names
            
        Returns:
            List containing a single PowerBiTable
        """
        # Get datasource name and caption
        ds_name = ds_element.get('name', '')
        ds_caption = ds_element.get('caption', ds_name)
        
        # Create a unique table name if needed
        table_name = ds_caption or ds_name
        final_table_name = table_name
        counter = 1
        while final_table_name in seen_table_names:
            final_table_name = f"{table_name}_{counter}"
            counter += 1
        
        # Extract columns
        columns, measures = self.column_parser.extract_columns_and_measures(
            ds_element,
            self.config.get('PowerBiColumn', {}),
            final_table_name
        )
        
        # Get the SQL query for description
        connection = ds_element.find('.//connection')
        relation = connection.find('.//relation[@type="text"]') if connection is not None else None
        sql_query = relation.text if relation is not None else ""
        sql_snippet = sql_query[:100] + "..." if len(sql_query) > 100 else sql_query
        
        # Extract partitions
        partitions = self._extract_partitions(ds_element, final_table_name, columns)
        
        # Create a table for this query
        table = PowerBiTable(
            source_name=final_table_name,
            description=f"SQL Query table: {final_table_name}\nQuery: {sql_snippet}",
            columns=columns,
            measures=measures,
            hierarchies=[],
            partitions=partitions
        )
        
        return [table]
    
    def process_multi_table_datasource(self, ds_element: ET.Element, seen_table_names: Set[str]) -> List[PowerBiTable]:
        """Process a datasource that contains multiple tables.
        
        Args:
            ds_element: Datasource element
            seen_table_names: Set of already used table names
            
        Returns:
            List of PowerBiTable objects
        """
        # Get datasource name for logging
        ds_name = ds_element.get('name', '')
        logger.info(f"Processing multi-table datasource: {ds_name}")
        
        # Extract all columns from the datasource
        all_columns, all_measures = self.column_parser.extract_columns_and_measures(
            ds_element,
            self.config.get('PowerBiColumn', {}),
            ""  # No table name prefix yet
        )
        
        # Extract table names from relations
        tables = []
        connection = ds_element.find('.//connection')
        if connection is not None:
            relations = connection.findall('.//relation')
            for relation in relations:
                # Skip join relations
                if relation.find('./join') is not None:
                    continue
                    
                # Get table name from relation
                table_name = relation.get('name', '')
                if not table_name:
                    continue
                    
                # Create a unique table name if needed
                final_table_name = table_name
                counter = 1
                while final_table_name in seen_table_names:
                    final_table_name = f"{table_name}_{counter}"
                    counter += 1
                seen_table_names.add(final_table_name)
                
                # Associate columns with this table based on naming patterns
                table_columns = self._associate_columns_with_table(all_columns, table_name)
                table_measures = self._associate_measures_with_table(all_measures, table_name)
                
                # Create table
                table = PowerBiTable(
                    source_name=final_table_name,
                    description=f"Table from multi-table datasource: {ds_name}",
                    columns=table_columns,
                    measures=table_measures,
                    hierarchies=[],
                    partitions=[]  # Partitions will be added by the partition parser
                )
                
                tables.append(table)
        
        # If no tables were created, create a single table with all columns
        if not tables:
            # Use datasource name for the table
            ds_caption = ds_element.get('caption', ds_name)
            final_table_name = ds_caption or ds_name
            counter = 1
            while final_table_name in seen_table_names:
                final_table_name = f"{final_table_name}_{counter}"
                counter += 1
            seen_table_names.add(final_table_name)
            
            # Extract partitions
            partitions = self._extract_partitions(ds_element, final_table_name, all_columns)
            
            # Create table with all columns
            table = PowerBiTable(
                source_name=final_table_name,
                description=f"Combined table from multi-table datasource: {ds_name}",
                columns=all_columns,
                measures=all_measures,
                hierarchies=[],
                partitions=partitions
            )
            
            tables.append(table)
        
        return tables
    
    def process_multi_table_join_datasource(self, ds_element: ET.Element, seen_table_names: Set[str]) -> List[PowerBiTable]:
        """Process a datasource with joined tables.
        
        Args:
            ds_element: Datasource element
            seen_table_names: Set of already used table names
            
        Returns:
            List of PowerBiTable objects
        """
        # Get datasource name for logging
        ds_name = ds_element.get('name', '')
        logger.info(f"Processing multi-table join datasource: {ds_name}")
        
        # Extract all columns from the datasource
        all_columns, all_measures = self.column_parser.extract_columns_and_measures(
            ds_element,
            self.config.get('PowerBiColumn', {}),
            ""  # No table name prefix yet
        )
        
        # Extract tables from join relations
        tables = []
        table_names = set()
        connection = ds_element.find('.//connection')
        
        if connection is not None:
            # Process join relations
            join_relations = connection.findall('.//relation/join')
            for join in join_relations:
                # Extract left and right clauses
                clauses = join.findall('.//clause')
                for clause in clauses:
                    expressions = clause.findall('.//expression')
                    for expr in expressions:
                        op = expr.get('op', '')
                        if '[' in op and '].[' in op:
                            # Extract table name from expression like [Table].[Column]
                            table_name = op.split('].[')[0].strip('[')
                            if table_name and table_name not in table_names:
                                table_names.add(table_name)
        
        # Create tables for each table name found
        for table_name in table_names:
            # Create a unique table name if needed
            final_table_name = table_name
            counter = 1
            while final_table_name in seen_table_names:
                final_table_name = f"{table_name}_{counter}"
                counter += 1
            seen_table_names.add(final_table_name)
            
            # Associate columns with this table based on naming patterns
            table_columns = self._associate_columns_with_table(all_columns, table_name)
            table_measures = self._associate_measures_with_table(all_measures, table_name)
            
            # Extract partitions
            partitions = self._extract_partitions(ds_element, final_table_name, table_columns)
            
            # Create table
            table = PowerBiTable(
                source_name=final_table_name,
                description=f"Table from join relation in datasource: {ds_name}",
                columns=table_columns,
                measures=table_measures,
                hierarchies=[],
                partitions=partitions
            )
            
            tables.append(table)
        
        # If no tables were created, create a single table with all columns
        if not tables:
            # Use datasource name for the table
            ds_caption = ds_element.get('caption', ds_name)
            final_table_name = ds_caption or ds_name
            counter = 1
            while final_table_name in seen_table_names:
                final_table_name = f"{final_table_name}_{counter}"
                counter += 1
            seen_table_names.add(final_table_name)
            
            # Extract partitions
            partitions = self._extract_partitions(ds_element, final_table_name, all_columns)
            
            # Create table with all columns
            table = PowerBiTable(
                source_name=final_table_name,
                description=f"Combined table from join datasource: {ds_name}",
                columns=all_columns,
                measures=all_measures,
                hierarchies=[],
                partitions=partitions
            )
            
            tables.append(table)
        
        return tables
    
    def process_federated_datasource(self, ds_element: ET.Element, seen_table_names: Set[str], root: ET.Element) -> List[PowerBiTable]:
        """Process a federated datasource that combines multiple sources.
        
        Args:
            ds_element: Datasource element
            seen_table_names: Set of already used table names
            root: Root element of the workbook
            
        Returns:
            List of PowerBiTable objects
        """
        # Get datasource name for logging
        ds_name = ds_element.get('name', '')
        logger.info(f"Processing federated datasource: {ds_name}")
        
        tables = []
        connection = ds_element.find('.//connection')
        
        if connection is not None and connection.get('class') == 'federated':
            # Get all relations in this federated datasource
            relations = connection.findall('.//relation')
            
            for relation in relations:
                # Extract table name from relation
                table_name = relation.get('name', '')
                if not table_name:
                    continue
                
                # Create a unique table name if needed
                final_table_name = table_name
                counter = 1
                while final_table_name in seen_table_names:
                    final_table_name = f"{table_name}_{counter}"
                    counter += 1
                seen_table_names.add(final_table_name)
                
                # Try to find the corresponding datasource for this table
                source_ds = None
                for ds in root.findall('.//datasource'):
                    if ds.get('name') == table_name or ds.get('caption') == table_name:
                        source_ds = ds
                        break
                
                if source_ds is not None:
                    # Process this datasource and add its table
                    ds_type = self.identify_datasource_type(source_ds)
                    if ds_type == "single_table":
                        table = self.process_single_table_datasource(source_ds, seen_table_names)[0]
                    elif ds_type == "excel":
                        table = self.process_excel_datasource(source_ds, seen_table_names)[0]
                    elif ds_type == "sql_query":
                        table = self.process_sql_query_datasource(source_ds, seen_table_names)[0]
                    else:
                        # For other types, just extract columns directly
                        columns, measures = self.column_parser.extract_columns_and_measures(
                            source_ds,
                            self.config.get('PowerBiColumn', {}),
                            final_table_name
                        )
                        
                        # Extract partitions
                        partitions = self._extract_partitions(source_ds, final_table_name, columns)
                        
                        table = PowerBiTable(
                            source_name=final_table_name,
                            description=f"Table from federated datasource: {ds_name}",
                            columns=columns,
                            measures=measures,
                            hierarchies=[],
                            partitions=partitions
                        )
                    
                    tables.append(table)
                else:
                    # Extract columns directly from the federated datasource
                    columns, measures = self.column_parser.extract_columns_and_measures(
                        ds_element,
                        self.config.get('PowerBiColumn', {}),
                        final_table_name
                    )
                    
                    # Filter columns that belong to this table
                    table_columns = self._associate_columns_with_table(columns, table_name)
                    table_measures = self._associate_measures_with_table(measures, table_name)
                    
                    # Extract partitions
                    partitions = self._extract_partitions(ds_element, final_table_name, table_columns)
                    
                    # Create a simple table from the relation
                    table = PowerBiTable(
                        source_name=final_table_name,
                        description=f"Table from federated relation: {table_name}",
                        columns=table_columns,
                        measures=table_measures,
                        hierarchies=[],
                        partitions=partitions
                    )
                    
                    tables.append(table)
        
        # If no tables were created, create a single table with all columns
        if not tables:
            # Extract all columns from the datasource
            all_columns, all_measures = self.column_parser.extract_columns_and_measures(
                ds_element,
                self.config.get('PowerBiColumn', {}),
                ""  # No table name prefix yet
            )
            
            # Use datasource name for the table
            ds_caption = ds_element.get('caption', ds_name)
            final_table_name = ds_caption or ds_name
            counter = 1
            while final_table_name in seen_table_names:
                final_table_name = f"{final_table_name}_{counter}"
                counter += 1
            seen_table_names.add(final_table_name)
            
            # Extract partitions
            partitions = self._extract_partitions(ds_element, final_table_name, all_columns)
            
            # Create table with all columns
            table = PowerBiTable(
                source_name=final_table_name,
                description=f"Combined table from federated datasource: {ds_name}",
                columns=all_columns,
                measures=all_measures,
                hierarchies=[],
                partitions=partitions
            )
            
            tables.append(table)
        
        return tables
    
    def process_parameter_datasource(self, ds_element: ET.Element, seen_table_names: Set[str]) -> List[PowerBiTable]:
        """Process a parameter datasource.
        
        Args:
            ds_element: Datasource element
            seen_table_names: Set of already used table names
            
        Returns:
            List containing a single PowerBiTable
        """
        # Get parameter information
        param_name = ds_element.get('name', '')
        param_caption = ds_element.get('caption', param_name)
        
        # Create a unique table name if needed
        table_name = param_caption or param_name
        final_table_name = table_name
        counter = 1
        while final_table_name in seen_table_names:
            final_table_name = f"{table_name}_{counter}"
            counter += 1
        seen_table_names.add(final_table_name)
        
        # Extract columns
        columns, measures = self.column_parser.extract_columns_and_measures(
            ds_element,
            self.config.get('PowerBiColumn', {}),
            final_table_name
        )
        
        # Extract partitions
        partitions = self._extract_partitions(ds_element, final_table_name, columns)
        
        # Create a parameter table
        table = PowerBiTable(
            source_name=final_table_name,
            description=f"Parameter table for {param_name}",
            columns=columns,
            measures=measures,
            hierarchies=[],
            partitions=partitions
        )
        
        return [table]
    
    def _associate_columns_with_table(self, columns: List[PowerBiColumn], table_name: str) -> List[PowerBiColumn]:
        """Associate columns with a specific table based on naming patterns.
        
        Args:
            columns: List of all columns
            table_name: Name of the table to associate columns with
            
        Returns:
            List of columns associated with the table
        """
        table_columns = []
        
        for column in columns:
            # Check if column belongs to this table
            column_name = column.source_name
            
            # Case 1: Column explicitly references table in source_column
            if hasattr(column, 'source_column') and column.source_column:
                source_col = column.source_column
                if f"[{table_name}]" in source_col or f"'{table_name}'" in source_col:
                    table_columns.append(column)
                    continue
            
            # Case 2: Column name matches pattern [Table].[Column]
            if '[' in column_name and '].[' in column_name:
                col_table_name = column_name.split('].[')[0].strip('[')
                if col_table_name == table_name:
                    table_columns.append(column)
                    continue
            
            # Case 3: Column description mentions the table
            if hasattr(column, 'description') and column.description:
                if f"from {table_name}" in column.description:
                    table_columns.append(column)
                    continue
            
            # Case 4: Simple heuristic - if no other criteria match and the column
            # doesn't explicitly belong to another table, include it
            belongs_to_other_table = False
            for other_col in columns:
                if other_col != column and hasattr(other_col, 'source_column') and other_col.source_column:
                    source_col = other_col.source_column
                    if '[' in source_col and ']' in source_col:
                        other_table = source_col.split(']')[0].strip('[')
                        if other_table != table_name and other_table in column_name:
                            belongs_to_other_table = True
                            break
            
            if not belongs_to_other_table:
                table_columns.append(column)
        
        return table_columns
    
    def _associate_measures_with_table(self, measures: List[PowerBiMeasure], table_name: str) -> List[PowerBiMeasure]:
        """Associate measures with a specific table based on naming patterns.
        
        Args:
            measures: List of all measures
            table_name: Name of the table to associate measures with
            
        Returns:
            List of measures associated with the table
        """
        table_measures = []
        
        for measure in measures:
            # Check if measure belongs to this table
            
            # Case 1: Measure expression references this table
            if hasattr(measure, 'expression') and measure.expression:
                if f"[{table_name}]" in measure.expression or f"'{table_name}'" in measure.expression:
                    table_measures.append(measure)
                    continue
            
            # Case 2: Measure description mentions the table
            if hasattr(measure, 'description') and measure.description:
                if f"from {table_name}" in measure.description:
                    table_measures.append(measure)
                    continue
        
        return table_measures
    
    def process_datasource(self, ds_element: ET.Element, seen_table_names: Set[str], root: ET.Element) -> List[PowerBiTable]:
        """Process a datasource and map it to Power BI tables.
        
        Args:
            ds_element: Datasource element
            seen_table_names: Set of already used table names
            root: Root element of the workbook
            
        Returns:
            List of PowerBiTable objects
        """
        ds_type = self.identify_datasource_type(ds_element)
        
        if ds_type == "single_table":
            return self.process_single_table_datasource(ds_element, seen_table_names)
        elif ds_type == "excel":
            return self.process_excel_datasource(ds_element, seen_table_names)
        elif ds_type == "multi_table":
            return self.process_multi_table_datasource(ds_element, seen_table_names)
        elif ds_type == "multi_table_join":
            return self.process_multi_table_join_datasource(ds_element, seen_table_names)
        elif ds_type == "federated":
            return self.process_federated_datasource(ds_element, seen_table_names, root)
        elif ds_type == "sql_query":
            return self.process_sql_query_datasource(ds_element, seen_table_names)
        elif ds_type == "parameter":
            return self.process_parameter_datasource(ds_element, seen_table_names)
        else:
            # Unknown type, use default processing
            logger.warning(f"Unknown datasource type: {ds_type}, using default processing")
            return self.process_single_table_datasource(ds_element, seen_table_names)
    
    def map_datasources_to_tables(self, root: ET.Element) -> List[PowerBiTable]:
        """Map all datasources in a workbook to Power BI tables.
        
        Args:
            root: Root element of the workbook
            
        Returns:
            List of PowerBiTable objects
        """
        tables = []
        seen_table_names = set()
        
        # Get all datasources
        datasources = root.findall('.//datasource')
        logger.info(f"Found {len(datasources)} datasources")
        
        # Process each datasource
        for ds_element in datasources:
            # Skip datasources without a connection
            connection = ds_element.find('.//connection')
            if connection is None:
                logger.info(f"Skipping datasource {ds_element.get('name', 'unknown')} - no connection found")
                continue
                
            # Process datasource
            ds_tables = self.process_datasource(ds_element, seen_table_names, root)
            tables.extend(ds_tables)
            
            logger.info(f"Processed datasource {ds_element.get('name', 'unknown')}, created {len(ds_tables)} tables")
        
        # Filter out empty tables
        filtered_tables = []
        for table in tables:
            if table.columns or table.measures:
                filtered_tables.append(table)
            else:
                logger.info(f"Filtering out empty table: {table.source_name}")
        
        logger.info(f"Created {len(filtered_tables)} tables from {len(datasources)} datasources")
        return filtered_tables
