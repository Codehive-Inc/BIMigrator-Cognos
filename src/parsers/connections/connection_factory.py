"""Factory for creating connection parsers."""
from typing import Dict, Any, List
import xml.etree.ElementTree as ET

from .base_connection import BaseConnectionParser
from .excel_parser import ExcelConnectionParser
from .sql_parser import SQLConnectionParser


class ConnectionParserFactory:
    """Factory for creating connection parsers."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the factory.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self._parsers: List[BaseConnectionParser] = [
            ExcelConnectionParser(config),
            SQLConnectionParser(config)
        ]
        
    def get_parser(self, connection_node: ET.Element) -> BaseConnectionParser:
        """Get the appropriate parser for a connection.
        
        Args:
            connection_node: Connection element from Tableau workbook
            
        Returns:
            Parser that can handle the connection
            
        Raises:
            ValueError: If no parser can handle the connection
        """
        for parser in self._parsers:
            if parser.can_handle(connection_node):
                return parser
                
        raise ValueError(f"No parser found for connection type: {connection_node.get('class')}")
