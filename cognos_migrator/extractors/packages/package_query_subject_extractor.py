"""
Package query subject extractor for Cognos Framework Manager packages.

This module provides functionality to extract query subjects (tables) from
Cognos Framework Manager (FM) package files.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any

from .base_package_extractor import BasePackageExtractor


class PackageQuerySubjectExtractor(BasePackageExtractor):
    """Extractor for query subjects in Cognos Framework Manager packages"""
    
    def __init__(self, logger=None):
        """Initialize the query subject extractor
        
        Args:
            logger: Optional logger instance
        """
        super().__init__(logger)
    
    def extract_and_save(self, package_file_path: str, output_dir: str) -> Dict[str, Any]:
        """Extract query subjects and save to JSON
        
        Args:
            package_file_path: Path to the FM package file
            output_dir: Directory to save extracted data
            
        Returns:
            Dictionary with extracted query subjects
        """
        try:
            # Parse the XML file
            tree = ET.parse(package_file_path)
            root = tree.getroot()
            
            # Extract query subjects
            query_subjects = self.extract_query_subjects(root)
            
            # Save to JSON file
            self.save_to_json(query_subjects, output_dir, "query_subjects.json")
            
            return {"query_subjects": query_subjects}
            
        except Exception as e:
            self.logger.error(f"Failed to extract query subjects from {package_file_path}: {e}")
            return {"error": str(e)}
    
    def extract_query_subjects(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract query subjects from the XML root
        
        Args:
            root: XML root element
            
        Returns:
            List of query subjects
        """
        query_subjects = []
        
        try:
            # First approach: Find all namespaces (Database Layer, Presentation Layer, etc.)
            namespace_elements = []
            for ns_prefix in ['bmt', 'ns']:
                # Find root namespace
                ns_elems = root.findall(f'.//{ns_prefix}:namespace', self.namespaces)
                if ns_elems:
                    namespace_elements.extend(ns_elems)
            
            self.logger.info(f"Found {len(namespace_elements)} namespace elements")
            
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
                            
                        self.logger.info(f"Found {len(qs_elements)} query subjects using path {search_path}")
                        
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
                            
                            # Check if this query subject is already in our list
                            if any(qs['name'] == qs_name for qs in query_subjects):
                                continue
                            
                            # Extract query items (columns)
                            query_items = self._extract_query_items(qs_elem)
                            
                            # Extract SQL definition if available
                            sql_definition = self._extract_sql_definition(qs_elem)
                            
                            # Create query subject info
                            query_subject = {
                                'name': qs_name,
                                'id': qs_elem.get('id', ''),
                                'type': qs_elem.get('type', ''),
                                'status': qs_elem.get('status', ''),
                                'items': query_items,
                                'sql_definition': sql_definition
                            }
                            
                            query_subjects.append(query_subject)
            
            return query_subjects
            
        except Exception as e:
            self.logger.error(f"Failed to extract query subjects: {e}")
            return []
    
    def _extract_query_items(self, qs_elem: ET.Element) -> List[Dict[str, Any]]:
        """Extract query items (columns) from a query subject element
        
        Args:
            qs_elem: Query subject XML element
            
        Returns:
            List of query items
        """
        query_items = []
        
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
                        
                        # Extract query item properties
                        qi_info = {
                            'name': qi_name,
                            'id': qi_elem.get('id', '')
                        }
                        
                        # Extract datatype
                        for dt_prefix in ['bmt', 'ns']:
                            datatype_elem = qi_elem.find(f'.//{dt_prefix}:datatype', self.namespaces)
                            if datatype_elem is not None and datatype_elem.text:
                                qi_info['datatype'] = datatype_elem.text.strip()
                                qi_info['powerbi_datatype'] = self.map_cognos_type_to_powerbi(datatype_elem.text.strip())
                                break
                        
                        # Extract usage
                        usage = None
                        for usage_prefix in ['bmt', 'ns']:
                            usage_elem = qi_elem.find(f'.//{usage_prefix}:usage', self.namespaces)
                            if usage_elem is not None and usage_elem.text:
                                usage = usage_elem.text.strip()
                                break
                        
                        if usage:
                            qi_info['usage'] = usage
                        
                        # Extract expression
                        for expr_prefix in ['bmt', 'ns']:
                            expr_elem = qi_elem.find(f'.//{expr_prefix}:expression', self.namespaces)
                            if expr_elem is not None:
                                # Get expression text or refobj
                                refobj_elem = expr_elem.find(f'.//{expr_prefix}:refobj', self.namespaces)
                                if refobj_elem is not None and refobj_elem.text:
                                    qi_info['expression'] = f"[{refobj_elem.text.strip()}]"
                                    qi_info['expression_type'] = 'reference'
                                elif expr_elem.text:
                                    qi_info['expression'] = expr_elem.text.strip()
                                    qi_info['expression_type'] = 'calculation'
                                break
                        
                        # Extract regular aggregate
                        for agg_prefix in ['bmt', 'ns']:
                            agg_elem = qi_elem.find(f'.//{agg_prefix}:regularAggregate', self.namespaces)
                            if agg_elem is not None and agg_elem.text:
                                qi_info['regularAggregate'] = agg_elem.text.strip()
                                break
                        
                        # Extract nullable
                        for null_prefix in ['bmt', 'ns']:
                            null_elem = qi_elem.find(f'.//{null_prefix}:nullable', self.namespaces)
                            if null_elem is not None:
                                qi_info['nullable'] = null_elem.text.strip().lower() == 'true'
                                break
                        
                        # Extract hidden
                        for hidden_prefix in ['bmt', 'ns']:
                            hidden_elem = qi_elem.find(f'.//{hidden_prefix}:hidden', self.namespaces)
                            if hidden_elem is not None:
                                qi_info['hidden'] = hidden_elem.text.strip().lower() == 'true'
                                break
                        
                        query_items.append(qi_info)
            
            return query_items
            
        except Exception as e:
            self.logger.warning(f"Failed to extract query items: {e}")
            return []
    
    def _extract_sql_definition(self, qs_elem: ET.Element) -> Dict[str, Any]:
        """Extract SQL definition from a query subject element
        
        Args:
            qs_elem: Query subject XML element
            
        Returns:
            Dictionary with SQL definition
        """
        sql_definition = {}
        
        try:
            # Try to find definition element
            for def_prefix in ['bmt', 'ns']:
                # Try to find dbQuery (Database Layer)
                def_elem = qs_elem.find(f'.//{def_prefix}:definition/{def_prefix}:dbQuery', self.namespaces)
                if def_elem is not None:
                    # Extract SQL
                    for sql_prefix in ['bmt', 'ns']:
                        sql_elem = def_elem.find(f'.//{sql_prefix}:sql', self.namespaces)
                        if sql_elem is not None and sql_elem.text:
                            sql_definition['sql'] = sql_elem.text.strip()
                            sql_definition['type'] = 'dbQuery'
                            break
                    
                    # Extract table type
                    for tt_prefix in ['bmt', 'ns']:
                        tt_elem = def_elem.find(f'.//{tt_prefix}:tableType', self.namespaces)
                        if tt_elem is not None and tt_elem.text:
                            sql_definition['tableType'] = tt_elem.text.strip()
                            break
                    
                    # Extract data source reference
                    for ds_prefix in ['bmt', 'ns']:
                        ds_elem = def_elem.find(f'.//{ds_prefix}:sources/{ds_prefix}:dataSourceRef', self.namespaces)
                        if ds_elem is not None and ds_elem.text:
                            sql_definition['dataSourceRef'] = ds_elem.text.strip()
                            break
                    
                    break
                
                # Try to find modelQuery (Presentation Layer)
                def_elem = qs_elem.find(f'.//{def_prefix}:definition/{def_prefix}:modelQuery', self.namespaces)
                if def_elem is not None:
                    # Extract SQL
                    for sql_prefix in ['bmt', 'ns']:
                        sql_elem = def_elem.find(f'.//{sql_prefix}:sql', self.namespaces)
                        if sql_elem is not None and sql_elem.text:
                            sql_definition['sql'] = sql_elem.text.strip()
                            sql_definition['type'] = 'modelQuery'
                            break
                    
                    break
            
            return sql_definition
            
        except Exception as e:
            self.logger.warning(f"Failed to extract SQL definition: {e}")
            return {}
