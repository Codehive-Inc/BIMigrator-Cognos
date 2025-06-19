# Module Migration Process

## Overview

The module migration process converts Cognos data modules to Power BI datasets (.pbit). This document details the specific steps, components, and considerations for module migration.

## Process Flow

1. **Module Extraction**
   - Connect to Cognos Analytics API
   - Extract module specification and metadata
   - Save raw extracted data to the output directory

2. **Module Parsing**
   - Parse Cognos module specification
   - Extract tables, columns, relationships, and calculations
   - Map Cognos data types to Power BI equivalents

3. **Data Model Generation**
   - Create Power BI tables and columns
   - Generate relationships between tables
   - Create measures and calculated columns

4. **M-Query Generation**
   - Use LLM service to generate optimized M-queries for each table
   - Map Cognos expressions to Power BI DAX/M expressions

5. **Power BI Project Generation**
   - Generate Power BI project files (.tmdl)
   - Create model structure and relationships
   - Package into .pbit format

6. **Documentation Generation**
   - Create migration report
   - Document any issues or limitations

## Key Components

### ModuleMigrator Class

The `ModuleMigrator` class in `module_migrator.py` orchestrates the module migration process:

```python
class ModuleMigrator:
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize services
        self.cognos_service = CognosService(config)
        self.module_parser = ModuleParser(config)
        self.module_generator = ModuleGenerator(config)
        
    def migrate_module(self, module_id: str, folder_id: Optional[str] = None, output_path: Optional[str] = None) -> str:
        """Migrate a Cognos module to Power BI"""
        try:
            # Extract module specification
            module_spec = self.cognos_service.get_module_spec(module_id)
            
            # Parse module specification
            data_model = self.module_parser.parse_module(module_spec, module_id)
            
            # Generate Power BI project
            output_dir = output_path or f"output/module_{module_id}"
            self.module_generator.generate_module(data_model, output_dir, folder_id)
            
            return output_dir
            
        except Exception as e:
            self.logger.error(f"Failed to migrate module {module_id}: {e}")
            raise
```

### ModuleParser Class

The `ModuleParser` class parses Cognos module specifications and extracts data model information:

```python
class ModuleParser:
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def parse_module(self, module_spec: str, module_id: str) -> DataModel:
        """Parse module specification and extract data model"""
        try:
            # Parse module XML
            module_xml = ET.fromstring(module_spec)
            
            # Extract tables
            tables = self._extract_tables(module_xml)
            
            # Extract relationships
            relationships = self._extract_relationships(module_xml)
            
            # Create data model
            data_model = DataModel(
                name=self._extract_module_name(module_xml),
                tables=tables,
                relationships=relationships,
                measures=[],  # Extract measures if available
                module_id=module_id
            )
            
            return data_model
            
        except Exception as e:
            self.logger.error(f"Failed to parse module: {e}")
            raise
```

### ModuleModelFileGenerator Class

The `ModuleModelFileGenerator` class in `module_model_file_generator.py` extends the base `ModelFileGenerator` class to handle module-specific requirements:

```python
class ModuleModelFileGenerator(ModelFileGenerator):
    def __init__(self, config: MigrationConfig):
        super().__init__(config)
        
    def _generate_model_file(self, data_model: DataModel, model_dir: Path):
        """Generate model.tmdl file with module-specific settings"""
        # Get table references
        table_references = [table.name for table in data_model.tables]
        
        # Build context for model template
        context = {
            'model_name': data_model.name,
            'tables': table_references,
            'culture': data_model.culture or 'en-US',
            'desktop_version': "2.141.1253.0 (25.03)+74f9999a1e95f78c739f3ea2b96ba340e9ba8729"
        }
        
        # Render model template
        content = self.template_engine.render('model', context)
        
        # Write model file
        model_file = model_dir / 'model.tmdl'
        with open(model_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        self.logger.info(f"Generated model file: {model_file}")
        
    def _generate_culture_file(self, data_model: DataModel, model_dir: Path):
        """Generate culture file"""
        # Get the version from data_model if available, otherwise use a default version
        version = getattr(data_model, 'version', '1.0.0') if hasattr(data_model, 'version') else '1.0.0'
        
        context = {
            'culture': data_model.culture or 'en-US',
            'version': version
        }
        
        content = self.template_engine.render('culture', context)
        
        culture_code = data_model.culture or 'en-US'
        culture_file = model_dir / 'cultures' / f'{culture_code}.tmdl'
        culture_file.parent.mkdir(exist_ok=True)
        with open(culture_file, 'w', encoding='utf-8') as f:
            f.write(content)
```

### Relationship Handling

Module relationships are handled differently from report relationships. The `_generate_relationships_file` method creates the relationships.tmdl file:

```python
def _generate_relationships_file(self, relationships: List[Relationship], model_dir: Path):
    relationships_context = []
    for rel in relationships:
        relationship_data = {
            'id': rel.name,  # Use name as the relationship ID
            'name': rel.name,
            'from_table': rel.from_table,
            'from_column': rel.from_column,
            'to_table': rel.to_table,
            'to_column': rel.to_column,
            'cardinality': rel.cardinality,
            'cross_filter_direction': rel.cross_filter_direction,
            'is_active': rel.is_active
        }
        relationships_context.append(relationship_data)
    context = {'relationships': relationships_context}
    content = self.template_engine.render('relationship', context)
    relationships_file = model_dir / 'relationships.tmdl'
    with open(relationships_file, 'w', encoding='utf-8') as f:
        f.write(content)
```

## Output Structure

The module migration process produces a directory structure compatible with the Power BI Desktop template format (.pbit):

```
pbit/
├── .pbixproj.json
├── Model/
│   ├── database.tmdl
│   ├── model.tmdl
│   ├── relationships.tmdl
│   ├── expressions.tmdl
│   ├── cultures/
│   │   └── en-US.tmdl
│   └── tables/
│       ├── Table1.tmdl
│       ├── Table2.tmdl
│       └── ...
├── Report/
│   ├── report.json
│   ├── config.json
│   └── sections/
│       └── section0.json
├── ReportMetadata.json
├── ReportSettings.json
├── DiagramLayout.json
└── Version.txt
```

## Command-Line Usage

To migrate a Cognos module to Power BI:

```
python main.py migrate-module <module_id> [<folder_id>] [output]
```

Where:
- `<module_id>` is the ID of the Cognos module to migrate
- `<folder_id>` (optional) is the ID of the folder containing the module
- `[output]` (optional) is the output directory path

## Important Considerations

1. **Relationship IDs**: Module relationships use the relationship name as the ID in the relationships.tmdl file.

2. **Culture Files**: Culture files are named after the culture code (e.g., "en-US.tmdl") and include the version "1.0.0".

3. **PBIDesktopVersion**: The full version string "2.141.1253.0 (25.03)+74f9999a1e95f78c739f3ea2b96ba340e9ba8729" is used in the model.tmdl file.

4. **Table Context**: Module tables may have different context requirements compared to report tables.

## Troubleshooting

Common issues that may occur during module migration:

1. **Missing Relationship Attributes**: Ensure that relationship objects have all required attributes (name, from_table, from_column, to_table, to_column).

2. **Culture File Naming**: Verify that culture files are named correctly (e.g., "en-US.tmdl" instead of "culture.tmdl").

3. **Version Format**: Check that version strings are in the correct format ("1.0.0" for culture files, full version string for PBIDesktopVersion).

4. **Method Signature Mismatches**: Ensure that method signatures match between base and derived classes, particularly for methods like `_build_table_context`.
