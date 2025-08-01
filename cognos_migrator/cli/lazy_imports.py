"""
Lazy Import Manager for CLI

Handles all lazy imports to avoid circular dependencies.
Follows Single Responsibility Principle.
"""

from typing import Dict, Any, Optional


class LazyImportManager:
    """Manages lazy imports for CLI to avoid circular dependencies"""
    
    def __init__(self):
        self._enhanced_main: Optional[Dict[str, Any]] = None
        self._dashboard: Optional[Any] = None
        self._websocket_client: Optional[Dict[str, Any]] = None
    
    def get_enhanced_main(self) -> Dict[str, Any]:
        """Get enhanced main functions"""
        if self._enhanced_main is None:
            from cognos_migrator.enhanced_main import (
                test_cognos_connection_enhanced,
                migrate_module_with_enhanced_validation,
                migrate_single_report_with_enhanced_validation,
                post_process_module_with_enhanced_validation
            )
            self._enhanced_main = {
                'test_connection': test_cognos_connection_enhanced,
                'migrate_module': migrate_module_with_enhanced_validation,
                'migrate_report': migrate_single_report_with_enhanced_validation,
                'post_process': post_process_module_with_enhanced_validation
            }
        return self._enhanced_main
    
    def get_dashboard_factory(self) -> Any:
        """Get dashboard factory function"""
        if self._dashboard is None:
            from cognos_migrator.dashboard.quality_dashboard import create_standalone_dashboard
            self._dashboard = create_standalone_dashboard
        return self._dashboard
    
    def get_websocket_client(self) -> Dict[str, Any]:
        """Get WebSocket client functions"""
        if self._websocket_client is None:
            from cognos_migrator.common.websocket_client import (
                set_websocket_post_function,
                set_task_info,
                set_websocket_url as configure_websocket_url
            )
            self._websocket_client = {
                'set_post_function': set_websocket_post_function,
                'set_task_info': set_task_info,
                'configure_url': configure_websocket_url
            }
        return self._websocket_client