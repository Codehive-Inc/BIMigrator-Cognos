"""
Validation Command Handler

Handles validate-module command.
Follows Single Responsibility Principle.
"""

import json
from typing import Any
from .base_command import BaseCommandHandler


class ValidationCommandHandler(BaseCommandHandler):
    """Handler for validate-module command"""
    
    def execute(self, args: Any) -> bool:
        """Execute validate-module command"""
        self.logger.info(f"Validating module {args.module_id}...")
        
        try:
            # Perform dry-run migration with validation
            enhanced_main = self.lazy_imports.get_enhanced_main()
            result = enhanced_main['migrate_module'](
                module_id=args.module_id,
                output_path="/tmp/validation_test",  # Temporary path
                cognos_url=args.cognos_url,
                session_key=args.session_key,
                enable_enhanced_validation=True,
                validation_config={'dry_run': True}
            )
            
            # Display validation results
            self.output_formatter.print_validation_results(result, args.module_id)
            
            # Save report if requested
            if hasattr(args, 'output_report') and args.output_report:
                self._save_validation_report(args.output_report, result)
            
            # Return success based on validation success rate
            validation_results = result.get('validation_results', {})
            success_rate = validation_results.get('validation_success_rate', 0)
            return success_rate > 0.8
            
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            print(f"\nError: {e}")
            return False
    
    def _save_validation_report(self, report_path: str, result: dict):
        """Save validation report to file"""
        try:
            with open(report_path, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\n✓ Validation report saved to {report_path}")
        except Exception as e:
            self.logger.error(f"Failed to save validation report: {e}")