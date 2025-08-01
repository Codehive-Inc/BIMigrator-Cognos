#!/usr/bin/env python3
"""
Enhanced CLI wrapper for BIMigrator-Cognos with validation framework

This module provides a comprehensive command-line interface for the enhanced
migration system without modifying the core enhanced_main.py module.
"""

import argparse
import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

# Import enhanced_main functions
from cognos_migrator.enhanced_main import (
    test_cognos_connection_enhanced,
    migrate_module_with_enhanced_validation,
    migrate_single_report_with_enhanced_validation,
    post_process_module_with_enhanced_validation
)

# Import dashboard
from cognos_migrator.dashboard.quality_dashboard import create_standalone_dashboard

# Import WebSocket client for progress tracking
from cognos_migrator.common.websocket_client import (
    set_websocket_post_function,
    set_task_info,
    set_websocket_url as configure_websocket_url
)


class EnhancedCLI:
    """Enhanced command-line interface for BIMigrator-Cognos"""
    
    def __init__(self):
        self.parser = self._create_parser()
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('enhanced_cli')
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger
        
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser with all commands"""
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
        parser.add_argument(
            '--config-file',
            help='Path to configuration file (JSON format)'
        )
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose output'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug output'
        )
        
        # Create subcommands
        subparsers = parser.add_subparsers(
            dest='command',
            help='Available commands'
        )
        
        # Add all command parsers
        self._add_test_connection_parser(subparsers)
        self._add_migrate_module_parser(subparsers)
        self._add_migrate_report_parser(subparsers)
        self._add_post_process_parser(subparsers)
        self._add_dashboard_parser(subparsers)
        self._add_batch_migrate_parser(subparsers)
        self._add_validate_module_parser(subparsers)
        self._add_list_strategies_parser(subparsers)
        self._add_show_config_parser(subparsers)
        
        return parser
    
    def _add_test_connection_parser(self, subparsers):
        """Add test-connection command"""
        parser = subparsers.add_parser(
            'test-connection',
            help='Test Cognos connection with validation framework'
        )
        parser.add_argument(
            '--cognos-url',
            required=True,
            help='Cognos API URL'
        )
        parser.add_argument(
            '--session-key',
            required=True,
            help='Cognos session key'
        )
        parser.add_argument(
            '--enable-validation',
            action='store_true',
            help='Enable validation framework testing'
        )
        
    def _add_migrate_module_parser(self, subparsers):
        """Add migrate-module command"""
        parser = subparsers.add_parser(
            'migrate-module',
            help='Migrate a Cognos module with enhanced validation'
        )
        parser.add_argument(
            '--module-id',
            required=True,
            help='Cognos module ID'
        )
        parser.add_argument(
            '--output-path',
            required=True,
            help='Output directory path'
        )
        parser.add_argument(
            '--cognos-url',
            required=True,
            help='Cognos API URL'
        )
        parser.add_argument(
            '--session-key',
            required=True,
            help='Cognos session key'
        )
        parser.add_argument(
            '--folder-id',
            help='Optional folder ID'
        )
        parser.add_argument(
            '--enable-enhanced-validation',
            action='store_true',
            help='Enable enhanced validation framework'
        )
        parser.add_argument(
            '--validation-config',
            help='JSON string with validation configuration'
        )
        parser.add_argument(
            '--enable-websocket',
            action='store_true',
            help='Enable WebSocket progress tracking'
        )
        parser.add_argument(
            '--websocket-url',
            default='ws://localhost:8765',
            help='WebSocket URL for progress tracking'
        )
        parser.add_argument(
            '--include-performance-metrics',
            action='store_true',
            help='Include performance metrics in output'
        )
        parser.add_argument(
            '--error-log-path',
            help='Path to error log file'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform validation only without actual migration'
        )
        
    def _add_migrate_report_parser(self, subparsers):
        """Add migrate-report command"""
        parser = subparsers.add_parser(
            'migrate-report',
            help='Migrate a single Cognos report'
        )
        parser.add_argument(
            '--report-id',
            required=True,
            help='Cognos report ID'
        )
        parser.add_argument(
            '--output-path',
            required=True,
            help='Output directory path'
        )
        parser.add_argument(
            '--cognos-url',
            required=True,
            help='Cognos API URL'
        )
        parser.add_argument(
            '--session-key',
            required=True,
            help='Cognos session key'
        )
        parser.add_argument(
            '--enable-enhanced-validation',
            action='store_true',
            help='Enable enhanced validation framework'
        )
        parser.add_argument(
            '--validation-config',
            help='JSON string with validation configuration'
        )
        
    def _add_post_process_parser(self, subparsers):
        """Add post-process command"""
        parser = subparsers.add_parser(
            'post-process',
            help='Post-process a migrated module'
        )
        parser.add_argument(
            '--module-id',
            required=True,
            help='Cognos module ID'
        )
        parser.add_argument(
            '--output-path',
            required=True,
            help='Output directory path'
        )
        parser.add_argument(
            '--cognos-url',
            required=True,
            help='Cognos API URL'
        )
        parser.add_argument(
            '--session-key',
            required=True,
            help='Cognos session key'
        )
        parser.add_argument(
            '--report-ids',
            help='Comma-separated list of successful report IDs'
        )
        parser.add_argument(
            '--generate-quality-report',
            action='store_true',
            help='Generate quality report'
        )
        
    def _add_dashboard_parser(self, subparsers):
        """Add dashboard command"""
        parser = subparsers.add_parser(
            'dashboard',
            help='Launch migration quality dashboard'
        )
        parser.add_argument(
            '--port',
            type=int,
            default=5000,
            help='Dashboard port (default: 5000)'
        )
        parser.add_argument(
            '--db-path',
            default='./migration_metrics.db',
            help='Database path for metrics'
        )
        parser.add_argument(
            '--host',
            default='127.0.0.1',
            help='Dashboard host (default: 127.0.0.1)'
        )
        
    def _add_batch_migrate_parser(self, subparsers):
        """Add batch-migrate command"""
        parser = subparsers.add_parser(
            'batch-migrate',
            help='Batch migrate multiple modules'
        )
        parser.add_argument(
            '--modules-file',
            required=True,
            help='File containing module IDs (one per line)'
        )
        parser.add_argument(
            '--output-base-path',
            required=True,
            help='Base output directory'
        )
        parser.add_argument(
            '--cognos-url',
            required=True,
            help='Cognos API URL'
        )
        parser.add_argument(
            '--session-key',
            required=True,
            help='Cognos session key'
        )
        parser.add_argument(
            '--enable-enhanced-validation',
            action='store_true',
            help='Enable enhanced validation framework'
        )
        parser.add_argument(
            '--parallel-workers',
            type=int,
            default=1,
            help='Number of parallel workers'
        )
        parser.add_argument(
            '--continue-on-error',
            action='store_true',
            help='Continue processing on errors'
        )
        
    def _add_validate_module_parser(self, subparsers):
        """Add validate-module command"""
        parser = subparsers.add_parser(
            'validate-module',
            help='Validate module without migration'
        )
        parser.add_argument(
            '--module-id',
            required=True,
            help='Cognos module ID'
        )
        parser.add_argument(
            '--cognos-url',
            required=True,
            help='Cognos API URL'
        )
        parser.add_argument(
            '--session-key',
            required=True,
            help='Cognos session key'
        )
        parser.add_argument(
            '--output-report',
            help='Output validation report path'
        )
        
    def _add_list_strategies_parser(self, subparsers):
        """Add list-strategies command"""
        parser = subparsers.add_parser(
            'list-strategies',
            help='List available validation strategies'
        )
        
    def _add_show_config_parser(self, subparsers):
        """Add show-validation-config command"""
        parser = subparsers.add_parser(
            'show-validation-config',
            help='Show validation configuration options'
        )
        
    def _load_config_file(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load config file: {e}")
            return {}
    
    def _setup_environment(self, args, config: Dict[str, Any]):
        """Setup environment variables from config"""
        # Set up validation environment variables
        if config.get('validation_config', {}).get('validation_enabled', False):
            os.environ['USE_ENHANCED_CONVERTER'] = 'true'
            os.environ['USE_ENHANCED_MQUERY_CONVERTER'] = 'true'
            os.environ['ENABLE_VALIDATION_FRAMEWORK'] = 'true'
            
            if 'validation_strictness' in config['validation_config']:
                os.environ['VALIDATION_STRICTNESS'] = config['validation_config']['validation_strictness']
            
            if config['validation_config'].get('enable_select_star_fallback', False):
                os.environ['ENABLE_SELECT_STAR_FALLBACK'] = 'true'
        
        # Set up WebSocket if enabled
        if args.get('enable_websocket') or config.get('websocket_config', {}).get('enabled', False):
            websocket_url = args.get('websocket_url') or config.get('websocket_config', {}).get('url', 'ws://localhost:8765')
            configure_websocket_url(websocket_url)
            self.logger.info(f"WebSocket progress tracking enabled at {websocket_url}")
    
    def _parse_validation_config(self, config_str: str) -> Dict[str, Any]:
        """Parse validation config from JSON string"""
        try:
            return json.loads(config_str) if config_str else {}
        except json.JSONDecodeError:
            self.logger.error("Invalid validation config JSON")
            return {}
    
    def cmd_test_connection(self, args):
        """Handle test-connection command"""
        self.logger.info("Testing Cognos connection...")
        
        result = test_cognos_connection_enhanced(
            cognos_url=args.cognos_url,
            session_key=args.session_key,
            enable_validation=args.enable_validation
        )
        
        # Print results
        print(f"\nConnection Status: {'✓ Valid' if result['connection_valid'] else '✗ Invalid'}")
        
        if args.enable_validation:
            print("\nValidation Framework Status:")
            print(f"  - Framework Available: {'✓' if result['validation_framework_available'] else '✗'}")
            print(f"  - Fallback Strategy: {'✓' if result['fallback_strategy_available'] else '✗'}")
            print(f"  - Reporters: {'✓' if result['reporters_available'] else '✗'}")
            print(f"  - Enhanced Converters: {'✓' if result['enhanced_converters_available'] else '✗'}")
        
        if 'error' in result:
            print(f"\nError: {result['error']}")
            return False
        
        return True
    
    def cmd_migrate_module(self, args):
        """Handle migrate-module command"""
        self.logger.info(f"Migrating module {args.module_id}...")
        
        # Parse validation config
        validation_config = self._parse_validation_config(args.validation_config)
        
        # Setup WebSocket if enabled
        if args.enable_websocket:
            configure_websocket_url(args.websocket_url)
            set_task_info(f"module_{args.module_id}", 100)
        
        # Execute migration
        result = migrate_module_with_enhanced_validation(
            module_id=args.module_id,
            output_path=args.output_path,
            cognos_url=args.cognos_url,
            session_key=args.session_key,
            folder_id=args.folder_id,
            enable_enhanced_validation=args.enable_enhanced_validation,
            validation_config=validation_config
        )
        
        # Print results
        self._print_migration_results(result, args.include_performance_metrics)
        
        # Log errors if specified
        if args.error_log_path and not result['success']:
            self._log_errors(args.error_log_path, result)
        
        return result['success']
    
    def cmd_migrate_report(self, args):
        """Handle migrate-report command"""
        self.logger.info(f"Migrating report {args.report_id}...")
        
        # Parse validation config
        validation_config = self._parse_validation_config(args.validation_config)
        
        # Execute migration
        result = migrate_single_report_with_enhanced_validation(
            report_id=args.report_id,
            output_path=args.output_path,
            cognos_url=args.cognos_url,
            session_key=args.session_key,
            enable_enhanced_validation=args.enable_enhanced_validation,
            validation_config=validation_config
        )
        
        # Print results
        self._print_migration_results(result, False)
        
        return result['success']
    
    def cmd_post_process(self, args):
        """Handle post-process command"""
        self.logger.info(f"Post-processing module {args.module_id}...")
        
        # Parse report IDs
        report_ids = args.report_ids.split(',') if args.report_ids else None
        
        # Execute post-processing
        result = post_process_module_with_enhanced_validation(
            module_id=args.module_id,
            output_path=args.output_path,
            cognos_url=args.cognos_url,
            session_key=args.session_key,
            successful_report_ids=report_ids,
            generate_quality_report=args.generate_quality_report
        )
        
        # Print results
        print(f"\nPost-Processing Status: {'✓ Success' if result['success'] else '✗ Failed'}")
        
        if args.generate_quality_report and result.get('quality_report'):
            print("\nQuality Report Summary:")
            summary = result['quality_report'].get('executive_summary', {})
            print(f"  - Overall Success Rate: {summary.get('success_rate', 0):.1f}%")
            print(f"  - Total Expressions: {summary.get('total_expressions', 0)}")
            print(f"  - Fallback Usage: {summary.get('fallback_usage', 0):.1f}%")
        
        return result['success']
    
    def cmd_dashboard(self, args):
        """Handle dashboard command"""
        self.logger.info(f"Launching quality dashboard on {args.host}:{args.port}...")
        
        # Create and run dashboard
        dashboard = create_standalone_dashboard(db_path=args.db_path)
        
        print(f"\n✓ Dashboard running at http://{args.host}:{args.port}")
        print("Press Ctrl+C to stop")
        
        try:
            dashboard.app.run(host=args.host, port=args.port, debug=False)
        except KeyboardInterrupt:
            print("\n✓ Dashboard stopped")
        
        return True
    
    def cmd_batch_migrate(self, args):
        """Handle batch-migrate command"""
        self.logger.info(f"Batch migrating modules from {args.modules_file}...")
        
        # Read module IDs
        try:
            with open(args.modules_file, 'r') as f:
                module_ids = [line.strip() for line in f if line.strip()]
        except Exception as e:
            self.logger.error(f"Failed to read modules file: {e}")
            return False
        
        # Process modules
        results = []
        success_count = 0
        
        for i, module_id in enumerate(module_ids, 1):
            print(f"\n[{i}/{len(module_ids)}] Processing module {module_id}...")
            
            output_path = os.path.join(args.output_base_path, module_id)
            
            try:
                result = migrate_module_with_enhanced_validation(
                    module_id=module_id,
                    output_path=output_path,
                    cognos_url=args.cognos_url,
                    session_key=args.session_key,
                    enable_enhanced_validation=args.enable_enhanced_validation
                )
                
                results.append(result)
                if result['success']:
                    success_count += 1
                    print(f"  ✓ Success")
                else:
                    print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"  ✗ Exception: {e}")
                results.append({'success': False, 'module_id': module_id, 'error': str(e)})
                
                if not args.continue_on_error:
                    break
        
        # Print summary
        print(f"\n=== Batch Migration Summary ===")
        print(f"Total modules: {len(module_ids)}")
        print(f"Successful: {success_count}")
        print(f"Failed: {len(module_ids) - success_count}")
        print(f"Success rate: {(success_count / len(module_ids) * 100):.1f}%")
        
        return success_count == len(module_ids)
    
    def cmd_validate_module(self, args):
        """Handle validate-module command"""
        self.logger.info(f"Validating module {args.module_id}...")
        
        # Perform dry-run migration with validation
        result = migrate_module_with_enhanced_validation(
            module_id=args.module_id,
            output_path="/tmp/validation_test",  # Temporary path
            cognos_url=args.cognos_url,
            session_key=args.session_key,
            enable_enhanced_validation=True,
            validation_config={'dry_run': True}
        )
        
        # Print validation results
        print(f"\n=== Validation Results for Module {args.module_id} ===")
        
        if result.get('validation_results'):
            val_results = result['validation_results']
            print(f"\nTotal Expressions: {val_results.get('total_expressions', 0)}")
            print(f"Valid Expressions: {val_results.get('successful_conversions', 0)}")
            print(f"Invalid Expressions: {val_results.get('failed_conversions', 0)}")
            print(f"Validation Success Rate: {val_results.get('validation_success_rate', 0)*100:.1f}%")
            print(f"Would Use Fallbacks: {val_results.get('fallbacks_used', 0)}")
        
        # Save report if requested
        if args.output_report:
            with open(args.output_report, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\n✓ Validation report saved to {args.output_report}")
        
        return result.get('validation_results', {}).get('validation_success_rate', 0) > 0.8
    
    def cmd_list_strategies(self, args):
        """Handle list-strategies command"""
        print("\n=== Available Validation Strategies ===\n")
        
        strategies = {
            'primary': 'Direct LLM conversion without validation',
            'enhanced': 'LLM conversion with pre/post validation',
            'fallback_level_1': 'Simplified conversion attempt',
            'fallback_level_2': 'Template-based conversion',
            'safe_fallback': 'Guaranteed safe expressions (BLANK(), SUM())',
            'select_star': 'SELECT * fallback for M-Query (100% success)'
        }
        
        for name, description in strategies.items():
            print(f"  {name}: {description}")
        
        print("\n=== Validation Strictness Levels ===\n")
        print("  low: Basic syntax validation only")
        print("  medium: Syntax + semantic validation (default)")
        print("  high: Comprehensive validation with type checking")
        
        return True
    
    def cmd_show_config(self, args):
        """Handle show-validation-config command"""
        print("\n=== Validation Configuration Options ===\n")
        
        config_template = {
            "validation_config": {
                "validation_enabled": True,
                "validation_strictness": "medium | high | low",
                "fallback_enabled": True,
                "enable_select_star_fallback": True,
                "fallback_threshold": 0.8,
                "max_fallback_attempts": 3,
                "enable_post_validation": True,
                "enable_pre_validation": True
            },
            "websocket_config": {
                "enabled": False,
                "url": "ws://localhost:8765",
                "progress_interval": 1000
            },
            "reporting_config": {
                "generate_html": True,
                "generate_json": True,
                "generate_comprehensive": True,
                "include_performance_metrics": True
            },
            "performance_config": {
                "enable_caching": True,
                "cache_size": 1000,
                "parallel_validation": False,
                "batch_size": 10
            }
        }
        
        print(json.dumps(config_template, indent=2))
        
        print("\n=== Environment Variables ===\n")
        print("  USE_ENHANCED_CONVERTER=true|false")
        print("  USE_ENHANCED_MQUERY_CONVERTER=true|false")
        print("  ENABLE_VALIDATION_FRAMEWORK=true|false")
        print("  VALIDATION_STRICTNESS=low|medium|high")
        print("  ENABLE_SELECT_STAR_FALLBACK=true|false")
        print("  DAX_API_URL=http://localhost:8080")
        
        return True
    
    def _print_migration_results(self, result: Dict[str, Any], include_performance: bool):
        """Print migration results in a formatted way"""
        print(f"\n=== Migration Results ===")
        print(f"Status: {'✓ Success' if result['success'] else '✗ Failed'}")
        print(f"Migration Type: {result.get('migration_type', 'standard')}")
        print(f"Validation Enabled: {result.get('validation_enabled', False)}")
        
        if result.get('validation_results'):
            val_results = result['validation_results']
            print(f"\n=== Validation Metrics ===")
            print(f"Total Expressions: {val_results.get('total_expressions', 0)}")
            print(f"Successful Conversions: {val_results.get('successful_conversions', 0)}")
            print(f"Failed Conversions: {val_results.get('failed_conversions', 0)}")
            print(f"Fallbacks Used: {val_results.get('fallbacks_used', 0)}")
            print(f"Success Rate: {val_results.get('conversion_success_rate', 0)*100:.1f}%")
        
        if include_performance and result.get('performance_metrics'):
            perf = result['performance_metrics']
            print(f"\n=== Performance Metrics ===")
            print(f"Processing Time: {perf.get('processing_time', 0):.2f}s")
            print(f"Memory Usage: {perf.get('memory_usage', 0):.2f}MB")
            print(f"Expressions/Second: {perf.get('expressions_per_second', 0):.2f}")
        
        if result.get('output_path'):
            print(f"\n✓ Output saved to: {result['output_path']}")
    
    def _log_errors(self, log_path: str, result: Dict[str, Any]):
        """Log errors to file"""
        try:
            with open(log_path, 'a') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Timestamp: {result.get('timestamp', 'N/A')}\n")
                f.write(f"Module ID: {result.get('module_id', 'N/A')}\n")
                f.write(f"Error: {result.get('error', 'Unknown error')}\n")
                
                if result.get('validation_results', {}).get('failed_expressions'):
                    f.write("\nFailed Expressions:\n")
                    for expr in result['validation_results']['failed_expressions']:
                        f.write(f"  - {expr}\n")
        except Exception as e:
            self.logger.error(f"Failed to write error log: {e}")
    
    def run(self, argv: List[str] = None):
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
            config = self._load_config_file(args.config_file)
        
        # Setup environment
        self._setup_environment(vars(args), config)
        
        # Execute command
        if not args.command:
            self.parser.print_help()
            return False
        
        # Map commands to methods
        command_map = {
            'test-connection': self.cmd_test_connection,
            'migrate-module': self.cmd_migrate_module,
            'migrate-report': self.cmd_migrate_report,
            'post-process': self.cmd_post_process,
            'dashboard': self.cmd_dashboard,
            'batch-migrate': self.cmd_batch_migrate,
            'validate-module': self.cmd_validate_module,
            'list-strategies': self.cmd_list_strategies,
            'show-validation-config': self.cmd_show_config
        }
        
        handler = command_map.get(args.command)
        if handler:
            try:
                return handler(args)
            except Exception as e:
                self.logger.error(f"Command failed: {e}")
                if args.debug:
                    import traceback
                    traceback.print_exc()
                return False
        else:
            self.logger.error(f"Unknown command: {args.command}")
            return False


def main():
    """Main entry point"""
    cli = EnhancedCLI()
    success = cli.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()