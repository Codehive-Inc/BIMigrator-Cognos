"""
Post-Process Command Handler

Handles post-process command.
Follows Single Responsibility Principle.
"""

from typing import Any
from .base_command import BaseCommandHandler


class PostProcessCommandHandler(BaseCommandHandler):
    """Handler for post-process command"""
    
    def execute(self, args: Any) -> bool:
        """Execute post-process command"""
        self.logger.info(f"Post-processing module {args.module_id}...")
        
        try:
            # Parse report IDs
            report_ids = None
            if hasattr(args, 'report_ids') and args.report_ids:
                report_ids = args.report_ids.split(',')
            
            # Execute post-processing
            enhanced_main = self.lazy_imports.get_enhanced_main()
            result = enhanced_main['post_process'](
                module_id=args.module_id,
                output_path=args.output_path,
                cognos_url=args.cognos_url,
                session_key=args.session_key,
                successful_report_ids=report_ids,
                generate_quality_report=getattr(args, 'generate_quality_report', False)
            )
            
            # Display results
            self.output_formatter.print_post_process_results(
                result, 
                getattr(args, 'generate_quality_report', False)
            )
            
            return result['success']
            
        except Exception as e:
            self.logger.error(f"Post-processing failed: {e}")
            print(f"\nError: {e}")
            return False