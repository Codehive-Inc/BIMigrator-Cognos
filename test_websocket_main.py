#!/usr/bin/env python
"""
Test script to demonstrate WebSocket logging in the migration process.
This script simulates a Django application setting up WebSocket logging
and then running a migration.
"""
import os
import sys
from bimigrator.common.websocket_client import set_websocket_post_function, set_db_save_function
from bimigrator.main import migrate_to_tmdl

def mock_websocket_sender(data):
    """
    Mock function that simulates sending data to a WebSocket.
    In a real Django application, this would use channel_layer.group_send.
    """
    print(f"[WEBSOCKET] {data['message_type'].upper()}: {data['message']} (Progress: {data['progress']}%)")

def mock_db_save(data):
    """
    Mock function that simulates saving log data to a database.
    In a real Django application, this would create a database record.
    """
    print(f"[DATABASE] Saved: {data['message']} (Progress: {data['progress']}%)")

def main():
    """
    Main function to test WebSocket logging with the migration process.
    """
    # Check if a file path was provided
    if len(sys.argv) < 2:
        print("Usage: python test_websocket_main.py <path_to_twb_file>")
        sys.exit(1)
    
    # Get the file path from command line arguments
    file_path = sys.argv[1]
    
    # Set up WebSocket logging
    set_websocket_post_function(mock_websocket_sender)
    set_db_save_function(mock_db_save)
    
    # Create output directory
    output_dir = "websocket_test_output"
    os.makedirs(output_dir, exist_ok=True)
    
    print("\n=== Starting migration with WebSocket logging ===\n")
    
    # Run the migration with WebSocket logging
    # Skip license check for testing purposes
    migrate_to_tmdl(
        file_path,
        output_dir=output_dir,
        skip_license_check=True
    )
    
    print("\n=== Migration completed ===\n")

if __name__ == "__main__":
    main()
