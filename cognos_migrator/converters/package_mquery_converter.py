"""
Package-specific M-Query Converter for converting Cognos package queries to Power BI M-query format.
"""
import json
import re
from typing import Dict, Any, Optional, List
from pathlib import Path

from ..models import Table
from .base_mquery_converter import BaseMQueryConverter


class PackageMQueryConverter(BaseMQueryConverter):
    """Converts Cognos package queries to Power BI M-query format"""
    
    def convert_to_m_query(self, table: Table, package_spec: Optional[str] = None, data_sample: Optional[Dict] = None) -> str:
        """
        Convert a table's source query to Power BI M-query format for package migrations
        
        Args:
            table: Table object containing source query and metadata
            package_spec: Optional package specification for context
            data_sample: Optional data sample for context
            
        Returns:
            M-query string
            
        Raises:
            Exception: If the conversion fails or returns invalid results
        """
        self.logger.info(f"[MQUERY_TRACKING] Converting source query to M-query for package table: {table.name}")
        
        # For packages, we first try to use the source_query directly if available
        if hasattr(table, 'source_query') and table.source_query:
            self.logger.info(f"Using direct source query for package table {table.name}")
            sql_query = table.source_query
        else:
            # Otherwise, try to build SQL from package metadata
            sql_query = self._build_sql_from_package_metadata(table)
            
        if not sql_query:
            self.logger.warning(f"Could not build SQL for package table {table.name}. Falling back to default M-query.")
            return self._build_default_m_query(table)

        self.logger.info(f"Built SQL query for package table {table.name}: {sql_query}")
        
        # Generate M-query directly from SQL
        m_query = self._build_m_query_from_sql(sql_query, table)
        
        # Clean and format the M-query
        cleaned_m_query = self._clean_m_query(m_query)
        self.logger.info(f"[MQUERY_TRACKING] Cleaned M-query for package table {table.name}: {cleaned_m_query[:200]}...")
        
        return cleaned_m_query
    
    def _build_sql_from_package_metadata(self, table: Table) -> Optional[str]:
        """
        Build a SQL query from package metadata files specific to package migrations.

        Args:
            table: Table object

        Returns:
            SQL query string or None if metadata is not available or invalid.
        """
        if not self.output_path:
            self.logger.warning("Output path not set in PackageMQueryConverter. Cannot find package metadata.")
            return None

        # For packages, we look for query_subjects.json and query_items.json in the extracted directory
        extracted_dir = Path(self.output_path) / "extracted"
        query_subjects_path = extracted_dir / "query_subjects.json"
        query_items_path = extracted_dir / "query_items.json"

        if not query_subjects_path.exists() or not query_items_path.exists():
            self.logger.warning(f"Package metadata files not found at {extracted_dir}")
            return None

        try:
            # Load query subjects
            with open(query_subjects_path, 'r') as f:
                query_subjects = json.load(f)
                
            # Load query items
            with open(query_items_path, 'r') as f:
                query_items = json.load(f)
                
            # Find the query subject that matches this table
            subject = next((s for s in query_subjects if s['name'] == table.name), None)
            if not subject:
                self.logger.warning(f"No query subject found for table {table.name}")
                return None
                
            # Get the items for this subject
            subject_id = subject.get('id')
            if not subject_id:
                self.logger.warning(f"Query subject {table.name} has no ID")
                return None
                
            # Find items belonging to this subject
            items = [item for item in query_items.get(subject_id, [])]
            if not items:
                self.logger.warning(f"No query items found for subject {table.name}")
                return None
                
            # Build SQL query from subject and items
            select_clauses = []
            
            # Use the subject's table name for FROM clause
            table_name = subject.get('table_name', table.name)
            schema_name = subject.get('schema_name', 'dbo')
            
            # Add each item as a column in the SELECT clause
            for item in items:
                item_name = item.get('name')
                column_name = item.get('column_name', item_name)
                
                if item_name and column_name:
                    select_clauses.append(f'    "{column_name}" AS "{item_name}"')
            
            if not select_clauses:
                self.logger.warning(f"No columns found for table {table.name}")
                return None
                
            # Build the SQL query
            sql = "SELECT\n"
            sql += ",\n".join(select_clauses)
            sql += f"\nFROM\n    \"{schema_name}\".\"{table_name}\""
            
            return sql
            
        except Exception as e:
            self.logger.error(f"Error building SQL from package metadata: {e}")
            return None
