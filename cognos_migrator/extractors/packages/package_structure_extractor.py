"""
Package structure extractor for Cognos Framework Manager packages.

This module provides functionality to extract the overall structure from
Cognos Framework Manager (FM) package files.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any

from .base_package_extractor import BasePackageExtractor


class PackageStructureExtractor(BasePackageExtractor):
    """Extractor for the overall structure of Cognos Framework Manager packages"""
    
    def __init__(self, logger=None):
        """Initialize the package structure extractor
        
        Args:
            logger: Optional logger instance
        """
        super().__init__(logger)
    
    def extract_and_save(self, package_file_path: str, output_dir: str) -> Dict[str, Any]:
        """Extract package structure and save to JSON
        
        Args:
            package_file_path: Path to the FM package file
            output_dir: Directory to save extracted data
            
        Returns:
            Dictionary with extracted package structure
        """
        try:
            # Parse the XML file
            tree = ET.parse(package_file_path)
            root = tree.getroot()
            
            # Extract package structure
            structure = self.extract_package_structure(root)
            
            # Save to JSON file
            self.save_to_json(structure, output_dir, "package_structure.json")
            
            return structure
            
        except Exception as e:
            self.logger.error(f"Failed to extract package structure from {package_file_path}: {e}")
            return {"error": str(e)}
    
    def extract_package_structure(self, root: ET.Element) -> Dict[str, Any]:
        """Extract the overall structure from a package
        
        Args:
            root: XML root element
            
        Returns:
            Dictionary with extracted package structure
        """
        # Extract package name
        package_name = self._extract_package_name(root)
        
        # Extract namespaces (layers)
        namespaces = self._extract_namespaces(root)
        
        # Extract data sources
        data_sources = self._extract_data_sources(root)
        
        # Combine into package structure
        structure = {
            "name": package_name,
            "namespaces": namespaces,
            "dataSources": data_sources
        }
        
        return structure
    
    def _extract_package_name(self, root: ET.Element) -> str:
        """Extract package name from the XML root
        
        Args:
            root: XML root element
            
        Returns:
            Package name
        """
        try:
            # Try to find the name element with different namespace prefixes and paths
            for ns_prefix in ['bmt', 'ns']:
                # Try direct child name element
                name_elem = root.find(f'.//{ns_prefix}:n', self.namespaces)
                if name_elem is not None and name_elem.text:
                    return name_elem.text.strip()
                
                # Try project name attribute
                project_elem = root.find(f'.//{ns_prefix}:project', self.namespaces)
                if project_elem is not None and project_elem.get('name'):
                    return project_elem.get('name')
            
            # If still not found, look for name in other formats
            for ns_prefix in ['bmt', 'ns']:
                name_elem = root.find(f'.//{ns_prefix}:name', self.namespaces)
                if name_elem is not None and name_elem.text:
                    return name_elem.text.strip()
                
            return "Unknown Package"
        except Exception as e:
            self.logger.warning(f"Failed to extract package name: {e}")
            return "Unknown Package"
    
    def _extract_namespaces(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract namespaces (layers) from the XML root
        
        Args:
            root: XML root element
            
        Returns:
            List of namespaces
        """
        namespaces = []
        
        try:
            # Find all namespace elements
            for ns_prefix in ['bmt', 'ns']:
                ns_elements = root.findall(f'.//{ns_prefix}:namespace', self.namespaces)
                
                for ns_elem in ns_elements:
                    # Extract namespace name
                    ns_name = None
                    
                    # Try different paths to find the name
                    for path_prefix in ['bmt', 'ns']:
                        # Try name/n path
                        name_elem = ns_elem.find(f'.//{path_prefix}:name/{path_prefix}:n', self.namespaces)
                        if name_elem is not None and name_elem.text:
                            ns_name = name_elem.text.strip()
                            break
                        
                        # Try direct n element
                        name_elem = ns_elem.find(f'.//{path_prefix}:n', self.namespaces)
                        if name_elem is not None and name_elem.text:
                            ns_name = name_elem.text.strip()
                            break
                        
                        # Try name element with text directly
                        name_elem = ns_elem.find(f'.//{path_prefix}:name', self.namespaces)
                        if name_elem is not None and name_elem.text:
                            ns_name = name_elem.text.strip()
                            break
                    
                    # Try name attribute
                    if not ns_name:
                        if ns_elem.get('name'):
                            ns_name = ns_elem.get('name')
                    
                    # Skip if no name found
                    if not ns_name:
                        continue
                    
                    # Create namespace info
                    namespace = {
                        "name": ns_name,
                        "type": ns_elem.get('type', ''),
                        "id": ns_elem.get('id', '')
                    }
                    
                    namespaces.append(namespace)
            
            return namespaces
            
        except Exception as e:
            self.logger.warning(f"Failed to extract namespaces: {e}")
            return []
    
    def _extract_data_sources(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract data sources from the XML root
        
        Args:
            root: XML root element
            
        Returns:
            List of data sources
        """
        data_sources = []
        
        try:
            # Find all data source elements
            for ns_prefix in ['bmt', 'ns']:
                ds_paths = [
                    f'.//{ns_prefix}:dataSources/{ns_prefix}:dataSource',
                    f'./{ns_prefix}:dataSources/{ns_prefix}:dataSource'
                ]
                
                for ds_path in ds_paths:
                    ds_elements = root.findall(ds_path, self.namespaces)
                    
                    for ds_elem in ds_elements:
                        # Extract data source properties
                        ds_info = {
                            "id": ds_elem.get('id', ''),
                            "type": ds_elem.get('type', '')
                        }
                        
                        # Extract CM data source
                        for path_prefix in ['bmt', 'ns']:
                            cm_ds_elem = ds_elem.find(f'.//{path_prefix}:cmDataSource', self.namespaces)
                            if cm_ds_elem is not None:
                                ds_info["cmDataSource"] = cm_ds_elem.text.strip() if cm_ds_elem.text else ""
                                break
                        
                        # Extract schema
                        for path_prefix in ['bmt', 'ns']:
                            schema_elem = ds_elem.find(f'.//{path_prefix}:schema', self.namespaces)
                            if schema_elem is not None:
                                ds_info["schema"] = schema_elem.text.strip() if schema_elem.text else ""
                                break
                        
                        # Extract catalog
                        for path_prefix in ['bmt', 'ns']:
                            catalog_elem = ds_elem.find(f'.//{path_prefix}:catalog', self.namespaces)
                            if catalog_elem is not None:
                                ds_info["catalog"] = catalog_elem.text.strip() if catalog_elem.text else ""
                                break
                        
                        data_sources.append(ds_info)
            
            return data_sources
            
        except Exception as e:
            self.logger.warning(f"Failed to extract data sources: {e}")
            return []
