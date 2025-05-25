"""Main column parser that orchestrates the parsing of different column types."""
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Tuple

from bimigrator.config.data_classes import PowerBiColumn, PowerBiMeasure
from bimigrator.parsers.column_parser_calculated import CalculatedFieldParser
from bimigrator.parsers.column_parser_relation import RelationColumnParser
from bimigrator.parsers.column_parser_metadata import MetadataColumnParser


class ColumnParser:
    """Main parser that orchestrates the parsing of different column types."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the column parser.
        
        Args:
            config: Configuration dictionary
        """
        self.calculated_parser = CalculatedFieldParser(config)
        self.relation_parser = RelationColumnParser(config)
        self.metadata_parser = MetadataColumnParser(config)

    def extract_columns_and_measures(
            self,
            ds_element: ET.Element,
            columns_yaml_config: Dict[str, Any],
            pbi_table_name: str
    ) -> Tuple[List[PowerBiColumn], List[PowerBiMeasure]]:
        """Extract columns and measures from a datasource element.
        
        Args:
            ds_element: Datasource element
            columns_yaml_config: YAML configuration for columns
            pbi_table_name: Table name for DAX expressions
            
        Returns:
            Tuple of (columns, measures)
        """
        # Extract from each parser
        calc_cols, calc_measures = self.calculated_parser.extract_columns_and_measures(
            ds_element, columns_yaml_config, pbi_table_name
        )
        rel_cols, _ = self.relation_parser.extract_columns_and_measures(
            ds_element, columns_yaml_config, pbi_table_name
        )
        meta_cols, _ = self.metadata_parser.extract_columns_and_measures(
            ds_element, columns_yaml_config, pbi_table_name
        )

        # Combine results
        all_columns = calc_cols + rel_cols + meta_cols

        # Remove duplicates based on source_name
        seen_names = set()
        unique_columns = []
        for col in all_columns:
            if col.source_name not in seen_names:
                unique_columns.append(col)
                seen_names.add(col.source_name)

        return unique_columns, calc_measures
