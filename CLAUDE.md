# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BIMigrator-Cognos is a migration tool that converts Cognos Analytics reports and data modules to Power BI format (.pbit files). The tool handles two main migration types:
- **Report Migration**: Converts individual Cognos reports to Power BI reports
- **Module Migration**: Converts Cognos data modules to Power BI datasets

## Architecture

### Key Components

1. **Main Entry Points**
   - `cognos_migrator/main.py`: CLI interface and orchestration
   - `cognos_migrator/migrator.py`: Report migration orchestrator
   - `cognos_migrator/module_migrator.py`: Module migration orchestrator

2. **Core Modules**
   - **Client** (`cognos_migrator/client.py`): Handles Cognos API authentication and communication
   - **Parsers**: Extract and transform Cognos specifications
     - `report_parser.py`: Parses Cognos report XML specifications
     - `module_parser.py`: Extracts data module information
   - **Extractors** (`extractors/`): Extract specific components (data items, expressions, filters, queries)
   - **Generators** (`generators/`): Generate Power BI project files
     - `model_file_generator.py`: Base generator for Power BI model files
     - `module_model_file_generator.py`: Module-specific generator
     - `report_file_generator.py`: Report-specific generator
   - **Converters**: Transform Cognos expressions to Power BI DAX/M expressions
   - **LLM Service** (`llm_service.py`): AI-powered expression transformations

3. **Templates** (`cognos_migrator/templates/`): Power BI TMDL and JSON templates

## Common Commands

### Build and Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Install as editable package
pip install -e .

# Run using the installed command
bimigrator --help
```

### Running Migrations
```bash
# List available content
python cognos_migrator/main.py list

# Migrate a single report
python cognos_migrator/main.py migrate-report <report_id> [output_dir]

# Migrate a data module
python cognos_migrator/main.py migrate-module <module_id> [<folder_id>] [output_dir]

# Migrate all reports in a folder
python cognos_migrator/main.py migrate-folder <folder_id> [output_dir]

# Run demonstration
python cognos_migrator/main.py demo

# Validate setup
python cognos_migrator/main.py validate
```

### Testing
```bash
# Run individual test files
python test_module_migration.py
python test_real_folder.py
python tests/test_complete_migration.py

# Run specific test demos
python tests/demo_migration.py
python tests/demo_module_migration.py
```

### Development and Debugging
```bash
# List Cognos content (debugging)
python list_cognos_content.py

# Deep search for reports
python deep_search_reports.py

