"""
Test suite for M-Query Template System

This module tests the comprehensive M-Query template system including
template generation, validation, and integration with enhanced converters.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import M-Query template system components
from cognos_migrator.templates.mquery import (
    MQueryTemplate, MQueryTemplateManager, DataSourceType,
    SQLDatabaseTemplate, SelectStarFallbackTemplate, DirectQueryTemplate,
    AdvancedQueryTemplate, ODataTemplate, ExcelTemplate,
    get_template_manager, generate_mquery_from_template,
    COMMON_CONTEXTS
)

from cognos_migrator.templates.mquery.mquery_template_engine import (
    MQueryTemplateEngine, create_mquery_template_engine,
    integrate_mquery_templates_with_converter
)

from cognos_migrator.converters.enhanced_mquery_converter import EnhancedMQueryConverter
from cognos_migrator.models import Table, Column, DataType


class TestMQueryTemplateManager:
    """Test M-Query template manager functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.manager = get_template_manager()
    
    def test_template_manager_initialization(self):
        """Test template manager initialization"""
        assert self.manager is not None
        templates = self.manager.list_templates()
        
        # Verify all expected templates are available
        expected_templates = [
            'sql_database', 'select_star_fallback', 'direct_query',
            'advanced_query', 'odata_feed', 'excel_workbook'
        ]
        
        for template_name in expected_templates:
            assert template_name in templates
    
    def test_sql_database_template_generation(self):
        """Test SQL database template generation"""
        context = {
            'server': 'test-server',
            'database': 'TestDB',
            'table_name': 'Sales',
            'schema': 'dbo',
            'query': 'SELECT * FROM Sales WHERE Year >= 2023'
        }
        
        result = self.manager.generate_mquery('sql_database', context)
        
        assert result['success'] is True
        assert 'mquery' in result
        assert 'test-server' in result['mquery']
        assert 'TestDB' in result['mquery']
        assert 'SELECT * FROM Sales WHERE Year >= 2023' in result['mquery']
    
    def test_select_star_fallback_generation(self):
        """Test SELECT * fallback template generation"""
        context = {
            'server': 'localhost',
            'database': 'SalesDB',
            'table_name': 'CustomerSales',
            'schema': 'dbo'
        }
        
        result = self.manager.generate_mquery('select_star_fallback', context)
        
        assert result['success'] is True
        assert 'SELECT * FROM dbo.CustomerSales' in result['mquery']
        assert 'Fallback: Simple SELECT *' in result['mquery']
    
    def test_advanced_query_template(self):
        """Test advanced query template with complex SQL"""
        context = {
            'server': 'prod-server',
            'database': 'Analytics',
            'query': '''
                SELECT s.CustomerID, c.CustomerName, SUM(s.Amount) as TotalSales
                FROM Sales s 
                JOIN Customer c ON s.CustomerID = c.ID 
                WHERE s.OrderDate >= '2023-01-01'
                GROUP BY s.CustomerID, c.CustomerName
            ''',
            'enable_folding': True
        }
        
        result = self.manager.generate_mquery('advanced_query', context)
        
        assert result['success'] is True
        assert 'EnableFolding=true' in result['mquery']
        assert 'JOIN Customer' in result['mquery']
        assert 'GROUP BY' in result['mquery']
    
    def test_odata_template_generation(self):
        """Test OData template generation"""
        context = {
            'url': 'https://services.odata.org/V4/Northwind/Northwind.svc/',
            'entity_set': 'Products'
        }
        
        result = self.manager.generate_mquery('odata_feed', context)
        
        assert result['success'] is True
        assert 'OData.Feed' in result['mquery']
        assert 'Products' in result['mquery']
        assert 'Northwind.svc' in result['mquery']
    
    def test_excel_template_generation(self):
        """Test Excel template generation"""
        context = {
            'file_path': 'C:\\Data\\SalesData.xlsx',
            'sheet_name': 'Sheet1',
            'has_headers': True
        }
        
        result = self.manager.generate_mquery('excel_workbook', context)
        
        assert result['success'] is True
        assert 'Excel.Workbook' in result['mquery']
        assert 'SalesData.xlsx' in result['mquery']
        assert 'Promoted Headers' in result['mquery']
    
    def test_context_validation(self):
        """Test template context validation"""
        # Test with missing required fields
        invalid_context = {
            'table_name': 'Sales'
            # Missing server and database
        }
        
        result = self.manager.generate_mquery('sql_database', invalid_context)
        
        assert result['success'] is False
        assert 'validation_errors' in result
        assert any('server' in error for error in result['validation_errors'])
        assert any('database' in error for error in result['validation_errors'])
    
    def test_template_not_found(self):
        """Test handling of non-existent template"""
        result = self.manager.generate_mquery('non_existent_template', {})
        
        assert result['success'] is False
        assert 'Template not found' in result['error']
        assert 'available_templates' in result
    
    def test_common_contexts(self):
        """Test predefined common contexts"""
        # Test SQL Server basic context
        sql_context = COMMON_CONTEXTS['sql_server_basic']
        result = self.manager.generate_mquery('sql_database', sql_context)
        
        assert result['success'] is True
        assert 'localhost' in result['mquery']
        assert 'SalesDB' in result['mquery']
        
        # Test fallback context
        fallback_context = COMMON_CONTEXTS['select_star_fallback']
        result = self.manager.generate_mquery('select_star_fallback', fallback_context)
        
        assert result['success'] is True
        assert 'FactSales' in result['mquery']


