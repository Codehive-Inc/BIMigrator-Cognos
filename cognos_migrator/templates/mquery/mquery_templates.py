"""
M-Query Template System for Power BI Data Source Generation

This module provides templates for generating M-Query expressions for various
data sources and scenarios commonly used in Cognos to Power BI migrations.
"""

from typing import Dict, List, Any, Optional
from enum import Enum
import re


class DataSourceType(Enum):
    """Enumeration of supported data source types"""
    SQL_SERVER = "sql_server"
    ORACLE = "oracle"
    DB2 = "db2"
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    EXCEL = "excel"
    CSV = "csv"
    ODATA = "odata"
    WEB_API = "web_api"
    SHAREPOINT = "sharepoint"


class MQueryTemplate:
    """Base class for M-Query templates"""
    
    def __init__(self, template_name: str, description: str):
        self.template_name = template_name
        self.description = description
    
    def generate(self, context: Dict[str, Any]) -> str:
        """Generate M-Query from template with given context"""
        raise NotImplementedError("Subclasses must implement generate method")
    
    def validate_context(self, context: Dict[str, Any]) -> List[str]:
        """Validate required context parameters"""
        return []


class SQLDatabaseTemplate(MQueryTemplate):
    """Template for SQL database connections"""
    
    def __init__(self):
        super().__init__(
            "sql_database",
            "Standard SQL database connection with query"
        )
    
    def generate(self, context: Dict[str, Any]) -> str:
        """Generate SQL database M-Query"""
        server = context.get('server', 'localhost')
        database = context.get('database', 'DefaultDB')
        query = context.get('query', 'SELECT * FROM Table1')
        table_name = context.get('table_name', 'Table1')
        
        # Clean and format the query
        formatted_query = self._format_sql_query(query)
        
        template = f'''let
    Source = Sql.Database("{server}", "{database}"),
    {table_name} = Source{{[Schema="{context.get('schema', 'dbo')}", Item="{table_name}"]}}{{"[Data]"}},
    QueryResult = Value.NativeQuery(Source, "{formatted_query}")
in
    QueryResult'''
        
        return template
    
    def validate_context(self, context: Dict[str, Any]) -> List[str]:
        """Validate SQL database context"""
        errors = []
        required_fields = ['server', 'database']
        
        for field in required_fields:
            if not context.get(field):
                errors.append(f"Missing required field: {field}")
        
        return errors
    
    def _format_sql_query(self, query: str) -> str:
        """Format SQL query for M-Query embedding"""
        # Escape double quotes
        query = query.replace('"', '""')
        # Remove excessive whitespace
        query = re.sub(r'\s+', ' ', query.strip())
        return query


class SelectStarFallbackTemplate(MQueryTemplate):
    """Template for SELECT * fallback queries"""
    
    def __init__(self):
        super().__init__(
            "select_star_fallback",
            "Safe SELECT * fallback for guaranteed data loading"
        )
    
    def generate(self, context: Dict[str, Any]) -> str:
        """Generate SELECT * fallback M-Query"""
        server = context.get('server', 'localhost')
        database = context.get('database', 'DefaultDB')
        table_name = context.get('table_name', 'Table1')
        schema = context.get('schema', 'dbo')
        
        template = f'''let
    Source = Sql.Database("{server}", "{database}"),
    Navigation = Source{{[Schema="{schema}", Item="{table_name}"]}}{{"[Data]"}},
    // Fallback: Simple SELECT * to ensure data loads
    SelectAll = Value.NativeQuery(Source, "SELECT * FROM {schema}.{table_name}")
in
    SelectAll'''
        
        return template


class DirectQueryTemplate(MQueryTemplate):
    """Template for DirectQuery mode connections"""
    
    def __init__(self):
        super().__init__(
            "direct_query",
            "DirectQuery connection for real-time data access"
        )
    
    def generate(self, context: Dict[str, Any]) -> str:
        """Generate DirectQuery M-Query"""
        server = context.get('server', 'localhost')
        database = context.get('database', 'DefaultDB')
        table_name = context.get('table_name', 'Table1')
        schema = context.get('schema', 'dbo')
        
        template = f'''let
    Source = Sql.Database("{server}", "{database}", [CreateNavigationProperties=false]),
    {table_name} = Source{{[Schema="{schema}", Item="{table_name}"]}}{{"[Data]"}}
in
    {table_name}'''
        
        return template


class AdvancedQueryTemplate(MQueryTemplate):
    """Template for advanced queries with joins and transformations"""
    
    def __init__(self):
        super().__init__(
            "advanced_query",
            "Advanced query with joins, filters, and transformations"
        )
    
    def generate(self, context: Dict[str, Any]) -> str:
        """Generate advanced M-Query"""
        server = context.get('server', 'localhost')
        database = context.get('database', 'DefaultDB')
        query = context.get('query', '')
        enable_folding = context.get('enable_folding', True)
        
        folding_hint = "true" if enable_folding else "false"
        
        template = f'''let
    Source = Sql.Database("{server}", "{database}", [EnableFolding={folding_hint}]),
    CustomQuery = Value.NativeQuery(Source, "{self._format_sql_query(query)}")
in
    CustomQuery'''
        
        return template
    
    def _format_sql_query(self, query: str) -> str:
        """Format complex SQL query"""
        # Escape double quotes
        query = query.replace('"', '""')
        # Format for readability while keeping it single line for M-Query
        query = re.sub(r'\s+', ' ', query.strip())
        return query


