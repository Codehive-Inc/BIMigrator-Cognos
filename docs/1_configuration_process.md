# Configuration Process

## Overview

The configuration process loads all necessary settings for the migration tool from environment variables and configuration files.

## Process Flow

1. **Initialize ConfigManager**
   - Load `.env` file if present
   - Set up default configuration values

2. **Load Cognos Configuration**
   - Base URL for Cognos Analytics API
   - Authentication credentials
   - Namespace ID
   - Connection timeout settings

3. **Load Migration Configuration**
   - Template directory for Power BI templates
   - Output directory for migration results
   - LLM service configuration
     - URL
     - API key
     - Enabled/disabled flag

## Key Components

### ConfigManager Class

The `ConfigManager` class in `config.py` is responsible for loading and managing configuration settings:

```python
class ConfigManager:
    def __init__(self):
        # Load environment variables from .env file if present
        load_dotenv()
        
    def get_cognos_config(self) -> CognosConfig:
        # Create and return Cognos configuration
        
    def get_migration_config(self) -> MigrationConfig:
        # Create and return migration configuration
```

### Configuration Classes

- **CognosConfig**: Contains Cognos Analytics connection settings
- **MigrationConfig**: Contains migration tool settings

## Environment Variables

The following environment variables can be used to configure the tool:

- `COGNOS_BASE_URL`: Base URL for Cognos Analytics API
- `COGNOS_USERNAME`: Username for Cognos authentication
- `COGNOS_PASSWORD`: Password for Cognos authentication
- `COGNOS_NAMESPACE`: Cognos namespace ID
- `TEMPLATE_DIRECTORY`: Directory containing Power BI templates
- `OUTPUT_DIRECTORY`: Directory for migration output
- `LLM_SERVICE_URL`: URL for the LLM service API
- `LLM_SERVICE_API_KEY`: API key for the LLM service
- `LLM_SERVICE_ENABLED`: Flag to enable/disable LLM service

## Usage

The configuration is loaded at the start of the migration process:

```python
def load_config():
    """Load migration configuration"""
    config_manager = ConfigManager()
    return config_manager.get_migration_config()
```
