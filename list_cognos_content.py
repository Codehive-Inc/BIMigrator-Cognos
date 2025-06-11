#!/usr/bin/env python3
"""
Cognos Content Discovery Tool
Lists available reports and folders with their IDs for migration testing
"""

import sys
import os
import logging
from pathlib import Path

# Add the cognos_migrator directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cognos_migrator'))

from cognos_migrator.config import ConfigManager
from cognos_migrator.client import CognosClient

def list_cognos_content():
    """List all available content from Cognos server"""
    print("🔍 COGNOS CONTENT DISCOVERY")
    print("=" * 60)
    
    try:
        # Load configuration
        config_manager = ConfigManager()
        cognos_config = config_manager.get_cognos_config()
        
        print(f"🔌 Connecting to Cognos...")
        print(f"   URL: {cognos_config.base_url}")
        print(f"   Username: {cognos_config.username}")
        print(f"   Namespace: {cognos_config.namespace}")
        
        # Create client and test connection
        client = CognosClient(cognos_config)
        
        if not client.test_connection():
            print("❌ Failed to connect to Cognos server")
            print("💡 Check your .env configuration and network connectivity")
            return False
            
        print("✅ Connected successfully!")
        print()
        
        # Get root content
        print("📋 LISTING ROOT CONTENT")
        print("-" * 40)
        
        root_objects = client.list_root_objects()
        
        if not root_objects:
            print("❌ No content found in root directory")
            return False
            
        print(f"Found {len(root_objects)} root objects:")
        print()
        
        reports_found = []
        folders_found = []
        
        for obj in root_objects:
            obj_type = obj.get('type', 'unknown')
            obj_id = obj.get('id', 'no-id')
            obj_name = obj.get('defaultName', 'Unknown')
            
            print(f"📁 {obj_type.upper()}: {obj_name}")
            print(f"   ID: {obj_id}")
            print(f"   Type: {obj_type}")
            
            if obj_type == 'folder':
                folders_found.append((obj_id, obj_name))
                print(f"   📂 Exploring folder contents...")
                
                # List folder contents
                try:
                    folder_items = client.list_child_objects(obj_id)
                    if folder_items:
                        print(f"   📋 Found {len(folder_items)} items in folder:")
                        
                        for item in folder_items[:10]:  # Show first 10 items
                            item_type = item.get('type', 'unknown')
                            item_id = item.get('id', 'no-id')
                            item_name = item.get('defaultName', 'Unknown')
                            
                            print(f"      └── {item_type}: {item_name}")
                            print(f"          ID: {item_id}")
                            
                            if item_type == 'report':
                                reports_found.append((item_id, item_name, obj_name))
                            elif item_type == 'folder':
                                folders_found.append((item_id, item_name))
                        
                        if len(folder_items) > 10:
                            print(f"      ... and {len(folder_items) - 10} more items")
                    else:
                        print(f"   📂 Folder is empty")
                        
                except Exception as e:
                    print(f"   ❌ Could not access folder contents: {e}")
                    
            elif obj_type == 'report':
                reports_found.append((obj_id, obj_name, "Root"))
                
            print()
        
        # Summary of findings
        print("=" * 60)
        print("📊 DISCOVERY SUMMARY")
        print("=" * 60)
        
        print(f"\n📈 REPORTS FOUND ({len(reports_found)}):")
        if reports_found:
            print("   Copy these IDs to test migration:")
            print()
            for i, (report_id, report_name, folder_name) in enumerate(reports_found, 1):
                print(f"   {i}. {report_name}")
                print(f"      ID: {report_id}")
                print(f"      Location: {folder_name}")
                print(f"      Command: python main.py migrate-report {report_id}")
                print()
        else:
            print("   ❌ No reports found")
            print("   💡 Check if you have access to reports or try different folders")
        
        print(f"\n📁 FOLDERS FOUND ({len(folders_found)}):")
        if folders_found:
            print("   Copy these IDs to test batch migration:")
            print()
            for i, (folder_id, folder_name) in enumerate(folders_found, 1):
                print(f"   {i}. {folder_name}")
                print(f"      ID: {folder_id}")
                print(f"      Command: python main.py migrate-folder {folder_id}")
                print()
        else:
            print("   ❌ No accessible folders found")
        
        # Generate quick test commands
        print("🚀 QUICK TEST COMMANDS")
        print("-" * 40)
        
        if reports_found:
            first_report = reports_found[0]
            print(f"Test single report migration:")
            print(f"python main.py migrate-report {first_report[0]}")
            print()
            
        if folders_found:
            first_folder = folders_found[0]
            print(f"Test folder migration:")
            print(f"python main.py migrate-folder {first_folder[0]}")
            print()
            
        print("Validate system first:")
        print("python main.py validate")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error discovering content: {e}")
        import traceback
        traceback.print_exc()
        return False

