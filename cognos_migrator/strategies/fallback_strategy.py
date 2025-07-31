"""
Fallback strategy implementation for safe migration
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from cognos_migrator.validators import ExpressionValidator, MQueryValidator, FallbackValidator


class ConversionStrategy(Enum):
    """Strategy used for conversion"""
    AI_FULLY_VALIDATED = "AI with full validation"
    AI_WITH_FEEDBACK = "AI with feedback improvements"
    SAFE_FALLBACK = "Safe fallback (BLANK/SELECT *)"
    MANUAL_TEMPLATE = "Manual configuration template"


class FallbackTrigger(Enum):
    """Reasons for triggering fallback"""
    VALIDATION_FAILED = "validation_failed"
    LOW_CONFIDENCE = "low_confidence"
    LLM_ERROR = "llm_error"
    COMPLEXITY_EXCEEDED = "complexity_exceeded"
    RETRY_EXHAUSTED = "retry_exhausted"


@dataclass
class MigrationStrategyConfig:
    """Configuration for migration strategies"""
    # Validation settings
    enable_pre_validation: bool = True
    enable_post_validation: bool = True
    enable_semantic_validation: bool = False  # Requires test data
    
    # Fallback settings
    enable_select_all_fallback: bool = True
    enable_safe_dax_fallback: bool = True
    fallback_on_validation_failure: bool = True
    fallback_on_low_confidence: bool = True
    
    # Thresholds
    confidence_threshold: float = 0.7
    complexity_threshold: int = 10
    max_retry_attempts: int = 3
    
    # Query folding preferences
    query_folding_preference: str = "BestEffort"  # "Strict", "BestEffort", "None"
    
    # Reporting
    generate_full_report: bool = True
    track_conversion_path: bool = True
    highlight_manual_fixes: bool = True


@dataclass
class ConversionResult:
    """Result of a conversion attempt"""
    original_expression: str
    converted_expression: str
    expression_type: str  # "dax" or "mquery"
    strategy_used: ConversionStrategy
    confidence_score: float
    validation_passed: bool
    fallback_applied: bool
    fallback_trigger: Optional[FallbackTrigger] = None
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    conversion_path: List[str] = field(default_factory=list)
    requires_manual_review: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class FallbackStrategy:
    """Implements the complete fallback strategy with validation"""
    
    def __init__(self, config: Optional[MigrationStrategyConfig] = None, 
                 logger: Optional[logging.Logger] = None):
        self.config = config or MigrationStrategyConfig()
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize validators
        self.expression_validator = ExpressionValidator(logger=self.logger)
        self.mquery_validator = MQueryValidator(logger=self.logger)
        self.fallback_validator = FallbackValidator(logger=self.logger)
        
        # Track results for reporting
        self.conversion_results: List[ConversionResult] = []
    
    async def convert_with_fallback(self, 
                                  expression: str,
                                  expression_type: str,
                                  context: Dict[str, Any],
                                  llm_converter=None) -> ConversionResult:
        """
        Convert expression with full validation and fallback strategy
        
        Args:
            expression: The expression to convert
            expression_type: "dax" or "mquery"
            context: Context information (table name, columns, etc.)
            llm_converter: Function to call LLM service
            
        Returns:
            ConversionResult with converted expression and metadata
        """
        result = ConversionResult(
            original_expression=expression,
            converted_expression="",
            expression_type=expression_type,
            strategy_used=ConversionStrategy.MANUAL_TEMPLATE,
            confidence_score=0.0,
            validation_passed=False,
            fallback_applied=False
        )
        
        # Step 1: Pre-validation (if enabled)
        if self.config.enable_pre_validation and expression_type == "dax":
            pre_validation = self.expression_validator.validate_cognos_expression(expression)
            
            if not pre_validation["is_valid"]:
                result.issues.extend(pre_validation["issues"])
                result.warnings.extend(pre_validation.get("warnings", []))
                result.conversion_path.append("PRE_VALIDATION_FAILED")
                
                if self.config.fallback_on_validation_failure:
                    return self._apply_fallback(result, FallbackTrigger.VALIDATION_FAILED, context)
        
        # Step 2: Try LLM conversion
        if llm_converter:
            try:
                llm_result = await self._try_llm_conversion(
                    expression, expression_type, context, llm_converter
                )
                
                if llm_result["success"]:
                    result.converted_expression = llm_result["converted"]
                    result.confidence_score = llm_result.get("confidence", 0.8)
                    result.conversion_path.append("LLM_CONVERSION_SUCCESS")
                    
                    # Step 3: Post-validation
                    if self.config.enable_post_validation:
                        validation = self._validate_converted_expression(
                            llm_result["converted"], expression_type, context
                        )
                        
                        if validation["is_valid"]:
                            result.validation_passed = True
                            result.strategy_used = ConversionStrategy.AI_FULLY_VALIDATED
                            result.conversion_path.append("POST_VALIDATION_PASSED")
                            
                            # Check confidence threshold
                            if (self.config.fallback_on_low_confidence and 
                                result.confidence_score < self.config.confidence_threshold):
                                result.warnings.append(
                                    f"Low confidence score: {result.confidence_score:.2f}"
                                )
                                result.requires_manual_review = True
                            
                            self._record_result(result)
                            return result
                        else:
                            result.issues.extend(validation.get("issues", []))
                            result.conversion_path.append("POST_VALIDATION_FAILED")
                            
                            if self.config.fallback_on_validation_failure:
                                return self._apply_fallback(
                                    result, FallbackTrigger.VALIDATION_FAILED, context
                                )
                else:
                    result.conversion_path.append("LLM_CONVERSION_FAILED")
                    
            except Exception as e:
                self.logger.error(f"LLM conversion error: {e}")
                result.issues.append(f"LLM error: {str(e)}")
                result.conversion_path.append(f"LLM_ERROR: {str(e)}")
                
                return self._apply_fallback(result, FallbackTrigger.LLM_ERROR, context)
        
        # If we get here, apply fallback
        return self._apply_fallback(result, FallbackTrigger.LLM_ERROR, context)
    
    def _apply_fallback(self, 
                       result: ConversionResult,
                       trigger: FallbackTrigger,
                       context: Dict[str, Any]) -> ConversionResult:
        """Apply appropriate fallback based on expression type"""
        result.fallback_applied = True
        result.fallback_trigger = trigger
        result.requires_manual_review = True
        
        if result.expression_type == "dax":
            # Apply DAX fallback
            if self.config.enable_safe_dax_fallback:
                fallback_expr = self._create_safe_dax_fallback(
                    result.original_expression, context
                )
                result.converted_expression = fallback_expr
                result.strategy_used = ConversionStrategy.SAFE_FALLBACK
                result.confidence_score = 1.0  # Fallback always works
                result.validation_passed = True
                result.conversion_path.append("SAFE_DAX_FALLBACK_APPLIED")
            else:
                # Keep original (will fail in Power BI)
                result.converted_expression = result.original_expression
                result.strategy_used = ConversionStrategy.MANUAL_TEMPLATE
                result.conversion_path.append("NO_FALLBACK_AVAILABLE")
                
        elif result.expression_type == "mquery":
            # Apply M-Query fallback
            if self.config.enable_select_all_fallback:
                fallback_query = self._create_select_all_fallback(context)
                result.converted_expression = fallback_query
                result.strategy_used = ConversionStrategy.SAFE_FALLBACK
                result.confidence_score = 1.0
                result.validation_passed = True
                result.conversion_path.append("SELECT_ALL_FALLBACK_APPLIED")
            else:
                # Create manual template
                fallback_query = self._create_manual_template(context)
                result.converted_expression = fallback_query
                result.strategy_used = ConversionStrategy.MANUAL_TEMPLATE
                result.conversion_path.append("MANUAL_TEMPLATE_CREATED")
        
        self._record_result(result)
        return result
    
    async def _try_llm_conversion(self,
                                expression: str,
                                expression_type: str,
                                context: Dict[str, Any],
                                llm_converter) -> Dict[str, Any]:
        """Try to convert using LLM service"""
        try:
            if expression_type == "dax":
                # Call DAX converter
                llm_result = await llm_converter(
                    expression,
                    table_name=context.get("table_name"),
                    column_mappings=context.get("column_mappings", {})
                )
                
                return {
                    "success": bool(llm_result.get("dax_expression")),
                    "converted": llm_result.get("dax_expression", ""),
                    "confidence": llm_result.get("confidence", 0.5)
                }
                
            else:  # mquery
                # Call M-Query generator
                llm_result = await llm_converter(context)
                
                return {
                    "success": bool(llm_result),
                    "converted": llm_result or "",
                    "confidence": 0.8 if llm_result else 0.0
                }
                
        except Exception as e:
            self.logger.error(f"LLM conversion failed: {e}")
            return {"success": False, "converted": "", "confidence": 0.0}
    
    def _validate_converted_expression(self,
                                     expression: str,
                                     expression_type: str,
                                     context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate converted expression"""
        if expression_type == "dax":
            return self.expression_validator.validate_dax_expression(expression, context)
        else:  # mquery
            return self.mquery_validator.validate_m_query(expression, context)
    
    def _create_safe_dax_fallback(self, 
                                original: str,
                                context: Dict[str, Any]) -> str:
        """Create safe DAX fallback expression"""
        timestamp = datetime.now().isoformat()
        column_name = context.get("column_name", "Unknown")
        
        return f"""// MIGRATION FALLBACK APPLIED
// Timestamp: {timestamp}
// Original Cognos: {original[:100]}{"..." if len(original) > 100 else ""}
// Column: {column_name}
// TODO: Manually convert this expression
BLANK()  // Safe placeholder - returns blank value"""
    
    def _create_select_all_fallback(self, context: Dict[str, Any]) -> str:
        """Create SELECT * fallback for M-Query"""
        table_name = context.get("table_name", "UnknownTable")
        source_info = context.get("source_info", {})
        source_type = source_info.get("source_type", "unknown").lower()
        
        if source_type in ["sql", "sqlserver"]:
            server = source_info.get("server", "YOUR_SERVER")
            database = source_info.get("database", "YOUR_DATABASE")
            schema = source_info.get("schema", "dbo")
            
            return f'''let
    // FALLBACK: SELECT * query
    // TODO: Verify connection parameters
    Source = Sql.Database("{server}", "{database}"),
    Data = Source{{[Schema="{schema}",Item="{table_name}"]}}[Data],
    
    // Preserve all columns
    AllColumns = Table.ColumnNames(Data),
    Result = Table.SelectColumns(Data, AllColumns)
in
    Result'''
            
        elif source_type == "oracle":
            server = source_info.get("server", "YOUR_SERVER")
            database = source_info.get("database", "YOUR_DATABASE")
            
            return f'''let
    // FALLBACK: SELECT * from Oracle
    Source = Oracle.Database("{server}", "{database}"),
    Data = Source{{[Schema="YOUR_SCHEMA",Item="{table_name}"]}}[Data]
in
    Data'''
            
        else:
            # Generic fallback
            return self._create_manual_template(context)
    
    def _create_manual_template(self, context: Dict[str, Any]) -> str:
        """Create manual configuration template"""
        table_name = context.get("table_name", "UnknownTable")
        columns = context.get("columns", [])
        
        # Build column type definitions
        column_defs = []
        for col in columns[:5]:  # Limit to first 5 columns for brevity
            col_name = col.get("name", "Column") if isinstance(col, dict) else str(col)
            column_defs.append(f'            {col_name} = text')
        
        if len(columns) > 5:
            column_defs.append('            // ... add remaining columns')
        
        column_text = ",\n".join(column_defs) if column_defs else "            Column1 = text"
        
        return f'''let
    // FALLBACK: Manual configuration required
    // Table: {table_name}
    // Generated: {datetime.now().isoformat()}
    
    // TODO: Configure your data source below
    Source = Table.FromRows(
        {{}}, 
        type table [
{column_text}
        ]
    ),
    
    #"Configuration Required" = "Update the Source step with your actual data connection"
in
    Source'''
    
    def _record_result(self, result: ConversionResult):
        """Record conversion result for reporting"""
        self.conversion_results.append(result)
        
        # Log summary
        self.logger.info(
            f"Conversion completed: {result.expression_type} | "
            f"Strategy: {result.strategy_used.value} | "
            f"Confidence: {result.confidence_score:.2f} | "
            f"Fallback: {result.fallback_applied}"
        )
    
    def generate_migration_report(self) -> Dict[str, Any]:
        """Generate comprehensive migration report"""
        total = len(self.conversion_results)
        
        if total == 0:
            return {"summary": "No conversions performed"}
        
        report = {
            "summary": {
                "total_conversions": total,
                "successful_ai": sum(
                    1 for r in self.conversion_results 
                    if r.strategy_used == ConversionStrategy.AI_FULLY_VALIDATED
                ),
                "with_fallback": sum(1 for r in self.conversion_results if r.fallback_applied),
                "manual_review_required": sum(
                    1 for r in self.conversion_results if r.requires_manual_review
                ),
                "success_rate": f"{(total - sum(1 for r in self.conversion_results if r.strategy_used == ConversionStrategy.MANUAL_TEMPLATE)) / total * 100:.1f}%"
            },
            "by_type": {
                "dax": sum(1 for r in self.conversion_results if r.expression_type == "dax"),
                "mquery": sum(1 for r in self.conversion_results if r.expression_type == "mquery")
            },
            "by_strategy": {},
            "fallback_triggers": {},
            "items_for_review": []
        }
        
        # Count by strategy
        for strategy in ConversionStrategy:
            count = sum(1 for r in self.conversion_results if r.strategy_used == strategy)
            if count > 0:
                report["by_strategy"][strategy.value] = count
        
        # Count fallback triggers
        for trigger in FallbackTrigger:
            count = sum(1 for r in self.conversion_results 
                       if r.fallback_trigger == trigger)
            if count > 0:
                report["fallback_triggers"][trigger.value] = count
        
        # List items needing review
        for result in self.conversion_results:
            if result.requires_manual_review:
                report["items_for_review"].append({
                    "type": result.expression_type,
                    "original": result.original_expression[:100] + "..." 
                              if len(result.original_expression) > 100 else result.original_expression,
                    "strategy": result.strategy_used.value,
                    "issues": result.issues,
                    "warnings": result.warnings
                })
        
        return report