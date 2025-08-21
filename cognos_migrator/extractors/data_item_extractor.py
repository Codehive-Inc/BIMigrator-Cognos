"""
Data Item Extractor for Cognos XML report specifications.

This module provides functionality to extract data item information from Cognos XML report specifications.
"""

import logging
import re
import uuid
from .base_extractor import BaseExtractor


class DataItemExtractor(BaseExtractor):
    """Extractor for data items from Cognos XML report specifications."""
    
    def __init__(self, logger=None):
        """Initialize the data item extractor with optional logger."""
        super().__init__(logger)
        self.column_table_mapping = {}  # Store column to table mapping
        
    def extract_table_name(self, expression: str) -> str:
        """
        Extract table name from a source column expression.
        
        Args:
            expression: The source column expression
            
        Returns:
            str: Extracted table name or empty string if not found
        """
        if not expression:
            return ""
            
        # Match pattern [Schema].[Table].[Column]
        match = re.match(r'\[.*?\]\.\[(.*?)\]\.\[.*?\]', expression)
        if match:
            return match.group(1)
        return ""
        
    def extract_referenced_columns(self, expression: str) -> list:
        """
        Extract column names referenced in a calculation expression.
        
        Args:
            expression: The calculation expression
            
        Returns:
            list: List of referenced column names
        """
        if not expression:
            return []
            
        # Find all column references in square brackets that aren't part of a qualified reference
        return re.findall(r'\[([^\]]+)\](?!\.[^\]]+\])', expression)
    
    def is_source_column(self, expression: str) -> bool:
        """
        Determine if an expression refers to a source column or a calculation.
        
        Args:
            expression: The Cognos expression string
            
        Returns:
            True if the expression is a source column reference, False if it's a calculation
        """
        if not expression:
            return False
            
        # Check if the expression matches the pattern of bracketed segments separated by dots
        # This is typical for direct source column references: [Namespace].[Folder].[Item]
        source_column_pattern = r'^\[.*?\](?:\.\[.*?\])+$'
        if re.match(source_column_pattern, expression):
            # If matches pattern, it's likely a source column
            self.logger.debug(f"Expression '{expression}' classified as source column (pattern match)")
            return True
            
        # Check for calculation indicators - if found, it's definitely a calculation
        # Operators and special characters
        if any(op in expression for op in ['+', '-', '*', '/', '>', '<', '=', '!=', '<=', '>=', '(', ')']):
            self.logger.debug(f"Expression '{expression}' contains operators/parentheses, classified as calculation")
            return False
            
        # Convert to lowercase for case-insensitive keyword checking
        expr_lower = expression.lower()
        
        # Check for keywords with word boundaries to avoid false positives
        keywords = [
            r'\bif\b', r'\bthen\b', r'\belse\b',  # Conditional logic
            r'\band\b', r'\bor\b', r'\bnot\b',    # Logical operators
            r'\bin\b', r'\bcase\b', r'\bwhen\b'   # Other keywords
        ]
        
        for keyword in keywords:
            if re.search(keyword, expr_lower):
                self.logger.debug(f"Expression '{expression}' contains keyword matching '{keyword}', classified as calculation")
                return False
                
        # Check for functions with word boundaries to avoid false positives
        functions = [
            r'\bsubstring\b', r'\brpad\b', r'\blpad\b', r'\btrim\b',  # String functions
            r'\bsum\b', r'\bcount\b', r'\bavg\b', r'\bmax\b', r'\bmin\b'  # Aggregate functions
        ]
        
        for func in functions:
            if re.search(func, expr_lower):
                self.logger.debug(f"Expression '{expression}' contains function matching '{func}', classified as calculation")
                return False
        
        # If we get here, it's likely a simple reference or a calculation we couldn't detect
        # Default to treating it as a calculation if it doesn't match the source column pattern
        self.logger.debug(f"Expression '{expression}' doesn't match source column pattern, classified as calculation")
        return False
    
    def extract_data_items(self, root, ns=None):
        """Extract data items from report specification XML using two passes"""
        data_items = []
        try:
            # Register namespace if present
            namespace = self.register_namespace(ns)
            
            # Find all data items in the report
            data_item_elements = self.findall_elements(root, "dataItem", ns)
            
            # First pass: Process source columns and build column-table mapping
            for item_elem in data_item_elements:
                # Get basic item info
                name = item_elem.get("name", "")
                
                # Extract expression
                expr_elem = self.find_element(item_elem, "expression", ns)
                expression = self.get_element_text(expr_elem) if expr_elem is not None else ""
                
                # Extract table name and build mapping
                table_name = self.extract_table_name(expression)
                if table_name and name:
                    self.column_table_mapping[name] = table_name
                    self.logger.debug(f"Mapped column '{name}' to table '{table_name}'")
            
            # Second pass: Process all items with table name resolution
            for item_elem in data_item_elements:
                # Get the ID from the XML or extract it from the expression
                item_id = item_elem.get("id", "")
                name = item_elem.get("name", "")
                
                if not item_id:
                    # Try to extract the column name from the expression
                    expression_elem = item_elem.find("expression", ns)
                    if expression_elem is not None and expression_elem.text:
                        # Extract the last part of the path
                        expression_text = expression_elem.text
                        match = re.search(r'\[([^\]]+)\]$', expression_text)
                        if match:
                            item_id = match.group(1)
                    
                    # If we couldn't extract from expression, fall back to name-based ID
                    if not item_id:
                        if name:
                            item_id = name.replace(" ", "_")
                        else:
                            # Last resort: generate a random UUID
                            item_id = f"col_{str(uuid.uuid4())[:8]}"
                
                data_item = {
                    "name": name,
                    "id": item_id,
                    "aggregate": item_elem.get("aggregate", "none"),
                }
                
                # Extract expression
                expr_elem = self.find_element(item_elem, "expression", ns)
                expression = ""
                if expr_elem is not None:
                    expression = self.get_element_text(expr_elem)
                    data_item["expression"] = expression
                
                # Determine if this is a source column or calculation
                is_source = self.is_source_column(expression)
                data_item["type"] = "source_column" if is_source else "calculation"
                
                # Extract table name
                table_name = ""
                if expression:
                    # First try to extract directly from expression
                    table_name = self.extract_table_name(expression)
                    if not table_name:
                        # If no direct table name, try to find from referenced columns
                        referenced_cols = self.extract_referenced_columns(expression)
                        for col in referenced_cols:
                            if col in self.column_table_mapping:
                                table_name = self.column_table_mapping[col]
                                self.logger.debug(f"Found table name '{table_name}' for calculation '{name}' from referenced column '{col}'")
                                break
                
                if table_name:
                    data_item["table_name"] = table_name
                
                # Extract XML attributes for data type and usage
                xml_attrs = self.find_element(item_elem, "XMLAttributes", ns)
                    
                if xml_attrs is not None:
                    data_type_attr = self.find_element(xml_attrs, "XMLAttribute[@name='RS_dataType']", ns)
                    data_usage_attr = self.find_element(xml_attrs, "XMLAttribute[@name='RS_dataUsage']", ns)
                    format_attr = self.find_element(xml_attrs, "XMLAttribute[@name='RS_formatProperties']", ns)
                        
                    if data_type_attr is not None:
                        data_item["dataType"] = data_type_attr.get("value", "")
                    if data_usage_attr is not None:
                        data_item["dataUsage"] = data_usage_attr.get("value", "")
                    if format_attr is not None:
                        data_item["formatProperties"] = format_attr.get("value", "")
                
                # Try to determine the source query by looking at the context
                query_elements = self.findall_elements(root, "query", ns)
                    
                for query_elem in query_elements:
                    query_name = query_elem.get("name", "")
                    
                    # Look for this data item in the query's selection
                    selection_elem = self.find_element(query_elem, "selection", ns)
                        
                    if selection_elem is not None:
                        query_data_items = self.findall_elements(
                            selection_elem, 
                            f"dataItem[@name='{data_item['name']}']", 
                            ns
                        )
                            
                        if query_data_items:
                            data_item["queryName"] = query_name
                            break
                
                # Log the classification for debugging
                self.logger.debug(f"Classified data item '{data_item['name']}' as {data_item['type']} in table '{table_name}'")
                
                data_items.append(data_item)
                
        except Exception as e:
            self.logger.warning(f"Error extracting data items: {e}")
            
        return data_items
