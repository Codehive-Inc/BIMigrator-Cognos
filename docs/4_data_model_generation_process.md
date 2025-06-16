# Data Model Generation Process

## Overview

The data model generation process creates a Power BI data model from the parsed Cognos report structure, including tables, columns, measures, and relationships.

## Process Flow

1. **Create Data Model Structure**
   - Create tables based on data sources in the report
   - Define columns with appropriate data types
   - Create measures from calculations

2. **Process Module Information**
   - Extract module metadata using `ModuleParser`
   - Map Cognos module structure to Power BI tables

3. **Generate Relationships**
   - Identify relationships between tables
   - Define cardinality and cross-filter direction

4. **Enhance with CPF Metadata (if available)**
   - Incorporate metadata from Cognos package files
   - Enhance data model with additional information

## Key Components

### Data Model Creation in CognosMigrator

The `CognosMigrator` class in `migrator.py` handles the creation of the Power BI data model:

```python
def _create_data_model(self, converted_data: Dict[str, Any], model_name: str) -> DataModel:
    # Create tables
    tables = []
    for table_data in converted_data.get('tables', []):
        columns = []
        for col_data in table_data.get('columns', []):
            column = Column(
                name=col_data.get('name', 'Unknown'),
                data_type=self._map_data_type(col_data.get('data_type', 'string')),
                description=col_data.get('description', '')
            )
            columns.append(column)
        
        # Create table with columns
        table = Table(
            name=table_data.get('name', 'Unknown'),
            columns=columns,
            source_query=table_data.get('source_query', '')
        )
        tables.append(table)
    
    # Create relationships
    relationships = []
    for rel_data in converted_data.get('relationships', []):
        relationship = Relationship(
            name=f"Relationship_{len(relationships)}",
            from_table=rel_data.get('from_table', ''),
            from_column=rel_data.get('from_column', ''),
            to_table=rel_data.get('to_table', ''),
            to_column=rel_data.get('to_column', ''),
            cardinality=rel_data.get('cardinality', 'many_to_one'),
            cross_filter_direction=rel_data.get('cross_filter_direction', 'both')
        )
        relationships.append(relationship)
    
    # Create measures
    measures = []
    for measure_data in converted_data.get('measures', []):
        measure = Measure(
            name=measure_data.get('name', 'Unknown'),
            expression=measure_data.get('expression', ''),
            description=measure_data.get('description', '')
        )
        measures.append(measure)
    
    # Create data model
    data_model = DataModel(
        name=model_name,
        tables=tables,
        relationships=relationships,
        measures=measures
    )
    
    return data_model
```

### Module Parser

The `CognosModuleParser` class in `module_parser.py` extracts structured information from Cognos modules:

```python
class CognosModuleParser:
    def __init__(self, client: CognosClient):
        # Initialize parser
        
    def fetch_module(self, module_id: str) -> Dict[str, Any]:
        # Fetch module data from Cognos Analytics
        
    def parse_module_to_table(self, module_data: Dict[str, Any]) -> ModuleTable:
        # Parse Cognos module data into a table structure
        
    def _extract_table_name(self, module_data: Dict[str, Any]) -> str:
        # Extract table name from module data
        
    def _parse_columns(self, module_data: Dict[str, Any]) -> List[ModuleColumn]:
        # Parse columns from module data
        
    def detect_relationships(self, modules_metadata: List[Dict]) -> List[Relationship]:
        # Detect relationships between modules/tables
```

### CPF Enhancement

If a Cognos Package File (CPF) is available, the data model is enhanced with additional metadata:

```python
def _enhance_with_cpf_metadata(self, powerbi_project: PowerBIProject) -> None:
    """Enhance Power BI project with metadata from CPF file"""
    if not self.cpf_extractor or not self.cpf_extractor.metadata:
        return
    
    # Get data model
    data_model = powerbi_project.data_model
    
    # Process query subjects (tables)
    for query_subject in self.cpf_extractor.parser.get_query_subjects():
        table_name = query_subject.get('name')
        table = self._find_table_by_name(data_model, table_name)
        
        if table:
            # Update table properties if needed
            if 'description' in query_subject:
                table.description = query_subject['description']
            
            # Process query items (columns)
            for query_item in query_subject.get('queryItems', []):
                item_name = query_item.get('name')
                for column in table.columns:
                    if column.name == item_name:
                        # Update column properties
                        if 'description' in query_item:
                            column.description = query_item['description']
                        if 'dataType' in query_item:
                            column.data_type = self._map_cpf_data_type(query_item['dataType'])
                        break
    
    # Process relationships
    for relationship in self.cpf_extractor.parser.get_relationships():
        from_table = relationship.get('fromQuerySubject')
        from_column = relationship.get('fromQueryItem')
        to_table = relationship.get('toQuerySubject')
        to_column = relationship.get('toQueryItem')
        cardinality = relationship.get('cardinality', 'oneToMany')
        
        new_rel = Relationship(
            name=f"Relationship_{len(data_model.relationships)}",
            from_table=from_table,
            from_column=from_column,
            to_table=to_table,
            to_column=to_column,
            cardinality=self._map_cpf_cardinality(cardinality),
            cross_filter_direction="both"
        )
        
        # Add relationship if it doesn't already exist
        if not self._relationship_exists(data_model, new_rel):
            data_model.relationships.append(new_rel)
```

## Output Structure

The data model generation process produces a structured `DataModel` object containing:

- Tables with columns and their data types
- Relationships between tables
- Measures with DAX expressions

This data model is then used in the Power BI project generation process to create the actual Power BI model files.