# Test module CLI
python test_module_cli.py
```

## Environment Configuration

The project uses a `.env` file for configuration. Key variables:
- `COGNOS_BASE_URL`: Cognos Analytics API endpoint
- `COGNOS_USERNAME` / `COGNOS_PASSWORD`: Authentication credentials
- `COGNOS_NAMESPACE`: Cognos namespace (default: CognosEx)
- `OUTPUT_DIR`: Output directory for migrations
- `TEMPLATE_DIR`: Template directory path

## Migration Process Flow

1. **Configuration Loading**: Load environment variables and settings
2. **Authentication**: Connect to Cognos Analytics API
3. **Extraction**: Extract specifications and metadata from Cognos
4. **Parsing**: Parse XML specifications to extract components
5. **Model Generation**: Create Power BI tables, columns, and measures
6. **Expression Conversion**: Convert Cognos expressions to DAX/M
7. **Project Generation**: Generate Power BI project files (.tmdl format)
8. **Documentation**: Create migration reports and logs

## Key Considerations

- The tool generates Power BI Tabular Model Definition Language (TMDL) files
- Expressions are converted using LLM service when complex transformations are needed
- The migration preserves relationships, hierarchies, and calculations where possible
- Output follows Power BI project structure with Model/ and Report/ directories
- Migration reports document any issues or limitations encountered

## File Structure Patterns

- **Extractors**: `extractors/*_extractor.py` - Component-specific extraction logic
- **Generators**: `generators/*_generator.py` - File generation logic
- **Templates**: `templates/*.tmdl` / `templates/*.json` - Power BI templates
- **Output**: `output/<migration_id>/extracted/` and `output/<migration_id>/pbit/`





Normally, COGNOS_BASE_URL, COGNOS_USERNAME, COGNOS_PASSWORD, COGNOS_AUTH_KEY, and COGNOS_BASE_AUTH_TOKEN to generate session_key to perform further actions. If the session_key is expired, we regenerate a new session_key by re-authentication with COGNOS_BASE_URL, COGNOS_USERNAME, COGNOS_PASSWORD, COGNOS_AUTH_KEY, and COGNOS_BASE_AUTH_TOKEN. 

I want to add a new test_connection method that specifically takes only cognos_url and session_key as parameters explicitly. and see if the connection is set or not. We won't be using environment variables in this function.

Similarly, I want to create a version for each migrate_module and post_process_module functions that would take additional parameters cognos_url, and session_key explicitly. It also won't use .env variables to get the results if the session_key is expired rather will throw an exception.

## Explicit Session Functions

The following functions have been added to support explicit session-based authentication without using environment variables:

### In `cognos_migrator/client.py`:
- `CognosClient.test_connection(cognos_url: str, session_key: str) -> bool`: Static method to test connection validity

### In `cognos_migrator/module_migrator.py`:
- `test_cognos_connection(cognos_url: str, session_key: str) -> bool`: Module-level function to test connection
- `migrate_module_with_explicit_session(module_id, output_path, cognos_url, session_key, report_ids=None, cpf_file_path=None) -> bool`: Migrate module with explicit credentials
- `post_process_module_with_explicit_session(module_id, output_path, cognos_url, session_key, successful_report_ids=None) -> bool`: Post-process module with explicit credentials
- `CognosModuleMigrator.migrate_module_with_session(...)`: Instance method version
- `CognosModuleMigrator.post_process_module_with_session(...)`: Instance method version

These functions will raise `CognosAPIError` if the session key is expired or invalid, rather than attempting to re-authenticate.

**Key Features:**
- ✅ **Zero .env dependencies** - No environment variables required
- ✅ **Explicit session management** - Full control over authentication
- ✅ **Clear error handling** - Raises exceptions for expired sessions
- ✅ **Web application ready** - Easy integration into REST APIs
- ✅ **Minimal configuration** - Creates configs programmatically
- ✅ **WebSocket integration** - Real-time progress tracking with logging_helper

### Example Usage:
```python
from cognos_migrator.module_migrator import (
    test_cognos_connection,
    migrate_module_with_explicit_session,
    post_process_module_with_explicit_session
)
from cognos_migrator.client import CognosAPIError

# Test connection first
if not test_cognos_connection(cognos_url, session_key):
    raise Exception("Invalid session")

# Migrate module
try:
    success = migrate_module_with_explicit_session(
        module_id="i5F34A7A52E2645C0AB03C34BA50941D7",
        output_path="./output/my_module",
        cognos_url="http://20.244.32.126:9300/api/v1",
        session_key="CAM AWkyOTE4...",
        report_ids=["report1", "report2"],
        cpf_file_path=None,  # Optional
        auth_key="IBM-BA-Authorization"  # Optional
    )
    
    if success:
        # Post-process
        post_process_module_with_explicit_session(
            module_id="i5F34A7A52E2645C0AB03C34BA50941D7",
            output_path="./output/my_module",
            cognos_url="http://20.244.32.126:9300/api/v1",
            session_key="CAM AWkyOTE4...",
            successful_report_ids=["report1", "report2"]
        )
        
except CognosAPIError as e:
    print(f"Session expired: {e}")
```

### WebSocket Integration:
```python
from cognos_migrator.common.websocket_client import set_websocket_post_function, set_task_info

# Set up WebSocket for real-time progress tracking
def websocket_handler(data):
    print(f"Progress: {data['message']} ({data.get('progress', 0)}%)")

set_websocket_post_function(websocket_handler)
set_task_info("migration_task", 100)

# Now run migration - progress will be sent to WebSocket
migrate_module_with_explicit_session(...)
```

### Testing:
```bash
# Test the explicit session functions with WebSocket tracking
python test_explicit_session.py "YOUR_SESSION_KEY"

# Comprehensive validation test (tests error handling with invalid sessions)
python test_comprehensive_validation.py

# Comprehensive validation test with valid session
python test_comprehensive_validation.py "YOUR_VALID_SESSION_KEY"

# See example usage patterns
python example_explicit_session_usage.py
```

### Validation Results:
✅ **All methods properly validate session keys before proceeding**
✅ **Invalid/expired sessions immediately raise `CognosAPIError`**
✅ **No .env dependencies - functions work completely independently**
✅ **WebSocket integration provides real-time progress tracking**
✅ **Proper error handling at all levels (connection, migration, post-processing)**
✅ **Class instantiation works with both valid and invalid sessions**
