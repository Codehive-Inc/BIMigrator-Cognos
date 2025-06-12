#!/usr/bin/env python3
"""
Test Cognos Connection - Updated for Session-Based Authentication
Tests connection to Cognos Analytics and lists available content
"""

import sys
import os
import logging
from pathlib import Path

# Add the cognos_migrator directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cognos_migrator'))

from cognos_migrator.config import ConfigManager
from cognos_migrator.client import CognosClient

def test_cognos_connection():
    """Test connection to Cognos using the proper client"""
    print("🚀 TESTING COGNOS CONNECTION")
    print("=" * 50)
    
    try:
        # Load configuration
        print("📋 Loading configuration...")
        config_manager = ConfigManager()
        cognos_config = config_manager.get_cognos_config()
        
        print(f"🔗 Connection Details:")
        print(f"   URL: {cognos_config.base_url}")
        print(f"   Username: {cognos_config.username}")
        print(f"   Namespace: {cognos_config.namespace}")
        print(f"   Auth Key: {cognos_config.auth_key}")
        
        if hasattr(cognos_config, 'base_auth_token') and cognos_config.base_auth_token:
            print(f"   Base Token: {cognos_config.base_auth_token[:20]}...")
            print(f"   🔐 Using session-based authentication")
        else:
            print(f"   🔐 Using direct authentication")
        
        print()
        
        # Create client (this will trigger authentication)
        print("🔌 Creating Cognos client...")
        client = CognosClient(cognos_config)
        
        print("✅ Client created successfully!")
        
        # Test the connection
        print("\n🧪 Testing connection...")
        if client.test_connection():
            print("✅ Connection test PASSED!")
            
            # Try to get session info
            try:
                print("\n📋 Getting session information...")
                session_info = client.get_session_info()
                if session_info:
                    print("✅ Session info retrieved:")
                    print(f"   User: {session_info.get('defaultName', 'Unknown')}")
                    print(f"   Locale: {session_info.get('locale', 'Unknown')}")
                    print(f"   Anonymous: {session_info.get('isAnonymous', 'Unknown')}")
                else:
                    print("⚠️  Session info not available")
            except Exception as e:
                print(f"⚠️  Could not get session info: {e}")
            
            # Try to list content
            print("\n📁 Listing root content...")
            try:
                root_objects = client.list_root_objects()
                if root_objects:
                    print(f"✅ Found {len(root_objects)} root objects:")
                    
                    reports_found = []
                    folders_found = []
                    
                    for obj in root_objects:
                        obj_type = obj.get('type', 'unknown')
                        obj_name = obj.get('defaultName', 'Unknown')
                        obj_id = obj.get('id', 'no-id')
                        
                        print(f"   📋 {obj_type.upper()}: {obj_name}")
                        print(f"      ID: {obj_id}")
                        
                        if obj_type == 'report':
                            reports_found.append((obj_id, obj_name))
                        elif obj_type == 'folder':
                            folders_found.append((obj_id, obj_name))
                    
                    # Summary
                    print(f"\n📊 Content Summary:")
                    print(f"   Reports found: {len(reports_found)}")
                    print(f"   Folders found: {len(folders_found)}")
                    
                    # Explore a folder if no reports found
                    if not reports_found and folders_found:
                        print(f"\n🔍 No reports in root, exploring first folder...")
                        folder_id, folder_name = folders_found[0]
                        reports_found = explore_folder_for_reports(client, folder_id, folder_name)
                    
                    # Return test recommendations
                    return provide_test_recommendations(reports_found, folders_found)
                    
                else:
                    print("❌ No content found - check permissions")
                    return False
                    
            except Exception as e:
                print(f"❌ Failed to list content: {e}")
                return False
                
        else:
            print("❌ Connection test FAILED!")
            print("💡 Check your .env configuration:")
            print("   - COGNOS_BASE_URL")
            print("   - COGNOS_USERNAME")
            print("   - COGNOS_PASSWORD")
            print("   - COGNOS_NAMESPACE")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed with error: {e}")
        print("\n🔧 Troubleshooting steps:")
        print("1. Check your .env file configuration")
        print("2. Verify Cognos server is accessible")
        print("3. Check username/password credentials")
        print("4. Verify namespace is correct (try 'CognosEx' or 'LDAP')")
        import traceback
        traceback.print_exc()
        return False

def explore_folder_for_reports(client, folder_id, folder_name):
    """Explore a folder to find reports"""
    print(f"   📁 Exploring folder: {folder_name}")
    
    try:
        folder_items = client.list_child_objects(folder_id)
        reports_found = []
        
        if folder_items:
            print(f"   📋 Found {len(folder_items)} items in folder:")
            
            for item in folder_items[:10]:  # Show first 10 items
                item_type = item.get('type', 'unknown')
                item_name = item.get('defaultName', 'Unknown')
                item_id = item.get('id', 'no-id')
                
                print(f"      - {item_type}: {item_name}")
                
                if item_type == 'report':
                    reports_found.append((item_id, item_name))
            
            if len(folder_items) > 10:
                print(f"      ... and {len(folder_items) - 10} more items")
        
        return reports_found
        
    except Exception as e:
        print(f"   ⚠️  Could not explore folder: {e}")
        return []

def provide_test_recommendations(reports_found, folders_found):
    """Provide testing recommendations based on what was found"""
    print(f"\n🎯 TEST RECOMMENDATIONS")
    print("=" * 30)
    
    if reports_found:
        print(f"✅ REPORTS AVAILABLE FOR TESTING:")
        for i, (report_id, report_name) in enumerate(reports_found[:3], 1):
            print(f"   {i}. {report_name}")
            print(f"      Command: python main.py migrate-report {report_id}")
        
        if len(reports_found) > 3:
            print(f"      ... and {len(reports_found) - 3} more reports")
        
        print(f"\n💡 Quick test command:")
        print(f"   python main.py migrate-report {reports_found[0][0]}")
    
    if folders_found:
        print(f"\n📁 FOLDERS AVAILABLE FOR TESTING:")
        for i, (folder_id, folder_name) in enumerate(folders_found[:3], 1):
            print(f"   {i}. {folder_name}")
            print(f"      Command: python main.py migrate-folder {folder_id}")
        
        if len(folders_found) > 3:
            print(f"      ... and {len(folders_found) - 3} more folders")
        
        if not reports_found:
            print(f"\n💡 Try exploring folders for reports:")
            print(f"   python main.py list")
            print(f"   python list_cognos_content.py")
    
    if not reports_found and not folders_found:
        print("❌ No testable content found")
        print("💡 Possible solutions:")
        print("   - Check with Cognos administrator for access")
        print("   - Try different credentials or namespace")
        print("   - Verify you can access content via Cognos web interface")
        return False
    
    print(f"\n🚀 NEXT STEPS:")
    print("1. Copy a command from above and test migration")
    print("2. Check results in the output/ directory")
    print("3. Run: python main.py list  (for more options)")
    
    return True

def main():
    """Main test function"""
    print("🧪 COGNOS CONNECTION TEST SUITE")
    print("=" * 50)
    print("This will test your connection to Cognos Analytics")
    print("and provide you with report/folder IDs for testing.\n")
    
    # Enable basic logging for debugging
    logging.basicConfig(level=logging.WARNING)
    
    success = test_cognos_connection()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 CONNECTION TEST COMPLETED SUCCESSFULLY!")
        print("✅ Your system is ready for Cognos to Power BI migration")
    else:
        print("❌ CONNECTION TEST FAILED")
        print("🔧 Please fix the issues above before proceeding")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)