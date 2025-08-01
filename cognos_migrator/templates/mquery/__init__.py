"""
M-Query Templates Package

This package provides M-Query templates for various data sources and scenarios
commonly used in Cognos to Power BI migrations.
"""

from .mquery_templates import (
    MQueryTemplate, MQueryTemplateManager, DataSourceType,
    SQLDatabaseTemplate, SelectStarFallbackTemplate, DirectQueryTemplate,
    AdvancedQueryTemplate, ODataTemplate, ExcelTemplate,
    get_template_manager, generate_mquery_from_template,
    COMMON_CONTEXTS
)

from .mquery_template_engine import (
    MQueryTemplateEngine, create_mquery_template_engine,
    integrate_mquery_templates_with_converter
)

__all__ = [
    # Template classes
    'MQueryTemplate',
    'MQueryTemplateManager', 
    'DataSourceType',
    'SQLDatabaseTemplate',
    'SelectStarFallbackTemplate',
    'DirectQueryTemplate',
    'AdvancedQueryTemplate',
    'ODataTemplate',
    'ExcelTemplate',
    
    # Template engine
    'MQueryTemplateEngine',
    'create_mquery_template_engine',
    
    # Utility functions
    'get_template_manager',
    'generate_mquery_from_template',
    'integrate_mquery_templates_with_converter',
    
    # Constants
    'COMMON_CONTEXTS'
]