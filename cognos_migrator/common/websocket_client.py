"""
WebSocket client for sending log messages to Django.

This module provides functionality to send log messages to a Django WebSocket consumer.
It can be used alongside the existing logging system.
"""

import json
import logging
import datetime
from typing import Dict, Any, Optional, Callable, Union, Literal

# Type hint for the WebSocket post function
WebSocketPostFunc = Optional[Callable[[Dict[str, Any]], None]]

# Global variables
_cognos_websocket_post_function: WebSocketPostFunc = None
_cognos_task_id: Optional[str] = None
_cognos_total_steps: Optional[int] = None
_cognos_current_step: int = 0
_cognos_db_save_function: Optional[Callable[[Dict[str, Any]], None]] = None

def set_websocket_post_function(func: WebSocketPostFunc) -> None:
    """
    Set the function that will be used to post data to WebSockets.
    
    This function should be called by the Django app to provide the
    implementation for sending data to WebSockets.
    
    Args:
        func: A function that takes a dictionary and sends it to WebSockets
    """
    global _cognos_websocket_post_function
    _cognos_websocket_post_function = func

def set_task_info(task_id: str, total_steps: int) -> None:
    """
    Set information about the current task for progress tracking.
    
    Args:
        task_id: The ID of the current task
        total_steps: The total number of steps in the task
    """
    global _cognos_task_id, _cognos_total_steps, _cognos_current_step
    _cognos_task_id = task_id
    _cognos_total_steps = total_steps
    _cognos_current_step = 0

def increment_progress() -> None:
    """
    Increment the progress counter.
    
    Returns:
        The current progress percentage (0-100)
    """
    global _cognos_current_step, _cognos_total_steps
    if _cognos_total_steps is not None and _cognos_total_steps > 0:
        _cognos_current_step = min(_cognos_current_step + 1, _cognos_total_steps)
        return int((_cognos_current_step / _cognos_total_steps) * 100)
    return None

def get_progress() -> Optional[int]:
    """
    Get the current progress percentage.
    
    Returns:
        The current progress percentage (0-100) or None if not set
    """
    global _cognos_current_step, _cognos_total_steps
    if _cognos_total_steps is not None and _cognos_total_steps > 0:
        return int((_cognos_current_step / _cognos_total_steps) * 100)
    return None

def set_db_save_function(func: Callable[[Dict[str, Any]], None]) -> None:
    """
    Set the function that will be used to save log data to the database.
    
    Args:
        func: A function that takes a dictionary and saves it to the database
    """
    global _cognos_db_save_function
    _cognos_db_save_function = func

def post_websocket_data(data: Dict[str, Any]) -> None:
    """
    Post data to WebSockets if a posting function has been set.
    
    Args:
        data: The data to post to WebSockets
    """
    global _cognos_websocket_post_function, _cognos_task_id, _cognos_db_save_function
    
    # Add task_id if available
    if _cognos_task_id is not None and "task_id" not in data:
        data["task_id"] = _cognos_task_id
        
    # Add timestamp if not present
    if "timestamp" not in data:
        data["timestamp"] = datetime.datetime.now().isoformat()
    
    # Send to WebSocket if function is set
    if _cognos_websocket_post_function is not None:
        try:
            _cognos_websocket_post_function(data)
        except Exception as e:
            logging.error(f"Error sending to WebSocket: {str(e)}")
    else:
        # Log that we would have sent data if the function was set
        logging.debug(f"WebSocket post function not set, would have posted: {data}")
    
    # Save to database if function is set
    if _cognos_db_save_function is not None:
        try:
            _cognos_db_save_function(data)
        except Exception as e:
            logging.error(f"Error saving to database: {str(e)}")

def logging_helper(
    message: str,
    progress: Optional[int] = None,
    message_type: Literal['info', 'warning', 'error'] = 'info',
    options: Optional[Dict[str, Any]] = None
) -> None:
    """
    Logging helper for using inside migrator function.
    
    This function sends log messages to both the standard logging system
    and to the WebSocket for real-time updates in the Django frontend.
    
    Args:
        message: Message of output or processing.
        progress: Progress of task in percentage integer. Must be within 0 and 100.
        message_type: Type of message, must be of type info, warning, error.
        options: Additional options to include in the log message.
    
    Usage:
        >>> logging_helper("Importing module for processing.", progress=12, message_type='info')
    """
    # Map message_type to log level
    level_map = {
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR
    }
    level = level_map.get(message_type, logging.INFO)
    
    # Log using the standard logging system
    logger = logging.getLogger('cognos_migrator')
    logger.log(level, message)
    
    # Use provided progress or calculate from the task info
    current_progress = progress if progress is not None else get_progress()
    
    # Create the data to send
    data = {
        "message": message,
        "progress": current_progress,
        "message_type": message_type,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    # Add any additional options
    if options:
        data.update(options)
    
    # Post the data to WebSockets and/or database
    post_websocket_data(data)

# Create a class that can be used as a logging handler
class WebSocketLogHandler(logging.Handler):
    """
    A logging handler that sends log messages to WebSockets.
    """
    
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
    
    def emit(self, record):
        """
        Emit a log record to WebSockets.
        
        Args:
            record: The log record to emit
        """
        # Determine message type based on log level
        message_type = 'info'
        if record.levelno >= logging.ERROR:
            message_type = 'error'
        elif record.levelno >= logging.WARNING:
            message_type = 'warning'
        
        # Format the message
        message = self.format(record)
        
        # Send the log message
        logging_helper(message, None, message_type)
