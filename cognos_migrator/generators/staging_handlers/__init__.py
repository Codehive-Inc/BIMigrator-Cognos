"""
Staging handlers package for different data model processing approaches.

This package contains specialized handlers for different combinations of:
- Model handling: star_schema vs merged_tables
- Data load mode: import vs direct_query
"""

from .base_handler import BaseHandler
from .star_schema_handler import StarSchemaHandler
from .merged_tables_handler import MergedTablesHandler

__all__ = [
    'BaseHandler',
    'StarSchemaHandler', 
    'MergedTablesHandler'
]