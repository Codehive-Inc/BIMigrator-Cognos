"""
Configuration system for enhanced migration features
"""

# Import original config classes for backward compatibility
# Temporarily disable to avoid circular import - use enhanced config instead
# from ..config import MigrationConfig, CognosConfig
from .fallback_config import EnhancedMigrationConfig as MigrationConfig
from dataclasses import dataclass

@dataclass
class CognosConfig:
    """Temporary config class to avoid circular import"""
    base_url: str
    auth_key: str
    auth_value: str = None
    base_auth_token: str = None
    session_timeout: int = 3600
    max_retries: int = 3
    request_timeout: int = 30
    username: str = None
    password: str = None
    namespace: str = None

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