class TestMQueryTemplateEngine:
    """Test M-Query template engine functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create mock template directory structure
        mquery_dir = Path(self.temp_dir) / "mquery"
        mquery_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a test template file
        test_template = mquery_dir / "test_template.mquery"
        with open(test_template, 'w') as f:
            f.write('''let
    Source = Sql.Database("{{server}}", "{{database}}"),
    TestQuery = Value.NativeQuery(Source, "{{query}}")
in
    TestQuery''')
        
        self.engine = MQueryTemplateEngine(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    def test_template_engine_initialization(self):
        """Test template engine initialization"""
        assert self.engine is not None
        assert self.engine.mquery_manager is not None
        assert self.engine.mquery_template_dir.exists()
    
    def test_generate_table_mquery_sql(self):
        """Test generating M-Query for SQL table"""
        source_info = {
            'source_type': 'sql',
            'server': 'test-server',
            'database': 'TestDB',
            'schema': 'dbo',
            'query': 'SELECT * FROM Sales'
        }
        
        result = self.engine.generate_table_mquery('Sales', source_info)
        
        assert 'test-server' in result
        assert 'TestDB' in result
        assert 'SELECT * FROM Sales' in result
    
    def test_generate_table_mquery_with_fallback(self):
        """Test generating M-Query with fallback"""
        source_info = {
            'source_type': 'sql',
            'server': 'localhost',
            'database': 'SalesDB',
            'schema': 'dbo'
        }
        
        # Test fallback generation
        result = self.engine.generate_table_mquery('Sales', source_info, use_fallback=True)
        
        assert 'SELECT * FROM dbo.Sales' in result
        assert 'Fallback: Simple SELECT *' in result
    
    def test_complex_query_detection(self):
        """Test complex query detection logic"""
        simple_query = "SELECT * FROM Sales"
        complex_query = "SELECT s.*, c.Name FROM Sales s JOIN Customer c ON s.ID = c.CustomerID"
        
        assert not self.engine._is_complex_query(simple_query)
        assert self.engine._is_complex_query(complex_query)
    
    def test_generate_mquery_with_automatic_fallback(self):
        """Test automatic fallback when primary generation fails"""
        source_info = {
            'source_type': 'sql',
            'server': 'localhost',
            'database': 'TestDB',
            'schema': 'dbo',
            'query': 'INVALID SQL SYNTAX HERE'
        }
        
        result = self.engine.generate_mquery_with_fallback('TestTable', source_info)
        
        # Should succeed with fallback even if primary fails
        assert result['success'] is True
        if result['fallback_used']:
            assert 'SELECT * FROM dbo.TestTable' in result['mquery']
    
    def test_odata_source_generation(self):
        """Test OData source M-Query generation"""
        source_info = {
            'source_type': 'odata',
            'url': 'https://services.odata.org/V4/Northwind/Northwind.svc/',
            'entity_set': 'Products'
        }
        
        result = self.engine.generate_table_mquery('Products', source_info)
        
        assert 'OData.Feed' in result
        assert 'Products' in result
        assert 'Northwind.svc' in result
    
    def test_excel_source_generation(self):
        """Test Excel source M-Query generation"""
        source_info = {
            'source_type': 'excel',
            'file_path': 'C:\\Data\\TestData.xlsx',
            'sheet_name': 'Sheet1',
            'has_headers': True
        }
        
        result = self.engine.generate_table_mquery('Sheet1', source_info)
        
        assert 'Excel.Workbook' in result
        assert 'TestData.xlsx' in result
        assert 'Promoted Headers' in result
    
    def test_list_mquery_templates(self):
        """Test listing available M-Query templates"""
        templates = self.engine.list_mquery_templates()
        
        assert isinstance(templates, dict)
        assert 'sql_database' in templates
        assert 'select_star_fallback' in templates
        assert 'advanced_query' in templates


class TestEnhancedMQueryConverterIntegration:
    """Test integration of M-Query templates with enhanced converter"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_llm_service = Mock()
        self.converter = EnhancedMQueryConverter(
            llm_service_client=self.mock_llm_service
        )
    
    def test_converter_has_template_engine(self):
        """Test that converter has template engine initialized"""
        assert hasattr(self.converter, 'template_engine')
        assert self.converter.template_engine is not None
    
    def test_generate_mquery_from_template_method(self):
        """Test template-based M-Query generation method"""
        # Create test table
        table = Table(name="TestTable", columns=[])
        
        context = {
            'server': 'localhost',
            'database': 'TestDB',
            'schema': 'dbo'
        }
        
        result = self.converter.generate_mquery_from_template(
            table=table,
            cognos_query="SELECT * FROM TestTable",
            context=context
        )
        
        assert result['success'] is True
        assert result['template_used'] is True
        assert 'mquery' in result
    
    def test_template_based_fallback_creation(self):
        """Test template-based fallback creation"""
        # Create test table
        table = Table(name="SalesTable", columns=[])
        
        context = {
            'server': 'prod-server',
            'database': 'SalesDB',
            'schema': 'sales'
        }
        
        # Test the _create_select_all_fallback method with templates
        result = self.converter._create_select_all_fallback(table, context)
        
        assert isinstance(result, str)
        assert 'prod-server' in result or 'localhost' in result  # Should use context or default
        assert 'SalesDB' in result or 'DefaultDB' in result
        assert 'SalesTable' in result
    
    def test_template_integration_with_llm_failure(self):
        """Test template fallback when LLM service fails"""
        # Mock LLM service failure
        self.mock_llm_service.convert_to_mquery.return_value = {
            'success': False,
            'error': 'LLM service unavailable'
        }
        
        table = Table(name="FailureTable", columns=[])
        context = {
            'server': 'localhost',
            'database': 'TestDB'
        }
        
        result = self.converter.generate_mquery_from_template(
            table=table,
            context=context
        )
        
        # Should still succeed via template fallback
        assert result['success'] is True
        assert result['template_used'] is True


