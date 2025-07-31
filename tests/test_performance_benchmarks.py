"""
Performance benchmark tests comparing original vs enhanced migration

This module provides comprehensive performance benchmarks to measure
the impact of the enhanced validation system on migration speed and success rates.
"""

import pytest
import time
import statistics
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime
from typing import Dict, List, Tuple

# Import components to benchmark
from cognos_migrator.validators.expression_validator import ExpressionValidator
from cognos_migrator.validators.mquery_validator import MQueryValidator
from cognos_migrator.strategies.fallback_strategy import FallbackStrategy
from cognos_migrator.converters.expression_converter import ExpressionConverter
from cognos_migrator.converters.enhanced_expression_converter import EnhancedExpressionConverter
from cognos_migrator.converters.mquery_converter import MQueryConverter
from cognos_migrator.converters.enhanced_mquery_converter import EnhancedMQueryConverter
from cognos_migrator.reporting.migration_reporter import MigrationReporter

# Import test data
from tests.sample_cognos_expressions import (
    get_expression_samples, get_all_expressions, 
    get_performance_data, MQUERY_PATTERNS
)


class PerformanceBenchmark:
    """Base class for performance benchmarking"""
    
    def __init__(self):
        self.results = {}
        self.temp_dir = None
    
    def setup(self):
        """Setup benchmark environment"""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown(self):
        """Cleanup benchmark environment"""
        if self.temp_dir:
            shutil.rmtree(self.temp_dir)
    
    def time_function(self, func, *args, **kwargs) -> Tuple[float, any]:
        """Time a function execution
        
        Returns:
            Tuple of (execution_time, result)
        """
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        return end_time - start_time, result
    
    def calculate_statistics(self, times: List[float]) -> Dict[str, float]:
        """Calculate statistics for execution times"""
        return {
            'mean': statistics.mean(times),
            'median': statistics.median(times),
            'stdev': statistics.stdev(times) if len(times) > 1 else 0,
            'min': min(times),
            'max': max(times),
            'total': sum(times)
        }


class ValidationPerformanceBenchmark(PerformanceBenchmark):
    """Benchmark validation performance"""
    
    def __init__(self):
        super().__init__()
        self.expression_validator = ExpressionValidator()
        self.mquery_validator = MQueryValidator()
    
    def benchmark_expression_validation(self, expressions: List[str]) -> Dict[str, any]:
        """Benchmark expression validation performance"""
        times = []
        results = []
        
        for expr in expressions:
            exec_time, result = self.time_function(
                self.expression_validator.validate_cognos_expression, expr
            )
            times.append(exec_time)
            results.append(result)
        
        success_rate = sum(1 for r in results if r['is_valid']) / len(results)
        
        return {
            'timing_stats': self.calculate_statistics(times),
            'success_rate': success_rate,
            'total_expressions': len(expressions),
            'expressions_per_second': len(expressions) / sum(times) if sum(times) > 0 else 0,
            'results': results
        }
    
    def benchmark_mquery_validation(self, queries: List[str]) -> Dict[str, any]:
        """Benchmark M-Query validation performance"""
        times = []
        results = []
        
        for query in queries:
            exec_time, result = self.time_function(
                self.mquery_validator.validate_mquery, query
            )
            times.append(exec_time)
            results.append(result)
        
        success_rate = sum(1 for r in results if r['is_valid']) / len(results)
        
        return {
            'timing_stats': self.calculate_statistics(times),
            'success_rate': success_rate,
            'total_queries': len(queries),
            'queries_per_second': len(queries) / sum(times) if sum(times) > 0 else 0,
            'results': results
        }


