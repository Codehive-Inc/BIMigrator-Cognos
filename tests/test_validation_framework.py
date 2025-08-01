"""
Comprehensive test suite for the enhanced validation framework

This test suite validates all components of the enhanced migration system:
- Expression validation
- M-Query validation  
- Fallback strategies
- Configuration management
- Reporting system
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import validation components
from cognos_migrator.validators.expression_validator import ExpressionValidator
from cognos_migrator.validators.mquery_validator import MQueryValidator
from cognos_migrator.validators.fallback_validator import FallbackValidator
from cognos_migrator.strategies.fallback_strategy import FallbackStrategy
from cognos_migrator.config.fallback_config import EnhancedMigrationConfig, ConfigurationManager
from cognos_migrator.reporting.migration_reporter import MigrationReporter
from cognos_migrator.converters.enhanced_expression_converter import EnhancedExpressionConverter
from cognos_migrator.converters.enhanced_mquery_converter import EnhancedMQueryConverter
from cognos_migrator.templates.mquery import get_template_manager


class TestExpressionValidator:
    """Test suite for expression validation"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.validator = ExpressionValidator()
    
    def test_valid_cognos_expressions(self):
        """Test validation of valid Cognos expressions"""
        valid_expressions = [
            "total([Sales])",
            "sum([Revenue] for [Region] = 'US')",
            "count([Customer ID])",
            "[Quantity] * [Price]",
            "case when [Status] = 'Active' then 1 else 0 end"
        ]
        
        for expr in valid_expressions:
            result = self.validator.validate_cognos_expression(expr)
            assert result['is_valid'], f"Expression should be valid: {expr}"
            assert not result['errors'], f"Should have no errors: {expr}"
    
    def test_invalid_cognos_expressions(self):
        """Test validation of invalid Cognos expressions"""
        invalid_expressions = [
            "",  # Empty expression
            "invalid_function([Sales])",  # Invalid function
            "total([Sales] for [Region] =",  # Incomplete expression
            "sum([Revenue] + )",  # Incomplete arithmetic
            "[NonExistentField]"  # Non-existent field (context dependent)
        ]
        
        for expr in invalid_expressions:
            result = self.validator.validate_cognos_expression(expr)
            assert not result['is_valid'], f"Expression should be invalid: {expr}"
            assert result['errors'], f"Should have errors: {expr}"
    
    def test_valid_dax_expressions(self):
        """Test validation of valid DAX expressions"""
        valid_dax = [
            "SUM(Sales[Amount])",
            "CALCULATE(SUM(Sales[Amount]), Region[Name] = \"US\")",
            "AVERAGE(Sales[Quantity])",
            "COUNT(Customer[ID])",
            "BLANK()"
        ]
        
        for expr in valid_dax:
            result = self.validator.validate_dax_expression(expr)
            assert result['is_valid'], f"DAX should be valid: {expr}"
            assert not result['errors'], f"Should have no errors: {expr}"
    
    def test_invalid_dax_expressions(self):
        """Test validation of invalid DAX expressions"""
        invalid_dax = [
            "",  # Empty
            "SUM(",  # Incomplete
            "INVALID_FUNCTION(Sales[Amount])",  # Invalid function
            "SUM(Sales[Amount] +)",  # Incomplete arithmetic
            "CALCULATE()"  # Missing arguments
        ]
        
        for expr in invalid_dax:
            result = self.validator.validate_dax_expression(expr)
            assert not result['is_valid'], f"DAX should be invalid: {expr}"
            assert result['errors'], f"Should have errors: {expr}"
    
    def test_complexity_scoring(self):
        """Test expression complexity scoring"""
        simple_expr = "SUM(Sales[Amount])"
        complex_expr = "CALCULATE(SUM(Sales[Amount]), FILTER(ALL(Region), Region[Country] = \"US\"))"
        
        simple_result = self.validator.validate_cognos_expression(simple_expr)
        complex_result = self.validator.validate_cognos_expression(complex_expr)
        
        assert simple_result['complexity_score'] < complex_result['complexity_score']


