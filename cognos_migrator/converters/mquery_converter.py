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
        
        # Check if table has source_query
        if not hasattr(table, 'source_query') or not table.source_query:
            error_msg = f"Table {table.name} does not have a source_query attribute or it's empty"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        
        # Prepare context for LLM service
        context = self._build_context(table, report_spec, data_sample)
        
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
            
            # Remove the leading 'm' if present (sometimes added by LLM)
            if m_query.startswith('m '):
                m_query = m_query[2:]
            
            # Parse the query to identify key components
            if 'let' in m_query and 'in' in m_query:
                # Extract the parts between let and in
                let_part = m_query.split('let')[1].split('in')[0]
                in_part = m_query.split('in')[1].strip()
                
                # Process the let part to remove comments but keep code
                cleaned_let_part = ""
                for line in let_part.split(','):
                    # Remove comments (text after // or / /)
                    code_part = re.sub(r'(/ /|//).*?(?=,|$)', '', line).strip()
                    if code_part:
                        cleaned_let_part += code_part + ", "
                
                # Remove trailing comma if present
                cleaned_let_part = cleaned_let_part.rstrip(', ')
                
                # Clean the in part
                cleaned_in_part = re.sub(r'(/ /|//).*', '', in_part).strip()
                
                # Reconstruct the query
                m_query = f"let {cleaned_let_part} in {cleaned_in_part}"
            
                # Now extract the steps and format them properly
                steps = []
                for step in m_query.split('let')[1].split('in')[0].split(','):
                    step = step.strip()
                    if step:
                        steps.append(step)
                
                # Format the final M-query with proper indentation for TMDL
                formatted_query = "let\n"
                
                # Process each step
                for i, step in enumerate(steps):
                    if '=' in step:
                        parts = step.split('=', 1)
                        step_name = parts[0].strip()
                        step_content = parts[1].strip()
                        
                        # Handle SQL queries - keep them on one line
                        if 'Value.NativeQuery' in step_content or 'Sql.Database' in step_content:
                            # Ensure SQL query is on one line
                            sql_pattern = r'"([^"]*?)"'
                            sql_queries = re.findall(sql_pattern, step_content)
                            for sql in sql_queries:
                                cleaned_sql = sql.replace('\n', ' ').replace('\r', '')
                                step_content = step_content.replace(f'"{sql}"', f'"{cleaned_sql}"')
                        
                        # Handle parameter arrays - keep them on one line
                        if '{{' in step_content and '}}' in step_content:
                            # Ensure parameter arrays are on one line
                            step_content = re.sub(r'\s+', ' ', step_content)
                        
                        formatted_query += f"\t\t\t\t{step_name} = {step_content}"
                        if i < len(steps) - 1:
                            formatted_query += ",\n"
                    else:
                        # Handle steps without '=' (rare case)
                        formatted_query += f"\t\t\t\t{step}"
                        if i < len(steps) - 1:
                            formatted_query += ",\n"
                
                # Add the 'in' part
                formatted_query += f"\n\t\t\tin\n\t\t\t\t{cleaned_in_part}"
                
                return formatted_query
            else:
                # If query doesn't have let/in structure, return as is with minimal formatting
                self.logger.warning(f"M-query doesn't have standard let/in structure: {m_query[:100]}...")
                return m_query
                
        except Exception as e:
            self.logger.error(f"Error cleaning M-query: {e}")
            # Return original if cleaning fails
            return m_query
