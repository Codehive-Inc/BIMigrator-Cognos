"""
Configuration system for fallback strategies and validation settings
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum


class ValidationLevel(Enum):
    """Validation levels"""
    NONE = "none"
    BASIC = "basic"
    STRICT = "strict"
    COMPREHENSIVE = "comprehensive"


class FallbackMode(Enum):
    """Fallback modes"""
    DISABLED = "disabled"
    SAFE_ONLY = "safe_only"
    SELECT_ALL = "select_all"
    COMPREHENSIVE = "comprehensive"


@dataclass
class ValidationConfig:
    """Validation configuration"""
    enable_pre_validation: bool = True
    enable_post_validation: bool = True
    enable_semantic_validation: bool = False
    validation_level: ValidationLevel = ValidationLevel.BASIC
    strict_column_validation: bool = False
    max_expression_complexity: int = 15
    confidence_threshold: float = 0.7


@dataclass 
class FallbackConfig:
    """Fallback configuration"""
    fallback_mode: FallbackMode = FallbackMode.COMPREHENSIVE
    enable_dax_fallback: bool = True
    enable_mquery_fallback: bool = True
    enable_select_all_fallback: bool = True
    fallback_on_low_confidence: bool = True
    fallback_on_validation_failure: bool = True
    max_retry_attempts: int = 3
    preserve_original_in_comments: bool = True


@dataclass
class LLMConfig:
    """LLM service configuration"""
    enable_llm_service: bool = True
    service_timeout: int = 30
    max_concurrent_requests: int = 5
    retry_on_failure: bool = True
    cache_results: bool = True
    query_folding_preference: str = "BestEffort"  # "Strict", "BestEffort", "None"


@dataclass
class ReportingConfig:
    """Reporting configuration"""
    generate_reports: bool = True
    include_validation_details: bool = True
    include_performance_metrics: bool = True
    include_sample_conversions: bool = True
    max_sample_count: int = 10
    output_formats: List[str] = None
    
    def __post_init__(self):
        if self.output_formats is None:
            self.output_formats = ["json", "html"]


@dataclass
class EnhancedMigrationConfig:
    """Complete enhanced migration configuration"""
    validation: ValidationConfig = None
    fallback: FallbackConfig = None
    llm: LLMConfig = None
    reporting: ReportingConfig = None
    
    def __post_init__(self):
        if self.validation is None:
            self.validation = ValidationConfig()
        if self.fallback is None:
            self.fallback = FallbackConfig()
        if self.llm is None:
            self.llm = LLMConfig()
        if self.reporting is None:
            self.reporting = ReportingConfig()


class ConfigurationManager:
    """Manages configuration for enhanced migration features"""
    
    def __init__(self, config_file_path: Optional[str] = None, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.config_file_path = config_file_path
        self._config: Optional[EnhancedMigrationConfig] = None
    
    def load_config(self, config_source: Optional[str] = None) -> EnhancedMigrationConfig:
        """
        Load configuration from various sources
        
        Args:
            config_source: Optional specific config source ("file", "env", "default")
            
        Returns:
            EnhancedMigrationConfig instance
        """
        if config_source == "file" or (config_source is None and self.config_file_path):
            config = self._load_from_file()
        elif config_source == "env":
            config = self._load_from_environment()
        else:
            # Load with priority: file -> env -> defaults
            config = self._load_with_priority()
        
        self._config = config
        self.logger.info(f"Configuration loaded successfully from {config_source or 'multiple sources'}")
        return config
    
    def get_config(self) -> EnhancedMigrationConfig:
        """Get current configuration, loading defaults if not already loaded"""
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def save_config(self, config: EnhancedMigrationConfig, file_path: Optional[str] = None) -> str:
        """
        Save configuration to file
        
        Args:
            config: Configuration to save
            file_path: Optional file path, uses default if not provided
            
        Returns:
            Path where config was saved
        """
        save_path = file_path or self.config_file_path or "migration_config.json"
        
        # Convert to dictionary
        config_dict = asdict(config)
        
        # Convert enums to strings
        config_dict = self._serialize_enums(config_dict)
        
        # Save to file
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2)
        
        self.logger.info(f"Configuration saved to {save_path}")
        return save_path
    
    def _load_from_file(self) -> EnhancedMigrationConfig:
        """Load configuration from JSON file"""
        if not self.config_file_path or not Path(self.config_file_path).exists():
            self.logger.warning(f"Config file not found: {self.config_file_path}, using defaults")
            return EnhancedMigrationConfig()
        
        try:
            with open(self.config_file_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            
            # Deserialize enums
            config_dict = self._deserialize_enums(config_dict)
            
            # Create config objects
            validation = ValidationConfig(**config_dict.get("validation", {}))
            fallback = FallbackConfig(**config_dict.get("fallback", {}))
            llm = LLMConfig(**config_dict.get("llm", {}))
            reporting = ReportingConfig(**config_dict.get("reporting", {}))
            
            return EnhancedMigrationConfig(
                validation=validation,
                fallback=fallback,
                llm=llm,
                reporting=reporting
            )
            
        except Exception as e:
            self.logger.error(f"Error loading config from file: {e}")
            return EnhancedMigrationConfig()
    
    def _load_from_environment(self) -> EnhancedMigrationConfig:
        """Load configuration from environment variables"""
        
        # Validation config
        validation = ValidationConfig(
            enable_pre_validation=os.getenv('ENABLE_PRE_VALIDATION', 'true').lower() == 'true',
            enable_post_validation=os.getenv('ENABLE_POST_VALIDATION', 'true').lower() == 'true',
            enable_semantic_validation=os.getenv('ENABLE_SEMANTIC_VALIDATION', 'false').lower() == 'true',
            validation_level=ValidationLevel(os.getenv('VALIDATION_LEVEL', 'basic')),
            strict_column_validation=os.getenv('STRICT_COLUMN_VALIDATION', 'false').lower() == 'true', 
            max_expression_complexity=int(os.getenv('MAX_EXPRESSION_COMPLEXITY', '15')),
            confidence_threshold=float(os.getenv('CONFIDENCE_THRESHOLD', '0.7'))
        )
        
        # Fallback config
        fallback = FallbackConfig(
            fallback_mode=FallbackMode(os.getenv('FALLBACK_MODE', 'comprehensive')),
            enable_dax_fallback=os.getenv('ENABLE_DAX_FALLBACK', 'true').lower() == 'true',
            enable_mquery_fallback=os.getenv('ENABLE_MQUERY_FALLBACK', 'true').lower() == 'true',
            enable_select_all_fallback=os.getenv('ENABLE_SELECT_ALL_FALLBACK', 'true').lower() == 'true',
            fallback_on_low_confidence=os.getenv('FALLBACK_ON_LOW_CONFIDENCE', 'true').lower() == 'true',
            fallback_on_validation_failure=os.getenv('FALLBACK_ON_VALIDATION_FAILURE', 'true').lower() == 'true',
            max_retry_attempts=int(os.getenv('MAX_RETRY_ATTEMPTS', '3')),
            preserve_original_in_comments=os.getenv('PRESERVE_ORIGINAL_IN_COMMENTS', 'true').lower() == 'true'
        )
        
        # LLM config
        llm = LLMConfig(
            enable_llm_service=os.getenv('ENABLE_LLM_SERVICE', 'true').lower() == 'true',
            service_timeout=int(os.getenv('LLM_SERVICE_TIMEOUT', '30')),
            max_concurrent_requests=int(os.getenv('MAX_CONCURRENT_REQUESTS', '5')),
            retry_on_failure=os.getenv('RETRY_ON_FAILURE', 'true').lower() == 'true',
            cache_results=os.getenv('CACHE_LLM_RESULTS', 'true').lower() == 'true',
            query_folding_preference=os.getenv('QUERY_FOLDING_PREFERENCE', 'BestEffort')
        )
        
        # Reporting config
        output_formats = os.getenv('REPORT_OUTPUT_FORMATS', 'json,html').split(',')
        reporting = ReportingConfig(
            generate_reports=os.getenv('GENERATE_REPORTS', 'true').lower() == 'true',
            include_validation_details=os.getenv('INCLUDE_VALIDATION_DETAILS', 'true').lower() == 'true',
            include_performance_metrics=os.getenv('INCLUDE_PERFORMANCE_METRICS', 'true').lower() == 'true',
            include_sample_conversions=os.getenv('INCLUDE_SAMPLE_CONVERSIONS', 'true').lower() == 'true',
            max_sample_count=int(os.getenv('MAX_SAMPLE_COUNT', '10')),
            output_formats=[fmt.strip() for fmt in output_formats]
        )
        
        return EnhancedMigrationConfig(
            validation=validation,
            fallback=fallback,
            llm=llm,
            reporting=reporting
        )
    
    def _load_with_priority(self) -> EnhancedMigrationConfig:
        """Load configuration with priority: file -> env -> defaults"""
        
        # Start with defaults
        config = EnhancedMigrationConfig()
        
        # Override with file config if available
        if self.config_file_path and Path(self.config_file_path).exists():
            file_config = self._load_from_file()
            config = self._merge_configs(config, file_config)
        
        # Override with environment variables
        env_config = self._load_from_environment()
        config = self._merge_configs(config, env_config)
        
        return config
    
    def _merge_configs(self, base: EnhancedMigrationConfig, override: EnhancedMigrationConfig) -> EnhancedMigrationConfig:
        """Merge two configurations, with override taking precedence"""
        
        # For simplicity, we'll use the override values where they differ from defaults
        # In a more sophisticated implementation, you might do field-by-field merging
        
        return EnhancedMigrationConfig(
            validation=override.validation,
            fallback=override.fallback,
            llm=override.llm,
            reporting=override.reporting
        )
    
    def _serialize_enums(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Convert enum values to strings for JSON serialization"""
        
        def convert_value(value):
            if hasattr(value, 'value'):  # Enum
                return value.value
            elif isinstance(value, dict):
                return {k: convert_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [convert_value(v) for v in value]
            else:
                return value
        
        return convert_value(config_dict)
    
    def _deserialize_enums(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Convert string values back to enums"""
        
        # Map string values to enum types
        enum_mappings = {
            'validation_level': ValidationLevel,
            'fallback_mode': FallbackMode
        }
        
        def convert_section(section_name: str, section_data: Dict[str, Any]) -> Dict[str, Any]:
            converted = {}
            for key, value in section_data.items():
                if key in enum_mappings:
                    try:
                        converted[key] = enum_mappings[key](value)
                    except (ValueError, KeyError):
                        self.logger.warning(f"Invalid enum value '{value}' for {key}, using default")
                        # Use first value as default
                        converted[key] = list(enum_mappings[key])[0]
                else:
                    converted[key] = value
            return converted
        
        result = {}
        for section, data in config_dict.items():
            if isinstance(data, dict):
                result[section] = convert_section(section, data)
            else:
                result[section] = data
        
        return result
    
    def create_sample_config_file(self, file_path: str) -> str:
        """Create a sample configuration file with comments"""
        
        sample_config = {
            "_comment": "Enhanced Migration Configuration",
            "_description": "Configuration for Cognos to Power BI migration with validation and fallback",
            
            "validation": {
                "_comment": "Validation settings",
                "enable_pre_validation": True,
                "enable_post_validation": True,
                "enable_semantic_validation": False,
                "validation_level": "basic",
                "strict_column_validation": False,
                "max_expression_complexity": 15,
                "confidence_threshold": 0.7
            },
            
            "fallback": {
                "_comment": "Fallback strategy settings",
                "fallback_mode": "comprehensive",
                "enable_dax_fallback": True,
                "enable_mquery_fallback": True,
                "enable_select_all_fallback": True,
                "fallback_on_low_confidence": True,
                "fallback_on_validation_failure": True,
                "max_retry_attempts": 3,
                "preserve_original_in_comments": True
            },
            
            "llm": {
                "_comment": "LLM service settings",
                "enable_llm_service": True,
                "service_timeout": 30,
                "max_concurrent_requests": 5,
                "retry_on_failure": True,
                "cache_results": True,
                "query_folding_preference": "BestEffort"
            },
            
            "reporting": {
                "_comment": "Report generation settings",
                "generate_reports": True,
                "include_validation_details": True,
                "include_performance_metrics": True,
                "include_sample_conversions": True,
                "max_sample_count": 10,
                "output_formats": ["json", "html"]
            }
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(sample_config, f, indent=2)
        
        self.logger.info(f"Sample configuration file created at {file_path}")
        return file_path
    
    def validate_config(self, config: EnhancedMigrationConfig) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        # Validate thresholds
        if not 0 <= config.validation.confidence_threshold <= 1:
            issues.append("Confidence threshold must be between 0 and 1")
        
        if config.validation.max_expression_complexity < 1:
            issues.append("Max expression complexity must be at least 1")
        
        if config.fallback.max_retry_attempts < 0:
            issues.append("Max retry attempts cannot be negative")
        
        if config.llm.service_timeout < 1:
            issues.append("LLM service timeout must be at least 1 second")
        
        if config.reporting.max_sample_count < 0:
            issues.append("Max sample count cannot be negative")
        
        # Validate enum values
        valid_formats = ["json", "html", "csv", "markdown"]
        for fmt in config.reporting.output_formats:
            if fmt not in valid_formats:
                issues.append(f"Invalid output format: {fmt}")
        
        return issues


# Convenience function for getting configuration
_config_manager = None

def get_config_manager(config_file_path: Optional[str] = None) -> ConfigurationManager:
    """Get or create configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager(config_file_path)
    return _config_manager

def get_migration_config() -> EnhancedMigrationConfig:
    """Get current migration configuration"""
    return get_config_manager().get_config()