def search_for_specific_content(search_term=""):
    """Search for specific content by name"""
    print(f"\n🔍 SEARCHING FOR: '{search_term}'")
    print("-" * 40)
    
    try:
        config_manager = ConfigManager()
        cognos_config = config_manager.get_cognos_config()
        client = CognosClient(cognos_config)
        
        # Get all content and search
        root_objects = client.list_root_objects()
        matches = []
        
        for obj in root_objects:
            obj_name = obj.get('defaultName', '').lower()
            if search_term.lower() in obj_name:
                matches.append(obj)
                
            # Also search in folders
            if obj.get('type') == 'folder':
                try:
                    folder_items = client.list_child_objects(obj['id'])
                    for item in folder_items:
                        item_name = item.get('defaultName', '').lower()
                        if search_term.lower() in item_name:
                            matches.append(item)
                except:
                    pass
        
        if matches:
            print(f"✅ Found {len(matches)} matches:")
            for match in matches:
                print(f"   📋 {match.get('defaultName', 'Unknown')}")
                print(f"      ID: {match.get('id', 'no-id')}")
                print(f"      Type: {match.get('type', 'unknown')}")
                print()
        else:
            print(f"❌ No matches found for '{search_term}'")
            
    except Exception as e:
        print(f"❌ Search failed: {e}")

def get_detailed_object_info(object_id):
    """Get detailed information about a specific object"""
    print(f"\n🔍 DETAILED INFO FOR: {object_id}")
    print("-" * 40)
    
    try:
        config_manager = ConfigManager()
        cognos_config = config_manager.get_cognos_config()
        client = CognosClient(cognos_config)
        
        # Get object details
        obj_info = client.get_object(object_id)
        
        print(f"📋 Object Details:")
        print(f"   Name: {obj_info.get('defaultName', 'Unknown')}")
        print(f"   Type: {obj_info.get('type', 'unknown')}")
        print(f"   ID: {obj_info.get('id', 'no-id')}")
        print(f"   Created: {obj_info.get('creationTime', 'Unknown')}")
        print(f"   Modified: {obj_info.get('modificationTime', 'Unknown')}")
        print(f"   Owner: {obj_info.get('owner', {}).get('defaultName', 'Unknown')}")
        
        # If it's a report, try to get more details
        if obj_info.get('type') == 'report':
            print(f"\n📊 Report Specific Details:")
            try:
                report = client.get_cognos_report(object_id)
                if report:
                    print(f"   Specification Length: {len(report.specification)} characters")
                    print(f"   Data Sources: {len(report.data_sources)}")
            except:
                print(f"   Could not retrieve report specification")
                
    except Exception as e:
        print(f"❌ Failed to get object info: {e}")

def main():
    """Main function with interactive options"""
    print("🚀 COGNOS CONTENT DISCOVERY TOOL")
    print("=" * 60)
    print("This tool helps you find report_id and folder_id values for testing")
    print()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "search" and len(sys.argv) > 2:
            search_term = sys.argv[2]
            search_for_specific_content(search_term)
        elif command == "info" and len(sys.argv) > 2:
            object_id = sys.argv[2]
            get_detailed_object_info(object_id)
        else:
            print("❌ Invalid command")
            print("Usage:")
            print("  python list_cognos_content.py                    # List all content")
            print("  python list_cognos_content.py search <term>      # Search for specific content")
            print("  python list_cognos_content.py info <object_id>   # Get detailed info")
    else:
        # Default: list all content
        success = list_cognos_content()
        
        if success:
            print("\n💡 NEXT STEPS:")
            print("1. Copy a report_id from above and test:")
            print("   python main.py migrate-report <report_id>")
            print()
            print("2. Copy a folder_id from above and test:")
            print("   python main.py migrate-folder <folder_id>")
            print()
            print("3. Search for specific content:")
            print("   python list_cognos_content.py search <search_term>")
            print()
            print("4. Get detailed info about an object:")
            print("   python list_cognos_content.py info <object_id>")

if __name__ == "__main__":
    main()