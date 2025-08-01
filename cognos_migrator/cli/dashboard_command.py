"""
Dashboard Command Handler

Handles dashboard command.
Follows Single Responsibility Principle.
"""

from typing import Any
from .base_command import BaseCommandHandler


class DashboardCommandHandler(BaseCommandHandler):
    """Handler for dashboard command"""
    
    def execute(self, args: Any) -> bool:
        """Execute dashboard command"""
        self.logger.info(f"Launching quality dashboard on {args.host}:{args.port}...")
        
        try:
            # Create and run dashboard
            create_dashboard = self.lazy_imports.get_dashboard_factory()
            dashboard = create_dashboard(db_path=args.db_path)
            
            print(f"\n✓ Dashboard running at http://{args.host}:{args.port}")
            print("Press Ctrl+C to stop")
            
            try:
                dashboard.app.run(host=args.host, port=args.port, debug=False)
            except KeyboardInterrupt:
                print("\n✓ Dashboard stopped")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Dashboard failed: {e}")
            print(f"\nError: {e}")
            return False