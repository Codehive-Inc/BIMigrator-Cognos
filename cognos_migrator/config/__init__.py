"""
Configuration system for enhanced migration features
"""

# Import original config classes for backward compatibility
from ..config import MigrationConfig, CognosConfig

from .fallback_config import (
    ValidationConfig,
    FallbackConfig, 
    LLMConfig,
    ReportingConfig,
    EnhancedMigrationConfig,
    ConfigurationManager,
    ValidationLevel,
    FallbackMode,
    get_config_manager,
    get_migration_config
)

__all__ = [
    # Original config classes (backward compatibility)
    'MigrationConfig',
    'CognosConfig',
    # Enhanced config classes
    'ValidationConfig',
    'FallbackConfig',
    'LLMConfig', 
    'ReportingConfig',
    'EnhancedMigrationConfig',
    'ConfigurationManager',
    'ValidationLevel',
    'FallbackMode',
    'get_config_manager',
    'get_migration_config'
]