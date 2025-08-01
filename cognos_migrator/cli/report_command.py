"""
Report Migration Command Handler

Handles migrate-report command.
Follows Single Responsibility Principle.
"""

from typing import Any
from .base_command import BaseCommandHandler


class ReportMigrationCommandHandler(BaseCommandHandler):
    """Handler for migrate-report command"""
    
    def execute(self, args: Any) -> bool:
        """Execute migrate-report command"""
        self.logger.info(f"Migrating report {args.report_id}...")
        
        try:
            # Parse validation config
            validation_config = self.config_manager.parse_validation_config(
                getattr(args, 'validation_config', None)
            )
            
            # Execute migration
            enhanced_main = self.lazy_imports.get_enhanced_main()
            result = enhanced_main['migrate_report'](
                report_id=args.report_id,
                output_path=args.output_path,
                cognos_url=args.cognos_url,
                session_key=args.session_key,
                enable_enhanced_validation=getattr(args, 'enable_enhanced_validation', False),
                validation_config=validation_config
            )
            
            # Display results
            self.output_formatter.print_migration_results(result, False)
            
            return result['success']
            
        except Exception as e:
            self.logger.error(f"Report migration failed: {e}")
            print(f"\nError: {e}")
            return False