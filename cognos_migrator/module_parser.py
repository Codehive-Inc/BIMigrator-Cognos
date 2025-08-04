"""
Cognos Analytics Module Parser
Fetches module data from Cognos Analytics REST API and maps it to Power BI Table structure
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from .client import CognosClient
from .models import Table, Column, DataType, Relationship
from .expressions import CognosExpressionConverter
from .time_intelligence import CognosTimeIntelligenceConverter, create_standard_date_dimension, TimeIntelligenceMeasure


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
        self.time_intelligence = CognosTimeIntelligenceConverter()
        
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
    
    def detect_relationships(self, modules_metadata: List[Dict]) -> List[Relationship]:
        """
        Detect relationships between modules/tables
        
        Args:
            modules_metadata: List of module metadata from Cognos
            
        Returns:
            List of detected relationships
        """
        relationships = []
        
        try:
            # Method 1: Detect by column name patterns (FK conventions)
            relationships.extend(self._detect_relationships_by_naming(modules_metadata))
            
            # Method 2: Detect by data lineage if available
            relationships.extend(self._detect_relationships_by_lineage(modules_metadata))
            
            # Method 3: Detect by explicit relationship metadata
            relationships.extend(self._detect_explicit_relationships(modules_metadata))
            
            self.logger.info(f"Detected {len(relationships)} relationships")
            
        except Exception as e:
            self.logger.error(f"Failed to detect relationships: {e}")
        
        return relationships
    
    def _detect_relationships_by_naming(self, modules_metadata: List[Dict]) -> List[Relationship]:
        """Detect relationships based on column naming conventions"""
        relationships = []
        
        # Build table-column mapping
        table_columns = {}
        for module in modules_metadata:
            table_name = self._get_table_name(module)
            columns = self._parse_columns(module)
            table_columns[table_name] = [col.name for col in columns]
        
        # Common foreign key patterns
        fk_patterns = [
            r'(.+)_id$',           # customer_id -> customer.id
            r'(.+)id$',            # customerid -> customer.id  
            r'fk_(.+)',            # fk_customer -> customer.id
            r'(.+)_key$',          # customer_key -> customer.key
            r'(.+)_ref$',          # customer_ref -> customer.id
        ]
        
        for table_name, columns in table_columns.items():
            for column in columns:
                column_lower = column.lower()
                
                for pattern in fk_patterns:
                    match = re.match(pattern, column_lower)
                    if match:
                        referenced_table = match.group(1)
                        
                        # Look for matching table
                        for other_table, other_columns in table_columns.items():
                            if (other_table.lower() == referenced_table or 
                                other_table.lower() == referenced_table + 's' or
                                other_table.lower() == referenced_table.rstrip('s')):
                                
                                # Find primary key column in referenced table
                                pk_column = self._find_primary_key_column(other_columns)
                                
                                if pk_column:
                                    relationship = Relationship(
                                        from_table=table_name,
                                        from_column=column,
                                        to_table=other_table,
                                        to_column=pk_column,
                                        id=f"{table_name}_{column}_to_{other_table}_{pk_column}",
                                        cardinality="many_to_one",
                                        cross_filter_behavior="single",
                                        is_active=True
                                    )
                                    relationships.append(relationship)
                                    break
        
        return relationships
    
    def _detect_relationships_by_lineage(self, modules_metadata: List[Dict]) -> List[Relationship]:
        """Detect relationships based on data lineage information"""
        relationships = []
        
        for module in modules_metadata:
            # Check if module metadata contains relationship information
            if 'relationships' in module:
                for rel_data in module['relationships']:
                    relationship = self._parse_relationship_metadata(rel_data)
                    if relationship:
                        relationships.append(relationship)
            
            # Check for join information in queries
            if 'query' in module and 'joins' in module['query']:
                for join_data in module['query']['joins']:
                    relationship = self._parse_join_to_relationship(join_data)
                    if relationship:
                        relationships.append(relationship)
        
        return relationships
    
    def _detect_explicit_relationships(self, modules_metadata: List[Dict]) -> List[Relationship]:
        """Detect explicitly defined relationships in module metadata"""
        relationships = []
        
        for module in modules_metadata:
            # Look for explicit relationship definitions
            if 'modelRelationships' in module:
                for rel_def in module['modelRelationships']:
                    relationship = Relationship(
                        from_table=rel_def.get('fromTable', ''),
                        from_column=rel_def.get('fromColumn', ''),
                        to_table=rel_def.get('toTable', ''),
                        to_column=rel_def.get('toColumn', ''),
                        id=rel_def.get('name', 'Unknown_Relationship'),
                        from_cardinality=self._map_cardinality(rel_def.get('cardinality', '1:*')),
                        cross_filtering_behavior=rel_def.get('crossFilterBehavior', 'single'),
                        is_active=rel_def.get('isActive', True)
                    )
                    relationships.append(relationship)
        
        return relationships
    
    def _find_primary_key_column(self, columns: List[str]) -> Optional[str]:
        """Find the primary key column in a list of columns"""
        # Common primary key patterns
        pk_patterns = [
            r'^id$',
            r'^(.+)_id$',
            r'^(.+)id$', 
            r'^pk_(.+)',
            r'^(.+)_key$',
            r'^key$'
        ]
        
        for column in columns:
            column_lower = column.lower()
            for pattern in pk_patterns:
                if re.match(pattern, column_lower):
                    return column
        
        # If no pattern matches, return first column (assumption)
        return columns[0] if columns else None
    
    def _parse_relationship_metadata(self, rel_data: Dict) -> Optional[Relationship]:
        """Parse relationship from metadata"""
        try:
            return Relationship(
                from_table=rel_data.get('fromTable', ''),
                from_column=rel_data.get('fromColumn', ''),
                to_table=rel_data.get('toTable', ''),
                to_column=rel_data.get('toColumn', ''),
                id=rel_data.get('name', 'Unknown_Relationship'),
                from_cardinality=self._map_cardinality(rel_data.get('cardinality', '1:*')),
                cross_filtering_behavior=rel_data.get('crossFilterBehavior', 'single'),
                is_active=rel_data.get('isActive', True)
            )
        except Exception as e:
            self.logger.warning(f"Failed to parse relationship metadata: {e}")
            return None
    
    def _parse_join_to_relationship(self, join_data: Dict) -> Optional[Relationship]:
        """Convert join information to relationship"""
        try:
            # Extract table and column information from join
            left_table = join_data.get('leftTable', '')
            left_column = join_data.get('leftColumn', '')
            right_table = join_data.get('rightTable', '')
            right_column = join_data.get('rightColumn', '')
            join_type = join_data.get('type', 'inner')
            
            # Map join type to cardinality
            cardinality_map = {
                'inner': 'many_to_one',
                'left': 'many_to_one', 
                'right': 'one_to_many',
                'full': 'many_to_many'
            }
            
            relationship = Relationship(
                from_table=left_table,
                from_column=left_column,
                to_table=right_table,
                to_column=right_column,
                id=f"{left_table}_{left_column}_to_{right_table}_{right_column}",
                from_cardinality=cardinality_map.get(join_type, 'many_to_one'),
                cross_filtering_behavior='single',
                is_active=True
            )
            
            return relationship
            
        except Exception as e:
            self.logger.warning(f"Failed to parse join to relationship: {e}")
            return None
    
    def _map_cardinality(self, cognos_cardinality: str) -> str:
        """Map Cognos cardinality to Power BI cardinality"""
        cardinality_map = {
            '1:1': 'one_to_one',
            '1:*': 'one_to_many',
            '*:1': 'many_to_one',
            '*:*': 'many_to_many',
            'one_to_one': 'one_to_one',
            'one_to_many': 'one_to_many',
            'many_to_one': 'many_to_one',
            'many_to_many': 'many_to_many'
        }
        
        return cardinality_map.get(cognos_cardinality.lower(), 'many_to_one')
    
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
    
    def _is_date_column_obj(self, column: ModuleColumn) -> bool:
        """Check if a ModuleColumn is a date column"""
        data_type = column.data_type.lower()
        col_name = column.name.lower()
        
        # Check data type
        if any(dt in data_type for dt in ['date', 'time', 'datetime', 'timestamp']):
            return True
        
        # Check column name patterns
        date_patterns = ['date', 'time', 'created', 'modified', 'start', 'end', 'day', 'month', 'year']
        if any(pattern in col_name for pattern in date_patterns):
            return True
        
        return False
    
    def generate_time_intelligence_measures(self, module_table: ModuleTable) -> List[TimeIntelligenceMeasure]:
        """Generate time intelligence measures for numeric columns and existing measures"""
        time_measures = []
        
        try:
            # Find date columns to use for time intelligence
            date_columns = [col for col in module_table.columns if self._is_date_column_obj(col)]
            
            if not date_columns:
                self.logger.info("No date columns found, skipping time intelligence generation")
                return time_measures
            
            # Use first date column for time intelligence
            primary_date_col = date_columns[0]
            date_dimension = create_standard_date_dimension(module_table.name, primary_date_col.name)
            
            # Find numeric measures and columns that can be aggregated
            aggregatable_items = []
            
            # Add existing measures
            for measure in module_table.measures:
                aggregatable_items.append(measure.name)
            
            # Add numeric columns that aren't IDs or keys
            for col in module_table.columns:
                if (col.data_type in ['int64', 'decimal', 'double'] and 
                    col.summarize_by == 'sum' and
                    not any(keyword in col.name.lower() for keyword in ['id', 'key', 'code'])):
                    aggregatable_items.append(col.name)
            
            # Generate time intelligence measures
            if aggregatable_items:
                time_measures = self.time_intelligence.generate_time_intelligence_measures(
                    aggregatable_items, date_dimension
                )
                
                self.logger.info(f"Generated {len(time_measures)} time intelligence measures")
            
        except Exception as e:
            self.logger.error(f"Failed to generate time intelligence measures: {e}")
        
        return time_measures
    
    def enhance_date_columns(self, module_table: ModuleTable) -> List[Dict[str, Any]]:
        """Enhance date columns with calculated date parts"""
        date_calculations = []
        
        try:
            # Find date columns
            date_columns = [col for col in module_table.columns if self._is_date_column_obj(col)]
            
            for date_col in date_columns:
                # Create date dimension for this column
                date_dimension = create_standard_date_dimension(module_table.name, date_col.name)
                
                # Generate date calculations
                date_template = self.time_intelligence.create_date_dimension_template(date_dimension)
                
                if date_template and 'calculated_columns' in date_template:
                    date_calculations.extend(date_template['calculated_columns'])
                
                self.logger.info(f"Enhanced date column {date_col.name} with {len(date_template.get('calculated_columns', []))} calculations")
        
        except Exception as e:
            self.logger.error(f"Failed to enhance date columns: {e}")
        
        return date_calculations
    
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
        
        # Add time intelligence measures
        try:
            time_measures = self.generate_time_intelligence_measures(module_table)
            for time_measure in time_measures:
                time_measure_json = {
                    'source_name': time_measure.name,
                    'expression': time_measure.dax_expression,
                    'is_hidden': False,
                    'folder': time_measure.folder
                }
                
                if time_measure.format_string:
                    time_measure_json['format_string'] = time_measure.format_string
                
                measures_json.append(time_measure_json)
                
        except Exception as e:
            self.logger.warning(f"Failed to add time intelligence measures: {e}")
        
        # Add enhanced date columns as calculated columns
        enhanced_date_columns = []
        try:
            enhanced_date_columns = self.enhance_date_columns(module_table)
        except Exception as e:
            self.logger.warning(f"Failed to enhance date columns: {e}")
        
        # Merge enhanced date columns with regular columns
        for enhanced_col in enhanced_date_columns:
            enhanced_column_json = {
                'source_name': enhanced_col['name'],
                'source_column': enhanced_col['expression'],
                'datatype': enhanced_col['dataType'],
                'is_calculated': True,
                'is_hidden': enhanced_col.get('isHidden', False),
                'is_data_type_inferred': True,
                'summarize_by': enhanced_col.get('summarizeBy', 'none'),
                'annotations': {'SummarizationSetBy': 'Automatic'}
            }
            columns_json.append(enhanced_column_json)
        
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
        if not source_query:
            # Handle empty source query
            self.logger.info("Empty source query provided, generating generic table structure")
            return '''let
    Source = Table.FromRows({{}}, type table [])
in
    Source'''
        else:
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
