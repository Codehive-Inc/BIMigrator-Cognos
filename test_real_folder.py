#!/usr/bin/env python3
"""
Test module migration with real folder IDs
"""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from cognos_migrator.main import setup_logging, migrate_module_with_session_key

def test_with_library_folder():
    """Test with the library folder ID from the list command output"""
    print("Testing module migration with library folder")
    print("=" * 60)
    
    # Setup logging
    setup_logging("INFO")
    
    # Using real module ID from Cognos instance
    module_id = "i5F34A7A52E2645C0AB03C34BA50941D7"
    folder_id = "i9EA2C6D84DE9437CA99C62EB44E18F26"  # Using the provided folder ID
    cognos_url = "http://20.244.32.126:9300/api/v1"
    session_key = "CAM MTsxMDE6NzhmNDVlZjQtMTMzMS0zMmU3LTVhZWUtMmY3NzEyNzNiOWU1OjA5ODQ1OTI1MDc7MDszOzA7"
    output_path = "/tmp/test_library_module"
    
    print(f"Module ID: {module_id}")
    print(f"Folder ID: {folder_id}")
    print(f"Cognos URL: {cognos_url}")
    print(f"Output Path: {output_path}")
    print()
    
    try:
        results = migrate_module_with_session_key(
            module_id=module_id,
            cognos_url=cognos_url,
            session_key=session_key,
            folder_id=folder_id,
            output_path=output_path
        )
        
        print(f"\nMigration Results: {results}")
        
        if results:
            successful = sum(1 for success in results.values() if success)
            total = len(results)
            print(f"Success Rate: {successful}/{total} reports")
            print(f"\nDetailed results:")
            for report_id, success in results.items():
                status = "✓" if success else "✗"
                print(f"  {status} Report {report_id}")
        else:
            print("No results returned or migration failed")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_with_library_folder()
    print("\nNote: This test uses the 'library' folder which exists in the system.")
    print("However, you need to provide a valid module ID for it to work properly.")