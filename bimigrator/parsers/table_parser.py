"""Main table parser that orchestrates the parsing of different table components."""
import xml.etree.ElementTree as ET
from typing import Dict, Any, List

from bimigrator.common.logging import logger
from bimigrator.config.data_classes import PowerBiTable
from bimigrator.parsers.table_parser_base import TableParserBase
from bimigrator.parsers.table_parser_datasource import DatasourceParser
from bimigrator.parsers.table_parser_deduplication import TableDeduplicator


class TableParser(TableParserBase):
    """Main parser that orchestrates the parsing of different table components."""

    def __init__(self, twb_file: str, config: Dict[str, Any], output_dir: str):
        """Initialize TableParser.
        
        Args:
            twb_file: Path to the TWB file
            config: Configuration dictionary
            output_dir: Output directory
        """
        super().__init__(twb_file, config, output_dir)
        self.datasource_parser = DatasourceParser(twb_file, config, output_dir)
        self.deduplicator = TableDeduplicator()

    def extract_all_tables(self) -> List[PowerBiTable]:
        """Extract all table information from the workbook.
        
        Returns:
            List of PowerBiTable objects
        """
        try:
            # Extract tables from datasources
            tables = self.datasource_parser.extract_all_tables()
            logger.info(f"Found {len(tables)} tables before deduplication")

            # Deduplicate tables
            tables = self.deduplicator.deduplicate_tables(tables)
            logger.info(f"After deduplication, found {len(tables)} unique tables")

            # Deduplicate partitions in each table
            for table in tables:
                table.partitions = self.deduplicator.deduplicate_partitions(table.partitions)

        except Exception as e:
            logger.error(f"Error extracting tables: {str(e)}", exc_info=True)
            tables = []

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