class TestMQueryValidator:
    """Test suite for M-Query validation"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.validator = MQueryValidator()
    
    def test_valid_mquery(self):
        """Test validation of valid M-Query expressions"""
        valid_mquery = '''
        let
            Source = Sql.Database("server", "database", [Query="SELECT * FROM Sales"]),
            Navigation = Source{[Name="Sales"]}[Data]
        in
            Navigation
        '''
        
        result = self.validator.validate_mquery(valid_mquery)
        assert result['is_valid']
        assert not result['errors']
        assert result['has_source_definition']
    
    def test_invalid_mquery_syntax(self):
        """Test validation of invalid M-Query syntax"""
        invalid_mquery = '''
        let
            Source = Sql.Database("server", "database"
            Navigation = Source{[Name="Sales"]}[Data]
        in
            Navigation
        '''  # Missing closing parenthesis
        
        result = self.validator.validate_mquery(invalid_mquery)
        assert not result['is_valid']
        assert result['errors']
    
    def test_select_star_fallback_validation(self):
        """Test validation of SELECT * fallback queries"""
        select_star_query = '''
        let
            Source = Sql.Database("server", "database", [Query="SELECT * FROM Sales"])
        in
            Source
        '''
        
        result = self.validator.validate_select_star_fallback(select_star_query)
        assert result['is_valid']
        assert result['is_select_star']
        assert result['guaranteed_success']
    
    def test_query_folding_detection(self):
        """Test detection of query folding opportunities"""
        foldable_query = '''
        let
            Source = Sql.Database("server", "database"),
            Navigation = Source{[Name="Sales"]}[Data],
            Filter = Table.SelectRows(Navigation, each [Amount] > 1000)
        in
            Filter
        '''
        
        result = self.validator.validate_mquery(foldable_query)
        assert result['query_folding_capable']


class TestFallbackValidator:
    """Test suite for fallback validation"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.validator = FallbackValidator()
    
    def test_safe_dax_fallback(self):
        """Test generation and validation of safe DAX fallbacks"""
        fallback = self.validator.generate_safe_dax_fallback("Sales", "Amount")
        
        result = self.validator.validate_safe_fallback(fallback, "dax")
        assert result['is_valid']
        assert result['is_safe_fallback']
        assert result['guaranteed_success']
    
    def test_select_star_generation(self):
        """Test generation of SELECT * fallback queries"""
        fallback = self.validator.generate_select_star_fallback("Sales", "localhost", "TestDB")
        
        result = self.validator.validate_safe_fallback(fallback, "mquery")
        assert result['is_valid']
        assert result['is_safe_fallback']
        assert "SELECT * FROM Sales" in fallback
    
    def test_fallback_suggestions(self):
        """Test generation of fallback suggestions"""
        failed_expression = "INVALID_FUNCTION(Sales[Amount])"
        suggestions = self.validator.suggest_fallbacks(failed_expression, "dax")
        
        assert len(suggestions) > 0
        assert all(suggestion['type'] in ['safe', 'simplified', 'blank'] for suggestion in suggestions)


