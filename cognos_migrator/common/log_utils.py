"""
Simplified logging utilities for Cognos Migrator.

This module provides a streamlined logging interface that:
1. Centralizes logging configuration and formatting
2. Provides function-based logging to reduce code duplication
3. Filters out unnecessary logs for generated files
4. Ensures important information is still logged
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, Union

# Environment variables for logging control
ENV_LOG_LEVEL = 'COGNOS_MIGRATOR_LOG_LEVEL'
ENV_LOG_OUTPUT_FILES = 'COGNOS_MIGRATOR_LOG_OUTPUT_FILES'

# Configure logger
logger = logging.getLogger('cognos_migrator')

def should_log_output_files() -> bool:
    """Check if output file logging is enabled.
    
    Returns:
        True if output file logging is enabled, False otherwise
    """
    return os.environ.get(ENV_LOG_OUTPUT_FILES, 'false').lower() == 'true'

def configure_logging(module_name: Optional[str] = None) -> None:
    """Configure the logging system.
    
    Args:
        module_name: Optional name of the module being processed
    """
    # Get log level from environment variable
    log_level_name = os.environ.get(ENV_LOG_LEVEL, 'info').lower()
    log_level = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }.get(log_level_name, logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s', 
                                 '%Y-%m-%d %H:%M:%S')
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if module name is provided
    if module_name:
        # Create logs directory if it doesn't exist
        logs_dir = Path('logs')
        logs_dir.mkdir(exist_ok=True)
        
        # Create a log file with module name and timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        clean_name = ''.join(c if c.isalnum() else '_' for c in module_name)
        log_file = logs_dir / f'cognos_migrator_{clean_name}_{timestamp}.log'
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        
        # Log configuration details
        logger.info(f"Logging configured with level: {logging.getLevelName(log_level)}")
        logger.info(f"Log file: {log_file}")

def log_info(message: str, context: Optional[Dict[str, Any]] = None) -> None:
    """Log an informational message.
    
    Args:
        message: Message to log
        context: Optional context dictionary
    """
    logger.info(message)

def log_debug(message: str, context: Optional[Dict[str, Any]] = None) -> None:
    """Log a debug message.
    
    Args:
        message: Message to log
        context: Optional context dictionary
    """
    logger.debug(message)

def log_warning(message: str, context: Optional[Dict[str, Any]] = None) -> None:
    """Log a warning message.
    
    Args:
        message: Message to log
        context: Optional context dictionary
    """
    logger.warning(message)

def log_error(message: str, exception: Optional[Exception] = None, context: Optional[Dict[str, Any]] = None) -> None:
    """Log an error message.
    
    Args:
        message: Message to log
        exception: Optional exception that caused the error
        context: Optional context dictionary
    """
    if exception:
        logger.error(f"{message}: {str(exception)}", exc_info=exception)
    else:
        logger.error(message)

def log_file_operation(file_path: str, operation_type: str, details: Optional[str] = None) -> None:
    """Log a file operation, filtering out output file operations unless explicitly enabled.
    
    Args:
        file_path: Path to the file being operated on
        operation_type: Type of operation (e.g., 'Saved', 'Generated', 'Write')
        details: Optional additional details about the operation
    """
    # Check if this is an output file that should be suppressed
    is_output_file = False
    
    # Check if the file path contains /pbit/ directory or ends with .tmdl or .pbixproj.json
    if '/pbit/' in file_path or file_path.endswith('.tmdl') or file_path.endswith('.pbixproj.json'):
        is_output_file = True
    
    # Check if this is an extracted file
    is_extracted_file = '/extracted/' in file_path
    
    # Only log if:
    # 1. It's an extracted file (always log these)
    # 2. It's not an output file, or
    # 3. It's an output file but output file logging is enabled
    if is_extracted_file or not is_output_file or should_log_output_files():
        message = f"{operation_type} {file_path}"
        if details:
            message += f" - {details}"
        
        logger.info(message)

def log_file_write(file_path: str, details: Optional[str] = None) -> None:
    """Log a file write operation.
    
    Args:
        file_path: Path to the file being written
        details: Optional additional details about the operation
    """
    log_file_operation(file_path, "Write file:", details)

def log_file_generated(file_path: str, details: Optional[str] = None) -> None:
    """Log a file generation operation.
    
    Args:
        file_path: Path to the file being generated
        details: Optional additional details about the operation
    """
    log_file_operation(file_path, "Generated", details)

def log_file_saved(file_path: str, details: Optional[str] = None) -> None:
    """Log a file save operation.
    
    Args:
        file_path: Path to the file being saved
        details: Optional additional details about the operation
    """
    log_file_operation(file_path, "Saved", details)

# Configure logging when the module is imported
configure_logging()
