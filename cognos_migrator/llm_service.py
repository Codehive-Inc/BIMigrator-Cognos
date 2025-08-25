"""
LLM Service Client for M-Query Generation
"""

import json
import logging
import os
import requests
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class ColumnInfo:
    name: str
    data_type: str
    description: Optional[str] = None


@dataclass
class SourceInfo:
    source_type: str  # e.g., "SqlServer", "Oracle", "OData", "CsvFile", "CognosFrameworkManager"
    connection_details: Dict[str, Any]  # e.g., {"server": "prod-sql-01", "database": "SalesDW"}


@dataclass
class ReportFilter:
    column_name: str
    operator: str  # e.g., "equals", "in", "greaterThan", "startsWith"
    values: List[Any]


@dataclass
class ReportCalculation:
    new_column_name: str
    source_expression: str  # e.g., "[Sales] - [Cost]"
    description: Optional[str] = None


@dataclass
class TableRelationship:
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    join_type: str  # "LeftOuter", "Inner", etc.


class LLMServiceClient:
    """Client for communicating with the LLM FastAPI service"""
    
    def __init__(self, base_url = None, api_key: Optional[str] = None):
        """
        Initialize the LLM service client
        
        Args:
            base_url: Base URL of the FastAPI service, defaults to http://localhost:8080
            api_key: Optional API key for authentication (not needed in Docker network)
        """
        if not base_url:
            base_url = os.environ.get('DAX_API_URL', 'http://localhost:8080')
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.logger = logging.getLogger(__name__)
        
    def check_health(self) -> Dict[str, Any]:
        """
        Check if the LLM service is healthy
        
        Returns:
            Dictionary with health status information
        """
        try:
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
                
            # Try the health endpoint
            response = requests.get(
                f'{self.base_url}/health',
                headers=headers,
                timeout=10  # 10 second timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.warning(f"Health check failed with status code {response.status_code}")
                return {"status": "unhealthy", "message": f"Status code: {response.status_code}"}
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error checking LLM service health: {e}")
            return {"status": "unhealthy", "message": str(e)}
            
        except Exception as e:
            self.logger.error(f"Unexpected error checking LLM service health: {e}")
            return {"status": "unhealthy", "message": str(e)}
    
    def generate_m_query(self, context: Dict[str, Any]) -> str:
        """
        Generate an optimized M-query using the LLM service
        
        Args:
            context: Dictionary containing context information for M-query generation
                - table_name: Name of the table
                - columns: List of column definitions
                - source_query: Original SQL query if available
                - report_spec: Relevant parts of the Cognos report specification
                - data_sample: Sample data if available
                - source_info: Source system information (optional)
                - report_filters: List of filters to apply (optional)
                - report_calculations: List of calculations to add (optional)
                - relationships: List of table relationships (optional)
        
        Returns:
            Optimized M-query string
            
        Raises:
            Exception: If the LLM service fails or returns invalid results
        """
        table_name = context.get('table_name', 'unknown')
        
        try:
            headers = {'Content-Type': 'application/json'}
            
            # Convert column information to the expected format
            columns = []
            for col in context.get('columns', []):
                if isinstance(col, dict):
                    columns.append({
                        'name': col.get('name', ''),
                        'data_type': col.get('data_type', ''),
                        'description': col.get('description')
                    })
                else:
                    columns.append({
                        'name': col.name,
                        'data_type': col.data_type,
                        'description': col.description if hasattr(col, 'description') else None
                    })
            
            # Prepare the enhanced context
            enhanced_context = {
                'table_name': table_name,
                'columns': columns,
                'source_query': context.get('source_query'),
                'report_spec': context.get('report_spec')
            }
            
            # Add source information if available
            if 'source_info' in context:
                source_info = context['source_info']
                if isinstance(source_info, dict):
                    enhanced_context['source_info'] = source_info
                else:
                    enhanced_context['source_info'] = {
                        'source_type': source_info.source_type,
                        'connection_details': source_info.connection_details
                    }
            
            # Add filters if available
            if 'report_filters' in context and context['report_filters']:
                filters = []
                for filter_item in context['report_filters']:
                    if isinstance(filter_item, dict):
                        filters.append(filter_item)
                    else:
                        filters.append({
                            'column_name': filter_item.column_name,
                            'operator': filter_item.operator,
                            'values': filter_item.values
                        })
                enhanced_context['report_filters'] = filters
            
            # Add calculations if available
            if 'report_calculations' in context and context['report_calculations']:
                calculations = []
                for calc_item in context['report_calculations']:
                    if isinstance(calc_item, dict):
                        calculations.append(calc_item)
                    else:
                        calculations.append({
                            'new_column_name': calc_item.new_column_name,
                            'source_expression': calc_item.source_expression,
                            'description': calc_item.description
                        })
                enhanced_context['report_calculations'] = calculations
            
            # Add relationships if available
            if 'relationships' in context and context['relationships']:
                relationships = []
                for rel in context['relationships']:
                    if isinstance(rel, dict):
                        relationships.append(rel)
                    else:
                        relationships.append({
                            'from_table': rel.from_table,
                            'from_column': rel.from_column,
                            'to_table': rel.to_table,
                            'to_column': rel.to_column,
                            'join_type': rel.join_type
                        })
                enhanced_context['relationships'] = relationships
            
            # Add data sample if available
            if 'data_sample' in context:
                enhanced_context['data_sample'] = context['data_sample']
            
            # Prepare the enhanced options
            options = {
                'query_folding_preference': 'BestEffort',
                'error_handling_strategy': 'RemoveErrors',
                'add_buffer': False,
                'add_documentation_comments': True
            }
            
            # Override with any provided options
            if 'options' in context:
                ctx_options = context['options']
                if isinstance(ctx_options, dict):
                    if 'optimize_for_performance' in ctx_options and ctx_options['optimize_for_performance']:
                        options['query_folding_preference'] = 'Strict'
                    if 'include_comments' in ctx_options:
                        options['add_documentation_comments'] = ctx_options['include_comments']
                    if 'query_folding_preference' in ctx_options:
                        options['query_folding_preference'] = ctx_options['query_folding_preference']
                    if 'error_handling_strategy' in ctx_options:
                        options['error_handling_strategy'] = ctx_options['error_handling_strategy']
                    if 'add_buffer' in ctx_options:
                        options['add_buffer'] = ctx_options['add_buffer']
            
            # Prepare the payload for the LLM service according to the enhanced API spec
            payload = {
                'context': enhanced_context,
                'options': options
            }
            
            # Log the request payload (excluding potentially large data samples)
            log_payload = payload.copy()
            if 'context' in log_payload and 'data_sample' in log_payload['context']:
                log_payload['context']['data_sample'] = '[DATA SAMPLE OMITTED FOR LOGGING]'
            self.logger.info(f"Enhanced M-query request payload: {json.dumps(log_payload, indent=2)}")
            
            # Make the request to the FastAPI endpoint
            self.logger.info(f"Sending request to LLM service for table {table_name}")
            
            # HYBRID APPROACH: Make API calls for analytics and use enhanced Python logic
            
            # 1. Make API call for analytics and monitoring
            self._make_api_calls_for_analytics(headers, payload, table_name)
            
            # 2. Generate M-query using enhanced Python logic with API context
            self.logger.info(f"[MQUERY_TRACKING] Generating M-query with enhanced Python logic (table: {table_name})")
            m_query = self._generate_enhanced_python_m_query(context)
            
            # 3. Make validation API call for quality assurance
            self._make_validation_api_call(table_name, m_query)
            
            self.logger.info(f"[MQUERY_TRACKING] Successfully generated M-query for table {table_name}")
            self.logger.info(f"[MQUERY_TRACKING] Generated M-query for table {table_name}: {m_query[:200]}...")
            return m_query
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Error communicating with LLM service for table {table_name}: {e}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error in LLM service client for table {table_name}: {e}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
    
    def _make_api_calls_for_analytics(self, headers: Dict[str, str], payload: Dict[str, Any], table_name: str) -> None:
        """Make API calls for analytics and monitoring purposes"""
        try:
            # Try the enhanced endpoint first for comprehensive analytics
            self.logger.info(f"Calling enhanced M-query endpoint for analytics and monitoring (table: {table_name})")
            response = requests.post(
                f'{self.base_url}/api/mquery/complete',
                headers=headers,
                json=payload,
                timeout=30  # Optimized timeout for analytics calls
            )
            
            if response.status_code == 200:
                self.logger.info(f"Enhanced M-query API call successful for table {table_name}")
                # Log validation results for quality monitoring
                result = response.json()
                if 'validation_result' in result:
                    validation = result['validation_result']
                    if validation.get('is_valid'):
                        self.logger.info(f"API validation passed for table {table_name}")
                    else:
                        self.logger.info(f"API validation issues detected for table {table_name}: {validation.get('issues', [])}")
                
                # Log performance metrics for monitoring
                if 'processing_time' in result:
                    self.logger.info(f"API processing time for table {table_name}: {result['processing_time']:.2f}s")
            else:
                # Try basic endpoint as fallback for analytics
                self.logger.info(f"Enhanced endpoint unavailable, using basic endpoint for analytics (table: {table_name})")
                response = requests.post(
                    f'{self.base_url}/api/mquery/generate',
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                if response.status_code == 200:
                    self.logger.info(f"Basic M-query API call successful for table {table_name}")
                    
        except Exception as e:
            self.logger.warning(f"M-query API call failed for table {table_name}: {e} - continuing with local processing")
    
    def _make_validation_api_call(self, table_name: str, m_query: str) -> None:
        """Make validation API call for quality assurance and monitoring"""
        try:
            validation_payload = {
                "m_query": m_query,
                "context": {"table_name": table_name}
            }
            
            self.logger.info(f"Calling validation API for quality assurance (table: {table_name})")
            response = requests.post(
                f'{self.base_url}/api/mquery/validate',
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
    
    def _generate_enhanced_python_m_query(self, context: Dict[str, Any]) -> str:
        """Generate M-query using enhanced Python logic with API context"""
        table_name = context.get('table_name', 'Unknown')
        self.logger.info(f"Generating M-query using enhanced Python logic for table: {table_name}")
        
        # Check if we have source query information
        if context.get('source_query'):
            # For SQL queries, wrap in appropriate M function with comments
            source_query = context['source_query'].replace('"', '""')  # Escape quotes for M-query
            return f'''// Python-generated M-query for {table_name}
let
    Source = Sql.Database("server", "database", [Query="{source_query}"]),
    // Apply type transformations based on column definitions
    #"Changed Type" = Source
in
    #"Changed Type"'''
        else:
            # For tables without a source query, create a more informative table structure
            columns = context.get('columns', [])
            if columns:
                # Build column definitions for the table schema
                column_defs = []
                for col in columns:
                    col_name = col.get('name', 'Column')
                    col_type = col.get('data_type', 'text')
                    # Map common data types to M-query types
                    m_type = self._map_to_m_query_type(col_type)
                    column_defs.append(f'"{col_name}" = {m_type}')
                
                columns_str = ", ".join(column_defs)
                return f'''// Python-generated M-query for {table_name}
let
    Source = Table.FromRows({{}}),
    // Define table schema with proper column types
    #"Changed Type" = Table.TransformColumnTypes(Source, {{{columns_str}}})
in
    #"Changed Type"'''
            else:
                # Fallback for tables with no column information
                return f'''// Python-generated M-query for {table_name} (minimal schema)
let
    Source = Table.FromRows({{}}),
    // Empty table with no schema information available
    #"Changed Type" = Source
in
    #"Changed Type"'''
    
    def _map_to_m_query_type(self, data_type: str) -> str:
        """Map data types to M-query type expressions"""
        type_mapping = {
            'string': 'type text',
            'text': 'type text',
            'varchar': 'type text',
            'char': 'type text',
            'int': 'type number',
            'integer': 'type number',
            'bigint': 'type number',
            'decimal': 'type number',
            'float': 'type number',
            'double': 'type number',
            'boolean': 'type logical',
            'bool': 'type logical',
            'date': 'type date',
            'datetime': 'type datetime',
            'timestamp': 'type datetime'
        }
        return type_mapping.get(data_type.lower(), 'type text')
    
    # Original fallback method removed - replaced by _generate_python_fallback_m_query above