class ODataTemplate(MQueryTemplate):
    """Template for OData feed connections"""
    
    def __init__(self):
        super().__init__(
            "odata_feed",
            "OData feed connection for web services"
        )
    
    def generate(self, context: Dict[str, Any]) -> str:
        """Generate OData M-Query"""
        url = context.get('url', 'https://services.odata.org/V4/Northwind/Northwind.svc/')
        entity_set = context.get('entity_set', 'Products')
        
        template = f'''let
    Source = OData.Feed("{url}"),
    {entity_set}_Table = Source{{{entity_set}}},
    Navigation = {entity_set}_Table{{[Name="{entity_set}"]}}{{[Data]}}
in
    Navigation'''
        
        return template


class ExcelTemplate(MQueryTemplate):
    """Template for Excel file connections"""
    
    def __init__(self):
        super().__init__(
            "excel_workbook",
            "Excel workbook connection"
        )
    
    def generate(self, context: Dict[str, Any]) -> str:
        """Generate Excel M-Query"""
        file_path = context.get('file_path', 'C:\\Data\\Workbook.xlsx')
        sheet_name = context.get('sheet_name', 'Sheet1')
        has_headers = context.get('has_headers', True)
        
        template = f'''let
    Source = Excel.Workbook(File.Contents("{file_path}"), null, true),
    {sheet_name}_Sheet = Source{{[Item="{sheet_name}",Kind="Sheet"]}}{{[Data]}},
    #"Promoted Headers" = Table.PromoteHeaders({sheet_name}_Sheet, [PromoteAllScalars=true])
in
    #"Promoted Headers"''' if has_headers else f'''let
    Source = Excel.Workbook(File.Contents("{file_path}"), null, true),
    {sheet_name}_Sheet = Source{{[Item="{sheet_name}",Kind="Sheet"]}}{{[Data]}}
in
    {sheet_name}_Sheet'''
        
        return template


class MQueryTemplateManager:
    """Manager class for M-Query templates"""
    
    def __init__(self):
        self.templates = {
            'sql_database': SQLDatabaseTemplate(),
            'select_star_fallback': SelectStarFallbackTemplate(),
            'direct_query': DirectQueryTemplate(),
            'advanced_query': AdvancedQueryTemplate(),
            'odata_feed': ODataTemplate(),
            'excel_workbook': ExcelTemplate()
        }
    
    def get_template(self, template_name: str) -> Optional[MQueryTemplate]:
        """Get template by name"""
        return self.templates.get(template_name)
    
    def list_templates(self) -> List[str]:
        """List available template names"""
        return list(self.templates.keys())
    
    def generate_mquery(self, template_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate M-Query using specified template"""
        template = self.get_template(template_name)
        if not template:
            return {
                'success': False,
                'error': f'Template not found: {template_name}',
                'available_templates': self.list_templates()
            }
        
        # Validate context
        validation_errors = template.validate_context(context)
        if validation_errors:
            return {
                'success': False,
                'error': 'Context validation failed',
                'validation_errors': validation_errors
            }
        
        try:
            mquery = template.generate(context)
            return {
                'success': True,
                'mquery': mquery,
                'template_name': template_name,
                'template_description': template.description
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Template generation failed: {str(e)}'
            }
    
    def add_template(self, name: str, template: MQueryTemplate):
        """Add custom template"""
        self.templates[name] = template
    
    def get_template_info(self) -> Dict[str, str]:
        """Get information about all templates"""
        return {
            name: template.description 
            for name, template in self.templates.items()
        }


# Predefined template contexts for common scenarios
COMMON_CONTEXTS = {
    'sql_server_basic': {
        'server': 'localhost',
        'database': 'SalesDB',
        'table_name': 'Sales',
        'schema': 'dbo',
        'query': 'SELECT * FROM dbo.Sales'
    },
    
    'sql_server_with_filter': {
        'server': 'localhost',
        'database': 'SalesDB',
        'table_name': 'Sales',
        'schema': 'dbo',
        'query': 'SELECT * FROM dbo.Sales WHERE Year >= 2023'
    },
    
    'oracle_basic': {
        'server': 'oracle-server',
        'database': 'ORCL',
        'table_name': 'SALES',
        'schema': 'SALES_SCHEMA',
        'query': 'SELECT * FROM SALES_SCHEMA.SALES'
    },
    
    'select_star_fallback': {
        'server': 'localhost',
        'database': 'DefaultDB',
        'table_name': 'FactSales',
        'schema': 'dbo'
    }
}


def get_template_manager() -> MQueryTemplateManager:
    """Get singleton template manager instance"""
    if not hasattr(get_template_manager, '_instance'):
        get_template_manager._instance = MQueryTemplateManager()
    return get_template_manager._instance


def generate_mquery_from_template(template_name: str, context: Dict[str, Any]) -> str:
    """Convenience function to generate M-Query from template"""
    manager = get_template_manager()
    result = manager.generate_mquery(template_name, context)
    
    if result['success']:
        return result['mquery']
    else:
        raise ValueError(f"Template generation failed: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    # Example usage
    manager = get_template_manager()
    
    # Generate SQL Server M-Query
    context = {
        'server': 'localhost',
        'database': 'SalesDB',
        'table_name': 'Sales',
        'query': 'SELECT CustomerID, SUM(Amount) as TotalSales FROM Sales GROUP BY CustomerID'
    }
    
    result = manager.generate_mquery('advanced_query', context)
    if result['success']:
        print("Generated M-Query:")
        print(result['mquery'])
    else:
        print(f"Error: {result['error']}")
    
    # Generate fallback M-Query
    fallback_result = manager.generate_mquery('select_star_fallback', {
        'server': 'localhost',
        'database': 'SalesDB',
        'table_name': 'Sales'
    })
    
    if fallback_result['success']:
        print("\nFallback M-Query:")
        print(fallback_result['mquery'])