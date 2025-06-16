"""
Cognos Expression to DAX Converter
Converts Cognos Analytics expressions and calculations to Power BI DAX format

DEPRECATED: This module is deprecated and will be removed in a future version.
Please use cognos_migrator.converters.expression_converter.ExpressionConverter instead.
"""

import re
import logging
import warnings
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ExpressionMapping:
    """Maps a Cognos function to its DAX equivalent"""
    cognos_pattern: str
    dax_template: str
    requires_context: bool = False
    description: str = ""


class CognosExpressionConverter:
    """Converts Cognos expressions to DAX equivalents"""
    
    def __init__(self):
        warnings.warn(
            "CognosExpressionConverter is deprecated. Please use cognos_migrator.converters.expression_converter.ExpressionConverter instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.logger = logging.getLogger(__name__)
        self._load_function_mappings()
    
    def _load_function_mappings(self):
        """Load mappings from Cognos functions to DAX functions"""
        self.function_mappings = {
            # Aggregation Functions
            'total': ExpressionMapping(
                cognos_pattern=r'total\s*\(\s*([^)]+)\s*\)',
                dax_template='SUM({0})',
                description='Total/Sum aggregation'
            ),
            'average': ExpressionMapping(
                cognos_pattern=r'average\s*\(\s*([^)]+)\s*\)',
                dax_template='AVERAGE({0})',
                description='Average aggregation'
            ),
            'count': ExpressionMapping(
                cognos_pattern=r'count\s*\(\s*([^)]+)\s*\)',
                dax_template='COUNT({0})',
                description='Count aggregation'
            ),
            'minimum': ExpressionMapping(
                cognos_pattern=r'minimum\s*\(\s*([^)]+)\s*\)',
                dax_template='MIN({0})',
                description='Minimum value'
            ),
            'maximum': ExpressionMapping(
                cognos_pattern=r'maximum\s*\(\s*([^)]+)\s*\)',
                dax_template='MAX({0})',
                description='Maximum value'
            ),
            
            # Date Functions
            '_year': ExpressionMapping(
                cognos_pattern=r'_year\s*\(\s*([^)]+)\s*\)',
                dax_template='YEAR({0})',
                description='Extract year from date'
            ),
            '_month': ExpressionMapping(
                cognos_pattern=r'_month\s*\(\s*([^)]+)\s*\)',
                dax_template='MONTH({0})',
                description='Extract month from date'
            ),
            '_day': ExpressionMapping(
                cognos_pattern=r'_day\s*\(\s*([^)]+)\s*\)',
                dax_template='DAY({0})',
                description='Extract day from date'
            ),
            '_quarter': ExpressionMapping(
                cognos_pattern=r'_quarter\s*\(\s*([^)]+)\s*\)',
                dax_template='FORMAT({0}, "Q")',
                description='Extract quarter from date'
            ),
            
            # String Functions
            'substring': ExpressionMapping(
                cognos_pattern=r'substring\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^)]+)\s*\)',
                dax_template='MID({0}, {1}, {2})',
                description='Extract substring'
            ),
            'length': ExpressionMapping(
                cognos_pattern=r'length\s*\(\s*([^)]+)\s*\)',
                dax_template='LEN({0})',
                description='String length'
            ),
            'upper': ExpressionMapping(
                cognos_pattern=r'upper\s*\(\s*([^)]+)\s*\)',
                dax_template='UPPER({0})',
                description='Convert to uppercase'
            ),
            'lower': ExpressionMapping(
                cognos_pattern=r'lower\s*\(\s*([^)]+)\s*\)',
                dax_template='LOWER({0})',
                description='Convert to lowercase'
            ),
            
            # Mathematical Functions
            'round': ExpressionMapping(
                cognos_pattern=r'round\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)',
                dax_template='ROUND({0}, {1})',
                description='Round to specified decimal places'
            ),
            'abs': ExpressionMapping(
                cognos_pattern=r'abs\s*\(\s*([^)]+)\s*\)',
                dax_template='ABS({0})',
                description='Absolute value'
            ),
            
            # Running Totals (Complex)
            'running-total': ExpressionMapping(
                cognos_pattern=r'running-total\s*\(\s*([^)]+)\s*\)',
                dax_template='CALCULATE(SUM({0}), FILTER(ALL({{table}}), {{table}}[{{date_column}}] <= MAX({{table}}[{{date_column}}])))',
                requires_context=True,
                description='Running total calculation'
            ),
            
            # Conditional Functions
            'if': ExpressionMapping(
                cognos_pattern=r'if\s*\(\s*([^)]+?)\s*\)\s*then\s*\(\s*([^)]+?)\s*\)\s*else\s*\(\s*([^)]+?)\s*\)',
                dax_template='IF({0}, {1}, {2})',
                description='Conditional expression'
            ),
            
            # Case Statements
            'case': ExpressionMapping(
                cognos_pattern=r'case\s+(.+?)\s+end',
                dax_template='SWITCH(TRUE(), {0})',
                requires_context=True,
                description='Case/Switch statement'
            )
        }
        
        # Operator mappings
        self.operator_mappings = {
            ' and ': ' && ',
            ' or ': ' || ',
            ' not ': ' NOT ',
            ' = ': ' = ',
            ' <> ': ' <> ',
            ' != ': ' <> ',
            ' is null': ' = BLANK()',
            ' is not null': ' <> BLANK()'
        }
    
    def convert_expression(self, cognos_expr: str, context: Optional[Dict] = None) -> str:
        """
        Convert a Cognos expression to DAX
        
        Args:
            cognos_expr: The Cognos expression to convert
            context: Optional context with table and column information
            
        Returns:
            Converted DAX expression
        """
        if not cognos_expr or not cognos_expr.strip():
            return ""
        
        try:
            dax_expr = cognos_expr.strip()
            
            # Clean up the expression
            dax_expr = self._clean_expression(dax_expr)
            
            # Convert functions
            dax_expr = self._convert_functions(dax_expr, context)
            
            # Convert operators
            dax_expr = self._convert_operators(dax_expr)
            
            # Convert column references
            dax_expr = self._convert_column_references(dax_expr)
            
            # Final cleanup
            dax_expr = self._final_cleanup(dax_expr)
            
            self.logger.info(f"Converted Cognos expression: '{cognos_expr}' -> '{dax_expr}'")
            return dax_expr
            
        except Exception as e:
            self.logger.error(f"Failed to convert expression '{cognos_expr}': {e}")
            # Return original expression as fallback
            return cognos_expr
    
    def _clean_expression(self, expr: str) -> str:
        """Clean up the expression for processing"""
        # Remove extra whitespace
        expr = re.sub(r'\s+', ' ', expr)
        
        # Normalize quotes
        expr = expr.replace("'", '"')
        
        return expr.strip()
    
    def _convert_functions(self, expr: str, context: Optional[Dict] = None) -> str:
        """Convert Cognos functions to DAX functions"""
        for func_name, mapping in self.function_mappings.items():
            pattern = mapping.cognos_pattern
            template = mapping.dax_template
            
            # Find all matches
            matches = re.finditer(pattern, expr, re.IGNORECASE)
            
            for match in reversed(list(matches)):  # Process in reverse to maintain positions
                groups = match.groups()
                
                if mapping.requires_context:
                    # Handle complex functions that need context
                    if func_name == 'running-total':
                        dax_replacement = self._convert_running_total(groups[0], context)
                    elif func_name == 'case':
                        dax_replacement = self._convert_case_statement(groups[0])
                    else:
                        dax_replacement = template.format(*groups)
                else:
                    # Simple function replacement
                    dax_replacement = template.format(*groups)
                
                # Replace in expression
                expr = expr[:match.start()] + dax_replacement + expr[match.end():]
        
        return expr
    
    def _convert_operators(self, expr: str) -> str:
        """Convert Cognos operators to DAX operators"""
        for cognos_op, dax_op in self.operator_mappings.items():
            expr = re.sub(re.escape(cognos_op), dax_op, expr, flags=re.IGNORECASE)
        
        return expr
    
    def _convert_column_references(self, expr: str) -> str:
        """Convert Cognos column references to DAX format"""
        # Convert [Query1].[Column] to [Column] format
        expr = re.sub(r'\[([^\]]+)\]\.\[([^\]]+)\]', r'[\2]', expr)
        
        # Convert bare column names to bracket notation
        # This is a simplified approach - in practice, you'd need more sophisticated parsing
        
        return expr
    
    def _convert_running_total(self, measure_expr: str, context: Optional[Dict] = None) -> str:
        """Convert running total to DAX CALCULATE expression"""
        if not context:
            # Fallback without context
            return f"CALCULATE(SUM({measure_expr}), FILTER(ALL(Table), Table[Date] <= MAX(Table[Date])))"
        
        table_name = context.get('table_name', 'Table')
        date_column = context.get('date_column', 'Date')
        
        return f"CALCULATE(SUM({measure_expr}), FILTER(ALL({table_name}), {table_name}[{date_column}] <= MAX({table_name}[{date_column}])))"
    
    def _convert_case_statement(self, case_body: str) -> str:
        """Convert Cognos CASE statement to DAX SWITCH"""
        # This is a simplified conversion
        # In practice, you'd need to parse the WHEN clauses properly
        
        # Extract WHEN clauses
        when_pattern = r'when\s+(.+?)\s+then\s+(.+?)(?=\s+when|\s+else|$)'
        when_matches = re.findall(when_pattern, case_body, re.IGNORECASE | re.DOTALL)
        
        # Extract ELSE clause
        else_pattern = r'else\s+(.+?)$'
        else_match = re.search(else_pattern, case_body, re.IGNORECASE | re.DOTALL)
        
        # Build SWITCH expression
        switch_conditions = []
        for condition, result in when_matches:
            switch_conditions.append(f"{condition.strip()}, {result.strip()}")
        
        switch_expr = ", ".join(switch_conditions)
        
        if else_match:
            switch_expr += f", {else_match.group(1).strip()}"
        
        return f"SWITCH(TRUE(), {switch_expr})"
    
    def _final_cleanup(self, expr: str) -> str:
        """Final cleanup of the DAX expression"""
        # Remove extra spaces around operators
        expr = re.sub(r'\s*([+\-*/=<>])\s*', r' \1 ', expr)
        
        # Clean up multiple spaces
        expr = re.sub(r'\s+', ' ', expr)
        
        return expr.strip()
    
    def get_supported_functions(self) -> List[str]:
        """Get list of supported Cognos functions"""
        return list(self.function_mappings.keys())
    
    def validate_expression(self, cognos_expr: str) -> Tuple[bool, List[str]]:
        """
        Validate if a Cognos expression can be converted
        
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        if not cognos_expr or not cognos_expr.strip():
            issues.append("Empty expression")
            return False, issues
        
        # Check for unsupported functions
        # This is a basic check - could be enhanced
        
        return len(issues) == 0, issues


class DAXExpressionBuilder:
    """Helper class for building complex DAX expressions"""
    
    def __init__(self):
        self.converter = CognosExpressionConverter()
    
    def build_time_intelligence_measure(self, base_measure: str, time_function: str, 
                                      date_table: str = "Date", date_column: str = "Date") -> str:
        """Build time intelligence DAX measures"""
        time_functions = {
            'ytd': f"TOTALYTD({base_measure}, {date_table}[{date_column}])",
            'qtd': f"TOTALQTD({base_measure}, {date_table}[{date_column}])",
            'mtd': f"TOTALMTD({base_measure}, {date_table}[{date_column}])",
            'py': f"CALCULATE({base_measure}, SAMEPERIODLASTYEAR({date_table}[{date_column}]))",
            'pq': f"CALCULATE({base_measure}, PARALLELPERIOD({date_table}[{date_column}], -1, QUARTER))",
            'pm': f"CALCULATE({base_measure}, PARALLELPERIOD({date_table}[{date_column}], -1, MONTH))"
        }
        
        return time_functions.get(time_function.lower(), base_measure)
    
    def build_variance_measure(self, current_measure: str, comparison_measure: str, 
                             variance_type: str = "absolute") -> str:
        """Build variance DAX measures"""
        if variance_type.lower() == "percentage":
            return f"DIVIDE({current_measure} - {comparison_measure}, {comparison_measure}, 0)"
        else:
            return f"{current_measure} - {comparison_measure}"