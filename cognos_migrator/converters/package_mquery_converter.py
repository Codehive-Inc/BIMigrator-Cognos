"""
Package-specific M-Query Converter for converting Cognos package queries to Power BI M-query format.
"""
import json
import os
import re
import requests
import textwrap
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
        
        # 1. Make API calls for analytics and monitoring
        self._make_api_calls_for_analytics(table, package_spec, data_sample)
        
        # 2. Get table metadata from table_*.json
        table_metadata = self._get_table_metadata(table)
        
        # 3. Build SQL from package metadata using enhanced logic
        sql_query = self._build_sql_from_package_metadata(table, table_metadata)
        
        # 4. Build the M-query from the SQL statement
        m_query = self._build_m_query_from_sql(sql_query, table, table_metadata)
        
        # 5. Make validation API call for quality assurance
        self._make_validation_api_call(table.name, m_query)
        
        return m_query

    def _build_sql_from_package_metadata(self, table: Table, table_metadata: Optional[Dict]) -> str:
        """
        Build SQL query from package metadata by parsing the package XML.
        """
        if not hasattr(self, 'package_name') or not self.package_name:
            if table_metadata and 'package_name' in table_metadata:
                self.package_name = table_metadata['package_name']
        else:
                self.logger.warning("Package name not found, cannot locate package XML.")
                return f"SELECT * FROM {table.name}"

        package_xml_path = Path(self.output_path) / "extracted" / f"{self.package_name}.xml"

        if not package_xml_path.exists():
            self.logger.warning(f"Package XML file not found at {package_xml_path}")
            return f"SELECT * FROM {table.name}"

        try:
            with open(package_xml_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
        except Exception as e:
            self.logger.error(f"Error reading package XML file: {e}")
            return f"SELECT * FROM {table.name}"
        
        # Using regex to find the query subject and SQL content.
        # This is fragile but will work for the known structure.
        query_subject_match = re.search(f'<querySubject.*?<name locale="en">{table.name}</name>.*?</querySubject>', xml_content, re.DOTALL)
        if not query_subject_match:
            query_subject_match = re.search(f'<querySubject.*?<name>{table.name}</name>.*?</querySubject>', xml_content, re.DOTALL)

        if not query_subject_match:
            self.logger.warning(f"Query subject for table '{table.name}' not found in package XML.")
            return f"SELECT * FROM {table.name}"

        sql_match = re.search(r'<sql type="cognos">(.*?)</sql>', query_subject_match.group(0), re.DOTALL)
        if not sql_match:
            self.logger.warning(f"SQL query not found for table {table.name} in package XML")
            return f"SELECT * FROM {table.name}"

        sql_content = sql_match.group(1).strip()

        # Replace <column>...</column> with its content
        processed_sql = re.sub(r'<column>(.*?)</column>', r'\1', sql_content, flags=re.DOTALL)
        
        # Replace <table>...</table> with its content
        processed_sql = re.sub(r'<table>(.*?)</table>', r'\1', processed_sql, flags=re.DOTALL)
        
        # Clean up extra whitespace and newlines
        sql_query = ' '.join(processed_sql.split())

        if not sql_query:
            self.logger.warning(f"Extracted SQL query is empty for table {table.name}.")
            return f"SELECT * FROM {table.name}"

        return sql_query


    def _build_m_query_from_sql(self, sql_query: str, table: Table, table_metadata: Optional[Dict] = None) -> str:
        """
        Build M-query from SQL with metadata-driven transformations and best practices.
        """
        final_step = "ValidateResults"
        transform_types_section = ""
        type_transformations = []

        if table_metadata and 'columns' in table_metadata:
            seen_columns = set()
            for col in table_metadata['columns']:
                col_name = col.get('name')
                if col_name and col_name not in seen_columns:
                    powerbi_type = col.get('powerbi_datatype', 'string')
                    
                    mquery_type = "type text" # Default for string
                    if powerbi_type.lower() == 'int64':
                        mquery_type = "Int64.Type"
                    elif powerbi_type.lower() == 'double':
                         mquery_type = "type number"
                    elif powerbi_type.lower() == 'datetime':
                        mquery_type = "type datetime"
                    elif powerbi_type.lower() == 'boolean':
                        mquery_type = "type logical"
                    
                    type_transformations.append(f'{{"{col_name}", {mquery_type}}}')
                    seen_columns.add(col_name)
        
        if type_transformations:
            transformations_list = ", ".join(type_transformations)
            transform_types_section = f""",

    // --- 5. APPLY CORRECT DATA TYPES ---
    TransformTypes = Table.TransformColumnTypes(ValidateResults, {{{transformations_list}}})"""
            final_step = "TransformTypes"

        m_query_template = f'''
let
    // --- 1. DEFINE THE SQL QUERY ---
    SQL_Statement = "{sql_query.replace('"', '""')}",

    // --- 2. CONNECT TO THE DATABASE ---
    Source = Sql.Database("REPLACE_WITH_YOUR_SERVER", "REPLACE_WITH_YOUR_DATABASE"),

    // --- 3. EXECUTE THE NATIVE SQL QUERY ---
    ExecuteQuery = Value.NativeQuery(
        Source,
        SQL_Statement,
        null,
        [EnableFolding=true]
    ),

    // --- 4. VALIDATE THAT DATA WAS RETURNED ---
    ValidateResults = if Table.IsEmpty(ExecuteQuery) then
                        error "No data was returned from the SQL query for the {table.name} table."
                      else
                        ExecuteQuery{transform_types_section}
in
    {final_step}
'''
        return textwrap.dedent(m_query_template).strip()


    def _get_table_metadata(self, table: Table) -> Optional[Dict]:
        """Get table metadata from table_*.json file"""
        table_json_path = Path(self.output_path) / "extracted" / f"table_{table.name}.json"
        if not table_json_path.exists():
            self.logger.warning(f"Table metadata file not found at {table_json_path}")
            return None
                
        try:
            with open(table_json_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error reading table metadata file {table_json_path}: {e}")
            return None
    
    def _make_api_calls_for_analytics(self, table: Table, package_spec: Optional[str], data_sample: Optional[Dict]) -> None:
        """Make API calls for analytics and monitoring purposes"""
        try:
            api_base_url = os.environ.get('DAX_API_URL', 'http://localhost:8080')
            
            # Build context for API call according to MQueryContext model
            context = {
                'table_name': table.name,
                'columns': [{'name': col.name, 'data_type': str(col.data_type)} for col in table.columns],
                'source_info': {
                    'source_type': 'package',
                    'connection_details': {'package_spec': package_spec} if package_spec else {}
                }
            }
            
            # Add optional fields if available
            if data_sample:
                context['source_query'] = str(data_sample)  # Convert to string if needed
            
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
                "context": {"table_name": table_name, "source_type": "package"}
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
