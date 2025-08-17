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
            
            # Try the enhanced endpoint first
            try:
                response = requests.post(
                    f'{self.base_url}/api/m-query/enhanced',
                    headers=headers,
                    json=payload,
                    timeout=180  # 180 second timeout for enhanced endpoint
                )
                response.raise_for_status()
                result = response.json()
                
                # Log validation results if available
                if 'validation_result' in result:
                    validation = result['validation_result']
                    if validation['is_valid']:
                        self.logger.info(f"M-query validation passed for table {table_name}")
                    else:
                        self.logger.warning(f"M-query validation failed for table {table_name}: {validation['issues']}")
                
                # Log explanation if available
                if 'explanation' in result and result['explanation']:
                    self.logger.info(f"M-query explanation: {result['explanation'][:200]}...")
                
            except (requests.exceptions.RequestException, KeyError):
                # Fall back to the basic endpoint if enhanced fails
                self.logger.warning(f"Enhanced M-query endpoint failed, falling back to basic endpoint for table {table_name}")
                response = requests.post(
                    f'{self.base_url}/api/m-query',
                    headers=headers,
                    json=payload,
                    timeout=120  # 120 second timeout for basic endpoint
                )
                response.raise_for_status()
                result = response.json()
            
            # Log the complete API response structure (excluding potentially large fields)
            log_result = result.copy()
            if 'explanation' in log_result and log_result['explanation'] and len(log_result['explanation']) > 200:
                log_result['explanation'] = log_result['explanation'][:200] + '...'
            self.logger.info(f"Complete API response: {json.dumps(log_result, indent=2)}")
            
            if 'm_query' in result:
                self.logger.info(f"[MQUERY_TRACKING] Successfully generated M-query for table {table_name}")
                # Log the actual M-query content
                self.logger.info(f"[MQUERY_TRACKING] LLM service generated M-query for table {table_name}: {result['m_query'][:200]}...")
                # Log performance notes if available
                if 'performance_notes' in result and result['performance_notes']:
                    self.logger.info(f"[MQUERY_TRACKING] Performance notes: {result['performance_notes']}")
                # Log confidence score
                if 'confidence' in result:
                    self.logger.info(f"[MQUERY_TRACKING] Confidence score: {result['confidence']}")
                return result['m_query']
            else:
                error_msg = f"LLM service response missing 'm_query' field for table {table_name}: {result}"
                self.logger.error(f"[MQUERY_TRACKING] {error_msg}")
                raise Exception(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Error communicating with LLM service for table {table_name}: {e}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error in LLM service client for table {table_name}: {e}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
    
    def call_api_endpoint(self, endpoint: str, method: str = "POST", payload: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Call a specific API endpoint with proper formatting
        
        Args:
            endpoint: API endpoint path (e.g., "/api/mquery/staging")
            method: HTTP method (GET, POST)
            payload: Request payload
            
        Returns:
            API response or None if failed
        """
        try:
            headers = {'Content-Type': 'application/json'}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            url = f"{self.base_url.rstrip('/')}{endpoint}"
            
            self.logger.info(f"Calling API endpoint: {method} {url}")
            
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=payload, timeout=120)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            result = response.json()
            
            self.logger.info(f"API call successful: {endpoint}")
            return result
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API call failed for {endpoint}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error calling {endpoint}: {e}")
            return None
