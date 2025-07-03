"""
Package relationship extractor for Cognos Framework Manager packages.

This module provides functionality to extract relationships from
Cognos Framework Manager (FM) package files.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any

from .base_package_extractor import BasePackageExtractor


class PackageRelationshipExtractor(BasePackageExtractor):
    """Extractor for relationships in Cognos Framework Manager packages"""
    
    def __init__(self, logger=None):
        """Initialize the relationship extractor
        
        Args:
            logger: Optional logger instance
        """
        super().__init__(logger)
    
    def extract_and_save(self, package_file_path: str, output_dir: str) -> Dict[str, Any]:
        """Extract relationships and save to JSON
        
        Args:
            package_file_path: Path to the FM package file
            output_dir: Directory to save extracted data
            
        Returns:
            Dictionary with extracted relationships
        """
        try:
            # Parse the XML file
            tree = ET.parse(package_file_path)
            root = tree.getroot()
            
            # Extract relationships
            relationships = self.extract_relationships(root)
            
            # Save to JSON file
            self.save_to_json(relationships, output_dir, "relationships.json")
            
            return {"relationships": relationships}
            
        except Exception as e:
            self.logger.error(f"Failed to extract relationships from {package_file_path}: {e}")
            return {"error": str(e)}
    
    def extract_relationships(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract relationships from the XML root
        
        Args:
            root: XML root element
            
        Returns:
            List of relationships
        """
        relationships = []
        
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
            
            # Process each namespace to find relationships
            for namespace in namespace_elements:
                # Try to find relationships in this namespace with different prefixes
                for ns_prefix in ['bmt', 'ns']:
                    # Try multiple paths to find relationships
                    search_paths = [
                        f'.//{ns_prefix}:relationship',
                        f'./{ns_prefix}:relationship',
                        f'./{ns_prefix}:content//{ns_prefix}:relationship',
                        f'./{ns_prefix}:folder//{ns_prefix}:relationship'
                    ]
                    
                    for search_path in search_paths:
                        rel_elements = namespace.findall(search_path, self.namespaces)
                        
                        if not rel_elements:
                            continue
                            
                        self.logger.info(f"Found {len(rel_elements)} relationships using path {search_path}")
                        
                        for rel_elem in rel_elements:
                            # Extract relationship name - try different paths
                            rel_name = None
                            
                            # Try name/n path
                            for path_prefix in ['bmt', 'ns']:
                                name_elem = rel_elem.find(f'.//{path_prefix}:name/{path_prefix}:n', self.namespaces)
                                if name_elem is not None and name_elem.text:
                                    rel_name = name_elem.text.strip()
                                    break
                            
                            # Try direct n element
                            if not rel_name:
                                for path_prefix in ['bmt', 'ns']:
                                    name_elem = rel_elem.find(f'.//{path_prefix}:n', self.namespaces)
                                    if name_elem is not None and name_elem.text:
                                        rel_name = name_elem.text.strip()
                                        break
                            
                            # Try name element with text directly
                            if not rel_name:
                                for path_prefix in ['bmt', 'ns']:
                                    name_elem = rel_elem.find(f'.//{path_prefix}:name', self.namespaces)
                                    if name_elem is not None and name_elem.text:
                                        rel_name = name_elem.text.strip()
                                        break
                            
                            # Try name attribute
                            if not rel_name:
                                if rel_elem.get('name'):
                                    rel_name = rel_elem.get('name')
                            
                            # Skip if no name found
                            if not rel_name:
                                rel_name = f"Relationship_{rel_elem.get('id', 'unknown')}"
                            
                            # Extract left and right sides
                            left_info = self._extract_relationship_side(rel_elem, 'left')
                            right_info = self._extract_relationship_side(rel_elem, 'right')
                            
                            # Extract join expression
                            join_expression = self._extract_join_expression(rel_elem)
                            
                            # Create relationship info
                            relationship = {
                                'name': rel_name,
                                'id': rel_elem.get('id', ''),
                                'left': left_info,
                                'right': right_info,
                                'join_expression': join_expression
                            }
                            
                            # Extract determinants (join columns)
                            determinants = self._extract_determinants(rel_elem)
                            if determinants:
                                relationship['determinants'] = determinants
                            
                            relationships.append(relationship)
            
            return relationships
            
        except Exception as e:
            self.logger.error(f"Failed to extract relationships: {e}")
            return []
    
    def _extract_relationship_side(self, rel_elem: ET.Element, side: str) -> Dict[str, Any]:
        """Extract information about one side of a relationship
        
        Args:
            rel_elem: Relationship XML element
            side: 'left' or 'right'
            
        Returns:
            Dictionary with side information
        """
        side_info = {}
        
        try:
            # Find side element
            for side_prefix in ['bmt', 'ns']:
                side_elem = rel_elem.find(f'.//{side_prefix}:{side}', self.namespaces)
                if side_elem is not None:
                    # Extract refobj (query subject reference)
                    for ref_prefix in ['bmt', 'ns']:
                        refobj_elem = side_elem.find(f'.//{ref_prefix}:refobj', self.namespaces)
                        if refobj_elem is not None and refobj_elem.text:
                            side_info['query_subject'] = refobj_elem.text.strip()
                            break
                    
                    # Extract cardinality
                    for card_prefix in ['bmt', 'ns']:
                        mincard_elem = side_elem.find(f'.//{card_prefix}:mincard', self.namespaces)
                        if mincard_elem is not None and mincard_elem.text:
                            side_info['mincard'] = mincard_elem.text.strip()
                        
                        maxcard_elem = side_elem.find(f'.//{card_prefix}:maxcard', self.namespaces)
                        if maxcard_elem is not None and maxcard_elem.text:
                            side_info['maxcard'] = maxcard_elem.text.strip()
                        
                        break
                    
                    break
            
            return side_info
            
        except Exception as e:
            self.logger.warning(f"Failed to extract relationship {side} side: {e}")
            return {}
    
    def _extract_join_expression(self, rel_elem: ET.Element) -> str:
        """Extract join expression from a relationship element
        
        Args:
            rel_elem: Relationship XML element
            
        Returns:
            Join expression string
        """
        try:
            # Find expression element
            for expr_prefix in ['bmt', 'ns']:
                expr_elem = rel_elem.find(f'.//{expr_prefix}:expression', self.namespaces)
                if expr_elem is not None and expr_elem.text:
                    return expr_elem.text.strip()
            
            return ""
            
        except Exception as e:
            self.logger.warning(f"Failed to extract join expression: {e}")
            return ""
    
    def _extract_determinants(self, rel_elem: ET.Element) -> List[Dict[str, Any]]:
        """Extract determinants (join columns) from a relationship element
        
        Args:
            rel_elem: Relationship XML element
            
        Returns:
            List of determinants
        """
        determinants = []
        
        try:
            # Find determinant elements
            for det_prefix in ['bmt', 'ns']:
                det_elems = rel_elem.findall(f'.//{det_prefix}:determinant', self.namespaces)
                
                for det_elem in det_elems:
                    determinant = {}
                    
                    # Extract left and right expressions
                    for expr_prefix in ['bmt', 'ns']:
                        left_expr_elem = det_elem.find(f'.//{expr_prefix}:leftExpr', self.namespaces)
                        if left_expr_elem is not None:
                            # Try to find refobj
                            refobj_elem = left_expr_elem.find(f'.//{expr_prefix}:refobj', self.namespaces)
                            if refobj_elem is not None and refobj_elem.text:
                                determinant['left_column'] = refobj_elem.text.strip()
                            elif left_expr_elem.text:
                                determinant['left_expression'] = left_expr_elem.text.strip()
                        
                        right_expr_elem = det_elem.find(f'.//{expr_prefix}:rightExpr', self.namespaces)
                        if right_expr_elem is not None:
                            # Try to find refobj
                            refobj_elem = right_expr_elem.find(f'.//{expr_prefix}:refobj', self.namespaces)
                            if refobj_elem is not None and refobj_elem.text:
                                determinant['right_column'] = refobj_elem.text.strip()
                            elif right_expr_elem.text:
                                determinant['right_expression'] = right_expr_elem.text.strip()
                        
                        break
                    
                    # Extract operator
                    for op_prefix in ['bmt', 'ns']:
                        op_elem = det_elem.find(f'.//{op_prefix}:operator', self.namespaces)
                        if op_elem is not None and op_elem.text:
                            determinant['operator'] = op_elem.text.strip()
                            break
                    
                    if determinant:
                        determinants.append(determinant)
            
            return determinants
            
        except Exception as e:
            self.logger.warning(f"Failed to extract determinants: {e}")
            return []
