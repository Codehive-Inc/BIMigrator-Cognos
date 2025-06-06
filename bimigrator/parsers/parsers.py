"""
Parsers for Cognos API responses and data structures
"""

import json
import re
from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime

from .models import (
    Column, Table, DataType, QueryDefinition, 
    CognosReport, DataSource, Measure, Relationship
)


class CognosAPIParser:
    """Parser for Cognos Analytics API responses"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse_report_from_api(self, report_data: dict, report_metadata: dict = None) -> CognosReport:
        """Parse Cognos report data from API response into structured format"""
        try:
            # Extract basic report information from API response
            report_name = report_data.get('defaultName', 'Unknown Report')
            report_id = report_data.get('id', '')
            report_type = report_data.get('type', 'report')
            
            # Parse data sources from API metadata
            data_sources = self._parse_data_sources_from_api(report_metadata or {})
            
            # Parse queries and data items from API
            queries = self._parse_queries_from_api(report_metadata or {})
            
            # Parse layout and visualizations from API
            layout = self._parse_layout_from_api(report_metadata or {})
            
            return CognosReport(
                id=report_id,
                name=report_name,
                data_sources=data_sources,
                queries=queries,
                layout=layout,
                metadata=report_metadata or {}
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing Cognos report from API: {e}")
            raise ValueError(f"Failed to parse Cognos report data: {e}")
    
    def parse_datasource_from_api(self, datasource_data: dict) -> DataSource:
        """Parse data source information from API response"""
        try:
            return DataSource(
                id=datasource_data.get('id', ''),
                name=datasource_data.get('defaultName', 'Unknown DataSource'),
                type=datasource_data.get('type', 'database'),
                connection_string=self._extract_connection_info(datasource_data),
                capabilities=datasource_data.get('capabilities', [])
            )
        except Exception as e:
            self.logger.error(f"Error parsing data source from API: {e}")
            raise ValueError(f"Failed to parse data source: {e}")
    
    def parse_schema_from_api(self, schema_data: dict) -> Dict[str, Any]:
        """Parse schema information from API response"""
        try:
            return {
                'id': schema_data.get('id', ''),
                'name': schema_data.get('defaultName', 'Unknown Schema'),
                'catalog': schema_data.get('catalog', ''),
                'schema': schema_data.get('schema', ''),
                'tables': self._extract_tables_from_schema(schema_data),
                'status': schema_data.get('status', 'unknown')
            }
        except Exception as e:
            self.logger.error(f"Error parsing schema from API: {e}")
            return {}
    
    def parse_table_metadata_from_api(self, table_data: List[str], schema_info: dict) -> List[Dict[str, Any]]:
        """Parse table metadata from API response"""
        tables = []
        
        for table_name in table_data:
            table_info = {
                'name': table_name,
                'schema': schema_info.get('schema', ''),
                'catalog': schema_info.get('catalog', ''),
                'full_name': f"{schema_info.get('catalog', '')}.{schema_info.get('schema', '')}.{table_name}",
                'columns': []  # Will be populated by separate API call
            }
            tables.append(table_info)
        
        return tables
    
    def _parse_data_sources_from_api(self, metadata: dict) -> List[DataSource]:
        """Extract data sources from API metadata"""
        data_sources = []
        
        # Look for data source references in metadata
        if 'dataSources' in metadata:
            for ds_data in metadata['dataSources']:
                data_source = DataSource(
                    id=ds_data.get('id', ''),
                    name=ds_data.get('name', 'Unknown'),
                    type=ds_data.get('type', 'database'),
                    connection_string=ds_data.get('connectionString', ''),
                    capabilities=ds_data.get('capabilities', [])
                )
                data_sources.append(data_source)
        
        return data_sources
    
    def _parse_queries_from_api(self, metadata: dict) -> List[QueryDefinition]:
        """Extract query definitions from API metadata"""
        queries = []
        
        # Look for query information in metadata
        if 'queries' in metadata:
            for query_data in metadata['queries']:
                query = QueryDefinition(
                    name=query_data.get('name', 'Unknown Query'),
                    sql=query_data.get('sql', ''),
                    data_items=query_data.get('dataItems', []),
                    filters=query_data.get('filters', []),
                    parameters=query_data.get('parameters', [])
                )
                queries.append(query)
        
        return queries
    
    def _parse_layout_from_api(self, metadata: dict) -> Dict[str, Any]:
        """Extract layout information from API metadata"""
        layout = {
            'pages': [],
            'sections': [],
            'visualizations': []
        }
        
        # Extract layout information if available
        if 'layout' in metadata:
            layout_data = metadata['layout']
            layout['pages'] = layout_data.get('pages', [])
            layout['sections'] = layout_data.get('sections', [])
            layout['visualizations'] = layout_data.get('visualizations', [])
        
        return layout
    
    def _extract_connection_info(self, datasource_data: dict) -> str:
        """Extract connection string from data source data"""
        # Look for connection information in various places
        if 'connections' in datasource_data:
            connections = datasource_data['connections']
            if connections and len(connections) > 0:
                return connections[0].get('connectionString', '')
        
        return datasource_data.get('connectionString', '')
    
    def _extract_tables_from_schema(self, schema_data: dict) -> List[str]:
        """Extract table names from schema data"""
        tables = []
        
        if 'tables' in schema_data:
            if isinstance(schema_data['tables'], list):
                tables = schema_data['tables']
            elif isinstance(schema_data['tables'], dict):
                tables = list(schema_data['tables'].keys())
        
        return tables


class DataTypeMapper:
    """Maps Cognos data types to Power BI data types"""
    
    TYPE_MAPPING = {
        'string': DataType.STRING,
        'varchar': DataType.STRING,
        'char': DataType.STRING,
        'text': DataType.STRING,
        'nvarchar': DataType.STRING,
        'nchar': DataType.STRING,
        'integer': DataType.INTEGER,
        'int': DataType.INTEGER,
        'bigint': DataType.INTEGER,
        'smallint': DataType.INTEGER,
        'tinyint': DataType.INTEGER,
        'decimal': DataType.DECIMAL,
        'numeric': DataType.DECIMAL,
        'money': DataType.DECIMAL,
        'float': DataType.DOUBLE,
        'double': DataType.DOUBLE,
        'real': DataType.DOUBLE,
        'boolean': DataType.BOOLEAN,
        'bit': DataType.BOOLEAN,
        'date': DataType.DATE,
        'datetime': DataType.DATE,
        'datetime2': DataType.DATE,
        'timestamp': DataType.DATE,
        'time': DataType.DATE,
        'uniqueidentifier': DataType.STRING,
        'guid': DataType.STRING
    }
    
    @classmethod
    def map_data_type(cls, cognos_type: str) -> DataType:
        """Map Cognos data type to Power BI data type"""
        return cls.TYPE_MAPPING.get(cognos_type.lower(), DataType.STRING)


class QueryAnalyzer:
    """Analyzes SQL queries and data transformations from API responses"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_query_from_api(self, query_data: dict) -> Dict[str, Any]:
        """Analyze query information from API response"""
        try:
            analysis = {
                'tables': [],
                'columns': [],
                'joins': [],
                'filters': [],
                'aggregations': [],
                'data_items': []
            }
            
            # Extract SQL if present
            sql = query_data.get('sql', '')
            if sql:
                analysis.update(self._analyze_sql(sql))
            
            # Extract data items
            data_items = query_data.get('dataItems', [])
            analysis['data_items'] = self._analyze_data_items(data_items)
            
            # Extract filters
            filters = query_data.get('filters', [])
            analysis['filters'] = self._analyze_filters(filters)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze query from API: {e}")
            return {}
    
    def _analyze_sql(self, sql: str) -> Dict[str, Any]:
        """Analyze SQL query to extract structural information"""
        try:
            return {
                'tables': self._extract_tables_from_sql(sql),
                'columns': self._extract_columns_from_sql(sql),
                'joins': self._extract_joins_from_sql(sql),
                'aggregations': self._extract_aggregations_from_sql(sql)
            }
        except Exception as e:
            self.logger.error(f"Failed to analyze SQL: {e}")
            return {}
    
    def _analyze_data_items(self, data_items: List[dict]) -> List[Dict[str, Any]]:
        """Analyze data items from API response"""
        analyzed_items = []
        
        for item in data_items:
            analyzed_item = {
                'name': item.get('name', ''),
                'expression': item.get('expression', ''),
                'data_type': item.get('dataType', 'string'),
                'usage': item.get('usage', 'fact'),
                'is_measure': self._is_measure(item),
                'is_dimension': self._is_dimension(item)
            }
            analyzed_items.append(analyzed_item)
        
        return analyzed_items
    
    def _analyze_filters(self, filters: List[dict]) -> List[Dict[str, Any]]:
        """Analyze filter definitions from API response"""
        analyzed_filters = []
        
        for filter_item in filters:
            analyzed_filter = {
                'expression': filter_item.get('expression', ''),
                'usage': filter_item.get('usage', 'optional'),
                'type': self._determine_filter_type(filter_item)
            }
            analyzed_filters.append(analyzed_filter)
        
        return analyzed_filters
    
    def _extract_tables_from_sql(self, sql: str) -> List[str]:
        """Extract table names from SQL query"""
        tables = []
        
        # Simple regex patterns for table extraction
        from_pattern = r'FROM\s+([^\s,\(\)]+)'
        join_pattern = r'JOIN\s+([^\s,\(\)]+)'
        
        from_matches = re.findall(from_pattern, sql, re.IGNORECASE)
        join_matches = re.findall(join_pattern, sql, re.IGNORECASE)
        
        all_tables = from_matches + join_matches
        
        # Clean up table names
        for table in all_tables:
            # Remove schema prefix and aliases
            clean_table = table.split('.')[-1].split()[0]
            if clean_table not in tables:
                tables.append(clean_table)
        
        return tables
    
    def _extract_columns_from_sql(self, sql: str) -> List[str]:
        """Extract column names from SQL SELECT clause"""
        columns = []
        
        # Find SELECT clause
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
        if select_match:
            select_clause = select_match.group(1)
            
            # Split by comma and clean up
            column_parts = [part.strip() for part in select_clause.split(',')]
            
            for part in column_parts:
                if part == '*':
                    continue
                
                # Handle aliases
                if ' AS ' in part.upper():
                    column_name = part.split(' AS ')[-1].strip()
                elif ' ' in part and not any(func in part.upper() for func in ['SUM', 'COUNT', 'AVG', 'MAX', 'MIN']):
                    column_name = part.split()[-1].strip()
                else:
                    # Extract column name
                    if '.' in part:
                        column_name = part.split('.')[-1].strip()
                    else:
                        column_name = part.strip()
                
                # Clean up column name
                column_name = column_name.strip('"\'[]')
                if column_name:
                    columns.append(column_name)
        
        return columns
    
    def _extract_joins_from_sql(self, sql: str) -> List[Dict[str, str]]:
        """Extract JOIN information from SQL"""
        joins = []
        
        join_pattern = r'(LEFT|RIGHT|INNER|OUTER)?\s*JOIN\s+([^\s]+)\s+ON\s+([^WHERE|GROUP|ORDER|HAVING|JOIN]+)'
        matches = re.findall(join_pattern, sql, re.IGNORECASE)
        
        for match in matches:
            join_type = match[0].strip() if match[0] else 'INNER'
            table = match[1].strip()
            condition = match[2].strip()
            
            joins.append({
                'type': join_type,
                'table': table,
                'condition': condition
            })
        
        return joins
    
    def _extract_aggregations_from_sql(self, sql: str) -> List[Dict[str, str]]:
        """Extract aggregation functions from SQL"""
        aggregations = []
        
        agg_pattern = r'(SUM|COUNT|AVG|MAX|MIN)\s*\(\s*([^)]+)\s*\)'
        matches = re.findall(agg_pattern, sql, re.IGNORECASE)
        
        for match in matches:
            function = match[0].upper()
            column = match[1].strip()
            
            aggregations.append({
                'function': function,
                'column': column
            })
        
        return aggregations
    
    def _is_measure(self, data_item: dict) -> bool:
        """Determine if data item is a measure"""
        usage = data_item.get('usage', '').lower()
        expression = data_item.get('expression', '').upper()
        
        return (usage == 'fact' or 
                any(func in expression for func in ['SUM', 'COUNT', 'AVG', 'MAX', 'MIN']))
    
    def _is_dimension(self, data_item: dict) -> bool:
        """Determine if data item is a dimension"""
        usage = data_item.get('usage', '').lower()
        return usage in ['attribute', 'identifier']
    
    def _determine_filter_type(self, filter_item: dict) -> str:
        """Determine the type of filter"""
        expression = filter_item.get('expression', '').upper()
        
        if 'BETWEEN' in expression:
            return 'range'
        elif 'IN (' in expression:
            return 'list'
        elif any(op in expression for op in ['=', '>', '<', '>=', '<=']):
            return 'comparison'
        elif 'LIKE' in expression:
            return 'text'
        else:
            return 'custom'


