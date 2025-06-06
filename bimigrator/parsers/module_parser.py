"""
Cognos Analytics Module Parser
Fetches module data from Cognos Analytics REST API and maps it to Power BI Table structure
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from .client import CognosClient
from .models import Table, Column, DataType


@dataclass
class ModuleColumn:
    """Represents a column from a Cognos module"""
    name: str
    data_type: str
    source_column: str
    is_calculated: bool = False
    format_string: Optional[str] = None
    is_hidden: bool = False
    data_category: Optional[str] = None
    summarize_by: Optional[str] = None
    annotations: Dict[str, Any] = None

    def __post_init__(self):
        if self.annotations is None:
            self.annotations = {}


@dataclass
class ModuleMeasure:
    """Represents a measure from a Cognos module"""
    name: str
    expression: str
    format_string: Optional[str] = None
    is_hidden: bool = False
    folder: Optional[str] = None


@dataclass
class ModuleTable:
    """Represents a table structure from a Cognos module"""
    name: str
    columns: List[ModuleColumn]
    measures: List[ModuleMeasure]
    is_hidden: bool = False
    source_query: Optional[str] = None


class CognosModuleParser:
    """Parser for Cognos Analytics modules"""
    
    def __init__(self, client: CognosClient):
        self.client = client
        self.logger = logging.getLogger(__name__)
        
        # Data type mapping from Cognos to Power BI
        self.datatype_mapping = {
            'string': 'string',
            'text': 'string',
            'varchar': 'string',
            'char': 'string',
            'integer': 'int64',
            'int': 'int64',
            'bigint': 'int64',
            'smallint': 'int64',
            'decimal': 'decimal',
            'numeric': 'decimal',
            'float': 'double',
            'double': 'double',
            'real': 'double',
            'boolean': 'boolean',
            'bit': 'boolean',
            'date': 'dateTime',
            'datetime': 'dateTime',
            'timestamp': 'dateTime',
            'time': 'dateTime'
        }
    
    def fetch_module(self, module_id: str) -> Dict[str, Any]:
        """Fetch module data from Cognos Analytics"""
        try:
            self.logger.info(f"Fetching module: {module_id}")
            
            # Get module metadata
            module_data = self.client.get_module_metadata(module_id)
            
            if not module_data:
                raise ValueError(f"Module {module_id} not found")
            
            return module_data
            
        except Exception as e:
            self.logger.error(f"Failed to fetch module {module_id}: {e}")
            raise
    
    def parse_module_to_table(self, module_data: Dict[str, Any]) -> ModuleTable:
        """Parse Cognos module data into a table structure"""
        try:
            # Extract basic table information
            table_name = self._extract_table_name(module_data)
            
            # Parse columns from module
            columns = self._parse_columns(module_data)
            
            # Parse measures from module
            measures = self._parse_measures(module_data)
            
            # Extract source query if available
            source_query = self._extract_source_query(module_data)
            
            return ModuleTable(
                name=table_name,
                columns=columns,
                measures=measures,
                source_query=source_query
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse module data: {e}")
            raise
    
    def _extract_table_name(self, module_data: Dict[str, Any]) -> str:
        """Extract table name from module data"""
        # For real Cognos data, check querySubject first
        if 'querySubject' in module_data and module_data['querySubject']:
            query_subject = module_data['querySubject'][0]
            # Use the label or identifier from querySubject
            table_name = query_subject.get('label') or query_subject.get('identifier')
            if table_name:
                # Clean up the name (remove file extensions, etc.)
                if table_name.endswith('.xlsx') or table_name.endswith('.csv'):
                    table_name = table_name.rsplit('.', 1)[0]
                return table_name.replace(' ', '_').replace('-', '_')
        
        # Fallback to module-level names
        if 'label' in module_data:
            return module_data['label'].replace(' ', '_').replace('-', '_')
        elif 'identifier' in module_data:
            return module_data['identifier']
        elif 'name' in module_data:
            return module_data['name']
        elif 'defaultName' in module_data:
            return module_data['defaultName']
        else:
            return "Unknown_Table"
    
    def _parse_columns(self, module_data: Dict[str, Any]) -> List[ModuleColumn]:
        """Parse columns from module data"""
        columns = []
        
        # For real Cognos data, check querySubject structure first
        if 'querySubject' in module_data and module_data['querySubject']:
            query_subject = module_data['querySubject'][0]
            if 'item' in query_subject:
                for item in query_subject['item']:
                    if 'queryItem' in item:
                        column = self._parse_cognos_query_item(item['queryItem'])
                        if column:
                            columns.append(column)
        
        # Fallback: Look for columns in other possible structures
        if not columns:
            column_sources = [
                module_data.get('columns', []),
                module_data.get('items', []),
                module_data.get('queryItems', []),
                module_data.get('dataItems', [])
            ]
            
            for column_list in column_sources:
                if column_list:
                    for col_data in column_list:
                        column = self._parse_single_column(col_data)
                        if column:
                            columns.append(column)
                    break  # Use the first non-empty column source
        
        # If still no columns found, create a sample column
        if not columns:
            columns.append(ModuleColumn(
                name="Sample_Column",
                data_type="string",
                source_column="Sample_Column"
            ))
        
        return columns
    
    def _parse_cognos_query_item(self, query_item: Dict[str, Any]) -> Optional[ModuleColumn]:
        """Parse a Cognos queryItem into a ModuleColumn"""
        try:
            # Extract column name from identifier or label
            name = query_item.get('identifier') or query_item.get('label') or 'Unknown_Column'
            
            # Extract data type - use highlevelDatatype first, then datatype
            data_type_raw = (query_item.get('highlevelDatatype') or 
                           query_item.get('datatype') or 
                           'string')
            
            # Map to Power BI data type
            data_type = self._map_data_type(data_type_raw)
            
            # Extract source column (expression or identifier)
            source_column = query_item.get('expression') or query_item.get('identifier') or name
            
            # Check if it's a calculated column (expression different from identifier)
            is_calculated = bool(query_item.get('expression') and 
                               query_item.get('expression') != query_item.get('identifier'))
            
            # Extract format information
            format_string = self._extract_cognos_format(query_item.get('format'))
            
            # Extract other properties
            is_hidden = query_item.get('hidden', False)
            
            # Determine data category from taxonomy
            data_category = self._extract_data_category(query_item.get('taxonomy', []))
            
            # Determine summarization based on usage and data type
            summarize_by = self._determine_cognos_summarize_by(query_item, data_type)
            
            # Build annotations
            annotations = self._build_cognos_annotations(query_item, data_type)
            
            return ModuleColumn(
                name=name,
                data_type=data_type,
                source_column=source_column,
                is_calculated=is_calculated,
                format_string=format_string,
                is_hidden=is_hidden,
                data_category=data_category,
                summarize_by=summarize_by,
                annotations=annotations
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to parse Cognos queryItem {query_item}: {e}")
            return None
    
    def _parse_single_column(self, col_data: Dict[str, Any]) -> Optional[ModuleColumn]:
        """Parse a single column from module data"""
        try:
            # Extract column name
            name = (col_data.get('name') or 
                   col_data.get('defaultName') or 
                   col_data.get('label') or 
                   'Unknown_Column')
            
            # Extract data type
            data_type_raw = (col_data.get('dataType') or 
                           col_data.get('type') or 
                           col_data.get('usage') or 
                           'string')
            
            # Map to Power BI data type
            data_type = self._map_data_type(data_type_raw)
            
            # Extract source column (might be same as name)
            source_column = (col_data.get('sourceColumn') or 
                           col_data.get('expression') or 
                           name)
            
            # Check if it's a calculated column
            is_calculated = bool(col_data.get('expression') and 
                               col_data.get('expression') != name)
            
            # Extract format information
            format_string = col_data.get('format') or col_data.get('formatString')
            
            # Extract other properties
            is_hidden = col_data.get('hidden', False)
            data_category = col_data.get('dataCategory')
            summarize_by = self._determine_summarize_by(data_type, col_data)
            
            # Build annotations
            annotations = self._build_column_annotations(col_data, data_type)
            
            return ModuleColumn(
                name=name,
                data_type=data_type,
                source_column=source_column,
                is_calculated=is_calculated,
                format_string=format_string,
                is_hidden=is_hidden,
                data_category=data_category,
                summarize_by=summarize_by,
                annotations=annotations
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to parse column {col_data}: {e}")
            return None
    
    def _parse_measures(self, module_data: Dict[str, Any]) -> List[ModuleMeasure]:
        """Parse measures from module data"""
        measures = []
        
        # Look for measures in various possible structures
        measure_sources = [
            module_data.get('measures', []),
            module_data.get('calculations', []),
            module_data.get('aggregations', [])
        ]
        
        for measure_list in measure_sources:
            if measure_list:
                for measure_data in measure_list:
                    measure = self._parse_single_measure(measure_data)
                    if measure:
                        measures.append(measure)
        
        return measures
    
    def _parse_single_measure(self, measure_data: Dict[str, Any]) -> Optional[ModuleMeasure]:
        """Parse a single measure from module data"""
        try:
            name = (measure_data.get('name') or 
                   measure_data.get('defaultName') or 
                   measure_data.get('label') or 
                   'Unknown_Measure')
            
            expression = (measure_data.get('expression') or 
                         measure_data.get('formula') or 
                         'SUM([Value])')
            
            format_string = measure_data.get('format') or measure_data.get('formatString')
            is_hidden = measure_data.get('hidden', False)
            folder = measure_data.get('folder') or measure_data.get('displayFolder')
            
            return ModuleMeasure(
                name=name,
                expression=expression,
                format_string=format_string,
                is_hidden=is_hidden,
                folder=folder
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to parse measure {measure_data}: {e}")
            return None
    
    def _extract_source_query(self, module_data: Dict[str, Any]) -> Optional[str]:
        """Extract source query from module data"""
        return (module_data.get('query') or 
                module_data.get('sourceQuery') or 
                module_data.get('sql'))
    
    def _map_data_type(self, cognos_type: str) -> str:
        """Map Cognos data type to Power BI data type"""
        if not cognos_type:
            return 'string'
        
        cognos_type_lower = cognos_type.lower()
        return self.datatype_mapping.get(cognos_type_lower, 'string')
    
    def _determine_summarize_by(self, data_type: str, col_data: Dict[str, Any]) -> Optional[str]:
        """Determine the summarizeBy property based on data type and column properties"""
        # Check if explicitly specified
        if 'summarizeBy' in col_data:
            return col_data['summarizeBy']
        
        # Auto-determine based on data type
        if data_type in ['int64', 'decimal', 'double']:
            # Check if it looks like an ID or key field
            name_lower = col_data.get('name', '').lower()
            if any(keyword in name_lower for keyword in ['id', 'key', 'code', 'number']):
                return 'none'
            else:
                return 'sum'
        else:
            return 'none'
    
    def _build_column_annotations(self, col_data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
        """Build annotations for a column"""
        annotations = {}
        
        # Add SummarizationSetBy annotation
        annotations['SummarizationSetBy'] = 'Automatic'
        
        # Add format hint for numeric types
        if data_type in ['int64', 'decimal', 'double']:
            annotations['PBI_FormatHint'] = '{"isGeneralNumber":true}'
        
        # Add any custom annotations from source
        if 'annotations' in col_data:
            annotations.update(col_data['annotations'])
        
        return annotations
    
    def _extract_cognos_format(self, format_data: Optional[str]) -> Optional[str]:
        """Extract format string from Cognos format data"""
        if not format_data:
            return None
        
        try:
            # Parse JSON format data
            format_obj = json.loads(format_data)
            format_group = format_obj.get('formatGroup', {})
            
            # Handle number format
            if 'numberFormat' in format_group:
                return 'General Number'
            
            # Handle date format
            elif 'dateTimeFormat' in format_group:
                return 'Short Date'
            
            # Default
            return 'General'
            
        except (json.JSONDecodeError, AttributeError):
            return None
    
    def _extract_data_category(self, taxonomy: List[Dict[str, Any]]) -> Optional[str]:
        """Extract data category from Cognos taxonomy"""
        if not taxonomy:
            return None
        
        for tax in taxonomy:
            if tax.get('domain') == 'cognos':
                family = tax.get('family')
                if family == 'cDate':
                    return 'Date'
                elif family == 'cRegion':
                    return 'Geography'
                elif tax.get('class') == 'cGeoLocation':
                    return 'Geography'
        
        return None
    
    def _determine_cognos_summarize_by(self, query_item: Dict[str, Any], data_type: str) -> Optional[str]:
        """Determine summarizeBy based on Cognos usage and data type"""
        usage = query_item.get('usage', '')
        regular_aggregate = query_item.get('regularAggregate', '')
        identifier = query_item.get('identifier', '').lower()
        
        # If it's a fact, use sum for numeric types
        if usage == 'fact':
            if data_type in ['int64', 'decimal', 'double']:
                return 'sum'
            else:
                return 'none'
        
        # If it's an identifier or attribute, don't summarize
        elif usage in ['identifier', 'attribute']:
            return 'none'
        
        # Check regular aggregate
        elif regular_aggregate == 'total':
            return 'sum'
        elif regular_aggregate in ['count', 'countDistinct']:
            return 'none'  # IDs should not be summed
        
        # Default based on data type and name
        elif data_type in ['int64', 'decimal', 'double']:
            # Check if it looks like an ID field
            if any(keyword in identifier for keyword in ['id', 'key', 'code', 'number']):
                return 'none'
            else:
                return 'sum'
        else:
            return 'none'
    
    def _build_cognos_annotations(self, query_item: Dict[str, Any], data_type: str) -> Dict[str, Any]:
        """Build annotations for a Cognos column"""
        annotations = {}
        
        # Add SummarizationSetBy annotation
        annotations['SummarizationSetBy'] = 'Automatic'
        
        # Add format hint for numeric types
        if data_type in ['int64', 'decimal', 'double']:
            annotations['PBI_FormatHint'] = '{"isGeneralNumber":true}'
        
        # Add usage information as annotation
        usage = query_item.get('usage')
        if usage:
            annotations['CognosUsage'] = usage
        
        # Add regular aggregate information
        regular_aggregate = query_item.get('regularAggregate')
        if regular_aggregate:
            annotations['CognosRegularAggregate'] = regular_aggregate
        
        return annotations
    
    def generate_table_json(self, module_table: ModuleTable) -> Dict[str, Any]:
        """Generate JSON structure for populating Table.tmdl template"""
        
        # Build columns structure
        columns_json = []
        for col in module_table.columns:
            column_json = {
                'source_name': col.name,
                'source_column': col.source_column,
                'datatype': col.data_type,
                'is_calculated': col.is_calculated,
                'is_hidden': col.is_hidden,
                'is_data_type_inferred': True,
                'annotations': col.annotations
            }
            
            if col.format_string:
                column_json['format_string'] = col.format_string
            if col.data_category:
                column_json['data_category'] = col.data_category
            if col.summarize_by:
                column_json['summarize_by'] = col.summarize_by
                
            columns_json.append(column_json)
        
        # Build measures structure
        measures_json = []
        for measure in module_table.measures:
            measure_json = {
                'source_name': measure.name,
                'expression': measure.expression,
                'is_hidden': measure.is_hidden
            }
            
            if measure.format_string:
                measure_json['format_string'] = measure.format_string
            if measure.folder:
                measure_json['folder'] = measure.folder
                
            measures_json.append(measure_json)
        
        # Build partitions structure
        partitions_json = []
        if module_table.source_query:
            partitions_json.append({
                'name': f'{module_table.name}-partition',
                'source_type': 'm',
                'expression': self._build_m_expression(module_table.source_query)
            })
        
        # Build complete table JSON
        table_json = {
            'source_name': module_table.name,
            'is_hidden': module_table.is_hidden,
            'columns': columns_json,
            'measures': measures_json,
            'hierarchies': [],  # Empty for now
            'partitions': partitions_json,
            'has_widget_serialization': False,
            'visual_type': 'Table',
            'column_settings': '[]'
        }
        
        return table_json
    
    def _build_m_expression(self, source_query: str) -> str:
        """Build M expression for Power BI partition"""
        # Simple M expression wrapper for SQL queries
        return f'''let
    Source = Sql.Database("server", "database", [Query="{source_query}"])
in
    Source'''


def create_module_parser_demo():
    """Demo function to show how to use the module parser"""
    
    # Sample module data (what would come from Cognos API)
    sample_module_data = {
        "name": "Sales_Data_Module",
        "defaultName": "Sales Data Module",
        "columns": [
            {
                "name": "ProductID",
                "dataType": "integer",
                "sourceColumn": "ProductID",
                "hidden": False
            },
            {
                "name": "ProductName",
                "dataType": "string",
                "sourceColumn": "ProductName",
                "hidden": False
            },
            {
                "name": "SalesAmount",
                "dataType": "decimal",
                "sourceColumn": "SalesAmount",
                "format": "Currency",
                "hidden": False
            },
            {
                "name": "OrderDate",
                "dataType": "date",
                "sourceColumn": "OrderDate",
                "hidden": False
            }
        ],
        "measures": [
            {
                "name": "Total Sales",
                "expression": "SUM([SalesAmount])",
                "format": "Currency"
            },
            {
                "name": "Average Sales",
                "expression": "AVERAGE([SalesAmount])",
                "format": "Currency"
            }
        ],
        "query": "SELECT ProductID, ProductName, SalesAmount, OrderDate FROM Sales"
    }
    
    return sample_module_data


if __name__ == "__main__":
    # Demo usage
    sample_data = create_module_parser_demo()
    
    # Create a mock client for demo
    class MockClient:
        def get_module_metadata(self, module_id):
            return sample_data
    
    parser = CognosModuleParser(MockClient())
    module_table = parser.parse_module_to_table(sample_data)
    table_json = parser.generate_table_json(module_table)
    
    print("Generated Table JSON:")
    print(json.dumps(table_json, indent=2))
