"""Utility for loading environment variables for the licensing system."""

import os
import logging
from pathlib import Path
from typing import Optional, Dict

# Configure logging
logger = logging.getLogger(__name__)


def load_env_file(env_file: Optional[str] = None) -> None:
    """Load environment variables from a .env file.
    
    Args:
        env_file: Path to the .env file. If None, will look for .env in the project root.
    """
    if env_file is None:
        # Try to find .env in the project root
        project_root = Path(__file__).resolve().parent.parent.parent
        env_file = project_root / '.env'
    
    if not os.path.isfile(env_file):
        logger.warning(f"Environment file not found: {env_file}")
        return
    
    logger.info(f"Loading environment variables from: {env_file}")
    
    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse key-value pairs
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value and value[0] == value[-1] and value[0] in ('"', "'"):
                        value = value[1:-1]
                    
                    # Set environment variable if not already set
                    if key and key not in os.environ:
                        os.environ[key] = value
                        logger.debug(f"Set environment variable: {key}")
    except Exception as e:
        logger.error(f"Error loading environment variables: {str(e)}")


def get_env_var(name: str, default: Optional[str] = None) -> Optional[str]:
    """Get an environment variable with an optional default value.
    
    Args:
        name: Name of the environment variable
        default: Default value if the variable is not set
        
    Returns:
        Value of the environment variable or default
    """
    return os.environ.get(name, default)


def get_db_config() -> Dict[str, str]:
    """Get database configuration from environment variables.
    
    Returns:
        Dictionary with database configuration
    """
    return {
        'host': get_env_var('BIMIGRATOR_DB_HOST', 'localhost'),
        'port': get_env_var('BIMIGRATOR_DB_PORT', '5432'),
        'dbname': get_env_var('BIMIGRATOR_DB_NAME', 'bimigrator_db'),
        'user': get_env_var('BIMIGRATOR_DB_USER', 'app_user'),
        'password': get_env_var('BIMIGRATOR_DB_PASSWORD', ''),
    }


# Automatically load environment variables when the module is imported
load_env_file()
