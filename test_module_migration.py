#!/usr/bin/env python3
"""
Test script for module migration functions
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from cognos_migrator.main import migrate_module, migrate_module_with_session_key, setup_logging

def test_migrate_module():
    """Test the migrate_module function"""
    print("=" * 60)
    print("Testing migrate_module function")
    print("=" * 60)
    
    # Using real module ID from Cognos instance
    module_id = "i5F34A7A52E2645C0AB03C34BA50941D7"
    folder_id = "i9EA2C6D84DE9437CA99C62EB44E18F26"
    output_path = "/tmp/test_module_migration"
    
    print(f"Module ID: {module_id}")
    print(f"Folder ID: {folder_id}")
    print(f"Output Path: {output_path}")
    print()
    
    try:
        # Call the migrate_module function
        results = migrate_module(module_id, folder_id, output_path)
        
        print(f"Migration Results: {results}")
        
        if results:
            successful = sum(1 for success in results.values() if success)
            total = len(results)
            print(f"Success Rate: {successful}/{total} reports")
        else:
            print("No results returned or migration failed")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()


def test_migrate_module_with_session_key():
    """Test the migrate_module_with_session_key function"""
    print("\n" + "=" * 60)
    print("Testing migrate_module_with_session_key function")
    print("=" * 60)
    
    # Using real module ID from Cognos instance
    module_id = "i5F34A7A52E2645C0AB03C34BA50941D7"
    folder_id = "i9EA2C6D84DE9437CA99C62EB44E18F26"
    cognos_url = "http://20.244.32.126:9300/api/v1"
    session_key = "CAM MTsxMDE6NzhmNDVlZjQtMTMzMS0zMmU3LTVhZWUtMmY3NzEyNzNiOWU1OjA5ODQ1OTI1MDc7MDszOzA7"
    output_path = "/tmp/test_module_migration_session"
    
    print(f"Module ID: {module_id}")
    print(f"Folder ID: {folder_id}")
    print(f"Cognos URL: {cognos_url}")
    print(f"Session Key: {session_key[:20]}...")  # Show only first 20 chars for security
    print(f"Output Path: {output_path}")
    print()
    
    try:
        # Call the migrate_module_with_session_key function
        results = migrate_module_with_session_key(
            module_id=module_id,
            cognos_url=cognos_url,
            session_key=session_key,
            folder_id=folder_id,
            output_path=output_path
        )
        
        print(f"Migration Results: {results}")
        
        if results:
            successful = sum(1 for success in results.values() if success)
            total = len(results)
            print(f"Success Rate: {successful}/{total} reports")
        else:
            print("No results returned or migration failed")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()


def test_with_real_ids():
    """Test with real IDs from the main function"""
    print("\n" + "=" * 60)
    print("Testing with real IDs from main.py")
    print("=" * 60)
    
    # Using real module ID from Cognos instance
    module_id = "i5F34A7A52E2645C0AB03C34BA50941D7"
    folder_id = "i9EA2C6D84DE9437CA99C62EB44E18F26"
    cognos_url = "http://20.244.32.126:9300/api/v1"
    session_key = "CAM MTsxMDE6Y2I3ZTQ0N2ItYjgyNC01NTZhLTRmZmYtYmQzYjBlYTIyNzQ3OjA4MzY1MzgzMTM7MDszOzA7"
    
    print("Testing migrate_module_with_session_key with real values...")
    
    try:
        results = migrate_module_with_session_key(
            module_id=module_id,
            cognos_url=cognos_url,
            session_key=session_key,
            folder_id=folder_id,
            output_path="/tmp/real_module_test"
        )
        
        print(f"Results: {results}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main test function"""
    # Setup logging
    setup_logging("DEBUG")
    
    print("Module Migration Test Suite")
    print("=" * 60)
    
    # Check if we have a .env file
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print("WARNING: .env file not found. Tests may fail without proper configuration.")
        print("Please ensure your .env file contains:")
        print("  - COGNOS_URL")
        print("  - COGNOS_USERNAME")
        print("  - COGNOS_PASSWORD")
        print("  - COGNOS_NAMESPACE")
        print("  - OUTPUT_DIRECTORY")
        print("  - TEMPLATE_DIRECTORY")
        print()
    
    # Run tests based on command line arguments
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        if test_name == "module":
            test_migrate_module()
        elif test_name == "session":
            test_migrate_module_with_session_key()
        elif test_name == "real":
            test_with_real_ids()
        else:
            print(f"Unknown test: {test_name}")
            print("Available tests: module, session, real")
    else:
        # Run all tests
        test_migrate_module()
        test_migrate_module_with_session_key()
        
        print("\n" + "=" * 60)
        print("To test with real IDs, run:")
        print("python test_module_migration.py real")


if __name__ == "__main__":
    main()