class ConverterComparisonBenchmark(PerformanceBenchmark):
    """Benchmark original vs enhanced converters"""
    
    def __init__(self):
        super().__init__()
        
        # Mock LLM service for consistent testing
        self.mock_llm_service = Mock()
        
        # Initialize converters
        self.original_expression_converter = ExpressionConverter(
            llm_service_client=self.mock_llm_service
        )
        self.enhanced_expression_converter = EnhancedExpressionConverter(
            llm_service_client=self.mock_llm_service
        )
        
        self.original_mquery_converter = MQueryConverter(
            llm_service_client=self.mock_llm_service
        )
        self.enhanced_mquery_converter = EnhancedMQueryConverter(
            llm_service_client=self.mock_llm_service
        )
    
    def setup_llm_mock(self, success_rate: float = 0.7):
        """Setup LLM mock with specified success rate"""
        def mock_convert_expression(expr):
            import random
            if random.random() < success_rate:
                return {
                    'success': True,
                    'dax_expression': f'SUM(Table[{expr[:10]}])'
                }
            else:
                return {
                    'success': False,
                    'error': 'Mock LLM failure'
                }
        
        def mock_convert_mquery(query):
            if random.random() < success_rate:
                return {
                    'success': True,
                    'mquery': f'let Source = Sql.Database("server", "db") in Source'
                }
            else:
                return {
                    'success': False,
                    'error': 'Mock M-Query failure'
                }
        
        self.mock_llm_service.convert_expression.side_effect = mock_convert_expression
        self.mock_llm_service.convert_to_mquery.side_effect = mock_convert_mquery
    
    def benchmark_expression_conversion_comparison(self, expressions: List[str]) -> Dict[str, any]:
        """Compare original vs enhanced expression conversion"""
        self.setup_llm_mock(success_rate=0.7)  # 70% LLM success rate
        
        # Benchmark original converter
        original_times = []
        original_results = []
        
        for expr in expressions:
            exec_time, result = self.time_function(
                self.original_expression_converter.convert_expression, expr
            )
            original_times.append(exec_time)
            original_results.append(result)
        
        # Benchmark enhanced converter
        enhanced_times = []
        enhanced_results = []
        
        for expr in expressions:
            exec_time, result = self.time_function(
                self.enhanced_expression_converter.convert_expression, expr
            )
            enhanced_times.append(exec_time)
            enhanced_results.append(result)
        
        # Calculate success rates
        original_success_rate = sum(1 for r in original_results if r.get('success', False)) / len(original_results)
        enhanced_success_rate = sum(1 for r in enhanced_results if r.get('success', False)) / len(enhanced_results)
        
        return {
            'original': {
                'timing_stats': self.calculate_statistics(original_times),
                'success_rate': original_success_rate,
                'total_expressions': len(expressions)
            },
            'enhanced': {
                'timing_stats': self.calculate_statistics(enhanced_times),
                'success_rate': enhanced_success_rate,
                'total_expressions': len(expressions),
                'fallback_usage': sum(1 for r in enhanced_results if r.get('fallback_used', False)) / len(enhanced_results)
            },
            'improvement': {
                'success_rate_improvement': enhanced_success_rate - original_success_rate,
                'speed_ratio': sum(original_times) / sum(enhanced_times) if sum(enhanced_times) > 0 else 0
            }
        }
    
    def benchmark_mquery_conversion_comparison(self, table_names: List[str]) -> Dict[str, any]:
        """Compare original vs enhanced M-Query conversion"""
        self.setup_llm_mock(success_rate=0.6)  # 60% LLM success rate for M-Query
        
        # Create test queries
        test_queries = [f"SELECT * FROM {table}" for table in table_names]
        
        # Benchmark original converter
        original_times = []
        original_results = []
        
        for i, query in enumerate(test_queries):
            exec_time, result = self.time_function(
                self.original_mquery_converter.convert_to_mquery,
                query, table_names[i], "localhost", "TestDB"
            )
            original_times.append(exec_time)
            original_results.append(result)
        
        # Benchmark enhanced converter
        enhanced_times = []
        enhanced_results = []
        
        for i, query in enumerate(test_queries):
            exec_time, result = self.time_function(
                self.enhanced_mquery_converter.convert_to_mquery,
                query, table_names[i], "localhost", "TestDB"
            )
            enhanced_times.append(exec_time)
            enhanced_results.append(result)
        
        # Calculate success rates
        original_success_rate = sum(1 for r in original_results if r.get('success', False)) / len(original_results)
        enhanced_success_rate = sum(1 for r in enhanced_results if r.get('success', False)) / len(enhanced_results)
        
        return {
            'original': {
                'timing_stats': self.calculate_statistics(original_times),
                'success_rate': original_success_rate,
                'total_queries': len(test_queries)
            },
            'enhanced': {
                'timing_stats': self.calculate_statistics(enhanced_times),
                'success_rate': enhanced_success_rate,
                'total_queries': len(test_queries),
                'fallback_usage': sum(1 for r in enhanced_results if r.get('fallback_used', False)) / len(enhanced_results),
                'select_star_usage': sum(1 for r in enhanced_results if 'SELECT *' in r.get('mquery', '')) / len(enhanced_results)
            },
            'improvement': {
                'success_rate_improvement': enhanced_success_rate - original_success_rate,
                'speed_ratio': sum(original_times) / sum(enhanced_times) if sum(enhanced_times) > 0 else 0
            }
        }


