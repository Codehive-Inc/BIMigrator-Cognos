#!/usr/bin/env python3
"""
Debug script to check what list_child_objects returns
"""

import sys
import os
from pathlib import Path

# Add the cognos_migrator directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cognos_migrator'))

from cognos_migrator.config import ConfigManager
from cognos_migrator.client import CognosClient

def debug_folder_contents():
    """Debug what's in the folder"""
    try:
        # Initialize client
        config_manager = ConfigManager()
        cognos_config = config_manager.get_cognos_config()
        client = CognosClient(cognos_config)
        
        folder_id = "i6765AFC28C0C471082E951F89A28C230"  # Tools folder
        
        print(f"🔍 Debugging folder contents for: {folder_id}")
        print("=" * 60)
        
        # Test connection
        if not client.test_connection():
            print("❌ Connection failed")
            return
        
        print("✅ Connected successfully")
        
        # Get raw response from list_child_objects
        print(f"\n📋 Getting child objects...")
        items = client.list_child_objects(folder_id)
        
        print(f"Raw response type: {type(items)}")
        print(f"Raw response length: {len(items) if hasattr(items, '__len__') else 'N/A'}")
        print(f"Raw response content: {items}")
        
        if isinstance(items, list):
            print(f"\n📝 Processing {len(items)} items:")
            for i, item in enumerate(items):
                print(f"  Item {i}:")
                print(f"    Type: {type(item)}")
                print(f"    Content: {item}")
                
                if isinstance(item, dict):
                    print(f"    Dict keys: {list(item.keys())}")
                    print(f"    Object type: {item.get('type', 'NO_TYPE')}")
                    print(f"    Object name: {item.get('defaultName', 'NO_NAME')}")
                    print(f"    Object ID: {item.get('id', 'NO_ID')}")
        
        # Try the list_reports_in_folder method
        print(f"\n🎯 Testing list_reports_in_folder...")
        reports = client.list_reports_in_folder(folder_id)
        print(f"Reports found: {len(reports)}")
        for report in reports:
            print(f"  - {report.name} (ID: {report.id})")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_folder_contents()