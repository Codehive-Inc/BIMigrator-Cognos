#!/usr/bin/env python3
"""
Test script for migrate_module_with_explicit_session function

This script demonstrates how to test the migrate_module_with_explicit_session
function that takes explicit cognos_url and session_key parameters without
using environment variables.
"""

import sys
import logging
from cognos_migrator.module_migrator import (
    test_cognos_connection,
    migrate_module_with_explicit_session
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
    set_task_info("migrate_module_explicit_session_test", 12)  # 12 total steps
    
    # Example usage - replace these with actual values
    cognos_url = "http://20.244.32.126:9300/api/v1"
    session_key = session_key or "YOUR_SESSION_KEY_HERE"  # Replace with actual session key
    module_id = "i5F34A7A52E2645C0AB03C34BA50941D7"  # Example module ID
    output_path = "./output/test_migrate_module_explicit_session"
    folder_id = "i9EA2C6D84DE9437CA99C62EB44E18F26"  # Optional folder ID
    
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
    print("\n=== Testing Module Migration with Explicit Session ===")
    try:
        success = migrate_module_with_explicit_session(
            module_id=module_id,
            output_path=output_path,
            cognos_url=cognos_url,
            session_key=session_key,
            folder_id=folder_id
        )
        if success:
            print("✅ Module migration with explicit session successful!")
            print(f"📁 Output saved to: {output_path}")
        else:
            print("❌ Module migration with explicit session failed!")
    except CognosAPIError as e:
        print(f"❌ Session error: {e}")
        print("The session key has expired. Please generate a new session key.")
        return
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return
    
    # Test 3: Test with CPF file (optional)
    print("\n=== Testing Module Migration with CPF File ===")
    cpf_file_path = "/path/to/your/file.cpf"  # Replace with actual CPF file path
    print(f"Note: To test with CPF file, provide a valid path to a CPF file.")
    print(f"Current CPF path (update if needed): {cpf_file_path}")
    
    # Uncomment the following to test with CPF file:
    # try:
    #     success = migrate_module_with_explicit_session(
    #         module_id=module_id,
    #         output_path=output_path + "_with_cpf",
    #         cognos_url=cognos_url,
    #         session_key=session_key,
    #         cpf_file_path=cpf_file_path
    #     )
    #     if success:
    #         print("✅ Module migration with CPF file successful!")
    #     else:
    #         print("❌ Module migration with CPF file failed!")
    # except Exception as e:
    #     print(f"❌ CPF migration error: {e}")
    
    # Test 4: Test with custom authentication header
    print("\n=== Testing Module Migration with Custom Auth Header ===")
    try:
        success = migrate_module_with_explicit_session(
            module_id=module_id,
            output_path=output_path + "_custom_auth",
            cognos_url=cognos_url,
            session_key=session_key,
            auth_key="IBM-BA-Authorization"  # Default value, can be customized
        )
        if success:
            print("✅ Module migration with custom auth header successful!")
        else:
            print("❌ Module migration with custom auth header failed!")
    except Exception as e:
        print(f"❌ Custom auth migration error: {e}")
    
    print("\n=== Test Complete ===")
    print("✨ All tests for migrate_module_with_explicit_session completed!")


if __name__ == "__main__":
    # Check if session key is provided as command line argument
    if len(sys.argv) > 1:
        session_key = sys.argv[1]
        main(session_key)
    else:
        print("Usage: python test_migrate_module_explicit_session.py <session_key>")
        print("\nExample:")
        print("python test_migrate_module_explicit_session.py 'CAM AWkyOTE4MjMwOEY3N0Q0QkIyOEUwRURFMTQ2NzREQjUwNgJxgOzruzMUgqRDMXRAZl2ODpkK'")
        print("\nNote: The session key expires over time. Use a fresh session key for testing.")
        print("\nThis test specifically focuses on the migrate_module_with_explicit_session function.")
        print("It tests module migration without using .env files or environment variables.")
        print("WebSocket integration provides real-time progress tracking during migration.")