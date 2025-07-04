"""
Logging configuration for Cognos Migrator.

This module sets up basic logging and re-exports the logging utilities
from log_utils for easier access.
"""

import logging
from .log_utils import (
    configure_logging, log_info, log_debug, log_warning, log_error,
    log_file_operation, log_file_write, log_file_generated, log_file_saved,
    should_log_output_files, ENV_LOG_LEVEL, ENV_LOG_OUTPUT_FILES
)

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Re-export everything from log_utils
__all__ = [
    'configure_logging', 'log_info', 'log_debug', 'log_warning', 'log_error',
    'log_file_operation', 'log_file_write', 'log_file_generated', 'log_file_saved',
    'should_log_output_files', 'ENV_LOG_LEVEL', 'ENV_LOG_OUTPUT_FILES'
]