class TestFallbackStrategy:
    """Test suite for fallback strategy"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.strategy = FallbackStrategy()
        
        # Mock LLM service
        self.mock_llm_service = Mock()
        self.strategy.llm_service = self.mock_llm_service
    
    def test_successful_primary_conversion(self):
        """Test successful primary conversion without fallback"""
        # Mock successful LLM response
        self.mock_llm_service.convert_expression.return_value = {
            'success': True,
            'dax_expression': 'SUM(Sales[Amount])'
        }
        
        result = self.strategy.convert_with_fallback(
            cognos_expression="total([Sales])",
            expression_type="dax"
        )
        
        assert result['success']
        assert result['final_expression'] == 'SUM(Sales[Amount])'
        assert result['conversion_method'] == 'primary'
        assert not result['fallback_used']
    
    def test_fallback_on_llm_failure(self):
        """Test fallback activation when LLM fails"""
        # Mock failed LLM response
        self.mock_llm_service.convert_expression.return_value = {
            'success': False,
            'error': 'LLM service unavailable'
        }
        
        result = self.strategy.convert_with_fallback(
            cognos_expression="total([Sales])",
            expression_type="dax"
        )
        
        assert result['success']  # Should still succeed via fallback
        assert result['fallback_used']
        assert result['conversion_method'] in ['fallback_level_1', 'fallback_level_2', 'safe_fallback']
    
    def test_mquery_select_star_fallback(self):
        """Test M-Query SELECT * fallback"""
        # Mock failed LLM response
        self.mock_llm_service.convert_to_mquery.return_value = {
            'success': False,
            'error': 'Complex query conversion failed'
        }
        
        result = self.strategy.convert_with_fallback(
            cognos_expression="complex query with joins",
            expression_type="mquery",
            table_name="Sales",
            server="localhost",
            database="TestDB"
        )
        
        assert result['success']
        assert result['fallback_used']
        assert "SELECT * FROM Sales" in result['final_expression']
        assert result['guaranteed_success']


class TestConfigurationManager:
    """Test suite for configuration management"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.config_manager = ConfigurationManager()
    
    def test_default_configuration(self):
        """Test default configuration values"""
        config = self.config_manager.get_current_config()
        
        assert isinstance(config, EnhancedMigrationConfig)
        assert config.validation_enabled
        assert config.fallback_enabled
        assert config.reporting_enabled
    
    def test_configuration_update(self):
        """Test configuration updates"""
        updates = {
            'validation_strictness': 'high',
            'fallback_threshold': 0.9,
            'enable_select_star_fallback': False
        }
        
        self.config_manager.update_config(updates)
        config = self.config_manager.get_current_config()
        
        assert config.validation_strictness == 'high'
        assert config.fallback_threshold == 0.9
        assert not config.enable_select_star_fallback
    
    def test_configuration_validation(self):
        """Test configuration validation"""
        invalid_config = {
            'validation_strictness': 'invalid_level',
            'fallback_threshold': 1.5  # Should be between 0 and 1
        }
        
        with pytest.raises(ValueError):
            self.config_manager.update_config(invalid_config)


