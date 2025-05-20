"""Base class for connection parsers."""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import xml.etree.ElementTree as ET

from config.data_classes import PowerBiPartition, PowerBiColumn


class BaseConnectionParser(ABC):
    """Base class for parsing different types of Tableau connections."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the connection parser.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
    @abstractmethod
    def can_handle(self, connection_node: ET.Element) -> bool:
        """Check if this parser can handle the given connection.
        
        Args:
            connection_node: Connection element from Tableau workbook
            
        Returns:
            True if this parser can handle the connection, False otherwise
        """
        pass
        
    @abstractmethod
    def extract_partition_info(
        self,
        connection_node: ET.Element,
        relation_node: ET.Element,
        table_name: str,
        columns: Optional[List[PowerBiColumn]] = None
    ) -> List[PowerBiPartition]:
        """Extract partition information from connection and relation nodes.
        
        Args:
            connection_node: Connection element
            relation_node: Relation element
            table_name: Name of the table
            columns: Optional list of PowerBiColumn objects with type information
            
        Returns:
            List of PowerBiPartition objects
        """
        pass
        
    @abstractmethod
    def extract_columns(
        self,
        connection_node: ET.Element,
        relation_node: ET.Element,
        columns_yaml_config: Dict[str, Any]
    ) -> List[PowerBiColumn]:
        """Extract columns from connection and relation nodes.
        
        Args:
            connection_node: Connection element
            relation_node: Relation element
            columns_yaml_config: YAML configuration for columns
            
        Returns:
            List of PowerBiColumn objects
        """
        pass
