# WebSocket Logging Integration for BIMigrator

This document explains how to use the WebSocket logging system to send real-time logs from BIMigrator to a Django frontend.

## Overview

The WebSocket logging system allows BIMigrator to send log messages to a Django frontend in real-time via WebSockets. This is useful for displaying progress updates and log messages to users while a migration is running.

The system consists of:

1. **WebSocket Client**: A module that handles sending log messages to WebSockets
2. **Logging Helper**: A function for sending log messages with progress information
3. **Django Integration**: Code for receiving and displaying log messages in a Django application

## Installation

The WebSocket client is already included in the BIMigrator codebase. No additional installation is required.

## Usage

### 1. Setting Up in Django

Before calling BIMigrator from your Django application, you need to set up the WebSocket client:

```python
from bimigrator.common.websocket_client import (
    set_websocket_post_function,
    set_task_info,
    set_db_save_function
)
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def setup_websocket_logging(task_id):
    """Set up WebSocket logging for BIMigrator"""
    
    # Define a function to send data to WebSockets
    def websocket_sender(data):
        """Send data to WebSockets using Django Channels"""
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'migration_{data["task_id"]}',
            {
                'type': 'log_message',
                'message': data
            }
        )
    
    # Define a function to save logs to the database (optional)
    def db_saver(data):
        """Save log data to database"""
        from myapp.models import MigrationLog
        
        MigrationLog.objects.create(
            task_id=data.get('task_id'),
            message=data.get('message'),
            message_type=data.get('message_type'),
            progress=data.get('progress'),
            timestamp=data.get('timestamp')
        )
    
    # Set up the WebSocket client
    set_websocket_post_function(websocket_sender)
    set_db_save_function(db_saver)  # Optional
    
    # Set task info for progress tracking
    # Estimate the total number of steps based on your migration process
    set_task_info(task_id, total_steps=100)
```

### 2. Using in BIMigrator

There are two ways to use the WebSocket logging in BIMigrator:

#### Option 1: Using the logging_helper Function

You can use the `logging_helper` function directly in your code:

```python
from bimigrator.common.websocket_client import logging_helper

def extract_all_tables(self):
    """Extract all tables from the workbook."""
    try:
        # Log a message with progress
        logging_helper(
            "Using TableMetadataMapper to extract tables from datasources",
            progress=30,
            message_type='info'
        )
        
        # Do some work...
        mapper_tables = self.table_mapper.map_datasources_to_tables(self.root)
        
        # Log another message with progress
        logging_helper(
            f"TableMetadataMapper found {len(mapper_tables)} tables",
            progress=40,
            message_type='info'
        )
        
        # Rest of your code...
    except Exception as e:
        # Log an error
        logging_helper(
            f"Error extracting tables: {str(e)}",
            message_type='error',
            options={"exception": str(e)}
        )
```

#### Option 2: Using the Existing Logger

If you don't want to change your existing code, you can add a WebSocket handler to the logger:

```python
from bimigrator.common.websocket_client import WebSocketLogHandler
import logging

# Create and add the WebSocket handler
websocket_handler = WebSocketLogHandler()
logging.getLogger('bimigrator').addHandler(websocket_handler)

# Now all your existing logger.info() calls will also send to WebSockets
```

### 3. Django WebSocket Consumer

In your Django application, you need to create a WebSocket consumer to receive the log messages:

```python
# In consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class LogConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.task_id = self.scope['url_route']['kwargs']['task_id']
        self.log_group_name = f'migration_{self.task_id}'
        
        # Join log group
        await self.channel_layer.group_add(
            self.log_group_name,
            self.channel_name
        )
        
        await self.accept()

    async def disconnect(self, close_code):
        # Leave log group
        await self.channel_layer.group_discard(
            self.log_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        # Not used in this case
        pass

    # Receive message from room group
    async def log_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps(event['message']))
```

### 4. Django URL Routing

Set up URL routing for the WebSocket consumer:

```python
# In routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/migration/(?P<task_id>\w+)/$', consumers.LogConsumer.as_asgi()),
]
```

### 5. JavaScript Client

In your frontend, you can use JavaScript to connect to the WebSocket and display the log messages:

```javascript
// Connect to WebSocket
const taskId = "your_task_id";
const socket = new WebSocket(`ws://${window.location.host}/ws/migration/${taskId}/`);

