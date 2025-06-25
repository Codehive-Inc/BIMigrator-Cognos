#!/usr/bin/env python3
"""
Test script for cognos_migrator package - explicit session migration functions

This is the only test file needed for the refactored cognos_migrator package.
Tests all essential functions exposed in the public API.
"""

import sys
import logging

# Test the public API import
import cognos_migrator

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
    """Main test function for cognos_migrator public API"""
    
    print(f"🧪 Testing cognos_migrator v{cognos_migrator.__version__}")
    print(f"📋 Available functions: {cognos_migrator.__all__}")
    
    # Configuration
    cognos_url = "http://20.244.32.126:9300/api/v1"
    session_key = session_key or "CAM MTsxMDE6NGE0NjhiZjYtNTU3OC0yZjY2LTg2YmYtY2FmNmM3ZDA0YWQ5OjI0OTk5Mjg0OTU7MDszOzA;"
    module_id = "i5F34A7A52E2645C0AB03C34BA50941D7"
    folder_id = "i9EA2C6D84DE9437CA99C62EB44E18F26"
    report_id = "iFEE26FFBB98643308E6FEFC235B2D2CF"
    output_path = "./test_output"
    
    # Test 1: Test connection
    print("\n=== Testing Connection ===")
    try:
        is_connected = cognos_migrator.test_cognos_connection(cognos_url, session_key)
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
        success = cognos_migrator.migrate_module_with_explicit_session(
            module_id=module_id,
            output_path=output_path,
            cognos_url=cognos_url,
            session_key=session_key,
            folder_id=folder_id
        )
        if success:
            print("✅ Module migration successful!")
            print(f"📁 Output saved to: {output_path}")
        else:
            print("❌ Module migration failed!")
    except cognos_migrator.CognosAPIError as e:
        print(f"❌ Cognos API Error: {e}")
        return
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return
    
    # Test 3: Test single report migration
    print("\n=== Testing Single Report Migration ===")
    try:
        success = cognos_migrator.migrate_single_report_with_explicit_session(
            report_id=report_id,
            output_path=output_path + "_single_report",
            cognos_url=cognos_url,
            session_key=session_key
        )
        if success:
            print("✅ Single report migration successful!")
        else:
            print("❌ Single report migration failed!")
    except cognos_migrator.CognosAPIError as e:
        print(f"❌ Cognos API Error: {e}")
    except Exception as e:
        print(f"❌ Single report migration error: {e}")
    
    # Test 4: Test post-processing
    print("\n=== Testing Post-Processing ===")
    try:
        success = cognos_migrator.post_process_module_with_explicit_session(
            module_id=module_id,
            output_path=output_path,
            cognos_url=cognos_url,
            session_key=session_key
        )
        if success:
            print("✅ Post-processing successful!")
        else:
            print("❌ Post-processing failed!")
    except Exception as e:
        print(f"❌ Post-processing error: {e}")
    
    print("\n=== All Tests Complete ===")
    print("✨ All cognos_migrator public API functions tested!")


if __name__ == "__main__":
    # Check if session key is provided as command line argument
    if len(sys.argv) > 1:
        session_key = sys.argv[1]
        main(session_key)
    else:
        print("Usage: python test_migrate_module_explicit_session.py <session_key>")
        print("\nExample:")
        print("python test_migrate_module_explicit_session.py 'CAM AWkyOTE4MjMwOEY3N0Q0QkIyOEUwRURFMTQ2NzREQjUwNgJxgOzruzMUgqRDMXRAZl2ODpkK'")
        print("\nNote: This test validates the complete cognos_migrator public API.")
        print("It tests all functions exposed in cognos_migrator.__all__")
        print("The package works entirely without .env files or environment variables.")