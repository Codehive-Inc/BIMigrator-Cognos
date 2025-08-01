"""
Configuration Manager for CLI

Handles configuration loading, validation, and environment setup.
Follows Single Responsibility Principle.
"""

import json
import os
import logging
from typing import Dict, Any
from pathlib import Path


class ConfigManager:
    """Manages configuration for CLI operations"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def load_config_file(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                self.logger.warning(f"Config file not found: {config_path}")
                return {}
            
            with open(config_file, 'r') as f:
                config = json.load(f)
                self.logger.info(f"Loaded configuration from {config_path}")
                return config
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in config file: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Failed to load config file: {e}")
            return {}
    
    def parse_validation_config(self, config_str: str) -> Dict[str, Any]:
        """Parse validation config from JSON string"""
        if not config_str:
            return {}
        
        try:
            return json.loads(config_str)
        except json.JSONDecodeError:
            self.logger.error("Invalid validation config JSON")
            return {}
    
    def setup_environment(self, args: Dict[str, Any], config: Dict[str, Any]):
        """Setup environment variables from configuration"""
        # Set up validation environment variables
        validation_config = config.get('validation_config', {})
        if validation_config.get('validation_enabled', False):
            os.environ['USE_ENHANCED_CONVERTER'] = 'true'
            os.environ['USE_ENHANCED_MQUERY_CONVERTER'] = 'true'
            os.environ['ENABLE_VALIDATION_FRAMEWORK'] = 'true'
            
            if 'validation_strictness' in validation_config:
                os.environ['VALIDATION_STRICTNESS'] = validation_config['validation_strictness']
            
            if validation_config.get('enable_select_star_fallback', False):
                os.environ['ENABLE_SELECT_STAR_FALLBACK'] = 'true'
        
        # Set up WebSocket if enabled
        websocket_config = config.get('websocket_config', {})
        if args.get('enable_websocket') or websocket_config.get('enabled', False):
            websocket_url = args.get('websocket_url') or websocket_config.get('url', 'ws://localhost:8765')
            self.logger.info(f"WebSocket progress tracking configured for {websocket_url}")
            return websocket_url
        
        return None