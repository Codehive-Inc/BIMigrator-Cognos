"""
M-Query Converter for converting SQL and other data sources to Power BI M-query format.
Uses LLM service to generate optimized M-queries.
"""
import logging
import re
import json
from typing import Dict, Any, Optional, List
from pathlib import Path

from ..models import Table


class MQueryConverter:
    """Converts data source queries to Power BI M-query format using LLM service"""
    
    def __init__(self, output_path: Optional[str] = None):
        """
        Initialize the M-Query converter with an LLM service client
        
        Args:
            output_path: The root output path for the migration.
        """
        self.output_path = output_path
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
        self.logger.info(f"[MQUERY_TRACKING] Converting source query to M-query for table: {table.name}")
        
        # Build SQL from report queries if report_spec is available
        sql_query = self._build_sql_from_report_queries(table)
        if not sql_query:
            self.logger.warning(f"Could not build SQL for table {table.name}. Falling back to default M-query.")
            return self._build_default_m_query(table)

        self.logger.info(f"Built SQL query for table {table.name}: {sql_query}")
        
        # Generate M-query directly from SQL
        m_query = self._build_m_query_from_sql(sql_query, table)
        
        # Clean and format the M-query
        cleaned_m_query = self._clean_m_query(m_query)
        self.logger.info(f"[MQUERY_TRACKING] Cleaned M-query for table {table.name}: {cleaned_m_query[:200]}...")
        
        return cleaned_m_query

    def _build_m_query_from_sql(self, sql_query: str, table: Table) -> str:
        """
        Builds an M-query from a SQL query.
        
        Args:
            sql_query: The SQL query.
            table: The table object.
            
        Returns:
            The M-query string.
        """
        # A real implementation would require database connection details
        # For now, we'll create a placeholder M-query.
        # Replace this with a call to a real database connector in a production scenario.
        
        # Escape the SQL query for use in the M-query string
        escaped_sql = sql_query.replace('"', '""')
        
        m_query = f"""
let
    Source = Sql.Database("REPLACE_WITH_YOUR_SERVER", "REPLACE_WITH_YOUR_DATABASE"),
    SQL = Value.NativeQuery(Source, "{escaped_sql}", null, [EnableFolding=true])
in
    SQL
"""
        return m_query

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
    
    def _build_sql_from_report_queries(self, table: Table) -> Optional[str]:
        """
        Build a SQL query from the report_queries.json file.

        Args:
            table: Table object

        Returns:
            SQL query string or None if the file doesn't exist or is invalid.
        """
        if not self.output_path:
            self.logger.warning("Output path not set in MQueryConverter. Cannot find report_queries.json.")
            return None

        report_queries_path = Path(self.output_path) / "extracted" / "report_queries.json"

        if not report_queries_path.exists():
            self.logger.warning(f"report_queries.json not found at {report_queries_path}")
            return None

        try:
            with open(report_queries_path, 'r') as f:
                queries = json.load(f)
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in {report_queries_path}")
            return None

        query_spec = next((q for q in queries if q['name'] == table.name), None)

        if not query_spec:
            self.logger.warning(f"No query specification found for table {table.name} in {report_queries_path}")
            return None

        select_clauses = []
        from_clauses = set()
        where_clauses = []

        for item in query_spec['data_items']:
            expression = item['expression']
            # Regex to find all occurrences of [schema].[table].[column]
            matches = re.findall(r'\[(.*?)\]\.\[(.*?)\]\.\[(.*?)\]', expression)
            
            for match in matches:
                schema, table_name, column = match
                from_clauses.add(f'"{schema}"."{table_name}"')

            # Replace the Cognos-style references with SQL-style references
            sql_expression = re.sub(r'\[(.*?)\]\.\[(.*?)\]\.\[(.*?)\]', r'"\2"."\3"', expression)
            select_clauses.append(f'    {sql_expression} AS "{item["name"]}"')
        
        if 'filters' in query_spec:
            for f in query_spec['filters']:
                # Also transform expression in filters
                sql_filter_expression = re.sub(r'\[(.*?)\]\.\[(.*?)\]\.\[(.*?)\]', r'"\2"."\3"', f["expression"])
                where_clauses.append(f'    {sql_filter_expression}')

        if not select_clauses:
            return None
            
        sql = "SELECT\n"
        sql += ",\n".join(select_clauses)
        sql += "\nFROM\n"
        sql += ", ".join(sorted(list(from_clauses))) # Sort for consistency
        
        if where_clauses:
            sql += "\nWHERE\n"
            sql += "\n    AND ".join(where_clauses)
            
        return sql
    
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
