"""
M-Query Template Engine Extension

This module extends the existing template engine to support M-Query template
rendering with both file-based and programmatic template generation.
"""

import os
import re
from pathlib import Path
import logging
from typing import Dict, Any, List, Optional
import json

from cognos_migrator.generators.template_engine import TemplateEngine
from .mquery_templates import MQueryTemplateManager, get_template_manager


class MQueryTemplateEngine(TemplateEngine):
    """Enhanced template engine with M-Query support"""
    
    def __init__(self, template_directory: str):
        """Initialize M-Query template engine"""
        super().__init__(template_directory)
        
        # Initialize M-Query template manager
        self.mquery_manager = get_template_manager()
        
        # Set M-Query template directory
        self.mquery_template_dir = Path(template_directory) / "mquery"
        
        # Load M-Query template files
        self._load_mquery_templates()
    
    def _load_mquery_templates(self):
        """Load M-Query template files (.mquery extension)"""
        if not self.mquery_template_dir.exists():
            self.logger.warning(f"M-Query template directory not found: {self.mquery_template_dir}")
            return
        
        mquery_files = {
            'sql_database_file': {
                'filename': 'sql_database.mquery',
                'path': 'Model/tables',
                'target_filename': '{table_name}_source.mquery'
            },
            'select_star_fallback_file': {
                'filename': 'select_star_fallback.mquery', 
                'path': 'Model/tables',
                'target_filename': '{table_name}_fallback.mquery'
            },
            'direct_query_file': {
                'filename': 'direct_query.mquery',
                'path': 'Model/tables', 
                'target_filename': '{table_name}_direct.mquery'
            },
            'advanced_query_file': {
                'filename': 'advanced_query.mquery',
                'path': 'Model/tables',
                'target_filename': '{table_name}_advanced.mquery'
            },
            'odata_feed_file': {
                'filename': 'odata_feed.mquery',
                'path': 'Model/tables',
                'target_filename': '{entity_set}_odata.mquery'
            },
            'excel_workbook_file': {
                'filename': 'excel_workbook.mquery',
                'path': 'Model/tables',
                'target_filename': '{sheet_name}_excel.mquery'
            }
        }
        
        # Load M-Query template files
        for template_name, template_info in mquery_files.items():
            template_path = self.mquery_template_dir / template_info['filename']
            if template_path.exists():
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                
                # Store as raw template - do simple string replacement instead of Jinja2 parsing
                self.templates[template_name] = template_content
                self.template_info[template_name] = template_info
                
                self.logger.info(f"Loaded M-Query template: {template_name}")
            else:
                self.logger.warning(f"M-Query template file not found: {template_path}")
    
    def render_mquery(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render M-Query using programmatic templates"""
        result = self.mquery_manager.generate_mquery(template_name, context)
        
        if result['success']:
            return result['mquery']
        else:
            raise ValueError(f"M-Query generation failed: {result.get('error', 'Unknown error')}")
    
    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Override render to handle raw string templates with simple substitution"""
        if template_name not in self.templates:
            raise ValueError(f"Template not found: {template_name}")
        
        template_content = self.templates[template_name]
        
        # If it's a raw string (not a Jinja2 Template object), do simple substitution
        if isinstance(template_content, str):
            result = template_content
            for key, value in context.items():
                result = result.replace(f"{{{{{key}}}}}", str(value))
            return result
        else:
            # Fall back to parent render method for Jinja2 templates
            return super().render(template_name, context)
    
    def render_mquery_file(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render M-Query using file-based templates"""
        file_template_name = f"{template_name}_file"
        
        if file_template_name not in self.templates:
            raise ValueError(f"M-Query file template not found: {file_template_name}")
        
        return self.render(file_template_name, context)
    
    def generate_table_mquery(self, table_name: str, source_info: Dict[str, Any], 
                             use_fallback: bool = False) -> str:
        """Generate M-Query for a table based on source information"""
        
        # Determine the appropriate template based on source type
        source_type = source_info.get('source_type', 'sql').lower()
        
        context = {
            'table_name': table_name,
            'server': source_info.get('server', 'localhost'),
            'database': source_info.get('database', 'DefaultDB'),
            'schema': source_info.get('schema', 'dbo'),
            'query': source_info.get('query', f'SELECT * FROM {table_name}'),
            'enable_folding': source_info.get('enable_folding', True)
        }
        
        if use_fallback:
            # Use fallback template for guaranteed success
            return self.render_mquery('select_star_fallback', context)
        
        # Select template based on source type and complexity
        if source_type in ['sql_server', 'sql', 'database']:
            query = context.get('query', '')
            
            # Check query complexity
            if self._is_complex_query(query):
                try:
                    return self.render_mquery('advanced_query', context)
                except Exception:
                    # Fall back to SELECT * if advanced query fails
                    return self.render_mquery('select_star_fallback', context)
            else:
                return self.render_mquery('sql_database', context)
        
        elif source_type == 'odata':
            context.update({
                'url': source_info.get('url', 'https://services.odata.org/V4/service/'),
                'entity_set': source_info.get('entity_set', table_name)
            })
            return self.render_mquery('odata_feed', context)
        
        elif source_type == 'excel':
            context.update({
                'file_path': source_info.get('file_path', f'C:\\Data\\{table_name}.xlsx'),
                'sheet_name': source_info.get('sheet_name', table_name),
                'has_headers': source_info.get('has_headers', True)
            })
            return self.render_mquery('excel_workbook', context)
        
        else:
            # Default to SQL database template
            return self.render_mquery('sql_database', context)
    
    def _is_complex_query(self, query: str) -> bool:
        """Determine if a query is complex and needs advanced template"""
        if not query:
            return False
        
        query_lower = query.lower()
        complex_indicators = [
            'join', 'union', 'case when', 'group by', 'having',
            'window', 'partition', 'with', 'exists', 'in (',
            'subquery', 'cte'
        ]
        
        return any(indicator in query_lower for indicator in complex_indicators)
    
    def validate_mquery_context(self, template_name: str, context: Dict[str, Any]) -> List[str]:
        """Validate context for M-Query template"""
        template = self.mquery_manager.get_template(template_name)
        if template:
            return template.validate_context(context)
        return []
    
    def list_mquery_templates(self) -> Dict[str, str]:
        """List available M-Query templates with descriptions"""
        programmatic = self.mquery_manager.get_template_info()
        
        file_based = {}
        for name, info in self.template_info.items():
            if name.endswith('_file') and name.replace('_file', '') in programmatic:
                base_name = name.replace('_file', '')
                file_based[f"{base_name}_file"] = f"File-based template for {programmatic[base_name]}"
        
        return {**programmatic, **file_based}
    
    def generate_mquery_with_fallback(self, table_name: str, source_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate M-Query with automatic fallback on failure"""
        try:
            # Try primary generation
            mquery = self.generate_table_mquery(table_name, source_info, use_fallback=False)
            
            return {
                'success': True,
                'mquery': mquery,
                'fallback_used': False,
                'method': 'primary'
            }
            
        except Exception as primary_error:
            self.logger.warning(f"Primary M-Query generation failed: {primary_error}")
            
            try:
                # Try fallback generation
                mquery = self.generate_table_mquery(table_name, source_info, use_fallback=True)
                
                return {
                    'success': True,
                    'mquery': mquery,
                    'fallback_used': True,
                    'method': 'fallback',
                    'primary_error': str(primary_error)
                }
                
            except Exception as fallback_error:
                return {
                    'success': False,
                    'error': f'Both primary and fallback generation failed',
                    'primary_error': str(primary_error),
                    'fallback_error': str(fallback_error)
                }


def create_mquery_template_engine(template_directory: str = None) -> MQueryTemplateEngine:
    """Create M-Query template engine instance"""
    if template_directory is None:
        # Use default template directory - parent.parent is cognos_migrator, then templates
        current_dir = Path(__file__).parent.parent.parent  # Go up from mquery -> templates -> cognos_migrator
        template_directory = current_dir / "templates"
    
    return MQueryTemplateEngine(str(template_directory))


# Integration with existing converters
def integrate_mquery_templates_with_converter():
    """Integration function for enhanced M-Query converter"""
    
    def create_mquery_from_template(cognos_query: str, table_name: str, 
                                   server: str, database: str,
                                   schema: str = 'dbo') -> Dict[str, Any]:
        """Create M-Query using template system"""
        
        engine = create_mquery_template_engine()
        
        source_info = {
            'source_type': 'sql',
            'server': server,
            'database': database,
            'schema': schema,
            'query': cognos_query,
            'enable_folding': True
        }
        
        return engine.generate_mquery_with_fallback(table_name, source_info)
    
    return create_mquery_from_template


# Usage examples and testing
if __name__ == "__main__":
    # Example usage
    engine = create_mquery_template_engine()
    
    # List available templates
    print("Available M-Query templates:")
    for name, desc in engine.list_mquery_templates().items():
        print(f"  {name}: {desc}")
    
    # Generate SQL Server M-Query
    source_info = {
        'source_type': 'sql',
        'server': 'localhost',
        'database': 'SalesDB',
        'schema': 'dbo',
        'query': 'SELECT CustomerID, SUM(Amount) as TotalSales FROM Sales WHERE Year >= 2023 GROUP BY CustomerID'
    }
    
    result = engine.generate_mquery_with_fallback('CustomerSales', source_info)
    
    if result['success']:
        print(f"\nGenerated M-Query (Method: {result['method']}):")
        print(result['mquery'])
        
        if result['fallback_used']:
            print(f"\nFallback was used due to: {result.get('primary_error', 'Unknown error')}")
    else:
        print(f"\nM-Query generation failed: {result['error']}")
    
    # Generate fallback M-Query
    print("\n" + "="*50)
    print("Testing SELECT * fallback:")
    
    fallback_result = engine.generate_table_mquery(
        'Sales', 
        {'server': 'localhost', 'database': 'SalesDB', 'schema': 'dbo'},
        use_fallback=True
    )
    
    print(fallback_result)