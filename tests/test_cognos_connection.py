"""
Test script to connect to Cognos and retrieve report IDs
"""

import requests
import json
from cognos_migrator.config import ConfigManager

def test_cognos_connection():
    """Test connection to Cognos and retrieve content"""
    try:
        # Load configuration
        config_manager = ConfigManager()
        cognos_config = config_manager.get_cognos_config()
        
        print(f"🔗 Connecting to Cognos at: {cognos_config.base_url}")
        print(f"🔑 Using auth key: {cognos_config.auth_key}")
        
        # Set up headers
        headers = {
            cognos_config.auth_key: cognos_config.auth_value,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Test basic connection - get root content
        print("\n📋 Fetching root content...")
        response = requests.get(
            f"{cognos_config.base_url}/content",
            headers=headers,
            timeout=cognos_config.request_timeout
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            content = response.json()
            print("✅ Connection successful!")
            
            # Display root content
            if 'content' in content:
                print(f"\n📁 Found {len(content['content'])} root items:")
                for item in content['content'][:10]:  # Show first 10 items
                    print(f"  - {item.get('defaultName', 'Unnamed')} (Type: {item.get('type', 'Unknown')}, ID: {item.get('id', 'No ID')})")
                
                # Look for reports specifically
                reports = [item for item in content['content'] if item.get('type') == 'report']
                if reports:
                    print(f"\n📊 Found {len(reports)} reports:")
                    for report in reports[:5]:  # Show first 5 reports
                        print(f"  - Report: {report.get('defaultName', 'Unnamed')} (ID: {report.get('id', 'No ID')})")
                    
                    # Return first report ID for testing
                    return reports[0].get('id')
                else:
                    print("ℹ️  No reports found in root content. Let's explore folders...")
                    
                    # Look for folders to explore
                    folders = [item for item in content['content'] if item.get('type') == 'folder']
                    if folders:
                        print(f"\n📁 Found {len(folders)} folders:")
                        for folder in folders[:5]:
                            print(f"  - Folder: {folder.get('defaultName', 'Unnamed')} (ID: {folder.get('id', 'No ID')})")
                        
                        # Explore first folder
                        folder_id = folders[0].get('id')
                        if folder_id:
                            return explore_folder(cognos_config, headers, folder_id)
            else:
                print("⚠️  No content found in response")
                
        else:
            print(f"❌ Connection failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing connection: {e}")
        return None

def explore_folder(cognos_config, headers, folder_id):
    """Explore a folder to find reports"""
    try:
        print(f"\n🔍 Exploring folder ID: {folder_id}")
        response = requests.get(
            f"{cognos_config.base_url}/content/{folder_id}/items",
            headers=headers,
            timeout=cognos_config.request_timeout
        )
        
        if response.status_code == 200:
            content = response.json()
            if 'content' in content:
                print(f"📁 Folder contains {len(content['content'])} items:")
                
                for item in content['content'][:10]:
                    print(f"  - {item.get('defaultName', 'Unnamed')} (Type: {item.get('type', 'Unknown')}, ID: {item.get('id', 'No ID')})")
                
                # Look for reports in this folder
                reports = [item for item in content['content'] if item.get('type') == 'report']
                if reports:
                    print(f"\n📊 Found {len(reports)} reports in folder:")
                    for report in reports[:3]:
                        print(f"  - Report: {report.get('defaultName', 'Unnamed')} (ID: {report.get('id', 'No ID')})")
                    
                    # Return first report ID
                    return reports[0].get('id')
                else:
                    print("ℹ️  No reports found in this folder either")
                    return None
            else:
                print("⚠️  No content found in folder")
                return None
        else:
            print(f"❌ Failed to explore folder: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error exploring folder: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Testing Cognos Connection...")
    report_id = test_cognos_connection()
    
    if report_id:
        print(f"\n🎯 Found report ID for testing: {report_id}")
        print(f"\n💡 You can now test migration with:")
        print(f"   python main.py migrate-report {report_id}")
    else:
        print("\n⚠️  No report ID found for testing")
