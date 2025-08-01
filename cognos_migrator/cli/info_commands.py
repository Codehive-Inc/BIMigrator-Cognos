"""
Info Commands Handler

Handles list-strategies and show-validation-config commands.
Follows Single Responsibility Principle.
"""

import json
from typing import Any
from .base_command import BaseCommandHandler


class InfoCommandsHandler(BaseCommandHandler):
    """Handler for information commands"""
    
    def execute_list_strategies(self, args: Any) -> bool:
        """Execute list-strategies command"""
        print("\n=== Available Validation Strategies ===\n")
        
        strategies = {
            'primary': 'Direct LLM conversion without validation',
            'enhanced': 'LLM conversion with pre/post validation',
            'fallback_level_1': 'Simplified conversion attempt',
            'fallback_level_2': 'Template-based conversion',
            'safe_fallback': 'Guaranteed safe expressions (BLANK(), SUM())',
            'select_star': 'SELECT * fallback for M-Query (100% success)'
        }
        
        for name, description in strategies.items():
            print(f"  {name}: {description}")
        
        print("\n=== Validation Strictness Levels ===\n")
        print("  low: Basic syntax validation only")
        print("  medium: Syntax + semantic validation (default)")
        print("  high: Comprehensive validation with type checking")
        
        return True
    
    def execute_show_config(self, args: Any) -> bool:
        """Execute show-validation-config command"""
        print("\n=== Validation Configuration Options ===\n")
        
        config_template = {
            "validation_config": {
                "validation_enabled": True,
                "validation_strictness": "medium | high | low",
                "fallback_enabled": True,
                "enable_select_star_fallback": True,
                "fallback_threshold": 0.8,
                "max_fallback_attempts": 3,
                "enable_post_validation": True,
                "enable_pre_validation": True
            },
            "websocket_config": {
                "enabled": False,
                "url": "ws://localhost:8765",
                "progress_interval": 1000
            },
            "reporting_config": {
                "generate_html": True,
                "generate_json": True,
                "generate_comprehensive": True,
                "include_performance_metrics": True
            },
            "performance_config": {
                "enable_caching": True,
                "cache_size": 1000,
                "parallel_validation": False,
                "batch_size": 10
            }
        }
        
        print(json.dumps(config_template, indent=2))
        
        print("\n=== Environment Variables ===\n")
        print("  USE_ENHANCED_CONVERTER=true|false")
        print("  USE_ENHANCED_MQUERY_CONVERTER=true|false")
        print("  ENABLE_VALIDATION_FRAMEWORK=true|false")
        print("  VALIDATION_STRICTNESS=low|medium|high")
        print("  ENABLE_SELECT_STAR_FALLBACK=true|false")
        print("  DAX_API_URL=http://localhost:8080")
        
        return True