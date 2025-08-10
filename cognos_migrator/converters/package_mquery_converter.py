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
        
        # Get column metadata from query_subjects.json
        column_metadata = self._get_column_metadata(table)
        
        # Generate M-query with metadata-driven transformations
        m_query = self._build_m_query_from_sql(sql_query, table, column_metadata)
        
        # Clean and format the M-query
        cleaned_m_query = self._clean_m_query(m_query)
        self.logger.info(f"[MQUERY_TRACKING] Cleaned M-query for package table {table.name}: {cleaned_m_query[:200]}...")
        
        return cleaned_m_query

    def _get_column_metadata(self, table: Table) -> Optional[List[Dict]]:
        """
        Get column metadata from query_subjects.json for the given table
        
        Args:
            table: Table object
            
        Returns:
            List of column metadata dictionaries or None if not found
        """
        if not self.output_path:
            return None
            
        query_subjects_path = Path(self.output_path) / "extracted" / "query_subjects.json"
        if not query_subjects_path.exists():
            return None
            
        try:
            with open(query_subjects_path, 'r') as f:
                query_subjects = json.load(f)
                
            # Find the subject that matches this table
            subject = next((s for s in query_subjects if s['name'] == table.name), None)
            if not subject:
                return None
                
            return subject.get('items', [])
            
        except Exception as e:
            self.logger.error(f"Error reading query_subjects.json: {e}")
            return None

    def _build_m_query_from_sql(self, sql_query: str, table: Table, column_metadata: Optional[List[Dict]] = None) -> str:
        """
        Build M-query from SQL with metadata-driven transformations
        
        Args:
            sql_query: SQL query string
            table: Table object
            column_metadata: Optional list of column metadata from query_subjects.json
            
        Returns:
            M-query string with proper transformations
        """
        # Basic template with error handling and transformations
        template = """
            let
                Source = Sql.Database(#"DB Server", #"DB Name"),
                
                // Validate connection
                ValidateConnection = try Source otherwise error 
                    "Failed to connect to database. Error: " & Text.From([Error][Message]),
                    
                // Execute query with folding
                ExecuteQuery = Value.NativeQuery(
                    ValidateConnection, 
                    "{sql}",
                    null,
                    [EnableFolding=true]
                ),
                
                // Validate results
                ValidateResults = if Table.IsEmpty(ExecuteQuery) then
                    error "No data returned from query for table {table}"
                else
                    ExecuteQuery{type_transformations}{null_handling}
            in
                {final_step}
        """
        
        # Build type transformations if we have metadata
        type_transforms = []
        if column_metadata:
            for col in column_metadata:
                col_name = col.get('name')
                powerbi_type = col.get('powerbi_datatype', 'String')
                if col_name:
                    type_transforms.append(f'{{"${col_name}", type {powerbi_type.lower()}}}')
                    
        type_transformation_step = """
                ,
                // Apply data type transformations
                TransformTypes = Table.TransformColumnTypes(
                    ValidateResults,
                    {
                        %s
                    }
                )""" % ",\n                        ".join(type_transforms) if type_transforms else ""
                
        # Add null handling if we have metadata
        has_nullables = any(col.get('nullable', False) for col in (column_metadata or []))
        null_handling_step = """
                ,
                // Handle nulls appropriately
                HandleNulls = Table.ReplaceValue(
                    TransformTypes,
                    null,
                    "",
                    Replacer.ReplaceValue,
                    Table.ColumnNames(TransformTypes)
                )""" if has_nullables and type_transforms else ""
                
        # Determine final step name
        final_step = "HandleNulls" if has_nullables and type_transforms else \
                    "TransformTypes" if type_transforms else \
                    "ValidateResults"
        
        # Format template with query and table name
        m_query = template.format(
            sql=sql_query.replace('"', '""'),  # Escape quotes for M-query
            table=table.name,
            type_transformations=type_transformation_step,
            null_handling=null_handling_step,
            final_step=final_step
        )
        
        # Clean up formatting
        m_query = re.sub(r'\n\s+', '\n', m_query.strip())
        
        return m_query

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
            
        # Get column metadata
        column_metadata = self._get_column_metadata(table)
        if not column_metadata:
            self.logger.warning(f"No column metadata found for table {table.name}")
            return None
            
        # Build SQL query from metadata
        select_clauses = []
        for col in column_metadata:
            col_name = col.get('name')
            if col_name:
                select_clauses.append(f'"{col_name}"')
                
        if not select_clauses:
            self.logger.warning(f"No columns found for table {table.name}")
            return None
            
        # Build the SQL query
        sql = "SELECT\n    "
        sql += ",\n    ".join(select_clauses)
        sql += f"\nFROM\n    {table.name}"
        
        return sql
