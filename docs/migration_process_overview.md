# Cognos to Power BI Migration Process Overview

This document provides a high-level overview of the migration process from Cognos Analytics reports to Power BI.

## Migration Process Flow

The migration process follows these main steps:

1. **Configuration Loading**
   - Load environment variables and configuration settings
   - Configure logging

2. **Report Extraction**
   - Connect to Cognos Analytics API
   - Extract report specifications and metadata
   - Save raw extracted data

3. **Report Parsing**
   - Parse Cognos report XML specification
   - Extract data items, calculations, and visual elements

4. **Data Model Generation**
   - Create Power BI tables, columns, and measures
   - Map Cognos data types to Power BI data types
   - Generate relationships between tables

5. **M-Query Generation**
   - Use LLM service to generate optimized M-queries
   - Map Cognos expressions to Power BI DAX/M expressions

6. **Power BI Project Generation**
   - Generate Power BI project files (.tmdl)
   - Create report visuals and layouts
   - Package into .pbit format

7. **Documentation Generation**
   - Create migration report
   - Document any issues or limitations

## Key Components

- **Main Module (`main.py`)**: Entry point and CLI interface
- **Migrator (`migrator.py`)**: Orchestrates the migration process
- **Report Parser (`report_parser.py`)**: Parses Cognos report specifications
- **Module Parser (`module_parser.py`)**: Extracts data model information
- **Generators (`generators.py`)**: Generates Power BI project files
- **LLM Service (`llm_service.py`)**: Handles AI-powered transformations
- **CPF Extractor (`cpf_extractor.py`)**: Extracts metadata from Cognos package files

## Command-Line Interface

The tool provides several commands:

- `python main.py demo`: Run a demonstration migration
- `python main.py list`: List available reports and folders
- `python main.py migrate-report <report_id> [output]`: Migrate a single report
- `python main.py migrate-folder <folder_id> [output]`: Migrate all reports in a folder
- `python main.py validate`: Validate migration prerequisites

For more detailed information on each component, see the individual process documentation files.
