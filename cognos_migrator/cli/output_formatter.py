"""
Output Formatter for CLI

Handles all CLI output formatting and display.
Follows Single Responsibility Principle.
"""

import json
from typing import Dict, Any
from pathlib import Path


class OutputFormatter:
    """Formats and displays CLI output"""
    
    @staticmethod
    def print_connection_results(result: Dict[str, Any], enable_validation: bool):
        """Print connection test results"""
        print(f"\nConnection Status: {'✓ Valid' if result['connection_valid'] else '✗ Invalid'}")
        
        if enable_validation:
            print("\nValidation Framework Status:")
            print(f"  - Framework Available: {'✓' if result.get('validation_framework_available') else '✗'}")
            print(f"  - Fallback Strategy: {'✓' if result.get('fallback_strategy_available') else '✗'}")
            print(f"  - Reporters: {'✓' if result.get('reporters_available') else '✗'}")
            print(f"  - Enhanced Converters: {'✓' if result.get('enhanced_converters_available') else '✗'}")
        
        if 'error' in result:
            print(f"\nError: {result['error']}")
    
    @staticmethod
    def print_migration_results(result: Dict[str, Any], include_performance: bool):
        """Print migration results"""
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
    
    @staticmethod
    def print_post_process_results(result: Dict[str, Any], generate_quality_report: bool):
        """Print post-processing results"""
        print(f"\nPost-Processing Status: {'✓ Success' if result['success'] else '✗ Failed'}")
        
        if generate_quality_report and result.get('quality_report'):
            print("\nQuality Report Summary:")
            summary = result['quality_report'].get('executive_summary', {})
            print(f"  - Overall Success Rate: {summary.get('success_rate', 0):.1f}%")
            print(f"  - Total Expressions: {summary.get('total_expressions', 0)}")
            print(f"  - Fallback Usage: {summary.get('fallback_usage', 0):.1f}%")
    
    @staticmethod
    def print_validation_results(result: Dict[str, Any], module_id: str):
        """Print validation results"""
        print(f"\n=== Validation Results for Module {module_id} ===")
        
        if result.get('validation_results'):
            val_results = result['validation_results']
            print(f"\nTotal Expressions: {val_results.get('total_expressions', 0)}")
            print(f"Valid Expressions: {val_results.get('successful_conversions', 0)}")
            print(f"Invalid Expressions: {val_results.get('failed_conversions', 0)}")
            print(f"Validation Success Rate: {val_results.get('validation_success_rate', 0)*100:.1f}%")
            print(f"Would Use Fallbacks: {val_results.get('fallbacks_used', 0)}")
    
    @staticmethod
    def write_error_log(log_path: str, result: Dict[str, Any]):
        """Write errors to log file"""
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
            print(f"Failed to write error log: {e}")