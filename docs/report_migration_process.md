# Cognos to Power BI Report Migration Process

## Overview

This document provides a comprehensive overview of the report migration process from Cognos to Power BI within the BIMigrator-Cognos system. The migration process involves several key components working together to extract, transform, and generate Power BI artifacts from Cognos reports.

### Key Files and Modules

- **Main Entry Point**: `/cognos_migrator/main.py`
- **Core Migration Logic**: `/cognos_migrator/migrator.py`
- **Report Parsing**: `/cognos_migrator/report_parser.py`
- **Client API**: `/cognos_migrator/client.py`
- **Summary Generation**: `/cognos_migrator/summary.py`

## Migration Flow

### 1. Entry Points

The migration process begins with the `main.py` module, which provides functions for:
- `test_cognos_connection(cognos_url, session_key)`: Tests Cognos connections
- `post_process_module_with_explicit_session(module_id, output_path, cognos_url, session_key, ...)`: Post-processes modules with explicit session credentials
- `consolidate_model_tables(output_path)`: Consolidates model tables into a single file

The core migration functionality is implemented in the `migrator.py` module through the `CognosModuleMigratorExplicit` class, which handles migration without requiring environment variables. Key methods include:
- `migrate_report(report_id, output_path)`: Migrates a single report
- `migrate_folder(folder_id, output_path, recursive)`: Migrates all reports in a folder
- `migrate_module(module_id, output_path, folder_id, cpf_file_path)`: Migrates a module

### 2. Report Migration Process

The report migration process follows these key steps:

#### 2.1. Initialization

```
CognosModuleMigratorExplicit.__init__()
```
- Initializes the Cognos client with explicit credentials
- Sets up the module parser
- Initializes LLM service client and M-query converter if enabled
- Creates project generator and documentation generator
- Initializes expression converter
- Sets up module extractors for different aspects of the migration
- Initializes CPF extractor if provided
- Sets up the summary generator

#### 2.2. Report Migration

```python
# In cognos_migrator/migrator.py
def migrate_report(self, report_id: str, output_path: str) -> bool:
    """Migrate a single Cognos report to Power BI without using environment variables"""
```

1. **Directory Setup**
   - Creates output directory structure: `{output_path}/`
   - Creates subdirectories:
     - `{output_path}/extracted/` - For raw extracted data
     - `{output_path}/pbit/` - For Power BI template files

2. **Fetch Cognos Report**
   - Retrieves the report from Cognos using `cognos_client.get_report(report_id)`
   - Saves raw report data to the extracted folder using `_save_extracted_report_data()`
   - Output files:
     - `{output_path}/extracted/report_specification.xml` - Raw XML
     - `{output_path}/extracted/report_specification_formatted.xml` - Formatted XML
     - `{output_path}/extracted/report_metadata.json` - Report metadata
     - `{output_path}/extracted/report_details.json` - Basic report details

3. **Convert to Power BI Structures**
   - Calls `_convert_cognos_report_to_powerbi(cognos_report)` to transform the report
   - Enhances the project with CPF metadata if available via `cpf_metadata_enhancer.enhance_project()`
   - Intermediate files:
     - `{output_path}/extracted/report_queries.json` - Extracted queries
     - `{output_path}/extracted/report_data_items.json` - Data items/columns
     - `{output_path}/extracted/calculations.json` - Converted expressions
     - `{output_path}/extracted/report_parameters.json` - Parameters
     - `{output_path}/extracted/report_filters.json` - Filters
     - `{output_path}/extracted/report_layout.json` - Layout information

4. **Generate Power BI Project Files**
   - Uses `project_generator.generate_project(powerbi_project, pbit_dir)` to create Power BI files
   - Generates documentation via `doc_generator.generate_migration_report()`
   - Output files:
     - `{output_path}/pbit/Report.pbir` - Power BI report file
     - `{output_path}/pbit/DataModel.tmdl` - Power BI data model
     - `{output_path}/pbit/DiagramLayout.json` - Layout information
     - `{output_path}/pbit/Settings.json` - Project settings
     - `{output_path}/extracted/migration_report.md` - Migration documentation

#### 2.3. Report Data Extraction

```python
# In cognos_migrator/migrator.py
def _save_extracted_report_data(self, cognos_report, extracted_dir):
    """Save extracted report data to files for investigation"""
```

1. Initializes various extractors from `cognos_migrator/extractors/`:
   - `BaseExtractor` - Base class for all extractors
   - `QueryExtractor` - Extracts query definitions
   - `DataItemExtractor` - Extracts columns and properties
   - `ExpressionExtractor` - Processes expressions
   - `ParameterExtractor` - Extracts parameters
   - `FilterExtractor` - Extracts filters
   - `LayoutExtractor` - Extracts visual layout

