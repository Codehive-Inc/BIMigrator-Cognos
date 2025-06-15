"""
Expression Extractor for Cognos XML report specifications.

This module provides functionality to extract expression information from Cognos XML report specifications.
"""

import logging
from typing import Dict, Any, Optional, List
from .base_extractor import BaseExtractor


class ExpressionExtractor(BaseExtractor):
    """Extractor for expressions from Cognos XML report specifications."""
    
    def __init__(self, expression_converter=None, logger=None):
        """Initialize the expression extractor with optional expression converter and logger."""
        super().__init__(logger)
        self.expression_converter = expression_converter
    
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
    
    def convert_to_dax(self, expressions, table_mappings=None):
        """
        Convert Cognos expressions to DAX using the expression converter
        
        Args:
            expressions: List of expression dictionaries from extract_expressions
            table_mappings: Optional mapping of Cognos table names to Power BI table names
            
        Returns:
            List of expression dictionaries with added DAX conversion
        """
        if not self.expression_converter:
            self.logger.warning("No expression converter provided, skipping DAX conversion")
            return expressions
            
        converted_expressions = []
        
        for expr in expressions:
            cognos_expr = expr.get("expression", "")
            context = expr.get("context", "unknown")
            name = expr.get("name", "")
            
            # Create a copy of the original expression dict
            converted_expr = expr.copy()
            
            # Convert the expression to DAX
            try:
                # Determine table name from context if possible
                table_name = None
                if table_mappings and name in table_mappings:
                    table_name = table_mappings[name]
                
                # Convert the expression
                conversion_result = self.expression_converter.convert_expression(
                    cognos_formula=cognos_expr,
                    table_name=table_name
                )
                
                # Add the DAX expression and metadata to the result
                converted_expr["dax_expression"] = conversion_result.get("dax_expression", cognos_expr)
                converted_expr["conversion_confidence"] = conversion_result.get("confidence", 0.0)
                converted_expr["conversion_notes"] = conversion_result.get("notes", "")
                
            except Exception as e:
                self.logger.warning(f"Error converting expression to DAX: {e}")
                converted_expr["dax_expression"] = cognos_expr  # Use original as fallback
                converted_expr["conversion_confidence"] = 0.0
                converted_expr["conversion_notes"] = f"Conversion error: {str(e)}"
            
            converted_expressions.append(converted_expr)
        
        return converted_expressions
