# BIMigrator-Cognos Module Documentation

## Overview

This document provides a comprehensive overview of the module structure for the BIMigrator-Cognos system. The system is designed to migrate Cognos reports to Power BI, with a modular architecture that separates concerns across multiple components.

## Core Modules

### 1. Main Module (`main.py`)

**Purpose**: Entry point for the migration system, providing high-level functions for migration operations.

**Key Functions**:
- `test_cognos_connection(cognos_url, session_key)`: Tests connectivity to Cognos server
- `post_process_module_with_explicit_session(module_id, output_path, cognos_url, session_key, ...)`: Main function to process a Cognos module
- `consolidate_model_tables(output_path)`: Combines individual model tables into a consolidated model

**Dependencies**: `migrator.py`, `client.py`

**Usage Example**:
```python
from cognos_migrator.main import post_process_module_with_explicit_session

result = post_process_module_with_explicit_session(
    module_id="my_module_id",
    output_path="/path/to/output",
    cognos_url="https://cognos-server/ibmcognos",
    session_key="valid_session_key",
    cpf_file_path=None,
    use_llm=True
)
```

### 2. Migrator Module (`migrator.py`)

**Purpose**: Core migration logic for converting Cognos reports to Power BI.

**Key Classes**:
- `CognosModuleMigratorExplicit`: Handles migration without requiring environment variables

**Key Methods**:
- `migrate_report(report_id, output_path)`: Migrates a single Cognos report
- `migrate_folder(folder_id, output_path, recursive)`: Migrates all reports in a folder
- `migrate_module(module_id, output_path, folder_id, cpf_file_path)`: Migrates a complete module
- `_convert_cognos_report_to_powerbi(cognos_report)`: Converts Cognos report to Power BI structure
- `_save_extracted_report_data(cognos_report, extracted_dir)`: Saves extracted report data to files

**Dependencies**: `report_parser.py`, `client.py`, extractors, generators, converters

**Usage Example**:
```python
from cognos_migrator.migrator import CognosModuleMigratorExplicit

migrator = CognosModuleMigratorExplicit(
    cognos_url="https://cognos-server/ibmcognos",
    session_key="valid_session_key",
    use_llm=True
)
success = migrator.migrate_report("report123", "/path/to/output")
```

### 3. Client Module (`client.py`)

**Purpose**: Handles communication with the Cognos API.

**Key Classes**:
- `CognosClient`: Manages connections and requests to Cognos server

**Key Methods**:
- `get_report(report_id)`: Retrieves a report from Cognos
- `get_reports_in_folder(folder_id)`: Lists all reports in a folder
- `get_report_metadata(report_id)`: Retrieves metadata for a report
- `test_connection()`: Tests if the connection to Cognos is valid

**Dependencies**: External HTTP libraries

**Usage Example**:
```python
from cognos_migrator.client import CognosClient

client = CognosClient(
    cognos_url="https://cognos-server/ibmcognos",
    session_key="valid_session_key"
)
report = client.get_report("report123")
```

### 4. Report Parser Module (`report_parser.py`)

**Purpose**: Parses Cognos report specifications and creates structured representations.

**Key Classes**:
- `CognosReportSpecificationParser`: Parses report specifications
- `CognosReportStructure`: Represents the structure of a Cognos report
- `ReportPage`: Represents a page in a report
- `CognosVisual`: Represents a visual element in a report

**Key Methods**:
- `parse_report_specification(report_spec, report_metadata)`: Parses a report specification
- `_parse_xml_specification()`: Handles XML-based reports
- `_parse_json_specification()`: Handles JSON-based reports
- `_extract_pages_from_xml()`: Extracts page definitions
- `_extract_visuals_from_xml_layout()`: Extracts visual elements

**Dependencies**: XML parsing libraries

**Usage Example**:
```python
from cognos_migrator.report_parser import CognosReportSpecificationParser

parser = CognosReportSpecificationParser()
report_structure = parser.parse_report_specification(
    report_spec=xml_content,
    report_metadata=metadata_dict
)
```