2. Saves report specification in multiple formats:
   - `{extracted_dir}/report_specification.xml` - Raw XML
   - `{extracted_dir}/report_specification_formatted.xml` - Formatted XML
   - `{extracted_dir}/report_specification_layout.xml` - Layout component
   - `{extracted_dir}/report_specification_query.xml` - Query component

3. Extracts and saves additional components:
   - `{extracted_dir}/report_metadata.json` - Report metadata
   - `{extracted_dir}/report_details.json` - Basic report details
   - `{extracted_dir}/cognos_report.json` - Serialized report object
   - `{extracted_dir}/report_queries.json` - Extracted queries
   - `{extracted_dir}/report_data_items.json` - Data items/columns
   - `{extracted_dir}/calculations.json` - Expressions with DAX conversion
   - `{extracted_dir}/report_parameters.json` - Parameters
   - `{extracted_dir}/report_filters.json` - Filters
   - `{extracted_dir}/report_layout.json` - Layout information

#### 2.4. Report Conversion

```python
# In cognos_migrator/migrator.py
def _convert_cognos_report_to_powerbi(self, cognos_report) -> Optional[PowerBIProject]:
    """Convert Cognos report to Power BI project structure"""
```

1. **Initialize Report Parser**
   - Creates an instance of `CognosReportSpecificationParser` from `report_parser.py`
   - This parser handles both XML and JSON report specifications

2. **Parse Report Specification**
   - Calls `report_parser.parse_report_specification(cognos_report.specification, cognos_report.metadata)`
   - Creates a structured representation of the report with pages, visuals, and data sources
   - Handles different Cognos visual types and maps them to Power BI equivalents

3. **Prepare Safe Table Name**
   - Sanitizes the report name for use as a table name
   - Removes special characters and replaces spaces with underscores

4. **Convert Parsed Structure**
   - Calls `_convert_parsed_structure(parsed_structure, safe_table_name)`
   - Transforms the parsed structure into a format suitable for Power BI
   - Creates tables, columns, measures, and relationships

5. **Create Data Model**
   - Calls `_create_report_data_model(converted_data, cognos_report.name)`
   - Builds a `DataModel` object with tables, relationships, and measures
   - Output structure: `PowerBIProject.data_model`

6. **Create Report Structure**
   - Calls `_create_report_structure_from_cognos(cognos_report, converted_data, data_model)`
   - Builds a `Report` object with pages and visuals
   - Maps Cognos visuals to Power BI visuals
   - Output structure: `PowerBIProject.report`

7. **Create Power BI Project**
   - Assembles a complete `PowerBIProject` object with:
     - Name: Based on Cognos report name
     - Version: "1.0"
     - Creation/modification timestamps
     - Data model
     - Report structure

8. **Perform Deduplication**
   - Calls `_deduplicate_columns(table)` for each table in the project
   - Removes duplicate columns that may have been missed in earlier processing
   - Ensures clean data model for Power BI

### 3. Key Components

#### 3.1. Report Parser

`CognosReportSpecificationParser` in `cognos_migrator/report_parser.py`:

```python
def parse_report_specification(self, report_spec: str, report_metadata: Dict) -> CognosReportStructure:
    """Parse Cognos report specification"""
```

This parser is responsible for:
- Parsing Cognos report specifications in XML or JSON format
- Extracting pages, visuals, data sources, and parameters
- Mapping Cognos visual types to Power BI visual types via `_load_visual_mappings()`
- Creating a structured representation of the report using classes:
  - `CognosReportStructure`: Complete report structure
  - `ReportPage`: Individual report pages
  - `CognosVisual`: Visual elements (tables, charts, etc.)
  - `VisualField`: Fields used in visuals

Key methods:
- `_parse_xml_specification()`: Handles XML-based reports
- `_parse_json_specification()`: Handles JSON-based reports
- `_extract_pages_from_xml()`: Extracts page definitions
- `_extract_visuals_from_xml_layout()`: Extracts visual elements
- `_extract_data_sources_from_xml()`: Extracts data source definitions

#### 3.2. Extractors

Located in the `cognos_migrator/extractors/` directory:

- **Base Extractor** (`base_extractor.py`):
  ```python
  class BaseExtractor:
      """Base class for all extractors"""
  ```
  - Provides common functionality for all extractors
  - Handles XML parsing and navigation
  - Implements common utility methods
  - Output: None (base class only)

