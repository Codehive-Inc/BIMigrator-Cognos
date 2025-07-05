"""
Package filter extractor for Cognos Framework Manager packages.

This module provides functionality to extract filters from
Cognos Framework Manager (FM) package files.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any

from .base_package_extractor import BasePackageExtractor


class PackageFilterExtractor(BasePackageExtractor):
    """Extractor for filters in Cognos Framework Manager packages"""
    
    def __init__(self, logger=None):
        """Initialize the filter extractor
        
        Args:
            logger: Optional logger instance
        """
        super().__init__(logger)
    
    def extract_and_save(self, package_file_path: str, output_dir: str) -> Dict[str, Any]:
        """Extract filters and save to JSON
        
        Args:
            package_file_path: Path to the FM package file
            output_dir: Directory to save extracted data
            
        Returns:
            Dictionary with extracted filters
        """
        try:
            # Parse the XML file
            tree = ET.parse(package_file_path)
            root = tree.getroot()
            
            # Extract filters
            filters = self.extract_filters(root)
            
            # Save to JSON file
            self.save_to_json(filters, output_dir, "filters.json")
            
            return {"filters": filters}
            
        except Exception as e:
            self.logger.error(f"Failed to extract filters from {package_file_path}: {e}")
            return {"error": str(e)}
    
    def extract_filters(self, root: ET.Element) -> Dict[str, List[Dict[str, Any]]]:
        """Extract filters from the XML root
        
        Args:
            root: XML root element
            
        Returns:
            Dictionary mapping query subject identifiers to lists of filters
        """
        filters_by_subject = {}
        
        try:
            # First approach: Find all namespaces (Database Layer, Presentation Layer, etc.)
            namespace_elements = []
            for ns_prefix in ['bmt', 'ns']:
                # Find root namespace
                ns_elems = root.findall(f'.//{ns_prefix}:namespace', self.namespaces)
                if ns_elems:
                    namespace_elements.extend(ns_elems)
            
            # If no namespaces found, try searching from root
            if not namespace_elements:
                namespace_elements = [root]
                self.logger.info("No explicit namespace elements found, using root as namespace")
            
            # Process each namespace to find query subjects
            for namespace in namespace_elements:
                # Try to find query subjects in this namespace with different prefixes
                for ns_prefix in ['bmt', 'ns']:
                    # Try multiple paths to find query subjects
                    search_paths = [
                        f'.//{ns_prefix}:querySubject',
                        f'./{ns_prefix}:querySubject',
                        f'./{ns_prefix}:content//{ns_prefix}:querySubject',
                        f'./{ns_prefix}:folder//{ns_prefix}:querySubject'
                    ]
                    
                    for search_path in search_paths:
                        qs_elements = namespace.findall(search_path, self.namespaces)
                        
                        if not qs_elements:
                            continue
                        
                        for qs_elem in qs_elements:
                            # Extract query subject name - try different paths
                            qs_name = None
                            
                            # Try name/n path
                            for path_prefix in ['bmt', 'ns']:
                                name_elem = qs_elem.find(f'.//{path_prefix}:name/{path_prefix}:n', self.namespaces)
                                if name_elem is not None and name_elem.text:
                                    qs_name = name_elem.text.strip()
                                    break
                            
                            # Try direct n element
                            if not qs_name:
                                for path_prefix in ['bmt', 'ns']:
                                    name_elem = qs_elem.find(f'.//{path_prefix}:n', self.namespaces)
                                    if name_elem is not None and name_elem.text:
                                        qs_name = name_elem.text.strip()
                                        break
                            
                            # Try name element with text directly
                            if not qs_name:
                                for path_prefix in ['bmt', 'ns']:
                                    name_elem = qs_elem.find(f'.//{path_prefix}:name', self.namespaces)
                                    if name_elem is not None and name_elem.text:
                                        qs_name = name_elem.text.strip()
                                        break
                            
                            # Try name attribute
                            if not qs_name:
                                if qs_elem.get('name'):
                                    qs_name = qs_elem.get('name')
                            
                            # Skip if no name found
                            if not qs_name:
                                continue
                            
                            # Extract filters
                            filters = self._extract_subject_filters(qs_elem, qs_name)
                            
                            if filters:
                                filters_by_subject[qs_name] = filters
            
            return filters_by_subject
            
        except Exception as e:
            self.logger.error(f"Failed to extract filters: {e}")
            return {}
    
    def _extract_subject_filters(self, qs_elem: ET.Element, qs_name: str) -> List[Dict[str, Any]]:
        """Extract filters from a query subject element
        
        Args:
            qs_elem: Query subject XML element
            qs_name: Query subject name
            
        Returns:
            List of filters
        """
        filters = []
        
        try:
            # Try to find filter elements with different prefixes and paths
            for path_prefix in ['bmt', 'ns']:
                filter_paths = [
                    f'.//{path_prefix}:filter',
                    f'./{path_prefix}:filter',
                    f'./{path_prefix}:filters/{path_prefix}:filter'
                ]
                
                for filter_path in filter_paths:
                    filter_elements = qs_elem.findall(filter_path, self.namespaces)
                    
                    if not filter_elements:
                        continue
                    
                    for filter_elem in filter_elements:
                        # Extract filter name
                        filter_name = None
                        
                        # Try different paths to find the name
                        for name_prefix in ['bmt', 'ns']:
                            # Try name/n path
                            name_elem = filter_elem.find(f'.//{name_prefix}:name/{name_prefix}:n', self.namespaces)
                            if name_elem is not None and name_elem.text:
                                filter_name = name_elem.text.strip()
                                break
                            
                            # Try direct n element
                            name_elem = filter_elem.find(f'.//{name_prefix}:n', self.namespaces)
                            if name_elem is not None and name_elem.text:
                                filter_name = name_elem.text.strip()
                                break
                            
                            # Try name element with text directly
                            name_elem = filter_elem.find(f'.//{name_prefix}:name', self.namespaces)
                            if name_elem is not None and name_elem.text:
                                filter_name = name_elem.text.strip()
                                break
                        
                        # Try name attribute
                        if not filter_name:
                            if filter_elem.get('name'):
                                filter_name = filter_elem.get('name')
                        
                        # If no name found, generate a default name
                        if not filter_name:
                            filter_name = f"Filter_{len(filters) + 1}"
                        
                        # Extract filter expression
                        expression = None
                        for expr_prefix in ['bmt', 'ns']:
                            expr_elem = filter_elem.find(f'.//{expr_prefix}:expression', self.namespaces)
                            if expr_elem is not None and expr_elem.text:
                                expression = expr_elem.text.strip()
                                break
                        
                        # Skip if no expression found
                        if not expression:
                            continue
                        
                        # Create filter info
                        filter_info = {
                            'name': filter_name,
                            'query_subject': qs_name,
                            'expression': expression,
                            'powerbi_expression': self._convert_to_dax(expression, qs_name)
                        }
                        
                        # Extract usage
                        for usage_prefix in ['bmt', 'ns']:
                            usage_elem = filter_elem.find(f'.//{usage_prefix}:usage', self.namespaces)
                            if usage_elem is not None and usage_elem.text:
                                filter_info['usage'] = usage_elem.text.strip()
                                break
                        
                        # Extract description
                        for desc_prefix in ['bmt', 'ns']:
                            desc_elem = filter_elem.find(f'.//{desc_prefix}:description', self.namespaces)
                            if desc_elem is not None and desc_elem.text:
                                filter_info['description'] = desc_elem.text.strip()
                                break
                        
                        filters.append(filter_info)
            
            return filters
            
        except Exception as e:
            self.logger.warning(f"Failed to extract filters: {e}")
            return []
    
    def _convert_to_dax(self, cognos_expression: str, table_name: str) -> str:
        """Convert Cognos expression to Power BI DAX expression
        
        Args:
            cognos_expression: Cognos expression
            table_name: Table name for context
            
        Returns:
            DAX expression
        """
        # This is a simplified conversion - a real implementation would need more complex parsing
        try:
            # Replace common Cognos functions with DAX equivalents
            dax_expression = cognos_expression
            
            # Replace [table].[column] with 'table'[column]
            import re
            dax_expression = re.sub(r'\[([^\]]+)\]\.?\[([^\]]+)\]', r"'\1'[\2]", dax_expression)
            
            # Replace common functions
            function_mappings = {
                'sum\\(': 'SUM(',
                'average\\(': 'AVERAGE(',
                'count\\(': 'COUNT(',
                'minimum\\(': 'MIN(',
                'maximum\\(': 'MAX(',
                'if\\s*\\(': 'IF(',
                'case\\s+when': 'SWITCH(TRUE(),',
                'then': ',',
                'else': ',',
                'end': ')'
            }
            
            for cognos_func, dax_func in function_mappings.items():
                dax_expression = re.sub(cognos_func, dax_func, dax_expression, flags=re.IGNORECASE)
            
            return dax_expression
            
        except Exception as e:
            self.logger.warning(f"Failed to convert expression to DAX: {e}")
            return cognos_expression  # Return original expression if conversion fails
