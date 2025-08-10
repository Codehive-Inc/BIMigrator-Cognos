"""
Base M-Query Converter for converting data sources to Power BI M-query format.
This is an abstract base class that defines the interface for all M-query converters.
"""
import logging
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path

from ..models import Table


class BaseMQueryConverter(ABC):
    """Abstract base class for M-query converters"""
    
    def __init__(self, output_path: Optional[str] = None):
        """
        Initialize the base M-Query converter
        
        Args:
            output_path: The root output path for the migration.
        """
        self.output_path = output_path
        self.logger = logging.getLogger(__name__)
    
    @abstractmethod
    def convert_to_m_query(self, table: Table, spec: Optional[str] = None, data_sample: Optional[Dict] = None) -> str:
        """
        Convert a table's source query to Power BI M-query format
        
        Args:
            table: Table object containing source query and metadata
            spec: Optional specification (report or package) for context
            data_sample: Optional data sample for context
            
        Returns:
            M-query string
            
        Raises:
            Exception: If the conversion fails or returns invalid results
        """
        pass
    
    def _build_default_m_query(self, table: Table) -> str:
        """
        Builds a default M-query that loads data from a sample Excel file.
        
        Args:
            table: The table object.
            
        Returns:
            The default M-query string.
        """
        column_types = []
        for col in table.columns:
            # A simple mapping, can be improved
            m_type = "type text"
            if col.data_type == "integer":
                m_type = "Int64.Type"
            elif col.data_type == "decimal":
                m_type = "type number"
            elif col.data_type == "datetime":
                m_type = "type datetime"
            
            column_types.append(f'{{\"{col.name}\", {m_type}}}')

        column_types_str = ", ".join(column_types)

        return f"""
let
    Source = Excel.Workbook(File.Contents("C:\\Users\\PowerBIUser\\Documents\\sample_data.xlsx"), null, true),
    Sheet1_Sheet = Source{{[Item="Sheet1",Kind="Sheet"]}}[Data],
    #\"Promoted Headers\" = Table.PromoteHeaders(Sheet1_Sheet, [PromoteAllScalars=true]),
    #\"Changed Type\" = Table.TransformColumnTypes(#\"Promoted Headers\",{{{column_types_str}}})
in
    #\"Changed Type\"
"""
    
    def _build_m_query_from_sql(self, sql_query: str, table: Table) -> str:
        """
        Builds an M-query from a SQL query.
        
        Args:
            sql_query: The SQL query.
            table: The table object.
            
        Returns:
            The M-query string.
        """
        # Escape the SQL query for use in the M-query string
        escaped_sql = sql_query.replace('"', '""')
        
        m_query = f"""
let
    Source = Sql.Database("your_server", "your_database"),
    SQL = Value.NativeQuery(Source, "{escaped_sql}", null, [EnableFolding=true])
in
    SQL
"""
        return m_query
    
    def _clean_m_query(self, m_query: str) -> str:
        """
        Clean M-query by removing comments and fixing formatting
        
        Args:
            m_query: Raw M-query from LLM service
            
        Returns:
            Cleaned and formatted M-query
        """
        try:
            # Log original query for debugging
            self.logger.info(f"[MQUERY_TRACKING] Original M-query before cleaning: {m_query[:200]}...")
            
            # Fix comment formatting - replace spaced comment delimiters and ensure no spaces
            m_query = m_query.replace('/ *', '/*').replace('* /', '*/')
            # Additional check for comment formatting with spaces
            m_query = re.sub(r'/\s*\*', '/*', m_query)
            m_query = re.sub(r'\*\s*/', '*/', m_query)
            
            # Unescape double quotes that are incorrectly escaped
            m_query = m_query.replace('\\"', '"')
            
            # Split into let and in parts
            let_in_parts = re.split(r'\s+in\s+', m_query, 1)
            
            if len(let_in_parts) != 2:
                self.logger.warning(f"[MQUERY_TRACKING] M-query doesn't have the expected 'let...in' structure")
                return m_query
                
            let_part = let_in_parts[0].strip()
            in_part = let_in_parts[1].strip()
            
            # Remove 'let' keyword
            if let_part.lower().startswith('let'):
                let_part = let_part[3:].strip()
            
            # Split the let part into steps by commas, but be careful with commas inside functions
            steps = []
            current_step = ""
            bracket_count = 0
            paren_count = 0
            in_quotes = False
            
            for char in let_part:
                if char == '"' and (len(current_step) == 0 or current_step[-1] != '\\'):
                    in_quotes = not in_quotes
                
                if not in_quotes:
                    if char == '{':
                        bracket_count += 1
                    elif char == '}':
                        bracket_count -= 1
                    elif char == '(':
                        paren_count += 1
                    elif char == ')':
                        paren_count -= 1
                    elif char == ',' and bracket_count == 0 and paren_count == 0:
                        steps.append(current_step.strip())
                        current_step = ""
                        continue
                
                current_step += char
            
            if current_step.strip():
                steps.append(current_step.strip())
            
            # Format the M-query with proper indentation for TMDL files
            # Using the exact indentation pattern from Sheet1.tmdl
            formatted_query = "\tlet\n"
            
            for i, step in enumerate(steps):
                if '=' in step:
                    var_name, expression = step.split('=', 1)
                    var_name = var_name.strip()
                    expression = expression.strip()
                    
                    # Format table operations to be on a single line
                    if any(func in expression for func in ['Table.', 'Sql.']):
                        # Keep the expression on a single line but preserve quoted strings
                        expression = self._format_table_expression(expression)
                    
                    # Match the exact indentation from Sheet1.tmdl with 5 tabs
                    formatted_query += f"\t\t\t\t\t{var_name} = {expression}"
                else:
                    formatted_query += f"\t\t\t\t\t{step}"
                
                if i < len(steps) - 1:
                    formatted_query += ",\n"
            
            # Format the 'in' part with correct indentation (4 tabs for 'in', 5 tabs for expression)
            formatted_query += f"\n\t\t\t\tin\n\t\t\t\t\t{in_part}"
            
            return formatted_query
        
        except Exception as e:
            self.logger.error(f"Error cleaning M-query: {str(e)}")
            return m_query  # Return the original query if cleaning fails
    
    def _format_table_expression(self, expression):
        """
        Format a Table expression to be on a single line with proper formatting.
        
        Args:
            expression (str): The Table expression to format
            
        Returns:
            str: The formatted expression
        """
        # Replace newlines and multiple spaces with a single space
        expression = re.sub(r'\s+', ' ', expression)
        
        # Fix array formatting for column specifications
        # Match patterns like {{"column", type}} and ensure proper spacing
        expression = re.sub(r'\{\{\s*"([^"]+)"\s*,\s*([^\}]+)\s*\}\}', r'{{"\1", \2}}', expression)
        
        # Fix multiple items in an array
        # This matches patterns like {{...}, {...}} and ensures proper formatting
        expression = re.sub(r'\}\}\s*,\s*\{\{', r'}}, {{', expression)
        
        return expression
