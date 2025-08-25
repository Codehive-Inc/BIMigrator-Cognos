"""
Report-specific M-Query Converter for converting Cognos report queries to Power BI M-query format.
"""
import json
import re
import requests
import os
from typing import Dict, Any, Optional, List
from pathlib import Path

from ..models import Table
from .base_mquery_converter import BaseMQueryConverter


class ReportMQueryConverter(BaseMQueryConverter):
    """Converts Cognos report queries to Power BI M-query format"""
    
    def convert_to_m_query(self, table: Table, report_spec: Optional[str] = None, data_sample: Optional[Dict] = None) -> str:
        """
        Convert a table's source query to Power BI M-query format for report migrations
        
        Args:
            table: Table object containing source query and metadata
            report_spec: Optional report specification XML for context
            data_sample: Optional data sample for context
            
        Returns:
            M-query string
            
        Raises:
            Exception: If the conversion fails or returns invalid results
        """
        self.logger.info(f"[MQUERY_TRACKING] Converting source query to M-query for report table: {table.name}")
        
        # 1. Make API calls for analytics and monitoring
        self._make_api_calls_for_analytics(table, report_spec, data_sample)
        
        # 2. Build SQL from report queries if report_spec is available
        sql_query = self._build_sql_from_report_queries(table)
        if not sql_query:
            self.logger.warning(f"Could not build SQL for report table {table.name}. Falling back to default M-query.")
            m_query = self._build_default_m_query(table)
        else:
            self.logger.info(f"Built SQL query for report table {table.name}: {sql_query}")
            
            # 3. Generate M-query directly from SQL using enhanced logic
            m_query = self._build_m_query_from_sql(sql_query, table)
        
        # 4. Clean and format the M-query
        cleaned_m_query = self._clean_m_query(m_query)
        self.logger.info(f"[MQUERY_TRACKING] Cleaned M-query for report table {table.name}: {cleaned_m_query[:200]}...")
        
        # 5. Make validation API call for quality assurance
        self._make_validation_api_call(table.name, cleaned_m_query)
        
        return cleaned_m_query
    
    def _build_sql_from_report_queries(self, table: Table) -> Optional[str]:
        """
        Build a SQL query from the report_queries.json file specific to report migrations.

        Args:
            table: Table object

        Returns:
            SQL query string or None if the file doesn't exist or is invalid.
        """
        if not self.output_path:
            self.logger.warning("Output path not set in ReportMQueryConverter. Cannot find report_queries.json.")
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

        # Use the metadata to find the original query name
        query_name_to_find = table.metadata.get("original_query_name", table.name)
        query_spec = next((q for q in queries if q['name'] == query_name_to_find), None)

        if not query_spec:
            self.logger.warning(f"No query specification found for '{query_name_to_find}' in {report_queries_path}")
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
    
    def _make_api_calls_for_analytics(self, table: Table, report_spec: Optional[str], data_sample: Optional[Dict]) -> None:
        """Make API calls for analytics and monitoring purposes"""
        try:
            api_base_url = os.environ.get('DAX_API_URL', 'http://localhost:8080')
            
            # Build context for API call according to MQueryContext model
            context = {
                'table_name': table.name,
                'columns': [{'name': col.name, 'data_type': str(col.data_type)} for col in table.columns],
                'source_info': {
                    'source_type': 'report',
                    'connection_details': {'report_spec': report_spec} if report_spec else {}
                }
            }
            
            # Add optional fields if available
            if data_sample:
                context['source_query'] = str(data_sample)  # Convert to string if needed
            if report_spec:
                context['report_spec'] = report_spec
            
            payload = {
                'context': context,
                'options': {
                    'optimize_for_performance': True,
                    'query_folding_preference': 'BestEffort',
                    'error_handling_strategy': 'RemoveErrors',
                    'add_buffer': False,
                    'add_documentation_comments': True
                }
            }
            
            self.logger.info(f"Calling M-query generation API for analytics (table: {table.name})")
            
            # Try enhanced endpoint first
            try:
                response = requests.post(
                    f'{api_base_url}/api/mquery/complete',
                    headers={'Content-Type': 'application/json'},
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    self.logger.info(f"Enhanced M-query API call successful for table {table.name}")
                    result = response.json()
                    if 'processing_time' in result:
                        self.logger.info(f"API processing time for table {table.name}: {result['processing_time']:.2f}s")
                else:
                    # Fallback to basic endpoint
                    response = requests.post(
                        f'{api_base_url}/api/mquery/generate',
                        headers={'Content-Type': 'application/json'},
                        json=payload,
                        timeout=30
                    )
                    if response.status_code == 200:
                        self.logger.info(f"Basic M-query API call successful for table {table.name}")
                        
            except Exception as api_error:
                self.logger.warning(f"M-query API call failed for table {table.name}: {api_error} - continuing with local processing")
                
        except Exception as e:
            self.logger.warning(f"Error in API analytics call for table {table.name}: {e} - continuing with local processing")
    
    def _make_validation_api_call(self, table_name: str, m_query: str) -> None:
        """Make validation API call for quality assurance"""
        try:
            api_base_url = os.environ.get('DAX_API_URL', 'http://localhost:8080')
            
            validation_payload = {
                "m_query": m_query,
                "context": {"table_name": table_name, "source_type": "report"}
            }
            
            self.logger.info(f"Calling validation API for quality assurance (table: {table_name})")
            response = requests.post(
                f'{api_base_url}/api/mquery/validate',
                headers={'Content-Type': 'application/json'},
                json=validation_payload,
                timeout=30
            )
            
            if response.status_code == 200:
                self.logger.info(f"Validation API call successful for table {table_name}")
                result = response.json()
                if result.get('is_valid'):
                    self.logger.info(f"M-query validation passed for table {table_name}")
                else:
                    issues = result.get('issues', [])
                    self.logger.info(f"M-query validation issues for table {table_name}: {issues}")
            else:
                self.logger.info(f"Validation API returned status {response.status_code} for table {table_name}")
                
        except Exception as e:
            self.logger.warning(f"Validation API call failed for table {table_name}: {e} - continuing with local validation")