class FallbackStrategyBenchmark(PerformanceBenchmark):
    """Benchmark fallback strategy performance"""
    
    def __init__(self):
        super().__init__()
        self.fallback_strategy = FallbackStrategy()
        
        # Mock LLM service that always fails to test fallback performance
        self.failing_llm_service = Mock()
        self.failing_llm_service.convert_expression.return_value = {
            'success': False,
            'error': 'Always fails for testing'
        }
        self.failing_llm_service.convert_to_mquery.return_value = {
            'success': False,
            'error': 'Always fails for testing'
        }
        
        self.fallback_strategy.llm_service = self.failing_llm_service
    
    def benchmark_fallback_performance(self, expressions: List[str]) -> Dict[str, any]:
        """Benchmark fallback strategy performance when LLM always fails"""
        times = []
        results = []
        
        for expr in expressions:
            exec_time, result = self.time_function(
                self.fallback_strategy.convert_with_fallback,
                expr, "dax"
            )
            times.append(exec_time)
            results.append(result)
        
        # All should succeed via fallback
        success_rate = sum(1 for r in results if r['success']) / len(results)
        fallback_usage = sum(1 for r in results if r['fallback_used']) / len(results)
        
        return {
            'timing_stats': self.calculate_statistics(times),
            'success_rate': success_rate,
            'fallback_usage': fallback_usage,
            'total_expressions': len(expressions),
            'expressions_per_second': len(expressions) / sum(times) if sum(times) > 0 else 0
        }


class ReportingPerformanceBenchmark(PerformanceBenchmark):
    """Benchmark reporting system performance"""
    
    def __init__(self):
        super().__init__()
        self.reporter = None
    
    def setup(self):
        """Setup benchmark with temp directory"""
        super().setup()
        self.reporter = MigrationReporter(
            output_directory=self.temp_dir,
            module_id="benchmark_test"
        )
    
    def benchmark_report_generation(self, migration_data_size: int) -> Dict[str, any]:
        """Benchmark report generation performance"""
        # Generate test migration data
        migration_data = {
            'module_id': 'benchmark_test',
            'timestamp': datetime.now().isoformat(),
            'validation_results': {
                'total_expressions': migration_data_size,
                'success_rate': 0.95,
                'fallbacks_used': migration_data_size // 4
            },
            'expression_results': [
                {
                    'original_expression': f'expr_{i}',
                    'converted_expression': f'converted_{i}',
                    'success': True,
                    'fallback_used': i % 4 == 0
                }
                for i in range(migration_data_size)
            ]
        }
        
        # Benchmark different report types
        report_benchmarks = {}
        
        # HTML report
        exec_time, html_path = self.time_function(
            self.reporter.generate_html_report, migration_data
        )
        report_benchmarks['html'] = {
            'time': exec_time,
            'file_size': Path(html_path).stat().st_size if Path(html_path).exists() else 0
        }
        
        # JSON report
        exec_time, json_report = self.time_function(
            self.reporter.generate_validation_report, migration_data['validation_results']
        )
        report_benchmarks['json'] = {
            'time': exec_time,
            'data_size': len(json.dumps(json_report))
        }
        
        # Comprehensive report
        exec_time, comprehensive_report = self.time_function(
            self.reporter.generate_comprehensive_report, migration_data
        )
        report_benchmarks['comprehensive'] = {
            'time': exec_time,
            'data_size': len(json.dumps(comprehensive_report))
        }
        
        return {
            'data_size': migration_data_size,
            'report_benchmarks': report_benchmarks,
            'total_time': sum(r['time'] for r in report_benchmarks.values())
        }


