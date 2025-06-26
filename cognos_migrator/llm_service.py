"""
LLM Service Client for M-Query Generation
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
            
            # Prepare the payload for the LLM service according to the API spec
            payload = {
                'context': context,
                'options': {
                    'optimize_for_performance': True,
                    'include_comments': True
                }
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
                self.logger.info(f"Successfully generated M-query for table {table_name}")
                # Log performance notes if available
                if 'performance_notes' in result and result['performance_notes']:
                    self.logger.info(f"Performance notes: {result['performance_notes']}")
                # Log confidence score
                if 'confidence' in result:
                    self.logger.info(f"Confidence score: {result['confidence']}")
                return result['m_query']
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