class TestMigrationReporter:
    """Test suite for migration reporting"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.reporter = MigrationReporter(
            output_directory=self.temp_dir,
            module_id="test_module"
        )
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    def test_validation_report_generation(self):
        """Test generation of validation reports"""
        validation_data = {
            'total_expressions': 10,
            'validated_expressions': 8,
            'failed_validations': 2,
            'fallbacks_used': 3,
            'success_rate': 0.8
        }
        
        report = self.reporter.generate_validation_report(validation_data)
        
        assert 'validation_summary' in report
        assert 'expression_details' in report
        assert report['validation_summary']['success_rate'] == 0.8
    
    def test_html_report_generation(self):
        """Test HTML report generation"""
        migration_data = {
            'module_id': 'test_module',
            'timestamp': datetime.now().isoformat(),
            'validation_results': {'success_rate': 0.9},
            'fallback_usage': {'total_fallbacks': 5}
        }
        
        html_path = self.reporter.generate_html_report(migration_data)
        
        assert Path(html_path).exists()
        assert Path(html_path).suffix == '.html'
        
        # Verify HTML content
        with open(html_path, 'r') as f:
            content = f.read()
            assert 'test_module' in content
            assert 'success_rate' in content
    
    def test_comprehensive_report(self):
        """Test comprehensive report generation"""
        migration_data = {
            'module_id': 'test_module',
            'success': True,
            'validation_results': {'success_rate': 0.95},
            'performance_metrics': {'processing_time': 120}
        }
        
        report = self.reporter.generate_comprehensive_report(migration_data)
        
        assert 'executive_summary' in report
        assert 'detailed_results' in report
        assert 'recommendations' in report
        assert report['executive_summary']['overall_success']


class TestEnhancedConverters:
    """Test suite for enhanced converters"""
    
    def setup_method(self):
        """Setup test fixtures"""
        # Mock LLM service
        self.mock_llm_service = Mock()
        
        # Initialize enhanced converters
        self.expression_converter = EnhancedExpressionConverter(
            llm_service_client=self.mock_llm_service
        )
        self.mquery_converter = EnhancedMQueryConverter(
            llm_service_client=self.mock_llm_service
        )
    
    def test_enhanced_expression_conversion_success(self):
        """Test successful enhanced expression conversion"""
        # Mock successful LLM response
        self.mock_llm_service.convert_expression.return_value = {
            'success': True,
            'dax_expression': 'SUM(Sales[Amount])'
        }
        
        result = self.expression_converter.convert_expression("total([Sales])")
        
        assert result['success']
        assert result['dax_expression'] == 'SUM(Sales[Amount])'
        assert not result['fallback_used']
    
    def test_enhanced_expression_conversion_with_fallback(self):
        """Test enhanced expression conversion with fallback"""
        # Mock failed LLM response
        self.mock_llm_service.convert_expression.return_value = {
            'success': False,
            'error': 'Conversion failed'
        }
        
        result = self.expression_converter.convert_expression("invalid_expression")
        
        assert result['success']  # Should succeed via fallback
        assert result['fallback_used']
        assert result['dax_expression'] is not None
    
    def test_enhanced_mquery_conversion_with_select_star(self):
        """Test enhanced M-Query conversion with SELECT * fallback"""
        # Mock failed LLM response
        self.mock_llm_service.convert_to_mquery.return_value = {
            'success': False,
            'error': 'Complex query failed'
        }
        
        result = self.mquery_converter.convert_to_mquery(
            cognos_query="complex join query",
            table_name="Sales",
            server="localhost",
            database="TestDB"
        )
        
        assert result['success']
        assert result['fallback_used']
        assert "SELECT * FROM Sales" in result['mquery']
        assert result['guaranteed_success']


class TestIntegrationScenarios:
    """Integration tests for complete validation workflow"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    def test_end_to_end_validation_workflow(self):
        """Test complete validation workflow from expression to report"""
        # Mock components
        mock_llm_service = Mock()
        mock_llm_service.convert_expression.return_value = {
            'success': False,
            'error': 'Service unavailable'
        }
        
        # Initialize workflow components
        strategy = FallbackStrategy()
        strategy.llm_service = mock_llm_service
        
        reporter = MigrationReporter(
            output_directory=self.temp_dir,
            module_id="integration_test"
        )
        
        # Test expressions
        test_expressions = [
            "total([Sales])",
            "sum([Revenue] for [Region] = 'US')",
            "invalid_expression"
        ]
        
        results = []
        for expr in test_expressions:
            result = strategy.convert_with_fallback(expr, "dax")
            results.append(result)
        
        # Generate reports
        migration_data = {
            'module_id': 'integration_test',
            'expression_results': results,
            'total_expressions': len(test_expressions),
            'fallbacks_used': sum(1 for r in results if r.get('fallback_used', False))
        }
        
        report = reporter.generate_comprehensive_report(migration_data)
        
        # Verify end-to-end success
        assert all(result['success'] for result in results)
        assert report['executive_summary']['overall_success']
        assert len(results) == len(test_expressions)


# Performance benchmarking tests
class TestPerformanceBenchmarks:
    """Performance benchmark tests for validation framework"""
    
    def test_validation_performance(self):
        """Test validation performance with large datasets"""
        validator = ExpressionValidator()
        
        # Generate test expressions
        test_expressions = [f"SUM(Table{i}[Amount{i}])" for i in range(100)]
        
        import time
        start_time = time.time()
        
        results = []
        for expr in test_expressions:
            result = validator.validate_dax_expression(expr)
            results.append(result)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Performance assertions
        assert processing_time < 5.0  # Should complete within 5 seconds
        assert all(result['is_valid'] for result in results)
        
        # Calculate expressions per second
        eps = len(test_expressions) / processing_time
        assert eps > 20  # Should process at least 20 expressions per second
    
    def test_fallback_strategy_performance(self):
        """Test fallback strategy performance"""
        strategy = FallbackStrategy()
        
        # Mock always-failing LLM service to test fallback speed
        mock_llm_service = Mock()
        mock_llm_service.convert_expression.return_value = {
            'success': False,
            'error': 'Always fails for testing'
        }
        strategy.llm_service = mock_llm_service
        
        test_expressions = [f"total([Sales{i}])" for i in range(50)]
        
        import time
        start_time = time.time()
        
        results = []
        for expr in test_expressions:
            result = strategy.convert_with_fallback(expr, "dax")
            results.append(result)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Performance assertions
        assert processing_time < 10.0  # Should complete within 10 seconds
        assert all(result['success'] for result in results)  # All should succeed via fallback
        assert all(result['fallback_used'] for result in results)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])