- **Query Extractor** (`query_extractor.py`):
  ```python
  class QueryExtractor(BaseExtractor):
      """Extracts query definitions from Cognos report"""
  ```
  - Extracts query definitions and data sources
  - Identifies query items, joins, and filters
  - Output: `report_queries.json` containing query structures

- **Data Item Extractor** (`data_item_extractor.py`):
  ```python
  class DataItemExtractor(BaseExtractor):
      """Extracts data items from Cognos report"""
  ```
  - Extracts columns and their properties
  - Identifies data types, formats, and aggregations
  - Output: `report_data_items.json` with column definitions

- **Expression Extractor** (`expression_extractor.py`):
  ```python
  class ExpressionExtractor(BaseExtractor):
      """Extracts and converts expressions from Cognos report"""
  ```
  - Processes Cognos expressions and converts to DAX
  - Optionally uses LLM services for complex conversions
  - Output: `calculations.json` with original and converted expressions

- **Parameter Extractor** (`parameter_extractor.py`):
  ```python
  class ParameterExtractor(BaseExtractor):
      """Extracts parameters from Cognos report"""
  ```
  - Extracts report parameters and their properties
  - Identifies parameter types, defaults, and prompt text
  - Output: `report_parameters.json` with parameter definitions

- **Filter Extractor** (`filter_extractor.py`):
  ```python
  class FilterExtractor(BaseExtractor):
      """Extracts filters from Cognos report"""
  ```
  - Extracts report filters and their conditions
  - Identifies filter types, operators, and values
  - Output: `report_filters.json` with filter definitions

- **Layout Extractor** (`layout_extractor.py`):
  ```python
  class LayoutExtractor(BaseExtractor):
      """Extracts layout information from Cognos report"""
  ```
  - Extracts visual layout information
  - Identifies visual positions, sizes, and properties
  - Output: `report_layout.json` with layout definitions

#### 3.3. Generators

Located in the `cognos_migrator/generators/` directory:

- **Project Generator** (`project_generator.py`):
  ```python
  class PowerBIProjectGenerator:
      """Generates Power BI project files"""
  ```
  - Orchestrates the generation of all Power BI files
  - Coordinates other generators
  - Output files:
    - `Report.pbir` - Main Power BI report file
    - `DataModel.tmdl` - Tabular model definition
    - `DiagramLayout.json` - Model diagram layout
    - `Settings.json` - Project settings

- **Documentation Generator** (`doc_generator.py`):
  ```python
  class MigrationDocumentationGenerator:
      """Generates documentation for the migration"""
  ```
  - Creates comprehensive documentation for the migration
  - Documents tables, measures, and visuals
  - Output: `migration_report.md` with detailed documentation

- **Model File Generator** (`model_file_generator.py`):
  ```python
  class PowerBIModelFileGenerator:
      """Generates Power BI data model files"""
  ```
  - Generates the Power BI data model files
  - Creates tables, relationships, measures, and calculated columns
  - Output: `DataModel.tmdl` in Tabular Model Definition Language

- **Report File Generator** (`report_file_generator.py`):
  ```python
  class PowerBIReportFileGenerator:
      """Generates Power BI report files"""
  ```
  - Generates the Power BI report files
  - Creates pages, visuals, and their properties
  - Output: `Report.pbir` containing report definition

- **Template Engine** (`template_engine.py`):
  ```python
  class TemplateEngine:
      """Handles template-based file generation"""
  ```
  - Provides template-based file generation capabilities
  - Uses Jinja2 templates for generating structured files
  - Supports both JSON and XML output formats

#### 3.4. Converters

Located in the `cognos_migrator/converters/` directory:

- **Expression Converter** (`expression_converter.py`):
  ```python
  class CognosExpressionConverter:
      """Converts Cognos expressions to DAX"""
  ```
  - Converts Cognos expressions to DAX (Data Analysis Expressions)
  - Handles functions, operators, and aggregations
  - Optionally uses LLM services for complex conversions
  - Output: Converted DAX expressions used in `calculations.json`

- **M Query Converter** (`mquery_converter.py`):
  ```python
  class CognosMQueryConverter:
      """Converts Cognos queries to Power Query M"""
  ```
  - Converts Cognos queries to Power Query M language
  - Handles data sources, joins, and filters
  - Generates M query strings for Power BI
  - Output: M queries used in `DataModel.tmdl`

- **Visual Converter** (`visual_converter.py`):
  ```python
  class CognosVisualConverter:
      """Maps Cognos visuals to Power BI visuals"""
  ```
  - Maps Cognos visuals to Power BI visuals
  - Converts properties, formatting, and data bindings
  - Uses visual mapping configuration from `visual_mappings.json`
  - Output: Visual definitions used in `Report.pbir`

