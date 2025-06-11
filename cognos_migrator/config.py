"""
Configuration management for Cognos to BI Migrator
"""

import os
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class CognosConfig:
    """Configuration for Cognos Analytics connection"""
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
    """Configuration for migration process"""
    output_directory: str = "output"
    template_directory: str = "bimigrator/templates"
    preserve_structure: bool = True
    include_metadata: bool = True
    generate_documentation: bool = True


class ConfigManager:
    """Manages configuration loading and validation"""
    
    def __init__(self, env_file: Optional[str] = None):
        self.env_file = env_file or ".env"
        self._load_environment()
    
    def load_config(self) -> MigrationConfig:
        """Load complete configuration"""
        return self.get_migration_config()
    
    def _load_environment(self):
        """Load environment variables from .env file"""
        if os.path.exists(self.env_file):
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
    
    def get_cognos_config(self) -> CognosConfig:
        """Get Cognos configuration from environment"""
        base_url = os.getenv('COGNOS_BASE_URL') or os.getenv('BASE_URL')
        if not base_url:
            raise ValueError("COGNOS_BASE_URL not found in environment variables")
        
        # Extract auth key and values from environment
        auth_key = os.getenv('COGNOS_AUTH_KEY', 'IBM-BA-Authorization')
        auth_value = os.getenv('COGNOS_AUTH_VALUE') or os.getenv('VALUE')
        base_auth_token = os.getenv('COGNOS_BASE_AUTH_TOKEN')
        
        # Check for authentication credentials
        if not base_auth_token and not auth_value:
            raise ValueError("Either COGNOS_BASE_AUTH_TOKEN or COGNOS_AUTH_VALUE must be provided")
        
        return CognosConfig(
            base_url=base_url,
            auth_key=auth_key,
            auth_value=auth_value,
            base_auth_token=base_auth_token,
            session_timeout=int(os.getenv('SESSION_TIMEOUT', '3600')),
            max_retries=int(os.getenv('MAX_RETRIES', '3')),
            request_timeout=int(os.getenv('REQUEST_TIMEOUT', '30')),
            username=os.getenv('COGNOS_USERNAME'),
            password=os.getenv('COGNOS_PASSWORD'),
            namespace=os.getenv('COGNOS_NAMESPACE')
        )
    
    def get_migration_config(self) -> MigrationConfig:
        """Get migration configuration"""
        return MigrationConfig(
            output_directory=os.getenv('OUTPUT_DIR', 'output'),
            template_directory=os.getenv('TEMPLATE_DIR', 'bimigrator/templates'),
            preserve_structure=os.getenv('PRESERVE_STRUCTURE', 'true').lower() == 'true',
            include_metadata=os.getenv('INCLUDE_METADATA', 'true').lower() == 'true',
            generate_documentation=os.getenv('GENERATE_DOCS', 'true').lower() == 'true'
        )
    
    def validate_config(self) -> bool:
        """Validate configuration settings"""
        try:
            cognos_config = self.get_cognos_config()
            migration_config = self.get_migration_config()
            
            # Validate Cognos config
            if not cognos_config.base_url.startswith(('http://', 'https://')):
                raise ValueError("Invalid BASE_URL format")
            
            # Validate migration config
            template_path = Path(migration_config.template_directory)
            if not template_path.exists():
                raise ValueError(f"Template directory not found: {template_path}")
            
            return True
        except Exception as e:
            print(f"Configuration validation failed: {e}")
            return False
