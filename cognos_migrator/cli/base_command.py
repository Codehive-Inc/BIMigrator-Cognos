"""
Base Command Handler

Base class for all command handlers.
Follows Dependency Inversion Principle.
"""

import logging
from typing import Any
from .command_registry import CommandHandler
from .lazy_imports import LazyImportManager
from .config_manager import ConfigManager
from .output_formatter import OutputFormatter


class BaseCommandHandler(CommandHandler):
    """Base class for command handlers"""
    
    def __init__(self, 
                 lazy_imports: LazyImportManager,
                 config_manager: ConfigManager,
                 output_formatter: OutputFormatter,
                 logger: logging.Logger):
        self.lazy_imports = lazy_imports
        self.config_manager = config_manager
        self.output_formatter = output_formatter
        self.logger = logger
    
    def setup_websocket(self, args: Any, websocket_url: str = None):
        """Setup WebSocket if enabled"""
        if getattr(args, 'enable_websocket', False) and websocket_url:
            ws_client = self.lazy_imports.get_websocket_client()
            ws_client['configure_url'](websocket_url)
            
            if hasattr(args, 'module_id'):
                ws_client['set_task_info'](f"module_{args.module_id}", 100)
            elif hasattr(args, 'report_id'):
                ws_client['set_task_info'](f"report_{args.report_id}", 100)
            
            self.logger.info(f"WebSocket configured for {websocket_url}")
    
    def handle_error_logging(self, args: Any, result: dict):
        """Handle error logging if specified"""
        if hasattr(args, 'error_log_path') and args.error_log_path and not result['success']:
            self.output_formatter.write_error_log(args.error_log_path, result)