// Set up event listeners
socket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    
    // Display the log message
    console.log(data);
    
    // Update progress bar if progress is available
    if (data.progress !== null) {
        document.getElementById('progress-bar').style.width = `${data.progress}%`;
        document.getElementById('progress-text').innerText = `${data.progress}%`;
    }
    
    // Add log message to log container
    const logContainer = document.getElementById('log-container');
    const logItem = document.createElement('div');
    logItem.className = `log-item log-${data.message_type}`;
    logItem.innerHTML = `
        <span class="timestamp">${new Date(data.timestamp).toLocaleTimeString()}</span>
        <span class="message">${data.message}</span>
    `;
    logContainer.appendChild(logItem);
    logContainer.scrollTop = logContainer.scrollHeight;
};

socket.onclose = function(e) {
    console.error('WebSocket closed unexpectedly');
};
```

## API Reference

### WebSocket Client Functions

#### `set_websocket_post_function(func)`

Set the function that will be used to post data to WebSockets.

- **Parameters:**
  - `func`: A function that takes a dictionary and sends it to WebSockets

#### `set_db_save_function(func)`

Set the function that will be used to save log data to the database.

- **Parameters:**
  - `func`: A function that takes a dictionary and saves it to the database

#### `set_task_info(task_id, total_steps)`

Set information about the current task for progress tracking.

- **Parameters:**
  - `task_id`: The ID of the current task
  - `total_steps`: The total number of steps in the task

#### `increment_progress()`

Increment the progress counter.

- **Returns:** The current progress percentage (0-100)

#### `logging_helper(message, progress=None, message_type='info', options=None)`

Send a log message to both the standard logging system and WebSockets.

- **Parameters:**
  - `message`: The log message to send
  - `progress`: Optional progress percentage (0-100)
  - `message_type`: Type of message ('info', 'warning', 'error')
  - `options`: Additional options to include in the message

### WebSocket Log Handler

#### `WebSocketLogHandler`

A logging handler that sends log messages to WebSockets.

- **Usage:**
  ```python
  handler = WebSocketLogHandler()
  logger.addHandler(handler)
  ```

## Examples

### Example 1: Basic Usage

```python
# In Django view
from bimigrator.common.websocket_client import set_websocket_post_function, set_task_info

def migrate_view(request):
    # Set up WebSocket logging
    task_id = "task_123"
    setup_websocket_logging(task_id)
    
    # Run migration
    migrate_to_tmdl(filename, output_dir)
    
    return JsonResponse({"task_id": task_id})
```

### Example 2: Progress Tracking

```python
# In BIMigrator code
from bimigrator.common.websocket_client import logging_helper

def process_tables(self):
    total_tables = len(self.tables)
    
    for i, table in enumerate(self.tables):
        # Calculate progress percentage
        progress = int((i / total_tables) * 100)
        
        # Log progress
        logging_helper(
            f"Processing table {table.name} ({i+1}/{total_tables})",
            progress=progress
        )
        
        # Process the table...
```

### Example 3: Error Handling

```python
# In BIMigrator code
from bimigrator.common.websocket_client import logging_helper

def extract_relationships(self):
    try:
        # Try to extract relationships
        relationships = self._extract_relationships()
        logging_helper(f"Extracted {len(relationships)} relationships", progress=70)
        return relationships
    except Exception as e:
        # Log the error
        logging_helper(
            f"Error extracting relationships: {str(e)}",
            message_type='error',
            options={"exception_type": type(e).__name__}
        )
        return []
```

## Best Practices

1. **Set Task Info Early**: Call `set_task_info()` before running any BIMigrator code to enable progress tracking.

2. **Estimate Total Steps**: Try to estimate the total number of steps in your migration process accurately for better progress reporting.

3. **Use Appropriate Message Types**: Use 'info' for normal messages, 'warning' for potential issues, and 'error' for errors.

4. **Include Context**: Use the `options` parameter to include additional context with your log messages.

5. **Handle WebSocket Errors**: Make sure your Django application handles WebSocket connection errors gracefully.

## Troubleshooting

### No Messages Being Sent

- Check that `set_websocket_post_function()` has been called with a valid function.
- Verify that the WebSocket connection is established in the frontend.

### Progress Not Updating

- Ensure that `set_task_info()` has been called with a reasonable estimate of total steps.
- Check that progress values are being provided to `logging_helper()`.

### WebSocket Connection Errors

- Verify that Django Channels is properly configured.
- Check that the WebSocket URL is correct in the frontend code.

## Conclusion

The WebSocket logging system provides a powerful way to send real-time updates from BIMigrator to a Django frontend. By following the instructions in this document, you can easily integrate this system into your application.