class TestPerformanceBenchmarks:
    """Test class for running performance benchmarks"""
    
    def setup_method(self):
        """Setup test method"""
        self.benchmark_results = {}
    
    def test_validation_performance_small_dataset(self):
        """Test validation performance with small dataset"""
        benchmark = ValidationPerformanceBenchmark()
        benchmark.setup()
        
        try:
            expressions = get_performance_data('small_dataset')['expressions']
            result = benchmark.benchmark_expression_validation(expressions)
            
            # Performance assertions
            assert result['timing_stats']['mean'] < 0.1  # Average < 100ms per expression
            assert result['expressions_per_second'] > 10  # At least 10 expressions/second
            assert result['success_rate'] > 0.8  # At least 80% success rate
            
            self.benchmark_results['validation_small'] = result
            
        finally:
            benchmark.teardown()
    
    def test_validation_performance_large_dataset(self):
        """Test validation performance with large dataset"""
        benchmark = ValidationPerformanceBenchmark()
        benchmark.setup()
        
        try:
            expressions = get_all_expressions()
            result = benchmark.benchmark_expression_validation(expressions)
            
            # Performance assertions for large dataset
            assert result['timing_stats']['mean'] < 0.3  # Average < 300ms per expression
            assert result['expressions_per_second'] > 3   # At least 3 expressions/second
            
            self.benchmark_results['validation_large'] = result
            
        finally:
            benchmark.teardown()
    
    def test_converter_comparison_performance(self):
        """Test original vs enhanced converter performance comparison"""
        benchmark = ConverterComparisonBenchmark()
        benchmark.setup()
        
        try:
            expressions = get_expression_samples('simple_aggregations') + \
                         get_expression_samples('arithmetic_expressions')
            
            result = benchmark.benchmark_expression_conversion_comparison(expressions)
            
            # Enhanced converter should have higher success rate
            assert result['enhanced']['success_rate'] >= result['original']['success_rate']
            
            # Enhanced converter should maintain reasonable performance
            assert result['improvement']['speed_ratio'] > 0.5  # Not more than 2x slower
            
            # Success rate improvement should be significant with fallbacks
            assert result['improvement']['success_rate_improvement'] >= 0.0
            
            self.benchmark_results['converter_comparison'] = result
            
        finally:
            benchmark.teardown()
    
    def test_mquery_converter_comparison(self):
        """Test M-Query converter performance comparison"""
        benchmark = ConverterComparisonBenchmark()
        benchmark.setup()
        
        try:
            table_names = ['Sales', 'Customer', 'Product', 'Orders', 'Region']
            result = benchmark.benchmark_mquery_conversion_comparison(table_names)
            
            # Enhanced M-Query converter should have much higher success rate due to SELECT * fallback
            assert result['enhanced']['success_rate'] >= 0.95  # Should be near 100% with SELECT * fallback
            assert result['enhanced']['success_rate'] > result['original']['success_rate']
            
            # Should show SELECT * fallback usage
            assert result['enhanced']['select_star_usage'] > 0
            
            self.benchmark_results['mquery_comparison'] = result
            
        finally:
            benchmark.teardown()
    
    def test_fallback_strategy_performance(self):
        """Test fallback strategy performance when LLM fails"""
        benchmark = FallbackStrategyBenchmark()
        benchmark.setup()
        
        try:
            expressions = get_expression_samples('simple_aggregations')
            result = benchmark.benchmark_fallback_performance(expressions)
            
            # All expressions should succeed via fallback
            assert result['success_rate'] == 1.0  # 100% success rate
            assert result['fallback_usage'] == 1.0  # 100% fallback usage
            
            # Fallback should be reasonably fast
            assert result['expressions_per_second'] > 5  # At least 5 expressions/second
            
            self.benchmark_results['fallback_performance'] = result
            
        finally:
            benchmark.teardown()
    
    def test_reporting_performance(self):
        """Test reporting system performance"""
        benchmark = ReportingPerformanceBenchmark()
        benchmark.setup()
        
        try:
            # Test with different data sizes
            sizes = [10, 50, 100]
            results = {}
            
            for size in sizes:
                result = benchmark.benchmark_report_generation(size)
                results[f'size_{size}'] = result
                
                # Performance assertions
                assert result['total_time'] < 10.0  # Total time < 10 seconds
                assert all(r['time'] < 5.0 for r in result['report_benchmarks'].values())  # Individual reports < 5 seconds
            
            self.benchmark_results['reporting_performance'] = results
            
        finally:
            benchmark.teardown()
    
    def test_end_to_end_performance_comparison(self):
        """Test end-to-end performance comparison: original vs enhanced"""
        # This test simulates a complete migration workflow
        expressions = get_expression_samples('conditional_aggregations')
        
        # Mock original workflow (no validation, basic conversion)
        start_time = time.time()
        original_results = []
        for expr in expressions:
            # Simulate original converter (70% success rate)
            import random
            if random.random() < 0.7:
                original_results.append({'success': True, 'expression': f'CONVERTED_{expr[:10]}'})
            else:
                original_results.append({'success': False, 'error': 'Conversion failed'})
        original_time = time.time() - start_time
        
        # Enhanced workflow (with validation and fallbacks)
        start_time = time.time()
        validator = ExpressionValidator()
        strategy = FallbackStrategy()
        
        # Mock LLM service
        mock_llm = Mock()
        mock_llm.convert_expression.side_effect = lambda x: (
            {'success': True, 'dax_expression': f'SUM(Table[{x[:10]}])'} 
            if random.random() < 0.7 
            else {'success': False, 'error': 'Failed'}
        )
        strategy.llm_service = mock_llm
        
        enhanced_results = []
        for expr in expressions:
            # Validate first
            validation = validator.validate_cognos_expression(expr)
            if validation['is_valid']:
                # Convert with fallback
                result = strategy.convert_with_fallback(expr, 'dax')
                enhanced_results.append(result)
            else:
                enhanced_results.append({'success': False, 'error': 'Invalid expression'})
        
        enhanced_time = time.time() - start_time
        
        # Calculate metrics
        original_success_rate = sum(1 for r in original_results if r['success']) / len(original_results)
        enhanced_success_rate = sum(1 for r in enhanced_results if r['success']) / len(enhanced_results)
        
        comparison_result = {
            'original': {
                'success_rate': original_success_rate,
                'execution_time': original_time,
                'expressions_per_second': len(expressions) / original_time
            },
            'enhanced': {
                'success_rate': enhanced_success_rate,
                'execution_time': enhanced_time,
                'expressions_per_second': len(expressions) / enhanced_time,
                'fallback_usage': sum(1 for r in enhanced_results if r.get('fallback_used', False)) / len(enhanced_results)
            },
            'improvement': {
                'success_rate_improvement': enhanced_success_rate - original_success_rate,
                'time_overhead_ratio': enhanced_time / original_time
            }
        }
        
        # Assertions
        assert comparison_result['enhanced']['success_rate'] >= comparison_result['original']['success_rate']
        assert comparison_result['improvement']['time_overhead_ratio'] < 3.0  # Not more than 3x slower
        
        self.benchmark_results['end_to_end_comparison'] = comparison_result
    
    def teardown_method(self):
        """Print benchmark results summary"""
        if self.benchmark_results:
            print("\n=== PERFORMANCE BENCHMARK RESULTS ===")
            for test_name, result in self.benchmark_results.items():
                print(f"\n{test_name.upper()}:")
                if isinstance(result, dict):
                    self._print_dict(result, indent=2)
    
    def _print_dict(self, d, indent=0):
        """Recursively print dictionary with indentation"""
        for key, value in d.items():
            if isinstance(value, dict):
                print(" " * indent + f"{key}:")
                self._print_dict(value, indent + 2)
            elif isinstance(value, (int, float)):
                print(" " * indent + f"{key}: {value:.4f}")
            else:
                print(" " * indent + f"{key}: {value}")


if __name__ == "__main__":
    # Run benchmarks directly
    pytest.main([__file__, "-v", "-s"])