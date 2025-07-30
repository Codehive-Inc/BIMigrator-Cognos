"""
Expression validation for DAX and Cognos formulas
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any


class ExpressionValidator:
    """Validates Cognos and DAX expressions"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Common Cognos functions
        self.cognos_functions = {
            'total', 'average', 'minimum', 'maximum', 'count', 
            'count_distinct', 'runningSum', 'current_date', 
            'current_timestamp', '_days_between', '_add_days',
            'if', 'then', 'else', 'case', 'when', 'end'
        }
        
        # Common DAX functions
        self.dax_functions = {
            'SUM', 'AVERAGE', 'MIN', 'MAX', 'COUNT', 'DISTINCTCOUNT',
            'CALCULATE', 'FILTER', 'ALL', 'IF', 'SWITCH', 'BLANK',
            'TODAY', 'NOW', 'DATEDIFF', 'DATEADD', 'SUMX', 'AVERAGEX',
            'RELATED', 'RELATEDTABLE', 'VALUES', 'HASONEVALUE'
        }
    
    def validate_cognos_expression(self, expression: str) -> Dict[str, Any]:
        """
        Validate a Cognos expression before conversion
        
        Args:
            expression: The Cognos expression to validate
            
        Returns:
            Dictionary with validation results
        """
        result = {
            "is_valid": True,
            "issues": [],
            "warnings": [],
            "complexity_score": 0,
            "has_balanced_parentheses": True,
            "has_valid_functions": True,
            "column_references": []
        }
        
        if not expression or not expression.strip():
            result["is_valid"] = False
            result["issues"].append("Empty expression")
            return result
        
        # Check balanced parentheses
        if not self._check_balanced_parentheses(expression):
            result["is_valid"] = False
            result["has_balanced_parentheses"] = False
            result["issues"].append("Unbalanced parentheses")
        
        # Extract and validate functions
        functions = self._extract_functions(expression)
        unknown_functions = [f for f in functions if f.lower() not in self.cognos_functions]
        if unknown_functions:
            result["warnings"].append(f"Unknown functions: {', '.join(unknown_functions)}")
        
        # Extract column references
        result["column_references"] = self._extract_column_references(expression)
        
        # Calculate complexity
        result["complexity_score"] = self._calculate_complexity(expression)
        if result["complexity_score"] > 10:
            result["warnings"].append(f"High complexity score: {result['complexity_score']}")
        
        return result
    
    def validate_dax_expression(self, expression: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a DAX expression after conversion
        
        Args:
            expression: The DAX expression to validate
            context: Context containing table name, column mappings, etc.
            
        Returns:
            Dictionary with validation results
        """
        result = {
            "is_valid": True,
            "issues": [],
            "warnings": [],
            "syntax_valid": True,
            "table_references_valid": True,
            "column_references_valid": True,
            "functions_valid": True
        }
        
        if not expression or not expression.strip():
            result["is_valid"] = False
            result["issues"].append("Empty DAX expression")
            return result
        
        # Check basic syntax
        syntax_check = self._validate_dax_syntax(expression)
        if not syntax_check["is_valid"]:
            result["is_valid"] = False
            result["syntax_valid"] = False
            result["issues"].extend(syntax_check["issues"])
        
        # Validate table references
        table_check = self._validate_table_references(expression, context)
        if not table_check["is_valid"]:
            result["is_valid"] = False
            result["table_references_valid"] = False
            result["issues"].extend(table_check["issues"])
        
        # Validate column references
        column_check = self._validate_column_references(expression, context)
        if not column_check["is_valid"]:
            result["is_valid"] = False
            result["column_references_valid"] = False
            result["issues"].extend(column_check["issues"])
        
        # Validate DAX functions
        function_check = self._validate_dax_functions(expression)
        if function_check["warnings"]:
            result["warnings"].extend(function_check["warnings"])
        
        return result
    
    def _check_balanced_parentheses(self, expression: str) -> bool:
        """Check if parentheses are balanced"""
        stack = []
        pairs = {'(': ')', '[': ']', '{': '}'}
        
        for char in expression:
            if char in pairs:
                stack.append(char)
            elif char in pairs.values():
                if not stack:
                    return False
                if pairs[stack.pop()] != char:
                    return False
        
        return len(stack) == 0
    
    def _extract_functions(self, expression: str) -> List[str]:
        """Extract function names from expression"""
        # Pattern to match function calls (word followed by parenthesis)
        pattern = r'(\w+)\s*\('
        matches = re.findall(pattern, expression)
        return list(set(matches))
    
    def _extract_column_references(self, expression: str) -> List[str]:
        """Extract column references from Cognos expression"""
        # Pattern for [ColumnName] format
        pattern = r'\[([^\]]+)\]'
        matches = re.findall(pattern, expression)
        return list(set(matches))
    
    def _calculate_complexity(self, expression: str) -> int:
        """Calculate expression complexity score"""
        score = 0
        
        # Count nested functions
        score += expression.count('(')
        
        # Count operators
        operators = ['+', '-', '*', '/', '=', '<>', '>', '<', '>=', '<=', 'AND', 'OR']
        for op in operators:
            score += expression.upper().count(op)
        
        # Count conditional statements
        conditionals = ['if', 'case', 'when']
        for cond in conditionals:
            score += len(re.findall(rf'\b{cond}\b', expression, re.IGNORECASE))
        
        return score
    
    def _validate_dax_syntax(self, expression: str) -> Dict[str, Any]:
        """Validate basic DAX syntax"""
        result = {"is_valid": True, "issues": []}
        
        # Check for balanced quotes
        single_quotes = expression.count("'")
        if single_quotes % 2 != 0:
            result["is_valid"] = False
            result["issues"].append("Unbalanced single quotes")
        
        double_quotes = expression.count('"')
        if double_quotes % 2 != 0:
            result["is_valid"] = False
            result["issues"].append("Unbalanced double quotes")
        
        # Check parentheses
        if not self._check_balanced_parentheses(expression):
            result["is_valid"] = False
            result["issues"].append("Unbalanced parentheses in DAX")
        
        # Check for common syntax errors
        if "''" in expression:  # Double single quotes
            result["issues"].append("Double single quotes detected")
        
        if expression.strip().endswith(','):
            result["is_valid"] = False
            result["issues"].append("Expression ends with comma")
        
        return result
    
    def _validate_table_references(self, expression: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate table references in DAX"""
        result = {"is_valid": True, "issues": []}
        
        # Extract table references (pattern: 'TableName'[Column])
        pattern = r"'([^']+)'\s*\["
        table_refs = re.findall(pattern, expression)
        
        # Check if context has available tables
        available_tables = context.get("available_tables", [])
        if available_tables:
            invalid_tables = [t for t in table_refs if t not in available_tables]
            if invalid_tables:
                result["is_valid"] = False
                result["issues"].append(f"Unknown tables: {', '.join(invalid_tables)}")
        
        # Check for spaces in table references
        if re.search(r"'\s+\w+\s+'", expression):
            result["issues"].append("Table names contain extra spaces")
        
        return result
    
    def _validate_column_references(self, expression: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate column references in DAX"""
        result = {"is_valid": True, "issues": []}
        
        # Extract column references
        # Pattern 1: [Column] (same table)
        same_table_pattern = r'(?<!\w)\[([^\]]+)\]'
        # Pattern 2: 'Table'[Column]
        cross_table_pattern = r"'[^']+'\s*\[([^\]]+)\]"
        
        same_table_cols = re.findall(same_table_pattern, expression)
        all_cols = re.findall(r'\[([^\]]+)\]', expression)
        
        # Validate against context if available
        available_columns = context.get("columns", [])
        if available_columns:
            # Convert to names if columns are objects
            if isinstance(available_columns[0], dict):
                column_names = [col.get("name", col) for col in available_columns]
            else:
                column_names = available_columns
            
            invalid_columns = [col for col in all_cols if col not in column_names]
            if invalid_columns and context.get("strict_validation", False):
                result["is_valid"] = False
                result["issues"].append(f"Unknown columns: {', '.join(invalid_columns)}")
        
        return result
    
    def _validate_dax_functions(self, expression: str) -> Dict[str, Any]:
        """Validate DAX functions used"""
        result = {"is_valid": True, "warnings": []}
        
        # Extract function calls
        functions = self._extract_functions(expression)
        
        # Check against known DAX functions
        unknown_functions = []
        for func in functions:
            if func.upper() not in self.dax_functions:
                unknown_functions.append(func)
        
        if unknown_functions:
            result["warnings"].append(f"Potentially unknown DAX functions: {', '.join(unknown_functions)}")
        
        return result