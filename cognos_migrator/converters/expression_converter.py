"""
LLM-powered Cognos Expression to DAX Converter

This module provides functionality to convert Cognos expressions to DAX using the LLM service.
"""

import logging
import json
import re
import requests
from typing import Dict, List, Any, Optional
import json

from cognos_migrator.llm_service import LLMServiceClient


class ExpressionConverter:
    """Converts Cognos expressions to DAX using LLM service"""
    
    def __init__(self, llm_service_client=None, logger=None):
        """
        Initialize the expression converter
        
        Args:
            llm_service_client: Optional LLMServiceClient instance
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.llm_service_client = llm_service_client
        
    def convert_expression(self, 
                          cognos_formula: str, 
                          table_name: str = None, 
                          column_mappings: Dict[str, str] = None,
                          query_data: List[Dict] = None):
        """
        Convert a Cognos formula to DAX using the LLM service
        
        Args:
            cognos_formula: The Cognos formula to convert
            table_name: Optional table name for context
            column_mappings: Optional mapping of Cognos column names to DAX column names
            query_data: Optional query data from report_queries.json for context extraction
            
        Returns:
            Dictionary containing:
                - dax_expression: The converted DAX expression
                - confidence: Confidence score (0-1)
                - notes: Any notes about the conversion
        """
        if not cognos_formula:
            self.logger.warning("Empty Cognos formula provided")
            return {
                "dax_expression": "",
                "confidence": 0,
                "notes": "Empty Cognos formula provided"
            }
        
        # Extract table name from expression if not provided
        extracted_table = self._extract_table_from_expression(cognos_formula)
        if extracted_table and not table_name:
            table_name = extracted_table
            self.logger.info(f"Extracted table name from expression: {table_name}")
        
        # Extract column mappings from query data if available
        if query_data and not column_mappings:
            extracted_mappings = self._extract_column_mappings_from_query(query_data, cognos_formula)
            if extracted_mappings:
                column_mappings = extracted_mappings
                self.logger.info(f"Extracted column mappings: {column_mappings}")
        
        # Try to convert with LLM service
        if self.llm_service_client:
            try:
                result = self._convert_with_llm(cognos_formula, table_name, column_mappings)
                if result and result.get("dax_expression"):
                    return result
                else:
                    # Return error if LLM service didn't return a valid result
                    return {
                        "dax_expression": cognos_formula,  # Keep original expression
                        "confidence": 0.0,
                        "notes": "LLM service conversion failed: No valid result returned"
                    }
            except Exception as e:
                error_message = f"LLM service conversion failed: {e}"
                self.logger.error(error_message)
                return {
                    "dax_expression": cognos_formula,  # Keep original expression
                    "confidence": 0.0,
                    "notes": error_message
                }
        else:
            # No LLM service client available
            return {
                "dax_expression": cognos_formula,  # Keep original expression
                "confidence": 0.0,
                "notes": "LLM service not available"
            }
    
    def _extract_table_from_expression(self, expression):
        """
        Extract the table name from a Cognos expression
        
        Args:
            expression: The Cognos expression to extract from
            
        Returns:
            The extracted table name or None if not found
        """
        # Try to extract table name from fully qualified references like [Database_Layer].[TABLE_NAME].[COLUMN_NAME]
        table_pattern = r'\[([^\]]+)\]\.\[([^\]]+)\]\.\[([^\]]+)\]'
        matches = re.findall(table_pattern, expression)
        if matches:
            # Return the table name (second group)
            return matches[0][1]
        return None
        
    def _extract_column_mappings_from_query(self, query_data, expression):
        """
        Extract column mappings from query data
        
        Args:
            query_data: The query data from report_queries.json
            expression: The Cognos expression to analyze
            
        Returns:
            Dictionary mapping column references to fully qualified column references
        """
        column_mappings = {}
        
        # Extract column references from the expression
        column_pattern = r'\[([^\]]+)\]'
        referenced_columns = re.findall(column_pattern, expression)
        
        # Build mappings from query data
        for query in query_data:
            for item in query.get('data_items', []):
                item_name = item.get('name')
                item_expr = item.get('expression')
                
                if item_name in referenced_columns:
                    # Extract table name from the item expression
                    table_name = self._extract_table_from_expression(item_expr)
                    if table_name:
                        column_mappings[f'[{item_name}]'] = f"'{table_name}'[{item_name}]"
        
        return column_mappings
    
    def _convert_with_llm(self, 
                         cognos_formula: str, 
                         table_name: str = None, 
                         column_mappings: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Convert a Cognos formula to DAX using the LLM service
        
        Args:
            cognos_formula: The Cognos formula to convert
            table_name: Optional table name for context
            column_mappings: Optional mapping of Cognos column names to DAX column names
            
        Returns:
            Dictionary containing the conversion result
        """
        try:
            # Check if LLM service is healthy
            health = self.llm_service_client.check_health()
            if health.get("status") != "healthy":
                self.logger.warning(f"LLM service is not healthy: {health}")
                return None
            
            # Extract table name from the expression if not provided
            extracted_table = self._extract_table_from_expression(cognos_formula)
            if extracted_table and not table_name:
                table_name = extracted_table
                
            # Prepare the request payload
            payload = {
                "cognos_expression": cognos_formula,
                "table_name": table_name or "",
                "column_mappings": column_mappings or {}
            }
            
            # Make the API request
            self.logger.info(f"Converting expression with LLM service: {cognos_formula}")
            
            headers = {'Content-Type': 'application/json'}
            response = requests.post(
                f'{self.llm_service_client.base_url}/api/dax/convert',
                headers=headers,
                json=payload,
                timeout=30  # 30 second timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            self.logger.info(f"Successfully converted expression with LLM service. Confidence: {result.get('confidence', 'unknown')}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error converting expression with LLM service: {e}")
            return None
    
    # The _convert_with_rules method has been removed as we're now only using the LLM service
