"""
LLM-powered Cognos Expression to DAX Converter

This module provides functionality to convert Cognos expressions to DAX using the LLM service.
Now enhanced with validation and fallback strategies.
"""

import logging
import requests
from typing import Dict, Any, Optional, List
import json
import os

from cognos_migrator.llm_service import LLMServiceClient
from cognos_migrator.strategies import MigrationStrategyConfig
from .enhanced_expression_converter import EnhancedExpressionConverter


class ExpressionConverter:
    """Converts Cognos expressions to DAX using LLM service with validation and fallback"""
    
    def __init__(self, llm_service_client=None, logger=None):
        """
        Initialize the expression converter
        
        Args:
            llm_service_client: Optional LLMServiceClient instance
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.llm_service_client = llm_service_client
        
        # Check if enhanced mode is enabled via environment variable
        use_enhanced = os.getenv('USE_ENHANCED_CONVERTER', 'true').lower() == 'true'
        
        if use_enhanced:
            # Use enhanced converter with validation and fallback
            self._init_enhanced_converter()
        else:
            # Keep original behavior for backward compatibility
            self._use_enhanced = False
    
    def _init_enhanced_converter(self):
        """Initialize the enhanced converter with configuration"""
        # Create configuration based on environment variables
        config = MigrationStrategyConfig(
            enable_pre_validation=os.getenv('ENABLE_PRE_VALIDATION', 'false').lower() == 'true',
            enable_post_validation=os.getenv('ENABLE_POST_VALIDATION', 'true').lower() == 'true',
            enable_safe_dax_fallback=os.getenv('ENABLE_DAX_FALLBACK', 'true').lower() == 'true',
            confidence_threshold=float(os.getenv('CONFIDENCE_THRESHOLD', '0.7')),
            max_retry_attempts=int(os.getenv('MAX_RETRY_ATTEMPTS', '3'))
        )
        
        # Create enhanced converter
        self._enhanced_converter = EnhancedExpressionConverter(
            llm_service_client=self.llm_service_client,
            strategy_config=config,
            logger=self.logger
        )
        self._use_enhanced = True
        
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
        # Use enhanced converter if available
        if hasattr(self, '_use_enhanced') and self._use_enhanced:
            result = self._enhanced_converter.convert_expression(
                cognos_formula=cognos_formula,
                table_name=table_name,
                column_mappings=column_mappings
            )
            
            # Filter out extra fields for backward compatibility
            return {
                "dax_expression": result.get("dax_expression", ""),
                "confidence": result.get("confidence", 0.0),
                "notes": result.get("notes", "")
            }
        
        # Original implementation (fallback mode)
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
                "cognos_formula": cognos_formula,
                "table_name": table_name or "",
                "column_mappings": column_mappings or {}
            }
            
            # Make the API request
            self.logger.info(f"Converting expression with LLM service: {cognos_formula}")
            
            headers = {'Content-Type': 'application/json'}
            response = requests.post(
                f'{self.llm_service_client.base_url}/convert',
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
    
    def get_conversion_report(self) -> Dict[str, Any]:
        """Get conversion report if using enhanced converter"""
        if hasattr(self, '_use_enhanced') and self._use_enhanced:
            return self._enhanced_converter.get_conversion_report()
        else:
            return {"message": "Conversion reporting not available in legacy mode"}
    
    def reset_history(self):
        """Reset conversion history if using enhanced converter"""
        if hasattr(self, '_use_enhanced') and self._use_enhanced:
            self._enhanced_converter.reset_history()
