"""
M-Query Converter for converting SQL and other data sources to Power BI M-query format.
Uses LLM service to generate optimized M-queries.
"""
import logging
import re
import json
from typing import Dict, Any, Optional, List

from ..llm_service import LLMServiceClient
from ..models import Table


class MQueryConverter:
    """Converts data source queries to Power BI M-query format using LLM service"""
    
    def __init__(self, llm_service_client: LLMServiceClient):
        """
        Initialize the M-Query converter with an LLM service client
        
        Args:
            llm_service_client: LLM service client for M-query generation
        """
        self.llm_service_client = llm_service_client
        self.logger = logging.getLogger(__name__)
    
    def convert_to_m_query(self, table: Table, report_spec: Optional[str] = None, data_sample: Optional[Dict] = None) -> str:
        """
        Convert a table's source query to Power BI M-query format
        
        Args:
            table: Table object containing source query and metadata
            report_spec: Optional report specification XML for context
            data_sample: Optional data sample for context
            
        Returns:
            M-query string
            
        Raises:
            Exception: If the LLM service fails or returns invalid results
        """
        self.logger.info(f"Converting source query to M-query for table: {table.name}")
        
        # Check if table has source_query attribute
        if not hasattr(table, 'source_query'):
            error_msg = f"Table {table.name} does not have a source_query attribute"
            self.logger.error(error_msg)
            raise Exception(error_msg)
            
        # Log if source_query is empty
        if not table.source_query:
            self.logger.info(f"Table {table.name} has empty source_query - this will be handled by the LLM service")
        
        # Prepare context for LLM service
        context = self._build_context(table, report_spec, data_sample)
        
        # Log the context being sent to the LLM service
        self.logger.info(f"Context for table {table.name}:")
        self.logger.info(f"  - Table name: {context['table_name']}")
        self.logger.info(f"  - Columns: {json.dumps([col['name'] for col in context['columns']], indent=2)}")
        self.logger.info(f"  - Source query: {context['source_query'][:100]}..." if context.get('source_query') else "  - Source query: None")
        
        # Call LLM service to generate M-query
        self.logger.info(f"Sending request to LLM service for M-query generation for table {table.name}")
        m_query = self.llm_service_client.generate_m_query(context)
        
        # Clean and format the M-query
        cleaned_m_query = self._clean_m_query(m_query)
        self.logger.info(f"Successfully generated M-query for table {table.name}")
        
        return cleaned_m_query
    
    def _build_context(self, table: Table, report_spec: Optional[str] = None, data_sample: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Build context dictionary for LLM service
        
        Args:
            table: Table object
            report_spec: Optional report specification XML
            data_sample: Optional data sample
            
        Returns:
            Context dictionary for LLM service
        """
        # Build basic context with table information
        context = {
            'table_name': table.name,
            'columns': [{
                'name': col.name,
                'data_type': col.data_type.value if hasattr(col.data_type, 'value') else str(col.data_type),
                'description': col.description if hasattr(col, 'description') else None
            } for col in table.columns],
            'source_query': table.source_query,
        }
        
        # Add report specification if available
        if report_spec:
            # Extract relevant parts of the report spec to keep context size manageable
            context['report_spec'] = self._extract_relevant_report_spec(report_spec, table.name)
        
        # Add data sample if available
        if data_sample:
            context['data_sample'] = data_sample
            
        return context
    
    def _extract_relevant_report_spec(self, report_spec: str, table_name: str) -> str:
        """
        Extract relevant parts of the report specification for a specific table
        
        Args:
            report_spec: Full report specification XML
            table_name: Name of the table to extract relevant parts for
            
        Returns:
            Relevant parts of the report specification
        """
        # This is a simplified implementation - in a real-world scenario,
        # you would parse the XML and extract only the parts relevant to the table
        try:
            # Look for sections related to the table
            table_pattern = f"<.*?{table_name}.*?>"
            matches = re.findall(f"(?s)<.*?{table_name}.*?>.*?</.*?>", report_spec)
            
            if matches:
                # Return first 1000 characters of matches to keep context size manageable
                return "".join(matches)[:1000]
            else:
                return ""
        except Exception as e:
            self.logger.warning(f"Error extracting relevant report spec: {e}")
            return ""
    
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
            self.logger.debug(f"Original M-query before cleaning: {m_query}")
            
            # Unescape double quotes that are incorrectly escaped
            m_query = m_query.replace('\\"', '"')
            
            # Split into let and in parts
            let_in_parts = re.split(r'\s+in\s+', m_query, 1)
            
            if len(let_in_parts) != 2:
                self.logger.warning(f"M-query for table {table_name} doesn't have the expected 'let...in' structure")
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
            
            # Format the M-query with proper indentation
            formatted_query = "let\n"
            
            for i, step in enumerate(steps):
                if '=' in step:
                    var_name, expression = step.split('=', 1)
                    var_name = var_name.strip()
                    expression = expression.strip()
                    
                    # Format table operations to be on a single line
                    if any(func in expression for func in ['Table.', 'Sql.']):
                        # Keep the expression on a single line but preserve quoted strings
                        expression = self._format_table_expression(expression)
                    
                    formatted_query += f"    {var_name} = {expression}"
                else:
                    formatted_query += f"    {step}"
                
                if i < len(steps) - 1:
                    formatted_query += ",\n"
            
            # Format the 'in' part
            formatted_query += f"\nin\n    {in_part}"
            
            return formatted_query
        
        except Exception as e:
            self.logger.error(f"Error cleaning M-query for table {table_name}: {str(e)}")
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
