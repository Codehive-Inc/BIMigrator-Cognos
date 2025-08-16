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
    
    def convert_to_dax(self, expressions, table_mappings=None, query_data=None):
        """
        Convert Cognos expressions to DAX using the expression converter
        
        Args:
            expressions: List of expression dictionaries from extract_expressions
            table_mappings: Optional mapping of Cognos table names to Power BI table names
            query_data: Optional query data from report_queries.json for context extraction
            
        Returns:
            Dictionary with calculations array in the desired format
        """
        if not self.expression_converter:
            self.logger.warning("No expression converter provided, skipping DAX conversion")
            return {"calculations": []}
            
        # Prepare calculations for batch processing
        calc_dict = {}
        for expr in expressions:
            name = expr.get('name')
            cognos_expr = expr.get('expression')
            query_name = expr.get('query_name')
            
            # Skip empty expressions
            if not cognos_expr or cognos_expr.strip() == "":
                self.logger.info(f"Skipping empty expression: {name}")
                continue
            
            # Determine table name for the expression
            table_name = query_name
            if table_mappings and name in table_mappings:
                # Check if we have a direct mapping for this field name
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
            
            # Add to calculation dictionary for batch processing
            calc_dict[name] = {
                "cognos_expression": cognos_expr,
                "table_name": table_name,
                "column_name": name,
                "type": expr.get('type', 'dataItem')
            }
        
        # Extract column mappings from query data if available
        column_mappings = {}
        if query_data:
            for query in query_data:
                for item in query.get('data_items', []):
                    item_name = item.get('name')
                    item_expr = item.get('expression')
                    if item_expr and '[' in item_expr and '].[' in item_expr:
                        # Extract table name from fully qualified references
                        parts = item_expr.split('].[')  
                        if len(parts) >= 3:
                            table_name = parts[1].strip('[')  # Extract middle part as table name
                            column_mappings[f'[{item_name}]'] = f"'{table_name}'[{item_name}]"
        
        # Try batch conversion with dependency resolution first
        calculations = []
        if self.expression_converter and len(calc_dict) > 1:  # Only use batch if we have multiple calculations
            self.logger.info(f"Attempting batch conversion with dependency resolution for {len(calc_dict)} expressions")
            try:
                batch_result = self.expression_converter.resolve_dependencies(
                    calculations=calc_dict,
                    table_mappings=table_mappings,
                    global_column_mappings=column_mappings
                )
                
                if batch_result and 'results' in batch_result:
                    self.logger.info(f"Batch conversion successful for {len(batch_result['results'])} expressions")
                    
                    # Process batch results
                    for name, result in batch_result['results'].items():
                        if name in calc_dict:
                            calc_data = calc_dict[name]
                            dax_expression = result.get('dax_expression', calc_data['cognos_expression'])
                            status = "converted" if result.get('status') == "converted" else "needs_review"
                            notes = result.get('notes', "")
                            
                            calculations.append({
                                "TableName": calc_data['table_name'],
                                "FormulaCaptionCognos": name,
                                "CognosName": name,
                                "FormulaCognos": calc_data['cognos_expression'],
                                "FormulaTypeCognos": calc_data['type'],
                                "PowerBIName": name,
                                "FormulaDax": dax_expression,
                                "Status": status,
                                "Notes": notes,
                                "Dependencies": result.get('dependencies', [])
                            })
                    
                    # Return early if all calculations were processed
                    if len(calculations) == len(calc_dict):
                        return {"calculations": calculations}
                    
                    # Otherwise, remove processed calculations from calc_dict
                    for name in batch_result['results'].keys():
                        if name in calc_dict:
                            del calc_dict[name]
            except Exception as e:
                self.logger.error(f"Error in batch conversion: {str(e)}")
                # Continue with individual conversion for remaining calculations
        
        # Process remaining expressions individually
        for name, calc_data in calc_dict.items():
            cognos_expr = calc_data['cognos_expression']
            table_name = calc_data['table_name']
            
            try:
                self.logger.info(f"Converting expression '{name}' individually: {cognos_expr}")
                
                # Convert the expression
                conversion_result = self.expression_converter.convert_expression(
                    cognos_formula=cognos_expr,
                    table_name=table_name,
                    column_mappings=column_mappings,
                    query_data=query_data
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
                    if confidence >= 0.8:
                        status = "converted"
                    else:
                        status = "needs_review"
                        
                # Add to calculations list
                calculations.append({
                    "TableName": table_name,
                    "FormulaCaptionCognos": name,
                    "CognosName": name,
                    "FormulaCognos": cognos_expr,
                    "FormulaTypeCognos": calc_data['type'],
                    "PowerBIName": name,
                    "FormulaDax": dax_expression,
                    "Status": status,
                    "Notes": notes
                })
                
            except Exception as e:
                self.logger.error(f"Error converting expression '{name}': {str(e)}")
                # Add to calculations list with error
                calculations.append({
                    "TableName": table_name,
                    "FormulaCaptionCognos": name,
                    "CognosName": name,
                    "FormulaCognos": cognos_expr,
                    "FormulaTypeCognos": calc_data['type'],
                    "PowerBIName": name,
                    "FormulaDax": cognos_expr,
                    "Status": "needs_review",
                    "Notes": f"Error during conversion: {str(e)}"
                })
        
        self.logger.info(f"Converted {len(calculations)} expressions, found {len([c for c in calculations if c['Status'] == 'converted'])} successful conversions")
        return {"calculations": calculations}
