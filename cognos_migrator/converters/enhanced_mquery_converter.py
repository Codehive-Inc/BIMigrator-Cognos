"""
Enhanced M-Query Converter with validation and fallback support
"""

import logging
from typing import Dict, Any, Optional, List
import json
import asyncio
from datetime import datetime

from cognos_migrator.models import Table, Column, DataType
from cognos_migrator.llm_service import LLMServiceClient
from cognos_migrator.strategies import FallbackStrategy, MigrationStrategyConfig
from cognos_migrator.validators import MQueryValidator
from cognos_migrator.templates.mquery import create_mquery_template_engine, MQueryTemplateEngine


class EnhancedMQueryConverter:
    """Enhanced M-Query converter with validation and SELECT * fallback"""
    
    def __init__(self,
                 llm_service_client: Optional[LLMServiceClient] = None,
                 strategy_config: Optional[MigrationStrategyConfig] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the enhanced M-Query converter
        
        Args:
            llm_service_client: Optional LLM service client
            strategy_config: Configuration for validation and fallback strategies
            logger: Optional logger instance
        """
        self.llm_service_client = llm_service_client
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize strategy configuration
        self.strategy_config = strategy_config or MigrationStrategyConfig()
        
        # Initialize validators and strategies
        self.mquery_validator = MQueryValidator(logger=self.logger)
        self.fallback_strategy = FallbackStrategy(
            config=self.strategy_config,
            logger=self.logger
        )
        
        # Track conversions for reporting
        self.conversion_history = []
        
        # Initialize M-Query template engine
        self.template_engine = create_mquery_template_engine()
    
    def convert_to_m_query(self, 
                          table: Table, 
                          report_spec: Optional[str] = None,
                          data_sample: Optional[Dict] = None) -> str:
        """
        Convert a table's source query to Power BI M-query format with validation
        
        Args:
            table: Table object containing source query and metadata
            report_spec: Optional report specification XML for context
            data_sample: Optional data sample for context (not used in practice)
            
        Returns:
            M-Query string (validated and safe)
        """
        start_msg = f"Converting table '{table.name}' to M-Query"
        if hasattr(table, 'source_query') and table.source_query:
            start_msg += f" with source query: {table.source_query[:100]}..."
        self.logger.info(start_msg)
        
        # Build context for conversion
        context = self._build_context(table, report_spec, data_sample)
        
        # Use asyncio to run the async conversion
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, create task
                task = asyncio.create_task(
                    self._convert_with_strategy(table, context)
                )
                result = asyncio.run_coroutine_threadsafe(
                    asyncio.wait_for(task, timeout=120),
                    loop
                ).result()
            else:
                # Otherwise run normally
                result = loop.run_until_complete(
                    self._convert_with_strategy(table, context)
                )
        except Exception as e:
            self.logger.error(f"Async conversion error: {e}")
            result = self._create_fallback_mquery(table, context, str(e))
        
        # Track conversion
        self.conversion_history.append({
            "table_name": table.name,
            "source_query": getattr(table, 'source_query', None),
            "result_length": len(result),
            "timestamp": datetime.now().isoformat()
        })
        
        return result
    
    async def _convert_with_strategy(self,
                                   table: Table,
                                   context: Dict[str, Any]) -> str:
        """Convert using fallback strategy with validation"""
        
        # Define LLM converter function
        async def llm_converter(context_data):
            if self.llm_service_client:
                try:
                    return self.llm_service_client.generate_m_query(context_data)
                except Exception as e:
                    self.logger.error(f"LLM M-Query generation failed: {e}")
                    return None
            return None
        
        # Use fallback strategy for conversion
        conversion_result = await self.fallback_strategy.convert_with_fallback(
            expression=context.get('source_query', f"Table for {table.name}"),
            expression_type="mquery",
            context=context,
            llm_converter=llm_converter
        )
        
        # Get the M-Query result
        m_query = conversion_result.converted_expression
        
        # Additional validation specific to M-Query
        if self.strategy_config.enable_post_validation:
            validation = self.mquery_validator.validate_m_query(m_query, context)
            
            if not validation["is_valid"] and self.strategy_config.enable_select_all_fallback:
                self.logger.warning(
                    f"M-Query validation failed for {table.name}: {validation['issues']}"
                )
                # Use SELECT * fallback
                m_query = self._create_select_all_fallback(table, context)
        
        return m_query
    
    def _build_context(self, 
                      table: Table, 
                      report_spec: Optional[str] = None,
                      data_sample: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Build context dictionary for LLM service and validation
        
        Args:
            table: Table object
            report_spec: Optional report specification XML
            data_sample: Optional data sample
            
        Returns:
            Context dictionary
        """
        # Build column information
        columns = []
        if hasattr(table, 'columns') and table.columns:
            for col in table.columns:
                col_info = {
                    'name': col.name,
                    'data_type': col.data_type.value if hasattr(col.data_type, 'value') else str(col.data_type)
                }
                if hasattr(col, 'description') and col.description:
                    col_info['description'] = col.description
                columns.append(col_info)
        
        # Extract source information
        source_info = self._extract_source_info(table)
        
        # Build context
        context = {
            'table_name': table.name,
            'columns': columns,
            'source_query': getattr(table, 'source_query', None),
            'report_spec': report_spec,
            'source_info': source_info,
            'query_folding_preference': self.strategy_config.query_folding_preference
        }
        
        # Add data sample if available (though typically not used)
        if data_sample:
            context['data_sample'] = data_sample
        
        return context
    
    def _extract_source_info(self, table: Table) -> Dict[str, Any]:
        """Extract source connection information from table"""
        source_info = {
            'source_type': 'unknown',
            'connection_details': {}
        }
        
        # Try to determine source type from source_query
        if hasattr(table, 'source_query') and table.source_query:
            query_lower = table.source_query.lower()
            
            if 'select' in query_lower and 'from' in query_lower:
                # Likely SQL
                source_info['source_type'] = 'sql'
                
                # Try to extract table name from query
                import re
                from_match = re.search(r'from\s+([^\s,]+)', query_lower)
                if from_match:
                    source_info['connection_details']['table'] = from_match.group(1)
        
        # Add any other table metadata that might help
        if hasattr(table, 'source_type'):
            source_info['source_type'] = table.source_type
        
        if hasattr(table, 'connection_info'):
            source_info['connection_details'].update(table.connection_info)
        
        return source_info
    
    def _create_select_all_fallback(self, 
                                  table: Table,
                                  context: Dict[str, Any]) -> str:
        """Create a SELECT * fallback M-Query using templates"""
        try:
            # Prepare source information for template
            source_info = {
                'source_type': 'sql',
                'server': context.get('server', 'localhost'),
                'database': context.get('database', 'DefaultDB'),
                'schema': context.get('schema', 'dbo'),
                'table_name': table.name
            }
            
            # Use template engine to generate fallback M-Query
            result = self.template_engine.generate_mquery_with_fallback(
                table.name, 
                source_info
            )
            
            if result['success']:
                return result['mquery']
            else:
                # Ultimate fallback if template fails
                return self._create_basic_fallback(table.name, source_info)
                
        except Exception as e:
            self.logger.warning(f"Template-based fallback failed: {e}")
            # Ultimate fallback
            return self._create_basic_fallback(table.name, {
                'server': 'localhost',
                'database': 'DefaultDB', 
                'schema': 'dbo',
                'table_name': table.name
            })
    
    def _create_basic_fallback(self, table_name: str, source_info: Dict[str, Any]) -> str:
        """Create basic fallback when all other methods fail"""
        server = source_info.get('server', 'localhost')
        database = source_info.get('database', 'DefaultDB')
        schema = source_info.get('schema', 'dbo')
        
        return f'''let
    // ULTIMATE FALLBACK: Basic SELECT * query
    // Table: {table_name}
    // Generated: {datetime.now().isoformat()}
    Source = Sql.Database("{server}", "{database}"),
    SelectAll = Value.NativeQuery(Source, "SELECT * FROM {schema}.{table_name}")
in
    SelectAll'''
    
    def generate_mquery_from_template(self, 
                                    table: Table,
                                    cognos_query: str = None,
                                    context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate M-Query using template system"""
        try:
            # Prepare source information
            source_info = {
                'source_type': 'sql',
                'server': context.get('server', 'localhost') if context else 'localhost',
                'database': context.get('database', 'DefaultDB') if context else 'DefaultDB',
                'schema': context.get('schema', 'dbo') if context else 'dbo',
                'query': cognos_query or f'SELECT * FROM {table.name}',
                'enable_folding': True
            }
            
            # Use template engine for primary generation
            result = self.template_engine.generate_mquery_with_fallback(
                table.name,
                source_info
            )
            
            if result['success']:
                return {
                    'success': True,
                    'mquery': result['mquery'],
                    'template_used': True,
                    'fallback_used': result.get('fallback_used', False),
                    'method': result.get('method', 'template')
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Template generation failed'),
                    'template_used': True
                }
                
        except Exception as e:
            self.logger.error(f"Template-based M-Query generation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'template_used': True
            }
    
    def _create_fallback_mquery(self,
                              table: Table,
                              context: Dict[str, Any],
                              error_message: str) -> str:
        """Create fallback M-Query when everything fails"""
        self.logger.error(f"Creating fallback M-Query for {table.name} due to: {error_message}")
        
        return f'''let
    // FALLBACK: Error during conversion
    // Table: {table.name}
    // Error: {error_message}
    // Generated: {datetime.now().isoformat()}
    
    // TODO: Manual configuration required
    Source = Table.FromRows(
        {{}},
        type table [
            ConfigureColumns = text
        ]
    ),
    
    ErrorMessage = "Manual configuration required - see comments above"
in
    Source'''
    
    def _map_to_m_type(self, data_type: str) -> str:
        """Map data types to M-Query types"""
        type_map = {
            'string': 'type text',
            'text': 'type text',
            'integer': 'Int64.Type',
            'int': 'Int64.Type',
            'decimal': 'type number',
            'double': 'type number',
            'float': 'type number',
            'boolean': 'type logical',
            'bool': 'type logical',
            'datetime': 'type datetime',
            'date': 'type date',
            'time': 'type time'
        }
        
        return type_map.get(data_type.lower(), 'type any')
    
    def get_conversion_report(self) -> Dict[str, Any]:
        """Get detailed conversion report"""
        
        # Get strategy report
        strategy_report = self.fallback_strategy.generate_migration_report()
        
        # Add M-Query specific stats
        enhanced_report = {
            **strategy_report,
            "mquery_stats": {
                "total_tables_converted": len(self.conversion_history),
                "tables_with_source_query": sum(
                    1 for h in self.conversion_history if h.get("source_query")
                ),
                "average_query_length": sum(
                    h.get("result_length", 0) for h in self.conversion_history
                ) / max(len(self.conversion_history), 1)
            },
            "conversion_history": self.conversion_history[-10:]  # Last 10 conversions
        }
        
        return enhanced_report
    
    def reset_history(self):
        """Clear conversion history"""
        self.conversion_history.clear()
        self.fallback_strategy.conversion_results.clear()