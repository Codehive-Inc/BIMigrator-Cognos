"""
Base package extractor for Cognos Framework Manager packages.

This module provides base functionality for extracting data from
Cognos Framework Manager (FM) package files.
"""

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import os
import json


class BasePackageExtractor:
    """Base extractor for Cognos Framework Manager package files"""
    
    def __init__(self, xml_file_path: str):
        """Initialize the base package extractor
        
        Args:
            xml_file_path: Path to the XML file
        """
        self.xml_file_path = xml_file_path
        self.logger = logging.getLogger(__name__)
        
        # Define XML namespaces - support multiple versions
        self.namespaces = {
            'bmt': 'http://www.developer.cognos.com/schemas/bmt/60/7',  # Common version
            'ns': 'http://www.developer.cognos.com/schemas/bmt/60/7',
            'bmtse': 'http://www.developer.cognos.com/schemas/bmt/60/12',  # Newer version
            'nsse': 'http://www.developer.cognos.com/schemas/bmt/60/12',
            'bmtpe': 'http://www.developer.cognos.com/schemas/bmt/60/3',  # Older version
            'nspe': 'http://www.developer.cognos.com/schemas/bmt/60/3',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
        }
        # Register namespaces for proper XML parsing
        for prefix, uri in self.namespaces.items():
            ET.register_namespace(prefix, uri)
    
    def extract_from_package(self, package_content: ET.Element) -> Dict[str, Any]:
        """Extract data from package content
        
        Args:
            package_content: XML root element of the package
            
        Returns:
            Dictionary with extracted data
        """
        # This is a placeholder method to be overridden by subclasses
        return {
            "type": "package",
            "extraction_status": "base_extractor_only"
        }
    
    def find_element_with_ns(self, element: ET.Element, path: str) -> Optional[ET.Element]:
        """Find an element using namespace
        
        Args:
            element: Parent XML element
            path: XPath to search
            
        Returns:
            Found element or None
        """
        try:
            return element.find(path, self.namespaces)
        except Exception as e:
            self.logger.warning(f"Error finding element at path {path}: {e}")
            return None
    
    def find_all_elements_with_ns(self, element: ET.Element, path: str) -> List[ET.Element]:
        """Find all elements using namespace
        
        Args:
            element: Parent XML element
            path: XPath to search
            
        Returns:
            List of found elements
        """
        try:
            return element.findall(path, self.namespaces)
        except Exception as e:
            self.logger.warning(f"Error finding elements at path {path}: {e}")
            return []
    
    def get_element_text(self, element: Optional[ET.Element]) -> str:
        """Safely get text from an XML element
        
        Args:
            element: XML element
            
        Returns:
            Text content of the element or empty string if element is None
        """
        if element is None:
            return ""
        return element.text or ""
    
    def get_attribute(self, element: ET.Element, attr_name: str, default: str = "") -> str:
        """Safely get attribute from an element
        
        Args:
            element: XML element
            attr_name: Name of the attribute
            default: Default value if attribute doesn't exist
            
        Returns:
            Attribute value or default
        """
        if element is None:
            return default
        return element.get(attr_name, default)
    
    def find_element_with_multiple_paths(self, element: ET.Element, paths: List[str]) -> Optional[ET.Element]:
        """Find an element using multiple possible paths
        
        Args:
            element: Parent XML element
            paths: List of XPaths to try
            
        Returns:
            Found element or None
        """
        for path in paths:
            found_element = self.find_element_with_ns(element, path)
            if found_element is not None:
                return found_element
        return None
    
    def find_all_elements_with_multiple_paths(self, element: ET.Element, paths: List[str]) -> List[ET.Element]:
        """Find all elements using multiple possible paths
        
        Args:
            element: Parent XML element
            paths: List of XPaths to try
            
        Returns:
            List of found elements
        """
        for path in paths:
            found_elements = self.find_all_elements_with_ns(element, path)
            if found_elements:
                return found_elements
        return []
    
    def save_to_json(self, data: Any, output_dir: Union[str, Path], filename: str) -> str:
        """Save extracted data to a JSON file
        
        Args:
            data: Data to save
            output_dir: Output directory
            filename: Output filename
            
        Returns:
            Path to the saved file
        """
        try:
            # Ensure output directory exists
            if isinstance(output_dir, str):
                output_dir = Path(output_dir)
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create file path
            file_path = output_dir / filename
            
            # Save data to JSON file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"Saved data to {file_path}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"Error saving data to {filename}: {e}")
            return ""
    
    def map_cognos_type_to_powerbi(self, cognos_type: str) -> str:
        """Map Cognos data types to Power BI data types
        
        Args:
            cognos_type: Cognos data type
            
        Returns:
            Equivalent Power BI data type
        """
        # Mapping of Cognos data types to Power BI data types
        type_mapping = {
            'int32': 'Int64',
            'int64': 'Int64',
            'float': 'Double',
            'double': 'Double',
            'decimal': 'Decimal',
            'character': 'String',
            'characterLength16': 'String',
            'date': 'DateTime',
            'time': 'DateTime',
            'timestamp': 'DateTime',
            'boolean': 'Boolean'
        }
        
        return type_mapping.get(cognos_type.lower(), 'String')
