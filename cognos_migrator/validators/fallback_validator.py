"""
Fallback validation for SELECT * queries and safe DAX expressions
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime


class FallbackValidator:
    """Validates fallback queries to ensure they will work in Power BI"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Safe M-Query patterns for fallback
        self.safe_m_patterns = {
            'sql': 'Sql.Database',
            'oracle': 'Oracle.Database', 
            'excel': 'Excel.Workbook',
            'csv': 'Csv.Document',
            'odata': 'OData.Feed',
            'sharepoint': 'SharePoint.Tables',
            'web': 'Web.Contents',
            'json': 'Json.Document'
        }
        
        # Operations that should NOT be in SELECT * fallback
        self.forbidden_operations = [
            'Table.RemoveColumns',    # Don't remove columns in SELECT *
            'Table.Skip',             # Don't skip rows
            'Table.FirstN',           # Don't limit rows  
            'Table.LastN',            # Don't limit rows
            'Table.MaxN',             # Don't limit rows
            'Table.MinN',             # Don't limit rows
            'Table.Range',            # Don't limit rows
            'Table.RemoveFirstN',     # Don't remove rows
            'Table.RemoveLastN',      # Don't remove rows
            'Table.Distinct',         # Keep all rows in fallback
            'Table.RemoveRowsWithErrors'  # Keep error rows visible
        ]
    
    def validate_select_all_query(self, m_query: str, source_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validate that a SELECT * fallback query will work
        
        Args:
            m_query: The M-Query to validate
            source_info: Optional source connection information
            
        Returns:
            Dictionary with validation results
        """
        result = {
            "is_valid": True,
            "issues": [],
            "warnings": [],
            "is_safe_fallback": True,
            "will_load_data": True,
            "requires_manual_config": False
        }
        
        if not m_query or not m_query.strip():
            result["is_valid"] = False
            result["issues"].append("Empty fallback query")
            return result
        
        # Check basic structure (should have let/in)
        if 'let' not in m_query.lower() or 'in' not in m_query.lower():
            result["is_valid"] = False
            result["issues"].append("Missing let/in structure in fallback query")
            result["is_safe_fallback"] = False
        
        # Check for source definition
        if 'Source' not in m_query:
            result["warnings"].append("No 'Source' step found - ensure data source is defined")
        
        # Check for forbidden operations
        for operation in self.forbidden_operations:
            if operation in m_query:
                result["is_safe_fallback"] = False
                result["issues"].append(f"Fallback query contains forbidden operation: {operation}")
        
        # Check if manual configuration is needed
        if self._requires_manual_configuration(m_query):
            result["requires_manual_config"] = True
            result["warnings"].append("Manual configuration required - contains placeholder values")
        
        # Validate based on source type
        if source_info:
            source_validation = self._validate_source_specific(m_query, source_info)
            if source_validation["issues"]:
                result["issues"].extend(source_validation["issues"])
                result["is_valid"] = False
            result["warnings"].extend(source_validation.get("warnings", []))
        
        # Check if query will actually load data
        data_check = self._check_data_loading(m_query)
        if not data_check["will_load"]:
            result["will_load_data"] = False
            result["issues"].extend(data_check["issues"])
        
        return result
    
    def validate_safe_dax_fallback(self, dax_expression: str, original_expression: str = None) -> Dict[str, Any]:
        """
        Validate that a DAX fallback expression is safe
        
        Args:
            dax_expression: The fallback DAX expression
            original_expression: Optional original expression for reference
            
        Returns:
            Dictionary with validation results
        """
        result = {
            "is_valid": True,
            "issues": [],
            "is_safe": True,
            "returns_blank": False,
            "has_todo_comment": False
        }
        
        if not dax_expression or not dax_expression.strip():
            result["is_valid"] = False
            result["issues"].append("Empty DAX fallback expression")
            return result
        
        # Check if it's a BLANK() fallback
        if 'BLANK()' in dax_expression:
            result["returns_blank"] = True
            result["is_safe"] = True
        
        # Check for TODO/FIXME comments
        if any(marker in dax_expression.upper() for marker in ['TODO', 'FIXME', 'FIX']):
            result["has_todo_comment"] = True
        
        # Check if original expression is preserved in comments
        if original_expression and original_expression not in dax_expression:
            result["warnings"] = ["Original expression not preserved in comments"]
        
        # Ensure no syntax errors in safe fallback
        basic_syntax = self._validate_basic_dax_syntax(dax_expression)
        if not basic_syntax["is_valid"]:
            result["is_valid"] = False
            result["is_safe"] = False
            result["issues"].extend(basic_syntax["issues"])
        
        return result
    
    def generate_safe_fallback_suggestions(self, failed_expression: str, expression_type: str) -> Dict[str, Any]:
        """
        Generate suggestions for safe fallback expressions
        
        Args:
            failed_expression: The expression that failed validation
            expression_type: Type of expression ('dax' or 'mquery')
            
        Returns:
            Dictionary with fallback suggestions
        """
        suggestions = {
            "expression_type": expression_type,
            "failed_expression": failed_expression,
            "suggestions": [],
            "recommended": None
        }
        
        if expression_type.lower() == 'dax':
            # DAX fallback suggestions
            suggestions["suggestions"] = [
                {
                    "name": "BLANK with TODO",
                    "expression": f"BLANK() // TODO: Convert - {failed_expression[:50]}...",
                    "description": "Returns blank value with original as comment"
                },
                {
                    "name": "Zero fallback",
                    "expression": f"0 // FIXME: Original - {failed_expression[:50]}...",
                    "description": "Returns zero for numeric calculations"
                },
                {
                    "name": "Empty string fallback", 
                    "expression": f'"" // TODO: Convert - {failed_expression[:50]}...',
                    "description": "Returns empty string for text calculations"
                },
                {
                    "name": "Error message",
                    "expression": f'"#MIGRATION_ERROR" // {failed_expression[:50]}...',
                    "description": "Returns visible error indicator"
                }
            ]
            suggestions["recommended"] = suggestions["suggestions"][0]
            
        elif expression_type.lower() == 'mquery':
            # M-Query fallback suggestions
            suggestions["suggestions"] = [
                {
                    "name": "Empty table template",
                    "expression": self._generate_empty_table_template(),
                    "description": "Creates empty table with correct structure"
                },
                {
                    "name": "Manual config template",
                    "expression": self._generate_manual_config_template(),
                    "description": "Template requiring manual configuration"
                },
                {
                    "name": "SELECT * template",
                    "expression": self._generate_select_all_template(),
                    "description": "Basic SELECT * requiring connection details"
                }
            ]
            suggestions["recommended"] = suggestions["suggestions"][2]  # SELECT * is usually best
        
        return suggestions
    
    def _requires_manual_configuration(self, m_query: str) -> bool:
        """Check if query has placeholder values requiring manual configuration"""
        placeholders = [
            'YOUR_SERVER',
            'YOUR_DATABASE',
            'TODO',
            'FIXME',
            'Configure',
            'PLACEHOLDER',
            'localhost',
            'sample_data'
        ]
        
        for placeholder in placeholders:
            if placeholder in m_query:
                return True
        
        return False
    
    def _validate_source_specific(self, m_query: str, source_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate query based on specific source type"""
        result = {"issues": [], "warnings": []}
        source_type = source_info.get("source_type", "").lower()
        
        if source_type in ['sql', 'sqlserver']:
            # Check for Sql.Database
            if 'Sql.Database' not in m_query:
                result["issues"].append("SQL source but missing Sql.Database function")
            
            # Check for server/database parameters
            if source_info.get("server") and source_info["server"] not in m_query:
                result["warnings"].append("Source server not found in query")
                
        elif source_type == 'oracle':
            if 'Oracle.Database' not in m_query:
                result["issues"].append("Oracle source but missing Oracle.Database function")
                
        elif source_type == 'excel':
            if 'Excel.Workbook' not in m_query:
                result["issues"].append("Excel source but missing Excel.Workbook function")
            if 'File.Contents' not in m_query:
                result["warnings"].append("Excel source typically needs File.Contents")
                
        elif source_type == 'csv':
            if 'Csv.Document' not in m_query:
                result["issues"].append("CSV source but missing Csv.Document function")
                
        return result
    
    def _check_data_loading(self, m_query: str) -> Dict[str, Any]:
        """Check if query will actually load data"""
        result = {"will_load": True, "issues": []}
        
        # Check for empty table constructors
        if 'Table.FromRows({})' in m_query or 'Table.FromList({})' in m_query:
            result["will_load"] = False
            result["issues"].append("Query creates empty table")
        
        # Check for error-only results
        if 'error "' in m_query.lower():
            result["will_load"] = False  
            result["issues"].append("Query returns an error")
        
        return result
    
    def _validate_basic_dax_syntax(self, dax_expression: str) -> Dict[str, Any]:
        """Basic syntax validation for DAX"""
        result = {"is_valid": True, "issues": []}
        
        # Remove comments for syntax checking
        expression_no_comments = re.sub(r'//.*$', '', dax_expression, flags=re.MULTILINE)
        expression_no_comments = re.sub(r'/\*.*?\*/', '', expression_no_comments, flags=re.DOTALL)
        
        # Check for balanced parentheses
        open_parens = expression_no_comments.count('(')
        close_parens = expression_no_comments.count(')')
        if open_parens != close_parens:
            result["is_valid"] = False
            result["issues"].append("Unbalanced parentheses in DAX fallback")
        
        # Check for balanced quotes
        if expression_no_comments.count('"') % 2 != 0:
            result["is_valid"] = False
            result["issues"].append("Unbalanced quotes in DAX fallback")
        
        return result
    
    def _generate_empty_table_template(self) -> str:
        """Generate empty table M-Query template"""
        return f'''let
    // FALLBACK: Empty table template - configure as needed
    // Generated: {datetime.now().isoformat()}
    Source = Table.FromRows(
        {{}}, 
        type table [
            Column1 = text,
            Column2 = number,
            Column3 = date
        ]
    ),
    #"Note" = "Replace with actual data source"
in
    Source'''
    
    def _generate_manual_config_template(self) -> str:
        """Generate manual configuration template"""
        return f'''let
    // FALLBACK: Manual configuration required
    // TODO: Update connection parameters below
    Config = [
        Server = "YOUR_SERVER",
        Database = "YOUR_DATABASE", 
        Schema = "dbo",
        Table = "YOUR_TABLE"
    ],
    
    // TODO: Uncomment and configure appropriate source
    // Source = Sql.Database(Config[Server], Config[Database]),
    // Source = Oracle.Database(Config[Server], Config[Database]),
    // Source = Excel.Workbook(File.Contents("C:\\path\\to\\file.xlsx")),
    
    Source = Table.FromRows({{}}, type table [Configure_Columns = text]),
    
    #"Error Message" = "Manual configuration required - see TODO comments above"
in
    Source'''
    
    def _generate_select_all_template(self) -> str:
        """Generate SELECT * template"""
        return f'''let
    // FALLBACK: SELECT * template
    // TODO: Update connection parameters
    Source = Sql.Database(
        "YOUR_SERVER",     // TODO: Replace with actual server
        "YOUR_DATABASE"    // TODO: Replace with actual database  
    ),
    
    // Simple SELECT * - modify table/schema as needed
    Data = Source{{[Schema="dbo",Item="YOUR_TABLE"]}}[Data],
    
    // Get all columns dynamically
    AllColumns = Table.ColumnNames(Data),
    
    // Ensure all columns are included
    Result = Table.SelectColumns(Data, AllColumns)
in
    Result'''