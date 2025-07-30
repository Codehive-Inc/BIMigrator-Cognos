"""
Enhanced Expression Converter with validation and fallback support
"""

import logging
import requests
from typing import Dict, Any, Optional, List
import json
import asyncio

from cognos_migrator.llm_service import LLMServiceClient
from cognos_migrator.strategies import FallbackStrategy, MigrationStrategyConfig


class EnhancedExpressionConverter:
    """Enhanced converter with validation and fallback strategies"""
    
    def __init__(self, 
                 llm_service_client=None, 
                 strategy_config: Optional[MigrationStrategyConfig] = None,
                 logger=None):
        """
        Initialize the enhanced expression converter
        
        Args:
            llm_service_client: Optional LLMServiceClient instance
            strategy_config: Configuration for validation and fallback strategies
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.llm_service_client = llm_service_client
        
        # Initialize strategy configuration
        self.strategy_config = strategy_config or MigrationStrategyConfig()
        
        # Initialize fallback strategy
        self.fallback_strategy = FallbackStrategy(
            config=self.strategy_config,
            logger=self.logger
        )
        
        # Track all conversions for reporting
        self.conversion_history = []
    
    def convert_expression(self, 
                          cognos_formula: str, 
                          table_name: str = None,
                          column_name: str = None,
                          column_mappings: Dict[str, str] = None,
                          available_columns: List[str] = None) -> Dict[str, Any]:
        """
        Convert a Cognos formula to DAX with validation and fallback
        
        Args:
            cognos_formula: The Cognos formula to convert
            table_name: Optional table name for context
            column_name: Optional column name being calculated
            column_mappings: Optional mapping of Cognos column names to DAX column names
            available_columns: List of available columns for validation
            
        Returns:
            Dictionary containing:
                - dax_expression: The converted DAX expression
                - confidence: Confidence score (0-1)
                - notes: Any notes about the conversion
                - validation_passed: Whether validation passed
                - fallback_applied: Whether fallback was used
                - requires_review: Whether manual review is needed
        """
        # Handle empty expressions
        if not cognos_formula or cognos_formula.strip() == "":
            return {
                "dax_expression": "",
                "confidence": 1.0,
                "notes": "Empty expression",
                "validation_passed": True,
                "fallback_applied": False,
                "requires_review": False
            }
        
        # Build context for validation
        context = {
            "table_name": table_name,
            "column_name": column_name,
            "column_mappings": column_mappings or {},
            "columns": available_columns or [],
            "available_tables": [table_name] if table_name else []
        }
        
        # Use asyncio to run the async conversion
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running (e.g., in Jupyter), create task
                task = asyncio.create_task(
                    self._convert_with_strategy(cognos_formula, context)
                )
                # Wait for task completion with timeout
                result = asyncio.run_coroutine_threadsafe(
                    asyncio.wait_for(task, timeout=30),
                    loop
                ).result()
            else:
                # Otherwise run normally
                result = loop.run_until_complete(
                    self._convert_with_strategy(cognos_formula, context)
                )
        except Exception as e:
            # Handle asyncio errors
            self.logger.error(f"Async conversion error: {e}")
            result = self._create_fallback_result(cognos_formula, context, str(e))
        
        # Track conversion
        self.conversion_history.append({
            "cognos_formula": cognos_formula,
            "table_name": table_name,
            "result": result
        })
        
        return result
    
    async def _convert_with_strategy(self, 
                                   cognos_formula: str,
                                   context: Dict[str, Any]) -> Dict[str, Any]:
        """Convert using fallback strategy"""
        
        # Define LLM converter function
        async def llm_converter(expression, **kwargs):
            if self.llm_service_client:
                return await self._convert_with_llm_async(
                    expression,
                    kwargs.get("table_name"),
                    kwargs.get("column_mappings")
                )
            else:
                return None
        
        # Use fallback strategy
        conversion_result = await self.fallback_strategy.convert_with_fallback(
            expression=cognos_formula,
            expression_type="dax",
            context=context,
            llm_converter=llm_converter
        )
        
        # Convert to expected format
        return {
            "dax_expression": conversion_result.converted_expression,
            "confidence": conversion_result.confidence_score,
            "notes": self._build_notes(conversion_result),
            "validation_passed": conversion_result.validation_passed,
            "fallback_applied": conversion_result.fallback_applied,
            "requires_review": conversion_result.requires_manual_review,
            "strategy_used": conversion_result.strategy_used.value,
            "issues": conversion_result.issues,
            "warnings": conversion_result.warnings
        }
    
    async def _convert_with_llm_async(self,
                                    cognos_formula: str,
                                    table_name: str = None,
                                    column_mappings: Dict[str, str] = None) -> Dict[str, Any]:
        """Async wrapper for LLM conversion"""
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
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            self.logger.info(
                f"Successfully converted expression. Confidence: {result.get('confidence', 'unknown')}"
            )
            return result
            
        except Exception as e:
            self.logger.error(f"Error converting expression with LLM service: {e}")
            return None
    
    def _create_fallback_result(self, 
                              cognos_formula: str,
                              context: Dict[str, Any],
                              error_message: str) -> Dict[str, Any]:
        """Create a fallback result when conversion fails completely"""
        return {
            "dax_expression": f"BLANK() // ERROR: {error_message} - Original: {cognos_formula[:50]}...",
            "confidence": 0.0,
            "notes": f"Fallback applied due to error: {error_message}",
            "validation_passed": True,  # Fallback is always valid
            "fallback_applied": True,
            "requires_review": True,
            "strategy_used": "ERROR_FALLBACK",
            "issues": [error_message],
            "warnings": ["Manual conversion required"]
        }
    
    def _build_notes(self, conversion_result) -> str:
        """Build notes string from conversion result"""
        notes = []
        
        if conversion_result.strategy_used.value:
            notes.append(f"Strategy: {conversion_result.strategy_used.value}")
        
        if conversion_result.fallback_trigger:
            notes.append(f"Fallback reason: {conversion_result.fallback_trigger.value}")
        
        if conversion_result.issues:
            notes.append(f"Issues: {'; '.join(conversion_result.issues[:2])}")
        
        if conversion_result.warnings:
            notes.append(f"Warnings: {'; '.join(conversion_result.warnings[:2])}")
        
        return " | ".join(notes) if notes else "Converted successfully"
    
    def convert_batch(self,
                     expressions: List[Dict[str, Any]],
                     progress_callback=None) -> List[Dict[str, Any]]:
        """
        Convert multiple expressions with progress tracking
        
        Args:
            expressions: List of expression dictionaries with formula and context
            progress_callback: Optional callback function for progress updates
            
        Returns:
            List of conversion results
        """
        results = []
        total = len(expressions)
        
        for i, expr_info in enumerate(expressions):
            # Extract expression details
            formula = expr_info.get("formula", "")
            table_name = expr_info.get("table_name")
            column_name = expr_info.get("column_name")
            column_mappings = expr_info.get("column_mappings")
            available_columns = expr_info.get("available_columns")
            
            # Convert expression
            result = self.convert_expression(
                formula,
                table_name=table_name,
                column_name=column_name,
                column_mappings=column_mappings,
                available_columns=available_columns
            )
            
            # Add identifier to result
            result["identifier"] = expr_info.get("identifier", f"expr_{i}")
            results.append(result)
            
            # Report progress
            if progress_callback:
                progress_callback(i + 1, total, result)
        
        return results
    
    def get_conversion_report(self) -> Dict[str, Any]:
        """Get detailed conversion report"""
        
        # Get report from fallback strategy
        strategy_report = self.fallback_strategy.generate_migration_report()
        
        # Add converter-specific information
        enhanced_report = {
            **strategy_report,
            "converter_stats": {
                "total_conversions": len(self.conversion_history),
                "llm_available": self.llm_service_client is not None,
                "validation_enabled": self.strategy_config.enable_post_validation,
                "fallback_enabled": self.strategy_config.enable_safe_dax_fallback
            },
            "configuration": {
                "confidence_threshold": self.strategy_config.confidence_threshold,
                "max_retry_attempts": self.strategy_config.max_retry_attempts,
                "query_folding_preference": self.strategy_config.query_folding_preference
            }
        }
        
        # Add sample conversions
        if self.conversion_history:
            enhanced_report["sample_conversions"] = self.conversion_history[:5]
        
        return enhanced_report
    
    def reset_history(self):
        """Clear conversion history"""
        self.conversion_history.clear()
        self.fallback_strategy.conversion_results.clear()


# Backward compatibility: Create a wrapper that mimics the original ExpressionConverter
class ExpressionConverter(EnhancedExpressionConverter):
    """Backward compatible expression converter"""
    
    def __init__(self, llm_service_client=None, logger=None):
        # Use default configuration for backward compatibility
        super().__init__(
            llm_service_client=llm_service_client,
            strategy_config=MigrationStrategyConfig(
                # Default to less strict for compatibility
                enable_pre_validation=False,
                enable_post_validation=True,
                enable_safe_dax_fallback=True,
                confidence_threshold=0.5
            ),
            logger=logger
        )