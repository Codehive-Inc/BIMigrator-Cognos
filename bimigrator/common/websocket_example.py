"""
Example showing how to use the WebSocket logging with Django.

This file demonstrates how to set up the WebSocket logging in both
the Django application and the BIMigrator codebase.
"""

from typing import Dict, Any
import logging

# Import the WebSocket client functions
from bimigrator.common.websocket_client import (
    set_websocket_post_function,
    set_task_info,
    set_db_save_function,
    logging_helper
)

# Example Django setup (this would be in your Django app)
def setup_for_django():
    """
    Example of how to set up the WebSocket client in a Django application.
    
    This function would be called from your Django views or tasks
    before running the BIMigrator code.
    """
    # Define a function to send data to WebSockets
    def django_websocket_sender(data: Dict[str, Any]) -> None:
        """
        Function that sends data to WebSockets using Django Channels.
        
        In a real Django app, this would use the channel_layer to send
        the data to the appropriate WebSocket group.
        """
        print(f"[DJANGO WEBSOCKET] Would send: {data}")
        # In a real Django app, this would be:
        # from channels.layers import get_channel_layer
        # from asgiref.sync import async_to_sync
        # 
        # channel_layer = get_channel_layer()
        # async_to_sync(channel_layer.group_send)(
        #     f'migration_{data["task_id"]}',
        #     {
        #         'type': 'log_message',
        #         'message': data
        #     }
        # )
    
    # Define a function to save data to the database
    def django_db_saver(data: Dict[str, Any]) -> None:
        """
        Function that saves log data to the database.
        
        In a real Django app, this would create a new database record
        for each log message.
        """
        print(f"[DJANGO DB] Would save: {data}")
        # In a real Django app, this would be:
        # from myapp.models import MigrationLog
        # 
        # MigrationLog.objects.create(
        #     task_id=data.get('task_id'),
        #     message=data.get('message'),
        #     message_type=data.get('message_type'),
        #     progress=data.get('progress'),
        #     timestamp=data.get('timestamp')
        # )
    
    # Set up the WebSocket client
    set_websocket_post_function(django_websocket_sender)
    set_db_save_function(django_db_saver)
    
    # Set task info for progress tracking
    set_task_info("example_task_123", 10)  # 10 total steps
    
    print("WebSocket client set up for Django")

# Example of how to use the logging_helper in BIMigrator code
def example_bimigrator_function():
    """
    Example of how to use the logging_helper in BIMigrator code.
    
    This shows how you can use the logging_helper function in your
    existing BIMigrator code to send logs to both the standard
    logging system and the WebSocket.
    """
    # Log a message with progress
    logging_helper("Starting table extraction", progress=10, message_type='info')
    
    # Do some work...
    
    # Log another message with progress
    logging_helper("Found 5 tables from datasources", progress=30, message_type='info')
    
    # Log a warning
    logging_helper("Some tables have missing columns", progress=50, message_type='warning')
    
    # Log an error
    logging_helper("Failed to extract relationship tables", progress=60, message_type='error', 
                  options={"error_code": "REL_001"})
    
    # Log completion
    logging_helper("Table extraction complete", progress=100, message_type='info')

# Example of how to run this from Django
def run_from_django():
    """
    Example of how to run BIMigrator from Django with WebSocket logging.
    """
    # Set up the WebSocket client
    setup_for_django()
    
    # Run the BIMigrator function
    example_bimigrator_function()

if __name__ == "__main__":
    # Set up logging for the example
    logging.basicConfig(level=logging.INFO)
    
    # Run the example
    run_from_django()
