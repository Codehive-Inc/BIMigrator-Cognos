"""
Module Migration Command Handler

Handles migrate-module command.
Follows Single Responsibility Principle.
"""

from typing import Any
from .base_command import BaseCommandHandler


class ModuleMigrationCommandHandler(BaseCommandHandler):
    """Handler for migrate-module command"""
    
    def execute(self, args: Any) -> bool:
        """Execute migrate-module command"""
        self.logger.info(f"Migrating module {args.module_id}...")
        
        try:
            # Parse validation config
            validation_config = self.config_manager.parse_validation_config(args.validation_config)
            
            # Setup WebSocket if enabled
            if args.enable_websocket:
                self.setup_websocket(args, args.websocket_url)
            
            # Execute migration
            enhanced_main = self.lazy_imports.get_enhanced_main()
            result = enhanced_main['migrate_module'](
                module_id=args.module_id,
                output_path=args.output_path,
                cognos_url=args.cognos_url,
                session_key=args.session_key,
                folder_id=getattr(args, 'folder_id', None),
                enable_enhanced_validation=args.enable_enhanced_validation,
                validation_config=validation_config
            )
            
            # Display results
            self.output_formatter.print_migration_results(
                result, 
                getattr(args, 'include_performance_metrics', False)
            )
            
            # Handle error logging
            self.handle_error_logging(args, result)
            
            return result['success']
            
        except Exception as e:
            self.logger.error(f"Module migration failed: {e}")
            print(f"\nError: {e}")
            return False