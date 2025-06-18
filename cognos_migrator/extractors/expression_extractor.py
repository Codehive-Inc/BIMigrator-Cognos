"""
Expression Extractor for Cognos XML report specifications.

This module provides functionality to extract expression information from Cognos XML report specifications.
"""

import logging
import re
from typing import Dict, Any, Optional, List
from .base_extractor import BaseExtractor


class ExpressionExtractor(BaseExtractor):
    """Extractor for expressions from Cognos XML report specifications."""
    
    def __init__(self, expression_converter=None, logger=None):
        """Initialize the expression extractor with optional expression converter and logger."""
        super().__init__(logger)
        self.expression_converter = expression_converter
        
    def is_source_column(self, expression: str) -> bool:
        """
        Determine if an expression is a source column or a calculation based on its structure.
        
        Source columns typically follow a pattern like [Namespace].[Folder].[Item] with no operations.
        Calculations contain functions, operators, or other computational elements.
        
        Args:
            expression: The expression string to analyze
            
        Returns:
            bool: True if the expression appears to be a source column, False if it's a calculation
        """
        if not expression:
            return False
            
        # Check if the expression matches the pattern of bracketed segments separated by dots
        # This is typical for direct source column references: [Namespace].[Folder].[Item]
        source_column_pattern = r'^\[.*?\](?:\.\[.*?\])+$'
        if re.match(source_column_pattern, expression):
            # Check for indicators that this might be a calculation despite matching the pattern
            calculation_indicators = [
                '(', ')',  # Function calls or grouping
                '+', '-', '*', '/', '>', '<', '=',  # Common operators
                ' if ', ' then ', ' else ',  # Conditional logic
                ' and ', ' or ', ' not ',  # Logical operators
                ' in ', ' case ', ' when '  # Other keywords
            ]
            
            # If any calculation indicators are found, it's likely a calculation
            for indicator in calculation_indicators:
                if indicator in expression:
                    self.logger.debug(f"Expression '{expression}' contains '{indicator}', classified as calculation")
                    return False
                    
            # If no calculation indicators found, it's likely a source column
            self.logger.debug(f"Expression '{expression}' classified as source column")
            return True
        else:
            # If it doesn't match the source column pattern, it's a calculation
            self.logger.debug(f"Expression '{expression}' doesn't match source column pattern, classified as calculation")
            return False
    
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
                    
                # Skip source columns - we only want to include calculations
                if self.is_source_column(expr_text):
                    self.logger.debug(f"Skipping source column expression: {expr_text}")
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
            Dictionary with calculations array in the desired format
        """
        if not self.expression_converter:
            self.logger.warning("No expression converter provided, skipping DAX conversion")
            return {"calculations": []}
            
        calculations = []
        
        for expr in expressions:
            cognos_expr = expr.get("expression", "")
            context = expr.get("context", "unknown")
            name = expr.get("name", "")
            
            # Determine table name from context if possible
            table_name = "Data"  # Default table name
            
            # First check if we have a direct mapping for this expression name
            if table_mappings and name in table_mappings:
                table_name = table_mappings[name]
            # Then check if we have a mapping for the default 'Data' table
            elif table_mappings and 'Data' in table_mappings:
                table_name = table_mappings['Data']
                self.logger.info(f"Using mapped table name for 'Data': {table_name}")
            
            # Convert the expression to DAX
            try:
                # Convert the expression
                conversion_result = self.expression_converter.convert_expression(
                    cognos_formula=cognos_expr,
                    table_name=table_name
                )
                
                dax_expression = conversion_result.get("dax_expression", cognos_expr)
                confidence = conversion_result.get("confidence", 0.0)
                notes = conversion_result.get("notes", "")
                
                # Determine status based on confidence
                status = "converted" if confidence > 0.5 else "needs_review"
                
                # Create calculation entry in the Cognos format
                calculation = {
                    "TableName": table_name,
                    "FormulaCaptionCognos": name,
                    "CognosName": name,
                    "FormulaCognos": cognos_expr,
                    "FormulaTypeCognos": context if context != "unknown" else "calculated_column",
                    "PowerBIName": name,
                    "FormulaDax": dax_expression,
                    "Status": status
                }
                
                calculations.append(calculation)
                
            except Exception as e:
                self.logger.warning(f"Error converting expression to DAX: {e}")
                
                # Create calculation entry with error information in Cognos format
                calculation = {
                    "TableName": table_name,
                    "FormulaCaptionCognos": name,
                    "CognosName": name,
                    "FormulaCognos": cognos_expr,
                    "FormulaTypeCognos": context if context != "unknown" else "calculated_column",
                    "PowerBIName": name,
                    "FormulaDax": cognos_expr,  # Use original as fallback
                    "Status": "needs_review"
                }
                
                calculations.append(calculation)
        
        return {"calculations": calculations}
