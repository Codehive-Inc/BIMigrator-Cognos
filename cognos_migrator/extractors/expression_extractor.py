"""
Expression Extractor for Cognos XML report specifications.

This module provides functionality to extract expression information from Cognos XML report specifications.
"""

import logging
from .base_extractor import BaseExtractor


class ExpressionExtractor(BaseExtractor):
    """Extractor for expressions from Cognos XML report specifications."""
    
    def __init__(self, logger=None):
        """Initialize the expression extractor with optional logger."""
        super().__init__(logger)
    
    def extract_expressions(self, root, ns=None):
        """Extract expressions from report specification XML"""
        expressions = []
        try:
            # Register namespace if present
            namespace = self.register_namespace(ns)
            
            # Find all expressions in the report
            expr_elements = self.findall_elements(root, "expression", ns)
                
            for expr_elem in expr_elements:
                # Extract the expression text
                expr_text = self.get_element_text(expr_elem)
                if not expr_text:
                    continue
                    
                # Try to determine context by looking at parent elements
                context = "unknown"
                name = ""
                
                # Since we can't directly get parent, we'll search for dataItems and check if this expression is inside
                data_items = self.findall_elements(root, "dataItem", ns)
                    
                for data_item in data_items:
                    item_expr = self.find_element(data_item, "expression", ns)
                        
                    if item_expr is not None and self.get_element_text(item_expr) == expr_text:
                        context = "dataItem"
                        name = data_item.get("name", "")
                        break
                
                # If not found in dataItems, check filters
                if context == "unknown":
                    filters = self.findall_elements(root, "filterExpression", ns)
                        
                    for filter_expr in filters:
                        if self.get_element_text(filter_expr) == expr_text:
                            context = "filter"
                            break
                
                expressions.append({
                    "context": context,
                    "name": name,
                    "expression": expr_text
                })
                
        except Exception as e:
            self.logger.warning(f"Error extracting expressions: {e}")
            
        return expressions
