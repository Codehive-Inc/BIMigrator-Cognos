"""
M-Query validation for Power BI expressions
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any


class MQueryValidator:
    """Validates Power BI M-Query expressions"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Core M-Query keywords that must be present
        self.required_keywords = {'let', 'in'}
        
        # Common M-Query functions
        self.m_functions = {
            # Table operations
            'Table.SelectColumns', 'Table.TransformColumnTypes', 'Table.AddColumn',
            'Table.RemoveColumns', 'Table.RenameColumns', 'Table.SelectRows',
            'Table.Sort', 'Table.Group', 'Table.Join', 'Table.NestedJoin',
            'Table.ExpandTableColumn', 'Table.Buffer', 'Table.Distinct',
            'Table.FromRows', 'Table.FromList', 'Table.FromRecords',
            'Table.PromoteHeaders', 'Table.Skip', 'Table.FirstN',
            'Table.RemoveRowsWithErrors', 'Table.ReplaceErrorValues',
            'Table.TransformColumns', 'Table.ColumnNames',
            
            # Data source connections
            'Sql.Database', 'Oracle.Database', 'OData.Feed', 'Web.Contents',
            'Excel.Workbook', 'Csv.Document', 'Json.Document', 'Xml.Document',
            'SharePoint.Tables', 'SharePoint.Contents', 'File.Contents',
            'Folder.Contents', 'Binary.Decompress',
            
            # Type operations
            'type table', 'type text', 'type number', 'type date', 
            'type datetime', 'type time', 'type logical', 'type any',
            'Int64.Type', 'Currency.Type', 'Percentage.Type',
            
            # List operations
            'List.Transform', 'List.Select', 'List.Generate', 'List.Accumulate',
            
            # Other common functions
            'Value.NativeQuery', 'Value.Type', 'DateTime.LocalNow',
            'Date.From', 'DateTime.From', 'Text.From', 'Number.From'
        }
        
        # Dangerous operations that might break query folding
        self.dangerous_operations = {
            'List.Generate': 'Breaks query folding',
            'List.Transform': 'May break query folding',
            'Table.AddIndexColumn': 'Breaks query folding',
            'Web.Page': 'No query folding support',
            'Json.Document': 'Limited query folding'
        }
    
    def validate_m_query(self, m_query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validate an M-Query expression
        
        Args:
            m_query: The M-Query expression to validate
            context: Optional context with table info, optimization preferences, etc.
            
        Returns:
            Dictionary with validation results
        """
        result = {
            "is_valid": True,
            "issues": [],
            "warnings": [],
            "structure_valid": True,
            "syntax_valid": True,
            "source_valid": True,
            "type_operations_valid": True,
            "query_folding_preserved": True,
            "performance_score": 100
        }
        
        if not m_query or not m_query.strip():
            result["is_valid"] = False
            result["issues"].append("Empty M-Query expression")
            return result
        
        # Check basic structure
        structure_check = self._validate_structure(m_query)
        if not structure_check["is_valid"]:
            result["is_valid"] = False
            result["structure_valid"] = False
            result["issues"].extend(structure_check["issues"])
        
        # Check syntax
        syntax_check = self._validate_syntax(m_query)
        if not syntax_check["is_valid"]:
            result["is_valid"] = False
            result["syntax_valid"] = False
            result["issues"].extend(syntax_check["issues"])
        
        # Check source definition
        source_check = self._validate_source_definition(m_query)
        if not source_check["is_valid"]:
            result["is_valid"] = False
            result["source_valid"] = False
            result["issues"].extend(source_check["issues"])
        
        # Check type operations
        type_check = self._validate_type_operations(m_query)
        if type_check["warnings"]:
            result["warnings"].extend(type_check["warnings"])
        
        # Check query folding if context specifies
        if context and context.get("query_folding_preference") != "None":
            folding_check = self._check_query_folding(m_query, context)
            if not folding_check["preserved"]:
                result["query_folding_preserved"] = False
                result["warnings"].extend(folding_check["warnings"])
                result["performance_score"] -= folding_check["penalty"]
        
        # Calculate overall performance score
        result["performance_score"] = max(0, result["performance_score"])
        
        return result
    
    def _validate_structure(self, m_query: str) -> Dict[str, Any]:
        """Validate basic let/in structure"""
        result = {"is_valid": True, "issues": []}
        
        # Normalize whitespace for checking
        normalized = ' '.join(m_query.split())
        
        # Check for 'let' keyword
        if not re.search(r'\blet\b', normalized, re.IGNORECASE):
            result["is_valid"] = False
            result["issues"].append("Missing 'let' keyword")
        
        # Check for 'in' keyword
        if not re.search(r'\bin\b', normalized, re.IGNORECASE):
            result["is_valid"] = False
            result["issues"].append("Missing 'in' keyword")
        
        # Check that 'let' comes before 'in'
        let_match = re.search(r'\blet\b', normalized, re.IGNORECASE)
        in_match = re.search(r'\bin\b', normalized, re.IGNORECASE)
        
        if let_match and in_match:
            if let_match.start() > in_match.start():
                result["is_valid"] = False
                result["issues"].append("'in' appears before 'let'")
        
        # Check for at least one step definition
        if not re.search(r'=', normalized):
            result["is_valid"] = False
            result["issues"].append("No step definitions found (missing '=' assignments)")
        
        return result
    
    def _validate_syntax(self, m_query: str) -> Dict[str, Any]:
        """Validate M-Query syntax"""
        result = {"is_valid": True, "issues": []}
        
        # Check for balanced parentheses
        if not self._check_balanced_delimiters(m_query, '(', ')'):
            result["is_valid"] = False
            result["issues"].append("Unbalanced parentheses")
        
        # Check for balanced square brackets
        if not self._check_balanced_delimiters(m_query, '[', ']'):
            result["is_valid"] = False
            result["issues"].append("Unbalanced square brackets")
        
        # Check for balanced curly braces
        if not self._check_balanced_delimiters(m_query, '{', '}'):
            result["is_valid"] = False
            result["issues"].append("Unbalanced curly braces")
        
        # Check for balanced quotes
        if m_query.count('"') % 2 != 0:
            result["is_valid"] = False
            result["issues"].append("Unbalanced double quotes")
        
        # Check for proper step definitions
        lines = m_query.split('\n')
        in_let_block = False
        for line in lines:
            if 'let' in line.lower():
                in_let_block = True
            elif 'in' in line.lower():
                in_let_block = False
            elif in_let_block and '=' in line:
                # Check for proper step naming
                step_name = line.split('=')[0].strip()
                if step_name and not self._is_valid_step_name(step_name):
                    result["issues"].append(f"Invalid step name: {step_name}")
        
        # Check for trailing commas
        if re.search(r',\s*\n\s*in\b', m_query, re.IGNORECASE):
            result["is_valid"] = False
            result["issues"].append("Trailing comma before 'in' keyword")
        
        return result
    
    def _validate_source_definition(self, m_query: str) -> Dict[str, Any]:
        """Validate that there's a valid source definition"""
        result = {"is_valid": True, "issues": []}
        
        # Look for Source = definition
        if not re.search(r'Source\s*=', m_query, re.IGNORECASE):
            # It's okay if the first step isn't named "Source"
            # Just check that there's at least one data source function
            
            source_functions = [
                'Sql.Database', 'Oracle.Database', 'Excel.Workbook',
                'Csv.Document', 'OData.Feed', 'Web.Contents',
                'Table.FromRows', 'Table.FromList', 'Table.FromRecords'
            ]
            
            has_source = False
            for func in source_functions:
                if func in m_query:
                    has_source = True
                    break
            
            if not has_source:
                result["issues"].append("No data source connection found")
        
        return result
    
    def _validate_type_operations(self, m_query: str) -> Dict[str, Any]:
        """Validate type operations and transformations"""
        result = {"warnings": []}
        
        # Check for Table.TransformColumnTypes
        if 'Table.TransformColumnTypes' not in m_query:
            result["warnings"].append("No explicit type transformations found - consider adding Table.TransformColumnTypes")
        
        # Check for 'type any' usage (less specific)
        if 'type any' in m_query:
            result["warnings"].append("Using 'type any' - consider using more specific types")
        
        # Check for proper type syntax
        type_pattern = r'type\s+(table|text|number|date|datetime|time|logical|any)'
        invalid_types = re.findall(r'type\s+(\w+)', m_query)
        valid_types = ['table', 'text', 'number', 'date', 'datetime', 'time', 'logical', 'any']
        
        for found_type in invalid_types:
            if found_type not in valid_types and not found_type.endswith('.Type'):
                result["warnings"].append(f"Potentially invalid type: 'type {found_type}'")
        
        return result
    
    def _check_query_folding(self, m_query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check if query folding is preserved"""
        result = {"preserved": True, "warnings": [], "penalty": 0}
        
        preference = context.get("query_folding_preference", "BestEffort")
        
        # Check for operations that break query folding
        for operation, reason in self.dangerous_operations.items():
            if operation in m_query:
                if preference == "Strict":
                    result["preserved"] = False
                    result["warnings"].append(f"{operation} breaks query folding: {reason}")
                    result["penalty"] += 20
                elif preference == "BestEffort":
                    result["warnings"].append(f"Warning: {operation} may impact performance: {reason}")
                    result["penalty"] += 10
        
        # Check for custom functions (usually break folding)
        if re.search(r'=>', m_query):  # Lambda expressions
            if preference == "Strict":
                result["preserved"] = False
                result["warnings"].append("Custom functions (=>) break query folding")
                result["penalty"] += 30
            else:
                result["warnings"].append("Custom functions may impact query performance")
                result["penalty"] += 15
        
        # Check for optimal operation order
        if 'Table.SelectRows' in m_query:
            # Check if filtering happens early
            lines = m_query.split('\n')
            select_line = -1
            transform_line = -1
            
            for i, line in enumerate(lines):
                if 'Table.SelectRows' in line:
                    select_line = i
                if 'Table.TransformColumnTypes' in line:
                    transform_line = i
            
            if select_line > transform_line > -1:
                result["warnings"].append("Consider filtering (Table.SelectRows) before type transformations for better performance")
                result["penalty"] += 5
        
        return result
    
    def _check_balanced_delimiters(self, text: str, open_delim: str, close_delim: str) -> bool:
        """Check if delimiters are balanced"""
        count = 0
        in_string = False
        i = 0
        
        while i < len(text):
            # Handle string literals
            if text[i] == '"' and (i == 0 or text[i-1] != '\\'):
                in_string = not in_string
            
            # Only count delimiters outside of strings
            if not in_string:
                if text[i] == open_delim:
                    count += 1
                elif text[i] == close_delim:
                    count -= 1
                    if count < 0:
                        return False
            
            i += 1
        
        return count == 0
    
    def _is_valid_step_name(self, name: str) -> bool:
        """Check if step name is valid"""
        # Remove # prefix and quotes if present
        cleaned = name.strip()
        if cleaned.startswith('#"') and cleaned.endswith('"'):
            cleaned = cleaned[2:-1]
        elif cleaned.startswith('#'):
            cleaned = cleaned[1:]
        
        # Check if it's a valid identifier
        if not cleaned:
            return False
        
        # Must start with letter or underscore
        if not (cleaned[0].isalpha() or cleaned[0] == '_'):
            return False
        
        # Can contain letters, numbers, underscores, spaces
        for char in cleaned:
            if not (char.isalnum() or char in '_ '):
                return False
        
        return True