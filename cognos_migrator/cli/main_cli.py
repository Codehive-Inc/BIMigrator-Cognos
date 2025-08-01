"""
Main CLI Controller

Main controller that orchestrates the CLI system.
Follows Dependency Inversion Principle.
"""

import sys
import logging
from typing import List
from .lazy_imports import LazyImportManager
from .config_manager import ConfigManager
from .output_formatter import OutputFormatter
from .command_registry import CommandRegistry
from .argument_parser import ArgumentParserFactory
from .parser_utils import ParserUtils
from .connection_command import ConnectionCommandHandler
from .module_command import ModuleMigrationCommandHandler
from .report_command import ReportMigrationCommandHandler
from .postprocess_command import PostProcessCommandHandler
from .dashboard_command import DashboardCommandHandler
from .batch_command import BatchMigrationCommandHandler
from .validation_command import ValidationCommandHandler
from .info_commands import InfoCommandsHandler


class EnhancedCLI:
    """Main CLI controller"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.lazy_imports = LazyImportManager()
        self.config_manager = ConfigManager(self.logger)
        self.output_formatter = OutputFormatter()
        self.command_registry = CommandRegistry()
        self.parser = self._create_parser()
        self._register_commands()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('enhanced_cli')
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger
    
    def _create_parser(self):
        """Create argument parser"""
        parser = ArgumentParserFactory.create_main_parser()
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Add command parsers
        ArgumentParserFactory.add_test_connection_parser(subparsers)
        ArgumentParserFactory.add_migrate_module_parser(subparsers)
        ArgumentParserFactory.add_migrate_report_parser(subparsers)
        ParserUtils.add_post_process_parser(subparsers)
        ParserUtils.add_dashboard_parser(subparsers)
        ParserUtils.add_batch_migrate_parser(subparsers)
        ParserUtils.add_validate_module_parser(subparsers)
        ParserUtils.add_info_parsers(subparsers)
        
        return parser
    
    def _register_commands(self):
        """Register command handlers"""
        # Create info handler instance
        info_handler = InfoCommandsHandler(
            self.lazy_imports, self.config_manager, self.output_formatter, self.logger
        )
        
        # Register standard commands
        handlers = {
            'test_connection': ConnectionCommandHandler,
            'migrate_module': ModuleMigrationCommandHandler,
            'migrate_report': ReportMigrationCommandHandler,
            'post_process': PostProcessCommandHandler,
            'dashboard': DashboardCommandHandler,
            'batch_migrate': BatchMigrationCommandHandler,
            'validate_module': ValidationCommandHandler
        }
        
        for name, handler_class in handlers.items():
            handler = handler_class(
                self.lazy_imports, self.config_manager, 
                self.output_formatter, self.logger
            )
            self.command_registry.register_command(name, handler)
        
        # Register info commands separately (they use different execute methods)
        class ListStrategiesHandler:
            def execute(self, args): return info_handler.execute_list_strategies(args)
        
        class ShowConfigHandler:
            def execute(self, args): return info_handler.execute_show_config(args)
        
        self.command_registry.register_command('list_strategies', ListStrategiesHandler())
        self.command_registry.register_command('show_config', ShowConfigHandler())
    
    def run(self, argv: List[str] = None) -> bool:
        """Run the CLI with given arguments"""
        args = self.parser.parse_args(argv)
        
        # Setup logging level
        if args.debug:
            self.logger.setLevel(logging.DEBUG)
        elif args.verbose:
            self.logger.setLevel(logging.INFO)
        
        # Load config file if provided
        config = {}
        if args.config_file:
            config = self.config_manager.load_config_file(args.config_file)
        
        # Setup environment
        websocket_url = self.config_manager.setup_environment(vars(args), config)
        
        # Execute command
        if not args.command:
            self.parser.print_help()
            return False
        
        if not self.command_registry.has_command(args.command):
            self.logger.error(f"Unknown command: {args.command}")
            return False
        
        try:
            return self.command_registry.execute_command(args.command, args)
        except Exception as e:
            self.logger.error(f"Command failed: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
            return False