### 4. Data Flow

1. **Input**: 
   - Cognos report specification (XML/JSON) from `cognos_client.get_report(report_id)`
   - Report metadata from Cognos API
   - File paths: Raw input from Cognos API

2. **Parsing**: 
   - `report_parser.parse_report_specification(report_spec, metadata)`
   - Creates `CognosReportStructure` object with pages, visuals, data sources
   - File paths: Intermediate in-memory structures

3. **Extraction**: 
   - Extract components using specialized extractors:
     - `query_extractor.extract_queries()` → `{extracted_dir}/report_queries.json`
     - `data_item_extractor.extract_data_items()` → `{extracted_dir}/report_data_items.json`
     - `expression_extractor.extract_expressions()` → `{extracted_dir}/calculations.json`
     - `parameter_extractor.extract_parameters()` → `{extracted_dir}/report_parameters.json`
     - `filter_extractor.extract_filters()` → `{extracted_dir}/report_filters.json`
     - `layout_extractor.extract_layout()` → `{extracted_dir}/report_layout.json`

4. **Conversion**: 
   - `_convert_cognos_report_to_powerbi(cognos_report)` converts to Power BI structures:
     - `expression_converter.convert_expression()` transforms Cognos expressions to DAX
     - `visual_converter.convert_visual()` maps Cognos visuals to Power BI equivalents
     - `_create_report_data_model()` builds the data model with tables and relationships
   - File paths: In-memory `PowerBIProject` object

5. **Generation**: 
   - `project_generator.generate_project(powerbi_project, pbit_dir)` creates:
     - `{output_path}/pbit/DataModel.tmdl` - Tabular model definition
     - `{output_path}/pbit/Report.pbir` - Power BI report definition
     - `{output_path}/pbit/DiagramLayout.json` - Model diagram layout
     - `{output_path}/pbit/Settings.json` - Project settings
   - `doc_generator.generate_migration_report()` creates:
     - `{output_path}/extracted/migration_report.md` - Migration documentation

### 5. Post-Processing

After individual reports are migrated, the system performs these post-processing steps:

1. **Model Table Consolidation**:
   - Function: `consolidate_model_tables(output_path)` in `main.py`
   - Purpose: Combines individual model tables into a single consolidated model
   - Process:
     - Scans all `DataModel.tmdl` files in the output directory
     - Extracts and merges table definitions
     - Resolves naming conflicts and duplicates
     - Creates relationships between tables from different reports
   - Output: `{output_path}/consolidated/DataModel.tmdl`

2. **Migration Summary Generation**:
   - Class: `MigrationSummaryGenerator` in `summary.py`
   - Method: `generate_summary(results, output_path)`
   - Purpose: Creates a comprehensive migration report with statistics
   - Contents:
     - Total reports processed
     - Successful migrations count and percentage
     - Failed migrations with report IDs
     - Migration date and time
     - Next steps and recommendations
   - Output: `{output_path}/migration_summary.md`

3. **Cleanup and Optimization** (optional):
   - Removes temporary files if configured
   - Optimizes generated Power BI files for size
   - Validates generated files for Power BI compatibility

### 6. Summary Generation

The migration summary report is generated by the `MigrationSummaryGenerator` class in `cognos_migrator/summary.py`:

```python
class MigrationSummaryGenerator:
    """Generates migration summary reports"""
    
    def generate_summary(self, results: Dict[str, bool], output_path: str) -> None:
        """Generate migration summary report"""
```

This class was refactored from the original implementation in `migrator.py` to improve modularity and separation of concerns. The summary report provides:

- **Statistics**:
  - Total number of reports processed
  - Number of successful and failed migrations
  - Success rate percentage (calculated as successful/total * 100)

- **Detailed Lists**:
  - List of successful report IDs with checkmarks (✓)
  - List of failed report IDs with X marks (✗)

- **Metadata**:
  - Migration date and time (using `datetime.now()`)
  - Output directory path

- **Next Steps**:
  - Review failed migrations and check logs for error details
  - Validate successful migrations in Power BI Desktop
  - Test data connections and refresh capabilities
  - Review and adjust visual layouts as needed

**Output File**: `{output_path}/migration_summary.md`

**Integration**: The summary generator is instantiated in the `CognosModuleMigratorExplicit` class and called after batch migrations complete.

### Report Parser

