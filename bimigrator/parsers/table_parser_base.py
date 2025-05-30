"""Base class for table parsing functionality."""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List

from bimigrator.config.data_classes import PowerBiTable
from bimigrator.common.log_utils import log_info, log_debug, log_warning, log_error
from bimigrator.parsers.base_parser import BaseParser
from bimigrator.parsers.column_parser import ColumnParser
from bimigrator.parsers.connections.connection_factory import ConnectionParserFactory
from bimigrator.generators.tmdl_generator import TMDLGenerator
from bimigrator.helpers.calculation_tracker import CalculationTracker


class TableParserBase(BaseParser):
    """Base class for table parsing functionality."""

    def __init__(self, twb_file: str, config: Dict[str, Any], output_dir: str):
        """Initialize TableParserBase.
        
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
        # Get workbook name for logging
        if isinstance(twb_file, (Path, str)):
            self.workbook_name = Path(twb_file).stem
        else:
            self.workbook_name = "Unknown"
            
        # Initialize calculation tracker with workbook name
        self.calculation_tracker = CalculationTracker(base_output_dir / 'extracted', self.workbook_name)

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

    def extract_all_tables(self) -> List[PowerBiTable]:
        """Extract all table information from the workbook.
        
        This is a placeholder that should be implemented by concrete classes.
        
        Returns:
            List of PowerBiTable objects
        """
        raise NotImplementedError("Subclasses must implement extract_all_tables")