### 5. Summary Module (`summary.py`)

**Purpose**: Generates migration summary reports.

**Key Classes**:
- `MigrationSummaryGenerator`: Creates summary reports for migrations

**Key Methods**:
- `generate_summary(results, output_path)`: Generates a migration summary report

**Dependencies**: None

**Usage Example**:
```python
from cognos_migrator.summary import MigrationSummaryGenerator

generator = MigrationSummaryGenerator()
generator.generate_summary(
    results={"report1": True, "report2": False},
    output_path="/path/to/output"
)
```

## Extractor Modules

Located in the `cognos_migrator/extractors/` directory:

### 1. Base Extractor (`base_extractor.py`)

**Purpose**: Provides common functionality for all extractors.

**Key Classes**:
- `BaseExtractor`: Base class for all extractors

**Key Methods**:
- `_parse_xml(xml_string)`: Parses XML content
- `_find_elements(element, xpath)`: Finds elements using XPath
- `_get_element_text(element, xpath)`: Gets text from an element

**Dependencies**: XML parsing libraries

### 2. Query Extractor (`query_extractor.py`)

**Purpose**: Extracts query definitions from Cognos reports.

**Key Classes**:
- `QueryExtractor(BaseExtractor)`: Extracts queries

**Key Methods**:
- `extract_queries(report_spec)`: Extracts queries from report specification
- `_extract_data_sources(query_element)`: Extracts data source information
- `_extract_query_items(query_element)`: Extracts query items

**Dependencies**: `base_extractor.py`

**Output**: `report_queries.json`

### 3. Data Item Extractor (`data_item_extractor.py`)

**Purpose**: Extracts data items/columns from Cognos reports.

**Key Classes**:
- `DataItemExtractor(BaseExtractor)`: Extracts data items

**Key Methods**:
- `extract_data_items(report_spec)`: Extracts data items from report specification
- `_extract_item_properties(item_element)`: Extracts properties of a data item
- `_determine_data_type(item_element)`: Determines the data type of an item

**Dependencies**: `base_extractor.py`

**Output**: `report_data_items.json`

### 4. Expression Extractor (`expression_extractor.py`)

**Purpose**: Extracts and converts expressions from Cognos reports.

**Key Classes**:
- `ExpressionExtractor(BaseExtractor)`: Extracts expressions

**Key Methods**:
- `extract_expressions(report_spec)`: Extracts expressions from report specification
- `convert_to_dax(expression)`: Converts Cognos expression to DAX
- `_process_function_call(expression_element)`: Processes a function call in an expression

**Dependencies**: `base_extractor.py`, optional LLM service

**Output**: `calculations.json`

### 5. Parameter Extractor (`parameter_extractor.py`)

**Purpose**: Extracts parameters from Cognos reports.

**Key Classes**:
- `ParameterExtractor(BaseExtractor)`: Extracts parameters

**Key Methods**:
- `extract_parameters(report_spec)`: Extracts parameters from report specification
- `_extract_parameter_properties(param_element)`: Extracts properties of a parameter
- `_determine_parameter_type(param_element)`: Determines the type of a parameter

**Dependencies**: `base_extractor.py`

**Output**: `report_parameters.json`

### 6. Filter Extractor (`filter_extractor.py`)

**Purpose**: Extracts filters from Cognos reports.

**Key Classes**:
- `FilterExtractor(BaseExtractor)`: Extracts filters

**Key Methods**:
- `extract_filters(report_spec)`: Extracts filters from report specification
- `_extract_filter_conditions(filter_element)`: Extracts conditions of a filter
- `_process_filter_expression(expression_element)`: Processes a filter expression

**Dependencies**: `base_extractor.py`

**Output**: `report_filters.json`

### 7. Layout Extractor (`layout_extractor.py`)

**Purpose**: Extracts layout information from Cognos reports.