The report parser is responsible for:
- Parsing the XML or JSON report specification
- Identifying report pages, layouts, and visuals
- Mapping Cognos visual types to their Power BI equivalents
- Extracting data sources and parameters
- Creating a structured representation of the report

### Extractors

Each extractor is specialized for a specific aspect of the report:

- **Query Extractor**: Extracts query definitions from the report specification
- **Data Item Extractor**: Extracts columns and their properties
- **Expression Extractor**: Extracts and processes Cognos expressions
- **Parameter Extractor**: Extracts report parameters and their properties
- **Filter Extractor**: Extracts report filters and conditions
- **Layout Extractor**: Extracts the visual layout of the report

### Generators

The generators are responsible for creating Power BI artifacts:

- **PowerBIProjectGenerator**: Orchestrates the generation of all Power BI files
- **ModelFileGenerator**: Creates the data model files (.tmdl)
- **ReportFileGenerator**: Creates the report files (.pbir)
- **DocumentationGenerator**: Creates documentation for the migration

### Converters

The converters transform Cognos-specific elements to Power BI:

- **ExpressionConverter**: Converts Cognos expressions to DAX
- **MQueryConverter**: Converts SQL or other queries to Power BI's M language

## Conclusion

The Cognos to Power BI migration process is a sophisticated pipeline that handles the extraction, transformation, and generation of Power BI artifacts from Cognos reports. The system uses a modular architecture with specialized components for each aspect of the migration, making it flexible and maintainable.

## Next Steps and Recommendations

### 1. Performance Optimization

- **Parallel Processing**: Implement parallel migration of reports using Python's `concurrent.futures` module
  ```python
  # Example implementation in migrator.py
  def migrate_folder_parallel(self, folder_id, output_path, max_workers=4):
      """Migrate all reports in a folder using parallel processing"""
      with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
          futures = {}
          for report_id in self.cognos_client.get_reports_in_folder(folder_id):
              futures[executor.submit(self.migrate_report, report_id, output_path)] = report_id
  ```

- **Batch Processing**: Add support for processing reports in configurable batch sizes
- **Caching**: Implement caching of common components like data sources and shared dimensions

### 2. Error Handling and Recovery

- **Checkpoint System**: Create checkpoints during migration to allow resuming from failures
  ```python
  # Example checkpoint implementation
  def _save_checkpoint(self, report_id, stage, data):
      """Save migration checkpoint"""
      checkpoint_file = Path(self.checkpoint_dir) / f"{report_id}_{stage}.checkpoint"
      with open(checkpoint_file, 'wb') as f:
          pickle.dump(data, f)
  ```

- **Partial Migration**: Allow successful parts of a failed migration to be preserved
- **Retry Mechanism**: Implement automatic retry for transient failures with exponential backoff

### 3. Visual Mapping Enhancements

- **Custom Visual Support**: Add support for custom Cognos visuals
  - Update `visual_mappings.json` with additional mappings
  - Extend `CognosVisualConverter` to handle custom visual properties

- **Advanced Formatting**: Improve conversion of complex formatting and conditional formatting
- **Interactive Features**: Better support for interactive features like drill-through and tooltips

### 4. LLM Integration Expansion

- **Enhanced Expression Conversion**: Expand LLM usage for complex expression conversion
  ```python
  # Example LLM integration for expression conversion
  def convert_complex_expression(self, cognos_expression):
      """Convert complex Cognos expression using LLM"""
      prompt = f"Convert this Cognos expression to DAX: {cognos_expression}"
      return self.llm_service.generate(prompt)
  ```

- **Query Optimization**: Use LLM to optimize generated M queries
- **Documentation Generation**: Generate more detailed documentation with LLM assistance

### 5. User Interface Development

- **Web Dashboard**: Create a web interface for monitoring migration progress
  - Real-time status updates via WebSockets
  - Visual representation of migration statistics
  - Detailed error reporting and troubleshooting guidance

- **Report Comparison**: Add visual comparison between original and migrated reports
- **Configuration UI**: Provide UI for configuring migration options and parameters

### 6. Testing and Validation

- **Automated Testing**: Develop automated tests to validate migrated reports
  ```python
  # Example test validation function
  def validate_migration(self, original_report_id, migrated_report_path):
      """Validate migrated report against original"""
      validation_results = {}
      # Check data model integrity
      validation_results['data_model'] = self._validate_data_model(migrated_report_path)
      # Check visual count and types
      validation_results['visuals'] = self._validate_visuals(original_report_id, migrated_report_path)
      return validation_results
  ```

- **Regression Testing**: Implement regression tests for ensuring migration quality over time
- **Performance Benchmarking**: Add tools for comparing performance between original and migrated reports