class CognosReportConverter:
    """Converts Cognos API data to Power BI structures"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_parser = CognosAPIParser()
        self.query_analyzer = QueryAnalyzer()
        self.type_mapper = DataTypeMapper()
    
    def convert_report_from_api(self, report_data: dict, datasources: List[dict] = None, 
                               schemas: List[dict] = None) -> Dict[str, Any]:
        """Convert Cognos report from API data to Power BI compatible structure"""
        try:
            # Parse report using API parser
            cognos_report = self.api_parser.parse_report_from_api(report_data)
            
            # Convert data sources
            converted_datasources = []
            if datasources:
                for ds in datasources:
                    converted_ds = self.api_parser.parse_datasource_from_api(ds)
                    converted_datasources.append(converted_ds)
            
            # Convert schemas to tables
            tables = []
            if schemas:
                for schema in schemas:
                    schema_tables = self._convert_schema_to_tables(schema)
                    tables.extend(schema_tables)
            
            # Extract relationships from queries
            relationships = self._extract_relationships_from_queries(cognos_report.queries)
            
            # Convert data items to measures
            measures = self._convert_data_items_to_measures(cognos_report.queries)
            
            return {
                'report': cognos_report,
                'datasources': converted_datasources,
                'tables': tables,
                'relationships': relationships,
                'measures': measures,
                'layout': cognos_report.layout
            }
            
        except Exception as e:
            self.logger.error(f"Failed to convert Cognos report from API: {e}")
            return {}
    
    def _convert_schema_to_tables(self, schema_data: dict) -> List[Table]:
        """Convert schema information to Power BI tables"""
        tables = []
        
        schema_info = self.api_parser.parse_schema_from_api(schema_data)
        
        for table_name in schema_info.get('tables', []):
            # Create basic table structure
            # In a real implementation, you would make additional API calls
            # to get column information for each table
            table = Table(
                name=table_name,
                columns=[],  # Will be populated by separate API calls
                source_schema=schema_info.get('schema', ''),
                source_catalog=schema_info.get('catalog', ''),
                partition_mode="Import"
            )
            tables.append(table)
        
        return tables
    
    def _extract_relationships_from_queries(self, queries: List[QueryDefinition]) -> List[Relationship]:
        """Extract relationships from query definitions"""
        relationships = []
        
        for query in queries:
            if query.sql:
                analysis = self.query_analyzer.analyze_query_from_api({
                    'sql': query.sql,
                    'dataItems': query.data_items
                })
                
                # Extract relationships from JOIN conditions
                for join in analysis.get('joins', []):
                    relationship = self._parse_join_to_relationship(join)
                    if relationship:
                        relationships.append(relationship)
        
        return relationships
    
    def _convert_data_items_to_measures(self, queries: List[QueryDefinition]) -> List[Measure]:
        """Convert data items to Power BI measures"""
        measures = []
        
        for query in queries:
            analysis = self.query_analyzer.analyze_query_from_api({
                'dataItems': query.data_items
            })
            
            for item in analysis.get('data_items', []):
                if item.get('is_measure', False):
                    measure = Measure(
                        name=item['name'],
                        expression=self._convert_expression_to_dax(item.get('expression', '')),
                        description=f"Converted from Cognos data item: {item['name']}"
                    )
                    measures.append(measure)
        
        return measures
    
    def _parse_join_to_relationship(self, join: Dict[str, str]) -> Optional[Relationship]:
        """Parse JOIN condition to create relationship"""
        try:
            condition = join.get('condition', '')
            
            # Simple parsing of "table1.col1 = table2.col2" format
            if '=' in condition:
                parts = condition.split('=')
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()
                    
                    if '.' in left and '.' in right:
                        left_table, left_col = left.split('.', 1)
                        right_table, right_col = right.split('.', 1)
                        
                        return Relationship(
                            name=f"{left_table.strip()}_{right_table.strip()}",
                            from_table=left_table.strip(),
                            from_column=left_col.strip(),
                            to_table=right_table.strip(),
                            to_column=right_col.strip(),
                            cardinality="many_to_one"
                        )
        except Exception as e:
            self.logger.error(f"Failed to parse join to relationship: {e}")
        
        return None
    
    def _convert_expression_to_dax(self, expression: str) -> str:
        """Convert Cognos expression to DAX"""
        # Basic conversion - in production, implement comprehensive mapping
        dax_expression = expression
        
        # Simple replacements
        replacements = {
            'SUM(': 'SUM(',
            'COUNT(': 'COUNT(',
            'AVG(': 'AVERAGE(',
            'MAX(': 'MAX(',
            'MIN(': 'MIN('
        }
        
        for cognos_func, dax_func in replacements.items():
            dax_expression = dax_expression.replace(cognos_func, dax_func)
        
        return dax_expression
