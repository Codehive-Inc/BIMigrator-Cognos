"""Configuration management for Cognos to BI Migrator.

Simplified for explicit session-based migration without .env dependencies.
"""
from dataclasses import dataclass
from typing import Optional

__all__ = ['CognosConfig', 'MigrationConfig']


@dataclass
class CognosConfig:
    """Configuration for Cognos Analytics connection."""
    base_url: str
    auth_key: str
    auth_value: Optional[str] = None
    base_auth_token: Optional[str] = None
    session_timeout: int = 3600
    max_retries: int = 3
    request_timeout: int = 30
    username: Optional[str] = None
    password: Optional[str] = None
    namespace: Optional[str] = None


@dataclass
class MigrationConfig:
    """Configuration for migration process."""
    output_directory: str = "output"
    template_directory: str = "templates"
    preserve_structure: bool = True
    include_metadata: bool = True
    generate_documentation: bool = True
    # LLM service configuration
    llm_service_url: Optional[str] = None
    llm_service_api_key: Optional[str] = None
    llm_service_enabled: bool = False