**Key Classes**:
- `LayoutExtractor(BaseExtractor)`: Extracts layout information

**Key Methods**:
- `extract_layout(report_spec)`: Extracts layout from report specification
- `_extract_page_layout(page_element)`: Extracts layout of a page
- `_extract_visual_properties(visual_element)`: Extracts properties of a visual

**Dependencies**: `base_extractor.py`

**Output**: `report_layout.json`

## Generator Modules

Located in the `cognos_migrator/generators/` directory:

### 1. Project Generator (`project_generator.py`)

**Purpose**: Orchestrates the generation of Power BI files.

**Key Classes**:
- `PowerBIProjectGenerator`: Generates Power BI project files

**Key Methods**:
- `generate_project(project, output_dir)`: Generates all project files
- `_generate_settings_file(project, output_dir)`: Generates settings file
- `_generate_diagram_layout(project, output_dir)`: Generates diagram layout

**Dependencies**: Other generators

**Output Files**:
- `Report.pbir`
- `DataModel.tmdl`
- `DiagramLayout.json`
- `Settings.json`

### 2. Documentation Generator (`doc_generator.py`)

**Purpose**: Creates documentation for the migration.

**Key Classes**:
- `MigrationDocumentationGenerator`: Generates documentation

**Key Methods**:
- `generate_migration_report(project, output_dir)`: Generates migration documentation
- `_document_data_model(data_model)`: Documents the data model
- `_document_visuals(report)`: Documents the visuals in the report

**Dependencies**: Markdown libraries

**Output Files**: `migration_report.md`

### 3. Model File Generator (`model_file_generator.py`)

**Purpose**: Generates Power BI data model files.

**Key Classes**:
- `PowerBIModelFileGenerator`: Generates data model files

**Key Methods**:
- `generate_data_model(data_model, output_dir)`: Generates data model file
- `_generate_tables(data_model)`: Generates table definitions
- `_generate_relationships(data_model)`: Generates relationship definitions
- `_generate_measures(data_model)`: Generates measure definitions

**Dependencies**: TMDL libraries

**Output Files**: `DataModel.tmdl`

### 4. Report File Generator (`report_file_generator.py`)

**Purpose**: Generates Power BI report files.

**Key Classes**:
- `PowerBIReportFileGenerator`: Generates report files

**Key Methods**:
- `generate_report(report, output_dir)`: Generates report file
- `_generate_pages(report)`: Generates page definitions
- `_generate_visuals(page)`: Generates visual definitions
- `_apply_formatting(visual)`: Applies formatting to visuals

**Dependencies**: None

**Output Files**: `Report.pbir`

### 5. Template Engine (`template_engine.py`)

**Purpose**: Provides template-based file generation.

**Key Classes**:
- `TemplateEngine`: Handles template-based generation

**Key Methods**:
- `render_template(template_name, context)`: Renders a template with context
- `save_to_file(content, file_path)`: Saves content to a file
- `load_template(template_name)`: Loads a template from file

**Dependencies**: Jinja2

**Output**: Various template-based files

## Converter Modules

Located in the `cognos_migrator/converters/` directory:

### 1. Expression Converter (`expression_converter.py`)

**Purpose**: Converts Cognos expressions to DAX.

**Key Classes**:
- `CognosExpressionConverter`: Converts expressions

**Key Methods**:
- `convert_expression(cognos_expression)`: Converts a Cognos expression to DAX
- `_convert_function(function_name, arguments)`: Converts a function call
- `_convert_operator(operator, operands)`: Converts an operator expression

**Dependencies**: Optional LLM service

**Output**: DAX expressions for `calculations.json`

### 2. M Query Converter (`mquery_converter.py`)

**Purpose**: Converts Cognos queries to Power Query M.

**Key Classes**:
- `CognosMQueryConverter`: Converts queries

