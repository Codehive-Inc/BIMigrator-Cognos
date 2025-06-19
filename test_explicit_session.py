#!/usr/bin/env python3
"""
Test script for explicit session-based Cognos migration functions

This script demonstrates how to use the new functions that take explicit
cognos_url and session_key parameters without using environment variables.
It also includes WebSocket integration for real-time progress tracking.
"""

import sys
import logging
from cognos_migrator.module_migrator import (
    test_cognos_connection,
    migrate_module_with_explicit_session,
    post_process_module_with_explicit_session
)
from cognos_migrator.client import CognosAPIError
from cognos_migrator.common.websocket_client import set_websocket_post_function, set_task_info

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sample_websocket_function(data):
    """Sample WebSocket function for demonstration"""
    print(f"📡 WebSocket: {data['message']} (Progress: {data.get('progress', 'N/A')}%)")


def main(session_key: str = None):
    """Main test function"""
    
    # Set up WebSocket integration for progress tracking
    set_websocket_post_function(sample_websocket_function)
    set_task_info("explicit_session_test", 100)  # 100 total steps
    
    # Example usage - replace these with actual values
    cognos_url = "http://20.244.32.126:9300/api/v1"
    session_key = session_key or "YOUR_SESSION_KEY_HERE"  # Replace with actual session key
    module_id = "i5F34A7A52E2645C0AB03C34BA50941D7"  # Example module ID
    output_path = "./output/test_explicit_session"
    
    # Test 1: Test connection
    print("\n=== Testing Connection ===")
    try:
        is_connected = test_cognos_connection(cognos_url, session_key)
        if is_connected:
            print("✅ Connection successful!")
        else:
            print("❌ Connection failed!")
            return
    except Exception as e:
        print(f"❌ Connection test error: {e}")
        return
    
    # Test 2: Migrate module with explicit session
    print("\n=== Testing Module Migration ===")
    try:
        success = migrate_module_with_explicit_session(
            module_id=module_id,
            output_path=output_path,
            cognos_url=cognos_url,
            session_key=session_key,
            report_ids=["report1", "report2"]  # Optional report IDs
        )
        if success:
            print("✅ Module migration successful!")
        else:
            print("❌ Module migration failed!")
    except CognosAPIError as e:
        print(f"❌ Session error: {e}")
        print("The session key has expired. Please generate a new session key.")
        return
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return
    
    # Test 3: Post-process module with explicit session
    print("\n=== Testing Module Post-Processing ===")
    try:
        success = post_process_module_with_explicit_session(
            module_id=module_id,
            output_path=output_path,
            cognos_url=cognos_url,
            session_key=session_key,
            successful_report_ids=["report1", "report2"]
        )
        if success:
            print("✅ Post-processing successful!")
        else:
            print("❌ Post-processing failed!")
    except CognosAPIError as e:
        print(f"❌ Session error: {e}")
        print("The session key has expired. Please generate a new session key.")
    except Exception as e:
        print(f"❌ Post-processing error: {e}")
    
    print("\n=== Test Complete ===")


if __name__ == "__main__":
    # Check if session key is provided as command line argument
    if len(sys.argv) > 1:
        session_key = sys.argv[1]
        main(session_key)
    else:
        print("Usage: python test_explicit_session.py <session_key>")
        print("\nExample:")
        print("python test_explicit_session.py 'CAM AWkyOTE4MjMwOEY3N0Q0QkIyOEUwRURFMTQ2NzREQjUwNgJxgOzruzMUgqRDMXRAZl2ODpkK'")
        print("\nNote: The session key expires over time. Use a fresh session key for testing.")
        print("\nThese functions are completely independent of .env files and environment variables.")
        print("WebSocket integration provides real-time progress tracking during migration.")