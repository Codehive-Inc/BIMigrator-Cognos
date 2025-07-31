"""
Integration tests for the complete enhanced validation system

This module tests the full end-to-end integration of all validation components
working together in realistic migration scenarios.
"""

import pytest
import tempfile
import shutil
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import all components for integration testing
from cognos_migrator.enhanced_main import (
    test_cognos_connection_enhanced,
    migrate_module_with_enhanced_validation,
    migrate_single_report_with_enhanced_validation,
    post_process_module_with_enhanced_validation
)
from cognos_migrator.enhanced_migration_orchestrator import EnhancedMigrationOrchestrator
from cognos_migrator.dashboard.quality_dashboard import QualityDashboard, create_standalone_dashboard
from tests.sample_cognos_expressions import get_sample_report, SAMPLE_REPORT_STRUCTURES


class TestCompleteIntegration:
    """Test complete integration of the enhanced validation system"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_cognos_url = "http://test-cognos:9300/api/v1"
        self.test_session_key = "CAM_TEST_SESSION_KEY"
        self.test_module_id = "TEST_MODULE_123"
        self.test_report_id = "TEST_REPORT_456"
        
        # Mock environment variables
        os.environ['USE_ENHANCED_CONVERTER'] = 'true'
        os.environ['USE_ENHANCED_MQUERY_CONVERTER'] = 'true'
        os.environ['DAX_API_URL'] = 'http://localhost:8080'
    
    def teardown_method(self):
        """Cleanup test environment"""
        shutil.rmtree(self.temp_dir)
        # Clean up environment variables
        for key in ['USE_ENHANCED_CONVERTER', 'USE_ENHANCED_MQUERY_CONVERTER', 'DAX_API_URL']:
            if key in os.environ:
                del os.environ[key]
    
    @patch('cognos_migrator.client.CognosClient.test_connection_with_session')
    def test_enhanced_connection_test(self, mock_test_connection):
        """Test enhanced connection testing with validation components"""
        # Mock successful connection
        mock_test_connection.return_value = True
        
        result = test_cognos_connection_enhanced(
            cognos_url=self.test_cognos_url,
            session_key=self.test_session_key,
            enable_validation=True
        )
        
        # Verify connection test results
        assert result['connection_valid'] is True
        assert result['validation_framework_available'] is True
        assert result['fallback_strategy_available'] is True
        assert result['reporters_available'] is True
        assert result['enhanced_converters_available'] is True
        assert 'timestamp' in result
        
        # Test with validation disabled
        result_no_validation = test_cognos_connection_enhanced(
            cognos_url=self.test_cognos_url,
            session_key=self.test_session_key,
            enable_validation=False
        )
        
        assert result_no_validation['connection_valid'] is True
        assert result_no_validation['validation_framework_available'] is False
    
    @patch('cognos_migrator.enhanced_migration_orchestrator.EnhancedMigrationOrchestrator')
    @patch('cognos_migrator.client.CognosClient.test_connection_with_session')
    def test_enhanced_module_migration_integration(self, mock_test_connection, mock_orchestrator):
        """Test complete enhanced module migration workflow"""
        # Mock successful connection
        mock_test_connection.return_value = True
        
        # Mock orchestrator and its methods
        mock_orchestrator_instance = Mock()
        mock_orchestrator.return_value = mock_orchestrator_instance
        
        # Mock successful migration result
        mock_migration_result = {
            'success': True,
            'module_id': self.test_module_id,
            'output_path': self.temp_dir,
            'migration_type': 'enhanced',
            'validation_enabled': True,
            'validation_results': {
                'total_expressions': 50,
                'successful_conversions': 45,
                'failed_conversions': 5,
                'fallbacks_used': 8,
                'validation_success_rate': 0.9,
                'conversion_success_rate': 0.95
            },
            'performance_metrics': {
                'processing_time': 120.5,
                'memory_usage': 256.7,
                'expressions_per_second': 2.4
            },
            'timestamp': datetime.now().isoformat()
        }
        
        mock_orchestrator_instance.migrate_module_with_validation.return_value = mock_migration_result
        
        # Execute enhanced migration
        result = migrate_module_with_enhanced_validation(
            module_id=self.test_module_id,
            output_path=self.temp_dir,
            cognos_url=self.test_cognos_url,
            session_key=self.test_session_key,
            folder_id="TEST_FOLDER_789",
            enable_enhanced_validation=True,
            validation_config={
                'validation_strictness': 'high',
                'fallback_threshold': 0.8,
                'enable_select_star_fallback': True
            }
        )
        
        # Verify integration results
        assert result['success'] is True
        assert result['module_id'] == self.test_module_id
        assert result['validation_enabled'] is True
        assert result['validation_results']['total_expressions'] == 50
        assert result['validation_results']['conversion_success_rate'] == 0.95
        assert result['performance_metrics']['processing_time'] == 120.5
        
        # Verify orchestrator was called with correct parameters
        mock_orchestrator.assert_called_once()
        mock_orchestrator_instance.migrate_module_with_validation.assert_called_once()
    
    @patch('cognos_migrator.enhanced_migration_orchestrator.EnhancedMigrationOrchestrator')
    @patch('cognos_migrator.client.CognosClient.test_connection_with_session')
    def test_enhanced_report_migration_integration(self, mock_test_connection, mock_orchestrator):
        """Test complete enhanced report migration workflow"""
        # Mock successful connection
        mock_test_connection.return_value = True
        
        # Mock orchestrator
        mock_orchestrator_instance = Mock()
        mock_orchestrator.return_value = mock_orchestrator_instance
        
        # Mock successful report migration result
        mock_report_result = {
            'success': True,
            'report_id': self.test_report_id,
            'output_path': self.temp_dir,
            'migration_type': 'enhanced',
            'validation_enabled': True,
            'validation_results': {
                'total_expressions': 25,
                'successful_conversions': 23,
                'failed_conversions': 2,
                'fallbacks_used': 4,
                'validation_success_rate': 0.92,
                'conversion_success_rate': 0.96
            },
            'timestamp': datetime.now().isoformat()
        }
        
        mock_orchestrator_instance.migrate_report_with_validation.return_value = mock_report_result
        
        # Execute enhanced report migration
        result = migrate_single_report_with_enhanced_validation(
            report_id=self.test_report_id,
            output_path=self.temp_dir,
            cognos_url=self.test_cognos_url,
            session_key=self.test_session_key,
            enable_enhanced_validation=True
        )
        
        # Verify integration results
        assert result['success'] is True
        assert result['report_id'] == self.test_report_id
        assert result['validation_enabled'] is True
        assert result['validation_results']['validation_success_rate'] == 0.92
        
        # Verify orchestrator interaction
        mock_orchestrator_instance.migrate_report_with_validation.assert_called_once()
    
    @patch('cognos_migrator.reporting.migration_reporter.MigrationReporter')
    @patch('cognos_migrator.main.post_process_module_with_explicit_session')
    @patch('cognos_migrator.client.CognosClient.test_connection_with_session')
    def test_enhanced_post_processing_integration(self, mock_test_connection, mock_post_process, mock_reporter):
        """Test enhanced post-processing with quality reports"""
        # Mock successful connection
        mock_test_connection.return_value = True
        
        # Mock successful standard post-processing
        mock_post_process.return_value = True
        
        # Mock reporter
        mock_reporter_instance = Mock()
        mock_reporter.return_value = mock_reporter_instance
        
        mock_quality_report = {
            'executive_summary': {
                'overall_success': True,
                'success_rate': 95.2,
                'total_expressions': 75,
                'fallback_usage': 12.0
            },
            'detailed_results': {
                'validation_details': 'Comprehensive validation passed',
                'conversion_details': 'High conversion success rate'
            },
            'recommendations': [
                'Excellent migration quality',
                'Consider documenting successful patterns'
            ]
        }
        
        mock_reporter_instance.generate_comprehensive_report.return_value = mock_quality_report
        
        # Execute enhanced post-processing
        result = post_process_module_with_enhanced_validation(
            module_id=self.test_module_id,
            output_path=self.temp_dir,
            cognos_url=self.test_cognos_url,
            session_key=self.test_session_key,
            successful_report_ids=["report1", "report2", "report3"],
            generate_quality_report=True
        )
        
        # Verify integration results
        assert result['success'] is True
        assert result['standard_post_processing'] is True
        assert result['enhanced_reports_generated'] is True
        assert result['quality_report']['executive_summary']['success_rate'] == 95.2
        
        # Verify reporter interaction
        mock_reporter_instance.generate_comprehensive_report.assert_called_once()
    
    def test_dashboard_integration(self):
        """Test integration with quality dashboard"""
        # Create standalone dashboard
        dashboard_db_path = os.path.join(self.temp_dir, "test_metrics.db")
        dashboard = create_standalone_dashboard(db_path=dashboard_db_path)
        
        # Create sample migration data
        migration_data = {
            'module_id': self.test_module_id,
            'timestamp': datetime.now().isoformat(),
            'validation_results': {
                'total_expressions': 100,
                'successful_conversions': 95,
                'failed_conversions': 5,
                'fallbacks_used': 15,
                'validation_success_rate': 0.95,
                'conversion_success_rate': 0.95,
                'error_count': 2
            },
            'performance_metrics': {
                'processing_time': 180.0,
                'memory_usage': 512.3
            }
        }
        
        # Record metrics in dashboard
        migration_id = dashboard.record_migration_metrics(migration_data)
        assert migration_id > 0
        
        # Generate dashboard data
        dashboard_data = dashboard.generate_dashboard_data()
        
        # Verify dashboard data structure
        assert hasattr(dashboard_data, 'overview')
        assert hasattr(dashboard_data, 'recent_migrations')
        assert hasattr(dashboard_data, 'performance_metrics')
        assert hasattr(dashboard_data, 'validation_insights')
        
        # Verify overview metrics
        assert dashboard_data.overview['total_migrations'] >= 1
        assert dashboard_data.overview['total_expressions_processed'] >= 100
        
        # Verify recent migrations
        assert len(dashboard_data.recent_migrations) >= 1
        recent_migration = dashboard_data.recent_migrations[0]
        assert recent_migration.module_id == self.test_module_id
        assert recent_migration.total_expressions == 100
    
    def test_real_world_scenario_simulation(self):
        """Test simulation of real-world migration scenario"""
        # Use sample report structure for testing
        sales_report = get_sample_report('sales_report')
        
        # Simulate processing the sample report
        expressions_to_process = sales_report.get('calculations', [])
        
        # Mock enhanced validation workflow
        from cognos_migrator.validators.expression_validator import ExpressionValidator
        from cognos_migrator.strategies.fallback_strategy import FallbackStrategy
        
        validator = ExpressionValidator()
        strategy = FallbackStrategy()
        
        # Mock LLM service with realistic success rate
        mock_llm_service = Mock()
        def mock_convert_expression(expr):
            # Simulate 80% success rate
            import random
            if random.random() < 0.8:
                return {
                    'success': True,
                    'dax_expression': f'SUM(Sales[{expr.split("[")[1].split("]")[0] if "[" in expr else "Amount"}])'
                }
            else:
                return {
                    'success': False,
                    'error': 'Complex expression conversion failed'
                }
        
        mock_llm_service.convert_expression.side_effect = mock_convert_expression
        strategy.llm_service = mock_llm_service
        
        # Process expressions
        results = []
        for expr in expressions_to_process:
            # Validate expression
            validation_result = validator.validate_cognos_expression(expr)
            
            if validation_result['is_valid']:
                # Convert with fallback
                conversion_result = strategy.convert_with_fallback(expr, 'dax')
                results.append({
                    'original_expression': expr,
                    'validation_passed': True,
                    'conversion_success': conversion_result['success'],
                    'fallback_used': conversion_result.get('fallback_used', False),
                    'final_expression': conversion_result.get('final_expression', '')
                })
            else:
                results.append({
                    'original_expression': expr,
                    'validation_passed': False,
                    'conversion_success': False,
                    'fallback_used': False,
                    'error': validation_result.get('errors', ['Unknown validation error'])
                })
        
        # Verify realistic results
        assert len(results) == len(expressions_to_process)
        
        # All should have some result (validation or conversion)
        assert all('original_expression' in result for result in results)
        
        # Calculate success metrics
        validation_success_rate = sum(1 for r in results if r['validation_passed']) / len(results)
        conversion_success_rate = sum(1 for r in results if r['conversion_success']) / len(results)
        fallback_usage_rate = sum(1 for r in results if r.get('fallback_used', False)) / len(results)
        
        # Verify realistic success rates
        assert validation_success_rate >= 0.5  # At least 50% should validate
        assert conversion_success_rate >= 0.8  # At least 80% should convert (with fallbacks)
        
        print(f"Real-world simulation results:")
        print(f"  Validation success rate: {validation_success_rate:.2%}")
        print(f"  Conversion success rate: {conversion_success_rate:.2%}")
        print(f"  Fallback usage rate: {fallback_usage_rate:.2%}")
    
    def test_error_handling_and_recovery(self):
        """Test error handling and recovery mechanisms"""
        # Test with invalid session key
        with pytest.raises(Exception):  # Should raise CognosAPIError or similar
            with patch('cognos_migrator.client.CognosClient.test_connection_with_session') as mock_conn:
                mock_conn.return_value = False
                migrate_module_with_enhanced_validation(
                    module_id=self.test_module_id,
                    output_path=self.temp_dir,
                    cognos_url=self.test_cognos_url,
                    session_key="INVALID_SESSION_KEY"
                )
        
        # Test with missing configuration
        with patch('cognos_migrator.client.CognosClient.test_connection_with_session') as mock_conn:
            mock_conn.return_value = True
            
            # This should handle gracefully and return error result
            result = migrate_module_with_enhanced_validation(
                module_id=self.test_module_id,
                output_path="/invalid/path/that/does/not/exist",
                cognos_url=self.test_cognos_url,
                session_key=self.test_session_key,
                enable_enhanced_validation=False  # Disable to test fallback to standard
            )
            
            # Should either succeed with standard migration or fail gracefully
            assert 'success' in result
            assert 'error' in result or result['success'] is True
    
    def test_performance_under_load(self):
        """Test performance under simulated load"""
        from tests.sample_cognos_expressions import get_all_expressions
        
        # Get all test expressions for load testing
        all_expressions = get_all_expressions()
        
        # Simulate processing many expressions
        from cognos_migrator.validators.expression_validator import ExpressionValidator
        
        validator = ExpressionValidator()
        
        import time
        start_time = time.time()
        
        # Process expressions in batches
        batch_size = 10
        batch_results = []
        
        for i in range(0, min(len(all_expressions), 50), batch_size):  # Limit to 50 for testing
            batch = all_expressions[i:i+batch_size]
            batch_start = time.time()
            
            batch_validation_results = []
            for expr in batch:
                result = validator.validate_cognos_expression(expr)
                batch_validation_results.append(result)
            
            batch_end = time.time()
            batch_results.append({
                'batch_size': len(batch),
                'processing_time': batch_end - batch_start,
                'success_rate': sum(1 for r in batch_validation_results if r['is_valid']) / len(batch_validation_results)
            })
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance assertions
        assert total_time < 30.0  # Should complete within 30 seconds
        assert all(batch['processing_time'] < 5.0 for batch in batch_results)  # Each batch < 5 seconds
        
        # Calculate overall metrics
        total_expressions_processed = sum(batch['batch_size'] for batch in batch_results)
        average_expressions_per_second = total_expressions_processed / total_time
        
        assert average_expressions_per_second > 1.0  # At least 1 expression per second
        
        print(f"Performance under load:")
        print(f"  Total expressions processed: {total_expressions_processed}")
        print(f"  Total processing time: {total_time:.2f} seconds")
        print(f"  Average expressions per second: {average_expressions_per_second:.2f}")


class TestBackwardCompatibility:
    """Test backward compatibility with existing migration workflows"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Cleanup test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_enhanced_disabled_falls_back_to_standard(self):
        """Test that disabling enhanced validation falls back to standard migration"""
        with patch('cognos_migrator.client.CognosClient.test_connection_with_session') as mock_conn:
            mock_conn.return_value = True
            
            with patch('cognos_migrator.main.migrate_module_with_explicit_session') as mock_standard:
                mock_standard.return_value = True
                
                result = migrate_module_with_enhanced_validation(
                    module_id="test_module",
                    output_path=self.temp_dir,
                    cognos_url="http://test:9300/api/v1",
                    session_key="test_session",
                    enable_enhanced_validation=False
                )
                
                # Should call standard migration
                mock_standard.assert_called_once()
                assert result['migration_type'] == 'standard'
                assert result['validation_enabled'] is False
    
    def test_environment_variable_compatibility(self):
        """Test environment variable compatibility for enabling/disabling features"""
        # Test with enhanced converters disabled via environment
        os.environ['USE_ENHANCED_CONVERTER'] = 'false'
        os.environ['USE_ENHANCED_MQUERY_CONVERTER'] = 'false'
        
        try:
            # Should still work but use original converters
            from cognos_migrator.converters.expression_converter import ExpressionConverter
            from cognos_migrator.converters.mquery_converter import MQueryConverter
            
            # These should import without issues
            assert ExpressionConverter is not None
            assert MQueryConverter is not None
            
        finally:
            # Clean up
            del os.environ['USE_ENHANCED_CONVERTER']
            del os.environ['USE_ENHANCED_MQUERY_CONVERTER']


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-s"])