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
            # Get relationships from relationship parser
            relationships = self.relationship_parser.extract_relationships()
            
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
            
            # Create tables for each relationship
            for rel in relationships:
                # Process from_table
                if rel.from_table not in tables:
                    mock_ds = ET.Element('datasource')
                    mock_conn = ET.SubElement(mock_ds, 'connection')
                    mock_conn.set('class', conn_class)
                    mock_conn.set('server', server)
                    mock_conn.set('schema', schema)
                    mock_conn.set('service', service)
                    
                    partitions = self.partition_parser._extract_partition_info(
                        mock_ds,
                        rel.from_table,
                        None  # No columns yet
                    )
                    
                    tables[rel.from_table] = PowerBiTable(
                        source_name=rel.from_table,
                        description=f"Table from relationship",
                        columns=[],
                        measures=[],
                        hierarchies=[],
                        partitions=partitions
                    )
                
                # Add from_column
                if rel.from_column not in {c.source_name for c in tables[rel.from_table].columns}:
                    column = PowerBiColumn(
                        source_name=rel.from_column,
                        pbi_datatype="string",  # Default to string, can be refined later
                        dataCategory="Uncategorized",
                        description=f"Relationship column from {rel.from_table}"
                    )
                    tables[rel.from_table].columns.append(column)
                
                # Process to_table
                if rel.to_table not in tables:
                    mock_ds = ET.Element('datasource')
                    mock_conn = ET.SubElement(mock_ds, 'connection')
                    mock_conn.set('class', conn_class)
                    mock_conn.set('server', server)
                    mock_conn.set('schema', schema)
                    mock_conn.set('service', service)
                    
                    partitions = self.partition_parser._extract_partition_info(
                        mock_ds,
                        rel.to_table,
                        None  # No columns yet
                    )
                    
                    tables[rel.to_table] = PowerBiTable(
                        source_name=rel.to_table,
                        description=f"Table from relationship",
                        columns=[],
                        measures=[],
                        hierarchies=[],
                        partitions=partitions
                    )
                
                # Add to_column
                if rel.to_column not in {c.source_name for c in tables[rel.to_table].columns}:
                    column = PowerBiColumn(
                        source_name=rel.to_column,
                        pbi_datatype="string",  # Default to string, can be refined later
                        dataCategory="Uncategorized",
                        description=f"Relationship column from {rel.to_table}"
                    )
                    tables[rel.to_table].columns.append(column)
                
        except Exception as e:
            logger.error(f"Error extracting relationship tables: {str(e)}", exc_info=True)
            
        return tables

    def extract_all_tables(self) -> List[PowerBiTable]:
        """Extract all tables from the workbook.
        
        Returns:
            List of PowerBiTable objects
        """
        try:
            # Extract tables from datasources
            datasource_tables = self.datasource_parser.extract_all_tables()
            logger.info(f"Found {len(datasource_tables)} tables from datasources")
            
            # Extract tables from joins
            join_tables = self._extract_join_tables()
            logger.info(f"Found {len(join_tables)} tables from joins")
            
            # Extract tables from relationships
            relationship_tables = self._extract_relationship_tables()
            logger.info(f"Found {len(relationship_tables)} tables from relationships")
            
            # Combine tables, preferring datasource tables over join/relationship tables
            all_tables = {}
            
            # Add relationship tables first (lowest priority)
            for name, table in relationship_tables.items():
                all_tables[name] = table
            
            # Add join tables next (medium priority)
            for name, table in join_tables.items():
                all_tables[name] = table
                
            # Add datasource tables last (highest priority)
            for table in datasource_tables:
                all_tables[table.source_name] = table
            
            # Convert to list and deduplicate
            tables = list(all_tables.values())
            tables = self.deduplicator.deduplicate_tables(tables, set(relationship_tables.keys()))
            logger.info(f"After deduplication, found {len(tables)} unique tables (including {len(relationship_tables)} from relationships)")

            # Deduplicate partitions in each table
            for table in tables:
                table.partitions = self.deduplicator.deduplicate_partitions(table.partitions)

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

