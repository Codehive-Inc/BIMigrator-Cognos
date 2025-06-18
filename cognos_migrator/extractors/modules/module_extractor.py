"""
Base module extractor for Cognos to Power BI migration
"""

import logging
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import xml.etree.ElementTree as ET


class ModuleExtractor:
    """Base class for extracting module components from Cognos modules"""
    
    def __init__(self, logger=None):
        """Initialize the module extractor
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
    
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
    
    def find_element_with_ns(self, element: ET.Element, path: str, namespaces: Dict[str, str]) -> Optional[ET.Element]:
        """Find an element using namespace
        
        Args:
            element: Parent XML element
            path: XPath to search
            namespaces: Namespace dictionary
            
        Returns:
            Found element or None
        """
        try:
            return element.find(path, namespaces)
        except Exception as e:
            self.logger.warning(f"Error finding element at path {path}: {e}")
            return None
    
    def find_all_elements_with_ns(self, element: ET.Element, path: str, namespaces: Dict[str, str]) -> List[ET.Element]:
        """Find all elements using namespace
        
        Args:
            element: Parent XML element
            path: XPath to search
            namespaces: Namespace dictionary
            
        Returns:
            List of found elements
        """
        try:
            return element.findall(path, namespaces)
        except Exception as e:
            self.logger.warning(f"Error finding elements at path {path}: {e}")
            return []
    
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
    
    def extract_from_module(self, module_content: str) -> Dict[str, Any]:
        """Extract data from module content
        
        Args:
            module_content: XML content of the module
            
        Returns:
            Dictionary with extracted data
        """
        try:
            root = ET.fromstring(module_content)
            
            # Register namespace if present
            ns = {}
            if root.tag.startswith('{'):
                ns_uri = root.tag.split('}')[0].strip('{')
                ns['ns'] = ns_uri
                self.logger.info(f"Detected XML namespace: {ns_uri}")
            
            return self._extract_data(root, ns)
        except Exception as e:
            self.logger.error(f"Error extracting data from module: {e}")
            return {}
    
    def _extract_data(self, root: ET.Element, namespaces: Dict[str, str]) -> Dict[str, Any]:
        """Extract data from module root element
        
        Args:
            root: Root XML element
            namespaces: Namespace dictionary
            
        Returns:
            Dictionary with extracted data
        """
        # This is a placeholder method to be overridden by subclasses
        return {
            "type": "module",
            "extraction_status": "base_extractor_only"
        }
    
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