**Key Methods**:
- `convert_query(cognos_query)`: Converts a Cognos query to M query
- `_convert_data_source(data_source)`: Converts a data source definition
- `_convert_join(join_definition)`: Converts a join definition
- `_convert_filter(filter_definition)`: Converts a filter definition

**Dependencies**: None

**Output**: M queries for `DataModel.tmdl`

### 3. Visual Converter (`visual_converter.py`)

**Purpose**: Maps Cognos visuals to Power BI visuals.

**Key Classes**:
- `CognosVisualConverter`: Converts visuals

**Key Methods**:
- `convert_visual(cognos_visual)`: Converts a Cognos visual to Power BI visual
- `_map_visual_type(cognos_type)`: Maps a Cognos visual type to Power BI
- `_convert_properties(cognos_properties)`: Converts visual properties
- `_convert_data_bindings(cognos_bindings)`: Converts data bindings

**Dependencies**: Visual mapping configuration

**Output**: Visual definitions for `Report.pbir`

## Utility Modules

### 1. Logger (`logger.py`)

**Purpose**: Provides logging functionality.

**Key Functions**:
- `get_logger(name)`: Gets a logger instance
- `configure_logging(log_level, log_file)`: Configures logging

### 2. Config (`config.py`)

**Purpose**: Manages configuration settings.

**Key Functions**:
- `load_config(config_file)`: Loads configuration from file
- `get_config_value(key, default=None)`: Gets a configuration value

### 3. Websocket Helper (`websocket_helper.py`)

**Purpose**: Provides websocket communication for progress reporting.

**Key Classes**:
- `WebSocketProgressReporter`: Reports progress via websocket

**Key Methods**:
- `report_progress(stage, percentage, message)`: Reports progress
- `report_error(error_message)`: Reports an error
- `report_completion(message)`: Reports completion

## Integration Points

### 1. LLM Service Integration

**Purpose**: Integrates with LLM services for complex conversions.

**Key Components**:
- `llm_service.py`: Provides LLM service integration
- Usage in `expression_converter.py` and `mquery_converter.py`

### 2. CPF Metadata Enhancement

**Purpose**: Enhances migration with CPF metadata.

**Key Components**:
- `cpf_metadata_enhancer.py`: Enhances projects with CPF metadata
- Usage in `migrator.py` during report conversion

## File Structure

```
cognos_migrator/
├── __init__.py
├── main.py                  # Entry point
├── migrator.py              # Core migration logic
├── client.py                # Cognos API client
├── report_parser.py         # Report specification parser
├── summary.py               # Migration summary generator
├── extractors/              # Extractors for report components
│   ├── __init__.py
│   ├── base_extractor.py    # Base extractor class
│   ├── query_extractor.py   # Query extractor
│   ├── data_item_extractor.py # Data item extractor
│   ├── expression_extractor.py # Expression extractor
│   ├── parameter_extractor.py # Parameter extractor
│   ├── filter_extractor.py  # Filter extractor
│   └── layout_extractor.py  # Layout extractor
├── generators/              # Generators for Power BI files
│   ├── __init__.py
│   ├── project_generator.py # Project generator
│   ├── doc_generator.py     # Documentation generator
│   ├── model_file_generator.py # Model file generator
│   ├── report_file_generator.py # Report file generator
│   └── template_engine.py   # Template engine
├── converters/              # Converters for Cognos to Power BI
│   ├── __init__.py
│   ├── expression_converter.py # Expression converter
│   ├── mquery_converter.py  # M query converter
│   └── visual_converter.py  # Visual converter
└── utils/                   # Utility modules
    ├── __init__.py
    ├── logger.py            # Logging utilities
    ├── config.py            # Configuration utilities
    └── websocket_helper.py  # WebSocket helper
```

## Conclusion

The BIMigrator-Cognos system follows a modular architecture with clear separation of concerns. Each module has a specific responsibility in the migration process, from extracting Cognos report components to generating Power BI artifacts. This modular design makes the system maintainable, extensible, and testable.
