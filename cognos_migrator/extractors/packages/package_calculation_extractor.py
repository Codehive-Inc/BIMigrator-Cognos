"""
Package calculation extractor for Cognos Framework Manager packages.

This module provides functionality to extract calculations from
Cognos Framework Manager (FM) package files.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any

from .base_package_extractor import BasePackageExtractor


class PackageCalculationExtractor(BasePackageExtractor):
    """Extractor for calculations in Cognos Framework Manager packages"""
    
    def __init__(self, logger=None):
        """Initialize the calculation extractor
        
        Args:
            logger: Optional logger instance
        """
        super().__init__(logger)
    
    def extract_and_save(self, package_file_path: str, output_dir: str) -> Dict[str, Any]:
        """Extract calculations and save to JSON
        
        Args:
            package_file_path: Path to the FM package file
            output_dir: Directory to save extracted data
            
        Returns:
            Dictionary with extracted calculations
        """
        try:
            # Parse the XML file
            tree = ET.parse(package_file_path)
            root = tree.getroot()
            
            # Extract calculations
            calculations = self.extract_calculations(root)
            
            # Save to JSON file
            self.save_to_json(calculations, output_dir, "calculations.json")
            
            return {"calculations": calculations}
            
        except Exception as e:
            self.logger.error(f"Failed to extract calculations from {package_file_path}: {e}")
            return {"error": str(e)}
    
    def extract_calculations(self, root: ET.Element) -> Dict[str, List[Dict[str, Any]]]:
        """Extract calculations from the XML root
        
        Args:
            root: XML root element
            
        Returns:
            Dictionary mapping query subject identifiers to lists of calculations
        """
        calculations_by_subject = {}
        
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
                            
                            # Extract calculated query items
                            calculations = self._extract_calculated_items(qs_elem, qs_name)
                            
                            if calculations:
                                calculations_by_subject[qs_name] = calculations
            
            return calculations_by_subject
            
        except Exception as e:
            self.logger.error(f"Failed to extract calculations: {e}")
            return {}
    
    def _extract_calculated_items(self, qs_elem: ET.Element, qs_name: str) -> List[Dict[str, Any]]:
        """Extract calculated query items from a query subject element
        
        Args:
            qs_elem: Query subject XML element
            qs_name: Query subject name
            
        Returns:
            List of calculated query items
        """
        calculated_items = []
        
        try:
            # Try to find query items with different prefixes and paths
            for path_prefix in ['bmt', 'ns']:
                qi_paths = [
                    f'.//{path_prefix}:queryItem',
                    f'./{path_prefix}:queryItem',
                    f'./{path_prefix}:items/{path_prefix}:queryItem'
                ]
                
                for qi_path in qi_paths:
                    qi_elements = qs_elem.findall(qi_path, self.namespaces)
                    
                    if not qi_elements:
                        continue
                    
                    for qi_elem in qi_elements:
                        # Extract query item name
                        qi_name = None
                        
                        # Try different paths to find the name
                        for name_prefix in ['bmt', 'ns']:
                            # Try name/n path
                            name_elem = qi_elem.find(f'.//{name_prefix}:name/{name_prefix}:n', self.namespaces)
                            if name_elem is not None and name_elem.text:
                                qi_name = name_elem.text.strip()
                                break
                            
                            # Try direct n element
                            name_elem = qi_elem.find(f'.//{name_prefix}:n', self.namespaces)
                            if name_elem is not None and name_elem.text:
                                qi_name = name_elem.text.strip()
                                break
                            
                            # Try name element with text directly
                            name_elem = qi_elem.find(f'.//{name_prefix}:name', self.namespaces)
                            if name_elem is not None and name_elem.text:
                                qi_name = name_elem.text.strip()
                                break
                        
                        # Try name attribute
                        if not qi_name:
                            if qi_elem.get('name'):
                                qi_name = qi_elem.get('name')
                        
                        # Skip if no name found
                        if not qi_name:
                            continue
                        
                        # Check if this is a calculated item by examining the expression
                        expression = None
                        expression_type = None
                        
                        for expr_prefix in ['bmt', 'ns']:
                            expr_elem = qi_elem.find(f'.//{expr_prefix}:expression', self.namespaces)
                            if expr_elem is not None:
                                # Check if this is a simple reference or a calculation
                                refobj_elem = expr_elem.find(f'.//{expr_prefix}:refobj', self.namespaces)
                                if refobj_elem is not None and refobj_elem.text:
                                    # This is a simple reference, not a calculation
                                    expression = f"[{refobj_elem.text.strip()}]"
                                    expression_type = 'reference'
                                elif expr_elem.text:
                                    # This is a calculation
                                    expression = expr_elem.text.strip()
                                    expression_type = 'calculation'
                                break
                        
                        # Skip if no expression found or if it's a simple reference
                        if not expression or expression_type != 'calculation':
                            continue
                        
                        # Extract datatype
                        datatype = None
                        for dt_prefix in ['bmt', 'ns']:
                            datatype_elem = qi_elem.find(f'.//{dt_prefix}:datatype', self.namespaces)
                            if datatype_elem is not None and datatype_elem.text:
                                datatype = datatype_elem.text.strip()
                                break
                        
                        # Extract usage
                        usage = None
                        for usage_prefix in ['bmt', 'ns']:
                            usage_elem = qi_elem.find(f'.//{usage_prefix}:usage', self.namespaces)
                            if usage_elem is not None and usage_elem.text:
                                usage = usage_elem.text.strip()
                                break
                        
                        # Create calculated item info
                        calc_item = {
                            'name': qi_name,
                            'query_subject': qs_name,
                            'expression': expression,
                            'datatype': datatype,
                            'powerbi_datatype': self.map_cognos_type_to_powerbi(datatype) if datatype else 'String'
                        }
                        
                        if usage:
                            calc_item['usage'] = usage
                        
                        # Extract regular aggregate
                        for agg_prefix in ['bmt', 'ns']:
                            agg_elem = qi_elem.find(f'.//{agg_prefix}:regularAggregate', self.namespaces)
                            if agg_elem is not None and agg_elem.text:
                                calc_item['regularAggregate'] = agg_elem.text.strip()
                                break
                        
                        # Extract description
                        for desc_prefix in ['bmt', 'ns']:
                            desc_elem = qi_elem.find(f'.//{desc_prefix}:description', self.namespaces)
                            if desc_elem is not None and desc_elem.text:
                                calc_item['description'] = desc_elem.text.strip()
                                break
                        
                        # Convert to Power BI DAX expression
                        calc_item['powerbi_expression'] = self._convert_to_dax(expression, qs_name)
                        
                        calculated_items.append(calc_item)
            
            return calculated_items
            
        except Exception as e:
            self.logger.warning(f"Failed to extract calculated items: {e}")
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
