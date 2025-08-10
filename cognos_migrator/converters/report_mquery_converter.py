"""
Report-specific M-Query Converter for converting Cognos report queries to Power BI M-query format.
"""
import json
import re
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
        
        # Build SQL from report queries if report_spec is available
        sql_query = self._build_sql_from_report_queries(table)
        if not sql_query:
            self.logger.warning(f"Could not build SQL for report table {table.name}. Falling back to default M-query.")
            return self._build_default_m_query(table)

        self.logger.info(f"Built SQL query for report table {table.name}: {sql_query}")
        
        # Generate M-query directly from SQL
        m_query = self._build_m_query_from_sql(sql_query, table)
        
        # Clean and format the M-query
        cleaned_m_query = self._clean_m_query(m_query)
        self.logger.info(f"[MQUERY_TRACKING] Cleaned M-query for report table {table.name}: {cleaned_m_query[:200]}...")
        
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
