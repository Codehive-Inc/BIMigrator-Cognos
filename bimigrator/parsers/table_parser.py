"""Main table parser that orchestrates the parsing of different table components."""
import xml.etree.ElementTree as ET
from typing import Dict, Any, List

from bimigrator.common.logging import logger
from bimigrator.config.data_classes import PowerBiTable
from bimigrator.parsers.table_parser_base import TableParserBase
from bimigrator.parsers.table_parser_datasource import DatasourceParser
from bimigrator.parsers.table_parser_deduplication import TableDeduplicator
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
                                        name=column_name,
                                        data_type="string",  # Default to string, can be refined later
                                        data_category="Uncategorized",
                                        description=f"Join column from {table_name}"
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
            
            # Get tables referenced in relationships
            relationship_tables = set()
            for ds in self.root.findall('.//datasource'):
                for clause in ds.findall('.//clause[@type="join"]'):
                    for expr in clause.findall('.//expression'):
                        op = expr.get('op', '')
                        if '[' in op and '].[' in op:
                            table_name = op.split('].[')[0].strip('[')
                            relationship_tables.add(table_name)
            
            # Combine tables, preferring datasource tables over join tables
            all_tables = {}
            
            # Add join tables first
            for name, table in join_tables.items():
                all_tables[name] = table
                
            # Add/update with datasource tables
            for table in datasource_tables:
                all_tables[table.source_name] = table
            
            # Convert to list and remove duplicates, preserving relationship tables
            tables = list(all_tables.values())
            tables = self.deduplicator.deduplicate_tables(tables, relationship_tables)
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

