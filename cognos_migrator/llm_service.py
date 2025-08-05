"""
Enhanced LLM Service Client for M-Query Generation with Error Handling
"""

import json
import logging
import os
import requests
from typing import Dict, Any, Optional


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
        
        Returns:
            Optimized M-query string
            
        Raises:
            Exception: If the LLM service fails or returns invalid results
        """
        table_name = context.get('table_name', 'unknown')
        
        try:
            headers = {'Content-Type': 'application/json'}
            
            # Prepare enhanced payload with error handling requirements
            enhanced_context = {
                **context,
                'source_type': context.get('source_type', 'sql'),
                'error_handling_requirements': {
                    'wrap_with_try_otherwise': True,
                    'include_fallback_empty_table': True,
                    'preserve_schema_on_error': True,
                    'add_error_info_column': True,
                    'connection_retry_logic': False  # Keep simple for now
                },
                'generation_guidelines': [
                    "Always wrap database connections with try...otherwise",
                    "Include fallback to empty table with correct schema on error",
                    "Add error information column when connection fails",
                    "Use proper M error records with Reason, Message, and Detail",
                    "Test for HasError before accessing Value",
                    "Implement graceful degradation for each transformation step"
                ]
            }
            
            payload = {
                'context': enhanced_context,
                'options': {
                    'optimize_for_performance': True,
                    'include_comments': True,
                    'error_handling_mode': 'comprehensive',
                    'include_exception_handling': True,
                    'fallback_strategy': 'empty_table_with_schema',
                    'use_template_mode': True,
                    'template_compliance': 'guided'
                },
                'system_prompt_additions': [
                    "Generate M-Query code with comprehensive exception handling",
                    "Use try...otherwise blocks for all potentially failing operations",
                    "Include proper error records and fallback mechanisms",
                    "Ensure the query won't break Power BI refresh even if data source is unavailable"
                ]
            }
            
            # Make the request to the FastAPI endpoint
            self.logger.info(f"Sending request to LLM service for table {table_name}")
            response = requests.post(
                f'{self.base_url}/api/m-query',
                headers=headers,
                json=payload,
                timeout=120  # 120 second timeout (increased from 30 to reduce timeout errors)
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Log the complete API response structure
            self.logger.info(f"Complete API response: {json.dumps(result, indent=2)}")
            
            if 'm_query' in result:
                m_query = result['m_query']
                
                # Validate error handling in generated M-Query
                validation_result = self._validate_error_handling(m_query)
                
                if validation_result['has_error_handling']:
                    self.logger.info(f"✅ Generated M-query has proper error handling for table {table_name}")
                else:
                    self.logger.warning(f"⚠️  Generated M-query lacks error handling for table {table_name}, applying fallback")
                    m_query = self._add_error_handling_wrapper(m_query, context)
                
                # Log enhanced features
                if result.get('template_used'):
                    self.logger.info(f"Template-based generation used for {table_name}")
                
                if result.get('validation', {}).get('is_valid'):
                    self.logger.info(f"DAX API validation passed for {table_name}")
                
                # Log performance notes if available
                if 'performance_notes' in result and result['performance_notes']:
                    self.logger.info(f"Performance notes: {result['performance_notes']}")
                
                # Log confidence score
                confidence = result.get('confidence', 1.0)
                if confidence:
                    self.logger.info(f"Generation confidence: {confidence:.2f} for {table_name}")
                
                return m_query
            else:
                error_msg = f"LLM service response missing 'm_query' field for table {table_name}: {result}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Error communicating with LLM service for table {table_name}: {e}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error in LLM service client for table {table_name}: {e}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
    
    # Removed fallback method as we now raise exceptions instead of falling back
    # def _fallback_m_query(self, context: Dict[str, Any]) -> str:
    #     """Generate a fallback M-query when the LLM service fails"""
    #     table_name = context.get('table_name', 'Unknown')
    #     self.logger.warning(f"Using fallback M-query generation for table: {table_name}")
    #     
    #     if context.get('source_query'):
            # For SQL queries, wrap in appropriate M function with comments
            return f'''// Fallback M-query for {table_name} (LLM service unavailable)
let
    Source = Sql.Database("server", "database", [Query="{context['source_query']}"])
    // Apply type transformations based on column definitions
    #"Changed Type" = Source
in
    #"Changed Type"'''
        else:
            # For tables without a source query, create a more informative empty table
            columns_str = ", ".join([f'"{col["name"]}"' for col in context.get('columns', [])])
            if columns_str:
                return f'''// Fallback M-query for {table_name} (LLM service unavailable)
let
    Source = Table.FromRows({{}}, type table [{columns_str}]),
    // This is an empty table with the correct schema
    #"Changed Type" = Source
in
    #"Changed Type"'''
            else:
                return f'''// Fallback M-query for {table_name} (LLM service unavailable)
let
    Source = Table.FromRows({{}}),
    // Empty table with no schema information
    #"Changed Type" = Source
in
    #"Changed Type"'''
    
    def _validate_error_handling(self, m_query: str) -> Dict[str, Any]:
        """
        Validate that M-Query includes proper error handling
        
        Args:
            m_query: The generated M-Query string
            
        Returns:
            Dictionary with validation results
        """
        validation = {
            'has_try_otherwise': 'try' in m_query and 'otherwise' in m_query,
            'has_error_checking': '[HasError]' in m_query or 'HasError' in m_query,
            'has_error_records': 'error [' in m_query or 'Reason =' in m_query,
            'has_fallback_table': any(x in m_query for x in ['Table.FromColumns', 'Table.FromRows']),
            'has_let_in_structure': 'let' in m_query and 'in' in m_query
        }
        
        # Overall assessment
        validation['has_error_handling'] = (
            validation['has_try_otherwise'] and 
            validation['has_error_checking'] and 
            validation['has_fallback_table']
        )
        
        return validation
    
    def _add_error_handling_wrapper(self, m_query: str, context: Dict[str, Any]) -> str:
        """
        Wrap M-Query with error handling if it's missing
        
        Args:
            m_query: Original M-Query without error handling
            context: Context information for generating fallback
            
        Returns:
            M-Query wrapped with error handling
        """
        table_name = context.get('table_name', 'Table')
        columns = context.get('columns', [])
        
        # Build column definitions for fallback
        column_names = [f'"{col.get("name", f"Column{i+1}")}"' for i, col in enumerate(columns)]
        empty_columns = [f'{{}}' for _ in columns]
        
        wrapped_query = f"""
// Enhanced with error handling by BIMigrator
let
    // Attempt to execute original query
    AttemptQuery = try (
        {m_query.strip()}
    ) otherwise error [
        Reason = "QueryExecutionFailed",
        Message = "Failed to execute M-Query for {table_name}",
        Detail = "Check data source connectivity and query syntax"
    ],
    
    // Handle query result with fallback
    Result = if AttemptQuery[HasError] then
        let
            // Create empty table with expected schema
            EmptyTable = Table.FromColumns(
                {{{', '.join(empty_columns)}}},
                {{{', '.join(column_names)}}}
            ),
            // Add error information column
            WithErrorInfo = Table.AddColumn(
                EmptyTable,
                "_QueryError",
                each "Query failed: " & Text.From(AttemptQuery[Error][Message])
            )
        in
            WithErrorInfo
    else
        AttemptQuery[Value]
in
    Result
"""
        
        self.logger.info(f"Applied error handling wrapper to M-Query for {table_name}")
        return wrapped_query
