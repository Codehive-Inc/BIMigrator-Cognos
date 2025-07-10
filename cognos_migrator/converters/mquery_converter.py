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
        
        # Prepare enhanced context for LLM service
        context = self._build_enhanced_context(table, report_spec, data_sample)
        
        # Log the context being sent to the LLM service
        self.logger.info(f"Enhanced context for table {table.name}:")
        self.logger.info(f"  - Table name: {context['table_name']}")
        self.logger.info(f"  - Columns: {json.dumps([col['name'] for col in context['columns']], indent=2)}")
        self.logger.info(f"  - Source query: {context['source_query'][:100]}..." if context.get('source_query') else "  - Source query: None")
        if 'source_info' in context:
            self.logger.info(f"  - Source type: {context['source_info']['source_type']}")
        
        # Add options for enhanced M-query generation
        context['options'] = {
            'query_folding_preference': 'BestEffort',
            'error_handling_strategy': 'RemoveErrors',
            'add_buffer': False,
            'add_documentation_comments': True
        }
        
        # Call LLM service to generate M-query
        self.logger.info(f"Sending request to LLM service for enhanced M-query generation for table {table.name}")
        m_query = self.llm_service_client.generate_m_query(context)
        
        # Clean and format the M-query
        cleaned_m_query = self._clean_m_query(m_query)
        self.logger.info(f"Successfully generated M-query for table {table.name}")
        
        return cleaned_m_query
    
    def _build_context(self, table: Table, report_spec: Optional[str] = None, data_sample: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Build basic context dictionary for LLM service (legacy method)
        
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
    
    def _build_enhanced_context(self, table: Table, report_spec: Optional[str] = None, data_sample: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Build enhanced context dictionary for LLM service with structured information
        
        Args:
            table: Table object
            report_spec: Optional report specification XML
            data_sample: Optional data sample
            
        Returns:
            Enhanced context dictionary for LLM service
        """
        # Start with basic context
        context = self._build_context(table, report_spec, data_sample)
        
        # Add source information based on table metadata
        source_type = "Unknown"
        connection_details = {}
        
        # Determine source type from table metadata
        if hasattr(table, 'source_type'):
            source_type = table.source_type
        elif hasattr(table, 'database_type') and table.database_type:
            source_type = table.database_type
        elif table.source_query and 'SELECT' in table.source_query.upper():
            source_type = "SqlServer"  # Default to SQL Server for SQL queries
        elif hasattr(table, 'cognos_path') and table.cognos_path:
            source_type = "CognosFrameworkManager"
        
        # Build connection details
        if hasattr(table, 'database_name') and table.database_name:
            connection_details['database'] = table.database_name
        if hasattr(table, 'server_name') and table.server_name:
            connection_details['server'] = table.server_name
        if hasattr(table, 'schema_name') and table.schema_name:
            connection_details['schema'] = table.schema_name
        if hasattr(table, 'cognos_path') and table.cognos_path:
            connection_details['package_path'] = table.cognos_path
        
        # Add source info to context
        context['source_info'] = {
            'source_type': source_type,
            'connection_details': connection_details
        }
        
        # Extract filters from report spec if available
        if report_spec:
            filters = self._extract_filters_from_report_spec(report_spec, table.name)
            if filters:
                context['report_filters'] = filters
            
            # Extract calculations from report spec if available
            calculations = self._extract_calculations_from_report_spec(report_spec, table.name)
            if calculations:
                context['report_calculations'] = calculations
        
        # Extract relationships if available
        if hasattr(table, 'relationships') and table.relationships:
            context['relationships'] = [{
                'from_table': rel.from_table,
                'from_column': rel.from_column,
                'to_table': rel.to_table,
                'to_column': rel.to_column,
                'join_type': rel.join_type if hasattr(rel, 'join_type') else 'Inner'
            } for rel in table.relationships]
        
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
    
    def _extract_filters_from_report_spec(self, report_spec: str, table_name: str) -> List[Dict[str, Any]]:
        """
        Extract filters from the report specification for a specific table
        
        Args:
            report_spec: Full report specification XML
            table_name: Name of the table to extract filters for
            
        Returns:
            List of filter dictionaries with column_name, operator, and values
        """
        filters = []
        try:
            # Look for filter sections in the report spec
            # This is a simplified implementation that looks for common filter patterns in Cognos XML
            filter_patterns = [
                # Pattern for simple filters
                r'<filter.*?<expression>\s*\[([^\]]+)\]\s*([=<>!]+)\s*([^<]+)</expression>',
                # Pattern for IN filters
                r'<filter.*?<expression>\s*\[([^\]]+)\]\s+in\s+\(([^)]+)\)</expression>',
                # Pattern for BETWEEN filters
                r'<filter.*?<expression>\s*\[([^\]]+)\]\s+between\s+([^\s]+)\s+and\s+([^\s<]+)</expression>'
            ]
            
            # Extract the relevant part of the report spec for this table
            relevant_spec = self._extract_relevant_report_spec(report_spec, table_name)
            
            # Process each filter pattern
            for pattern in filter_patterns:
                matches = re.findall(pattern, relevant_spec, re.IGNORECASE)
                
                for match in matches:
                    if len(match) == 3 and '=' in match[1]:
                        # Simple equality filter
                        filters.append({
                            'column_name': match[0].strip(),
                            'operator': 'equals',
                            'values': [match[2].strip().strip('"\'')] 
                        })
                    elif len(match) == 3 and '>' in match[1]:
                        # Greater than filter
                        filters.append({
                            'column_name': match[0].strip(),
                            'operator': 'greaterThan',
                            'values': [match[2].strip().strip('"\'')] 
                        })
                    elif len(match) == 3 and '<' in match[1]:
                        # Less than filter
                        filters.append({
                            'column_name': match[0].strip(),
                            'operator': 'lessThan',
                            'values': [match[2].strip().strip('"\'')] 
                        })
                    elif len(match) == 2:  # IN filter
                        # Split the values and clean them
                        values = [v.strip().strip('"\'\'') for v in match[1].split(',')]
                        filters.append({
                            'column_name': match[0].strip(),
                            'operator': 'in',
                            'values': values
                        })
                    elif len(match) == 3:  # BETWEEN filter
                        filters.append({
                            'column_name': match[0].strip(),
                            'operator': 'between',
                            'values': [match[1].strip().strip('"\'\''), match[2].strip().strip('"\'\'')]
                        })
            
            return filters
        except Exception as e:
            self.logger.warning(f"Error extracting filters from report spec: {e}")
            return []
    
    def _extract_calculations_from_report_spec(self, report_spec: str, table_name: str) -> List[Dict[str, Any]]:
        """
        Extract calculated columns from the report specification for a specific table
        
        Args:
            report_spec: Full report specification XML
            table_name: Name of the table to extract calculations for
            
        Returns:
            List of calculation dictionaries with new_column_name, source_expression, and description
        """
        calculations = []
        try:
            # Look for calculation sections in the report spec
            # This is a simplified implementation that looks for common calculation patterns in Cognos XML
            calc_patterns = [
                # Pattern for calculated columns
                r'<calculation.*?<name>([^<]+)</name>.*?<expression>([^<]+)</expression>',
                # Pattern for calculated measures
                r'<measure.*?<name>([^<]+)</name>.*?<expression>([^<]+)</expression>'
            ]
            
            # Extract the relevant part of the report spec for this table
            relevant_spec = self._extract_relevant_report_spec(report_spec, table_name)
            
            # Process each calculation pattern
            for pattern in calc_patterns:
                matches = re.findall(pattern, relevant_spec, re.IGNORECASE | re.DOTALL)
                
                for match in matches:
                    if len(match) == 2:
                        # Extract description if available
                        description = None
                        desc_match = re.search(r'<description>([^<]+)</description>', 
                                              relevant_spec, re.IGNORECASE)
                        if desc_match:
                            description = desc_match.group(1).strip()
                        
                        calculations.append({
                            'new_column_name': match[0].strip(),
                            'source_expression': match[1].strip(),
                            'description': description
                        })
            
            return calculations
        except Exception as e:
            self.logger.warning(f"Error extracting calculations from report spec: {e}")
            return []
    
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
