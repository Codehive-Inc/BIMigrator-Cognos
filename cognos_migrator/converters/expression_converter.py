"""
LLM-powered Cognos Expression to DAX Converter

This module provides functionality to convert Cognos expressions to DAX using the LLM service.
"""

import logging
import requests
from typing import Dict, Any, Optional, List
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
                          column_mappings: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Convert a Cognos formula to DAX using the LLM service
        
        Args:
            cognos_formula: The Cognos formula to convert
            table_name: Optional table name for context
            column_mappings: Optional mapping of Cognos column names to DAX column names
            
        Returns:
            Dictionary containing:
                - dax_expression: The converted DAX expression
                - confidence: Confidence score (0-1)
                - notes: Any notes about the conversion
        """
        if not cognos_formula or cognos_formula.strip() == "":
            return {
                "dax_expression": "",
                "confidence": 1.0,
                "notes": "Empty expression"
            }
            
        # Try using LLM service if available
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
