"""
FM Package extractor for Cognos Framework Manager packages.

This module provides functionality to extract data model information from
Cognos Framework Manager (FM) package files.
"""

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Any

from cognos_migrator.models import DataModel, Table, Column, Relationship


class PackageExtractor:
    """Extractor for Cognos Framework Manager package files"""
    
    def __init__(self, logger=None):
        """Initialize the package extractor
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        # Support multiple possible namespace versions
        self.namespaces = {
            'bmt': 'http://www.developer.cognos.com/schemas/bmt/60/12',  # Common in newer files
            'ns': 'http://www.developer.cognos.com/schemas/bmt/60/7',      # For backward compatibility
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
        }
    
    def extract_package(self, package_file_path: str) -> Dict[str, Any]:
        """Extract package information from an FM package file
        
        Args:
            package_file_path: Path to the FM package file
            
        Returns:
            Dictionary containing extracted package information
        """
        try:
            self.logger.info(f"Extracting package from {package_file_path}")
            
            # Parse the XML file
            tree = ET.parse(package_file_path)
            root = tree.getroot()
            
            # Extract package metadata
            package_name = self._extract_package_name(root)
            
            # Extract query subjects (tables)
            query_subjects = self._extract_query_subjects(root)
            
            # Extract relationships
            relationships = self._extract_relationships(root)
            
            # Combine into package info
            package_info = {
                'name': package_name,
                'query_subjects': query_subjects,
                'relationships': relationships
            }
            
            self.logger.info(f"Successfully extracted package: {package_name}")
            return package_info
            
        except Exception as e:
            self.logger.error(f"Failed to extract package from {package_file_path}: {e}")
            raise
    
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
    
    def _extract_query_subjects(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract query subjects (tables) from the XML root
        
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
                            query_items = []
                            
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
                                        # Extract query item name - try different paths
                                        qi_name = None
                                        
                                        # Try name/n path
                                        for item_prefix in ['bmt', 'ns']:
                                            qi_name_elem = qi_elem.find(f'.//{item_prefix}:name/{item_prefix}:n', self.namespaces)
                                            if qi_name_elem is not None and qi_name_elem.text:
                                                qi_name = qi_name_elem.text.strip()
                                                break
                                        
                                        # Try direct n element
                                        if not qi_name:
                                            for item_prefix in ['bmt', 'ns']:
                                                qi_name_elem = qi_elem.find(f'.//{item_prefix}:n', self.namespaces)
                                                if qi_name_elem is not None and qi_name_elem.text:
                                                    qi_name = qi_name_elem.text.strip()
                                                    break
                                        
                                        # Try name attribute
                                        if not qi_name and qi_elem.get('name'):
                                            qi_name = qi_elem.get('name')
                                        
                                        # Skip if no name found
                                        if not qi_name:
                                            continue
                                        
                                        # Extract usage (attribute, measure, etc.)
                                        usage = 'attribute'  # Default
                                        for item_prefix in ['bmt', 'ns']:
                                            usage_elem = qi_elem.find(f'.//{item_prefix}:usage', self.namespaces)
                                            if usage_elem is not None and usage_elem.text:
                                                usage = usage_elem.text.strip()
                                                break
                                
                                # Extract data type
                                datatype = 'string'  # Default
                                for item_prefix in ['bmt', 'ns']:
                                    datatype_elem = qi_elem.find(f'./{item_prefix}:datatype', self.namespaces)
                                    if datatype_elem is not None and datatype_elem.text:
                                        datatype = datatype_elem.text.strip()
                                        break
                                
                                # Create query item
                                query_item = {
                                    'name': qi_name,
                                    'usage': usage,
                                    'datatype': datatype
                                }
                                
                                query_items.append(query_item)
                        
                        # Extract SQL definition if available
                        sql_text = None
                        for path_prefix in ['bmt', 'ns']:
                            # Try different SQL paths
                            sql_paths = [
                                f'.//{path_prefix}:sql',
                                f'.//{path_prefix}:definition/{path_prefix}:dbQuery/{path_prefix}:sql',
                                f'.//{path_prefix}:definition/{path_prefix}:modelQuery/{path_prefix}:sql'
                            ]
                            
                            for sql_path in sql_paths:
                                sql_elem = qs_elem.find(sql_path, self.namespaces)
                                if sql_elem is not None and sql_elem.text:
                                    sql_text = sql_elem.text.strip()
                                    break
                            
                            if sql_text:
                                break
                        
                        # Create query subject
                        query_subject = {
                            'name': qs_name,
                            'columns': query_items,
                            'sql': sql_text
                        }
                        
                        query_subjects.append(query_subject)
            
            self.logger.info(f"Extracted {len(query_subjects)} query subjects")
            return query_subjects
            
        except Exception as e:
            self.logger.error(f"Failed to extract query subjects: {e}")
            return []
    
    def _extract_relationships(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract relationships from the XML root
        
        Args:
            root: XML root element
            
        Returns:
            List of relationships
        """
        relationships = []
        
        try:
            # Find all namespaces first (Database Layer, Presentation Layer, etc.)
            namespace_elements = []
            for ns_prefix in ['bmt', 'ns']:
                # Find root namespace
                ns_elems = root.findall(f'.//{ns_prefix}:namespace', self.namespaces)
                if ns_elems:
                    namespace_elements.extend(ns_elems)
                    break
            
            # Process each namespace to find relationships
            for namespace in namespace_elements:
                # Try to find relationships in this namespace with different prefixes
                for ns_prefix in ['bmt', 'ns']:
                    rel_elements = namespace.findall(f'.//{ns_prefix}:relationship', self.namespaces)
                    
                    if not rel_elements:
                        continue
                        
                    self.logger.info(f"Found {len(rel_elements)} relationships in namespace")
                    
                    for rel_elem in rel_elements:
                        # Extract relationship name - try different paths
                        rel_name = None
                        
                        # Try name/n path
                        for path_prefix in ['bmt', 'ns']:
                            name_elem = rel_elem.find(f'./{path_prefix}:name/{path_prefix}:n', self.namespaces)
                            if name_elem is not None and name_elem.text:
                                rel_name = name_elem.text.strip()
                                break
                        
                        # Try direct n element
                        if not rel_name:
                            for path_prefix in ['bmt', 'ns']:
                                name_elem = rel_elem.find(f'./{path_prefix}:n', self.namespaces)
                                if name_elem is not None and name_elem.text:
                                    rel_name = name_elem.text.strip()
                                    break
                        
                        # Use default name if not found
                        if not rel_name:
                            rel_name = "Unnamed Relationship"
                        
                        # Extract source and target tables
                        source_table = None
                        target_table = None
                        
                        # Try different paths for left/right elements
                        for path_prefix in ['bmt', 'ns']:
                            # Left (source) table
                            left_elem = rel_elem.find(f'./{path_prefix}:left/{path_prefix}:refobj', self.namespaces)
                            if left_elem is not None and left_elem.text:
                                source_table = left_elem.text.strip()
                            
                            # Right (target) table
                            right_elem = rel_elem.find(f'./{path_prefix}:right/{path_prefix}:refobj', self.namespaces)
                            if right_elem is not None and right_elem.text:
                                target_table = right_elem.text.strip()
                            
                            if source_table and target_table:
                                break
                        
                        # Skip if source or target table not found
                        if not source_table or not target_table:
                            continue
                        
                        # Extract source and target columns from expression
                        source_columns = []
                        target_columns = []
                        
                        # Try to find expression with different prefixes
                        expr_text = None
                        for path_prefix in ['bmt', 'ns']:
                            expr_elem = rel_elem.find(f'./{path_prefix}:expression', self.namespaces)
                            if expr_elem is not None and expr_elem.text:
                                expr_text = expr_elem.text.strip()
                                break
                        
                        if expr_text:
                            # Parse expression to find source and target columns
                            # Example: [Source].[Column] = [Target].[Column]
                            import re
                            
                            # Look for patterns like [Table].[Column]
                            matches = re.findall(r'\[(.*?)\]\.\[(.*?)\]', expr_text)
                            
                            if len(matches) >= 2:
                                # Extract column names from matches
                                # We need to determine which match belongs to source and which to target
                                for match in matches:
                                    table_name = match[0]
                                    column_name = match[1]
                                    
                                    # Check if this is part of the source table path
                                    if source_table and source_table.endswith(table_name):
                                        source_columns.append(column_name)
                                    # Check if this is part of the target table path
                                    elif target_table and target_table.endswith(table_name):
                                        target_columns.append(column_name)
                        
                        # If we couldn't extract columns from expression, check for determinants
                        if not source_columns or not target_columns:
                            # Try to extract from determinants
                            for path_prefix in ['bmt', 'ns']:
                                # Check for determinants in source table
                                determinants = rel_elem.findall(f'.//{path_prefix}:determinant', self.namespaces)
                                for det in determinants:
                                    # Extract key and attributes
                                    key_elem = det.find(f'./{path_prefix}:key/{path_prefix}:refobj', self.namespaces)
                                    if key_elem is not None and key_elem.text:
                                        # Extract column name from refobj path
                                        key_parts = key_elem.text.strip().split('.')[-1]
                                        if source_table in key_elem.text:
                                            source_columns.append(key_parts)
                                        elif target_table in key_elem.text:
                                            target_columns.append(key_parts)
                        
                        # Use empty lists if no columns found
                        if not source_columns:
                            source_columns = []
                        if not target_columns:
                            target_columns = []
                        
                        # Create relationship
                        relationship = {
                            'name': rel_name,
                            'source_table': source_table,
                            'target_table': target_table,
                            'source_columns': source_columns,
                            'target_columns': target_columns
                        }
                        
                        relationships.append(relationship)
            
            self.logger.info(f"Extracted {len(relationships)} relationships")
            return relationships
            
        except Exception as e:
            self.logger.error(f"Failed to extract relationships: {e}")
            return []
    
    def convert_to_data_model(self, package_info: Dict[str, Any]) -> DataModel:
        """Convert package info to a Power BI data model
        
        Args:
            package_info: Package information extracted from FM file
            
        Returns:
            DataModel object for Power BI
        """
        try:
            # Create tables
            tables = []
            for qs in package_info['query_subjects']:
                columns = []
                for col in qs['columns']:
                    column = Column(
                        name=col['name'],
                        data_type=self._map_data_type(col['datatype']),
                        is_hidden=False,
                        description=""
                    )
                    columns.append(column)
                
                table = Table(
                    name=qs['name'],
                    columns=columns,
                    measures=[],
                    source_query=qs.get('sql', '')
                )
                tables.append(table)
            
            # Create relationships
            relationships = []
            for rel in package_info['relationships']:
                # Only create relationships if we have exactly one column on each side
                if len(rel['source_columns']) == 1 and len(rel['target_columns']) == 1:
                    relationship = Relationship(
                        from_table=rel['source_table'],
                        from_column=rel['source_columns'][0],
                        to_table=rel['target_table'],
                        to_column=rel['target_columns'][0],
                        cross_filter_direction="both"
                    )
                    relationships.append(relationship)
            
            # Create data model
            data_model = DataModel(
                name=package_info['name'],
                tables=tables,
                relationships=relationships
            )
            
            return data_model
            
        except Exception as e:
            self.logger.error(f"Failed to convert package to data model: {e}")
            raise
    
    def _map_data_type(self, cognos_type: str) -> str:
        """Map Cognos data types to Power BI data types
        
        Args:
            cognos_type: Cognos data type
            
        Returns:
            Power BI data type
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
