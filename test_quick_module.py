#!/usr/bin/env python3
"""
Quick test for module migration
"""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from cognos_migrator.main import setup_logging, migrate_module, migrate_module_with_session_key

def test_basic_functionality():
    """Test basic functionality without actual migration"""
    print("Testing basic module migration functionality")
    print("=" * 60)
    
    # Setup logging
    setup_logging("INFO")
    
    # Test 1: Test with dummy IDs (will fail but should handle gracefully)
    print("\n1. Testing migrate_module with dummy IDs:")
    try:
        results = migrate_module("i5F34A7A52E2645C0AB03C34BA50941D7", "i9EA2C6D84DE9437CA99C62EB44E18F26", "/tmp/test_module")
        print(f"Results: {results}")
    except Exception as e:
        print(f"Expected error occurred: {e}")
    
    # Test 2: Test with session key
    print("\n2. Testing migrate_module_with_session_key:")
    try:
        results = migrate_module_with_session_key(
            module_id="i5F34A7A52E2645C0AB03C34BA50941D7",
            cognos_url="http://20.244.32.126:9300/api/v1",
            session_key="CAM MTsxMDE6NzhmNDVlZjQtMTMzMS0zMmU3LTVhZWUtMmY3NzEyNzNiOWU1OjA5ODQ1OTI1MDc7MDszOzA7",
            folder_id="i9EA2C6D84DE9437CA99C62EB44E18F26",
            output_path="/tmp/test_module_session"
        )
        print(f"Results: {results}")
    except Exception as e:
        print(f"Expected error occurred: {e}")
    
    print("\n" + "=" * 60)
    print("Basic tests completed!")
    print("\nNote: These tests used dummy IDs and are expected to fail.")
    print("To test with real data:")
    print("1. Use 'python -m cognos_migrator.main list' to get valid module/folder IDs")
    print("2. Update the test with real IDs")

if __name__ == "__main__":
    test_basic_functionality()