"""Base class for column parsing functionality."""
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Tuple, Set
from pathlib import Path

from bimigrator.config.data_classes import PowerBiColumn, PowerBiMeasure
from bimigrator.converters import CalculationConverter
from bimigrator.parsers.column_parser_types import ColumnTypeMapper


class ColumnParserBase:
    """Base class for column parsing functionality."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the base parser.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.type_mapper = ColumnTypeMapper(config)
        
        # Initialize CalculationConverter with output_dir
        output_dir = config.get('output_dir')
        if output_dir:
            config['output_dir'] = output_dir
        self.calculation_converter = CalculationConverter(config)

        # Initialize CalculationTracker
        if output_dir:
            from bimigrator.helpers.calculation_tracker import CalculationTracker
            self.calculation_tracker = CalculationTracker(Path(output_dir))
        else:
            self.calculation_tracker = None

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
        raise NotImplementedError("Subclasses must implement extract_columns_and_measures")
