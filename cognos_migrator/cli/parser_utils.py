"""
Additional Parser Utilities for CLI

Extends ArgumentParserFactory with remaining command parsers.
Follows Open/Closed Principle.
"""

import argparse


class ParserUtils:
    """Additional parser utilities"""
    
    @staticmethod
    def add_post_process_parser(subparsers):
        """Add post-process command parser"""
        parser = subparsers.add_parser('post-process', help='Post-process a migrated module')
        parser.add_argument('--module-id', required=True, help='Cognos module ID')
        parser.add_argument('--output-path', required=True, help='Output directory path')
        parser.add_argument('--cognos-url', required=True, help='Cognos API URL')
        parser.add_argument('--session-key', required=True, help='Cognos session key')
        parser.add_argument('--report-ids', help='Comma-separated list of successful report IDs')
        parser.add_argument('--generate-quality-report', action='store_true', help='Generate quality report')
        return parser
    
    @staticmethod
    def add_dashboard_parser(subparsers):
        """Add dashboard command parser"""
        parser = subparsers.add_parser('dashboard', help='Launch migration quality dashboard')
        parser.add_argument('--port', type=int, default=5000, help='Dashboard port (default: 5000)')
        parser.add_argument('--db-path', default='./migration_metrics.db', help='Database path for metrics')
        parser.add_argument('--host', default='127.0.0.1', help='Dashboard host (default: 127.0.0.1)')
        return parser
    
    @staticmethod
    def add_batch_migrate_parser(subparsers):
        """Add batch-migrate command parser"""
        parser = subparsers.add_parser('batch-migrate', help='Batch migrate multiple modules')
        parser.add_argument('--modules-file', required=True, help='File containing module IDs (one per line)')
        parser.add_argument('--output-base-path', required=True, help='Base output directory')
        parser.add_argument('--cognos-url', required=True, help='Cognos API URL')
        parser.add_argument('--session-key', required=True, help='Cognos session key')
        parser.add_argument('--enable-enhanced-validation', action='store_true', help='Enable enhanced validation framework')
        parser.add_argument('--parallel-workers', type=int, default=1, help='Number of parallel workers')
        parser.add_argument('--continue-on-error', action='store_true', help='Continue processing on errors')
        return parser
    
    @staticmethod
    def add_validate_module_parser(subparsers):
        """Add validate-module command parser"""
        parser = subparsers.add_parser('validate-module', help='Validate module without migration')
        parser.add_argument('--module-id', required=True, help='Cognos module ID')
        parser.add_argument('--cognos-url', required=True, help='Cognos API URL')
        parser.add_argument('--session-key', required=True, help='Cognos session key')
        parser.add_argument('--output-report', help='Output validation report path')
        return parser
    
    @staticmethod
    def add_info_parsers(subparsers):
        """Add information command parsers"""
        subparsers.add_parser('list-strategies', help='List available validation strategies')
        subparsers.add_parser('show-validation-config', help='Show validation configuration options')
        return subparsers