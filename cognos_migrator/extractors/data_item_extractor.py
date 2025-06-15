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
            
        # Check for calculation indicators
        calculation_indicators = [
            # Parentheses (function calls)
            '(', ')',
            # Common operators
            '+', '-', '*', '/', '>', '<', '=', '!=', '<=', '>=',
            # Keywords (with spaces to avoid matching within names)
            ' if ', ' then ', ' else ', ' case ', ' when ', ' and ', ' or ', ' not '
        ]
        
        # Check if any calculation indicators are present
        for indicator in calculation_indicators:
            if indicator in expression:
                return False
        
        # Check if it follows the source column pattern: [Namespace].[Folder].[Item]
        # Pattern: starts with [, ends with ], contains dots, and consists only of bracketed segments
        pattern = r'^\[.*?\](?:\.\[.*?\])+$'
        if re.match(pattern, expression):
            return True
        
        # If it doesn't match either pattern clearly, default to treating it as a calculation
        return False
    
    def extract_data_items(self, root, ns=None):
        """Extract data items from report specification XML"""
        data_items = []
        try:
            # Register namespace if present
            namespace = self.register_namespace(ns)
            
            # Find all data items in the report
            data_item_elements = self.findall_elements(root, "dataItem", ns)
                
            for item_elem in data_item_elements:
                # Get the ID from the XML or extract it from the expression
                item_id = item_elem.get("id", "")
                if not item_id:
                    # Try to extract the column name from the expression
                    expression_elem = item_elem.find("expression", ns)
                    if expression_elem is not None and expression_elem.text:
                        # Extract the last part of the path (e.g., As_Of_Date from [C].[C_Time_Perspective_data_module].[Sheet1].[As_Of_Date])
                        expression_text = expression_elem.text
                        # Find the last bracketed segment
                        match = re.search(r'\[([^\]]+)\]$', expression_text)
                        if match:
                            item_id = match.group(1)  # Use the actual column name as is
                    
                    # If we couldn't extract from expression, fall back to name-based ID
                    if not item_id:
                        name = item_elem.get("name", "")
                        if name:
                            item_id = name.replace(" ", "_")
                        else:
                            # Last resort: generate a random UUID
                            item_id = f"col_{str(uuid.uuid4())[:8]}"
                
                data_item = {
                    "name": item_elem.get("name", ""),
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
                # Since ElementTree doesn't have parent navigation, we'll use a different approach
                # Look for data items within query selections
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
                self.logger.debug(f"Classified data item '{data_item['name']}' as {data_item['type']}")
                
                data_items.append(data_item)
                
        except Exception as e:
            self.logger.warning(f"Error extracting data items: {e}")
            
        return data_items
