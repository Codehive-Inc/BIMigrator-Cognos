"""
Connection Command Handler

Handles test-connection command.
Follows Single Responsibility Principle.
"""

from typing import Any
from .base_command import BaseCommandHandler


class ConnectionCommandHandler(BaseCommandHandler):
    """Handler for test-connection command"""
    
    def execute(self, args: Any) -> bool:
        """Execute test-connection command"""
        self.logger.info("Testing Cognos connection...")
        
        try:
            enhanced_main = self.lazy_imports.get_enhanced_main()
            result = enhanced_main['test_connection'](
                cognos_url=args.cognos_url,
                session_key=args.session_key,
                enable_validation=args.enable_validation
            )
            
            # Display results
            self.output_formatter.print_connection_results(result, args.enable_validation)
            
            return result.get('connection_valid', False)
            
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            print(f"\nError: {e}")
            return False