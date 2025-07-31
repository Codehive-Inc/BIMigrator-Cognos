"""
Enhanced Migration Orchestrator that ties everything together
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

from cognos_migrator.config import get_migration_config, ConfigurationManager
from cognos_migrator.strategies import FallbackStrategy, MigrationStrategyConfig
from cognos_migrator.converters.enhanced_expression_converter import EnhancedExpressionConverter
from cognos_migrator.converters.enhanced_mquery_converter import EnhancedMQueryConverter
from cognos_migrator.reporting import MigrationReporter, ReportConfig, ReportFormat
from cognos_migrator.llm_service import LLMServiceClient


class EnhancedMigrationOrchestrator:
    """Orchestrates the complete enhanced migration with validation and fallback"""
    
    def __init__(self, 
                 config_file_path: Optional[str] = None,
                 llm_service_client: Optional[LLMServiceClient] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the enhanced migration orchestrator
        
        Args:
            config_file_path: Optional path to configuration file
            llm_service_client: Optional LLM service client
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Load configuration
        self.config_manager = ConfigurationManager(config_file_path, logger=self.logger)
        self.config = self.config_manager.load_config()
        
        # Initialize LLM service
        self.llm_service_client = llm_service_client
        
        # Initialize converters
        self._init_converters()
        
        # Initialize reporter
        self._init_reporter()
        
        # Migration state
        self.migration_start_time = None
        self.migration_results = []
        
    def _init_converters(self):
        """Initialize enhanced converters with configuration"""
        
        # Convert config to strategy config
        strategy_config = MigrationStrategyConfig(
            enable_pre_validation=self.config.validation.enable_pre_validation,
            enable_post_validation=self.config.validation.enable_post_validation,
            enable_semantic_validation=self.config.validation.enable_semantic_validation,
            enable_select_all_fallback=self.config.fallback.enable_select_all_fallback,
            enable_safe_dax_fallback=self.config.fallback.enable_dax_fallback,
            fallback_on_validation_failure=self.config.fallback.fallback_on_validation_failure,
            fallback_on_low_confidence=self.config.fallback.fallback_on_low_confidence,
            confidence_threshold=self.config.validation.confidence_threshold,
            complexity_threshold=self.config.validation.max_expression_complexity,
            max_retry_attempts=self.config.fallback.max_retry_attempts,
            query_folding_preference=self.config.llm.query_folding_preference
        )
        
        # Initialize enhanced converters
        self.expression_converter = EnhancedExpressionConverter(
            llm_service_client=self.llm_service_client,
            strategy_config=strategy_config,
            logger=self.logger
        )
        
        self.mquery_converter = EnhancedMQueryConverter(
            llm_service_client=self.llm_service_client,
            strategy_config=strategy_config,
            logger=self.logger
        )
    
    def _init_reporter(self):
        """Initialize migration reporter with configuration"""
        
        # Convert config formats to enum
        format_mapping = {
            "json": ReportFormat.JSON,
            "html": ReportFormat.HTML,
            "csv": ReportFormat.CSV,
            "markdown": ReportFormat.MARKDOWN
        }
        
        output_formats = [
            format_mapping.get(fmt, ReportFormat.JSON) 
            for fmt in self.config.reporting.output_formats
        ]
        
        report_config = ReportConfig(
            include_successful_conversions=True,
            include_failed_conversions=True,
            include_fallback_details=True,
            include_validation_results=self.config.reporting.include_validation_details,
            include_performance_metrics=self.config.reporting.include_performance_metrics,
            include_recommendations=True,
            output_formats=output_formats,
            max_sample_expressions=self.config.reporting.max_sample_count
        )
        
        self.reporter = MigrationReporter(config=report_config, logger=self.logger)
    
    def start_migration(self):
        """Start migration process"""
        self.migration_start_time = datetime.now()
        self.reporter.set_migration_metadata({
            "config": {
                "validation_enabled": self.config.validation.enable_post_validation,
                "fallback_enabled": self.config.fallback.enable_dax_fallback,
                "llm_service_enabled": self.config.llm.enable_llm_service,
                "confidence_threshold": self.config.validation.confidence_threshold
            }
        })
        self.logger.info("Enhanced migration started with full validation and fallback support")
    
    def migrate_expression(self, 
                          cognos_formula: str,
                          table_name: str = None,
                          column_name: str = None,
                          column_mappings: Dict[str, str] = None,
                          available_columns: List[str] = None) -> Dict[str, Any]:
        """
        Migrate a single expression with full validation and fallback
        
        Args:
            cognos_formula: Cognos formula to convert
            table_name: Table name for context
            column_name: Column name for context
            column_mappings: Column mappings
            available_columns: Available columns for validation
            
        Returns:
            Enhanced conversion result
        """
        result = self.expression_converter.convert_expression(
            cognos_formula=cognos_formula,
            table_name=table_name,
            column_name=column_name,
            column_mappings=column_mappings,
            available_columns=available_columns
        )
        
        # Add to reporter if available
        if hasattr(self.expression_converter.fallback_strategy, 'conversion_results'):
            for conversion_result in self.expression_converter.fallback_strategy.conversion_results:
                if conversion_result.original_expression == cognos_formula:
                    self.reporter.add_conversion_result(conversion_result)
                    break
        
        return result
    
    def migrate_table_mquery(self, table, report_spec: Optional[str] = None) -> str:
        """
        Migrate table M-Query with validation and fallback
        
        Args:
            table: Table object
            report_spec: Optional report specification
            
        Returns:
            Generated M-Query string
        """
        mquery = self.mquery_converter.convert_to_m_query(
            table=table,
            report_spec=report_spec
        )
        
        # Add to reporter
        self.reporter.add_table_result(
            table_name=table.name,
            mquery_result=mquery,
            fallback_applied=len(mquery) < 500  # Simple heuristic for fallback detection
        )
        
        return mquery
    
    def complete_migration(self, output_dir: str) -> Dict[str, Any]:
        """
        Complete migration and generate reports
        
        Args:
            output_dir: Directory to save reports
            
        Returns:
            Migration summary with report file paths
        """
        self.reporter.complete_migration()
        
        # Generate reports if enabled
        report_files = {}
        if self.config.reporting.generate_reports:
            report_files = self.reporter.generate_comprehensive_report(output_dir)
        
        # Get final statistics
        expression_report = self.expression_converter.get_conversion_report()
        mquery_report = self.mquery_converter.get_conversion_report()
        
        migration_summary = {
            "migration_completed": True,
            "start_time": self.migration_start_time.isoformat() if self.migration_start_time else None,
            "end_time": datetime.now().isoformat(),
            "report_files": report_files,
            "expression_statistics": expression_report,
            "mquery_statistics": mquery_report,
            "configuration_used": {
                "validation_level": self.config.validation.validation_level.value,
                "fallback_mode": self.config.fallback.fallback_mode.value,
                "confidence_threshold": self.config.validation.confidence_threshold
            }
        }
        
        self.logger.info(f"Enhanced migration completed. Reports generated: {list(report_files.keys())}")
        return migration_summary
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get summary of current configuration"""
        return {
            "validation": {
                "pre_validation": self.config.validation.enable_pre_validation,
                "post_validation": self.config.validation.enable_post_validation,
                "semantic_validation": self.config.validation.enable_semantic_validation,
                "validation_level": self.config.validation.validation_level.value,
                "confidence_threshold": self.config.validation.confidence_threshold
            },
            "fallback": {
                "mode": self.config.fallback.fallback_mode.value,
                "dax_fallback": self.config.fallback.enable_dax_fallback,
                "mquery_fallback": self.config.fallback.enable_mquery_fallback,
                "select_all_fallback": self.config.fallback.enable_select_all_fallback,
                "max_retry_attempts": self.config.fallback.max_retry_attempts
            },
            "llm": {
                "service_enabled": self.config.llm.enable_llm_service,
                "timeout": self.config.llm.service_timeout,
                "query_folding_preference": self.config.llm.query_folding_preference
            },
            "reporting": {
                "enabled": self.config.reporting.generate_reports,
                "output_formats": self.config.reporting.output_formats,
                "include_validation_details": self.config.reporting.include_validation_details
            }
        }
    
    def create_sample_config(self, file_path: str) -> str:
        """Create a sample configuration file"""
        return self.config_manager.create_sample_config_file(file_path)
    
    def validate_configuration(self) -> List[str]:
        """Validate current configuration"""
        return self.config_manager.validate_config(self.config)