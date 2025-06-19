# Cognos to Power BI Migration Process Overview

This document provides a high-level overview of the migration process from Cognos Analytics reports and modules to Power BI.

## Migration Types

The BIMigrator-Cognos tool supports two primary types of migration:

1. **Report Migration**: Converts individual Cognos reports to Power BI reports (.pbit)
2. **Module Migration**: Converts Cognos data modules to Power BI datasets (.pbit)

## Common Migration Process Flow

Both report and module migrations follow these common steps:

1. **Configuration Loading**
   - Load environment variables and configuration settings
   - Configure logging
   - Initialize services and connections

2. **Extraction**
   - Connect to Cognos Analytics API
   - Extract specifications and metadata
   - Save raw extracted data

3. **Data Model Generation**
   - Create Power BI tables, columns, and measures
   - Map Cognos data types to Power BI data types
   - Generate relationships between tables

4. **M-Query Generation**
   - Use LLM service to generate optimized M-queries
   - Map Cognos expressions to Power BI DAX/M expressions

5. **Power BI Project Generation**
   - Generate Power BI project files (.tmdl)
   - Create model structure and relationships
   - Package into .pbit format

6. **Documentation Generation**
   - Create migration report
   - Document any issues or limitations

## Report-Specific Process

Report migration includes these additional steps:

1. **Report Parsing**
   - Parse Cognos report XML specification
   - Extract data items, calculations, and visual elements

2. **Visual Conversion**
   - Map Cognos visuals to Power BI equivalents
   - Convert layout and formatting properties
   - Generate report.json and section files

## Module-Specific Process

Module migration includes these additional steps:

1. **Module Parsing**
   - Parse Cognos module specification
   - Extract tables, relationships, and calculations

2. **Module Structure Generation**
   - Generate module-specific model files
   - Create appropriate table structures
   - Preserve module-specific metadata

## Key Components

- **Main Module (`main.py`)**: Entry point and CLI interface
- **Migrator (`migrator.py` & `module_migrator.py`)**: Orchestrates the migration processes
- **Report Parser (`report_parser.py`)**: Parses Cognos report specifications
- **Module Parser (`module_parser.py`)**: Extracts data module information
- **Generators**: 
  - `model_file_generator.py`: Base generator for Power BI model files
  - `module_model_file_generator.py`: Module-specific generator
  - `report_file_generator.py`: Report-specific generator
- **LLM Service (`llm_service.py`)**: Handles AI-powered transformations
- **CPF Extractor (`cpf_extractor.py`)**: Extracts metadata from Cognos package files

## Command-Line Interface

The tool provides several commands:

- `python main.py demo`: Run a demonstration migration
- `python main.py list`: List available reports and folders
- `python main.py migrate-report <report_id> [output]`: Migrate a single report
- `python main.py migrate-module <module_id> [<folder_id>] [output]`: Migrate a data module
- `python main.py migrate-folder <folder_id> [output]`: Migrate all reports in a folder
- `python main.py validate`: Validate migration prerequisites

For more detailed information on each component, see the individual process documentation files.
