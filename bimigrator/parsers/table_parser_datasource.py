"""Parser for handling datasource elements in Tableau workbooks."""
import uuid
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Tuple

from bimigrator.common.logging import logger
from bimigrator.config.data_classes import PowerBiTable, PowerBiColumn, PowerBiMeasure
from bimigrator.parsers.table_parser_base import TableParserBase
from bimigrator.parsers.table_parser_partition import TablePartitionParser
from bimigrator.parsers.table_parser_relation import TableRelationParser


class DatasourceParser(TableParserBase):
    """Parser for handling datasource elements in Tableau workbooks."""

    def __init__(self, twb_file: str, config: Dict[str, Any], output_dir: str):
        """Initialize DatasourceParser.
        
        Args:
            twb_file: Path to the TWB file
            config: Configuration dictionary
            output_dir: Output directory
        """
        super().__init__(twb_file, config, output_dir)
        self.partition_parser = TablePartitionParser(twb_file, config, output_dir)
        self.relation_parser = TableRelationParser(twb_file, config, output_dir)

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

    def _process_datasource(
            self,
            ds_element: ET.Element,
            seen_table_names: set
    ) -> Tuple[PowerBiTable, str]:
        """Process a single datasource element.
        
        Args:
            ds_element: The datasource element
            seen_table_names: Set of already used table names
            
        Returns:
            Tuple of (PowerBiTable, table_name) or (None, None) if datasource should be skipped
        """
        # Get datasource name and caption
        ds_name = ds_element.get('name', '')
        ds_caption = ds_element.get('caption', ds_name)
        logger.info(f"Processing datasource: {ds_name} (caption: {ds_caption})")

        # Skip datasources without a connection
        connection = ds_element.find('.//connection')
        if connection is None:
            logger.info(f"Skipping datasource {ds_name} - no connection found")
            return None, None

        # Get datasource ID for deduplication
        ds_id = self._get_datasource_id(ds_element)

        # Get table name
        table_name = ds_caption or ds_name
        if connection.get('class') == 'excel-direct':
            # Find the relation element
            relation = connection.find('.//relation')
            if relation is not None:
                sheet_name = relation.get('name')
                if sheet_name:
                    table_name = sheet_name

        # Create a unique table name if needed
        final_table_name = table_name
        counter = 1
        while final_table_name in seen_table_names:
            final_table_name = f"{table_name}_{counter}"
            counter += 1

        # Extract columns and measures
        columns_yaml_config = self.config.get('PowerBiColumn', {})
        columns, measures = self.column_parser.extract_columns_and_measures(
            ds_element,
            columns_yaml_config,
            final_table_name
        )

        # Extract partition information
        all_partitions = self.partition_parser._extract_partition_info(ds_element, final_table_name, columns)

        # Create PowerBiTable
        table = PowerBiTable(
            source_name=final_table_name,
            description=f"Imported from Tableau datasource: {ds_name}",
            columns=columns,
            measures=measures,
            hierarchies=[],
            partitions=all_partitions
        )

        return table, final_table_name

    def extract_all_tables(self) -> List[PowerBiTable]:
        """Extract all table information from the workbook.
        
        Returns:
            List of PowerBiTable objects
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
                table, table_name = self._process_datasource(ds_element, seen_table_names)
                if table is not None:
                    tables.append(table)
                    seen_table_names.add(table_name)
                    logger.info(
                        f"Added table {table_name} with {len(table.columns)} columns, {len(table.measures)} measures, and {len(table.partitions)} partitions"
                    )

        except Exception as e:
            logger.error(f"Error extracting tables: {str(e)}", exc_info=True)

        return tables