class TestMQueryTemplatePerformance:
    """Performance tests for M-Query template system"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.manager = get_template_manager()
        self.engine = create_mquery_template_engine()
    
    def test_template_generation_performance(self):
        """Test performance of template generation"""
        import time
        
        context = COMMON_CONTEXTS['sql_server_basic']
        
        # Generate multiple templates and measure time
        start_time = time.time()
        
        for i in range(100):
            result = self.manager.generate_mquery('sql_database', context)
            assert result['success'] is True
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete within reasonable time
        assert processing_time < 5.0  # Less than 5 seconds for 100 generations
        
        # Calculate generations per second
        generations_per_second = 100 / processing_time
        assert generations_per_second > 20  # At least 20 generations per second
    
    def test_fallback_generation_performance(self):
        """Test performance of fallback generation"""
        import time
        
        source_info = {
            'source_type': 'sql',
            'server': 'localhost',
            'database': 'TestDB',
            'schema': 'dbo'
        }
        
        start_time = time.time()
        
        for i in range(50):
            result = self.engine.generate_mquery_with_fallback(f'Table{i}', source_info)
            assert result['success'] is True
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete within reasonable time
        assert processing_time < 3.0  # Less than 3 seconds for 50 generations
        
        fallbacks_per_second = 50 / processing_time
        assert fallbacks_per_second > 15  # At least 15 fallbacks per second


class TestMQueryTemplateErrorHandling:
    """Test error handling in M-Query template system"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.manager = get_template_manager()
    
    def test_invalid_template_context(self):
        """Test handling of invalid template context"""
        invalid_contexts = [
            {},  # Empty context
            {'server': ''},  # Empty server
            {'database': None},  # None values
            {'server': 'test', 'database': 'test', 'invalid_field': 'value'}  # Extra fields (should be ignored)
        ]
        
        for context in invalid_contexts:
            result = self.manager.generate_mquery('sql_database', context)
            
            if not context or any(not v for v in context.values() if v is not None):
                # Should fail validation for empty/invalid required fields
                assert result['success'] is False
            # Extra fields should be ignored and not cause failures
    
    def test_template_generation_exception_handling(self):
        """Test exception handling during template generation"""
        # Create a custom template that will raise an exception
        class FailingTemplate(MQueryTemplate):
            def __init__(self):
                super().__init__("failing_template", "Template that always fails")
            
            def generate(self, context):
                raise ValueError("Intentional test failure")
        
        # Add the failing template
        self.manager.add_template("failing_template", FailingTemplate())
        
        result = self.manager.generate_mquery("failing_template", {})
        
        assert result['success'] is False
        assert 'Template generation failed' in result['error']
        assert 'Intentional test failure' in result['error']
    
    def test_ultimate_fallback_generation(self):
        """Test ultimate fallback when all other methods fail"""
        converter = EnhancedMQueryConverter()
        
        # Test with a table that might cause issues
        table = Table(name="ProblematicTable", columns=[])
        
        # Test the basic fallback method directly
        result = converter._create_basic_fallback("TestTable", {
            'server': 'test-server',
            'database': 'test-db',
            'schema': 'test-schema'
        })
        
        assert isinstance(result, str)
        assert 'ULTIMATE FALLBACK' in result
        assert 'TestTable' in result
        assert 'test-server' in result


if __name__ == "__main__":
    # Run M-Query template tests
    pytest.main([__file__, "-v", "-s"])