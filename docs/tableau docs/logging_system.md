# BIMigrator Logging System

This document describes the logging system used in the BIMigrator project, including its design, configuration options, and how to extend it.

## Overview

The BIMigrator logging system is designed to:

1. Provide a centralized, consistent logging interface
2. Filter out unnecessary logs (e.g., PBIT file generation) while keeping important information
3. Support workbook-specific log files
4. Allow configuration through environment variables

## Key Components

### `log_utils.py`

The core of the logging system is the `log_utils.py` module, which provides:

- Function-based logging interface
- Environment variable configuration
- File operation filtering
- Workbook-specific log files

### Logging Functions

The module provides several logging functions:

- `log_info(message, context)`: Log an informational message
- `log_debug(message, context)`: Log a debug message
- `log_warning(message, context)`: Log a warning message
- `log_error(message, exception, context)`: Log an error message

### File Operation Logging

Special functions for logging file operations:

- `log_file_operation(file_path, operation_type, details)`: Base function for file operations
- `log_file_write(file_path, details)`: Log a file write operation
- `log_file_generated(file_path, details)`: Log a file generation operation
- `log_file_saved(file_path, details)`: Log a file save operation

## Configuration

The logging system can be configured using environment variables:

- `BIMIGRATOR_LOG_LEVEL`: Set the log level (debug, info, warning, error)
- `BIMIGRATOR_LOG_OUTPUT_FILES`: Enable logging of PBIT file generation (true/false)

## File Filtering

By default, the logging system filters out logs for:

- Files in the `/pbit/` directory
- Files with `.tmdl` extension
- Files with `.pbixproj.json` extension

But always shows logs for:

- Files in the `/extracted/` directory
- Other important files

## Log File Format

Log files are stored in the `logs` directory with the naming convention:

```
bimigrator_{workbook_name}_{timestamp}.log
```

Each log entry follows the format:

```
YYYY-MM-DD HH:MM:SS - LEVEL - MODULE - MESSAGE
```

## How to Use

### Basic Logging

```python
from bimigrator.common.log_utils import log_info, log_error

# Log an informational message
log_info("Processing started")

# Log an error with exception
try:
    # Some code that might raise an exception
    result = process_data()
except Exception as e:
    log_error("Failed to process data", e)
```

### File Operation Logging

```python
from bimigrator.common.log_utils import log_file_saved, log_file_generated

# Log a file save operation
log_file_saved("/path/to/file.json", "10 items")

# Log a file generation operation
log_file_generated("/path/to/generated/file.tmdl")
```

### Configuring Logging for a Workbook

```python
from bimigrator.common.log_utils import configure_logging

# Configure logging with workbook name
configure_logging("MyWorkbook")
```

## Extension Points

To extend the logging system:

1. **Add New Log Types**: Add new specialized logging functions in `log_utils.py`
2. **Enhance Filtering**: Modify the `log_file_operation` function to add more filtering rules
3. **Add Context Support**: Extend the context parameter usage for structured logging

## Best Practices

1. **Use the Right Log Level**: Use debug for development details, info for normal operations, warning for potential issues, and error for failures
2. **Include Context**: When logging, include relevant context to make troubleshooting easier
3. **Be Concise**: Keep log messages concise but informative
4. **Log at Boundaries**: Log at system boundaries (file I/O, network calls, etc.)
5. **Don't Log Sensitive Data**: Avoid logging sensitive information

## Future Improvements

Potential areas for improvement:

1. **Structured Logging**: Enhance with JSON-structured logging for better parsing
2. **Log Rotation**: Add log rotation to manage log file sizes
3. **Remote Logging**: Add support for sending logs to remote systems
4. **Performance Metrics**: Include performance metrics in logs
5. **Log Analysis Tools**: Develop tools to analyze and visualize logs

## Troubleshooting

If logs are not appearing as expected:

1. Check the `BIMIGRATOR_LOG_LEVEL` environment variable
2. Verify that `BIMIGRATOR_LOG_OUTPUT_FILES` is set correctly if you want to see PBIT file logs
3. Ensure that `configure_logging()` is called before any logging functions
4. Check the `logs` directory for the correct log file
