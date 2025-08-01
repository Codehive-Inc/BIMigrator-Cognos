"""
Argument Parser Factory for CLI

Creates and configures argument parsers for different commands.
Follows Single Responsibility Principle.
"""

import argparse


class ArgumentParserFactory:
    """Factory for creating argument parsers"""
    
    @staticmethod
    def create_main_parser() -> argparse.ArgumentParser:
        """Create main argument parser"""
        parser = argparse.ArgumentParser(
            prog='bimigrator-enhanced',
            description='Enhanced BIMigrator-Cognos CLI with validation framework',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Test connection
  %(prog)s test-connection --cognos-url http://server:9300/api/v1 --session-key "CAM..."
  
  # Migrate module with validation
  %(prog)s migrate-module --module-id iMODULE123 --output-path ./output --cognos-url http://server:9300/api/v1 --session-key "CAM..."
  
  # Launch dashboard
  %(prog)s dashboard --port 5000
"""
        )
        
        # Global options
        parser.add_argument('--config-file', help='Path to configuration file (JSON format)')
        parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
        parser.add_argument('--debug', action='store_true', help='Enable debug output')
        
        return parser
    
    @staticmethod
    def add_test_connection_parser(subparsers):
        """Add test-connection command parser"""
        parser = subparsers.add_parser('test-connection', help='Test Cognos connection with validation framework')
        parser.add_argument('--cognos-url', required=True, help='Cognos API URL')
        parser.add_argument('--session-key', required=True, help='Cognos session key')
        parser.add_argument('--enable-validation', action='store_true', help='Enable validation framework testing')
        return parser
    
    @staticmethod
    def add_migrate_module_parser(subparsers):
        """Add migrate-module command parser"""
        parser = subparsers.add_parser('migrate-module', help='Migrate a Cognos module with enhanced validation')
        parser.add_argument('--module-id', required=True, help='Cognos module ID')
        parser.add_argument('--output-path', required=True, help='Output directory path')
        parser.add_argument('--cognos-url', required=True, help='Cognos API URL')
        parser.add_argument('--session-key', required=True, help='Cognos session key')
        parser.add_argument('--folder-id', help='Optional folder ID')
        parser.add_argument('--enable-enhanced-validation', action='store_true', help='Enable enhanced validation framework')
        parser.add_argument('--validation-config', help='JSON string with validation configuration')
        parser.add_argument('--enable-websocket', action='store_true', help='Enable WebSocket progress tracking')
        parser.add_argument('--websocket-url', default='ws://localhost:8765', help='WebSocket URL for progress tracking')
        parser.add_argument('--include-performance-metrics', action='store_true', help='Include performance metrics in output')
        parser.add_argument('--error-log-path', help='Path to error log file')
        parser.add_argument('--dry-run', action='store_true', help='Perform validation only without actual migration')
        return parser
    
    @staticmethod
    def add_migrate_report_parser(subparsers):
        """Add migrate-report command parser"""
        parser = subparsers.add_parser('migrate-report', help='Migrate a single Cognos report')
        parser.add_argument('--report-id', required=True, help='Cognos report ID')
        parser.add_argument('--output-path', required=True, help='Output directory path')
        parser.add_argument('--cognos-url', required=True, help='Cognos API URL')
        parser.add_argument('--session-key', required=True, help='Cognos session key')
        parser.add_argument('--enable-enhanced-validation', action='store_true', help='Enable enhanced validation framework')
        parser.add_argument('--validation-config', help='JSON string with validation configuration')
        return parser