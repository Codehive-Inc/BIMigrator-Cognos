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
            
        # First check for calculation indicators - if found, it's definitely a calculation
        calculation_indicators = [
            '(', ')',  # Function calls or grouping
            '+', '-', '*', '/', '>', '<', '=', '!=', '<=', '>=',  # Common operators
            ' if ', ' then ', ' else ',  # Conditional logic
            ' and ', ' or ', ' not ',  # Logical operators
            ' in ', ' case ', ' when ',  # Other keywords
            'substring', 'rpad', 'lpad', 'trim',  # Common functions
            'sum', 'count', 'avg', 'max', 'min'  # Aggregate functions
        ]
        
        # Convert to lowercase for case-insensitive checking
        expr_lower = expression.lower()
        
        # If any calculation indicators are found, it's a calculation
        for indicator in calculation_indicators:
            if indicator.lower() in expr_lower:
                self.logger.debug(f"Expression '{expression}' contains '{indicator}', classified as calculation")
                return False
        
        # Check if the expression matches the pattern of bracketed segments separated by dots
        # This is typical for direct source column references: [Namespace].[Folder].[Item]
        source_column_pattern = r'^\[.*?\](?:\.\[.*?\])+$'
        if re.match(source_column_pattern, expression):
            # If no calculation indicators found and matches pattern, it's likely a source column
            self.logger.debug(f"Expression '{expression}' classified as source column")
            return True
        else:
            # If it doesn't match the source column pattern, it's a calculation
            self.logger.debug(f"Expression '{expression}' doesn't match source column pattern, classified as calculation")
            return False
    
    def extract_expressions(self, root, ns=None):
        """Extract expressions from report specification XML, including those within query dataItem elements"""
        expressions = []
        try:
            # Register namespace if present
            namespace = self.register_namespace(ns)
            
            # Method 1: Find standalone expressions in the report
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
            
            # Method 2: Look for expressions within query dataItem elements
            # This is where calculations like LOC_1 and LOC_2 are found in report queries
            queries = self.findall_elements(root, "query", ns)
            
            for query in queries:
                query_name = query.get("name", "")
                selection = self.find_element(query, "selection", ns)
                
                if selection is not None:
                    data_items = self.findall_elements(selection, "dataItem", ns)
                    
                    for data_item in data_items:
                        item_name = data_item.get("name", "")
                        item_expr = self.find_element(data_item, "expression", ns)
                        
                        if item_expr is not None:
                            expr_text = self.get_element_text(item_expr)
                            if expr_text and not self.is_source_column(expr_text):
                                # This is a calculation within a query dataItem
                                self.logger.debug(f"Found calculation in query '{query_name}': {item_name} = {expr_text}")
                                
                                # Check if we already have this expression
                                existing = next((e for e in expressions if e["expression"] == expr_text), None)
                                if not existing:
                                    expressions.append({
                                        "context": "dataItem",
                                        "name": item_name,
                                        "expression": expr_text,
                                        "query_name": query_name  # Add query context for better table mapping
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
            query_name = expr.get("query_name", "")
            
            # Determine table name from context if possible
            table_name = "Data"  # Default table name
            
            # Enhanced table name mapping logic
            if query_name:
                # Use query name as table name if available
                table_name = query_name
                self.logger.info(f"Using query name as table: {table_name}")
            elif table_mappings and name in table_mappings:
                # First check if we have a direct mapping for this expression name
                table_name = table_mappings[name]
                self.logger.info(f"Using direct mapping for '{name}': {table_name}")
            elif table_mappings and query_name in table_mappings:
                # Check if we have a mapping for the query name
                table_name = table_mappings[query_name]
                self.logger.info(f"Using query mapping for '{query_name}': {table_name}")
            elif table_mappings and 'Data' in table_mappings:
                # Use the default 'Data' table mapping
                table_name = table_mappings['Data']
                self.logger.info(f"Using mapped table name for 'Data': {table_name}")
            
            # Convert the expression to DAX
            try:
                self.logger.info(f"Converting expression '{name}': {cognos_expr}")
                
                # Convert the expression
                conversion_result = self.expression_converter.convert_expression(
                    cognos_formula=cognos_expr,
                    table_name=table_name
                )
                
                if conversion_result is None:
                    self.logger.warning(f"Expression converter returned None for '{name}'")
                    # Use original expression as fallback
                    dax_expression = cognos_expr
                    confidence = 0.0
                    notes = "Conversion service failed"
                    status = "needs_review"
                else:
                    dax_expression = conversion_result.get("dax_expression", cognos_expr)
                    confidence = conversion_result.get("confidence", 0.0)
                    notes = conversion_result.get("notes", "")
                    
                    # Determine status based on confidence
                    status = "converted" if confidence > 0.5 else "needs_review"
                    
                    self.logger.info(f"Conversion result for '{name}': confidence={confidence}, status={status}")
                
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
                
                if notes:
                    calculation["Notes"] = notes
                
                calculations.append(calculation)
                
            except Exception as e:
                self.logger.error(f"Error converting expression '{name}' to DAX: {e}")
                import traceback
                self.logger.debug(f"Full traceback: {traceback.format_exc()}")
                
                # Create calculation entry with error information in Cognos format
                calculation = {
                    "TableName": table_name,
                    "FormulaCaptionCognos": name,
                    "CognosName": name,
                    "FormulaCognos": cognos_expr,
                    "FormulaTypeCognos": context if context != "unknown" else "calculated_column",
                    "PowerBIName": name,
                    "FormulaDax": cognos_expr,  # Use original as fallback
                    "Status": "error",
                    "Error": str(e)
                }
                
                calculations.append(calculation)
        
        self.logger.info(f"Converted {len(calculations)} expressions, found {len([c for c in calculations if c['Status'] == 'converted'])} successful conversions")
        return {"calculations": calculations}
