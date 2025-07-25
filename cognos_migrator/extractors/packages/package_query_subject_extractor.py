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
            # Find all query subjects in the XML
            for def_prefix in ['bmt', 'ns']:
                # Look for query subjects in all layers
                layers = ['Database Layer', 'Business Layer', 'Presentation Layer']
                for layer in layers:
                    # Try to find query subjects in this layer
                    ns_path = f".//{def_prefix}:namespace/{def_prefix}:name[.='{layer}']/..//{def_prefix}:querySubject"
                    for qs in root.findall(ns_path, self.namespaces):
                        # Extract basic info
                        name = None
                        # Try name/n path first (common in this format)
                        name_elem = qs.find(f".//{def_prefix}:name/{def_prefix}:n", self.namespaces)
                        if name_elem is None or not name_elem.text:
                            # Try direct name element
                            name_elem = qs.find(f".//{def_prefix}:name", self.namespaces)
                        
                        if name_elem is not None and name_elem.text:
                            query_subject = {
                                'name': name_elem.text.strip(),
                                'layer': layer,
                                'status': qs.get('status', 'unknown')
                            }
                            
                            # Extract items (columns)
                            items = self._extract_query_items(qs)
                            if items:
                                query_subject['items'] = items
                            
                            # Extract SQL definition
                            sql_def = self._extract_sql_definition(qs)
                            if sql_def:
                                query_subject['sql_definition'] = sql_def
                                
                            # Log extraction
                            self.logger.info(f"Extracted query subject {query_subject['name']} from {layer}")
                            if 'sql_definition' in query_subject:
                                self.logger.info(f"SQL found for {query_subject['name']}: {query_subject['sql_definition'].get('sql', '')[:100]}...")
                            
                            query_subjects.append(query_subject)
            
            self.logger.info(f"Found {len(query_subjects)} query subjects")
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
            # Try all possible paths
            for def_prefix in ['bmt', 'ns']:
                # Find all query items
                items = qs_elem.findall(f'.//{def_prefix}:queryItem', self.namespaces)
                
                for item in items:
                    # Extract name - try name/n first, then name
                    name = None
                    name_elem = item.find(f'.//{def_prefix}:name/{def_prefix}:n', self.namespaces)
                    if name_elem is None or not name_elem.text:
                        name_elem = item.find(f'.//{def_prefix}:name', self.namespaces)
                    
                    if name_elem is not None and name_elem.text:
                        query_item = {
                            'name': name_elem.text.strip(),
                            'id': item.get('id', '')
                        }
                        
                        # Extract data type
                        datatype = item.find(f'.//{def_prefix}:datatype', self.namespaces)
                        if datatype is not None and datatype.text:
                            dtype = datatype.text.strip().lower()
                            query_item['datatype'] = dtype
                            
                            # Add precision and scale for numeric types
                            if 'decimal' in dtype or 'numeric' in dtype or 'double' in dtype:
                                precision = item.find(f'.//{def_prefix}:precision', self.namespaces)
                                if precision is not None and precision.text:
                                    query_item['precision'] = int(precision.text)
                                
                                scale = item.find(f'.//{def_prefix}:scale', self.namespaces)
                                if scale is not None and scale.text:
                                    query_item['scale'] = int(scale.text)
                            
                            # Add size for character types
                            if 'char' in dtype or 'string' in dtype:
                                size = item.find(f'.//{def_prefix}:size', self.namespaces)
                                if size is not None and size.text:
                                    query_item['size'] = int(size.text)
                        
                        # Extract usage (identifier, attribute, fact)
                        usage = item.find(f'.//{def_prefix}:usage', self.namespaces)
                        if usage is not None and usage.text:
                            query_item['usage'] = usage.text.strip()
                        
                        # Extract source column from expression/refobj
                        expr = item.find(f'.//{def_prefix}:expression/{def_prefix}:refobj', self.namespaces)
                        if expr is not None and expr.text:
                            # Clean up the reference - remove layer prefix if present
                            ref = expr.text.strip()
                            if '].[' in ref:
                                ref = ref.split('].[')[-1]  # Get last part after layer
                            query_item['source_column'] = ref
                        
                        # Extract nullable property
                        nullable = item.find(f'.//{def_prefix}:nullable', self.namespaces)
                        if nullable is not None and nullable.text:
                            query_item['nullable'] = nullable.text.strip().lower() == 'true'
                        
                        # Extract regular aggregate
                        agg = item.find(f'.//{def_prefix}:regularAggregate', self.namespaces)
                        if agg is not None and agg.text:
                            query_item['regular_aggregate'] = agg.text.strip()
                        
                        query_items.append(query_item)
                
                # If we found items, no need to try other prefixes
                if query_items:
                    break
            
            # Sort items by usage - identifiers first, then attributes, then facts
            usage_order = {'identifier': 0, 'attribute': 1, 'fact': 2}
            query_items.sort(key=lambda x: usage_order.get(x.get('usage', ''), 99))
            
            return query_items
            
        except Exception as e:
            self.logger.error(f"Failed to extract query items: {e}")
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
            # Try all possible SQL paths
            for def_prefix in ['bmt', 'ns']:
                # Try to find definition element first
                def_elem = qs_elem.find(f'.//{def_prefix}:definition', self.namespaces)
                if def_elem is not None:
                    # Try dbQuery first (Database Layer)
                    db_query = def_elem.find(f'.//{def_prefix}:dbQuery', self.namespaces)
                    if db_query is not None:
                        # Extract SQL
                        sql_elem = db_query.find(f'.//{def_prefix}:sql', self.namespaces)
                        if sql_elem is not None:
                            # Handle SQL element with type attribute
                            sql_type = sql_elem.get('type', '')
                            if sql_type == 'cognos':
                                # Extract SQL from column and table elements
                                column_elem = sql_elem.find(f'.//{def_prefix}:column', self.namespaces)
                                table_elem = sql_elem.find(f'.//{def_prefix}:table', self.namespaces)
                                if column_elem is not None and table_elem is not None:
                                    # Split table reference into database and table parts
                                    table_parts = table_elem.text.split('.')
                                    if len(table_parts) > 1:
                                        # Extract database name and clean it
                                        database = table_parts[0].strip('[]')
                                        table_name = table_parts[-1]
                                        sql_definition['sql'] = f"SELECT {column_elem.text} FROM {table_name}"
                                        sql_definition['database'] = database
                                    else:
                                        sql_definition['sql'] = f"SELECT {column_elem.text} FROM {table_elem.text}"
                            else:
                                # Direct SQL text
                                sql_definition['sql'] = sql_elem.text.strip() if sql_elem.text else None
                                
                            if sql_definition.get('sql'):
                                sql_definition['type'] = 'dbQuery'
                                
                                # Extract table type
                                tt_elem = db_query.find(f'.//{def_prefix}:tableType', self.namespaces)
                                if tt_elem is not None and tt_elem.text:
                                    sql_definition['tableType'] = tt_elem.text.strip()
                                
                                # Extract data source reference
                                ds_elem = db_query.find(f'.//{def_prefix}:sources/{def_prefix}:dataSourceRef', self.namespaces)
                                if ds_elem is not None and ds_elem.text:
                                    sql_definition['dataSourceRef'] = ds_elem.text.strip()
                                    # Extract server and database from data source ref
                                    # Format is typically [].[dataSources].[Database]
                                    parts = ds_elem.text.strip().split('.')[-1].strip('[]')
                                    sql_definition['server'] = 'localhost'  # Default to localhost
                                    sql_definition['database'] = parts
                                
                                break
                    
                    # Try expression (Business Layer)
                    if not sql_definition:
                        expr_items = def_elem.findall(f'.//{def_prefix}:expression/{def_prefix}:refobj', self.namespaces)
                        if expr_items:
                            # Build SQL from expression references
                            refs = []
                            for expr in expr_items:
                                if expr.text:
                                    refs.append(expr.text.strip())
                            if refs:
                                sql_definition['sql'] = f"SELECT {', '.join(refs)}"
                                sql_definition['type'] = 'expression'
                                break
                    
                    # Try modelQuery (Presentation Layer)
                    if not sql_definition:
                        model_query = def_elem.find(f'.//{def_prefix}:modelQuery', self.namespaces)
                        if model_query is not None:
                            # Extract SQL
                            sql_elem = model_query.find(f'.//{def_prefix}:sql', self.namespaces)
                            if sql_elem is not None and sql_elem.text:
                                sql_definition['sql'] = sql_elem.text.strip()
                                sql_definition['type'] = 'modelQuery'
                                break
                
                # Try direct SQL element as last resort
                if not sql_definition:
                    sql_elem = qs_elem.find(f'.//{def_prefix}:sql', self.namespaces)
                    if sql_elem is not None and sql_elem.text:
                        sql_definition['sql'] = sql_elem.text.strip()
                        sql_definition['type'] = 'directQuery'
                        break
            
            # Log the extracted SQL for debugging
            if 'sql' in sql_definition:
                self.logger.info(f"Extracted SQL ({sql_definition.get('type')}): {sql_definition['sql'][:100]}...")
            else:
                self.logger.warning("No SQL found in query subject")
            
            return sql_definition
            
        except Exception as e:
            self.logger.error(f"Failed to extract SQL definition: {e}")
            return {}
